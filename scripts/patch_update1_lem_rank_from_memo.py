#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "games" / "starrupture" / "Update_1" / "master_data.csv"

LEM_ID_BY_JP = {
    "スワッパーLEM": "Swapper LEM",
    "ライフギバーLEM": "Lifegiver LEM",
    "エアジャンパーLEM": "Air Jumper LEM",
    "デスイーターLEM": "Deatheater LEM",
    "インフィルトレーターLEM": "Infiltrator LEM",
    "イミューナーLEM": "Immuner LEM",
    "マイナーLEM": "Miner LEM",
    "ランナーLEM": "Runner LEM",
    "ドッジャーLEM": "Dodger LEM",
    "シールドギバーLEM": "Shieldgiver LEM",
    "フォールガイLEM": "Fallguy LEM",
    "ダイエティシャンLEM": "Dietician LEM",
    "レジスターLEM": "Resister LEM",
    "スライダーLEM": "Slider LEM",
    "レズレクターLEM": "Resurrector LEM",
    "スカルパーLEM": "Scalper LEM",
    "リローダーLEM": "Reloader LEM",
    "イリゲーターLEM": "Irrigator LEM",
    "シールドフィクサーLEM": "Shieldfixer LEM",
    "デトキシファイアーLEM": "Detoxifier LEM",
    "レプリンターLEM": "Reprinter LEM",
    "フィクサーLEM": "Fixer LEM",
    "コンパニオンLEM": "Companion LEM",
    "エイマーLEM": "Aimer LEM",
    "エンデュランスギバーLEM": "Endurancegiver LEM",
    "グルトンLEM": "Glutton LEM",
}


def parse_categories(raw: str):
    if not (raw or "").strip():
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def to_json(v):
    return json.dumps(v, ensure_ascii=False) if v else ""


def main():
    rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8-sig", newline="")))
    if not rows:
        print("no rows")
        return
    fields = list(rows[0].keys())
    patched = 0

    pat = re.compile(r"(上級|中級|下級)\s*([^\n\r<]*?LEM)")
    for r in rows:
        cats = parse_categories(r.get("categories", ""))
        has_lem = any(str(c.get("cat_id", "")).lower() == "lem" for c in cats if isinstance(c, dict))
        if has_lem:
            continue
        memo_jp = (r.get("memo_jp") or "").replace("<br>", "\n")
        m = pat.search(memo_jp)
        if not m:
            continue
        rank = m.group(1).strip()
        item_jp = m.group(2).strip()
        item_jp = re.sub(r"\s+LEM$", "LEM", item_jp)
        item_en = LEM_ID_BY_JP.get(item_jp)
        if not item_en:
            continue
        cats.append(
            {
                "cat_id": "lem",
                "category": "LEM",
                "item_id": item_en,
                "item_name_jp": item_jp,
                "item_name_en": item_en,
                "qty": "1",
                "attributes": {"ランク": rank},
            }
        )
        if not (r.get("category") or "").strip():
            r["category"] = "LEM"
        r["categories"] = to_json(cats)
        patched += 1

    if patched == 0:
        print("patched: 0")
        return

    bak = CSV_PATH.with_suffix(f".csv.{datetime.now().strftime('%Y%m%d_%H%M%S')}.lemfix.bak")
    bak.write_bytes(CSV_PATH.read_bytes())
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"patched: {patched}")
    print(f"backup: {bak.name}")


if __name__ == "__main__":
    main()

