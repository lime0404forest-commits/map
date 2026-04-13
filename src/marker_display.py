# -*- coding: utf-8 -*-
"""マップピンの表示スタイル（標準ピン vs アイコンのみ）の定数と正規化。"""
from __future__ import annotations

from typing import Any, Optional

MARKER_DISPLAY_STANDARD = "standard"
MARKER_DISPLAY_ICON_ONLY = "icon_only"


def normalize_marker_display_style(value: Optional[Any]) -> str:
    """未設定・未知は standard。icon_only の別表記も吸収。"""
    s = str(value or "").strip().lower().replace("-", "_")
    if s in ("icon_only", "icononly"):
        return MARKER_DISPLAY_ICON_ONLY
    return MARKER_DISPLAY_STANDARD
