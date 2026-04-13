# -*- coding: utf-8 -*-
"""
attr_mapping / category_master に保存される「type」文字列のうち、色・下位カテゴリ欄の既定など
**挙動面**を config で分離するモジュール。

**中心設計（現行）**はオブジェクト・カテゴリ・アイテム・入力構造（input_type / show_qty / attributes）である。
**loot / landmark / colony / other** は初期版から続く **旧仕様の type id** であり、既存データの解釈・
フォールバック・エイリアス置換のために残している（レガシー互換レイヤ）。新規プロジェクトでは
object_type_ui_order の先頭に自前の type id を置く運用を推奨。

config.json（任意）:
  object_type_aliases: { "loot": "resource" }  # 旧保存値 → 新 id への挙動寄せ
  object_type_config: {
    "loot": { "default_pin_inner_color": "#2ecc71", "default_use_category_slots": true },
    "poi":  { "default_pin_inner_color": "#9e9e9e", "default_use_category_slots": true }
  }
  object_type_ui_order: ["facility", "poi", "loot", ...]  # 先頭は新規行の既定 type にも使われる
  object_type_display_names: { "poi": "POI" }      # コンボ表示名

未設定時は BUILTIN_*（＝上記旧4 type の既定値テーブル）で既存プロジェクトと互換。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# --- 旧仕様（v1）4分類: 既存 JSON の type 文字列・未知 type のマージ基底に使用。名称は歴史的互換のため固定。 ---
BUILTIN_OBJECT_TYPE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "loot": {
        "default_pin_inner_color": "#2ecc71",
        "default_use_category_slots": True,
    },
    "landmark": {
        "default_pin_inner_color": "#3498db",
        "default_use_category_slots": False,
    },
    "colony": {
        "default_pin_inner_color": "#e67e22",
        "default_use_category_slots": True,
    },
    "other": {
        "default_pin_inner_color": "#7f8c8d",
        "default_use_category_slots": True,
    },
}

BUILTIN_OBJECT_TYPE_ORDER: List[str] = ["loot", "landmark", "colony", "other"]

# ドキュメント・UI 用。BUILTIN_OBJECT_TYPE_ORDER と同一（旧4 type の集合）。
LEGACY_OBJECT_TYPE_ORDER: List[str] = BUILTIN_OBJECT_TYPE_ORDER
LEGACY_OBJECT_TYPE_IDS: frozenset[str] = frozenset(BUILTIN_OBJECT_TYPE_ORDER)

BUILTIN_OBJECT_TYPE_LABELS: Dict[str, str] = {
    "loot": "アイテムルート源",
    "landmark": "ランドマーク",
    "colony": "群生地",
    "other": "その他",
}


def _is_hex6(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()))


def _norm_type_id(t: Optional[str]) -> str:
    """空の type を旧互換 id「loot」に寄せる（既存データ・欠損時の挙動維持）。"""
    s = (t or "").strip()
    return s if s else "loot"


def default_type_id_for_new_rows(game_config: Optional[dict]) -> str:
    """
    マスタで「空行を追加」したときの既定 type。
    object_type_ui_order の先頭があればそれを使い（新運用で旧4を先頭にしない配置が可能）、
    無ければ従来どおり旧互換の「loot」。
    """
    cfg = game_config if isinstance(game_config, dict) else {}
    order = cfg.get("object_type_ui_order")
    if isinstance(order, list) and order:
        for x in order:
            s = str(x).strip()
            if s:
                return s
    return "loot"


def merge_object_type_settings(raw_type: Optional[str], game_config: Optional[dict]) -> Dict[str, Any]:
    """
    種類 raw_type に対する effective 設定を返す。
    object_type_aliases で別名に寄せたうえで、object_type_config で上書き。
    未知の type は旧4分類の「other」相当の基底に落とす（後方互換）。
    """
    cfg = game_config if isinstance(game_config, dict) else {}
    raw = _norm_type_id(raw_type)
    aliases = cfg.get("object_type_aliases")
    if not isinstance(aliases, dict):
        aliases = {}
    otc = cfg.get("object_type_config")
    if not isinstance(otc, dict):
        otc = {}

    resolved = aliases.get(raw, raw)

    # ベース: resolved が内蔵にあればそれ、なければ raw、なければ other
    base_key = resolved if resolved in BUILTIN_OBJECT_TYPE_DEFAULTS else raw
    if base_key not in BUILTIN_OBJECT_TYPE_DEFAULTS:
        base_key = "other"
    out = dict(BUILTIN_OBJECT_TYPE_DEFAULTS[base_key])

    # raw / resolved 双方の config 断片を上書き（resolved が後勝ち）
    frag_raw = otc.get(raw)
    if isinstance(frag_raw, dict):
        out.update(frag_raw)
    if resolved != raw:
        frag_res = otc.get(resolved)
        if isinstance(frag_res, dict):
            out.update(frag_res)

    col = out.get("default_pin_inner_color")
    if not _is_hex6(col):
        out["default_pin_inner_color"] = BUILTIN_OBJECT_TYPE_DEFAULTS["other"]["default_pin_inner_color"]
    ucat = out.get("default_use_category_slots")
    if not isinstance(ucat, bool):
        out["default_use_category_slots"] = bool(BUILTIN_OBJECT_TYPE_DEFAULTS["other"]["default_use_category_slots"])
    return out


def get_default_pin_inner_color(raw_type: Optional[str], game_config: Optional[dict]) -> str:
    return str(merge_object_type_settings(raw_type, game_config)["default_pin_inner_color"])


def get_default_use_category_slots(raw_type: Optional[str], game_config: Optional[dict]) -> bool:
    return bool(merge_object_type_settings(raw_type, game_config)["default_use_category_slots"])


def resolve_type_alias(raw_type: Optional[str], game_config: Optional[dict]) -> str:
    """カテゴリ紐づけ等で比較に使う「エイリアス解決後の type id」。"""
    cfg = game_config if isinstance(game_config, dict) else {}
    raw = _norm_type_id(raw_type)
    aliases = cfg.get("object_type_aliases")
    if not isinstance(aliases, dict):
        return raw
    return str(aliases.get(raw, raw))


def types_match_for_category_filter(
    object_type: Optional[str],
    category_type: Optional[str],
    game_config: Optional[dict],
) -> bool:
    """
    ピン編集のカテゴリコンボ: オブジェクト種類とカテゴリの対応種類が同じグループか。
    object_type_aliases 解決後の文字列同士を比較する。
    """
    o = resolve_type_alias(object_type, game_config)
    c = resolve_type_alias(category_type, game_config)
    return o == c


def _types_referenced_in_game_data(cfg: dict) -> set[str]:
    """attr_mapping / category_master にだけ存在する type もコンボ候補に含める（手編集 JSON 対策）。"""
    s: set[str] = set()
    am = cfg.get("attr_mapping")
    if isinstance(am, dict):
        for v in am.values():
            if isinstance(v, dict):
                t = str(v.get("type") or "").strip()
                if t:
                    s.add(t)
    cm = cfg.get("category_master")
    if isinstance(cm, dict):
        for v in cm.values():
            if isinstance(v, dict):
                t = str(v.get("type") or "").strip()
                if t:
                    s.add(t)
    return s


def object_type_ids_for_ui(game_config: Optional[dict]) -> List[str]:
    """
    マスタ管理の種類コンボに出す type id の列（重複なし）。
    参照元（マージして重複除去）:
      - object_type_ui_order（任意・並びの主軸）
      - object_type_config のキー
      - object_type_display_names のキー
      - attr_mapping / category_master で使われている type
      - 旧仕様4 type loot/landmark/colony/other（既存データ互換・候補の最終マージ）
    """
    cfg = game_config if isinstance(game_config, dict) else {}
    otc = cfg.get("object_type_config")
    if not isinstance(otc, dict):
        otc = {}
    otc_keys = [str(k).strip() for k in otc.keys() if isinstance(k, str) and str(k).strip()]

    odn = cfg.get("object_type_display_names")
    label_keys: List[str] = []
    if isinstance(odn, dict):
        label_keys = [str(k).strip() for k in odn.keys() if isinstance(k, str) and str(k).strip()]

    data_types = _types_referenced_in_game_data(cfg)

    order = cfg.get("object_type_ui_order")
    out: List[str] = []
    seen: set[str] = set()

    def append_missing(keys: List[str]) -> None:
        for k in keys:
            if k and k not in seen:
                seen.add(k)
                out.append(k)

    if isinstance(order, list) and order:
        append_missing([str(x).strip() for x in order if str(x).strip()])
        append_missing(sorted(set(otc_keys) - seen))
        append_missing(sorted(set(label_keys) - seen))
        append_missing(sorted(data_types - seen))
        append_missing([k for k in BUILTIN_OBJECT_TYPE_ORDER if k not in seen])
        return out

    append_missing(list(BUILTIN_OBJECT_TYPE_ORDER))
    append_missing(sorted(set(otc_keys) - seen))
    append_missing(sorted(set(label_keys) - seen))
    append_missing(sorted(data_types - seen))
    return out


def object_type_labels_for_ui(game_config: Optional[dict]) -> Dict[str, str]:
    """種類コンボの表示ラベル（未設定キーは id をそのまま表示用に返す際に呼び出し側でフォールバック）。"""
    cfg = game_config if isinstance(game_config, dict) else {}
    labels = dict(BUILTIN_OBJECT_TYPE_LABELS)
    custom = cfg.get("object_type_display_names")
    if isinstance(custom, dict):
        for k, v in custom.items():
            if k and isinstance(v, str) and v.strip():
                labels[str(k).strip()] = v.strip()
    return labels


def label_for_type(type_id: str, game_config: Optional[dict]) -> str:
    """表示ラベル。空 id は旧互換で loot 扱い。"""
    tid = (type_id or "").strip()
    if not tid:
        tid = "loot"
    lab = object_type_labels_for_ui(game_config).get(tid)
    if lab:
        return lab
    return tid
