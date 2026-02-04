# -*- coding: utf-8 -*-
"""
ブログ出力レイヤー: ピンデータの ID をマスタから表示名に解決し、ブログ用にエクスポートする。
"""
import os
import json
import csv


def _load_config(game_path):
    path = os.path.join(game_path, "config.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_pins_csv(game_path, save_file="master_data.csv"):
    path = os.path.join(game_path, save_file)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["x"] = float(row["x"])
                row["y"] = float(row["y"])
            except (ValueError, KeyError):
                continue
            rows.append(dict(row))
    return rows


def resolve_pin_for_display(pin, config):
    """
    1本のピンを、マスタから表示名を解決した「ブログ用」の辞書に変換する。
    pin: CSV 1行相当の辞書（uid, x, y, attribute, obj_attributes, categories, ...）
    config: config.json の内容
    戻り値: id, coords, obj_id, obj_jp, obj_en, obj_props, contents[], importance, memo_jp, memo_en, updated_at
    """
    attr_mapping = config.get("attr_mapping", {})
    category_master = config.get("category_master", {})
    item_master = config.get("item_master", {})

    # cat_id → 表示名
    cat_id_to_jp = {}
    cat_id_to_en = {}
    for name_jp, info in category_master.items():
        if isinstance(info, dict) and info.get("id"):
            cat_id_to_jp[info["id"]] = name_jp
            cat_id_to_en[info["id"]] = info.get("name_en", name_jp)

    obj_id = pin.get("attribute") or pin.get("category_pin") or ""
    obj_info = attr_mapping.get(obj_id, {})
    if isinstance(obj_info, dict):
        obj_jp = obj_info.get("name_jp", obj_id)
        obj_en = (pin.get("obj_name_en") or "").strip() or obj_info.get("name_en", "")
    else:
        obj_jp = obj_id
        obj_en = (pin.get("obj_name_en") or "").strip() or ""

    obj_props = {}
    raw = pin.get("obj_attributes", "")
    if raw:
        try:
            obj_props = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            pass

    contents = []
    raw_cat = pin.get("categories", "")
    if raw_cat:
        try:
            cat_list = json.loads(raw_cat)
        except (TypeError, json.JSONDecodeError):
            cat_list = []
        for slot in cat_list:
            cat_id = slot.get("cat_id", "")
            category = slot.get("category", "")
            cat_jp = cat_id_to_jp.get(cat_id) or category
            # ピン側の分類(EN)上書きがあれば優先、なければマスタから解決
            cat_en = (slot.get("cat_name_en") or "").strip() or cat_id_to_en.get(cat_id) or ""
            item_id = slot.get("item_id", "")
            item_jp = slot.get("item_name_jp", "")
            # ピン側のアイテム(EN)上書きがあればそのまま、なければマスタから解決
            item_en = (slot.get("item_name_en") or "").strip()
            if item_id and category in item_master and item_id in item_master.get(category, {}):
                item_jp = item_master[category][item_id].get("name_jp", item_jp)
                if not item_en:
                    item_en = item_master[category][item_id].get("name_en", "")
            contents.append({
                "cat_id": cat_id,
                "cat_jp": cat_jp,
                "cat_en": cat_en,
                "item_id": item_id or None,
                "item_jp": item_jp or None,
                "item_en": item_en or None,
                "qty": slot.get("qty", "1"),
                "props": slot.get("attributes", {})
            })

    return {
        "id": pin.get("uid", ""),
        "coords": [pin.get("x", 0), pin.get("y", 0)],
        "obj_id": obj_id,
        "obj_jp": obj_jp,
        "obj_en": obj_en,
        "obj_props": obj_props,
        "contents": contents,
        "importance": pin.get("importance", ""),
        "memo_jp": pin.get("memo_jp", ""),
        "memo_en": pin.get("memo_en", ""),
        "updated_at": pin.get("updated_at", "")
    }


def export_pins_to_json(game_path, output_filename="pins_export.json"):
    """
    game_path の CSV と config を読み、全ピンを表示名解決して JSON に書き出す。
    戻り値: (出力ファイルの絶対パス, ピン数) または (None, 0) で失敗。
    """
    config = _load_config(game_path)
    save_file = config.get("save_file", "master_data.csv")
    pins = _load_pins_csv(game_path, save_file)
    if not pins:
        return None, 0
    resolved = [resolve_pin_for_display(p, config) for p in pins]
    out_path = os.path.join(game_path, output_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"pins": resolved}, f, indent=2, ensure_ascii=False)
    return out_path, len(resolved)
