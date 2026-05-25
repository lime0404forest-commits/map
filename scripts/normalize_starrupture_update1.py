#!/usr/bin/env python3
"""
Starrupture Update_1 データを「単一オブジェクト: LOOT_SOURCE」モデルへ正規化する。

- 対象: games/starrupture/Update_1/config.json, master_data.csv
- 安全策:
  - --dry-run: 変更内容のサマリだけ表示
  - --apply: 反映（反映前に .bak を作成）
"""

from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = ROOT / "games" / "starrupture" / "Update_1"
CONFIG_PATH = TARGET_DIR / "config.json"
CSV_PATH = TARGET_DIR / "master_data.csv"

LOOT_SOURCE_ID = "LOOT_SOURCE"

SOURCE_KIND_MAP = {
    "DEAD_BODY": {"id": "source_dead_body", "name_jp": "遺体", "name_en": "Dead Body"},
    "STORAGE_BOX": {"id": "source_storage_box", "name_jp": "ストレージボックス", "name_en": "Storage Box"},
    "DRONE_WRECK": {"id": "source_drone_wreck", "name_jp": "ドローンの残骸", "name_en": "Drone Wreck"},
    "RUBBLE_PILE": {"id": "source_rubble_pile", "name_jp": "がれきの山", "name_en": "Rubble Pile"},
    "PERSONAL_STORAGE": {"id": "source_personal_storage", "name_jp": "パーソナルストレージ", "name_en": "Personal Storage"},
    "CONSOLE": {"id": "source_console", "name_jp": "コンソール", "name_en": "Console"},
    "UNDERGROUND_CAVE": {"id": "source_underground_cave", "name_jp": "地下洞窟", "name_en": "Underground Cave"},
    "MONOLITH": {"id": "source_monolith", "name_jp": "モノリス", "name_en": "Monolith"},
    "GEO_SCANNER": {"id": "source_geo_scanner", "name_jp": "ジオスキャナー", "name_en": "Geo Scanner"},
    "SPACESHIP": {"id": "source_spaceship", "name_jp": "宇宙船", "name_en": "Spaceship"},
    "COLONY": {"id": "source_colony", "name_jp": "群生地", "name_en": "Colony"},
    "ITEM_PRINTER": {"id": "source_item_printer", "name_jp": "アイテムプリンター", "name_en": "Item Printer"},
    "SEARCH": {"id": "source_search", "name_jp": "サーチ", "name_en": "Search"},
    "KEYCARD": {"id": "source_keycard", "name_jp": "キーカード", "name_en": "Keycard"},
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def backup_file(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(path.suffix + f".{ts}.bak")
    bak.write_bytes(path.read_bytes())
    return bak


def normalize_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(cfg)

    out["object_types"] = {
        "loot": {"name_jp": "ルート源", "name_en": "Loot Source"},
        "other": {"name_jp": "その他", "name_en": "Other"},
    }
    out["attr_mapping"] = {
        LOOT_SOURCE_ID: {
            "name_jp": "ルート源",
            "name_en": "Loot Source",
            "type": "loot",
            "attributes": {},
            "use_category_slots": True,
        }
    }
    out["cat_mapping"] = {LOOT_SOURCE_ID: "ルート源"}

    # 拡張用メタ: 旧来のコンテナ種別をここで保持
    out["source_category_master"] = deepcopy(SOURCE_KIND_MAP)

    # 既存カテゴリ（設計図/LEM/戦時債権...）はそのまま利用する
    if not isinstance(out.get("category_master"), dict):
        out["category_master"] = {}
    if not isinstance(out.get("item_master"), dict):
        out["item_master"] = {}
    if not isinstance(out.get("category_list"), list):
        out["category_list"] = list(out["category_master"].keys())

    return out


def parse_json_cell(s: str) -> Any:
    t = (s or "").strip()
    if not t:
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


def dump_json_cell(v: Any) -> str:
    if v in (None, "", {}):
        return ""
    return json.dumps(v, ensure_ascii=False)


def normalize_rows(rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    counts = {
        "rows_total": 0,
        "attribute_rewritten": 0,
        "obj_attributes_updated": 0,
        "category_pin_rewritten": 0,
    }
    out: List[Dict[str, str]] = []
    for row in rows:
        counts["rows_total"] += 1
        r = dict(row)

        old_attr = (r.get("attribute") or "").strip()
        source = SOURCE_KIND_MAP.get(old_attr, {"id": "source_unknown", "name_jp": old_attr or "不明", "name_en": old_attr or "Unknown"})

        if old_attr != LOOT_SOURCE_ID:
            r["attribute"] = LOOT_SOURCE_ID
            counts["attribute_rewritten"] += 1

        if (r.get("category_pin") or "").strip() != LOOT_SOURCE_ID:
            r["category_pin"] = LOOT_SOURCE_ID
            counts["category_pin_rewritten"] += 1

        obj_attrs = parse_json_cell(r.get("obj_attributes", "")) or {}
        if not isinstance(obj_attrs, dict):
            obj_attrs = {}
        obj_attrs["source_category_id"] = source["id"]
        obj_attrs["source_category_jp"] = source["name_jp"]
        obj_attrs["source_category_en"] = source["name_en"]
        r["obj_attributes"] = dump_json_cell(obj_attrs)
        counts["obj_attributes_updated"] += 1

        out.append(r)

    return out, counts


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return fields, rows


def write_csv(path: Path, fields: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Starrupture Update_1 to loot-source model.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, dry-run only.")
    args = parser.parse_args()

    if not CONFIG_PATH.exists() or not CSV_PATH.exists():
        raise SystemExit("Update_1 config/master_data.csv が見つかりません。")

    cfg = load_json(CONFIG_PATH)
    new_cfg = normalize_config(cfg)
    fields, rows = read_csv(CSV_PATH)
    new_rows, counts = normalize_rows(rows)

    print("=== normalize_starrupture_update1 ===")
    for k, v in counts.items():
        print(f"{k}: {v}")
    print(f"config_changed: {cfg != new_cfg}")

    if not args.apply:
        print("dry-run complete. Use --apply to write files.")
        return

    cfg_bak = backup_file(CONFIG_PATH)
    csv_bak = backup_file(CSV_PATH)
    dump_json(CONFIG_PATH, new_cfg)
    write_csv(CSV_PATH, fields, new_rows)
    print(f"backups: {cfg_bak.name}, {csv_bak.name}")
    print("applied.")


if __name__ == "__main__":
    main()

