# -*- coding: utf-8 -*-
"""
WordPress REST API から記事一覧を取得し、JA/EN を slug で突き合わせたリンク候補を作る。
"""
from __future__ import annotations

import json
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
    .../wp/v2/posts のベース URL（クエリなし）を想定し、全ページ取得。
    """
    base = _normalize_rest_base(rest_posts_url)
    if not base:
        return []
    out: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        q = urllib.parse.urlencode({"page": str(page), "per_page": str(per_page)})
        url = f"{base}?{q}"
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


def build_paired_entries(
    posts_ja: List[Dict[str, Any]],
    posts_en: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    slug が一致する JA/EN を1行にまとめる。片方だけの slug も行として出す。
    """
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
        rows.append(
            {
                "slug": slug,
                "title_jp": _post_title(ja) if ja else "",
                "title_en": _post_title(en) if en else "",
                "url_jp": _post_link(ja) if ja else "",
                "url_en": _post_link(en) if en else "",
            }
        )
    return rows


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
        paired = build_paired_entries(posts_ja, posts_en)
        if not paired and (ja_u or en_u):
            errors.append(f"ソース{i + 1}: 記事を取得できませんでした")
        merged.extend(paired)
    return merged, ("; ".join(errors) if errors else None)
