# -*- coding: utf-8 -*-
"""
category_master[*].special_notes から map.js / pin_site_preview 用の
category_special_rules を生成する（単一の正とする）。
"""
from __future__ import annotations

from typing import Any, Dict, List


def _note_to_rule_for_map(note: Dict[str, Any]) -> Dict[str, Any]:
    """map.js specialRuleText / pin_site_preview.special_rule_text と整合する 1 ルール。"""
    if not isinstance(note, dict):
        return {}
    def _def_on() -> bool:
        return bool(note.get("default_enabled", True))

    kind = (note.get("kind") or "memo").strip()
    if kind == "memo":
        return {
            "note_type": "メモ",
            "memo_jp": (note.get("memo_jp") or "").strip(),
            "memo_en": (note.get("memo_en") or "").strip(),
            "default_enabled": _def_on(),
        }
    applicability = "lenient" if kind == "required_lenient" else "always"
    if kind == "recommended":
        note_type = "推奨条件"
    else:
        note_type = "必要条件"
    dk = (note.get("detail_kind") or "level").strip()
    base: Dict[str, Any] = {
        "note_type": note_type,
        "applicability": applicability,
        "default_enabled": _def_on(),
    }
    if dk == "skill_level":
        base["req_type"] = "スキルレベル"
        base["skill_id"] = (note.get("skill_id") or "").strip()
        lv = note.get("skill_level_value", note.get("skill_level", ""))
        base["skill_level"] = str(lv).strip() if lv is not None else ""
        return base
    if dk == "equipment":
        base["req_type"] = "装備"
        base["item_name"] = (note.get("equipment_name") or "").strip()
        return base
    if dk == "skill":
        base["req_type"] = "スキル"
        base["skill_id"] = (note.get("skill_id") or "").strip()
        return base
    base["level"] = str(note.get("level", "")).strip()
    return base


def sync_category_special_rules_from_master(config: Dict[str, Any]) -> None:
    """config を書き換え: category_special_rules を category_master から再構築。"""
    if not isinstance(config, dict):
        return
    cm = config.get("category_master")
    if not isinstance(cm, dict):
        config["category_special_rules"] = {}
        return
    out: Dict[str, Any] = {}
    for cat_jp, info in cm.items():
        if not isinstance(info, dict):
            continue
        raw = info.get("special_notes")
        if not isinstance(raw, list) or not raw:
            continue
        rules: List[Dict[str, Any]] = []
        for n in raw:
            r = _note_to_rule_for_map(n if isinstance(n, dict) else {})
            if r:
                rules.append(r)
        if not rules:
            continue
        block = {"rules": rules}
        out[str(cat_jp).strip()] = block
        cid = (info.get("id") or "").strip()
        if cid:
            out[cid] = block
    config["category_special_rules"] = out


def skill_name_master_to_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    """skill_name_master が list でも dict でも id→{name_jp,name_en} に統一。"""
    if not isinstance(config, dict):
        return {}
    raw = config.get("skill_name_master")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, list):
        return {}
    out: Dict[str, Any] = {}
    for it in raw:
        if not isinstance(it, dict):
            continue
        sid = (it.get("id") or "").strip()
        if not sid:
            continue
        out[sid] = {"name_jp": it.get("name_jp", ""), "name_en": it.get("name_en", "")}
    return out
