#!/usr/bin/env python3
"""
master_data.csv を現行仕様（attribute, obj_attributes, categories JSON, 全列）に変換する。
games/StarRupture/None/ の config.json と master_data.csv を読み、同ディレクトリに上書き保存する。
"""
import csv
import json
import os
import re
from datetime import datetime

GAME_DIR = os.path.join(os.path.dirname(__file__), "..", "games", "StarRupture", "None")
CONFIG_PATH = os.path.join(GAME_DIR, "config.json")
CSV_PATH = os.path.join(GAME_DIR, "master_data.csv")
OUT_PATH = os.path.join(GAME_DIR, "master_data.csv")

# name_jp / name_en の表記ゆれ → attr_mapping の ID
NAME_TO_OBJ_ID = {
    "遺体": "DEAD_BODY",
    "dead body": "DEAD_BODY",
    "ストレージボックス": "STORAGE_BOX",
    "storage box": "STORAGE_BOX",
    "ドローンの残骸": "DRONE_WRECK",
    "drone wreck": "DRONE_WRECK",
    "がれきの山": "RUBBLE_PILE",
    "rubble pile": "RUBBLE_PILE",
    "rubble piles": "RUBBLE_PILE",
    "パーソナルストレージ": "PERSONAL_STORAGE",
    "個人ストレージ": "PERSONAL_STORAGE",
    "personal storage": "PERSONAL_STORAGE",
    "コンソール": "CONSOLE",
    "console": "CONSOLE",
    "地下洞窟": "UNDERGROUND_CAVE",
    "cave": "UNDERGROUND_CAVE",
    "underground cave": "UNDERGROUND_CAVE",
    "モノリス": "MONOLITH",
    "monolith": "MONOLITH",
    "ジオスキャナー": "GEO_SCANNER",
    "geo scanner": "GEO_SCANNER",
    "宇宙船": "SPACESHIP",
    "spaceship": "SPACESHIP",
    "群生地": "COLONY",
    "colony": "COLONY",
    "プリズムハーブ群生地": "COLONY",
    "アイテムプリンター": "ITEM_PRINTER",
    "item printer": "ITEM_PRINTER",
    "サーチ": "SEARCH",
    "search": "SEARCH",
    "キーカード": "KEYCARD",
    "keycard": "KEYCARD",
    "key card": "KEYCARD",
}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def obj_id_from_name(name_jp: str, name_en: str, attr_mapping: dict) -> str:
    """name_jp / name_en からオブジェクトIDを決定する。"""
    # 括弧付きは括弧を除いて比較（遺体（洞窟内）→ 遺体）
    jp = (name_jp or "").strip()
    en = (name_en or "").strip().lower()
    jp_base = re.sub(r"[（(].*?[）)]", "", jp).strip()
    for key, val in attr_mapping.items():
        if not isinstance(val, dict):
            continue
        nj = (val.get("name_jp") or "").strip()
        ne = (val.get("name_en") or "").strip().lower()
        if jp == nj or jp_base == nj or en == ne:
            return key
    # 表記ゆれマップ
    if jp_base in NAME_TO_OBJ_ID:
        return NAME_TO_OBJ_ID[jp_base]
    if en in NAME_TO_OBJ_ID:
        return NAME_TO_OBJ_ID[en]
    # category_pin がそのまま object ID になっている場合（既に DEAD_BODY など）
    for key in attr_mapping:
        if key == jp or key == en:
            return key
    return ""


def obj_attributes_from_name(name_jp: str, name_en: str) -> dict:
    """遺体（洞窟内）など、名前から obj_attributes を生成。遺体かつ洞窟表記のときのみ。"""
    if not name_jp and not name_en:
        return {}
    jp = name_jp or ""
    en = (name_en or "").lower()
    if "遺体" in jp and ("洞窟" in jp or "cave" in en):
        return {"場所": "洞窟内"}
    return {}


def parse_memo_to_categories(memo_jp: str, memo_en: str, config: dict) -> tuple:
    """
    memo_jp の <br> 区切り行を解釈し、(categories 配列, 未解析行のインデックス一覧) を返す。
    設計図：XXX / 戦時債権（N）/ LEM名（下級・上級）/ 交換アイテム名（N） などを検出。
    カテゴリに取り込んだ行はメモから削除するため、未解析の行インデックスを返す。
    """
    cm = config.get("category_master", {})
    im = config.get("item_master", {})
    cat_name_to_id = {}
    for cname, cinfo in cm.items():
        if isinstance(cinfo, dict) and cinfo.get("id"):
            cat_name_to_id[cname] = cinfo["id"]

    # カテゴリ名 → そのカテゴリの item_id を name_jp で検索
    def find_item_id(cat_name: str, name_jp: str) -> str:
        if cat_name not in im:
            return ""
        for iid, info in im[cat_name].items():
            if isinstance(info, dict) and info.get("name_jp") == name_jp:
                return iid
        return ""

    def find_item_id_by_jp_any_category(name_jp: str) -> tuple:
        for cat_name, items in im.items():
            if not isinstance(items, dict):
                continue
            for iid, info in items.items():
                if isinstance(info, dict) and info.get("name_jp") == name_jp:
                    return cat_name, iid
        return "", ""

    out = []
    consumed = set()  # 解析してカテゴリに取り込んだ行のインデックス
    if not memo_jp:
        return out, []
    lines = [s.strip() for s in memo_jp.replace("<br>", "\n").split("\n") if s.strip()]

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 設計図：XXX または 設計図；XXX
        m = re.match(r"設計図[：:;；]\s*(.+)", line)
        if m:
            item_jp = m.group(1).strip()
            cat_id = cat_name_to_id.get("設計図", "blueprint")
            item_id = find_item_id("設計図", item_jp)
            if not item_id and "設計図" in im:
                for iid, info in im["設計図"].items():
                    if isinstance(info, dict) and item_jp in (info.get("name_jp") or ""):
                        item_id = iid
                        break
            if item_id:
                info = im["設計図"][item_id]
                out.append({
                    "cat_id": cat_id,
                    "category": "設計図",
                    "item_id": item_id,
                    "item_name_jp": info.get("name_jp", item_jp),
                    "item_name_en": info.get("name_en", item_jp),
                    "qty": "1",
                    "attributes": {}
                })
                consumed.add(idx)
            continue

        # 戦時債権（N） or 戦時債権N
        m = re.match(r"戦時債権\s*[（(]?\s*(\d+)\s*[）)]?", line)
        if m:
            qty = m.group(1)
            cat_id = cat_name_to_id.get("戦時債権", "war_bonds")
            item_id = "War Bonds" if im.get("戦時債権") else ""
            item_name_jp = "戦時債権"
            item_name_en = "War Bonds"
            if im.get("戦時債権"):
                for iid, info in im["戦時債権"].items():
                    if isinstance(info, dict):
                        item_name_jp = info.get("name_jp", item_name_jp)
                        item_name_en = info.get("name_en", item_name_en)
                        item_id = iid
                        break
            out.append({
                "cat_id": cat_id,
                "category": "戦時債権",
                "item_id": item_id,
                "item_name_jp": item_name_jp,
                "item_name_en": item_name_en,
                "qty": qty,
                "attributes": {}
            })
            consumed.add(idx)
            continue

        # 交換アイテム: "名前（ポイント）" 形式
        m = re.match(r"(.+?)\s*[（(]\s*(\d+)\s*[）)]\s*$", line)
        if m:
            label, num = m.group(1).strip(), m.group(2)
            cat_id = cat_name_to_id.get("交換アイテム", "trade_item")
            for cat_name, items in im.items():
                if cat_name != "交換アイテム" or not isinstance(items, dict):
                    continue
                for iid, info in items.items():
                    if not isinstance(info, dict):
                        continue
                    if info.get("name_jp") == label or label in (info.get("name_jp") or ""):
                        pt = info.get("attributes", {}).get("ポイント", {})
                        if isinstance(pt, dict):
                            pt = pt.get("value", num)
                        out.append({
                            "cat_id": cat_id,
                            "category": "交換アイテム",
                            "item_id": iid,
                            "item_name_jp": info.get("name_jp", label),
                            "item_name_en": info.get("name_en", label),
                            "qty": "1",
                            "attributes": {"ポイント": str(pt)}
                        })
                        consumed.add(idx)
                        break
                else:
                    continue
                break
            else:
                # マスタにない交換アイテムらしき行はスキップ（または attributes のみで追加は可能だが省略）
                pass
            continue

        # LEM: 下級XXX LEM / 上級XXX LEM / XXX LEM
        rank = ""
        lem_name = line
        if line.startswith("下級"):
            rank = "下級"
            lem_name = line[2:].strip()
        elif line.startswith("上級"):
            rank = "上級"
            lem_name = line[2:].strip()
        elif "LEM" in line:
            rank = "接頭語なし"
        if "LEM" in lem_name and "LEM" in im:
            # name_jp で検索（スワッパーLEM, ライフギバーLEM など）
            for iid, info in im["LEM"].items():
                if not isinstance(info, dict):
                    continue
                if info.get("name_jp") == lem_name or info.get("name_jp") == line:
                    out.append({
                        "cat_id": cat_name_to_id.get("LEM", "lem"),
                        "category": "LEM",
                        "item_id": iid,
                        "item_name_jp": info.get("name_jp", lem_name),
                        "item_name_en": info.get("name_en", lem_name),
                        "qty": "1",
                        "attributes": {"ランク": rank} if rank else {}
                    })
                    consumed.add(idx)
                    break
            else:
                # 名前が完全一致しない（表記ゆれ）場合は LEM のいずれかで近いものを探す
                for iid, info in im["LEM"].items():
                    if not isinstance(info, dict):
                        continue
                    nj = info.get("name_jp", "")
                    if lem_name in nj or nj in lem_name or line in nj:
                        out.append({
                            "cat_id": cat_name_to_id.get("LEM", "lem"),
                            "category": "LEM",
                            "item_id": iid,
                            "item_name_jp": info.get("name_jp", lem_name),
                            "item_name_en": info.get("name_en", lem_name),
                            "qty": "1",
                            "attributes": {"ランク": rank} if rank else {}
                        })
                        consumed.add(idx)
                        break
            continue

        # キーカード系（自由記述）は categories に含めず memo に残す
        # その他未対応の行も memo のみに残す
    unparsed_indices = [i for i in range(len(lines)) if i not in consumed]
    return out, unparsed_indices


def migrate_row(row: dict, config: dict) -> dict:
    attr_mapping = config.get("attr_mapping", {})
    name_jp = (row.get("name_jp") or "").strip()
    name_en = (row.get("name_en") or "").strip()
    x = row.get("x", "")
    y = row.get("y", "")
    uid = (row.get("uid") or "").strip()
    memo_jp = (row.get("memo_jp") or "").strip()
    memo_en = (row.get("memo_en") or "").strip()

    attribute = obj_id_from_name(name_jp, name_en, attr_mapping)
    if not attribute and row.get("category_pin"):
        # 既存の category_pin がオブジェクトIDになっている場合
        cp = row["category_pin"].strip()
        if cp in attr_mapping:
            attribute = cp
        else:
            # 旧コード（ITEM_WEAPON など）は name からだけ判定
            attribute = obj_id_from_name(name_jp, name_en, attr_mapping)

    obj_attributes = obj_attributes_from_name(name_jp, name_en)
    categories_data, unparsed_indices = parse_memo_to_categories(memo_jp, memo_en, config)

    # メモはカテゴリに取り込んだ行を除き、未解析の行だけ残す（重複削除）
    if memo_jp:
        lines_jp = [s.strip() for s in memo_jp.replace("<br>", "\n").split("\n") if s.strip()]
        lines_en = [s.strip() for s in (memo_en or "").replace("<br>", "\n").split("\n") if s.strip()]
        unparsed_jp = [lines_jp[i] for i in unparsed_indices if i < len(lines_jp)]
        unparsed_en = [lines_en[i] for i in unparsed_indices if i < len(lines_en)]
        memo_jp = "<br>".join(unparsed_jp) if unparsed_jp else ""
        memo_en = "<br>".join(unparsed_en) if unparsed_en else ""

    # name_jp / name_en: 中身があれば先頭スロットのアイテム名、なければオブジェクト表示名
    if categories_data:
        main_category = categories_data[0].get("category", "")
        name_jp = categories_data[0].get("item_name_jp", name_jp)
        name_en = categories_data[0].get("item_name_en", name_en)
    else:
        main_category = ""
        if attribute and attribute in attr_mapping:
            o = attr_mapping[attribute]
            if isinstance(o, dict):
                name_jp = o.get("name_jp", name_jp)
                name_en = o.get("name_en", name_en)

    return {
        "uid": uid,
        "x": x,
        "y": y,
        "name_jp": name_jp,
        "name_en": name_en,
        "attribute": attribute,
        "obj_attributes": json.dumps(obj_attributes, ensure_ascii=False) if obj_attributes else "",
        "category": main_category,
        "categories": json.dumps(categories_data, ensure_ascii=False) if categories_data else "",
        "importance": row.get("importance", ""),
        "category_pin": attribute,
        "contents": row.get("contents", ""),
        "memo_jp": memo_jp,
        "memo_en": memo_en,
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def main():
    config = load_config()
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            try:
                row["x"] = float(row.get("x", 0))
                row["y"] = float(row.get("y", 0))
            except (ValueError, TypeError):
                pass
            rows.append(row)

    out_fields = [
        "uid", "x", "y", "name_jp", "name_en", "attribute", "obj_attributes",
        "category", "categories", "importance", "category_pin", "contents",
        "memo_jp", "memo_en", "updated_at"
    ]
    out_rows = []
    for row in rows:
        out_rows.append(migrate_row(row, config))

    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    print(f"Wrote {len(out_rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
