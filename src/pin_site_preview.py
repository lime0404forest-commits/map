# -*- coding: utf-8 -*-
"""
埋め込み map.js（vein/world map 系）のピン表示テキスト・ポップアップ HTML 生成を
エディタ側で再現する。ロジックは games/vein/world map/map.js を参照。
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def escape_html_pin(s: Any) -> str:
    return (
        _s(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def memo_to_safe_popup_html(memo: Any) -> str:
    return re.sub(r"<script[\s\S]*?</script>", "", _s(memo), flags=re.IGNORECASE)


def plain_memo_for_tooltip(memo: Any) -> str:
    return re.sub(r"<br\s*/?>", "\n", _s(memo), flags=re.IGNORECASE).strip()


def _truthy_attr(val: Any) -> bool:
    if val is True:
        return True
    t = _s(val).strip().lower()
    return t == "true" or t == "1"


def truthy_slot_attr(val: Any) -> bool:
    """CSV/JSON の真偽（文字列含む）を map.js 相当で解釈。"""
    return _truthy_attr(val)


def category_label_from_entry(c: Optional[Dict], is_ja: bool) -> str:
    if not c:
        return ""
    if is_ja:
        v = c.get("cat_jp") or c.get("category") or c.get("cat_en") or c.get("cat_name_en")
    else:
        v = c.get("cat_en") or c.get("cat_name_en") or c.get("category") or c.get("cat_jp")
    return _s(v).strip()


def item_name_from_entry(c: Optional[Dict], is_ja: bool) -> str:
    if not c:
        return ""
    if is_ja:
        v = c.get("item_name_jp") or c.get("item_jp") or c.get("item_name_en") or c.get("item_en")
    else:
        v = c.get("item_name_en") or c.get("item_en") or c.get("item_name_jp") or c.get("item_jp")
    return _s(v).strip()


def lockpick_req_suffix(c: Optional[Dict], is_ja: bool) -> str:
    if not c:
        return ""
    a = c.get("attributes")
    if not isinstance(a, dict):
        return ""
    has25 = _truthy_attr(a.get("req_lockpick_lv25"))
    has75 = _truthy_attr(a.get("req_lockpick_lv75"))
    if not has25 and not has75:
        return ""
    lv = []
    if has25:
        lv.append("25")
    if has75:
        lv.append("75")
    if is_ja:
        return "（要ロックピック Lv." + "/Lv.".join(lv) + "）"
    return " (Req. Lv." + "/Lv.".join(lv) + ")"


def item_qty_string_for_entry(c: Optional[Dict]) -> str:
    """item_select は item_qty があれば優先、無ければ qty。qty_only は qty。アイテムありで空なら 1。"""
    if not c:
        return ""
    iid = _s(c.get("item_id")).strip()
    if iid:
        iq = c.get("item_qty")
        if iq is not None and _s(iq).strip() != "":
            return _s(iq).strip()
        q = c.get("qty")
        if q is not None and _s(q).strip() != "":
            return _s(q).strip()
        return "1"
    q2 = c.get("qty")
    return _s(q2).strip() if q2 is not None and _s(q2).strip() != "" else ""


def item_qty_for_hover(c: Optional[Dict]) -> str:
    return item_qty_string_for_entry(c)


def _qty_numeric_equals_one(s: str) -> bool:
    """数量文字列が数値 1（全角数字・小数可）か。"""
    if not s or not str(s).strip():
        return False
    t = str(s).strip()
    trans = str.maketrans("０１２３４５６７８９", "0123456789")
    t = t.translate(trans)
    try:
        return float(t) == 1.0
    except ValueError:
        return False


def _is_many_qty_token(v) -> bool:
    s = _s(v).strip().lower()
    return s in ("many", "多数")


def hover_qty_suffix(qty_str: str, is_ja: bool) -> str:
    """ホバー・クリックポップアップ用: 1は非表示、2以上は×数、多数トークンは「多数/Many」。"""
    if qty_str is None or not str(qty_str).strip():
        return ""
    s = str(qty_str).strip()
    if _is_many_qty_token(s):
        return " 多数" if is_ja else " (Many)"
    if _qty_numeric_equals_one(s):
        return ""
    return f" ×{s}"


def category_labels_from_contents(contents: List[Dict], is_ja: bool, legacy_category: str) -> List[str]:
    labels: List[str] = []
    for c in contents or []:
        if not c:
            continue
        if is_ja:
            lab = _s(c.get("cat_jp") or c.get("category")).strip()
        else:
            lab = _s(c.get("cat_en") or c.get("cat_name_en") or c.get("category")).strip()
        if lab and lab not in labels:
            labels.append(lab)
    if not labels and legacy_category.strip():
        labels.append(legacy_category.strip())
    return labels


def build_pin_headline(pin: Dict, is_ja: bool, contents: List[Dict], legacy_category: str) -> str:
    name_part = _s(
        pin.get("name_jp" if is_ja else "name_en") or pin.get("name_en" if is_ja else "name_jp")
    ).strip()
    obj_part = (
        _s(pin.get("obj_jp" if is_ja else "obj_en") or pin.get("obj_en" if is_ja else "obj_jp")).strip()
    )
    if obj_part and name_part:
        return f"{obj_part}：{name_part}"
    if obj_part:
        return obj_part
    cats = category_labels_from_contents(contents, is_ja, legacy_category or "")
    cat_part = "・".join(cats)
    if cat_part:
        return cat_part
    return "（無題）" if is_ja else "(Untitled)"


def build_pin_description(pin: Dict, is_ja: bool) -> str:
    if is_ja:
        return _s(pin.get("memo_jp")).strip()
    return _s(pin.get("memo_en") or pin.get("memo_jp")).strip()


def normalize_parent_relation_type(raw_type: Any, has_parent: bool) -> str:
    t = _s(raw_type).strip().lower()
    if t in ("in the area", "in-the-area", "in_the_area", "area", "inside_area", "inside-area"):
        t = "in_area"
    if t not in ("inside", "near", "in_area"):
        t = "inside" if has_parent else ""
    return t


def parent_relation_type_label(type_value: str, is_ja: bool) -> str:
    t = normalize_parent_relation_type(type_value, True)
    if is_ja:
        if t == "near":
            return "近く"
        if t == "in_area":
            return "エリア内"
        return "中"
    if t == "near":
        return "near"
    if t == "in_area":
        return "in the area"
    return "inside"


def child_pin_in_parent_text(pin: Dict, is_ja: bool) -> str:
    puid = _s(pin.get("parent_uid")).strip()
    if not puid:
        return ""
    p_name = _s(pin.get("parent_name_jp" if is_ja else "parent_name_en")).strip()
    if not p_name:
        p_name = _s(pin.get("parent_name_en" if is_ja else "parent_name_jp")).strip()
    if not p_name:
        p_name = _s(pin.get("parent_obj_jp" if is_ja else "parent_obj_en")).strip()
    if not p_name:
        p_name = _s(pin.get("parent_obj_en" if is_ja else "parent_obj_jp")).strip()
    if not p_name:
        return ""
    rel = parent_relation_type_label(_s(pin.get("parent_type")).strip(), is_ja)
    if is_ja:
        return f"{p_name}の{rel}"
    rel_type = normalize_parent_relation_type(_s(pin.get("parent_type")).strip(), True)
    if rel_type == "near":
        return f"Near {p_name}"
    if rel_type == "in_area":
        return f"Within {p_name}"
    return f"Inside {p_name}"


def skill_display_name_for_rule(skill_id: str, is_ja: bool, skill_name_master: Dict) -> str:
    sid = skill_id.strip()
    if not sid:
        return ""
    inf = skill_name_master.get(sid) if isinstance(skill_name_master, dict) else None
    if not isinstance(inf, dict):
        return sid
    jp = _s(inf.get("name_jp")).strip()
    en = _s(inf.get("name_en")).strip()
    if is_ja:
        return jp or en or sid
    return en or jp or sid


def special_rule_text(rule: Dict, is_ja: bool, skill_name_master: Dict) -> str:
    if not isinstance(rule, dict):
        return ""
    nt = _s(rule.get("note_type")).strip()
    rt = _s(rule.get("req_type")).strip()
    app = _s(rule.get("applicability") or "always").strip()
    nt_disp = nt if is_ja else ({"必要条件": "Required", "推奨条件": "Recommended", "メモ": "Memo"}.get(nt, nt))
    # JP の「必要条件(緩め)」は "必要条件（必要な場合がある）" を避ける
    if is_ja and nt == "必要条件" and app == "lenient":
        nt_disp = "必要な場合がある"
    # EN の「必要条件(緩め)」は "Required (May require)" を避ける
    if (not is_ja) and nt == "必要条件" and app == "lenient":
        nt_disp = "May require"
    if app == "sometimes":
        maybe_tag = "（場合あり）" if is_ja else " (Sometimes)"
    elif app == "lenient":
        maybe_tag = "（必要な場合がある）" if is_ja else " (May require)"
    else:
        maybe_tag = ""
    if is_ja and nt == "必要条件" and app == "lenient":
        maybe_tag = ""
    if (not is_ja) and nt == "必要条件" and app == "lenient":
        maybe_tag = ""
    if nt == "メモ":
        mjp = _s(rule.get("memo_jp")).strip()
        men = _s(rule.get("memo_en")).strip()
        leg = _s(rule.get("memo")).strip()
        if is_ja:
            t = mjp or leg
            return f"メモ: {t}" if t else ""
        t2 = men or leg or mjp
        return f"Memo: {t2}" if t2 else ""
    if rt == "装備":
        legacy = _s(rule.get("item_name")).strip()
        j = _s(rule.get("item_name_jp")).strip()
        e = _s(rule.get("item_name_en")).strip()
        if not j and legacy:
            j = legacy
        if not e and legacy:
            e = legacy
        iname = (j or e) if is_ja else (e or j)
        icnt = _s(rule.get("item_count")).strip()
        if not iname:
            return ""
        if icnt and not _qty_numeric_equals_one(icnt):
            body = f"{iname} ×{icnt}"
        else:
            body = iname
        return f"{nt_disp}{maybe_tag}: {body}"
    if rt == "スキルレベル":
        sid2 = _s(rule.get("skill_id")).strip()
        slv = _s(rule.get("skill_level")).strip()
        if not sid2 or not slv:
            return ""
        nm2 = skill_display_name_for_rule(sid2, is_ja, skill_name_master)
        return f"{nt_disp}{maybe_tag}: {nm2} Lv.{slv}"
    if rt == "スキル":
        sid3 = _s(rule.get("skill_id")).strip()
        if not sid3:
            return ""
        nm3 = skill_display_name_for_rule(sid3, is_ja, skill_name_master)
        if is_ja:
            return f"{nt_disp}{maybe_tag}: スキル {nm3}"
        return f"{nt_disp}{maybe_tag}: Skill {nm3}"
    lv = _s(rule.get("level")).strip()
    if not lv:
        return ""
    return f"{nt_disp}{maybe_tag}: Lv.{lv}"


def category_special_rules_for_entry(
    c: Optional[Dict], category_special_rules: Optional[Dict]
) -> List[Dict]:
    if not c or not isinstance(category_special_rules, dict):
        return []
    cid = _s(c.get("cat_id")).strip()
    cjp = _s(c.get("category") or c.get("cat_jp")).strip()
    v = None
    if cid and isinstance(category_special_rules.get(cid), dict):
        v = category_special_rules[cid]
    if v is None and cjp and isinstance(category_special_rules.get(cjp), dict):
        v = category_special_rules[cjp]
    if not v or not isinstance(v.get("rules"), list):
        return []
    return v["rules"]


def special_fragments_for_entry(
    c: Optional[Dict],
    is_ja: bool,
    category_special_rules: Optional[Dict],
    skill_name_master: Dict,
) -> List[str]:
    rules = category_special_rules_for_entry(c, category_special_rules)
    if not rules:
        return []
    attrs = c.get("attributes") if isinstance(c, dict) and isinstance(c.get("attributes"), dict) else {}
    parts: List[str] = []
    for idx, r in enumerate(rules):
        if not isinstance(r, dict):
            continue
        k = f"special_rule_enabled_{idx + 1}"
        if not _truthy_attr(attrs.get(k)):
            continue
        t = special_rule_text(r, is_ja, skill_name_master)
        if t:
            parts.append(t)
    return parts


def pin_has_category_with_special_rules_master(
    contents_arr: List[Dict], category_special_rules: Optional[Dict]
) -> bool:
    for c in contents_arr or []:
        if category_special_rules_for_entry(c, category_special_rules):
            return True
    return False


def aggregate_special_fragments_for_pin(
    contents_arr: List[Dict],
    is_ja: bool,
    category_special_rules: Optional[Dict],
    skill_name_master: Dict,
) -> List[str]:
    seen: Dict[str, bool] = {}
    order: List[str] = []
    for c in contents_arr or []:
        for t in special_fragments_for_entry(c, is_ja, category_special_rules, skill_name_master):
            key = t.strip()
            if not key or seen.get(key):
                continue
            seen[key] = True
            order.append(t)
    return order


def aggregate_special_html_for_pin(
    contents_arr: List[Dict],
    is_ja: bool,
    category_special_rules: Optional[Dict],
    skill_name_master: Dict,
) -> str:
    fr = aggregate_special_fragments_for_pin(
        contents_arr, is_ja, category_special_rules, skill_name_master
    )
    lab = "特記" if is_ja else "Notes"
    if fr:
        inner = "".join(
            f'<div style="margin-top:3px;">・{escape_html_pin(t)}</div>' for t in fr
        )
        return (
            f'<div style="font-size:12px;color:#333;margin-top:10px;line-height:1.45;">'
            f'<div style="font-weight:bold;">{lab}</div>{inner}</div>'
        )
    if pin_has_category_with_special_rules_master(contents_arr, category_special_rules):
        none = ": （なし）" if is_ja else ": (None)"
        return (
            f'<div style="font-size:12px;color:#333;margin-top:10px;">'
            f'<span style="font-weight:bold;">{lab}</span>{none}</div>'
        )
    return ""


def format_all_contents_for_popup_html(contents_arr: List[Dict], is_ja: bool) -> str:
    if not contents_arr:
        return ""
    parts: List[str] = []
    for c in contents_arr:
        if not c:
            continue
        cat_lab = category_label_from_entry(c, is_ja)
        item_name = item_name_from_entry(c, is_ja)
        qty_str = item_qty_string_for_entry(c)
        req_suffix = lockpick_req_suffix(c, is_ja)
        head = ""
        if item_name:
            head = f"{cat_lab}：{item_name}" if cat_lab else item_name
            # ホバーと同様: 数量が 1 のときは × を付けない
            head += hover_qty_suffix(qty_str, is_ja)
            head += req_suffix
        elif cat_lab:
            head = cat_lab
            head += hover_qty_suffix(qty_str, is_ja)
            head += req_suffix
        else:
            continue
        parts.append(
            '<div style="font-size:13px;font-weight:bold;color:#222;margin-bottom:4px;line-height:1.35;">'
            f"【{escape_html_pin(head)}】</div>"
        )
    return "".join(parts)


def build_hover_tooltip_text(
    pin: Dict, is_ja: bool, contents: List[Dict], legacy_category: str
) -> str:
    place_name = _s(
        pin.get("name_jp" if is_ja else "name_en") or pin.get("name_en" if is_ja else "name_jp")
    ).strip()
    if place_name:
        return place_name
    obj_name = (
        _s(pin.get("obj_jp" if is_ja else "obj_en") or pin.get("obj_en" if is_ja else "obj_jp")).strip()
    )
    rows: List[str] = []
    for c in contents or []:
        if not c:
            continue
        item_name = item_name_from_entry(c, is_ja)
        cat = category_label_from_entry(c, is_ja)
        qty = item_qty_string_for_entry(c)
        req = lockpick_req_suffix(c, is_ja)
        suffix = hover_qty_suffix(qty, is_ja) + req
        if item_name:
            rows.append(item_name + suffix)
        elif cat:
            rows.append(cat + suffix)
    if rows:
        return "\n".join(rows)
    if obj_name:
        return obj_name
    return "（無題）" if is_ja else "(Untitled)"


def tooltip_text_as_on_map(
    pin: Dict,
    is_ja: bool,
    headline: str,
    filter_mode: bool = False,
    filter_tooltip_text: str = "",
) -> str:
    if filter_mode and _s(filter_tooltip_text).strip():
        return _s(filter_tooltip_text).strip()
    ht = _s(pin.get("hover_tooltip")).strip()
    if ht:
        return ht
    if headline:
        return headline
    return "—"


def build_popup_html(
    pin: Dict,
    is_ja: bool,
    category_special_rules: Optional[Dict],
    skill_name_master: Dict,
) -> str:
    headline = build_pin_headline(pin, is_ja, pin.get("contents") or [], pin.get("category") or "")
    description = build_pin_description(pin, is_ja)
    desc_html = memo_to_safe_popup_html(description)
    detail_html = format_all_contents_for_popup_html(pin.get("contents") or [], is_ja)
    parent_ctx = child_pin_in_parent_text(pin, is_ja)
    special_html = aggregate_special_html_for_pin(
        pin.get("contents") or [], is_ja, category_special_rules, skill_name_master
    )
    mid_html = ""
    if detail_html:
        mid_html += f'<div style="font-size:12px;color:#333;">{detail_html}</div>'
    if special_html:
        mid_html += special_html
    popup_html = (
        '<div style="font-family:sans-serif;min-width:200px;line-height:1.4;">'
        f'<div style="font-size:14px;font-weight:bold;">{escape_html_pin(headline)}</div>'
    )
    if parent_ctx:
        popup_html += f'<div style="font-size:12px;color:#6b6b6b;margin-top:3px;">{escape_html_pin(parent_ctx)}</div>'
    popup_html += '<div style="margin:6px 0 8px;border-top:1px solid #bbb;"></div>'
    if mid_html:
        popup_html += mid_html
    if desc_html:
        popup_html += (
            '<div style="margin:6px 0 6px;border-top:1px solid #bbb;"></div>'
            f'<div style="font-size:12px;color:#333;white-space:normal;">{desc_html}</div>'
        )
    popup_html += "</div>"
    return popup_html


def popup_html_to_plain_text(html_str: str) -> str:
    """ブラウザなし用: タグを除き、改行をある程度保持。"""
    s = re.sub(r"(?i)<script[\s\S]*?</script>", "", html_str)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"</div>\s*", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).strip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def normalize_resolved_content_for_map_js(c: Dict) -> Dict:
    """resolve_pin_for_display の 1 スロットを map.js の c と同じ参照キーに寄せる。"""
    out = dict(c)
    props = out.pop("props", None)
    if props is not None and "attributes" not in out:
        out["attributes"] = props if isinstance(props, dict) else {}
    elif "attributes" not in out:
        out["attributes"] = {}
    if out.get("cat_jp") and not out.get("category"):
        out["category"] = out["cat_jp"]
    return out


def build_preview_bundle(
    resolved_pin: Dict,
    csv_row: Dict,
    config: Dict,
    filter_mode: bool = False,
    filter_tooltip_text: str = "",
) -> Dict[str, str]:
    """
    戻り値: hover_tooltip_jp/en, popup_plain_jp/en（サイト相当テキスト）
    """
    from . import category_special_rules_builder as _csrb

    cfg = dict(config) if isinstance(config, dict) else {}
    _csrb.sync_category_special_rules_from_master(cfg)
    csr = cfg.get("category_special_rules") if isinstance(cfg.get("category_special_rules"), dict) else None
    snm = _csrb.skill_name_master_to_dict(cfg)

    contents = [
        normalize_resolved_content_for_map_js(dict(x))
        for x in (resolved_pin.get("contents") or [])
    ]
    pin = {
        "obj_jp": resolved_pin.get("obj_jp", ""),
        "obj_en": resolved_pin.get("obj_en", ""),
        "memo_jp": _s(csv_row.get("memo_jp")),
        "memo_en": _s(csv_row.get("memo_en")),
        "category": _s(csv_row.get("category")),
        "contents": contents,
        "parent_uid": _s(resolved_pin.get("parent_uid") or csv_row.get("parent_uid")).strip(),
        "parent_type": _s(csv_row.get("parent_type")).strip(),
        "parent_name_jp": _s(csv_row.get("parent_name_jp")).strip(),
        "parent_name_en": _s(csv_row.get("parent_name_en")).strip(),
        "parent_obj_jp": _s(csv_row.get("parent_obj_jp")).strip(),
        "parent_obj_en": _s(csv_row.get("parent_obj_en")).strip(),
    }

    out: Dict[str, str] = {}
    for is_ja, suf in ((True, "jp"), (False, "en")):
        pin["hover_tooltip"] = build_hover_tooltip_text(
            pin, is_ja, contents, pin["category"]
        )
        headline = build_pin_headline(pin, is_ja, contents, pin["category"])
        out[f"hover_tooltip_{suf}"] = tooltip_text_as_on_map(
            pin, is_ja, headline, filter_mode, filter_tooltip_text
        )
        html_popup = build_popup_html(pin, is_ja, csr, snm)
        out[f"popup_plain_{suf}"] = popup_html_to_plain_text(html_popup)
    return out
