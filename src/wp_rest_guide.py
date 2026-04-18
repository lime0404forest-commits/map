# -*- coding: utf-8 -*-
"""
WordPress REST API から記事一覧を取得し、JA/EN をリンク候補の1行にまとめる。

- 各言語の URL は **REST の ``link`` をそのまま**使う（既定）。言語ごとに別 ID・別パスが返る前提。
- Polylang 等の ``translations``（言語コード → 相手の投稿 ID）があれば、slug が違っても 1 行にまとめる（自動検出）。無ければ ``slug`` 一致。
- 取得元 URL の ``lang=`` を **link に付け足す**のは、ソースに ``append_fetch_lang_to_link: true`` を書いたときだけ（同一 link しか返らないサイト向けの任意オプション）。
- 投稿に ``lang`` が付いているサイト向けに、``filter_posts_by_rest_lang: true`` で JP / EN リストを言語別に寄せる（**既定は false**。誤って片方リストを空にしやすいため）。``rest_lang_accept_ja`` / ``rest_lang_accept_en`` で許容コードを調整可。
- 突き合わせ後、同一 URL 相当の行は ``url_en`` を空にして単一言語として扱う。
"""
from __future__ import annotations

import html as html_lib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_WP_REST_GUIDE_SOURCES: List[Dict[str, str]] = []

USER_AGENT = "MapEditor-wp-rest-guide/1.0"


def _request_json(url: str, timeout: float = 30.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _normalize_rest_base(base: str) -> str:
    b = (base or "").strip().rstrip("/")
    return b


def fetch_posts_for_source(
    rest_posts_url: str,
    *,
    per_page: int = 100,
    max_pages: int = 200,
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    .../wp/v2/posts のベース URL。クエリ（例: ?lang=jp）が付いていても page/per_page を & で連結して全ページ取得。
    """
    base = _normalize_rest_base(rest_posts_url)
    if not base:
        return []
    out: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        q = urllib.parse.urlencode({"page": str(page), "per_page": str(per_page)})
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}{q}"
        try:
            data = _request_json(url, timeout=timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
            break
        if not isinstance(data, list) or len(data) == 0:
            break
        for item in data:
            if isinstance(item, dict):
                out.append(item)
        if len(data) < per_page:
            break
    return out


def _post_slug(p: Dict[str, Any]) -> str:
    s = p.get("slug")
    return (s or "").strip() if isinstance(s, str) else ""


def short_slug_for_display(slug: str) -> str:
    """一覧用。フル URL 形式の slug はパスの末尾だけに短縮（先頭に長い URL を出さない）。"""
    s = (slug or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        try:
            p = urllib.parse.urlparse(s)
            tail = (p.path or "").strip("/").split("/")[-1]
            return (tail or "post")[:56]
        except Exception:
            return s[:40]
    return s[:56]


def plain_text_for_guide_title(raw: str) -> str:
    """
    REST の title.rendered や手編集 JSON 用に、HTML 除去・改行正規化・
    文中に紛れた http(s) URL 文字列を取り除く（一覧先頭のパーマリンク表示を抑える）。
    """
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"https?://[^\s]+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _post_title(p: Dict[str, Any]) -> str:
    t = p.get("title")
    if isinstance(t, dict):
        inner = t.get("rendered", "")
        return inner if isinstance(inner, str) else ""
    if isinstance(t, str):
        return t
    return ""


def _post_link(p: Dict[str, Any]) -> str:
    link = p.get("link")
    return link.strip() if isinstance(link, str) else ""


def _rest_post_lang(post: Optional[Dict[str, Any]]) -> str:
    """Polylang 等が posts に付ける lang（例: ja, en）。無ければ空。"""
    if not isinstance(post, dict):
        return ""
    v = post.get("lang")
    return str(v).strip().lower() if isinstance(v, str) and v.strip() else ""


def infer_lang_code_from_permalink(url: str) -> str:
    """
    REST に ``lang`` が無いサイト向け: パスが ``/en/`` で始まる（または ``/en`` のみ）なら ``en``、
    それ以外で有効なパスがある URL は ``ja`` とみなす。URL が空なら空。
    """
    if not isinstance(url, str) or not url.strip():
        return ""
    try:
        raw = (urllib.parse.urlparse(url.strip()).path or "").lower()
    except Exception:
        return ""
    if raw.startswith("/en/") or raw.rstrip("/") == "/en":
        return "en"
    if not raw or raw == "/":
        return ""
    return "ja"


def _effective_rest_lang(post: Optional[Dict[str, Any]], url: str) -> str:
    """REST の lang があればそれを使い、無ければパーマリンクから推論。"""
    if isinstance(post, dict):
        lg = _rest_post_lang(post)
        if lg:
            return lg
    return infer_lang_code_from_permalink(url)


def _lang_matches_accept(lang: str, accept: Tuple[str, ...]) -> bool:
    if not lang:
        return False
    for a in accept:
        al = (a or "").strip().lower()
        if not al:
            continue
        if lang == al or lang.startswith(al):
            return True
    return False


def filter_posts_by_rest_lang(
    posts: List[Dict[str, Any]],
    accept_langs: Tuple[str, ...],
) -> List[Dict[str, Any]]:
    """
    REST の ``lang`` が付いている投稿だけを想定言語で絞り込む。
    いずれの投稿にも ``lang`` が無いときは何もしない（誤って空にしない）。
    絞り込みの結果が空になるときは元リストを返す（取得ゼロを防ぐ）。
    """
    if not posts or not accept_langs:
        return list(posts)
    has_meta = any(_rest_post_lang(p) for p in posts if isinstance(p, dict))
    if not has_meta:
        return list(posts)
    out: List[Dict[str, Any]] = []
    for p in posts:
        if not isinstance(p, dict):
            continue
        lg = _rest_post_lang(p)
        if not lg or _lang_matches_accept(lg, accept_langs):
            out.append(p)
    return out if out else list(posts)


def normalize_paired_row_urls_for_single_language(rows: List[Dict[str, Any]]) -> None:
    """
    同一 link（または lang クエリのみ差）のときは日英2本ではないので、EN 欄用 URL を空にする。
    """
    for row in rows:
        if not isinstance(row, dict):
            continue
        uj = (row.get("url_jp") or "").strip()
        ue = (row.get("url_en") or "").strip()
        if not uj or not ue:
            continue
        if uj == ue or urls_are_locale_duplicate_only(uj, ue):
            row["url_en"] = ""
            row["rest_lang_en"] = ""


def urls_are_locale_duplicate_only(uj: str, ue: str) -> bool:
    """
    同一のパス・同一の非-lang クエリで、lang= の有無・値だけが違う URL の組か。
    （link が同一で ?lang= だけ付け分けているとき → 実質1記事なので「日英2本」ではない）
    """
    if not (uj and ue):
        return False
    try:
        a = urllib.parse.urlparse(uj.strip())
        b = urllib.parse.urlparse(ue.strip())
    except Exception:
        return False
    if a.scheme.lower() != b.scheme.lower():
        return False
    if a.netloc.lower() != b.netloc.lower():
        return False
    pa = (a.path or "/").rstrip("/") or "/"
    pb = (b.path or "/").rstrip("/") or "/"
    if pa != pb:
        return False

    def _qs_without_lang(query: str) -> Dict[str, List[str]]:
        q = urllib.parse.parse_qs(query, keep_blank_values=True)
        return {k: v for k, v in q.items() if k.lower() != "lang"}

    return _qs_without_lang(a.query) == _qs_without_lang(b.query)


def link_row_availability_tag(row: Dict[str, Any]) -> str:
    """
    一覧用: 実質「別パスの日英」か、「同一ページの lang 付け分けだけ」かを区別した短いタグ文字列。
    """
    uj = (row.get("url_jp") or "").strip()
    ue = (row.get("url_en") or "").strip()
    lj = (row.get("rest_lang_jp") or "").strip().lower()
    le = (row.get("rest_lang_en") or "").strip().lower()
    if not lj and uj:
        lj = infer_lang_code_from_permalink(uj).lower()
    if not le and ue:
        le = infer_lang_code_from_permalink(ue).lower()

    def _lbl(code: str, default: str) -> str:
        s = (code or "").strip().lower()
        if s == "en":
            return "EN"
        if s in ("ja", "jp"):
            return "JP"
        return default if not s else s[:6].upper()

    if not uj and not ue:
        return "—"
    if uj and not ue:
        return _lbl(lj, "JP")
    if ue and not uj:
        return _lbl(le, "EN")
    if uj == ue:
        return "同一URL"
    if urls_are_locale_duplicate_only(uj, ue):
        return "単一言語"
    return "JP・EN"


def _lang_value_from_posts_api_url(posts_api_url: str) -> str:
    """.../posts?lang=jp のような REST URL から lang 値だけ取る（無ければ空）。"""
    try:
        u = urllib.parse.urlparse((posts_api_url or "").strip())
        q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
        v = (q.get("lang") or [None])[0]
        return str(v).strip() if v else ""
    except Exception:
        return ""


def _merge_lang_query_onto_permalink(permalink: str, posts_api_url: str) -> str:
    """
    Polylang 等で REST の ?lang= だけが効いて link フィールドは同一正規 URL のまま、というときに
    パーマリンクへ lang を付けて url_jp / url_en を区別する。
    """
    pl = (permalink or "").strip()
    if not pl:
        return ""
    lang_val = _lang_value_from_posts_api_url(posts_api_url)
    if not lang_val:
        return pl
    try:
        p = urllib.parse.urlparse(pl)
        q = urllib.parse.parse_qs(p.query, keep_blank_values=True)
        cur = (q.get("lang") or [None])[0]
        if cur and str(cur).strip().lower() == lang_val.lower():
            return pl
        q["lang"] = [lang_val]
        flat: List[Tuple[str, str]] = []
        for k, vs in q.items():
            for v in vs:
                flat.append((k, v))
        new_query = urllib.parse.urlencode(flat)
        return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
    except Exception:
        return pl


def _post_id(p: Dict[str, Any]) -> Optional[int]:
    try:
        v = p.get("id")
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _locale_key_for_translation(locale: str) -> str:
    s = (locale or "").strip().lower().replace("-", "_")
    if not s:
        return ""
    if "_" in s:
        return s.split("_", 1)[0]
    return s[:2] if len(s) >= 2 else s


def extract_translation_id_map(post: Dict[str, Any]) -> Dict[str, int]:
    """
    Polylang（Pro や REST 拡張）が返す翻訳 ID 一覧を正規化。
    キーは小文字の言語コード（en, ja, jp など）。値は投稿 ID（int）。
    """
    out: Dict[str, int] = {}
    if not isinstance(post, dict):
        return out
    t = post.get("translations")
    if isinstance(t, dict):
        for k, v in t.items():
            key = str(k).strip().lower()
            if not key:
                continue
            try:
                out[key] = int(v)
            except (TypeError, ValueError):
                pass
    alt = post.get("polylang_translations")
    if isinstance(alt, list):
        for item in alt:
            if not isinstance(item, dict):
                continue
            loc = item.get("locale") or item.get("slug") or item.get("lang") or ""
            key = _locale_key_for_translation(str(loc))
            if not key:
                continue
            vid = item.get("id") if item.get("id") is not None else item.get("ID")
            try:
                out[key] = int(vid)
            except (TypeError, ValueError):
                pass
    return out


def _first_translation_id(trans: Dict[str, int], keys: Tuple[str, ...]) -> Optional[int]:
    for raw in keys:
        k = raw.strip().lower()
        if k in trans:
            return trans[k]
    for raw in keys:
        pref = raw.strip().lower()
        for kk, vid in trans.items():
            if kk == pref or kk.startswith(pref):
                return vid
    return None


def _apply_urls_with_lang(
    ja: Optional[Dict[str, Any]],
    en: Optional[Dict[str, Any]],
    *,
    ja_posts_api_url: str,
    en_posts_api_url: str,
    append_fetch_lang_to_link: bool,
) -> Tuple[str, str]:
    uj = _post_link(ja) if ja else ""
    ue = _post_link(en) if en else ""
    if append_fetch_lang_to_link:
        if ja_posts_api_url and uj:
            uj = _merge_lang_query_onto_permalink(uj, ja_posts_api_url)
        if en_posts_api_url and ue:
            ue = _merge_lang_query_onto_permalink(ue, en_posts_api_url)
    return uj, ue


def _pair_posts_by_slug(
    posts_ja: List[Dict[str, Any]],
    posts_en: List[Dict[str, Any]],
    *,
    ja_posts_api_url: str,
    en_posts_api_url: str,
    append_fetch_lang_to_link: bool,
) -> List[Dict[str, str]]:
    by_slug_ja: Dict[str, Dict[str, Any]] = {}
    for p in posts_ja:
        slug = _post_slug(p)
        if slug:
            by_slug_ja[slug] = p
    by_slug_en: Dict[str, Dict[str, Any]] = {}
    for p in posts_en:
        slug = _post_slug(p)
        if slug:
            by_slug_en[slug] = p
    all_slugs = sorted(set(by_slug_ja.keys()) | set(by_slug_en.keys()))
    rows: List[Dict[str, str]] = []
    for slug in all_slugs:
        ja = by_slug_ja.get(slug)
        en = by_slug_en.get(slug)
        uj, ue = _apply_urls_with_lang(
            ja,
            en,
            ja_posts_api_url=ja_posts_api_url,
            en_posts_api_url=en_posts_api_url,
            append_fetch_lang_to_link=append_fetch_lang_to_link,
        )
        rows.append(
            {
                "slug": slug,
                "title_jp": plain_text_for_guide_title(_post_title(ja) if ja else ""),
                "title_en": plain_text_for_guide_title(_post_title(en) if en else ""),
                "url_jp": uj,
                "url_en": ue,
                "rest_lang_jp": _effective_rest_lang(ja, uj),
                "rest_lang_en": _effective_rest_lang(en, ue),
            }
        )
    return rows


def _find_en_post_for_ja(
    ja: Dict[str, Any],
    by_id_en: Dict[int, Dict[str, Any]],
    keys_en_from_ja: Tuple[str, ...],
    keys_ja_from_en: Tuple[str, ...],
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    """JA 投稿の translations から EN を探す。無ければ EN 側の translations に JA の id がある投稿を逆引き。"""
    trans = extract_translation_id_map(ja)
    en_id = _first_translation_id(trans, keys_en_from_ja)
    if en_id is not None:
        en = by_id_en.get(int(en_id))
        if en is not None:
            return en, int(en_id)
    ja_id = _post_id(ja)
    if ja_id is None:
        return None, None
    for e in by_id_en.values():
        t2 = extract_translation_id_map(e)
        jid = _first_translation_id(t2, keys_ja_from_en)
        if jid is not None and int(jid) == int(ja_id):
            eid = _post_id(e)
            if eid is not None:
                return e, eid
    return None, None


def _pair_posts_by_translations(
    posts_ja: List[Dict[str, Any]],
    posts_en: List[Dict[str, Any]],
    *,
    ja_posts_api_url: str,
    en_posts_api_url: str,
    keys_en_from_ja: Tuple[str, ...],
    keys_ja_from_en: Tuple[str, ...],
    append_fetch_lang_to_link: bool,
) -> List[Dict[str, str]]:
    by_id_en: Dict[int, Dict[str, Any]] = {}
    for p in posts_en:
        pid = _post_id(p)
        if pid is not None:
            by_id_en[pid] = p
    used_en: set[int] = set()
    rows: List[Dict[str, str]] = []
    for ja in posts_ja:
        if not isinstance(ja, dict):
            continue
        en, en_id = _find_en_post_for_ja(ja, by_id_en, keys_en_from_ja, keys_ja_from_en)
        if en is not None and en_id is not None:
            used_en.add(en_id)
        slug = _post_slug(ja)
        if not slug and en:
            slug = _post_slug(en)
        uj, ue = _apply_urls_with_lang(
            ja,
            en,
            ja_posts_api_url=ja_posts_api_url,
            en_posts_api_url=en_posts_api_url,
            append_fetch_lang_to_link=append_fetch_lang_to_link,
        )
        rows.append(
            {
                "slug": slug,
                "title_jp": plain_text_for_guide_title(_post_title(ja)),
                "title_en": plain_text_for_guide_title(_post_title(en) if en else ""),
                "url_jp": uj,
                "url_en": ue,
                "rest_lang_jp": _effective_rest_lang(ja, uj),
                "rest_lang_en": _effective_rest_lang(en, ue),
            }
        )
    for en in posts_en:
        if not isinstance(en, dict):
            continue
        eid = _post_id(en)
        if eid is None or eid in used_en:
            continue
        slug = _post_slug(en)
        uj, ue = _apply_urls_with_lang(
            None,
            en,
            ja_posts_api_url=ja_posts_api_url,
            en_posts_api_url=en_posts_api_url,
            append_fetch_lang_to_link=append_fetch_lang_to_link,
        )
        rows.append(
            {
                "slug": slug,
                "title_jp": "",
                "title_en": plain_text_for_guide_title(_post_title(en)),
                "url_jp": uj,
                "url_en": ue,
                "rest_lang_jp": "",
                "rest_lang_en": _effective_rest_lang(en, ue),
            }
        )
    rows.sort(key=lambda r: (r.get("slug") or "").lower())
    return rows


def _post_has_cross_language_translation_ids(p: Dict[str, Any]) -> bool:
    """translations に「自分以外の投稿 ID」が載っているときだけ True（空オブジェクト等で誤検出しない）。"""
    if not isinstance(p, dict):
        return False
    pid = _post_id(p)
    m = extract_translation_id_map(p)
    if not m or pid is None:
        return False
    try:
        self_id = int(pid)
    except (TypeError, ValueError):
        return False
    for _k, oid in m.items():
        try:
            if int(oid) != self_id:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _should_pair_by_translations(posts_ja: List[Dict[str, Any]], posts_en: List[Dict[str, Any]]) -> bool:
    for p in (posts_ja or [])[:20]:
        if isinstance(p, dict) and _post_has_cross_language_translation_ids(p):
            return True
    for p in (posts_en or [])[:20]:
        if isinstance(p, dict) and _post_has_cross_language_translation_ids(p):
            return True
    return False


def build_paired_entries(
    posts_ja: List[Dict[str, Any]],
    posts_en: List[Dict[str, Any]],
    *,
    ja_posts_api_url: str = "",
    en_posts_api_url: str = "",
    translation_keys_en_from_ja: Optional[Tuple[str, ...]] = None,
    translation_keys_ja_from_en: Optional[Tuple[str, ...]] = None,
    force_pair_mode: str = "auto",
    append_fetch_lang_to_link: bool = False,
) -> List[Dict[str, str]]:
    """
    既定: REST に translations（Polylang 等）があれば投稿 ID で日英を1行にまとめる。
    無ければ slug 一致で従来どおり突き合わせ。
    force_pair_mode: "auto" | "slug" | "translations"
    append_fetch_lang_to_link: True のときだけ、取得元 posts URL の lang= を link にマージ（既定は False。REST の link を信頼する）。
    """
    keys_en = translation_keys_en_from_ja or ("en", "EN")
    keys_ja = translation_keys_ja_from_en or ("ja", "jp", "JP", "japanese")
    mode = (force_pair_mode or "auto").strip().lower()
    use_trans = mode == "translations" or (mode == "auto" and _should_pair_by_translations(posts_ja, posts_en))
    if use_trans and (posts_ja or posts_en):
        rows_t = _pair_posts_by_translations(
            posts_ja,
            posts_en,
            ja_posts_api_url=ja_posts_api_url,
            en_posts_api_url=en_posts_api_url,
            keys_en_from_ja=keys_en,
            keys_ja_from_en=keys_ja,
            append_fetch_lang_to_link=append_fetch_lang_to_link,
        )
        if mode == "auto" and posts_ja and posts_en:
            n_ue = sum(1 for r in rows_t if isinstance(r, dict) and (r.get("url_en") or "").strip())
            if n_ue == 0:
                return _pair_posts_by_slug(
                    posts_ja,
                    posts_en,
                    ja_posts_api_url=ja_posts_api_url,
                    en_posts_api_url=en_posts_api_url,
                    append_fetch_lang_to_link=append_fetch_lang_to_link,
                )
        return rows_t
    return _pair_posts_by_slug(
        posts_ja,
        posts_en,
        ja_posts_api_url=ja_posts_api_url,
        en_posts_api_url=en_posts_api_url,
        append_fetch_lang_to_link=append_fetch_lang_to_link,
    )


def collect_paired_from_sources(
    sources: List[Dict[str, Any]],
    *,
    timeout: float = 30.0,
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """
    sources: [{"ja": "https://.../wp/v2/posts", "en": "https://.../wp/v2/posts"}, ...]
    戻り値: (merged_rows, error_message)
    """
    if not sources:
        return [], None
    merged: List[Dict[str, str]] = []
    errors: List[str] = []
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        ja_u = (src.get("ja") or src.get("jp") or "").strip()
        en_u = (src.get("en") or "").strip()
        if not ja_u and not en_u:
            continue
        posts_ja = fetch_posts_for_source(ja_u, timeout=timeout) if ja_u else []
        posts_en = fetch_posts_for_source(en_u, timeout=timeout) if en_u else []

        def _tuple_from_src(key: str, default: Tuple[str, ...]) -> Tuple[str, ...]:
            raw = src.get(key) if isinstance(src, dict) else None
            if isinstance(raw, list) and raw:
                return tuple(str(x).strip() for x in raw if str(x).strip())
            if isinstance(raw, str) and raw.strip():
                return tuple(x.strip() for x in raw.split(",") if x.strip())
            return default

        if bool(src.get("filter_posts_by_rest_lang", False)):
            accept_ja = _tuple_from_src("rest_lang_accept_ja", ("ja", "jp", "japanese"))
            accept_en = _tuple_from_src("rest_lang_accept_en", ("en", "english"))
            posts_ja = filter_posts_by_rest_lang(posts_ja, accept_ja)
            posts_en = filter_posts_by_rest_lang(posts_en, accept_en)

        keys_en = _tuple_from_src("translation_keys_en_from_ja", ("en", "EN"))
        keys_ja = _tuple_from_src("translation_keys_ja_from_en", ("ja", "jp", "JP"))
        pair_mode = str(src.get("pair_mode") or "auto").strip()
        append_lang = bool(src.get("append_fetch_lang_to_link", False))

        paired = build_paired_entries(
            posts_ja,
            posts_en,
            ja_posts_api_url=ja_u,
            en_posts_api_url=en_u,
            translation_keys_en_from_ja=keys_en,
            translation_keys_ja_from_en=keys_ja,
            force_pair_mode=pair_mode,
            append_fetch_lang_to_link=append_lang,
        )
        normalize_paired_row_urls_for_single_language(paired)
        if not paired and (ja_u or en_u):
            errors.append(f"ソース{i + 1}: 記事を取得できませんでした")
        merged.extend(paired)
    return merged, ("; ".join(errors) if errors else None)
