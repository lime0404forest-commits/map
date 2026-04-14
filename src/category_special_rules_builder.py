# -*- coding: utf-8 -*-
"""
category_master[*].special_notes から map.js / pin_site_preview 用の
category_special_rules を生成する（単一の正とする）。

装備（detail_kind equipment）ルールは item_name_jp / item_name_en を出力し、
旧データ互換のため item_name（JP 優先）も付与する。
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
        legacy = (note.get("equipment_name") or "").strip()
        j = (note.get("equipment_name_jp") or legacy or "").strip()
        e = (note.get("equipment_name_en") or "").strip()
        base["item_name_jp"] = j
        base["item_name_en"] = e
        base["item_name"] = j or e
        return base
    if dk == "skill":
        base["req_type"] = "スキル"
        base["skill_id"] = (note.get("skill_id") or "").strip()
        return base
    base["level"] = str(note.get("level", "")).strip()
    return base


def _legacy_rule_to_special_note(rule: Dict[str, Any]) -> Dict[str, Any]:
    """旧 category_special_rules の 1ルールを category_master.special_notes 形式へ変換。"""
    if not isinstance(rule, dict):
        return {}
    note_type = str(rule.get("note_type") or "").strip()
    req_type = str(rule.get("req_type") or "").strip()
    applicability = str(rule.get("applicability") or "").strip()
    default_enabled = bool(rule.get("default_enabled", True))

    if note_type == "メモ":
        return {
            "kind": "memo",
            "memo_jp": str(rule.get("memo_jp") or rule.get("memo") or "").strip(),
            "memo_en": str(rule.get("memo_en") or "").strip(),
            "default_enabled": default_enabled,
        }

    if note_type == "推奨条件":
        kind = "recommended"
    elif applicability == "lenient":
        kind = "required_lenient"
    else:
        kind = "required"

    out: Dict[str, Any] = {
        "kind": kind,
        "default_enabled": default_enabled,
    }
    if req_type == "スキルレベル":
        out["detail_kind"] = "skill_level"
        out["skill_id"] = str(rule.get("skill_id") or "").strip()
        out["skill_level_value"] = str(rule.get("skill_level") or rule.get("level") or "").strip()
        return out
    if req_type == "スキル":
        out["detail_kind"] = "skill"
        out["skill_id"] = str(rule.get("skill_id") or "").strip()
        return out
    if req_type == "装備":
        out["detail_kind"] = "equipment"
        out["equipment_name_jp"] = str(rule.get("item_name_jp") or rule.get("item_name") or "").strip()
        out["equipment_name_en"] = str(rule.get("item_name_en") or "").strip()
        return out

    out["detail_kind"] = "level"
    out["level"] = str(rule.get("level") or rule.get("skill_level") or "").strip()
    return out


def ensure_special_notes_from_legacy_rules(config: Dict[str, Any]) -> None:
    """
    category_master.special_notes が空のカテゴリに対し、
    旧 category_special_rules を読み取って復元する。
    """
    if not isinstance(config, dict):
        return
    cm = config.get("category_master")
    csr = config.get("category_special_rules")
    if not isinstance(cm, dict) or not isinstance(csr, dict) or not csr:
        return

    id_to_cat: Dict[str, str] = {}
    for cat_jp, info in cm.items():
        if not isinstance(info, dict):
            continue
        cid = str(info.get("id") or "").strip()
        if cid:
            id_to_cat[cid] = str(cat_jp)

    for key, block in csr.items():
        if not isinstance(block, dict):
            continue
        rules = block.get("rules")
        if not isinstance(rules, list) or not rules:
            continue
        cat_jp = None
        if key in cm:
            cat_jp = str(key)
        elif key in id_to_cat:
            cat_jp = id_to_cat[key]
        if not cat_jp:
            continue
        info = cm.get(cat_jp)
        if not isinstance(info, dict):
            continue
        cur = info.get("special_notes")
        if isinstance(cur, list) and cur:
            continue
        notes: List[Dict[str, Any]] = []
        for r in rules:
            n = _legacy_rule_to_special_note(r if isinstance(r, dict) else {})
            if n:
                notes.append(n)
        if notes:
            info["special_notes"] = notes


def sync_category_special_rules_from_master(config: Dict[str, Any]) -> None:
    """config を書き換え: category_special_rules を category_master から再構築。"""
    if not isinstance(config, dict):
        return
    ensure_special_notes_from_legacy_rules(config)
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
