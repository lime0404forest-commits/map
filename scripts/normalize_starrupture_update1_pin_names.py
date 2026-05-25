#!/usr/bin/env python3
"""
Update_1: name_jp/name_en は例外的な別名用。categories / source_category と重複する name は空にする。
対象: games/starrupture/Update_1/master_data.csv のみ。
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "games" / "starrupture" / "Update_1" / "master_data.csv"


def _parse_obj_attrs(raw: str) -> dict:
    if not (raw or "").strip():
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _parse_categories(raw: str) -> list:
    if not (raw or "").strip():
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _slot_redundant_with_name(nj: str, ne: str, c: dict) -> bool:
    """スロットの表示に相当する文字列と name が一致していれば冗長。"""
    if not isinstance(c, dict):
        return False
    cat_jp = (c.get("category") or "").strip()
    cat_en = (c.get("cat_name_en") or "").strip()
    ij = (c.get("item_name_jp") or "").strip()
    ie = (c.get("item_name_en") or "").strip()
    if not ie:
        ie = cat_en
    dj = ij or cat_jp
    de = ie or cat_en
    if not dj and not de:
        return False
    if nj and ne:
        return nj == dj and ne == de
    if nj and not ne:
        return nj == dj
    if ne and not nj:
        return ne == de
    return False


def _name_redundant_with_any_slot(nj: str, ne: str, arr: list) -> bool:
    for c in arr:
        if _slot_redundant_with_name(nj, ne, c):
            return True
    return False


def _strip_source_dup(nj: str, ne: str, oa: dict) -> tuple[str, str]:
    sj = (oa.get("source_category_jp") or "").strip()
    se = (oa.get("source_category_en") or "").strip()
    if sj and nj == sj:
        nj = ""
    if se and ne == se:
        ne = ""
    return nj, ne


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8-sig", newline="")))
    if not rows:
        print("no rows")
        return
    fields = list(rows[0].keys())
    changed = 0
    for r in rows:
        oj = (r.get("name_jp") or "").strip()
        oe = (r.get("name_en") or "").strip()
        if not oj and not oe:
            continue
        nj, ne = oj, oe
        oa = _parse_obj_attrs(r.get("obj_attributes", ""))
        arr = _parse_categories(r.get("categories", ""))

        if _name_redundant_with_any_slot(nj, ne, arr):
            nj, ne = "", ""
        else:
            nj, ne = _strip_source_dup(nj, ne, oa)

        if nj != oj or ne != oe:
            r["name_jp"] = nj
            r["name_en"] = ne
            changed += 1

    if changed == 0:
        print("changed: 0")
        return

    bak = CSV_PATH.with_suffix(".csv." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".names.bak")
    bak.write_bytes(CSV_PATH.read_bytes())
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"changed rows: {changed}")
    print(f"backup: {bak.name}")


if __name__ == "__main__":
    main()
