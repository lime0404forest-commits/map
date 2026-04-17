import tkinter as tk
from tkinter import messagebox, ttk, colorchooser
import customtkinter as ctk
import os
import json
import csv
import math
import time
from collections import OrderedDict
import re  # 追加
import threading
from datetime import datetime
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageTk

from .constants import GAMES_ROOT, PROJECT_ROOT
from . import svg_icon_assets
from . import wp_rest_guide
from .marker_display import normalize_marker_display_style
from .utils import save_cropped_image_with_annotations
from .export_utils import resolve_pin_for_display
from . import pin_site_preview
from . import category_special_notes
from . import category_special_rules_builder

# 入力ボックス共通スタイル（枠ではなく「ボックス本体」の見た目を統一）
BOX_FG = "#2e4053"           # やや柔らかい青系の塗り
BOX_CORNER = 8               # 角丸でカード風に
BOX_BORDER_WIDTH = 1
BOX_BORDER_COLOR = "#3d5166" # 控えめな縁で立体感
BOX_PADX, BOX_PADY = 12, 10 # 内側の余白

GUIDE_PAGE_LINKS_DEFAULT_FILE = "guide_page_links.json"
GUIDE_LINK_PICK_NONE = "（ページ候補から選ぶ）"
PARENT_TYPE_DEFAULT = "inside"
PARENT_TYPE_VALUES = ("inside", "near", "in_area")
PARENT_TYPE_LABELS = OrderedDict((
    ("inside", "中 (inside)"),
    ("near", "近く (near)"),
    ("in_area", "エリア内 (in the area)"),
))

# CTkScrollableFrame: event.widget が str になることがあり AttributeError を防ぐ
try:
    _orig_check = ctk.CTkScrollableFrame.check_if_master_is_canvas
    def _safe_check_if_master_is_canvas(self, widget):
        if widget is None or not hasattr(widget, "master"):
            return False
        return _orig_check(self, widget)
    ctk.CTkScrollableFrame.check_if_master_is_canvas = _safe_check_if_master_is_canvas
except Exception:
    pass

# ==========================================
# 環境設定ウィンドウ (カテゴリ & 高機能マスタ管理)
# ==========================================
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_path, current_config):
        super().__init__(parent)
        self.title("環境設定 & 高機能マスタ管理")
        self.geometry("1280x880")
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.transient(parent)
        self.parent = parent
        self.config_path = config_path
        self.config = current_config
        self.game_path = getattr(parent, "game_path", "") or ""
        self.project_root = PROJECT_ROOT
        
        self.attr_rows = []
        self.route_attr_rows = []
        self.cat_rows = []
        self.item_rows = []
        self._master_row_drag = None
        self._master_col_scale = 1.0
        self._attr_split_mode = self.config.get("map_object_attr_ids") is not None
        
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.tab_attr = self.tabview.add("1. オブジェクト")
        if self._attr_split_mode:
            self.tab_route = self.tabview.add("ルート参照")
        self.tab_cat = self.tabview.add("2. カテゴリ")
        self.tab_item = self.tabview.add("3. アイテム")
        self.tab_en = self.tabview.add("EN未設定確認")
        self.tab_type_legacy = self.tabview.add("種類(type)")
        
        self.setup_attr_tab()
        if self._attr_split_mode:
            self.setup_route_attr_tab()
        self.setup_cat_tab()
        self.setup_item_tab()
        self.setup_en_tab()
        self.setup_type_legacy_tab()

        f_foot = ctk.CTkFrame(self, fg_color="transparent")
        f_foot.pack(fill="x", padx=20, pady=10)
        f_scale = ctk.CTkFrame(f_foot, fg_color="transparent")
        f_scale.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ctk.CTkLabel(f_scale, text="マスタ表の列幅", font=("Meiryo", 10)).pack(side="left", padx=(0, 8))
        self._master_col_slider = ctk.CTkSlider(
            f_scale,
            from_=0.72,
            to=1.65,
            number_of_steps=46,
            width=280,
            command=self._on_master_col_slider,
        )
        self._master_col_slider.set(1.0)
        self._master_col_slider.pack(side="left", padx=4)
        ctk.CTkButton(
            f_foot,
            text="💾 設定を保存して反映",
            command=self.save_settings,
            fg_color="#27ae60",
            width=200,
            height=40,
            font=("Meiryo", 12, "bold"),
        ).pack(side="right")

    def _mcol(self, base: float) -> int:
        return max(1, int(round(float(base) * getattr(self, "_master_col_scale", 1.0))))

    def _on_master_col_slider(self, value=None):
        try:
            v = float(value) if value is not None else float(self._master_col_slider.get())
        except (TypeError, ValueError, AttributeError):
            v = 1.0
        self._master_col_scale = v
        self._refresh_all_master_table_grids()

    def _configure_attr_table_columns(self, f):
        m = self._mcol
        f.grid_columnconfigure(0, weight=0, minsize=m(92))
        f.grid_columnconfigure(1, weight=1, minsize=m(178))
        f.grid_columnconfigure(2, weight=1, minsize=m(178))
        f.grid_columnconfigure(3, weight=0, minsize=m(128))
        f.grid_columnconfigure(4, weight=0, minsize=m(50))
        f.grid_columnconfigure(5, weight=0, minsize=m(92))
        f.grid_columnconfigure(6, weight=1, minsize=m(142))
        f.grid_columnconfigure(7, weight=0, minsize=m(228))
        f.grid_columnconfigure(8, weight=0, minsize=m(42))

    def _configure_cat_table_columns(self, f):
        m = self._mcol
        f.grid_columnconfigure(0, weight=0, minsize=m(92))
        f.grid_columnconfigure(1, weight=0, minsize=m(168))
        f.grid_columnconfigure(2, weight=1, minsize=m(148))
        f.grid_columnconfigure(3, weight=1, minsize=m(148))
        f.grid_columnconfigure(4, weight=1, minsize=m(118))
        f.grid_columnconfigure(5, weight=0, minsize=m(108))
        f.grid_columnconfigure(6, weight=0, minsize=m(46))
        f.grid_columnconfigure(7, weight=0, minsize=m(228))
        f.grid_columnconfigure(8, weight=0, minsize=m(42))

    def _configure_item_table_columns(self, f):
        m = self._mcol
        f.grid_columnconfigure(0, weight=0, minsize=m(92))
        f.grid_columnconfigure(1, weight=0, minsize=m(138))
        f.grid_columnconfigure(2, weight=1, minsize=m(128))
        f.grid_columnconfigure(3, weight=1, minsize=m(172))
        f.grid_columnconfigure(4, weight=1, minsize=m(172))
        f.grid_columnconfigure(5, weight=0, minsize=m(92))
        f.grid_columnconfigure(6, weight=0, minsize=m(228))
        f.grid_columnconfigure(7, weight=0, minsize=m(42))

    def _refresh_all_master_table_grids(self):
        def _cfg_frame(f, kind):
            if f is None:
                return
            try:
                if not f.winfo_exists():
                    return
            except tk.TclError:
                return
            if kind == "attr":
                self._configure_attr_table_columns(f)
            elif kind == "cat":
                self._configure_cat_table_columns(f)
            elif kind == "item":
                self._configure_item_table_columns(f)

        _cfg_frame(getattr(self, "_f_head_attr", None), "attr")
        _cfg_frame(getattr(self, "_f_head_route", None), "attr")
        _cfg_frame(getattr(self, "_f_head_cat", None), "cat")
        _cfg_frame(getattr(self, "_f_head_item", None), "item")
        for r in self.attr_rows:
            try:
                self._configure_attr_table_columns(r["frame"])
                self._sync_attr_row_widget_sizes(r)
            except (tk.TclError, KeyError):
                pass
        for r in self.route_attr_rows:
            try:
                self._configure_attr_table_columns(r["frame"])
                self._sync_attr_row_widget_sizes(r)
            except (tk.TclError, KeyError):
                pass
        for r in self.cat_rows:
            try:
                self._configure_cat_table_columns(r["frame"])
                self._sync_cat_row_widget_sizes(r)
            except (tk.TclError, KeyError):
                pass
        for r in self.item_rows:
            try:
                self._configure_item_table_columns(r["frame"])
                self._sync_item_row_widget_sizes(r)
            except (tk.TclError, KeyError):
                pass

    def _sync_attr_row_widget_sizes(self, r):
        s = getattr(self, "_master_col_scale", 1.0)
        r["name_jp"].configure(width=max(72, int(178 * s)))
        r["name_en"].configure(width=max(72, int(178 * s)))
        r["type"].configure(width=max(96, int(124 * s)))
        r["lbl_id"].configure(width=max(72, int(138 * s)))

    def _sync_cat_row_widget_sizes(self, r):
        s = getattr(self, "_master_col_scale", 1.0)
        r["obj_group"].configure(width=max(88, int(164 * s)))
        r["name_jp"].configure(width=max(64, int(148 * s)))
        r["name_en"].configure(width=max(64, int(148 * s)))
        r["id"].configure(width=max(56, int(118 * s)))
        r["input_type"].configure(width=max(88, int(104 * s)))

    def _sync_item_row_widget_sizes(self, r):
        s = getattr(self, "_master_col_scale", 1.0)
        r["grp"].configure(width=max(72, int(132 * s)))
        r["id"].configure(width=max(64, int(128 * s)))
        r["jp"].configure(width=max(72, int(172 * s)))
        r["en"].configure(width=max(72, int(172 * s)))

    def setup_attr_tab(self):
        # オブジェクト種類リスト（JSON の type 値／「種類(type)」タブと対応）
        self.object_types = ["loot", "landmark", "colony", "other"]
        self.object_type_names = {
            "loot": "アイテムルート源",
            "landmark": "ランドマーク",
            "colony": "群生地",
            "other": "その他"
        }
        
        f_head = ctk.CTkFrame(self.tab_attr, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        self._f_head_attr = f_head
        hr = 0
        ctk.CTkLabel(f_head, text="並替", anchor="w", font=("Meiryo", 9, "bold"), text_color="#888888").grid(row=hr, column=0, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="表示名(JP)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=1, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="表示名(EN)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=2, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="種類(type)", anchor="w", font=("Meiryo", 11, "bold"), text_color="#888888").grid(row=hr, column=3, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="下位カテゴリ", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=4, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="属性項目", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=5, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="自動生成ID", anchor="w", font=("Meiryo", 11, "bold"), text_color="#888888").grid(row=hr, column=6, sticky="w", padx=4, pady=2)
        f_h_pin = ctk.CTkFrame(f_head, fg_color="transparent")
        f_h_pin.grid(row=hr, column=7, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_h_pin, text="アイコン", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f_h_pin, text="マーカー", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left")
        ctk.CTkLabel(f_head, text="削除", anchor="w", font=("Meiryo", 10, "bold"), text_color="#888888").grid(row=hr, column=8, sticky="e", padx=4, pady=2)
        self._configure_attr_table_columns(f_head)
        self.scroll_attr = ctk.CTkScrollableFrame(self.tab_attr, fg_color="#2b2b2b")
        self.scroll_attr.pack(expand=True, fill="both", padx=5, pady=5)
        ctk.CTkLabel(
            self.tab_attr,
            text="マップ上のピンで選ぶ「オブジェクト」です。config の map_object_attr_ids で行数・並びが決まります。",
            font=("Meiryo", 9),
            text_color="#888888",
        ).pack(anchor="w", padx=8, pady=(0, 4))
        ctk.CTkButton(self.tab_attr, text="＋ オブジェクト行を追加", command=self.add_attr_row_empty, fg_color="#e67e22").pack(pady=5)

    def setup_route_attr_tab(self):
        """カテゴリの object_ids などが参照するルート用 ID（コンテナ・沈没船など）。"""
        ctk.CTkLabel(
            self.tab_route,
            text="カテゴリマスタの object_ids から参照される定義です。マップのオブジェクトコンボには出ません。",
            font=("Meiryo", 9),
            text_color="#888888",
        ).pack(anchor="w", padx=8, pady=(8, 4))
        f_head = ctk.CTkFrame(self.tab_route, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        self._f_head_route = f_head
        hr = 0
        ctk.CTkLabel(f_head, text="並替", anchor="w", font=("Meiryo", 9, "bold"), text_color="#888888").grid(row=hr, column=0, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="表示名(JP)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=1, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="表示名(EN)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=2, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="種類(type)", anchor="w", font=("Meiryo", 11, "bold"), text_color="#888888").grid(row=hr, column=3, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="下位カテゴリ", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=4, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="属性項目", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=5, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="自動生成ID", anchor="w", font=("Meiryo", 11, "bold"), text_color="#888888").grid(row=hr, column=6, sticky="w", padx=4, pady=2)
        f_h_pin = ctk.CTkFrame(f_head, fg_color="transparent")
        f_h_pin.grid(row=hr, column=7, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_h_pin, text="アイコン", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f_h_pin, text="マーカー", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left")
        ctk.CTkLabel(f_head, text="削除", anchor="w", font=("Meiryo", 10, "bold"), text_color="#888888").grid(row=hr, column=8, sticky="e", padx=4, pady=2)
        self._configure_attr_table_columns(f_head)
        self.scroll_route = ctk.CTkScrollableFrame(self.tab_route, fg_color="#2b2b2b")
        self.scroll_route.pack(expand=True, fill="both", padx=5, pady=5)
        ctk.CTkButton(self.tab_route, text="＋ ルート参照行を追加", command=self.add_route_attr_row_empty, fg_color="#e67e22").pack(pady=5)

    def setup_cat_tab(self):
        f_head = ctk.CTkFrame(self.tab_cat, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        self._f_head_cat = f_head
        hr = 0
        ctk.CTkLabel(f_head, text="並替", anchor="w", font=("Meiryo", 9, "bold"), text_color="#888888").grid(row=hr, column=0, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="対応オブジェクト", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=1, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="カテゴリ名(JP)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=2, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="カテゴリ名(EN)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=3, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="ID", anchor="w", font=("Meiryo", 11, "bold"), text_color="#888888").grid(row=hr, column=4, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="入力形式", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=5, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="数量", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=6, sticky="w", padx=4, pady=2)
        f_h_pin = ctk.CTkFrame(f_head, fg_color="transparent")
        f_h_pin.grid(row=hr, column=7, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_h_pin, text="アイコン", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f_h_pin, text="マーカー", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left")
        ctk.CTkLabel(f_head, text="削除", anchor="w", font=("Meiryo", 10, "bold"), text_color="#888888").grid(row=hr, column=8, sticky="e", padx=4, pady=2)
        self._configure_cat_table_columns(f_head)
        self.scroll_cat = ctk.CTkScrollableFrame(self.tab_cat, fg_color="#2b2b2b")
        self.scroll_cat.pack(expand=True, fill="both", padx=5, pady=5)
        ctk.CTkButton(self.tab_cat, text="＋ カテゴリ行を追加", command=self.add_cat_row_empty, fg_color="#3498db").pack(pady=5)

    def setup_item_tab(self):
        f_tools = ctk.CTkFrame(self.tab_item, fg_color="transparent")
        f_tools.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(f_tools, text="📥 現在のCSVからデータをインポート", command=self.import_from_csv, 
                      fg_color="#8e44ad", width=200).pack(side="left", padx=5)

        f_head = ctk.CTkFrame(self.tab_item, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        self._f_head_item = f_head
        hr = 0
        ctk.CTkLabel(f_head, text="並替", anchor="w", font=("Meiryo", 9, "bold"), text_color="#888888").grid(row=hr, column=0, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="対応カテゴリ", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=1, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="ID", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=2, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="名前(JP)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=3, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="名前(EN)", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=4, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_head, text="属性・操作", anchor="w", font=("Meiryo", 11, "bold")).grid(row=hr, column=5, sticky="w", padx=4, pady=2)
        f_h_pin = ctk.CTkFrame(f_head, fg_color="transparent")
        f_h_pin.grid(row=hr, column=6, sticky="w", padx=4, pady=2)
        ctk.CTkLabel(f_h_pin, text="アイコン", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f_h_pin, text="マーカー", anchor="w", font=("Meiryo", 11, "bold")).pack(side="left")
        ctk.CTkLabel(f_head, text="削除", anchor="w", font=("Meiryo", 10, "bold"), text_color="#888888").grid(row=hr, column=7, sticky="e", padx=4, pady=2)
        self._configure_item_table_columns(f_head)

        self.scroll_item = ctk.CTkScrollableFrame(self.tab_item, fg_color="#2b2b2b")
        self.scroll_item.pack(expand=True, fill="both", padx=5, pady=5)
        ctk.CTkButton(self.tab_item, text="＋ アイテム行を追加", command=self.add_item_row_empty, fg_color="#3498db").pack(pady=5)

    def setup_en_tab(self):
        """EN未設定の項目を一覧し、JPで一括設定できるタブ"""
        f_tools = ctk.CTkFrame(self.tab_en, fg_color="transparent")
        f_tools.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(f_tools, text="🔄 一覧を更新", command=self.refresh_en_list, fg_color="#3498db", width=120).pack(side="left", padx=5)
        ctk.CTkButton(f_tools, text="EN未設定をJPで一括設定", command=self.fill_missing_en_from_jp,
                      fg_color="#27ae60", width=220).pack(side="left", padx=5)
        ctk.CTkLabel(self.tab_en, text="以下は name_en が空または未設定の項目です。一括設定で name_jp の値を name_en にコピーできます。",
                     font=("Meiryo", 10), text_color="#888").pack(anchor="w", padx=5, pady=(0,5))
        self.txt_en_missing = ctk.CTkTextbox(self.tab_en, fg_color="#1a1a1a", font=("Meiryo", 10))
        self.txt_en_missing.pack(expand=True, fill="both", padx=5, pady=5)
        self.refresh_en_list()

    def setup_type_legacy_tab(self):
        """config の type 列の後方互換用。編集不可の参照タブ。"""
        wrap = ctk.CTkFrame(self.tab_type_legacy, fg_color="#333333", corner_radius=8)
        wrap.pack(expand=True, fill="both", padx=16, pady=16)
        ctk.CTkLabel(
            wrap,
            text="種類(type) はオブジェクト廃止時の構造互換のため JSON に残しています。\n"
                 "このタブは一覧参照のみです。ルート用 ID の編集は「ルート参照」、マップ用は「1. オブジェクト」、カテゴリは「2. カテゴリ」で行ってください。",
            font=("Meiryo", 11),
            text_color="#909090",
            justify="left",
        ).pack(anchor="w", padx=14, pady=(14, 10))
        box = ctk.CTkFrame(wrap, fg_color="#2b2b2b", corner_radius=6)
        box.pack(fill="x", padx=12, pady=(0, 14))
        for t in self.object_types:
            jp = self.object_type_names.get(t, t)
            ctk.CTkLabel(
                box,
                text=f"  {t}  …  {jp}",
                font=("Consolas", 11),
                text_color="#666666",
                anchor="w",
            ).pack(fill="x", padx=10, pady=4)

    def refresh_en_list(self):
        """EN未設定の項目を収集してテキストに表示"""
        lines = []
        am = self.config.get("attr_mapping", {})
        for k, v in am.items():
            if isinstance(v, dict):
                nj = (v.get("name_jp") or "").strip()
                ne = (v.get("name_en") or "").strip()
                if not ne and nj:
                    lines.append(f"【オブジェクト】 {nj}")
        cm = self.config.get("category_master", {})
        for name, info in cm.items():
            if isinstance(info, dict):
                nj = (info.get("name_jp") or name or "").strip()
                ne = (info.get("name_en") or "").strip()
                if not ne and nj:
                    lines.append(f"【カテゴリ】 {nj}")
        im = self.config.get("item_master", {})
        for cat, items in im.items():
            if not isinstance(items, dict):
                continue
            for iid, info in items.items():
                if isinstance(info, dict):
                    nj = (info.get("name_jp") or "").strip()
                    ne = (info.get("name_en") or "").strip()
                    if not ne and nj:
                        lines.append(f"【アイテム】 {cat} > {nj}")
        self.txt_en_missing.delete("1.0", tk.END)
        if not lines:
            self.txt_en_missing.insert("1.0", "EN未設定の項目はありません。")
        else:
            self.txt_en_missing.insert("1.0", "\n".join(lines))

    def fill_missing_en_from_jp(self):
        """ENが空の項目について name_en を name_jp で埋めて保存"""
        changed = False
        am = self.config.get("attr_mapping", {})
        for k, v in am.items():
            if isinstance(v, dict):
                nj = (v.get("name_jp") or "").strip()
                ne = (v.get("name_en") or "").strip()
                if not ne and nj:
                    v["name_en"] = nj
                    changed = True
        cm = self.config.get("category_master", {})
        for name, info in cm.items():
            if isinstance(info, dict):
                nj = (info.get("name_jp") or name or "").strip()
                ne = (info.get("name_en") or "").strip()
                if not ne and nj:
                    info["name_en"] = nj
                    changed = True
        im = self.config.get("item_master", {})
        for cat, items in im.items():
            if not isinstance(items, dict):
                continue
            for iid, info in items.items():
                if isinstance(info, dict):
                    nj = (info.get("name_jp") or "").strip()
                    ne = (info.get("name_en") or "").strip()
                    if not ne and nj:
                        info["name_en"] = nj
                        changed = True
        if not changed:
            messagebox.showinfo("EN一括設定", "EN未設定の項目はありませんでした。")
            self.refresh_en_list()
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("EN一括設定", "EN未設定の項目を name_jp で埋めて保存しました。")
            self.refresh_en_list()
        except Exception as e:
            messagebox.showerror("保存エラー", str(e))

    def load_current_settings(self):
        for w in self.scroll_attr.winfo_children():
            w.destroy()
        self.attr_rows = []
        if self._attr_split_mode and getattr(self, "scroll_route", None):
            for w in self.scroll_route.winfo_children():
                w.destroy()
            self.route_attr_rows = []

        # オブジェクト設定（JP/EN + type + attributes対応）
        attr_mapping = self.config.get("attr_mapping", {})
        # 後方互換性：旧cat_mappingから変換
        if not attr_mapping:
            old_mapping = self.config.get("cat_mapping", {})
            if old_mapping:
                attr_mapping = {}
                for k, v in old_mapping.items():
                    attr_mapping[k] = {"name_jp": v, "name_en": k, "type": "loot", "attributes": {}}

        mo_ids = self.config.get("map_object_attr_ids")
        if mo_ids is not None:
            seen = set()
            for kid in mo_ids:
                seen.add(kid)
                if kid in attr_mapping:
                    v = attr_mapping[kid]
                    if isinstance(v, dict):
                        self.add_attr_row(
                            v.get("name_jp", ""),
                            v.get("name_en", ""),
                            v.get("type", "loot"),
                            v.get("attributes", {}),
                            v.get("use_category_slots", True),
                            kid,
                        )
                    else:
                        self.add_attr_row(v, kid, "loot", {}, True, kid)
                else:
                    self.add_attr_row("", "", "loot", {}, True, kid)
            for k, v in attr_mapping.items():
                if k in seen:
                    continue
                if isinstance(v, dict):
                    self.add_attr_row(
                        v.get("name_jp", ""),
                        v.get("name_en", ""),
                        v.get("type", "loot"),
                        v.get("attributes", {}),
                        v.get("use_category_slots", True),
                        k,
                        scroll_parent=self.scroll_route,
                        rows_list=self.route_attr_rows,
                    )
                else:
                    self.add_attr_row(
                        v, k, "loot", {}, True, k,
                        scroll_parent=self.scroll_route,
                        rows_list=self.route_attr_rows,
                    )
            if not self.attr_rows and not self.route_attr_rows:
                self.add_attr_row("", "", "loot", {}, True, None)
        else:
            if not attr_mapping:
                self.add_attr_row("", "", "loot", {}, True, None)
            for k, v in attr_mapping.items():
                if isinstance(v, dict):
                    self.add_attr_row(
                        v.get("name_jp", ""),
                        v.get("name_en", ""),
                        v.get("type", "loot"),
                        v.get("attributes", {}),
                        v.get("use_category_slots", True),
                        k,
                    )
                else:
                    self.add_attr_row(v, k, "loot", {}, True, k)

        # カテゴリマスタ（JP/EN + type + input_type + show_qty）
        category_master = self.config.get("category_master", {})
        # 後方互換性：旧category_listから変換
        if not category_master:
            old_list = self.config.get("category_list", [])
            if old_list:
                category_master = {}
                for cat in old_list:
                    if cat:
                        category_master[cat] = {"name_jp": cat, "name_en": "", "type": "loot", "input_type": "item_select", "show_qty": True}
        
        if not category_master: self.add_cat_row("", "", "", "item_select", True, "")
        for cat_key, cat_info in category_master.items():
            if isinstance(cat_info, dict):
                self.add_cat_row(
                    cat_info.get("name_jp", cat_key),
                    cat_info.get("name_en", ""),
                    self._infer_object_attr_id_from_cat_info(cat_info),
                    cat_info.get("input_type", "item_select"),
                    cat_info.get("show_qty", True),
                    cat_info.get("id", "")
                )
            else:
                self.add_cat_row(cat_info, "", "", "item_select", True, "")

        # アイテムマスタ
        item_master = self.config.get("item_master", {})
        if not item_master: self.add_item_row("", "", "", "", {})
        
        for grp, items in item_master.items():
            for i_id, info in items.items():
                attrs = info.get("attributes", {})
                self.add_item_row(grp, i_id, info.get("name_jp",""), info.get("name_en",""), attrs)

    def generate_id_from_en(self, en_name):
        """英語名からIDを自動生成"""
        if not en_name:
            return ""
        # スペースをアンダースコアに、大文字に変換、特殊文字を除去
        import re
        id_str = en_name.upper().replace(" ", "_")
        id_str = re.sub(r'[^A-Z0-9_]', '', id_str)
        return id_str

    def _hex6_or_default(self, v, default):
        s = (v or "").strip()
        if re.match(r"^#[0-9a-fA-F]{6}$", s):
            return s
        return default

    def _load_pin_marker_from_map(self, section, key):
        raw = None
        if isinstance(section, dict) and (key or "").strip():
            k = (key or "").strip()
            raw = section.get(k)
            if raw is None:
                ku = k.upper()
                if ku != k:
                    raw = section.get(ku)
        if not isinstance(raw, dict):
            return {
                "svg_icon_id": "",
                "svg_icon_scope": "common",
                "icon_color": "#ffffff",
                "background_color": "#95a5a6",
                "display_style": "",
                "_display_style_explicit": False,
            }
        # 旧キー marker_display_style も許容
        raw_ds = (raw.get("display_style") or raw.get("marker_display_style") or "").strip()
        ds_norm = normalize_marker_display_style(raw_ds) if raw_ds else ""
        return {
            "svg_icon_id": (raw.get("svg_icon_id") or "").strip(),
            "svg_icon_scope": (raw.get("svg_icon_scope") or "common").strip() or "common",
            "icon_color": self._hex6_or_default(raw.get("icon_color"), "#ffffff"),
            "background_color": self._hex6_or_default(raw.get("background_color"), "#95a5a6"),
            # 仕様: エントリが存在するレイヤーは display_style 未指定でも standard 扱い
            "display_style": ("icon_only" if ds_norm == "icon_only" else "standard"),
            "_display_style_explicit": bool(raw_ds),
        }

    def _load_pin_marker_for_key(self, obj_key):
        section = self.config.get("pin_marker_by_attribute") or {}
        k = (obj_key or "").strip()
        pm = self._load_pin_marker_from_map(section, k)
        # map.js 側は attribute キーを大文字でも引くため、マスタ管理も同じ見え方に合わせる
        if not pm.get("svg_icon_id") and normalize_marker_display_style(pm.get("display_style")) != "icon_only" and k:
            ku = k.upper()
            if ku != k:
                pm_u = self._load_pin_marker_from_map(section, ku)
                if pm_u.get("svg_icon_id") or normalize_marker_display_style(pm_u.get("display_style")) == "icon_only":
                    return pm_u
        return pm

    def _load_pin_marker_for_category_id(self, cat_id):
        return self._load_pin_marker_from_map(self.config.get("pin_marker_by_category_id") or {}, cat_id)

    def _load_pin_marker_for_item_id(self, item_id):
        return self._load_pin_marker_from_map(self.config.get("pin_marker_by_item_id") or {}, item_id)

    def _effective_category_id_from_row(self, r):
        n_jp = r["name_jp"].get().strip()
        n_en = r["name_en"].get().strip()
        cid = r["id"].get().strip() if r.get("id") else ""
        if not cid and n_en:
            cid = self.generate_id_from_en(n_en)
        if not cid and n_jp:
            cid = re.sub(r"[^a-zA-Z0-9_\u3040-\u9fff]", "_", n_jp)[:30].strip("_") or ("cat_" + str(abs(hash(n_jp)))[:8])
        return cid

    def _effective_item_id_from_row(self, r):
        """アイテム行から保存用IDを決める（空なら EN→JP の順で自動生成）。"""
        i = (r["id"].get().strip() if r.get("id") else "")
        if i:
            return i
        n_en = (r["en"].get().strip() if r.get("en") else "")
        if n_en:
            i = self.generate_id_from_en(n_en)
        if i:
            return i
        n_jp = (r["jp"].get().strip() if r.get("jp") else "")
        if n_jp:
            i = re.sub(r"[^a-zA-Z0-9_\u3040-\u9fff]", "_", n_jp)[:40].strip("_")
            if not i:
                i = "item_" + str(abs(hash(n_jp)))[:8]
        return i

    def _effective_object_key_from_row(self, r):
        prev_key = (r.get("obj_key") or "").strip()
        if prev_key:
            return prev_key
        n_en = (r.get("name_en") and r["name_en"].get() or "").strip()
        if n_en:
            k = self.generate_id_from_en(n_en)
            if k:
                return k
        n_jp = (r.get("name_jp") and r["name_jp"].get() or "").strip()
        if n_jp:
            k2 = re.sub(r"[^a-zA-Z0-9_\u3040-\u9fff]", "_", n_jp)[:40].strip("_")
            if k2:
                return k2
            return self.parent._generate_obj_id(n_jp)
        return ""

    def _normalize_bilingual_names(self, jp_raw, en_raw, fallback):
        jp = str(jp_raw or "").strip()
        en = str(en_raw or "").strip()
        fb = str(fallback or "").strip()
        if not jp:
            jp = en or fb
        if not en:
            en = jp or fb
        return jp, en

    def _serialize_pin_marker_row(self, pm):
        """map.js applyPinMarkerPartial と同じキー（svg_icon_id, svg_icon_scope, icon_color, background_color, display_style）。"""
        sid = (pm.get("svg_icon_id") or "").strip()
        ds = (pm.get("display_style") or "").strip().lower().replace("-", "_")
        if not sid and ds not in ("icon_only", "icononly"):
            return None
        out = {}
        if sid:
            out["svg_icon_id"] = sid
        sc = (pm.get("svg_icon_scope") or "common").strip()
        out["svg_icon_scope"] = sc if sc == "game" else "common"
        out["icon_color"] = self._hex6_or_default(pm.get("icon_color"), "#ffffff")
        out["background_color"] = self._hex6_or_default(pm.get("background_color"), "#95a5a6")
        if ds in ("icon_only", "icononly"):
            out["display_style"] = "icon_only"
        else:
            out["display_style"] = "standard"
        return out

    def _pin_marker_mode_label_text(self, pm):
        ds = normalize_marker_display_style((pm.get("display_style") or pm.get("marker_display_style") or "").strip())
        return "モード: icon_only" if ds == "icon_only" else "モード: 標準"

    def _refresh_pin_marker_row_preview(self, row_rec, icon_px=20):
        pm = row_rec["pin_marker"]
        try:
            row_rec["pin_swatch_icon"].configure(fg_color=pm["icon_color"])
            row_rec["pin_swatch_bg"].configure(fg_color=pm["background_color"])
        except Exception:
            pass
        if row_rec.get("lbl_pin_mode") is not None:
            try:
                row_rec["lbl_pin_mode"].configure(text=self._pin_marker_mode_label_text(pm))
            except Exception:
                pass
        lbl = row_rec["lbl_pin_preview"]
        holder = row_rec["_pin_preview_holder"]
        sid = (pm.get("svg_icon_id") or "").strip()
        ic = self._hex6_or_default(pm.get("icon_color"), "#ffffff")
        resolved = svg_icon_assets.resolve_svg_icon(self.project_root, self.game_path, sid) if sid else None
        if resolved and os.path.isfile(resolved["abs_path"]):
            pil = svg_icon_assets.svg_or_placeholder_pil_rgba(resolved["abs_path"], icon_px, ic)
            if pil is not None:
                cti = ctk.CTkImage(light_image=pil, dark_image=pil, size=(icon_px, icon_px))
                lbl.configure(image=cti, text="")
                holder.clear()
                holder.append(cti)
                return
        try:
            lbl.configure(image=None, text=("…" if sid else "—"))
        except tk.TclError:
            pass
        holder.clear()

    def _build_pin_marker_by_attribute_from_rows(self, rows, base_map=None):
        out = dict(base_map) if isinstance(base_map, dict) else {}
        for r in rows:
            key = self._effective_object_key_from_row(r)
            if not key:
                continue
            ser = self._serialize_pin_marker_row(r.get("pin_marker") or {})
            if ser:
                out[key] = ser
            else:
                out.pop(key, None)
        return out

    def _build_pin_marker_by_category_from_rows(self, rows, base_map=None):
        out = dict(base_map) if isinstance(base_map, dict) else {}
        for r in rows:
            cid = self._effective_category_id_from_row(r)
            if not cid:
                continue
            ser = self._serialize_pin_marker_row(r.get("pin_marker") or {})
            if ser:
                out[cid] = ser
            else:
                out.pop(cid, None)
        return out

    def _build_pin_marker_by_item_from_rows(self, rows, base_map=None):
        out = dict(base_map) if isinstance(base_map, dict) else {}
        for r in rows:
            i = self._effective_item_id_from_row(r)
            if not i:
                continue
            ser = self._serialize_pin_marker_row(r.get("pin_marker") or {})
            if ser:
                out[i] = ser
            else:
                out.pop(i, None)
        return out

    _PIN_MARKER_COLOR_PRESETS = (
        "#ffffff", "#ecf0f1", "#bdc3c7", "#95a5a6", "#7f8c8d", "#34495e", "#2c3e50", "#000000",
        "#e74c3c", "#e67e22", "#f39c12", "#f1c40f", "#2ecc71", "#16a085", "#1abc9c",
        "#3498db", "#2980b9", "#8e44ad", "#9b59b6", "#e91e63", "#d35400", "#c0392b",
    )

    def _open_pin_marker_dialog(self, row_rec, title="マーカー（ピン見た目）"):
        pm = row_rec["pin_marker"]
        default_pm = {
            "svg_icon_id": "",
            "svg_icon_scope": "common",
            "icon_color": "#ffffff",
            "background_color": "#95a5a6",
            "display_style": "",
            "_display_style_explicit": False,
        }
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("760x920")
        win.minsize(560, 620)
        win.attributes("-topmost", True)
        win.focus_force()
        win.grab_set()
        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=0, pady=0)

        cur_id = (pm.get("svg_icon_id") or "").strip()
        cur_scope = (pm.get("svg_icon_scope") or "common").strip() or "common"
        if cur_scope not in ("common", "game"):
            cur_scope = "common"

        entries = list(svg_icon_assets.list_svg_icon_entries(self.project_root, self.game_path))
        known_ids = {e["id"] for e in entries}
        if cur_id and cur_id not in known_ids:
            resolved = svg_icon_assets.resolve_svg_icon(self.project_root, self.game_path, cur_id)
            if resolved:
                entries.append(
                    {"id": cur_id, "abs_path": resolved["abs_path"], "scope": resolved["scope"]},
                )
            else:
                entries.append({"id": cur_id, "abs_path": "", "scope": cur_scope})

        selected_ref = [None]
        preview_img_holder = []
        debounce_id = [None]
        grid_btns = []

        scope_var = tk.StringVar(value="game" if cur_scope == "game" else "common")

        ctk.CTkLabel(body, text="プレビュー（選択中のアイコン・色）", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        f_preview = ctk.CTkFrame(body, fg_color="transparent")
        f_preview.pack(anchor="w", padx=12, pady=(0, 6))
        pin_bg_fr = ctk.CTkFrame(f_preview, width=88, height=88, corner_radius=10, fg_color="#95a5a6")
        pin_bg_fr.pack(side="left", padx=(0, 12))
        pin_bg_fr.pack_propagate(False)
        lbl_big = ctk.CTkLabel(pin_bg_fr, text="—", font=("Meiryo", 11), text_color="#ecf0f1")
        lbl_big.place(relx=0.5, rely=0.5, anchor="center")

        def refresh_dialog_preview():
            ic = self._hex6_or_default(ent_ic.get(), "#ffffff")
            bg = self._hex6_or_default(ent_bg.get(), "#95a5a6")
            pin_bg_fr.configure(fg_color=bg)
            sel = selected_ref[0]
            sid = (sel["id"] if sel else "") or ""
            path = ""
            if sel and (sel.get("abs_path") or "").strip() and os.path.isfile(sel["abs_path"]):
                path = sel["abs_path"]
            elif sid:
                r = svg_icon_assets.resolve_svg_icon(self.project_root, self.game_path, sid)
                path = r["abs_path"] if r else ""
            if path and os.path.isfile(path):
                pil = svg_icon_assets.svg_or_placeholder_pil_rgba(path, 56, ic)
                if pil is not None:
                    cti = ctk.CTkImage(light_image=pil, dark_image=pil, size=(56, 56))
                    lbl_big.configure(image=cti, text="")
                    preview_img_holder.clear()
                    preview_img_holder.append(cti)
                    return
            try:
                lbl_big.configure(image=None, text=("…" if sid else "—"))
            except tk.TclError:
                pass
            preview_img_holder.clear()

        def schedule_preview(*_):
            if debounce_id[0] is not None:
                try:
                    win.after_cancel(debounce_id[0])
                except tk.TclError:
                    pass
            debounce_id[0] = win.after(120, refresh_dialog_preview)

        def clear_icon_selection_style():
            none_btn.configure(border_width=0)
            for b in grid_btns:
                b.configure(border_width=0)

        def select_no_icon():
            clear_icon_selection_style()
            none_btn.configure(border_width=2, border_color="#1f6aa5")
            selected_ref[0] = None
            refresh_dialog_preview()

        def select_icon_entry(e, btn):
            clear_icon_selection_style()
            btn.configure(border_width=2, border_color="#1f6aa5")
            selected_ref[0] = e
            scope_var.set(e.get("scope") or "common")
            refresh_dialog_preview()

        def apply_preset_to_entry(ent_widget, hex_val):
            ent_widget.delete(0, "end")
            ent_widget.insert(0, hex_val)
            refresh_dialog_preview()

        def open_chooser_for(ent_widget, title_txt):
            cur = ent_widget.get().strip()
            init = cur if re.match(r"^#[0-9a-fA-F]{6}$", cur) else None
            pair = colorchooser.askcolor(color=init, title=title_txt, parent=win)
            if pair and pair[1]:
                apply_preset_to_entry(ent_widget, pair[1])

        def pack_color_row(parent, label, initial_hex, title_txt):
            ctk.CTkLabel(parent, text=label, font=("Meiryo", 10)).pack(anchor="w", padx=0, pady=(8, 2))
            pal = ctk.CTkFrame(parent, fg_color="transparent")
            pal.pack(anchor="w", fill="x")
            per_row = 11
            light_hex = {"#ffffff", "#ecf0f1", "#f1c40f", "#bdc3c7"}
            for i, hx in enumerate(self._PIN_MARKER_COLOR_PRESETS):
                rr, cc = divmod(i, per_row)
                light = hx.lower() in light_hex
                kw = dict(
                    master=pal,
                    text="",
                    width=28,
                    height=28,
                    corner_radius=4,
                    fg_color=hx,
                    hover_color=hx,
                    command=lambda h=hx: apply_preset_to_entry(ent_widget, h),
                )
                if light:
                    kw["border_width"] = 1
                    kw["border_color"] = "#555555"
                ctk.CTkButton(**kw).grid(row=rr, column=cc, padx=2, pady=2)
            nrows = (len(self._PIN_MARKER_COLOR_PRESETS) - 1) // per_row + 1
            ctk.CTkButton(
                pal,
                text="その他の色…",
                width=110,
                height=28,
                fg_color="#566573",
                command=lambda: open_chooser_for(ent_widget, title_txt),
            ).grid(row=nrows, column=0, columnspan=4, sticky="w", padx=2, pady=(8, 2))
            row_hex = ctk.CTkFrame(parent, fg_color="transparent")
            row_hex.pack(anchor="w", fill="x", pady=(4, 0))
            row_hex.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row_hex, text="色コード（上級者向け）", font=("Meiryo", 9), text_color="#888888").grid(row=0, column=0, sticky="w", padx=(0, 8))
            ent_widget = ctk.CTkEntry(row_hex, width=120)
            ent_widget.insert(0, initial_hex)
            ent_widget.grid(row=0, column=1, sticky="w")
            return ent_widget

        ctk.CTkLabel(
            body,
            text="アイコン（画像をクリックして選択・スクロールできます）",
            font=("Meiryo", 10),
        ).pack(anchor="w", padx=12, pady=(8, 2))

        scroll_icons = ctk.CTkScrollableFrame(body, height=240, fg_color="#2b2b2b", corner_radius=6)
        scroll_icons.pack(fill="x", padx=12, pady=(0, 4))

        none_btn = ctk.CTkButton(
            scroll_icons,
            text="アイコンなし",
            height=32,
            fg_color="#566573",
            command=select_no_icon,
        )
        none_btn.pack(fill="x", padx=6, pady=(6, 8))

        grid_wrap = ctk.CTkFrame(scroll_icons, fg_color="transparent")
        grid_wrap.pack(fill="x", padx=4, pady=(0, 8))
        thumb_refs = []
        cols = 5
        thumb_color = "#eeeeee"
        for idx, e in enumerate(entries):
            r, c = divmod(idx, cols)
            cell = ctk.CTkFrame(grid_wrap, fg_color="transparent")
            cell.grid(row=r, column=c, padx=4, pady=4, sticky="n")
            ap = e.get("abs_path") or ""
            pil = None
            if ap and os.path.isfile(ap):
                pil = svg_icon_assets.svg_or_placeholder_pil_rgba(ap, 42, thumb_color)
            if pil is not None:
                cti = ctk.CTkImage(light_image=pil, dark_image=pil, size=(42, 42))
                thumb_refs.append(cti)
                btn = ctk.CTkButton(
                    cell,
                    image=cti,
                    text="",
                    width=52,
                    height=52,
                    fg_color="#3d3d3d",
                    hover_color="#4a4a4a",
                )
            else:
                btn = ctk.CTkButton(
                    cell,
                    text="?",
                    width=52,
                    height=52,
                    fg_color="#3d3d3d",
                    font=("Meiryo", 14, "bold"),
                )
            btn.pack()
            scope_tag = "共通" if e.get("scope") == "common" else "ゲーム"
            ctk.CTkLabel(
                cell,
                text=f'{e["id"]}\n({scope_tag})',
                font=("Meiryo", 8),
                text_color="#aaaaaa",
                justify="center",
            ).pack(pady=(2, 0))
            btn.configure(command=lambda ei=e, b=btn: select_icon_entry(ei, b))
            grid_btns.append(btn)

        ctk.CTkLabel(body, text="参照先（アイコン選択時は自動で合わせます。必要なら変更可）", font=("Meiryo", 10)).pack(anchor="w", padx=12, pady=(6, 2))
        f_sc = ctk.CTkFrame(body, fg_color="transparent")
        f_sc.pack(anchor="w", padx=12)
        ctk.CTkRadioButton(f_sc, text="共通 assets", variable=scope_var, value="common").pack(side="left", padx=6)
        ctk.CTkRadioButton(f_sc, text="ゲームローカル", variable=scope_var, value="game").pack(side="left", padx=6)

        f_colors = ctk.CTkFrame(body, fg_color="transparent")
        f_colors.pack(fill="x", padx=12, pady=(4, 0))
        ent_ic = pack_color_row(f_colors, "アイコン色", pm.get("icon_color", "#ffffff"), "アイコン色を選ぶ")
        ent_bg = pack_color_row(f_colors, "背景色（標準モードの枠・ベース）", pm.get("background_color", "#95a5a6"), "背景色を選ぶ")

        ent_ic.bind("<KeyRelease>", schedule_preview)
        ent_bg.bind("<KeyRelease>", schedule_preview)

        ctk.CTkLabel(body, text="表示モード（map.js の marker_display_style）", font=("Meiryo", 10)).pack(anchor="w", padx=12, pady=(10, 2))
        ds_var = tk.StringVar(
            value="icon_only" if (pm.get("display_style") or "").strip().lower().replace("-", "_") in ("icon_only", "icononly") else "standard"
        )
        ds_explicit_ref = [bool(pm.get("_display_style_explicit"))]
        f_ds = ctk.CTkFrame(body, fg_color="transparent")
        f_ds.pack(anchor="w", padx=12)
        ctk.CTkRadioButton(f_ds, text="標準（枠＋アイコン）", variable=ds_var, value="standard").pack(side="left", padx=6)
        ctk.CTkRadioButton(f_ds, text="icon_only（シルエットのみ）", variable=ds_var, value="icon_only").pack(side="left", padx=6)

        ctk.CTkLabel(
            body,
            text="※ map.js は pin_marker_by_* と同じキーで読み込みます（svg_icon_assets / currentColor 契約）。",
            font=("Meiryo", 9),
            text_color="#888888",
            wraplength=620,
        ).pack(anchor="w", padx=12, pady=8)

        def reset_to_defaults():
            select_no_icon()
            scope_var.set(default_pm["svg_icon_scope"])
            apply_preset_to_entry(ent_ic, default_pm["icon_color"])
            apply_preset_to_entry(ent_bg, default_pm["background_color"])
            ds_var.set("standard")
            ds_explicit_ref[0] = False
            refresh_dialog_preview()

        def apply():
            sel = selected_ref[0]
            sid = (sel["id"] if sel else "") or ""
            pm["svg_icon_id"] = sid.strip()
            pm["svg_icon_scope"] = scope_var.get()
            pm["icon_color"] = self._hex6_or_default(ent_ic.get(), "#ffffff")
            pm["background_color"] = self._hex6_or_default(ent_bg.get(), "#95a5a6")
            if ds_var.get() == "icon_only":
                pm["display_style"] = "icon_only"
                pm["_display_style_explicit"] = True
            else:
                pm["display_style"] = "standard" if ds_explicit_ref[0] else ""
                pm["_display_style_explicit"] = ds_explicit_ref[0]
            self._refresh_pin_marker_row_preview(row_rec)
            win.destroy()

        f_btn = ctk.CTkFrame(win, fg_color="transparent")
        f_btn.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(
            f_btn,
            text="デフォルトに戻す",
            command=reset_to_defaults,
            fg_color="#566573",
            width=130,
        ).pack(side="left", padx=(4, 14))
        ctk.CTkButton(f_btn, text="OK", command=apply, fg_color="#27ae60", width=100).pack(side="left", padx=4)
        ctk.CTkButton(f_btn, text="キャンセル", command=win.destroy, fg_color="#7f8c8d", width=100).pack(side="left", padx=4)

        if cur_id:
            match = next((e for e in entries if e["id"] == cur_id), None)
            if match:
                bi = entries.index(match)
                btn = grid_btns[bi]
                select_icon_entry(match, btn)
            else:
                select_no_icon()
        else:
            select_no_icon()
        refresh_dialog_preview()

    def add_attr_row_empty(self):
        self.add_attr_row("", "", "loot", {}, True, None)
        self.after(10, lambda: self.scroll_attr._parent_canvas.yview_moveto(1.0))

    def add_route_attr_row_empty(self):
        self.add_attr_row(
            "", "", "loot", {}, True, None,
            scroll_parent=self.scroll_route,
            rows_list=self.route_attr_rows,
        )
        self.after(10, lambda: self.scroll_route._parent_canvas.yview_moveto(1.0))

    def _repack_rows_in_list(self, rows_list):
        if not rows_list:
            return
        for r in rows_list:
            try:
                r["frame"].pack_forget()
            except tk.TclError:
                pass
        for r in rows_list:
            r["frame"].pack(fill="x", pady=2)

    def _move_master_row(self, frame, rows_list, delta):
        try:
            idx = next(i for i, r in enumerate(rows_list) if r["frame"] == frame)
        except StopIteration:
            return
        j = idx + delta
        if j < 0 or j >= len(rows_list):
            return
        rows_list[idx], rows_list[j] = rows_list[j], rows_list[idx]
        self._repack_rows_in_list(rows_list)

    def _place_master_row_reorder_grid(self, parent, rows_list, row=0, col=0):
        f_ctl = ctk.CTkFrame(parent, fg_color="transparent")
        f_ctl.grid(row=row, column=col, sticky="nw", padx=(0, 2), pady=2)
        lbl = ctk.CTkLabel(
            f_ctl,
            text="⠿",
            width=22,
            cursor="hand2",
            font=("Segoe UI Symbol", 14),
            text_color="#95a5a6",
        )
        lbl.pack(side="left", padx=(0, 2))
        lbl.bind("<Button-1>", lambda e, rl=rows_list, fr=parent: self._master_row_drag_start(e, rl, fr))
        ctk.CTkButton(
            f_ctl,
            text="▲",
            width=24,
            height=24,
            fg_color="#34495e",
            command=lambda fr=parent, rl=rows_list: self._move_master_row(fr, rl, -1),
        ).pack(side="left", padx=1)
        ctk.CTkButton(
            f_ctl,
            text="▼",
            width=24,
            height=24,
            fg_color="#34495e",
            command=lambda fr=parent, rl=rows_list: self._move_master_row(fr, rl, 1),
        ).pack(side="left", padx=1)

    def _master_row_drag_start(self, event, rows_list, frame):
        if self._master_row_drag is not None:
            return
        try:
            idx = next(i for i, r in enumerate(rows_list) if r["frame"] == frame)
        except StopIteration:
            return
        self._master_row_drag = {"rows": rows_list, "from_idx": idx}
        try:
            self.grab_set()
        except tk.TclError:
            self._master_row_drag = None
            return
        self.bind("<B1-Motion>", self._master_row_drag_motion)
        self.bind("<ButtonRelease-1>", self._master_row_drag_release)

    def _master_row_drag_motion(self, event):
        pass

    def _master_row_drag_release(self, event):
        st = self._master_row_drag
        self._master_row_drag = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        try:
            self.unbind("<B1-Motion>")
            self.unbind("<ButtonRelease-1>")
        except tk.TclError:
            pass
        if not st:
            return
        rows_list = st["rows"]
        from_idx = st["from_idx"]
        if not rows_list or from_idx < 0 or from_idx >= len(rows_list):
            return
        cy = event.y_root
        new_idx = len(rows_list) - 1
        for j, r in enumerate(rows_list):
            fw = r["frame"]
            try:
                top = fw.winfo_rooty()
                h = max(fw.winfo_height(), 1)
            except tk.TclError:
                self._repack_rows_in_list(rows_list)
                return
            if cy < top + h // 2:
                new_idx = j
                break
        if new_idx == from_idx:
            self._repack_rows_in_list(rows_list)
            return
        row = rows_list.pop(from_idx)
        if new_idx > from_idx:
            new_idx -= 1
        rows_list.insert(new_idx, row)
        self._repack_rows_in_list(rows_list)

    def add_attr_row(self, name_jp, name_en, obj_type="loot", attributes=None, use_category_slots=True, obj_key=None,
                     scroll_parent=None, rows_list=None):
        if attributes is None:
            attributes = {}
        type_stored = obj_type if obj_type in self.object_types else "loot"
        scroll_parent = scroll_parent or self.scroll_attr
        rows_list = rows_list or self.attr_rows
        
        f = ctk.CTkFrame(scroll_parent, fg_color="transparent")
        f.pack(fill="x", pady=2)
        rw = 0
        self._place_master_row_reorder_grid(f, rows_list, rw, 0)
        s = getattr(self, "_master_col_scale", 1.0)
        e_name_jp = ctk.CTkEntry(f, width=max(72, int(178 * s)))
        e_name_jp.insert(0, name_jp)
        e_name_jp.grid(row=rw, column=1, sticky="ew", padx=4, pady=2)
        e_name_en = ctk.CTkEntry(f, width=max(72, int(178 * s)))
        e_name_en.insert(0, name_en)
        e_name_en.grid(row=rw, column=2, sticky="ew", padx=4, pady=2)

        # 種類(type): 表示のみ（グレーアウト・操作不可）
        type_display_list = [self.object_type_names.get(t, t) for t in self.object_types]
        cmb_type = ctk.CTkComboBox(f, values=type_display_list, width=max(96, int(124 * s)))
        cmb_type.set(self.object_type_names.get(type_stored, self.object_type_names["loot"]))
        cmb_type.grid(row=rw, column=3, sticky="w", padx=4, pady=2)
        try:
            cmb_type.configure(
                state="disabled",
                fg_color="#4a4a4a",
                button_color="#555555",
                border_color="#555555",
                text_color="#888888",
            )
        except Exception:
            cmb_type.configure(state="disabled")

        use_slots_var = tk.BooleanVar(value=bool(use_category_slots))
        chk_sub = ctk.CTkCheckBox(f, text="", variable=use_slots_var, width=36, checkbox_width=18, checkbox_height=18)
        chk_sub.grid(row=rw, column=4, sticky="w", padx=4, pady=2)

        # 属性項目ボタン
        attr_var = {"data": attributes if attributes else {}}
        btn_attr = ctk.CTkButton(f, text=f"属性({len(attr_var['data'])})", width=80, fg_color="#8e44ad",
                                 command=lambda: self.edit_obj_attributes(attr_var, btn_attr))
        btn_attr.grid(row=rw, column=5, sticky="w", padx=4, pady=2)

        # 自動生成ID（読み取り専用）— 保存済みキーがあればそれを表示
        id_preview = (obj_key or "").strip() or self.generate_id_from_en(name_en)
        lbl_id = ctk.CTkLabel(f, text=id_preview, width=max(72, int(138 * s)), text_color="#888888", anchor="w")
        lbl_id.grid(row=rw, column=6, sticky="ew", padx=4, pady=2)
        
        def on_en_change(*args):
            if not (obj_key or "").strip():
                lbl_id.configure(text=self.generate_id_from_en(e_name_en.get()))
            self._refresh_category_object_combo_values()
        e_name_en.bind("<KeyRelease>", on_en_change)
        e_name_jp.bind("<KeyRelease>", lambda e: self._refresh_category_object_combo_values())

        pin_marker = self._load_pin_marker_for_key((obj_key or "").strip())
        f_pin = ctk.CTkFrame(f, fg_color="transparent")
        f_pin.grid(row=rw, column=7, sticky="w", padx=4, pady=2)
        lbl_pin_preview = ctk.CTkLabel(
            f_pin, text="—", width=22, height=22, fg_color="transparent", corner_radius=0, text_color="#bdc3c7"
        )
        lbl_pin_preview.pack(side="left", padx=1)
        pin_swatch_icon = ctk.CTkFrame(f_pin, width=12, height=12, corner_radius=2, fg_color=pin_marker["icon_color"])
        pin_swatch_icon.pack(side="left", padx=2)
        pin_swatch_bg = ctk.CTkFrame(f_pin, width=12, height=12, corner_radius=2, fg_color=pin_marker["background_color"])
        pin_swatch_bg.pack(side="left", padx=2)
        lbl_pin_mode = ctk.CTkLabel(
            f_pin, text=self._pin_marker_mode_label_text(pin_marker), font=("Meiryo", 9), text_color="#95a5a6"
        )
        lbl_pin_mode.pack(side="left", padx=(4, 2))
        row_rec = {
            "frame": f,
            "name_jp": e_name_jp,
            "name_en": e_name_en,
            "type": cmb_type,
            "type_stored": type_stored,
            "use_slots_var": use_slots_var,
            "obj_key": obj_key,
            "lbl_id": lbl_id,
            "attr_var": attr_var,
            "pin_marker": pin_marker,
            "lbl_pin_preview": lbl_pin_preview,
            "pin_swatch_icon": pin_swatch_icon,
            "pin_swatch_bg": pin_swatch_bg,
            "lbl_pin_mode": lbl_pin_mode,
            "_pin_preview_holder": [],
        }
        ctk.CTkButton(
            f_pin, text="マーカー", width=68, height=26, fg_color="#2980b9",
            command=lambda rr=row_rec: self._open_pin_marker_dialog(
                rr, "マーカー（オブジェクト / pin_marker_by_attribute）",
            ),
        ).pack(side="left", padx=4)

        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", command=lambda: self.delete_row(f, rows_list)).grid(
            row=rw, column=8, sticky="e", padx=4, pady=2
        )
        self._configure_attr_table_columns(f)
        rows_list.append(row_rec)
        self._refresh_pin_marker_row_preview(row_rec)

    def edit_obj_attributes(self, attr_var, btn):
        """オブジェクトの属性項目を編集するウィンドウ"""
        win = ctk.CTkToplevel(self)
        win.title("オブジェクト属性項目の編集")
        win.geometry("600x500")
        win.attributes("-topmost", True)
        win.focus_force()
        win.grab_set()
        
        current_data = attr_var["data"]
        edit_rows = []
        
        ctk.CTkLabel(win, text="オブジェクトの属性項目を設定\n例：遺体の「場所」（地上/洞窟内）", font=("Meiryo", 11)).pack(pady=10)
        
        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        def on_type_change(row_data, type_val):
            if type_val == "select":
                row_data["options_frame"].pack(side="left", padx=2)
            else:
                row_data["options_frame"].pack_forget()

        def add_row(k="", attr_data=None):
            if attr_data is None:
                attr_data = {"type": "select", "options": []}
            
            if isinstance(attr_data, list):
                attr_data = {"type": "select", "options": attr_data}
            
            attr_type = attr_data.get("type", "select")
            options = attr_data.get("options", [])
            
            rf = ctk.CTkFrame(scroll, fg_color="#2b2b2b", corner_radius=5)
            rf.pack(fill="x", pady=5, padx=5)
            
            top_row = ctk.CTkFrame(rf, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(top_row, text="属性名:", width=60, anchor="w").pack(side="left", padx=2)
            ek = ctk.CTkEntry(top_row, width=120, placeholder_text="例: 場所")
            ek.insert(0, k)
            ek.pack(side="left", padx=2)
            
            ctk.CTkLabel(top_row, text="形式:", width=50, anchor="w").pack(side="left", padx=(10,2))
            type_var = tk.StringVar(value=attr_type)
            cmb_type = ctk.CTkComboBox(top_row, values=["number", "select"], width=100, variable=type_var)
            cmb_type.pack(side="left", padx=2)
            
            ctk.CTkButton(top_row, text="🗑️", width=30, fg_color="#c0392b", 
                         command=lambda: (rf.destroy(), edit_rows.remove(row_data) if row_data in edit_rows else None)).pack(side="right", padx=5)
            
            options_frame = ctk.CTkFrame(rf, fg_color="transparent")
            ctk.CTkLabel(options_frame, text="選択肢:", width=60, anchor="w").pack(side="left", padx=2)
            ev = ctk.CTkEntry(options_frame, width=350, placeholder_text="カンマ区切り 例: 地上,洞窟内")
            ev.insert(0, ",".join(options) if options else "")
            ev.pack(side="left", padx=2)
            
            row_data = {"frame": rf, "key": ek, "type_var": type_var, "options_entry": ev, "options_frame": options_frame}
            
            cmb_type.configure(command=lambda v: on_type_change(row_data, v))
            
            if attr_type == "select":
                options_frame.pack(fill="x", padx=10, pady=(0,5))
            
            edit_rows.append(row_data)

        for k, v in current_data.items():
            add_row(k, v)
        
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="＋ 属性項目追加", command=lambda: add_row(), fg_color="#3498db").pack(side="left", padx=10)
        
        def apply():
            new_attrs = {}
            for r in edit_rows:
                try:
                    k = r["key"].get().strip()
                    attr_type = r["type_var"].get()
                    if k:
                        if attr_type == "number":
                            new_attrs[k] = {"type": "number"}
                        else:
                            options_str = r["options_entry"].get().strip()
                            options = [x.strip() for x in options_str.split(",") if x.strip()]
                            new_attrs[k] = {"type": "select", "options": options}
                except: pass
            attr_var["data"] = new_attrs
            btn.configure(text=f"属性({len(new_attrs)})")
            win.destroy()
        
        ctk.CTkButton(btn_frame, text="✔ 完了", command=apply, fg_color="#27ae60").pack(side="right", padx=10)

    def add_cat_row_empty(self):
        self.add_cat_row("", "", "", "item_select", True, "")
        self.after(10, lambda: self.scroll_cat._parent_canvas.yview_moveto(1.0))

    def _master_object_options(self):
        labels = ["(なし)"]
        l2i = {"(なし)": ""}
        seen = set()
        rows = list(self.attr_rows)
        if self._attr_split_mode:
            rows.extend(self.route_attr_rows)
        for r in rows:
            nj = (r.get("name_jp") and r["name_jp"].get() or "").strip()
            ne = (r.get("name_en") and r["name_en"].get() or "").strip()
            oid = (r.get("obj_key") or "").strip() or self.generate_id_from_en(ne)
            if not oid or oid in seen:
                continue
            seen.add(oid)
            lab = f"{(nj or oid)} ({oid})"
            labels.append(lab)
            l2i[lab] = oid
        return labels, l2i

    def _infer_object_attr_id_from_cat_info(self, cat_info):
        if not isinstance(cat_info, dict):
            return ""
        oid = (cat_info.get("object_attr_id") or "").strip()
        if oid:
            return oid
        # 旧データ互換: object_ids が 1 件だけなら採用する。
        # type から推測すると意図しないオブジェクトに固定されるため行わない。
        raw_oids = cat_info.get("object_ids")
        if isinstance(raw_oids, list):
            candidates = []
            for x in raw_oids:
                s = str(x or "").strip()
                if s and s not in candidates:
                    candidates.append(s)
            if len(candidates) == 1:
                return candidates[0]
        return ""

    def _refresh_category_object_combo_values(self):
        labels, l2i = self._master_object_options()
        for r in self.cat_rows:
            cmb = r.get("obj_group")
            if not cmb:
                continue
            prev_map = r.get("_obj_label_to_id") or {}
            cur_lab = (cmb.get() or "").strip()
            cur_oid = prev_map.get(cur_lab, "")
            cmb.configure(values=labels)
            r["_obj_label_to_id"] = dict(l2i)
            if cur_oid:
                pick = next((lb for lb, oid in l2i.items() if oid == cur_oid), "(なし)")
                cmb.set(pick)
            elif cur_lab in labels:
                cmb.set(cur_lab)
            else:
                cmb.set("(なし)")

    def add_cat_row(self, name_jp, name_en, object_attr_id="", input_type="item_select", show_qty=True, cat_id=""):
        f = ctk.CTkFrame(self.scroll_cat, fg_color="transparent")
        f.pack(fill="x", pady=2)
        rw = 0
        self._place_master_row_reorder_grid(f, self.cat_rows, rw, 0)
        s = getattr(self, "_master_col_scale", 1.0)
        obj_labels, obj_l2i = self._master_object_options()
        cmb_obj = ctk.CTkComboBox(f, values=obj_labels, width=max(88, int(164 * s)))
        sel_lab = next((lb for lb, oid in obj_l2i.items() if oid == (object_attr_id or "").strip()), "(なし)")
        cmb_obj.set(sel_lab if sel_lab in obj_labels else "(なし)")
        cmb_obj.grid(row=rw, column=1, sticky="w", padx=4, pady=2)
        e_name_jp = ctk.CTkEntry(f, width=max(64, int(148 * s)))
        e_name_jp.insert(0, name_jp)
        e_name_jp.grid(row=rw, column=2, sticky="ew", padx=4, pady=2)
        e_name_en = ctk.CTkEntry(f, width=max(64, int(148 * s)))
        e_name_en.insert(0, name_en)
        e_name_en.grid(row=rw, column=3, sticky="ew", padx=4, pady=2)
        e_id = ctk.CTkEntry(f, width=max(56, int(118 * s)), placeholder_text="ID")
        e_id.insert(0, cat_id)
        e_id.grid(row=rw, column=4, sticky="ew", padx=4, pady=2)
        last_auto_id = {"value": ""}

        def on_en_change(_e=None):
            cur_id = (e_id.get() or "").strip()
            auto_now = self.generate_id_from_en(e_name_en.get().strip())
            # IDが空、または直前の自動生成値のままなら EN 変更に追従させる。
            can_follow = (cur_id == "") or (last_auto_id["value"] and cur_id == last_auto_id["value"])
            if can_follow:
                e_id.delete(0, "end")
                if auto_now:
                    e_id.insert(0, auto_now)
                last_auto_id["value"] = auto_now
            elif cur_id:
                # 手入力IDを検知したら自動追従を止める。
                last_auto_id["value"] = ""

        if not (cat_id or "").strip():
            on_en_change()
        e_name_en.bind("<KeyRelease>", on_en_change)
        input_type_options = ["item_select", "qty_only"]
        input_type_names = {"item_select": "アイテム選択", "qty_only": "数量のみ"}
        cmb_input = ctk.CTkComboBox(f, values=[input_type_names[t] for t in input_type_options], width=max(88, int(104 * s)))
        cmb_input.set(input_type_names.get(input_type, "アイテム選択"))
        cmb_input.grid(row=rw, column=5, sticky="w", padx=4, pady=2)
        show_qty_var = tk.BooleanVar(value=show_qty)
        chk_qty = ctk.CTkCheckBox(f, text="", variable=show_qty_var, width=30)
        chk_qty.grid(row=rw, column=6, sticky="w", padx=4, pady=2)
        eff_cid = (cat_id or "").strip()
        pin_marker = self._load_pin_marker_for_category_id(eff_cid)
        f_pin = ctk.CTkFrame(f, fg_color="transparent")
        f_pin.grid(row=rw, column=7, sticky="w", padx=4, pady=2)
        lbl_pin_preview = ctk.CTkLabel(
            f_pin, text="—", width=22, height=22, fg_color="transparent", corner_radius=0, text_color="#bdc3c7"
        )
        lbl_pin_preview.pack(side="left", padx=1)
        pin_swatch_icon = ctk.CTkFrame(f_pin, width=12, height=12, corner_radius=2, fg_color=pin_marker["icon_color"])
        pin_swatch_icon.pack(side="left", padx=2)
        pin_swatch_bg = ctk.CTkFrame(f_pin, width=12, height=12, corner_radius=2, fg_color=pin_marker["background_color"])
        pin_swatch_bg.pack(side="left", padx=2)
        lbl_pin_mode = ctk.CTkLabel(
            f_pin, text=self._pin_marker_mode_label_text(pin_marker), font=("Meiryo", 9), text_color="#95a5a6"
        )
        lbl_pin_mode.pack(side="left", padx=(4, 2))
        row_rec = {
            "frame": f,
            "name_jp": e_name_jp,
            "name_en": e_name_en,
            "id": e_id,
            "obj_group": cmb_obj,
            "input_type": cmb_input,
            "show_qty": show_qty_var,
            "pin_marker": pin_marker,
            "lbl_pin_preview": lbl_pin_preview,
            "pin_swatch_icon": pin_swatch_icon,
            "pin_swatch_bg": pin_swatch_bg,
            "lbl_pin_mode": lbl_pin_mode,
            "_obj_label_to_id": obj_l2i,
            "_pin_preview_holder": [],
        }
        ctk.CTkButton(
            f_pin, text="マーカー", width=68, height=26, fg_color="#2980b9",
            command=lambda rr=row_rec: self._open_pin_marker_dialog(
                rr, "マーカー（カテゴリ / pin_marker_by_category_id）",
            ),
        ).pack(side="left", padx=4)
        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", command=lambda: self.delete_row(f, self.cat_rows)).grid(
            row=rw, column=8, sticky="e", padx=4, pady=2
        )
        self._configure_cat_table_columns(f)
        self.cat_rows.append(row_rec)
        self._refresh_pin_marker_row_preview(row_rec)
        self._refresh_item_group_combo_values()
        e_name_jp.bind("<KeyRelease>", lambda e: self._refresh_item_group_combo_values())
        e_id.bind("<KeyRelease>", lambda e: self._refresh_item_group_combo_values())

    def add_item_row_empty(self):
        self.add_item_row("", "", "", "", {})
        self.after(10, lambda: self.scroll_item._parent_canvas.yview_moveto(1.0))

    def _master_item_group_values(self):
        vals = []
        seen = set()
        # 仕様: アイテムの対応カテゴリはカテゴリ（JP名）一覧
        for r in self.cat_rows:
            jp = (r.get("name_jp") and r["name_jp"].get() or "").strip()
            if jp and jp not in seen:
                seen.add(jp)
                vals.append(jp)
        # カテゴリタブ未初期化や空時の保険
        if not vals:
            for nm in (self.config.get("category_master") or {}).keys():
                s = str(nm or "").strip()
                if s and s not in seen:
                    seen.add(s)
                    vals.append(s)
        return vals or ["(なし)"]

    def _refresh_item_group_combo_values(self):
        vals = self._master_item_group_values()
        for r in self.item_rows:
            cmb = r.get("grp")
            if not cmb:
                continue
            cur = (cmb.get() or "").strip()
            cmb.configure(values=vals)
            if cur and cur in vals:
                cmb.set(cur)
            elif vals:
                cmb.set(vals[0])

    def _inherit_marker_from_category_to_item(self, row_rec, group_name):
        cm = self.config.get("category_master", {}) or {}
        cid = ""
        if group_name and isinstance(cm.get(group_name), dict):
            cid = (cm[group_name].get("id") or "").strip()
        if not cid:
            for cr in self.cat_rows:
                n = (cr.get("name_jp") and cr["name_jp"].get() or "").strip()
                if n == group_name:
                    cid = (cr.get("id") and cr["id"].get() or "").strip()
                    break
        if not cid:
            return
        cat_pm = self._load_pin_marker_for_category_id(cid)
        row_rec["pin_marker"] = {
            "svg_icon_id": (cat_pm.get("svg_icon_id") or "").strip(),
            "svg_icon_scope": (cat_pm.get("svg_icon_scope") or "common").strip() or "common",
            "icon_color": self._hex6_or_default(cat_pm.get("icon_color"), "#ffffff"),
            "background_color": self._hex6_or_default(cat_pm.get("background_color"), "#95a5a6"),
            "display_style": "icon_only" if normalize_marker_display_style(cat_pm.get("display_style")) == "icon_only" else "standard",
            "_display_style_explicit": True,
        }
        self._refresh_pin_marker_row_preview(row_rec)

    def add_item_row(self, grp, i_id, n_jp, n_en, attrs):
        f = ctk.CTkFrame(self.scroll_item, fg_color="transparent")
        f.pack(fill="x", pady=2)
        rw = 0
        self._place_master_row_reorder_grid(f, self.item_rows, rw, 0)
        s = getattr(self, "_master_col_scale", 1.0)

        current_groups = self._master_item_group_values()
        if grp and grp not in current_groups:
            current_groups = current_groups + [grp]
        e_grp = ctk.CTkComboBox(f, values=current_groups, width=max(72, int(132 * s)))
        e_grp.set(grp)
        e_grp.grid(row=rw, column=1, sticky="w", padx=4, pady=2)

        e_id = ctk.CTkEntry(f, width=max(64, int(128 * s)))
        e_id.insert(0, i_id)
        e_id.grid(row=rw, column=2, sticky="ew", padx=4, pady=2)
        e_jp = ctk.CTkEntry(f, width=max(72, int(172 * s)))
        e_jp.insert(0, n_jp)
        e_jp.grid(row=rw, column=3, sticky="ew", padx=4, pady=2)
        e_en = ctk.CTkEntry(f, width=max(72, int(172 * s)))
        e_en.insert(0, n_en)
        e_en.grid(row=rw, column=4, sticky="ew", padx=4, pady=2)
        last_auto_id = {"value": ""}

        def on_en_change(_e=None):
            cur_id = (e_id.get() or "").strip()
            auto_now = self.generate_id_from_en(e_en.get().strip())
            # IDが空、または直前の自動生成値のままなら EN 変更に追従させる。
            can_follow = (cur_id == "") or (last_auto_id["value"] and cur_id == last_auto_id["value"])
            if can_follow:
                e_id.delete(0, "end")
                if auto_now:
                    e_id.insert(0, auto_now)
                last_auto_id["value"] = auto_now
            elif cur_id:
                # 手入力IDを検知したら自動追従を止める。
                last_auto_id["value"] = ""

        if not (i_id or "").strip():
            on_en_change()
        e_en.bind("<KeyRelease>", on_en_change)

        attr_var = {"data": attrs}
        btn_attr = ctk.CTkButton(f, text=f"属性 ({len(attrs)})", width=80, fg_color="#8e44ad",
                                 command=lambda: self.edit_attributes(attr_var, btn_attr))
        btn_attr.grid(row=rw, column=5, sticky="w", padx=4, pady=2)

        pin_marker = self._load_pin_marker_for_item_id((i_id or "").strip())
        f_pin = ctk.CTkFrame(f, fg_color="transparent")
        f_pin.grid(row=rw, column=6, sticky="w", padx=4, pady=2)
        lbl_pin_preview = ctk.CTkLabel(
            f_pin, text="—", width=22, height=22, fg_color="transparent", corner_radius=0, text_color="#bdc3c7"
        )
        lbl_pin_preview.pack(side="left", padx=1)
        pin_swatch_icon = ctk.CTkFrame(f_pin, width=12, height=12, corner_radius=2, fg_color=pin_marker["icon_color"])
        pin_swatch_icon.pack(side="left", padx=2)
        pin_swatch_bg = ctk.CTkFrame(f_pin, width=12, height=12, corner_radius=2, fg_color=pin_marker["background_color"])
        pin_swatch_bg.pack(side="left", padx=2)
        lbl_pin_mode = ctk.CTkLabel(
            f_pin, text=self._pin_marker_mode_label_text(pin_marker), font=("Meiryo", 9), text_color="#95a5a6"
        )
        lbl_pin_mode.pack(side="left", padx=(4, 2))
        row_rec = {
            "frame": f,
            "grp": e_grp,
            "id": e_id,
            "jp": e_jp,
            "en": e_en,
            "attr_var": attr_var,
            "pin_marker": pin_marker,
            "lbl_pin_preview": lbl_pin_preview,
            "pin_swatch_icon": pin_swatch_icon,
            "pin_swatch_bg": pin_swatch_bg,
            "lbl_pin_mode": lbl_pin_mode,
            "_pin_preview_holder": [],
            "_last_group_name": (grp or "").strip(),
        }
        ctk.CTkButton(
            f_pin, text="マーカー", width=68, height=26, fg_color="#2980b9",
            command=lambda rr=row_rec: self._open_pin_marker_dialog(
                rr, "マーカー（アイテム / pin_marker_by_item_id）",
            ),
        ).pack(side="left", padx=4)

        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b",
                      command=lambda: self.delete_row(f, self.item_rows)).grid(
            row=rw, column=7, sticky="e", padx=4, pady=2
        )

        self._configure_item_table_columns(f)
        self.item_rows.append(row_rec)
        self._refresh_pin_marker_row_preview(row_rec)
        self._refresh_item_group_combo_values()

        def on_group_changed(v, rr=row_rec):
            new_grp = (v or "").strip()
            old_grp = (rr.get("_last_group_name") or "").strip()
            rr["_last_group_name"] = new_grp
            if not new_grp or new_grp == old_grp:
                return
            if messagebox.askyesno(
                "対応カテゴリ変更",
                "選択した対応カテゴリのマーカー設定をこのアイテムに引き継ぎますか？",
                parent=self,
            ):
                self._inherit_marker_from_category_to_item(rr, new_grp)

        e_grp.configure(command=on_group_changed)

    def edit_attributes(self, attr_var, btn):
        win = ctk.CTkToplevel(self)
        win.title("属性編集")
        win.geometry("480x520")
        win.attributes("-topmost", True)
        current_data = attr_var["data"] or {}
        edit_rows = []
        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        def add_row(k="", attr_type="number", val_str="", options_str=""):
            rf = ctk.CTkFrame(scroll, fg_color="transparent")
            rf.pack(fill="x", pady=4)
            ek = ctk.CTkEntry(rf, width=100, placeholder_text="属性名(例: ポイント)")
            ek.insert(0, k)
            ek.pack(side="left", padx=2)
            type_var = tk.StringVar(value="数値" if attr_type == "number" else "選択")
            cmb_type = ctk.CTkComboBox(rf, values=["数値", "選択"], variable=type_var, width=70)
            cmb_type.pack(side="left", padx=2)
            ev = ctk.CTkEntry(rf, width=180, placeholder_text="数値または選択肢(カンマ区切り)")
            if attr_type == "number":
                ev.insert(0, str(val_str) if val_str is not None else "")
            else:
                ev.insert(0, options_str)
            ev.pack(side="left", padx=2)
            ctk.CTkButton(rf, text="x", width=30, fg_color="#c0392b", command=lambda: rf.destroy()).pack(side="left")
            edit_rows.append({"frame": rf, "key": ek, "type_var": type_var, "val": ev})

        # 既存データを新形式で解釈して行を追加（fixed=マスタ登録値も数値として表示）
        for k, v in current_data.items():
            if isinstance(v, dict) and "type" in v:
                t = v.get("type", "number")
                if t in ("number", "fixed"):
                    add_row(k=k, attr_type="number", val_str=v.get("value", ""), options_str="")
                else:
                    opts = v.get("options", [])
                    add_row(k=k, attr_type="select", val_str="", options_str=",".join(opts) if isinstance(opts, list) else str(opts))
            elif isinstance(v, list):
                add_row(k=k, attr_type="select", val_str="", options_str=",".join(str(x) for x in v))
            else:
                add_row(k=k, attr_type="number", val_str=v if v is not None else "", options_str="")
        ctk.CTkButton(win, text="＋ 属性追加", command=lambda: add_row()).pack(pady=5)

        def apply():
            new_attrs = {}
            for r in edit_rows:
                try:
                    k = r["key"].get().strip()
                    if not k:
                        continue
                    is_number = r["type_var"].get().strip() == "数値"
                    v_str = r["val"].get().strip()
                    if is_number:
                        # ピン編集では固定表示とするため fixed でマスタ登録
                        new_attrs[k] = {"type": "fixed", "value": v_str if v_str else ""}
                    else:
                        opts = [x.strip() for x in v_str.split(",") if x.strip()]
                        new_attrs[k] = {"type": "select", "options": opts}
                except Exception:
                    pass
            attr_var["data"] = new_attrs
            btn.configure(text=f"属性 ({len(new_attrs)})")
            win.destroy()
        ctk.CTkButton(win, text="完了", command=apply, fg_color="#27ae60").pack(pady=10)

    # ★★★ 日英同時読み込み対応インポート (完全修正版) ★★★
    def import_from_csv(self):
        if not messagebox.askyesno("確認", "master_data.csv からアイテム情報を抽出しますか？\n(既存リストにない項目を追加します)"):
            return
            
        csv_path = os.path.join(self.parent.game_path, self.config.get("save_file", "master_data.csv"))
        if not os.path.exists(csv_path):
            messagebox.showerror("エラー", f"CSVファイルが見つかりません:\n{csv_path}")
            return

        added_count = 0
        # 既存の名前リスト（重複回避用）
        existing_names = set(r["jp"].get() for r in self.item_rows)

        rows = []
        # 文字コード対応
        for enc in ['utf-8-sig', 'utf-8', 'cp932']:
            try:
                with open(csv_path, "r", encoding=enc) as f:
                    rows = list(csv.DictReader(f))
                break 
            except Exception:
                continue

        if not rows:
            messagebox.showerror("エラー", "CSVファイルの読み込みに失敗しました")
            return

        for row in rows:
            memo_jp = str(row.get("memo_jp", ""))
            memo_en = str(row.get("memo_en", ""))
            
            # 日英を並行してパース
            lines_jp = re.split(r'<br>|\n|\\n', memo_jp)
            lines_en = re.split(r'<br>|\n|\\n', memo_en)
            
            max_len = max(len(lines_jp), len(lines_en))
            
            for i in range(max_len):
                line_jp = lines_jp[i].strip() if i < len(lines_jp) else ""
                line_en = lines_en[i].strip() if i < len(lines_en) else ""
                
                if not line_jp: continue
                
                grp, name_jp, name_en_val = "その他", line_jp, line_en
                
                # 日本語パース
                match_colon_jp = re.match(r'^([^：:]+)[：:](.+)$', line_jp)
                # ★修正: 第2引数の '' を削除しました
                match_count_jp = re.match(r'^(.+)[（\(].+[）\)]$', line_jp)
                
                if match_colon_jp:
                    grp = match_colon_jp.group(1).strip()
                    name_jp = match_colon_jp.group(2).strip()
                elif match_count_jp:
                    name_jp = match_count_jp.group(1).strip()
                
                # 英語パース
                if line_en:
                    match_colon_en = re.match(r'^([^：:]+)[：:](.+)$', line_en)
                    # ★修正: 第2引数の '' を削除しました
                    match_count_en = re.match(r'^(.+)[（\(].+[）\)]$', line_en)
                    
                    if match_colon_en:
                        name_en_val = match_colon_en.group(2).strip()
                    elif match_count_en:
                        name_en_val = match_count_en.group(1).strip()
                
                # 重複チェック & 追加
                if name_jp in existing_names: continue
                
                safe_id = f"ITEM_{abs(hash(name_jp)) % 100000:05d}"
                
                self.add_item_row(grp, safe_id, name_jp, name_en_val, {})
                existing_names.add(name_jp)
                added_count += 1
        
        messagebox.showinfo("完了", f"{added_count} 個のアイテムを新規追加しました。")

    def delete_row(self, frame, list_ref):
        frame.destroy()
        for i in range(len(list_ref)-1, -1, -1):
            if list_ref[i]["frame"] == frame: del list_ref[i]
        if list_ref in (self.attr_rows, self.route_attr_rows):
            self._refresh_category_object_combo_values()
        if list_ref is self.cat_rows:
            self._refresh_item_group_combo_values()

    def _collect_attr_rows_dict(self, rows):
        """UI 行から attr_mapping 用の dict を構築（キー重複は上書き）。"""
        out = {}
        for r in rows:
            n_jp_raw = r["name_jp"].get().strip()
            n_en_raw = r["name_en"].get().strip()
            key = self._effective_object_key_from_row(r)
            attrs = r.get("attr_var", {}).get("data", {})
            if not (n_jp_raw or n_en_raw or key or attrs):
                continue
            if not key:
                continue
            n_jp, n_en = self._normalize_bilingual_names(n_jp_raw, n_en_raw, key)
            obj_type = r.get("type_stored", "loot")
            if obj_type not in self.object_types:
                obj_type = "loot"
            use_slots = True
            if r.get("use_slots_var") is not None:
                try:
                    use_slots = bool(r["use_slots_var"].get())
                except Exception:
                    use_slots = True
            out[key] = {
                "name_jp": n_jp,
                "name_en": n_en,
                "type": obj_type,
                "attributes": attrs,
                "use_category_slots": use_slots,
            }
        return out

    def _find_duplicate_category_ids_for_save(self):
        """保存対象カテゴリ行から、重複している cat_id を列挙。"""
        counts = {}
        for r in self.cat_rows:
            n_jp_raw = r["name_jp"].get().strip()
            n_en_raw = r["name_en"].get().strip()
            cid = (self._effective_category_id_from_row(r) or "").strip()
            obj_lab = (r["obj_group"].get() or "").strip()
            if not (n_jp_raw or n_en_raw or cid or obj_lab):
                continue
            if not cid:
                continue
            counts[cid] = counts.get(cid, 0) + 1
        return sorted([k for k, c in counts.items() if c > 1], key=lambda s: s.lower())

    def _find_duplicate_item_ids_for_save(self):
        """保存対象アイテム行から、重複している item_id を列挙（全カテゴリ横断）。"""
        counts = {}
        for r in self.item_rows:
            g_raw = r["grp"].get().strip()
            i_raw = (r["id"].get().strip() if r.get("id") else "")
            nj_raw = r["jp"].get().strip()
            ne_raw = r["en"].get().strip()
            attrs = r["attr_var"]["data"]
            if not (g_raw or i_raw or nj_raw or ne_raw or attrs):
                continue
            iid = (self._effective_item_id_from_row(r) or "").strip()
            if not iid:
                continue
            counts[iid] = counts.get(iid, 0) + 1
        return sorted([k for k, c in counts.items() if c > 1], key=lambda s: s.lower())

    def save_settings(self):
        # 種類表示名→ID変換マップ
        if self._attr_split_mode:
            primary = self._collect_attr_rows_dict(self.attr_rows)
            route = self._collect_attr_rows_dict(self.route_attr_rows)
            overlap = set(primary.keys()) & set(route.keys())
            if overlap:
                messagebox.showerror(
                    "保存エラー",
                    "「1. オブジェクト」と「ルート参照」で同じ ID が使われています:\n"
                    + ", ".join(sorted(overlap)),
                    parent=self,
                )
                return
            new_attr_mapping = {**route, **primary}
            ordered_ids = []
            for r in self.attr_rows:
                n_jp = r["name_jp"].get().strip()
                n_en = r["name_en"].get().strip()
                key = self._effective_object_key_from_row(r)
                if not (n_jp or n_en or key):
                    continue
                if key:
                    ordered_ids.append(key)
            self.config["map_object_attr_ids"] = ordered_ids
        else:
            new_attr_mapping = self._collect_attr_rows_dict(self.attr_rows)

        dup_cat_ids = self._find_duplicate_category_ids_for_save()
        dup_item_ids = self._find_duplicate_item_ids_for_save()
        if dup_cat_ids or dup_item_ids:
            parts = ["ID 重複のため保存を中止しました。手動で修正してください。"]
            if dup_cat_ids:
                parts.append("カテゴリ ID 重複:\n- " + "\n- ".join(dup_cat_ids))
            if dup_item_ids:
                parts.append("アイテム ID 重複:\n- " + "\n- ".join(dup_item_ids))
            messagebox.showerror("保存エラー", "\n\n".join(parts), parent=self)
            try:
                if dup_cat_ids:
                    self.tabview.set("2. カテゴリ")
                else:
                    self.tabview.set("3. アイテム")
            except Exception:
                pass
            return

        self.config["attr_mapping"] = new_attr_mapping
        # 後方互換性のためcat_mappingも設定
        self.config["cat_mapping"] = {
            k: (str(v.get("name_jp") or v.get("name_en") or k).strip() or k)
            for k, v in new_attr_mapping.items()
        }

        rows_for_pin_markers = list(self.attr_rows)
        if self._attr_split_mode:
            rows_for_pin_markers.extend(self.route_attr_rows)
        self.config["pin_marker_by_attribute"] = self._build_pin_marker_by_attribute_from_rows(
            rows_for_pin_markers,
            self.config.get("pin_marker_by_attribute"),
        )
        self.config["pin_marker_by_category_id"] = self._build_pin_marker_by_category_from_rows(
            self.cat_rows,
            self.config.get("pin_marker_by_category_id"),
        )
        self.config["pin_marker_by_item_id"] = self._build_pin_marker_by_item_from_rows(
            self.item_rows,
            self.config.get("pin_marker_by_item_id"),
        )

        # カテゴリマスタ（id + JP/EN + type + input_type + show_qty）
        # object_ids / poi_type / attributes 等、UI に無いキーは従来値をマージして維持する
        input_type_name_to_id = {"アイテム選択": "item_select", "数量のみ": "qty_only"}
        old_cm = self.config.get("category_master", {}) or {}
        new_category_master = {}
        for r in self.cat_rows:
            n_jp_raw = r["name_jp"].get().strip()
            n_en_raw = r["name_en"].get().strip()
            cid = self._effective_category_id_from_row(r)
            obj_lab = (r["obj_group"].get() or "").strip()
            obj_map = r.get("_obj_label_to_id") or {}
            object_attr_id = (obj_map.get(obj_lab) or "").strip()
            cat_type = "loot"
            if object_attr_id:
                oi = new_attr_mapping.get(object_attr_id) or self.attr_mapping.get(object_attr_id)
                if isinstance(oi, dict):
                    cat_type = (oi.get("type") or "loot")
            input_display = r["input_type"].get()
            input_type = input_type_name_to_id.get(input_display, "item_select")
            show_qty = r["show_qty"].get()
            if not (n_jp_raw or n_en_raw or cid or object_attr_id):
                continue
            if not cid:
                cid = self.parent._generate_cat_id(n_en_raw or n_jp_raw or "cat")
            n_jp, n_en = self._normalize_bilingual_names(n_jp_raw, n_en_raw, cid)
            cm_key = n_jp or n_en or cid
            prev = (
                old_cm.get(cm_key)
                or old_cm.get(n_jp_raw)
                or old_cm.get(n_en_raw)
                or {}
            )
            prev = dict(prev) if isinstance(prev, dict) else {}
            # 現行は object_attr_id を単一の紐づけ元として扱う。
            # 旧互換キー object_ids は保存時に整理して混在を防ぐ。
            prev.pop("object_ids", None)
            prev.update({
                "id": cid,
                "name_jp": n_jp,
                "name_en": n_en,
                "type": cat_type,
                "object_attr_id": object_attr_id,
                "input_type": input_type,
                "show_qty": show_qty,
            })
            new_category_master[cm_key] = prev
        self.config["category_master"] = new_category_master
        # 後方互換性のためcategory_listも設定
        self.config["category_list"] = list(new_category_master.keys())

        # アイテムマスタ（UI 未編集の拡張フィールドは従来値をマージ）
        old_im = self.config.get("item_master", {}) or {}
        new_master = {}
        for r in self.item_rows:
            g_raw = r["grp"].get().strip()
            i_raw = (r["id"].get().strip() if r.get("id") else "")
            nj_raw = r["jp"].get().strip()
            ne_raw = r["en"].get().strip()
            attrs = r["attr_var"]["data"]
            if not (g_raw or i_raw or nj_raw or ne_raw or attrs):
                continue
            g = g_raw or "その他"
            i = self._effective_item_id_from_row(r)
            if not i:
                i = self.parent._generate_item_id(nj_raw or ne_raw or g)
            nj, ne = self._normalize_bilingual_names(nj_raw, ne_raw, i)
            if g not in new_master:
                new_master[g] = {}
            prev_it = (old_im.get(g) or {}).get(i, {})
            prev_it = dict(prev_it) if isinstance(prev_it, dict) else {}
            prev_it.update({"name_jp": nj, "name_en": ne, "attributes": attrs})
            new_master[g][i] = prev_it

        self.config["item_master"] = new_master

        category_special_rules_builder.sync_category_special_rules_from_master(self.config)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", "設定を保存しました。画面を更新します。", parent=self)
            self.parent.reload_config()
            self.destroy()
        except Exception as e:
            messagebox.showerror("エラー", f"保存失敗:\n{e}", parent=self)


# ==========================================
# ピン表示フィルタ（メニューから開く）
# ==========================================
class PinFilterWindow(ctk.CTkToplevel):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        editor._pin_filter_window = self
        self.title("ピン表示フィルタ")
        self.geometry("560x600")
        self.transient(editor)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.CTkLabel(
            self,
            text="チェックを外した項目に「該当する」ピンだけを隠します。"
                 "\n・オブジェクト … ピンのオブジェクト種別"
                 "\n・カテゴリ … 中身スロットのカテゴリ（いずれか一致すれば表示）"
                 "\n・アイテム … 中身スロットのアイテム（いずれか一致すれば表示）"
                 "\n中身スロットが無いピンは、カテゴリ・アイテム条件では隠しません。",
            font=("Meiryo", 10),
            text_color="#95a5a6",
            justify="left",
        ).pack(anchor="w", padx=12, pady=(12, 6))

        ctk.CTkCheckBox(
            self,
            text="⚠️ 未完成のみ表示（名前と中身が両方あるピンを隠す）",
            variable=editor.show_incomplete_only,
            command=editor.refresh_map,
            text_color="#e74c3c",
        ).pack(anchor="w", padx=12, pady=4)

        tv = ctk.CTkTabview(self, width=520, height=430)
        tv.pack(fill="both", expand=True, padx=10, pady=8)
        t_obj = tv.add("オブジェクト")
        t_cat = tv.add("カテゴリ")
        t_item = tv.add("アイテム")

        def fill_tab(parent, row_defs):
            f_btn = ctk.CTkFrame(parent, fg_color="transparent")
            f_btn.pack(fill="x", pady=(0, 6))

            def all_on():
                for _, var in row_defs:
                    var.set(True)
                editor.refresh_map()

            def all_off():
                for _, var in row_defs:
                    var.set(False)
                editor.refresh_map()

            ctk.CTkButton(f_btn, text="すべてオン", width=110, command=all_on, fg_color="#27ae60").pack(side="left", padx=4)
            ctk.CTkButton(f_btn, text="すべてオフ", width=110, command=all_off, fg_color="#7f8c8d").pack(side="left", padx=4)
            scr = ctk.CTkScrollableFrame(parent, fg_color="transparent")
            scr.pack(fill="both", expand=True)
            for label, var in row_defs:
                ctk.CTkCheckBox(scr, text=label, variable=var, command=editor.refresh_map).pack(anchor="w", padx=8, pady=2)

        editor._rebuild_pin_cat_mapping()
        o_rows = []
        for aid in editor.cat_mapping.keys():
            var = editor.pin_filter_object_vars.get(aid)
            if var:
                disp = editor._attr_display_name(aid)
                o_rows.append((f"{disp}  ({aid})", var))
        fill_tab(t_obj, o_rows)

        c_rows = []
        for cat_name, info in sorted((editor.category_master or {}).items(), key=lambda x: (x[0] or "")):
            if not isinstance(info, dict):
                continue
            cid = (info.get("id") or "").strip() or cat_name
            var = editor.pin_filter_cat_vars.get(cid)
            if var:
                nj = (info.get("name_jp") or cat_name or cid).strip()
                c_rows.append((f"{nj}  [{cid}]", var))
        fill_tab(t_cat, c_rows)

        i_rows = []
        for grp, items in sorted((editor.item_master or {}).items(), key=lambda x: (x[0] or "")):
            if not isinstance(items, dict):
                continue
            for iid, info in sorted(items.items(), key=lambda x: (x[0] or "")):
                key = f"{grp}\t{iid}"
                var = editor.pin_filter_item_vars.get(key)
                if var:
                    nj = (info.get("name_jp", iid) if isinstance(info, dict) else iid) or iid
                    i_rows.append((f"{grp} / {nj}  ({iid})", var))
        fill_tab(t_item, i_rows)

        ctk.CTkButton(self, text="閉じる", command=self._on_close, fg_color="#34495e", width=120).pack(pady=(4, 12))

    def _on_close(self):
        try:
            self.editor._pin_filter_window = None
        except Exception:
            pass
        self.destroy()


# ==========================================
# WordPress 記事ピッカー（リンク候補）
# ==========================================
class WpRestGuidePickerWindow(ctk.CTkToplevel):
    def __init__(self, parent, sources, rows_prefill=None):
        super().__init__(parent)
        self.title("WordPress 記事一覧（リンク候補）")
        self.geometry("920x580")
        self._sources = sources or []
        self._rows = list(rows_prefill or [])
        self._filtered = []
        self._apply_to = tk.StringVar(value="both")

        f_top = ctk.CTkFrame(self, fg_color="transparent")
        f_top.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(f_top, text="検索:", width=50, anchor="w").pack(side="left")
        self.ent_search = ctk.CTkEntry(f_top, placeholder_text="slug / タイトル")
        self.ent_search.pack(side="left", fill="x", expand=True, padx=6)
        self.ent_search.bind("<KeyRelease>", lambda e: self._apply_filter())

        f_rad = ctk.CTkFrame(self, fg_color="transparent")
        f_rad.pack(fill="x", padx=10, pady=4)
        ctk.CTkRadioButton(f_rad, text="JP/EN 両方反映", variable=self._apply_to, value="both").pack(side="left", padx=6)
        ctk.CTkRadioButton(f_rad, text="JP のみ", variable=self._apply_to, value="jp").pack(side="left", padx=6)
        ctk.CTkRadioButton(f_rad, text="EN のみ", variable=self._apply_to, value="en").pack(side="left", padx=6)

        self.lbl_status = ctk.CTkLabel(self, text="", font=("Meiryo", 10), text_color="#f39c12")
        self.lbl_status.pack(anchor="w", padx=12)

        list_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        list_frame.pack(fill="both", expand=True, padx=10, pady=6)
        sb = tk.Scrollbar(list_frame)
        self.listbox = tk.Listbox(
            list_frame, font=("Meiryo", 10), bg="#2b2b2b", fg="#ecf0f1",
            selectbackground="#3498db", height=18, yscrollcommand=sb.set
        )
        sb.config(command=self.listbox.yview)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        f_btn = ctk.CTkFrame(self, fg_color="transparent")
        f_btn.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(f_btn, text="選択を反映", command=self._do_apply, fg_color="#27ae60").pack(side="left", padx=4)
        ctk.CTkButton(f_btn, text="閉じる", command=self.destroy, fg_color="#7f8c8d").pack(side="left", padx=4)
        self.listbox.bind("<Double-Button-1>", lambda e: self._do_apply())

        if self._rows:
            self._apply_filter()
            self.lbl_status.configure(text=f"候補 {len(self._rows)} 件")
        elif self._sources:
            self.lbl_status.configure(text="記事一覧を取得しています…")
            threading.Thread(target=self._fetch_thread, daemon=True).start()
        else:
            self.lbl_status.configure(text="config に wp_rest_guide_sources がありません。")

    def _fetch_thread(self):
        rows, err = wp_rest_guide.collect_paired_from_sources(self._sources)

        def done():
            self._rows = rows
            self._apply_filter()
            if err:
                self.lbl_status.configure(text=err)
            else:
                self.lbl_status.configure(text=f"候補 {len(self._rows)} 件")

        self.after(0, done)

    def _apply_filter(self):
        q = (self.ent_search.get() or "").strip().lower()
        self._filtered = []
        self.listbox.delete(0, tk.END)
        for r in self._rows:
            slug = (r.get("slug") or "").lower()
            tj = (r.get("title_jp") or "").lower()
            te = (r.get("title_en") or "").lower()
            if q and q not in slug and q not in tj and q not in te:
                continue
            self._filtered.append(r)
            line = f"{r.get('slug', '')} | {(r.get('title_jp') or '')[:48]} | {(r.get('title_en') or '')[:48]}"
            self.listbox.insert(tk.END, line[:240])

    def _do_apply(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("選択", "行を選んでください。", parent=self)
            return
        r = self._filtered[sel[0]]
        mode = self._apply_to.get()
        p = self.master
        if mode in ("both", "jp") and (r.get("url_jp") or "").strip():
            p.ent_link_jp.delete(0, "end")
            p.ent_link_jp.insert(0, (r.get("url_jp") or "").strip())
        if mode in ("both", "en") and (r.get("url_en") or "").strip():
            p.ent_link_en.delete(0, "end")
            p.ent_link_en.insert(0, (r.get("url_en") or "").strip())
        if hasattr(p, "mark_dirty"):
            p.mark_dirty()
        messagebox.showinfo("反映", "リンク URL を入力欄に入れました。", parent=self)


# ==========================================
# サイト表示プリセット管理（view-presets.json）
# ==========================================
class ViewPresetWindow(ctk.CTkToplevel):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.title("サイト表示プリセット管理")
        self.geometry("980x780")
        self.transient(editor)
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.presets_path = os.path.join(editor.game_path, "view-presets.json")
        self.data = {"presets": {}}
        self.row_objs = []
        self.row_cats = []
        self.row_items = []
        self._loading = False

        self._load_file()
        self._build_sources()
        self._build_ui()
        self._refresh_preset_combo()
        keys = sorted((self.data.get("presets") or {}).keys())
        if keys:
            self.cmb_preset.set(keys[0])
            self._load_preset_to_ui(keys[0])
        else:
            # 初回でも必ず操作開始できるよう、空なら default を自動作成
            self.data.setdefault("presets", {})["default"] = {}
            self._refresh_preset_combo()
            self.cmb_preset.set("default")
            self._set_all(self.row_objs, show=False, default_on=False)
            self._set_all(self.row_cats, show=False, default_on=False)
            self._set_all(self.row_items, show=False, default_on=False)

    def _load_file(self):
        if not os.path.exists(self.presets_path):
            self.data = {"presets": {}}
            return
        try:
            with open(self.presets_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                if isinstance(raw.get("presets"), dict):
                    self.data = raw
                else:
                    # 互換: 直下に presets がある形式も許容
                    self.data = {"presets": raw}
            else:
                self.data = {"presets": {}}
        except Exception:
            self.data = {"presets": {}}

    def _build_sources(self):
        cfg = self.editor.config or {}
        am = cfg.get("attr_mapping") or {}
        mo = cfg.get("map_object_attr_ids") or []
        ordered_obj_ids = []
        if isinstance(mo, list):
            for x in mo:
                sid = str(x or "").strip()
                if sid and sid in am and sid not in ordered_obj_ids:
                    ordered_obj_ids.append(sid)
        for aid in am.keys():
            sid = str(aid or "").strip()
            if sid and sid not in ordered_obj_ids:
                ordered_obj_ids.append(sid)
        self.obj_source = []
        for oid in ordered_obj_ids:
            info = am.get(oid) if isinstance(am, dict) else {}
            if isinstance(info, dict):
                jp = (info.get("name_jp") or oid).strip() or oid
                en = (info.get("name_en") or jp).strip() or jp
            else:
                jp = oid
                en = oid
            self.obj_source.append({"id": oid, "label": f"{jp} ({en})"})

        cm = cfg.get("category_master") or {}
        self.cat_source = []
        if isinstance(cm, dict):
            for cat_jp, info in cm.items():
                if not isinstance(info, dict):
                    continue
                cid = (info.get("id") or "").strip()
                if not cid:
                    continue
                nj = (info.get("name_jp") or cat_jp or cid).strip() or cid
                ne = (info.get("name_en") or nj).strip() or nj
                self.cat_source.append({"id": cid, "label": f"{nj} ({ne})"})
        self.cat_source.sort(key=lambda x: (x.get("label") or ""))

        im = cfg.get("item_master") or {}
        self.item_source = []
        if isinstance(im, dict):
            for grp, items in im.items():
                if not isinstance(items, dict):
                    continue
                for iid, info in items.items():
                    sid = str(iid or "").strip()
                    if not sid:
                        continue
                    if isinstance(info, dict):
                        nj = (info.get("name_jp") or sid).strip() or sid
                        ne = (info.get("name_en") or nj).strip() or nj
                    else:
                        nj = sid
                        ne = sid
                    self.item_source.append({"id": sid, "label": f"{grp} / {nj} ({ne})"})
        self.item_source.sort(key=lambda x: (x.get("label") or ""))

    def _make_section(self, parent, title):
        box = ctk.CTkFrame(parent)
        ctk.CTkLabel(box, text=title, font=("Meiryo", 13, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(0, 4))
        body = ctk.CTkScrollableFrame(box, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        return box, head, body

    def _add_rows(self, body, rows_out, source):
        for ent in source:
            rid = str(ent.get("id") or "").strip()
            if not rid:
                continue
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            v_show = tk.BooleanVar(value=True)
            v_def = tk.BooleanVar(value=False)
            cb_show = ctk.CTkCheckBox(row, text="", variable=v_show, width=24)
            cb_show.pack(side="left", padx=(2, 6))
            cb_def = ctk.CTkCheckBox(row, text="", variable=v_def, width=24)
            cb_def.pack(side="left", padx=(2, 6))
            ctk.CTkLabel(row, text=ent.get("label") or rid, anchor="w").pack(side="left", fill="x", expand=True, padx=4)

            def _sync(*_):
                if not v_show.get():
                    v_def.set(False)
                    cb_def.configure(state="disabled")
                else:
                    cb_def.configure(state="normal")
            cb_show.configure(command=_sync)
            _sync()

            rows_out.append({"id": rid, "show": v_show, "default_on": v_def})

    def _set_all(self, rows, show=None, default_on=None):
        for r in rows:
            if show is not None:
                r["show"].set(bool(show))
            if default_on is not None:
                if not r["show"].get():
                    r["default_on"].set(False)
                else:
                    r["default_on"].set(bool(default_on))

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(top, text="プリセット:").pack(side="left", padx=(4, 6))
        self.cmb_preset = ctk.CTkComboBox(top, width=260, values=[], state="normal")
        self.cmb_preset.pack(side="left", padx=4)
        ctk.CTkButton(top, text="読込", width=72, command=lambda: self._load_preset_to_ui(self.cmb_preset.get().strip())).pack(side="left", padx=4)

        self.ent_new = ctk.CTkEntry(top, width=180, placeholder_text="新規名 (例: weapons_en)")
        self.ent_new.pack(side="left", padx=(14, 4))
        ctk.CTkButton(top, text="新規", width=72, command=self._new_preset).pack(side="left", padx=4)
        ctk.CTkButton(top, text="削除", width=72, fg_color="#8e3b3b", command=self._delete_preset).pack(side="left", padx=4)

        note = ctk.CTkLabel(
            self,
            text="手順: 1) プリセット選択/新規  2) 表示(左) と 初期ON(右) を設定  3) 保存。対象外は地図に出ません。",
            font=("Meiryo", 10),
            text_color="#95a5a6"
        )
        note.pack(anchor="w", padx=14, pady=(0, 6))

        grid = ctk.CTkFrame(self)
        grid.pack(fill="both", expand=True, padx=10, pady=6)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

        box_obj, head_obj, body_obj = self._make_section(grid, "オブジェクト")
        box_obj.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        box_cat, head_cat, body_cat = self._make_section(grid, "カテゴリ")
        box_cat.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        box_item, head_item, body_item = self._make_section(grid, "アイテム")
        box_item.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)

        for head, rows_ref in ((head_obj, self.row_objs), (head_cat, self.row_cats), (head_item, self.row_items)):
            ctk.CTkButton(head, text="全表示", width=70, command=lambda rr=rows_ref: self._set_all(rr, show=True)).pack(side="left", padx=2)
            ctk.CTkButton(head, text="全非表示", width=74, command=lambda rr=rows_ref: self._set_all(rr, show=False)).pack(side="left", padx=2)
            ctk.CTkButton(head, text="初期ON全", width=72, command=lambda rr=rows_ref: self._set_all(rr, default_on=True)).pack(side="left", padx=8)
            ctk.CTkButton(head, text="初期ON解除", width=86, command=lambda rr=rows_ref: self._set_all(rr, default_on=False)).pack(side="left", padx=2)

        self._add_rows(body_obj, self.row_objs, self.obj_source)
        self._add_rows(body_cat, self.row_cats, self.cat_source)
        self._add_rows(body_item, self.row_items, self.item_source)

        fbtn = ctk.CTkFrame(self, fg_color="transparent")
        fbtn.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(fbtn, text="保存", fg_color="#27ae60", width=120, command=self._save).pack(side="right", padx=4)
        ctk.CTkButton(fbtn, text="閉じる", fg_color="#7f8c8d", width=120, command=self.destroy).pack(side="right", padx=4)

    def _refresh_preset_combo(self):
        keys = sorted((self.data.get("presets") or {}).keys())
        self.cmb_preset.configure(values=keys if keys else [""])
        if keys and (self.cmb_preset.get().strip() not in keys):
            self.cmb_preset.set(keys[0])

    def _new_preset(self):
        name = (self.ent_new.get() or "").strip().lower()
        if not name:
            messagebox.showwarning("確認", "新規プリセット名を入力してください。", parent=self)
            return
        p = self.data.setdefault("presets", {})
        if name in p:
            messagebox.showwarning("確認", f"既に存在します: {name}", parent=self)
            return
        p[name] = {}
        self._refresh_preset_combo()
        self.cmb_preset.set(name)
        self._set_all(self.row_objs, show=False, default_on=False)
        self._set_all(self.row_cats, show=False, default_on=False)
        self._set_all(self.row_items, show=False, default_on=False)

    def _delete_preset(self):
        name = (self.cmb_preset.get() or "").strip()
        if not name:
            return
        if not messagebox.askyesno("削除確認", f"プリセット '{name}' を削除しますか？", parent=self):
            return
        p = self.data.setdefault("presets", {})
        if name in p:
            del p[name]
        self._refresh_preset_combo()
        self._set_all(self.row_objs, show=False, default_on=False)
        self._set_all(self.row_cats, show=False, default_on=False)
        self._set_all(self.row_items, show=False, default_on=False)

    def _load_ids_to_rows(self, rows, allowed_ids, on_ids):
        a = set(str(x).strip().upper() for x in (allowed_ids or []))
        o = set(str(x).strip().upper() for x in (on_ids or []))
        for r in rows:
            rid = str(r["id"]).strip().upper()
            show = rid in a if a else False
            r["show"].set(show)
            r["default_on"].set(show and (rid in o))

    def _load_preset_to_ui(self, name):
        name = (name or "").strip()
        p = self.data.setdefault("presets", {})
        rule = p.get(name) if name else None
        if not isinstance(rule, dict):
            return
        allowed_obj = rule.get("allowed_object_ids") or []
        on_obj = rule.get("default_on_object_ids")
        if not isinstance(on_obj, list):
            # 互換: default_off しかない旧形式
            off = set(str(x).strip().upper() for x in (rule.get("default_off_object_ids") or []))
            on_obj = [x for x in allowed_obj if str(x).strip().upper() not in off]
        self._load_ids_to_rows(self.row_objs, allowed_obj, on_obj)
        self._load_ids_to_rows(self.row_cats, rule.get("allowed_category_ids") or [], rule.get("default_on_category_ids") or [])
        self._load_ids_to_rows(self.row_items, rule.get("allowed_item_ids") or [], rule.get("default_on_item_ids") or [])

    def _collect_ids(self, rows):
        allowed = []
        default_on = []
        for r in rows:
            rid = str(r["id"]).strip()
            if not rid:
                continue
            if r["show"].get():
                allowed.append(rid)
                if r["default_on"].get():
                    default_on.append(rid)
        return allowed, default_on

    def _save(self):
        name = (self.cmb_preset.get() or "").strip().lower()
        if not name:
            messagebox.showwarning("確認", "保存するプリセットを選択してください。", parent=self)
            return
        p = self.data.setdefault("presets", {})
        old = p.get(name, {})
        old = dict(old) if isinstance(old, dict) else {}
        allowed_obj, on_obj = self._collect_ids(self.row_objs)
        allowed_cat, on_cat = self._collect_ids(self.row_cats)
        allowed_item, on_item = self._collect_ids(self.row_items)
        off_obj = [x for x in allowed_obj if str(x).strip().upper() not in {str(v).strip().upper() for v in on_obj}]

        new_rule = dict(old)
        new_rule.update({
            "allowed_object_ids": allowed_obj,
            "allowed_category_ids": allowed_cat,
            "allowed_item_ids": allowed_item,
            "default_on_object_ids": on_obj,
            "default_off_object_ids": off_obj,
            "default_on_category_ids": on_cat,
            "default_on_item_ids": on_item,
        })
        p[name] = new_rule

        try:
            with open(self.presets_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("保存エラー", str(e), parent=self)
            return
        messagebox.showinfo("保存", f"view-presets.json に '{name}' を保存しました。", parent=self)


# ==========================================
# メインエディタ (変更なし)
# ==========================================
class MapEditor(ctk.CTkToplevel):
    # キャンバスを delete("all") せずレイヤごとに消す（地図は itemconfig で差し替えてちらつき低減）
    _CTAG_MAP = "map_layer"
    _CTAG_AREA = "editor_area"
    _CTAG_PIN = "editor_pin"
    _CTAG_OVERLAY = "editor_overlay"

    def __init__(self, master, game_name, region_name):
        super().__init__(master)
        self.game_path = os.path.join(GAMES_ROOT, game_name, region_name)
        self.tile_dir = os.path.join(self.game_path, "tiles")
        self.config_path = os.path.join(self.game_path, "config.json")
        self.areas_path = os.path.join(self.game_path, "areas.json")
        
        self.load_config()
        
        if "orig_w" not in self.config or "orig_h" not in self.config:
            m_path = os.path.join(self.game_path, self.config.get("map_file", "map.png"))
            if os.path.exists(m_path):
                with Image.open(m_path) as tmp: self.config["orig_w"], self.config["orig_h"] = tmp.size
                with open(self.config_path, "w", encoding="utf-8") as f: 
                    json.dump(self.config, f, indent=4, ensure_ascii=False)

        zooms = [int(d) for d in os.listdir(self.tile_dir) if d.isdigit()] if os.path.isdir(self.tile_dir) else []
        self.max_zoom = max(zooms) if zooms else 0
        self.zoom = float(self.max_zoom) - 0.5
        self.orig_max_dim = (2 ** self.max_zoom) * 256 

        def _safe_pos_int(v):
            try:
                n = int(float(v))
                return n if n > 0 else None
            except Exception:
                return None

        ow = _safe_pos_int(self.config.get("orig_w"))
        oh = _safe_pos_int(self.config.get("orig_h"))
        if ow is None or oh is None:
            fallback = int(self.orig_max_dim) if self.orig_max_dim > 0 else 4096
            if ow is None:
                ow = fallback
                self.config["orig_w"] = ow
            if oh is None:
                oh = fallback
                self.config["orig_h"] = oh
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
        self.orig_w, self.orig_h = ow, oh
        
        self.title(f"Editor - {game_name} ({region_name})")
        self.geometry("1780x950")
        
        self.data_list = []
        self.current_uid = None
        # エリア編集用の状態
        self.area_list = []
        self.current_area_uid = None
        self.area_mode = "idle"          # idle / create_polygon / create_circle / create_rect / edit_polygon
        self.area_temp_points = []       # 新規作成中ポリゴン用
        self.area_drag_index = None      # 制御点ドラッグ中インデックス
        self.area_drag_mode = None       # create_shape / move_area
        self.area_drag_start = None      # ドラッグ開始時の画像座標
        self.area_preview_shape = None   # ドラッグ中の仮プレビュー
        self.area_show_points = tk.BooleanVar(value=True)
        self.area_edit_enabled = tk.BooleanVar(value=True)
        self.temp_coords = None
        self.is_autoscrolling = False
        self.tile_cache = OrderedDict()
        self._tile_cache_max = 384
        self._editor_pin_photo_cache = OrderedDict()
        self._editor_pin_photo_cache_max = 200
        self._throttle_refresh_after = None
        self._canvas_configure_after = None
        self._refresh_map_retry_after = None
        self._zoom_wheel_pending_delta = 0.0
        self._zoom_wheel_after_id = None
        self._zoom_wheel_anchor_ex = 0
        self._zoom_wheel_anchor_ey = 0
        self._suppress_configure_refresh_until = 0.0
        self._pending_scroll_after_zoom = None
        self._tile_pil_cache = OrderedDict()
        self._tile_pil_cache_max = 320
        self._map_viewport_photo = None
        self.category_slots = []
        self._pin_preview_after_id = None
        
        self.is_crop_mode = False
        self.crop_box = {"x": 100, "y": 100, "w": 640, "h": 360}
        self.drag_mode = None
        self.has_dragged = False
        self.drag_start = (0, 0)
        self.active_tool = None
        self.here_pos = None; self.arrow_pos = None
        self._pin_placement_active = False
        self._pin_editor_panel_open = False
        self._editing_pin_drag_active = False
        self._pin_filter_window = None
        self._pin_edit_baseline = None
        self._pin_save_last_ok = False
        self._parent_pick_mode = False

        self.setup_ui()
        self.load_csv()
        self.load_areas()
        self.is_dirty = False
        self.update_title_dirty()
        self.update_idletasks()
        self.after(100, self.refresh_map)
        self.run_autoscroll_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f: self.config = json.load(f)
        else: self.config = {}
        # 欠損時フォールバック（旧設定/壊れた設定でも起動できるように）
        if not str(self.config.get("save_file") or "").strip():
            self.config["save_file"] = "master_data.csv"
        if not str(self.config.get("map_file") or "").strip():
            self.config["map_file"] = "map.png"
        # 互換: skill_name_master は list / dict の両方を許可（builder 側で正規化）
        sm = self.config.get("skill_name_master")
        if not isinstance(sm, (list, dict)):
            self.config["skill_name_master"] = []
        category_special_rules_builder.sync_category_special_rules_from_master(self.config)

    def _sanitize_saved_pin_link_url(self, raw):
        """http(s) のみ許可。戻り値: (保存用文字列, 警告メッセージ or None)"""
        s = (raw or "").strip()
        if not s:
            return "", None
        try:
            p = urlparse(s)
        except Exception:
            return "", "URL の形式が不正なため保存しませんでした。"
        if p.scheme not in ("http", "https") or not p.netloc:
            return "", "http / https の URL のみ保存できます。"
        return s, None

    def _guide_page_links_path(self):
        name = self.config.get("guide_page_links_file", GUIDE_PAGE_LINKS_DEFAULT_FILE)
        return os.path.join(self.game_path, name)

    def _load_guide_page_links_raw(self):
        path = self._guide_page_links_path()
        if not os.path.isfile(path):
            return {"pages": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("pages"), list):
                return data
        except Exception:
            pass
        return {"pages": []}

    def _get_wp_rest_guide_sources(self):
        src = self.config.get("wp_rest_guide_sources")
        if isinstance(src, list) and src:
            return src
        return list(wp_rest_guide.DEFAULT_WP_REST_GUIDE_SOURCES)

    def _sync_link_combo_values(self):
        pages = self._guide_page_links_cache or []
        labels = [GUIDE_LINK_PICK_NONE]
        for pg in pages:
            if not isinstance(pg, dict):
                continue
            slug = (pg.get("slug") or "").strip()
            tj = (pg.get("title_jp") or "").strip()
            te = (pg.get("title_en") or "").strip()
            if slug or tj or te:
                labels.append(f"{slug} | {tj} | {te}"[:200])
        for combo in (getattr(self, "cmb_link_pick_jp", None), getattr(self, "cmb_link_pick_en", None)):
            if combo is not None:
                combo.configure(values=labels)
                cur = combo.get()
                if cur not in labels:
                    combo.set(GUIDE_LINK_PICK_NONE)

    def _toggle_link_settings_section(self):
        self.link_settings_expanded = not self.link_settings_expanded
        if self.link_settings_expanded:
            self.f_link_body.pack(fill="x", padx=4, pady=5, after=self.lbl_link_toggle)
            self.lbl_link_toggle.configure(text="▼ リンク設定")
        else:
            self.f_link_body.pack_forget()
            self.lbl_link_toggle.configure(text="▶ リンク設定")

    def _refresh_guide_page_links_from_disk(self):
        self._guide_page_links_cache = self._load_guide_page_links_raw().get("pages", [])
        self._sync_link_combo_values()

    def _on_link_combo_selected(self, which):
        pick = GUIDE_LINK_PICK_NONE
        combo = self.cmb_link_pick_jp if which == "jp" else self.cmb_link_pick_en
        try:
            pick = combo.get()
        except Exception:
            return
        if pick == GUIDE_LINK_PICK_NONE:
            return
        slug_part = pick.split("|", 1)[0].strip()
        for pg in self._guide_page_links_cache or []:
            if not isinstance(pg, dict):
                continue
            if (pg.get("slug") or "").strip() == slug_part:
                uj = (pg.get("url_jp") or "").strip()
                ue = (pg.get("url_en") or "").strip()
                if which == "jp" and uj:
                    self.ent_link_jp.delete(0, "end")
                    self.ent_link_jp.insert(0, uj)
                elif which == "en" and ue:
                    self.ent_link_en.delete(0, "end")
                    self.ent_link_en.insert(0, ue)
                self.mark_dirty()
                break
        try:
            combo.set(GUIDE_LINK_PICK_NONE)
        except Exception:
            pass

    def _open_wp_rest_guide_picker(self):
        sources = self._get_wp_rest_guide_sources()
        rows = None
        if not sources:
            cache = self._load_guide_page_links_raw().get("pages", [])
            rows = [r for r in cache if isinstance(r, dict)]
            if not rows:
                messagebox.showinfo(
                    "リンク候補",
                    "config.json に wp_rest_guide_sources が無く、guide_page_links.json にも候補がありません。",
                )
                return
        WpRestGuidePickerWindow(self, sources, rows_prefill=rows)

    def _generate_item_id(self, name_jp):
        """新規アイテム用に名前からIDを生成（マスタ自動追加用）"""
        s = re.sub(r'[^a-zA-Z0-9_\u3040-\u9fff]', '_', (name_jp or "")[:40]).strip('_')
        return (s or "ITEM") + "_" + str(abs(hash(name_jp)))[:8]

    def _get_cat_id(self, category_name):
        """カテゴリ表示名から cat_id を取得（生存戦略：保存はIDで）"""
        if not category_name:
            return ""
        info = self.category_master.get(category_name, {})
        if isinstance(info, dict) and info.get("id"):
            return info["id"]
        return category_name  # 後方互換：id がなければ表示名をそのまま

    def _generate_cat_id(self, name_jp):
        """新規カテゴリ用に名前からIDを生成（マスタ自動追加用）"""
        s = re.sub(r'[^a-zA-Z0-9_\u3040-\u9fff]', '_', (name_jp or "")[:30]).strip('_')
        return (s or "cat") + "_" + str(abs(hash(name_jp)))[:8]

    def _generate_obj_id(self, name_jp):
        """新規オブジェクト用に名前からIDを生成（マスタ自動追加用）"""
        return "OBJ_" + str(abs(hash(name_jp)))[:8]

    def _sync_pin_filter_vars_from_masters(self):
        """マスタに合わせてフィルタ用 BooleanVar を増減（新規はオン維持）。"""
        if not hasattr(self, "pin_filter_object_vars"):
            self.pin_filter_object_vars = {}
        if not hasattr(self, "pin_filter_cat_vars"):
            self.pin_filter_cat_vars = {}
        if not hasattr(self, "pin_filter_item_vars"):
            self.pin_filter_item_vars = {}
        self._rebuild_pin_cat_mapping()
        new_o = {}
        for aid in self.cat_mapping.keys():
            old = self.pin_filter_object_vars.get(aid)
            new_o[aid] = old if old is not None else tk.BooleanVar(value=True)
        self.pin_filter_object_vars = new_o
        new_c = {}
        for cat_name, info in (self.category_master or {}).items():
            if not isinstance(info, dict):
                continue
            cid = (info.get("id") or "").strip() or cat_name
            old = self.pin_filter_cat_vars.get(cid)
            new_c[cid] = old if old is not None else tk.BooleanVar(value=True)
        self.pin_filter_cat_vars = new_c
        new_i = {}
        for grp, items in (self.item_master or {}).items():
            if not isinstance(items, dict):
                continue
            for iid in items.keys():
                key = f"{grp}\t{iid}"
                old = self.pin_filter_item_vars.get(key)
                new_i[key] = old if old is not None else tk.BooleanVar(value=True)
        self.pin_filter_item_vars = new_i

    def _pin_passes_display_filters(self, d):
        """オブジェクト・カテゴリ・アイテム・未完成フィルタをすべて満たすか。"""
        if self._is_draft_pin_row(d):
            return True
        attr_key = (d.get("attribute") or d.get("category_pin") or "").strip() or "MISC_OTHER"
        ov = self.pin_filter_object_vars.get(attr_key)
        if ov is not None and not ov.get():
            return False
        cats = self._parse_categories_for_pin(d)
        cv = self.pin_filter_cat_vars
        if cv:
            all_c_on = all(v.get() for v in cv.values())
            if not all_c_on:
                enabled_c = {cid for cid, v in cv.items() if v.get()}
                if cats:
                    ok = False
                    for c in cats:
                        if not isinstance(c, dict):
                            continue
                        cid = (c.get("cat_id") or "").strip()
                        if cid and cid in enabled_c:
                            ok = True
                            break
                        cname = (c.get("category") or "").strip()
                        if cname:
                            resolved = self._get_cat_id(cname)
                            if resolved in enabled_c or cname in enabled_c:
                                ok = True
                                break
                    if not ok:
                        return False
        iv = self.pin_filter_item_vars
        if iv:
            all_i_on = all(v.get() for v in iv.values())
            if not all_i_on:
                enabled_i = {k for k, v in iv.items() if v.get()}
                if cats:
                    ok = False
                    for c in cats:
                        if not isinstance(c, dict):
                            continue
                        iid = (c.get("item_id") or "").strip()
                        if not iid:
                            continue
                        cname = (c.get("category") or "").strip()
                        if cname:
                            key = f"{cname}\t{iid}"
                            if key in enabled_i:
                                ok = True
                                break
                        for grp in (self.item_master or {}).keys():
                            key2 = f"{grp}\t{iid}"
                            if key2 in enabled_i:
                                ok = True
                                break
                        if ok:
                            break
                    if not ok:
                        return False
        if self.show_incomplete_only.get():
            has_name = bool(d.get("name_jp"))
            has_categories = bool(d.get("categories"))
            if has_name and has_categories:
                return False
        return True

    def _open_pin_filter_window(self):
        self._sync_pin_filter_vars_from_masters()
        w = getattr(self, "_pin_filter_window", None)
        if w is not None:
            try:
                if w.winfo_exists():
                    w.focus_force()
                    return
            except tk.TclError:
                pass
        PinFilterWindow(self)

    def _rebuild_pin_cat_mapping(self):
        """ピン編集コンボ用。map_object_attr_ids があるときはその順のみ。無ければ attr_mapping 全件。"""
        am = self.attr_mapping
        mo = self.config.get("map_object_attr_ids")
        if mo is not None:
            self.cat_mapping = {}
            for kid in mo:
                v = am.get(kid)
                if isinstance(v, dict):
                    self.cat_mapping[kid] = v.get("name_jp", kid)
                elif v is not None:
                    self.cat_mapping[kid] = v
        else:
            self.cat_mapping = {k: v["name_jp"] if isinstance(v, dict) else v for k, v in am.items()}

    def _attr_display_name(self, attr_key):
        """オブジェクト ID から表示名（コンボ・互換用）。ルートのみの ID も attr_mapping から解決。"""
        if not attr_key:
            return ""
        if attr_key in self.cat_mapping:
            return self.cat_mapping[attr_key]
        v = self.attr_mapping.get(attr_key)
        if isinstance(v, dict):
            return (v.get("name_jp") or "").strip() or attr_key
        if v is not None:
            return str(v)
        return str(attr_key)

    def _ensure_master_updated(self):
        """config 変更後にメモリ上のマスタ参照を更新（オブジェクト・カテゴリ・アイテム・フィルタ）"""
        self.attr_mapping = self.config.get("attr_mapping", {})
        if not self.attr_mapping:
            old_cat_mapping = self.config.get("cat_mapping", {})
            if old_cat_mapping:
                self.attr_mapping = {k: {"name_jp": v, "name_en": ""} for k, v in old_cat_mapping.items()}
        self._rebuild_pin_cat_mapping()
        self.display_names = list(self.cat_mapping.values())
        if hasattr(self, "cmb_attribute"):
            self.cmb_attribute.configure(values=["(なし)"] + self.display_names)
        self.category_master = self.config.get("category_master", {})
        self.category_list = list(self.category_master.keys())
        self.item_master = self.config.get("item_master", {})
        self._sync_pin_filter_vars_from_masters()
        # フィルタリストとスロットのコンボボックスを更新
        rev = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev.get(self.cmb_attribute.get(), "")
        obj_type = "loot"
        if attr_id and attr_id in self.attr_mapping:
            o = self.attr_mapping[attr_id]
            if isinstance(o, dict):
                obj_type = o.get("type", "loot")
        self.update_category_list_for_pin_object(obj_type, attr_id)

    def reload_config(self):
        self.load_config()
        # 属性マッピング（JP/EN対応）- 入れ物（宝箱、洞窟など）
        self.attr_mapping = self.config.get("attr_mapping", {})
        if not self.attr_mapping:
            old_cat_mapping = self.config.get("cat_mapping", {})
            if old_cat_mapping:
                self.attr_mapping = {k: {"name_jp": v, "name_en": ""} for k, v in old_cat_mapping.items()}
        
        self._rebuild_pin_cat_mapping()
        
        # カテゴリマスタ（JP/EN + 属性項目）- 中身（設計図、LEMなど）
        self.category_master = self.config.get("category_master", {})
        if not self.category_master:
            old_list = self.config.get("category_list", [])
            if old_list:
                self.category_master = {cat: {"name_jp": cat, "name_en": "", "attributes": {}} for cat in old_list if cat}
        self.category_list = list(self.category_master.keys())
        
        self.item_master = self.config.get("item_master", {})
        
        self.display_names = list(self.cat_mapping.values())
        self.cmb_attribute.configure(values=["(なし)"] + self.display_names)
        self._sync_pin_filter_vars_from_masters()

        # オブジェクト選択に応じた分類リスト（マスタの object_attr_id と連動）
        rev = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev.get(self.cmb_attribute.get(), "") if hasattr(self, "cmb_attribute") else ""
        obj_type = "loot"
        if attr_id and attr_id in self.attr_mapping:
            o = self.attr_mapping[attr_id]
            if isinstance(o, dict):
                obj_type = o.get("type", "loot")
        self.update_category_list_for_pin_object(obj_type, attr_id)

        self.refresh_map()

    def _sync_obj_en_from_attribute_master(self, attr_id):
        """オブジェクトコンボで選んだ JP に対応するマスタの EN を、(EN)欄に常に反映する（選択式なので手入力残りを避ける）。"""
        if not getattr(self, "ent_obj_en", None):
            return
        self.ent_obj_en.delete(0, "end")
        if not attr_id or attr_id not in self.attr_mapping:
            return
        o = self.attr_mapping[attr_id]
        if not isinstance(o, dict):
            return
        obj_en = (o.get("name_en", "") or o.get("name_jp", "") or "").strip()
        if obj_en:
            self.ent_obj_en.insert(0, obj_en)

    def on_attribute_changed(self, *args):
        """オブジェクト（見た目）選択時: ルール①で中身エリアの表示/非表示・追加ボタン制御。オブジェクト属性表示。分類を object_attr_id と type でフィルタ。"""
        attribute = (self.cmb_attribute.get() or "").strip()
        
        # 選択されたオブジェクトの情報を取得（表示名→ID）
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev_cat_map.get(attribute, "")
        
        # オブジェクトのtypeを取得
        obj_type = "loot"  # デフォルト
        if attr_id and attr_id in self.attr_mapping:
            obj_info = self.attr_mapping[attr_id]
            if isinstance(obj_info, dict):
                obj_type = obj_info.get("type", "loot")
        
        # オブジェクト属性フレームを表示（属性がある場合のみ実際に表示される）
        self.show_object_attributes(attr_id)
        
        # ルール①：登録済みオブジェクトかつ type=landmark のときだけ中身エリアを非表示
        if attr_id and obj_type == "landmark":
            if getattr(self, "f_pin_special_notes", None):
                self.f_pin_special_notes.pack_forget()
            self.f_cat_header.pack_forget()
            self.category_slots_frame.pack_forget()
            if getattr(self, "btn_add_category", None):
                self.btn_add_category.configure(state="disabled")
        else:
            if getattr(self, "btn_add_category", None):
                self.btn_add_category.configure(state="normal")
            self.update_category_list_for_pin_object(obj_type, attr_id)
            self._sync_pin_special_notes_pack_order()
        # オブジェクトはコンボ選択なので、通常は JP確定のたびに(EN)欄をマスタ値で上書きする。
        # ただし load_to_ui 読み込み中は保存済みの上書き値（obj_name_en）を保持したいので抑止する。
        if not getattr(self, "_suppress_obj_en_auto_sync", False):
            self._sync_obj_en_from_attribute_master(attr_id)
        # 地点の名称（JP/EN）は例外上書き専用。空が通常。マスタからは自動入力しない。
        self._schedule_pin_preview_refresh()
    
    def show_object_attributes(self, attr_id):
        """オブジェクトの属性入力欄を表示"""
        # 既存のオブジェクト属性ウィジェットをクリア
        self.obj_attr_frame.pack_forget()
        for w in self.obj_attr_frame.winfo_children():
            w.destroy()
        self.obj_attr_widgets = {}
        
        if not attr_id or attr_id not in self.attr_mapping:
            return
        
        obj_info = self.attr_mapping[attr_id]
        if not isinstance(obj_info, dict):
            return
        
        obj_attrs = obj_info.get("attributes", {})
        if not obj_attrs:
            return
        
        # 属性がある場合のみフレームを表示（オブジェクト直後に並べる）
        self.obj_attr_frame.pack(fill="x", padx=4, pady=5, after=self.f_attr)
        
        for attr_key, attr_data in obj_attrs.items():
            attr_row = ctk.CTkFrame(self.obj_attr_frame, fg_color="transparent")
            attr_row.pack(fill="x", padx=BOX_PADX, pady=2)
            
            ctk.CTkLabel(attr_row, text=f"{attr_key}:", width=80, anchor="w").pack(side="left", padx=5)
            
            # 後方互換性
            if isinstance(attr_data, list):
                attr_data = {"type": "select", "options": attr_data}
            
            attr_type = attr_data.get("type", "select") if isinstance(attr_data, dict) else "select"
            
            if attr_type == "number":
                ent = ctk.CTkEntry(attr_row, width=100, placeholder_text="数値")
                ent.pack(side="left", padx=5)
                self.obj_attr_widgets[attr_key] = {"type": "number", "widget": ent}
            else:
                options = attr_data.get("options", []) if isinstance(attr_data, dict) else attr_data
                cmb = ctk.CTkComboBox(attr_row, values=["(なし)"] + options, width=150)
                cmb.pack(side="left", padx=5)
                self.obj_attr_widgets[attr_key] = {"type": "select", "widget": cmb}
    
    def update_category_list_for_pin_object(self, obj_type, object_attr_id=""):
        """ピン編集の分類コンボを絞り込む。

        オブジェクト選択時は、マスタでそのオブジェクトに紐づいた分類だけを出す。
        紐づけは ``object_attr_id``（マスタ管理の対応オブジェクト）または
        従来の ``object_ids`` 配列のいずれかで判定する。
        オブジェクト未選択のときは、これらの紐づけが無い分類のみ type で絞って出す。
        """
        oid_sel = (object_attr_id or "").strip()
        # 下位項目が不要なタイプ（landmark等）は(なし)のみ
        if obj_type == "landmark":
            filtered_categories = []
        else:
            filtered_categories = []
            for cat_name, cat_info in self.category_master.items():
                if isinstance(cat_info, dict):
                    cat_type = cat_info.get("type", "loot")
                    if cat_type != obj_type:
                        continue
                    cat_oid = (cat_info.get("object_attr_id") or "").strip()
                    raw_oids = cat_info.get("object_ids")
                    oid_list = []
                    if isinstance(raw_oids, list):
                        for x in raw_oids:
                            if x is None:
                                continue
                            s = str(x).strip()
                            if s:
                                oid_list.append(s)
                    if oid_sel:
                        # 現行仕様: object_attr_id があるならそれを唯一の判定源にする。
                        # 旧互換: object_attr_id が無いデータのみ object_ids を参照。
                        if cat_oid:
                            match = (cat_oid == oid_sel)
                        else:
                            match = bool(oid_list) and (oid_sel in oid_list)
                        if match:
                            filtered_categories.append(cat_name)
                        # 紐づけ無しの分類はオブジェクト選択時は出さない
                    else:
                        if cat_oid:
                            continue
                        if oid_list:
                            continue
                        filtered_categories.append(cat_name)
                else:
                    if obj_type == "loot" and not oid_sel:
                        filtered_categories.append(cat_name)
        
        # カテゴリスロットのリストを更新
        for slot in self.category_slots:
            current_cat = slot["category"].get()
            slot["category"].configure(values=["(なし)"] + filtered_categories)
            if current_cat not in filtered_categories and current_cat != "(なし)":
                slot["category"].set("(なし)")
                self.on_slot_category_changed(slot["frame"])
        
        # 現在のフィルタリングされたカテゴリリストを保存
        self.filtered_category_list = filtered_categories

    def _merge_pin_category_combo_values(self, slot, category):
        """読み込み互換: フィルタ外の分類名（旧データなど）もコンボに含める。"""
        fc = list(getattr(self, "filtered_category_list", []) or [])
        vals = ["(なし)"] + fc
        if category and category not in ("(なし)",) and category not in fc:
            vals.append(category)
        slot["category"].configure(values=vals)

    def _update_slot_item_en_display(self, slot):
        """アイテム(EN)ラベルをマスタに合わせて更新（表示のみ）。"""
        if not slot.get("lbl_slot_item_en"):
            return
        category = (slot["category"].get() or "").strip()
        item_name = (slot["item"].get() or "").strip()
        if not category or category == "(なし)" or not item_name or item_name == "(なし)":
            slot["lbl_slot_item_en"].configure(text="—")
            return
        if category not in self.item_master:
            slot["lbl_slot_item_en"].configure(text="—")
            return
        for _iid, info in self.item_master[category].items():
            if isinstance(info, dict) and info.get("name_jp") == item_name:
                en = (info.get("name_en", "") or info.get("name_jp", "") or "").strip()
                slot["lbl_slot_item_en"].configure(text=en or "—")
                return
        slot["lbl_slot_item_en"].configure(text="—")

    def _is_many_qty_token(self, v) -> bool:
        s = str(v or "").strip().lower()
        return s in ("many", "多数")

    def _set_slot_many_mode(self, slot, is_many: bool):
        if not slot:
            return
        ent = slot.get("qty")
        var = slot.get("qty_many_var")
        if not ent or var is None:
            return
        if is_many:
            cur = (ent.get() or "").strip()
            if not self._is_many_qty_token(cur):
                slot["_qty_before_many"] = cur or "1"
            try:
                ent.configure(state="normal")
            except Exception:
                pass
            ent.delete(0, "end")
            ent.insert(0, "MANY")
            try:
                ent.configure(state="disabled")
            except Exception:
                pass
            var.set(True)
            return
        prev = (slot.get("_qty_before_many") or "1").strip() or "1"
        try:
            ent.configure(state="normal")
        except Exception:
            pass
        cur2 = (ent.get() or "").strip()
        if self._is_many_qty_token(cur2) or not cur2:
            ent.delete(0, "end")
            ent.insert(0, prev)
        var.set(False)

    def _on_slot_many_changed(self, slot_frame):
        slot = None
        for s in self.category_slots:
            if s.get("frame") == slot_frame:
                slot = s
                break
        if not slot:
            return
        var = slot.get("qty_many_var")
        is_many = bool(var.get()) if var is not None else False
        self._set_slot_many_mode(slot, is_many)
        self._schedule_pin_preview_refresh()

    def _refresh_category_slot_nav_buttons(self):
        """カテゴリスロットの上下移動ボタンを先頭/末尾で無効化。"""
        n = len(self.category_slots)
        for i, s in enumerate(self.category_slots):
            bu = s.get("btn_slot_up")
            bd = s.get("btn_slot_down")
            if bu is not None:
                try:
                    bu.configure(state="normal" if i > 0 else "disabled")
                except Exception:
                    pass
            if bd is not None:
                try:
                    bd.configure(state="normal" if i < n - 1 else "disabled")
                except Exception:
                    pass

    def move_category_slot(self, slot_frame, delta):
        """カテゴリスロットの表示順を入れ替える（delta: -1=上, +1=下）。"""
        idx = None
        for i, s in enumerate(self.category_slots):
            if s["frame"] == slot_frame:
                idx = i
                break
        if idx is None:
            return
        j = idx + int(delta)
        if j < 0 or j >= len(self.category_slots):
            return
        self.category_slots[idx], self.category_slots[j] = self.category_slots[j], self.category_slots[idx]
        for s in self.category_slots:
            s["frame"].pack_forget()
        for s in self.category_slots:
            s["frame"].pack(fill="x", padx=5, pady=5)
        self._refresh_category_slot_nav_buttons()
        if not getattr(self, "_suppress_special_notes_rebuild", False):
            self._rebuild_pin_special_notes_ui()
        self._schedule_pin_preview_refresh()

    def _repack_category_slot_actions_bottom(self, slot):
        """動的な pack 順の変化後に、削除行を常にスロット最下部へ戻す。"""
        if not slot:
            return
        fr = slot.get("row_frame_actions")
        if fr is None:
            return
        try:
            fr.pack_forget()
            fr.pack(fill="x", padx=BOX_PADX, pady=(10, BOX_PADY + 2))
        except Exception:
            pass

    def add_category_slot(self):
        # 入力ボックスと同じ塗りで統一（tk.FrameでCTk相性を回避）
        slot_frame = tk.Frame(self.category_slots_frame, bg=BOX_FG, relief="ridge", bd=1)
        slot_frame.pack(fill="x", padx=5, pady=5)

        f_row_nav = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_nav.pack(fill="x", padx=BOX_PADX, pady=(BOX_PADY, 2))
        btn_slot_up = ctk.CTkButton(
            f_row_nav,
            text="▲",
            width=40,
            height=26,
            fg_color="#34495e",
            hover_color="#4a6278",
            command=lambda sf=slot_frame: self.move_category_slot(sf, -1),
        )
        btn_slot_down = ctk.CTkButton(
            f_row_nav,
            text="▼",
            width=40,
            height=26,
            fg_color="#34495e",
            hover_color="#4a6278",
            command=lambda sf=slot_frame: self.move_category_slot(sf, 1),
        )
        btn_slot_up.pack(side="left", padx=(0, 4))
        btn_slot_down.pack(side="left", padx=(0, 0))

        # 1行目：カテゴリ選択
        f_row1 = tk.Frame(slot_frame, bg=BOX_FG)
        f_row1.pack(fill="x", padx=BOX_PADX, pady=(BOX_PADY,2))
        f_row1.grid_columnconfigure(1, weight=1)
        
        lbl_cat = ctk.CTkLabel(f_row1, text="分類:", width=60, anchor="w", font=("Meiryo", 10))
        lbl_cat.grid(row=0, column=0, padx=5, sticky="w")
        cat_list = getattr(self, 'filtered_category_list', self.category_list)
        
        cmb_cat = ctk.CTkComboBox(f_row1, values=["(なし)"] + cat_list, width=180, command=lambda v, sf=slot_frame: self.on_slot_category_changed(sf))
        cmb_cat.grid(row=0, column=1, padx=5, sticky="ew")
        cmb_cat.set("(なし)")
        
        # アイテム行と数量行を分ける（1行に詰めるとサイドバー幅で数量が画面外に押し出される）
        f_row_item = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_item.pack(fill="x", padx=BOX_PADX, pady=(2, 2))
        lbl_item = ctk.CTkLabel(f_row_item, text="アイテム:", width=60, anchor="w", font=("Meiryo", 10))
        lbl_item.pack(side="left", padx=5)
        cmb_item = ctk.CTkComboBox(
            f_row_item, values=["(なし)"], width=100,
            command=lambda v, sf=slot_frame: self.on_slot_item_changed(sf),
        )
        cmb_item.pack(side="left", fill="x", expand=True, padx=5)
        cmb_item.set("(なし)")

        f_row_qty = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_qty.pack(fill="x", padx=BOX_PADX, pady=(0, BOX_PADY))
        lbl_qty = ctk.CTkLabel(f_row_qty, text="数量:", width=60, anchor="w", font=("Meiryo", 10))
        lbl_qty.pack(side="left", padx=5)
        ent_qty = ctk.CTkEntry(f_row_qty, width=30, height=28)
        ent_qty.pack(side="left", padx=5)
        ent_qty.insert(0, "1")
        ent_qty.bind("<KeyRelease>", lambda e: self._schedule_pin_preview_refresh())
        qty_many_var = tk.BooleanVar(value=False)
        chk_qty_many = ctk.CTkCheckBox(
            f_row_qty,
            text="多数",
            variable=qty_many_var,
            command=lambda sf=slot_frame: self._on_slot_many_changed(sf),
            width=64,
        )
        chk_qty_many.pack(side="right", padx=(6, 4))

        # 分類(EN)・アイテム(EN): マスタ由来の表示のみ（編集不可）
        ro_pad = {"padx": 10, "pady": 6}
        ro_wrap_kw = {
            "fg_color": "#252525",
            "corner_radius": 4,
            "border_width": 1,
            "border_color": "#4a4a4a",
        }
        f_row_cat_en = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_cat_en.pack(fill="x", padx=BOX_PADX, pady=(4, 2))
        lbl_cat_en = ctk.CTkLabel(f_row_cat_en, text="分類(EN):", width=72, anchor="w", font=("Meiryo", 10))
        lbl_cat_en.pack(side="left", padx=5)
        wrap_cat_en = ctk.CTkFrame(f_row_cat_en, **ro_wrap_kw)
        wrap_cat_en.pack(side="left", fill="x", expand=True, padx=(0, 5))
        lbl_slot_cat_en = ctk.CTkLabel(
            wrap_cat_en, text="—", anchor="w", justify="left", font=("Meiryo", 10), text_color="#95a5a6",
        )
        lbl_slot_cat_en.pack(fill="x", **ro_pad)

        f_row_item_en = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_item_en.pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
        lbl_item_en = ctk.CTkLabel(f_row_item_en, text="アイテム(EN):", width=72, anchor="w", font=("Meiryo", 10))
        lbl_item_en.pack(side="left", padx=5)
        wrap_item_en = ctk.CTkFrame(f_row_item_en, **ro_wrap_kw)
        wrap_item_en.pack(side="left", fill="x", expand=True, padx=(0, 5))
        lbl_slot_item_en = ctk.CTkLabel(
            wrap_item_en, text="—", anchor="w", justify="left", font=("Meiryo", 10), text_color="#95a5a6",
        )
        lbl_slot_item_en.pack(fill="x", **ro_pad)

        # 属性設定フレーム（動的に生成、packしない - 属性がある場合のみ表示。削除行より上に差し込む）
        attr_frame = tk.Frame(slot_frame, bg=BOX_FG)

        f_row_actions = tk.Frame(slot_frame, bg=BOX_FG)
        btn_delete = ctk.CTkButton(
            f_row_actions,
            text="削除",
            width=100,
            height=30,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=lambda: self.delete_category_slot(slot_frame),
        )
        btn_delete.pack(fill="x", padx=4, pady=4)
        f_row_actions.pack(fill="x", padx=BOX_PADX, pady=(10, BOX_PADY + 2))

        slot_data = {
            "frame": slot_frame,
            "row_frame_nav": f_row_nav,
            "btn_slot_up": btn_slot_up,
            "btn_slot_down": btn_slot_down,
            "row_frame": f_row1,
            "row_frame_item": f_row_item,
            "row_frame_qty": f_row_qty,
            "row_frame_cat_en": f_row_cat_en,
            "row_frame_item_en": f_row_item_en,
            "row_frame_actions": f_row_actions,
            "lbl_cat": lbl_cat,
            "category": cmb_cat,
            "lbl_cat_en": lbl_cat_en,
            "lbl_slot_cat_en": lbl_slot_cat_en,
            "lbl_item": lbl_item,
            "item": cmb_item,
            "lbl_qty": lbl_qty,
            "qty": ent_qty,
            "qty_many_var": qty_many_var,
            "chk_qty_many": chk_qty_many,
            "lbl_item_en": lbl_item_en,
            "lbl_slot_item_en": lbl_slot_item_en,
            "btn_delete": btn_delete,
            "attr_frame": attr_frame,
            "attr_widgets": {}
        }
        self.category_slots.append(slot_data)
        self._refresh_category_slot_nav_buttons()
        if not getattr(self, "_suppress_special_notes_rebuild", False):
            self._rebuild_pin_special_notes_ui()
        self._schedule_pin_preview_refresh()
        return slot_data

    def delete_category_slot(self, slot_frame):
        for i, slot in enumerate(self.category_slots):
            if slot["frame"] == slot_frame:
                slot["frame"].destroy()
                del self.category_slots[i]
                break
        self._refresh_category_slot_nav_buttons()
        if not getattr(self, "_suppress_special_notes_rebuild", False):
            self._rebuild_pin_special_notes_ui()
        self._schedule_pin_preview_refresh()

    def on_slot_category_changed(self, slot_frame):
        """スロットのカテゴリ変更時: 属性エリアをクリア。input_type（qty_only/item_select）に応じてアイテム行を切り替え。数量はピン編集では常に表示。"""
        slot = None
        for s in self.category_slots:
            if s["frame"] == slot_frame:
                slot = s
                break
        if not slot:
            return
        
        category = slot["category"].get()
        
        # 属性フレームを非表示にしてクリア
        slot["attr_frame"].pack_forget()
        for w in slot["attr_frame"].winfo_children(): w.destroy()
        slot["attr_widgets"] = {}
        slot["lbl_item"].pack_forget()
        slot["item"].pack_forget()
        slot["lbl_qty"].pack_forget()
        slot["qty"].pack_forget()
        if slot.get("chk_qty_many"):
            slot["chk_qty_many"].pack_forget()
        slot["row_frame_item"].pack_forget()
        slot["row_frame_qty"].pack_forget()
        if slot.get("row_frame_cat_en"):
            slot["row_frame_cat_en"].pack_forget()
        if slot.get("row_frame_item_en"):
            slot["row_frame_item_en"].pack_forget()
        if slot.get("row_frame_actions"):
            slot["row_frame_actions"].pack_forget()

        if category == "(なし)" or not category:
            slot["item"].configure(values=["(なし)"])
            slot["item"].set("(なし)")
            slot["row_frame_item"].pack(fill="x", padx=BOX_PADX, pady=(2, 2))
            slot["lbl_item"].pack(side="left", padx=5)
            slot["item"].pack(side="left", fill="x", expand=True, padx=5)
            slot["row_frame_qty"].pack(fill="x", padx=BOX_PADX, pady=(0, BOX_PADY))
            slot["lbl_qty"].pack(side="left", padx=5)
            slot["qty"].pack(side="left", padx=5)
            if slot.get("chk_qty_many"):
                slot["chk_qty_many"].pack(side="right", padx=(6, 4))
            if slot.get("lbl_slot_cat_en"):
                slot["lbl_slot_cat_en"].configure(text="—")
            if slot.get("lbl_slot_item_en"):
                slot["lbl_slot_item_en"].configure(text="—")
            if slot.get("row_frame_cat_en"):
                slot["row_frame_cat_en"].pack(fill="x", padx=BOX_PADX, pady=(4, 2))
            if slot.get("row_frame_item_en"):
                slot["row_frame_item_en"].pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
            self._repack_category_slot_actions_bottom(slot)
            if not getattr(self, "_suppress_special_notes_rebuild", False):
                self._rebuild_pin_special_notes_ui()
            self._schedule_pin_preview_refresh()
            return
        
        # カテゴリの設定を取得
        input_type = "item_select"  # デフォルト
        if category in self.category_master:
            cat_info = self.category_master[category]
            if isinstance(cat_info, dict):
                input_type = cat_info.get("input_type", "item_select")
        
        if input_type == "qty_only":
            slot["item"].set("(なし)")
            slot["item"].configure(values=["(なし)"])
            slot["row_frame_qty"].pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
            slot["lbl_qty"].pack(side="left", padx=5)
            slot["qty"].pack(side="left", padx=5)
            if slot.get("chk_qty_many"):
                slot["chk_qty_many"].pack(side="right", padx=(6, 4))
            if slot.get("row_frame_cat_en"):
                slot["row_frame_cat_en"].pack(fill="x", padx=BOX_PADX, pady=(4, 2))
            if slot.get("row_frame_item_en"):
                slot["row_frame_item_en"].pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
        else:
            slot["row_frame_item"].pack(fill="x", padx=BOX_PADX, pady=(2, 2))
            slot["lbl_item"].pack(side="left", padx=5)
            slot["item"].pack(side="left", fill="x", expand=True, padx=5)
            if category in self.item_master:
                items = self.item_master[category]
                item_names = ["(なし)"] + [info["name_jp"] for info in items.values()]
                slot["item"].configure(values=item_names)
                slot["item"].set("(なし)")
            else:
                slot["item"].configure(values=["(なし)"])
                slot["item"].set("(なし)")
            slot["row_frame_qty"].pack(fill="x", padx=BOX_PADX, pady=(0, BOX_PADY))
            slot["lbl_qty"].pack(side="left", padx=5)
            slot["qty"].pack(side="left", padx=5)
            if slot.get("chk_qty_many"):
                slot["chk_qty_many"].pack(side="right", padx=(6, 4))
            if slot.get("row_frame_cat_en"):
                slot["row_frame_cat_en"].pack(fill="x", padx=BOX_PADX, pady=(4, 2))
            if slot.get("row_frame_item_en"):
                slot["row_frame_item_en"].pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
        # 分類(EN) / アイテム(EN): マスタの表示のみ
        if slot.get("lbl_slot_cat_en"):
            if category and category != "(なし)":
                cat_info = self.category_master.get(category)
                if isinstance(cat_info, dict):
                    cat_en = (cat_info.get("name_en", "") or cat_info.get("name_jp", "") or "").strip()
                    slot["lbl_slot_cat_en"].configure(text=cat_en or "—")
                else:
                    slot["lbl_slot_cat_en"].configure(text="—")
            else:
                slot["lbl_slot_cat_en"].configure(text="—")
        if input_type == "qty_only":
            if slot.get("lbl_slot_item_en"):
                if category and category != "(なし)" and isinstance(self.category_master.get(category), dict):
                    ci = self.category_master[category]
                    qen = (ci.get("name_en", "") or ci.get("name_jp", "") or "").strip()
                    slot["lbl_slot_item_en"].configure(text=qen or "—")
                else:
                    slot["lbl_slot_item_en"].configure(text="—")
        else:
            self._update_slot_item_en_display(slot)

        # カテゴリレベルで属性がある場合（例: LEMのランク）はここでウィジェット生成
        if input_type == "item_select" and category and category != "(なし)":
            cat_info = self.category_master.get(category)
            if isinstance(cat_info, dict) and cat_info.get("attributes"):
                attrs = cat_info["attributes"]
                if attrs:
                    slot["attr_frame"].pack(
                        fill="x",
                        padx=BOX_PADX,
                        pady=(0, BOX_PADY),
                        before=slot["row_frame_actions"],
                    )
                    attr_row = tk.Frame(slot["attr_frame"], bg=BOX_FG)
                    attr_row.pack(fill="x", padx=BOX_PADX, pady=5)
                    for attr_key, attr_data in attrs.items():
                        attr_item_frame = ctk.CTkFrame(attr_row, fg_color="transparent")
                        attr_item_frame.pack(side="left", padx=10)
                        ctk.CTkLabel(attr_item_frame, text=f"{attr_key}:", font=("Meiryo", 10)).pack(side="left", padx=2)
                        if isinstance(attr_data, list):
                            attr_data = {"type": "select", "options": attr_data}
                        attr_type = attr_data.get("type", "select") if isinstance(attr_data, dict) else "select"
                        if attr_type == "fixed":
                            fixed_val = attr_data.get("value", "")
                            lbl = ctk.CTkLabel(attr_item_frame, text=str(fixed_val), font=("Meiryo", 9, "bold"), text_color="#3498db")
                            lbl.pack(side="left", padx=2)
                            slot["attr_widgets"][attr_key] = {"type": "fixed", "value": fixed_val}
                        elif attr_type == "number":
                            ent = ctk.CTkEntry(attr_item_frame, width=100, height=28)
                            ent.pack(side="left", padx=2)
                            init_val = attr_data.get("value", "")
                            if init_val is not None:
                                ent.insert(0, str(init_val))
                            ent.bind("<KeyRelease>", lambda e, sf=slot_frame: self._schedule_pin_preview_refresh())
                            slot["attr_widgets"][attr_key] = {"type": "number", "widget": ent}
                        else:
                            options = attr_data.get("options", []) if isinstance(attr_data, dict) else attr_data
                            cmb = ctk.CTkComboBox(attr_item_frame, values=["(なし)"] + options, width=120)
                            cmb.set("(なし)")
                            cmb.pack(side="left", padx=2)
                            cmb.configure(command=lambda v, sf=slot_frame: self._schedule_pin_preview_refresh())
                            slot["attr_widgets"][attr_key] = {"type": "select", "widget": cmb}

        self._repack_category_slot_actions_bottom(slot)
        if not getattr(self, "_suppress_special_notes_rebuild", False):
            self._rebuild_pin_special_notes_ui()
        self._schedule_pin_preview_refresh()

    def on_slot_item_changed(self, slot_frame):
        """スロットのアイテム変更時: カテゴリに属性がなければ、item_master の attributes に応じてウィジェットを生成。"""
        slot = None
        for s in self.category_slots:
            if s["frame"] == slot_frame:
                slot = s
                break
        if not slot:
            return
        category = slot["category"].get()
        item_name = slot["item"].get()
        # カテゴリが属性を持っている場合（例: LEMのランク）は触らない
        cat_has_attrs = False
        if category and category in self.category_master:
            cat_info = self.category_master[category]
            if isinstance(cat_info, dict) and cat_info.get("attributes"):
                cat_has_attrs = True
        if cat_has_attrs:
            self._update_slot_item_en_display(slot)
            self._schedule_pin_preview_refresh()
            return
        
        # 属性フレームをクリア（カテゴリ属性はないのでアイテム属性用）
        slot["attr_frame"].pack_forget()
        for w in slot["attr_frame"].winfo_children(): w.destroy()
        slot["attr_widgets"] = {}
        
        if category == "(なし)" or item_name == "(なし)" or not category or not item_name:
            self._update_slot_item_en_display(slot)
            self._schedule_pin_preview_refresh()
            return
        if category not in self.item_master:
            self._update_slot_item_en_display(slot)
            self._schedule_pin_preview_refresh()
            return
        
        # 選択されたアイテムの属性を取得
        target_info = None
        target_id = None
        for i_id, info in self.item_master[category].items():
            if info["name_jp"] == item_name:
                target_info = info
                target_id = i_id
                break
        
        if target_info and "attributes" in target_info:
            attrs = target_info["attributes"]
            if attrs:
                # 属性がある場合のみフレームを表示
                slot["attr_frame"].pack(
                    fill="x",
                    padx=BOX_PADX,
                    pady=(0, BOX_PADY),
                    before=slot["row_frame_actions"],
                )

                attr_row = tk.Frame(slot["attr_frame"], bg=BOX_FG)
                attr_row.pack(fill="x", padx=BOX_PADX, pady=5)

                for attr_key, attr_data in attrs.items():
                    attr_item_frame = ctk.CTkFrame(attr_row, fg_color="transparent")
                    attr_item_frame.pack(side="left", padx=10)
                    ctk.CTkLabel(attr_item_frame, text=f"{attr_key}:", font=("Meiryo", 10)).pack(side="left", padx=2)

                    if isinstance(attr_data, list):
                        attr_data = {"type": "select", "options": attr_data}

                    attr_type = attr_data.get("type", "select") if isinstance(attr_data, dict) else "select"

                    if attr_type == "fixed":
                        fixed_val = attr_data.get("value", "")
                        lbl = ctk.CTkLabel(attr_item_frame, text=str(fixed_val), font=("Meiryo", 9, "bold"), text_color="#3498db")
                        lbl.pack(side="left", padx=2)
                        slot["attr_widgets"][attr_key] = {"type": "fixed", "value": fixed_val}
                    elif attr_type == "number":
                        ent = ctk.CTkEntry(attr_item_frame, width=100, height=28)
                        ent.pack(side="left", padx=2)
                        init_val = attr_data.get("value", "")
                        if init_val is not None:
                            ent.insert(0, str(init_val))
                        ent.bind("<KeyRelease>", lambda e, sf=slot_frame: self._schedule_pin_preview_refresh())
                        slot["attr_widgets"][attr_key] = {"type": "number", "widget": ent}
                    else:  # select
                        options = attr_data.get("options", []) if isinstance(attr_data, dict) else attr_data
                        cmb = ctk.CTkComboBox(attr_item_frame, values=["(なし)"] + options, width=120)
                        cmb.set("(なし)")
                        cmb.pack(side="left", padx=2)
                        cmb.configure(command=lambda v, sf=slot_frame: self._schedule_pin_preview_refresh())
                        slot["attr_widgets"][attr_key] = {"type": "select", "widget": cmb}
        self._repack_category_slot_actions_bottom(slot)
        self._update_slot_item_en_display(slot)
        self._schedule_pin_preview_refresh()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=380)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=260)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg="#12131a", highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        # サイドバーはやや細くして、マップエリアを広く確保
        self.sidebar = ctk.CTkFrame(self, width=420, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        # 右: 埋め込み map.js 相当のピン表示プレビュー（読み取り専用）
        self.preview_sidebar = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color="#252526")
        self.preview_sidebar.grid(row=0, column=2, sticky="nsew")
        ctk.CTkLabel(
            self.preview_sidebar, text="ピン表示プレビュー", font=("Meiryo", 13, "bold"),
        ).pack(anchor="w", padx=10, pady=(12, 2))
        ctk.CTkLabel(
            self.preview_sidebar,
            text="map.js と同じ表示ルール（ツールチップ／ポップアップ・JP/EN）。編集不可。",
            font=("Meiryo", 9), text_color="#95a5a6", wraplength=248, justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 6))
        ps_scroll = ctk.CTkScrollableFrame(self.preview_sidebar, fg_color="transparent")
        ps_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        def _preview_readonly_block(parent, title, h):
            ctk.CTkLabel(parent, text=title, font=("Meiryo", 10, "bold")).pack(anchor="w", pady=(10, 2))
            tb = ctk.CTkTextbox(parent, height=h, font=("Meiryo", 10), wrap="word")
            tb.pack(fill="x", pady=(0, 2))
            tb.configure(state="disabled")
            return tb

        self._pin_preview_hover_jp = _preview_readonly_block(ps_scroll, "カーソルオーバー（日本語）", 96)
        self._pin_preview_hover_en = _preview_readonly_block(ps_scroll, "カーソルオーバー（English）", 96)
        self._pin_preview_popup_jp = _preview_readonly_block(ps_scroll, "クリック時ポップアップ（日本語）", 200)
        self._pin_preview_popup_en = _preview_readonly_block(ps_scroll, "クリック時ポップアップ（English）", 200)
        self._clear_pin_site_preview("ピンを選択するか新規設置すると、ここに埋め込み表示のプレビューが出ます。")
        self._preview_sidebar_column_minsize = 260
        self.show_preview_sidebar_var = tk.BooleanVar(value=True)

        self.f_coords_bar = ctk.CTkFrame(self.sidebar, fg_color="#34495e", corner_radius=0)
        self.f_coords_bar.pack(fill="x")
        self.lbl_coords = ctk.CTkLabel(
            self.f_coords_bar, text="座標: ---", font=("Meiryo", 16, "bold"),
        )
        self.lbl_coords.pack(pady=(14, 14), padx=12)

        self.scroll_body = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_body.pack(expand=True, fill="both", padx=10, pady=10)

        # ピン・エリアの「ブラウズ」モード用（フォームと同じスクロール内の別枠）。ピン編集モード時は枠ごと非表示。
        self.f_mode_browse = ctk.CTkFrame(
            self.scroll_body,
            fg_color=BOX_FG,
            corner_radius=BOX_CORNER,
            border_width=BOX_BORDER_WIDTH,
            border_color=BOX_BORDER_COLOR,
        )
        ctk.CTkLabel(
            self.f_mode_browse,
            text="▼ ピン・エリア",
            font=("Meiryo", 12, "bold"),
        ).pack(anchor="w", padx=BOX_PADX, pady=(BOX_PADY, 4))
        ctk.CTkLabel(
            self.f_mode_browse,
            text="待機中は追加から開始。ピンを編集中はこの枠は表示されません。",
            font=("Meiryo", 9),
            text_color="#bdc3c7",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", padx=BOX_PADX, pady=(0, 6))

        self.f_quick_idle = ctk.CTkFrame(self.f_mode_browse, fg_color="transparent")
        self.btn_add_pin = ctk.CTkButton(
            self.f_quick_idle, text="ピンを追加", command=self._start_add_pin_flow,
            fg_color="#2980b9", height=32, font=("Meiryo", 12, "bold"),
        )
        self.btn_add_pin.pack(fill="x", pady=2)
        self.btn_add_area = ctk.CTkButton(
            self.f_quick_idle, text="エリアを追加", command=self._start_add_area_flow,
            fg_color="#16a085", height=32, font=("Meiryo", 12, "bold"),
        )
        self.btn_add_area.pack(fill="x", pady=2)

        self.f_area_tools = ctk.CTkFrame(self.f_mode_browse, fg_color="#2e4053", corner_radius=6)
        ctk.CTkLabel(
            self.f_area_tools, text="エリア（地図で描画）", font=("Meiryo", 9), text_color="#bdc3c7",
        ).pack(anchor="w", padx=6, pady=(4, 2))
        r1 = ctk.CTkFrame(self.f_area_tools, fg_color="transparent")
        r1.pack(fill="x", padx=4, pady=(2, 1))
        r2 = ctk.CTkFrame(self.f_area_tools, fg_color="transparent")
        r2.pack(fill="x", padx=4, pady=1)
        r3 = ctk.CTkFrame(self.f_area_tools, fg_color="transparent")
        r3.pack(fill="x", padx=4, pady=1)
        r4 = ctk.CTkFrame(self.f_area_tools, fg_color="transparent")
        r4.pack(fill="x", padx=4, pady=1)
        r5 = ctk.CTkFrame(self.f_area_tools, fg_color="transparent")
        r5.pack(fill="x", padx=4, pady=(1, 6))
        self.btn_area_edit_toggle = ctk.CTkButton(
            r1, text="編集: ON", command=self.toggle_area_edit_enabled, width=68, height=26, fg_color="#2ecc71",
        )
        self.btn_area_edit_toggle.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_point_toggle = ctk.CTkButton(
            r1, text="制御点: ON", command=self.toggle_area_points, width=84, height=26, fg_color="#34495e",
        )
        self.btn_area_point_toggle.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_poly = ctk.CTkButton(
            r2, text="多角形", command=lambda: self.set_area_mode("create_polygon"), width=56, height=26, fg_color="#1abc9c",
        )
        self.btn_area_poly.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_close_poly = ctk.CTkButton(
            r2, text="多角形確定", command=self.finalize_polygon_area, width=78, height=26, fg_color="#16a085",
        )
        self.btn_area_close_poly.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_circle = ctk.CTkButton(
            r3, text="円", command=lambda: self.set_area_mode("create_circle"), width=36, height=26, fg_color="#2980b9",
        )
        self.btn_area_circle.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_rect = ctk.CTkButton(
            r3, text="四角", command=lambda: self.set_area_mode("create_rect"), width=44, height=26, fg_color="#8e44ad",
        )
        self.btn_area_rect.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_edit_points = ctk.CTkButton(
            r4, text="点編集", command=self.start_edit_polygon_mode, width=56, height=26, fg_color="#2c3e50",
        )
        self.btn_area_edit_points.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_rot_ccw = ctk.CTkButton(
            r4, text="↺10°", command=lambda: self.rotate_current_area(-10), width=48, height=26, fg_color="#7f8c8d",
        )
        self.btn_area_rot_ccw.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_rot_cw = ctk.CTkButton(
            r4, text="↻10°", command=lambda: self.rotate_current_area(10), width=48, height=26, fg_color="#7f8c8d",
        )
        self.btn_area_rot_cw.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_save = ctk.CTkButton(
            r5, text="エリア保存", command=self.save_current_area, width=72, height=26, fg_color="#27ae60",
        )
        self.btn_area_save.pack(side="left", padx=1, fill="x", expand=True)
        self.btn_area_delete = ctk.CTkButton(
            r5, text="削除", command=self.delete_current_area, width=48, height=26, fg_color="#c0392b",
        )
        self.btn_area_delete.pack(side="left", padx=1, fill="x", expand=True)

        self.f_area_tools.pack_forget()
        self.f_quick_idle.pack_forget()

        # 属性マッピング（JP/EN対応）
        self.attr_mapping = self.config.get("attr_mapping", {})
        # 後方互換性
        if not self.attr_mapping:
            old_cat_mapping = self.config.get("cat_mapping", {})
            if old_cat_mapping:
                self.attr_mapping = {k: {"name_jp": v, "name_en": ""} for k, v in old_cat_mapping.items()}
        
        self._rebuild_pin_cat_mapping()
        
        # カテゴリマスタ（JP/EN + 属性項目）
        self.category_master = self.config.get("category_master", {})
        if not self.category_master:
            old_list = self.config.get("category_list", [])
            if old_list:
                self.category_master = {cat: {"name_jp": cat, "name_en": "", "attributes": {}} for cat in old_list if cat}
        self.category_list = list(self.category_master.keys())
        
        self.item_master = self.config.get("item_master", {})
        self.display_names = list(self.cat_mapping.values())
        self.show_incomplete_only = tk.BooleanVar(value=False)
        self.pin_filter_object_vars = {}
        self.pin_filter_cat_vars = {}
        self.pin_filter_item_vars = {}
        self._sync_pin_filter_vars_from_masters()

        # ピン編集ブロック（「ピンを追加」→地図クリック、または既存ピン選択時のみ表示）
        self.f_pin_editor = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        self.f_pin_toolbar = ctk.CTkFrame(self.f_pin_editor, fg_color="transparent")
        self.f_pin_toolbar.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            self.f_pin_toolbar, text="選択解除", command=self._dismiss_pin_editing,
            fg_color="#7f8c8d", height=30, font=("Meiryo", 11),
        ).pack(fill="x")

        # 地点の名称〜カテゴリ/アイテムまでをカード1枚にまとめる（スロットの ridge 枠と同系の見た目）
        self.f_pin_form_card = ctk.CTkFrame(
            self.f_pin_editor, fg_color=BOX_FG, corner_radius=BOX_CORNER,
            border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR,
        )
        self.f_pin_form_card.pack(fill="x", padx=4, pady=(0, 8))

        ctk.CTkLabel(self.f_pin_form_card, text="▼ 地点の名称", font=("Meiryo", 12, "bold")).pack(anchor="w", padx=BOX_PADX, pady=(BOX_PADY, 4))
        ctk.CTkLabel(
            self.f_pin_form_card,
            text="マップ上の表示名を変えたいときだけ入力。空が通常（オブジェクト／アイテムのマスタ名がそのまま使われます）。",
            font=("Meiryo", 9), text_color="#bdc3c7",
        ).pack(anchor="w", padx=BOX_PADX, pady=(0, 4))
        f_row_jp = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        f_row_jp.pack(fill="x", padx=BOX_PADX, pady=2)
        ctk.CTkLabel(f_row_jp, text="JP:", width=32, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(0, 5))
        self.ent_name_jp = ctk.CTkEntry(f_row_jp, height=28, placeholder_text="通常は空（別名にするときのみ）")
        self.ent_name_jp.pack(side="left", fill="x", expand=True)
        f_row_en = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        f_row_en.pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
        ctk.CTkLabel(f_row_en, text="EN:", width=32, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(0, 5))
        self.ent_name_en = ctk.CTkEntry(f_row_en, height=28, placeholder_text="通常は空（別名にするときのみ）")
        self.ent_name_en.pack(side="left", fill="x", expand=True)
        self.ent_name_jp.bind("<KeyRelease>", lambda e: self._schedule_pin_preview_refresh())
        self.ent_name_en.bind("<KeyRelease>", lambda e: self._schedule_pin_preview_refresh())

        ctk.CTkLabel(self.f_pin_form_card, text="▼ オブジェクト（見た目・外形）", font=("Meiryo", 12, "bold")).pack(anchor="w", padx=BOX_PADX, pady=(10, 0))
        self.f_attr = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        self.f_attr.pack(fill="x", padx=BOX_PADX, pady=5)
        f_attr_row = ctk.CTkFrame(self.f_attr, fg_color="transparent")
        f_attr_row.pack(fill="x", padx=BOX_PADX, pady=BOX_PADY)
        ctk.CTkLabel(f_attr_row, text="オブジェクト:", width=80, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(0,5))
        self.cmb_attribute = ctk.CTkComboBox(f_attr_row, values=["(なし)"] + self.display_names, width=280, command=lambda v: self.on_attribute_changed())
        self.cmb_attribute.pack(side="left", fill="x", expand=True)
        self.cmb_attribute.set("(なし)")
        # オブジェクトのEN（任意・空ならマスタの値）
        f_attr_en = ctk.CTkFrame(self.f_attr, fg_color="transparent")
        f_attr_en.pack(fill="x", padx=BOX_PADX, pady=(0,BOX_PADY))
        ctk.CTkLabel(f_attr_en, text="オブジェクト(EN):", width=100, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(0,5))
        self.ent_obj_en = ctk.CTkEntry(f_attr_en, height=28, placeholder_text="空ならマスタの値を使用")
        self.ent_obj_en.pack(side="left", fill="x", expand=True)
        self.ent_obj_en.bind("<KeyRelease>", lambda e: self._schedule_pin_preview_refresh())

        self.f_pin_special_notes = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        # 特記事項はルールがあるときだけ pack（空枠で隙間を作らない）

        # オブジェクト属性フレーム（遺体の場所など）- 初期は非表示
        self.obj_attr_frame = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        # packしない - 属性がある場合のみshow_object_attributesで表示
        self.obj_attr_widgets = {}

        # カテゴリスロット（複数選択可能）— 初期は 0 件。「＋ 追加」で増やし、各スロットの「削除」で消す
        self.f_cat_header = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        self.f_cat_header.pack(fill="x", padx=BOX_PADX, pady=(10, 0), after=self.f_attr)
        ctk.CTkLabel(self.f_cat_header, text="▼ 中身の分類（カテゴリ）", font=("Meiryo", 12, "bold")).pack(side="left")
        # ボタンは左側ラベルと重ならないよう右側にまとめ、幅を十分に取る
        f_cat_btns = ctk.CTkFrame(self.f_cat_header, fg_color="transparent")
        f_cat_btns.pack(side="right")
        self.btn_add_category = ctk.CTkButton(f_cat_btns, text="＋ 追加", command=self.add_category_slot, width=100, fg_color="#3498db", height=28)
        self.btn_add_category.pack(side="left", padx=2)
        ctk.CTkButton(f_cat_btns, text="📋 定型から作成", command=self.open_template_dialog, width=130, fg_color="#8e44ad", height=28).pack(side="left", padx=2)
        
        self.category_slots_frame = ctk.CTkFrame(self.f_pin_form_card, fg_color="transparent")
        self.category_slots_frame.pack(fill="x", padx=BOX_PADX, pady=5, after=self.f_cat_header)
        self.category_slots = []
        self.update_category_list_for_pin_object("loot", "")
        self._sync_pin_special_notes_pack_order()

        # 重要度選択
        f_importance = ctk.CTkFrame(self.f_pin_editor, fg_color="transparent")
        f_importance.pack(fill="x", padx=4, pady=(10, 0))
        ctk.CTkLabel(f_importance, text="▼ 重要度", font=("Meiryo", 12, "bold")).pack(side="left")
        self.cmb_importance = ctk.CTkComboBox(f_importance, values=["(なし)", "1", "2", "3", "4", "5"], width=100)
        self.cmb_importance.pack(side="left", padx=10)
        self.cmb_importance.set("(なし)")

        self.f_parent_pin = ctk.CTkFrame(self.f_pin_editor, fg_color="transparent")
        self.f_parent_pin.pack(fill="x", padx=4, pady=(10, 0))
        ctk.CTkLabel(self.f_parent_pin, text="▼ 親ピン", font=("Meiryo", 12, "bold")).pack(anchor="w")
        fp_row = ctk.CTkFrame(self.f_parent_pin, fg_color="transparent")
        fp_row.pack(fill="x", pady=4)
        self.btn_parent_pick = ctk.CTkButton(
            fp_row,
            text="親ピンを設定",
            width=120,
            command=self._begin_parent_pick_mode,
            fg_color="#2d5a8a",
        )
        self.btn_parent_pick.pack(side="left", padx=(0, 6))
        self.btn_parent_clear = ctk.CTkButton(
            fp_row,
            text="親を解除",
            width=90,
            command=self._clear_parent_pin,
            fg_color="#555555",
        )
        self.btn_parent_clear.pack(side="left")
        fp_type_row = ctk.CTkFrame(self.f_parent_pin, fg_color="transparent")
        fp_type_row.pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(fp_type_row, text="タイプ", width=70, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(2, 4))
        self.cmb_parent_type = ctk.CTkComboBox(
            fp_type_row,
            values=list(PARENT_TYPE_LABELS.values()),
            width=220,
            command=lambda _v: self._on_parent_type_changed(),
        )
        self.cmb_parent_type.pack(side="left")
        self.cmb_parent_type.set(PARENT_TYPE_LABELS[PARENT_TYPE_DEFAULT])
        self.lbl_parent_info = ctk.CTkLabel(
            self.f_parent_pin,
            text="現在: —",
            font=("Meiryo", 10),
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self.lbl_parent_info.pack(anchor="w", padx=2)
        self.lbl_parent_mode = ctk.CTkLabel(
            self.f_parent_pin,
            text="",
            font=("Meiryo", 10),
            text_color="#5dade2",
            anchor="w",
        )
        self.lbl_parent_mode.pack(anchor="w", padx=2)

        self.link_settings_expanded = False
        self.lbl_link_toggle = ctk.CTkLabel(
            self.f_pin_editor, text="▶ リンク設定", font=("Meiryo", 12, "bold"), cursor="hand2"
        )
        self.lbl_link_toggle.pack(anchor="w", padx=4, pady=(10, 0))
        self.lbl_link_toggle.bind("<Button-1>", lambda e: self._toggle_link_settings_section())
        self.f_link_body = ctk.CTkFrame(
            self.f_pin_editor, fg_color=BOX_FG, corner_radius=BOX_CORNER,
            border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR
        )
        ctk.CTkLabel(
            self.f_link_body, text="埋め込みマップのポップアップに「詳細ガイド」リンクとして出します（http/https のみ）。",
            font=("Meiryo", 9), text_color="#bdc3c7"
        ).pack(anchor="w", padx=BOX_PADX, pady=(BOX_PADY, 4))
        f_pick = ctk.CTkFrame(self.f_link_body, fg_color="transparent")
        f_pick.pack(fill="x", padx=BOX_PADX, pady=2)
        ctk.CTkLabel(f_pick, text="ページ候補", width=100, anchor="w", font=("Meiryo", 10)).pack(side="left")
        self.cmb_link_pick_jp = ctk.CTkComboBox(f_pick, values=[GUIDE_LINK_PICK_NONE], width=200, command=lambda v: self._on_link_combo_selected("jp"))
        self.cmb_link_pick_jp.set(GUIDE_LINK_PICK_NONE)
        self.cmb_link_pick_jp.pack(side="left", padx=4)
        self.cmb_link_pick_en = ctk.CTkComboBox(f_pick, values=[GUIDE_LINK_PICK_NONE], width=200, command=lambda v: self._on_link_combo_selected("en"))
        self.cmb_link_pick_en.set(GUIDE_LINK_PICK_NONE)
        self.cmb_link_pick_en.pack(side="left", padx=4)
        ctk.CTkButton(f_pick, text="候補を再読込", width=100, command=self._refresh_guide_page_links_from_disk, fg_color="#34495e").pack(side="left", padx=6)
        f_lj = ctk.CTkFrame(self.f_link_body, fg_color="transparent")
        f_lj.pack(fill="x", padx=BOX_PADX, pady=2)
        ctk.CTkLabel(f_lj, text="URL (JP)", width=72, anchor="w", font=("Meiryo", 10)).pack(side="left")
        self.ent_link_jp = ctk.CTkEntry(f_lj, height=28, placeholder_text="https://...")
        self.ent_link_jp.pack(side="left", fill="x", expand=True)
        f_le = ctk.CTkFrame(self.f_link_body, fg_color="transparent")
        f_le.pack(fill="x", padx=BOX_PADX, pady=(2, BOX_PADY))
        ctk.CTkLabel(f_le, text="URL (EN)", width=72, anchor="w", font=("Meiryo", 10)).pack(side="left")
        self.ent_link_en = ctk.CTkEntry(f_le, height=28, placeholder_text="https://...")
        self.ent_link_en.pack(side="left", fill="x", expand=True)
        self.ent_link_jp.bind("<KeyRelease>", lambda e: self.mark_dirty())
        self.ent_link_en.bind("<KeyRelease>", lambda e: self.mark_dirty())
        self._guide_page_links_cache = []
        self._refresh_guide_page_links_from_disk()

        self.txt_memo_jp = self.create_textbox("▼ 詳細メモ（日本語）", parent=self.f_pin_editor)
        self.txt_memo_en = self.create_textbox("▼ Memo (English)", parent=self.f_pin_editor)
        self.txt_memo_jp.bind("<KeyRelease>", lambda e: self._schedule_pin_preview_refresh())
        self.txt_memo_en.bind("<KeyRelease>", lambda e: self._schedule_pin_preview_refresh())

        f_foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_foot.pack(fill="x", side=tk.BOTTOM, padx=20, pady=20)
        self.setup_menu_bar()

        # ピン保存・削除（クロップより上。保存を上に）
        self.f_pin_foot_block = ctk.CTkFrame(f_foot, fg_color="transparent")
        self.f_pin_foot_block.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            self.f_pin_foot_block,
            text="ピン保存 (Ctrl+Enter)",
            command=self.save_data,
            fg_color="#2980b9",
            height=50,
            font=("Meiryo", 14, "bold"),
        ).pack(fill="x", pady=(0, 6))
        self.btn_delete = ctk.CTkButton(
            self.f_pin_foot_block,
            text="🗑️ ピン削除",
            command=self.delete_data,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            height=35,
        )
        self.btn_delete.pack(fill="x")

        f_crop = ctk.CTkFrame(f_foot, fg_color=BOX_FG, corner_radius=BOX_CORNER, border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR)
        self.f_crop_outer = f_crop
        f_crop.pack(fill="x", pady=10)
        self.btn_crop_mode = ctk.CTkButton(f_crop, text="✂ クロップ開始", command=self.toggle_crop_mode, fg_color="#e67e22", width=140); self.btn_crop_mode.pack(side=tk.LEFT, padx=10, pady=10)
        self.btn_crop_exec = ctk.CTkButton(f_crop, text="保存実行", command=self.execute_crop, state="disabled", fg_color="#27ae60", width=100); self.btn_crop_exec.pack(side=tk.LEFT, pady=10)
        f_ann = ctk.CTkFrame(f_foot, fg_color="transparent"); f_ann.pack(fill="x")
        self.btn_here = ctk.CTkButton(f_ann, text="Here!", command=lambda: self.set_tool("here"), state="disabled", width=100, fg_color="#3b8ed0"); self.btn_here.pack(side=tk.LEFT, padx=2)
        self.btn_arrow = ctk.CTkButton(f_ann, text="矢印", command=lambda: self.set_tool("arrow"), state="disabled", width=100, fg_color="#3b8ed0"); self.btn_arrow.pack(side=tk.LEFT, padx=2)

        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._apply_zoom_at_canvas_point(e.x, e.y, 120.0))
        self.canvas.bind("<Button-5>", lambda e: self._apply_zoom_at_canvas_point(e.x, e.y, -120.0))
        self.canvas.bind("<Button-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        self.canvas.bind("<Button-2>", self.toggle_autoscroll)
        self.bind("<Control-Return>", lambda e: self.save_data())
        self.bind("<Delete>", lambda e: self.delete_data())
        self.bind("<Escape>", lambda e: self._on_escape_editor())
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 初期はピン編集オフ（保存・削除はピン選択時のみ表示）
        self.f_pin_foot_block.pack_forget()
        self._refresh_sidebar_top_toolbar()

    def create_input(self, label, parent=None):
        p = parent or self.scroll_body
        ctk.CTkLabel(p, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        ent = ctk.CTkEntry(p, height=35); ent.pack(fill="x", padx=20, pady=5)
        return ent

    def create_textbox(self, label, parent=None):
        p = parent or self.scroll_body
        px = 4 if parent is not None else 20
        ctk.CTkLabel(p, text=label).pack(anchor="w", padx=px, pady=(10, 0))
        txt = ctk.CTkTextbox(p, height=100); txt.pack(fill="x", padx=px, pady=5)
        return txt

    def _refresh_sidebar_top_toolbar(self):
        """ブラウズ枠（追加・エリアツール）とピン編集フォームのモード切替。ピン編集中は枠ごと非表示。"""
        fb = getattr(self, "f_mode_browse", None)
        fq = getattr(self, "f_quick_idle", None)
        fa = getattr(self, "f_area_tools", None)
        if fq is None or fa is None:
            return
        pin_placement = getattr(self, "_pin_placement_active", False)
        aid = (getattr(self, "current_area_uid", None) or "").strip()
        panel_open = getattr(self, "_pin_editor_panel_open", False)
        # pack 直後は winfo_ismapped が False になり得るため、意図フラグで判定する。
        # エリアプロパティ表示中は current_area_uid があり、ブラウズ枠（エリアツール）を出す。
        pin_sidebar_editing = pin_placement or (panel_open and not aid)
        area_ctx = self.area_mode != "idle" or bool(aid)

        if pin_sidebar_editing:
            if fb is not None:
                try:
                    fb.pack_forget()
                except tk.TclError:
                    pass
            fq.pack_forget()
            fa.pack_forget()
            return

        if fb is not None:
            try:
                fb.pack_forget()
            except tk.TclError:
                pass
            try:
                fb.pack(fill="x", padx=0, pady=(0, 8), before=self.f_pin_editor)
            except tk.TclError:
                fb.pack(fill="x", padx=0, pady=(0, 8))

        if area_ctx:
            fq.pack_forget()
            fa.pack(fill="x", padx=BOX_PADX, pady=(0, BOX_PADY))
        else:
            fa.pack_forget()
            fq.pack(fill="x", padx=BOX_PADX, pady=(0, BOX_PADY))

    def _show_pin_editor_panel(self):
        self._pin_editor_panel_open = True
        if getattr(self, "f_pin_editor", None):
            self.f_pin_editor.pack(fill="both", expand=True, pady=(0, 4))
        if getattr(self, "f_pin_foot_block", None) and getattr(self, "f_crop_outer", None):
            self.f_pin_foot_block.pack(fill="x", pady=(0, 10), before=self.f_crop_outer)
        self._refresh_sidebar_top_toolbar()

    def _scroll_sidebar_editor_to_top(self):
        sb = getattr(self, "scroll_body", None)
        if not sb:
            return
        cv = getattr(sb, "_parent_canvas", None)
        if cv is None:
            return
        try:
            cv.yview_moveto(0.0)
        except Exception:
            pass

    def _hide_pin_editor_idle(self):
        self._pin_editor_panel_open = False
        self._editing_pin_drag_active = False
        if getattr(self, "f_pin_editor", None):
            self.f_pin_editor.pack_forget()
        if getattr(self, "f_pin_foot_block", None):
            self.f_pin_foot_block.pack_forget()
        self._clear_pin_site_preview()
        self._refresh_sidebar_top_toolbar()
        self._scroll_sidebar_editor_to_top()

    def _start_add_pin_flow(self):
        if not self._confirm_pin_edit_discard_or_save():
            return
        self._remove_draft_pin_row_if_any()
        if self.area_mode in ("create_polygon", "create_circle", "create_rect", "edit_polygon"):
            self.set_area_mode("idle")
        self._pin_placement_active = True
        self.current_uid = None
        self.temp_coords = None
        self._reset_pin_form_widgets()
        self._hide_pin_editor_idle()
        self.lbl_coords.configure(text="ピン: 地図上で設置位置をクリック")
        self.refresh_map()

    def _start_add_area_flow(self):
        if not self._confirm_pin_edit_discard_or_save():
            return
        self._pin_placement_active = False
        self.temp_coords = None
        self.current_uid = None
        self._reset_pin_form_widgets()
        self._hide_pin_editor_idle()
        if not self.area_edit_enabled.get():
            self.area_edit_enabled.set(True)
            self.btn_area_edit_toggle.configure(text="編集: ON", fg_color="#2ecc71")
        self.set_area_mode("create_polygon")
        self.lbl_coords.configure(text="エリア: 地図で頂点をクリック → 上部の「多角形確定」")
        self.refresh_map()

    def _dismiss_pin_editing(self):
        if not self._confirm_pin_edit_discard_or_save():
            return
        self._remove_draft_pin_row_if_any()
        self._pin_placement_active = False
        self.temp_coords = None
        if self.area_mode in ("create_polygon", "create_circle", "create_rect", "edit_polygon"):
            self.set_area_mode("idle")
        self.current_uid = None
        self.current_area_uid = None
        self._reset_pin_form_widgets()
        self._hide_pin_editor_idle()
        self.lbl_coords.configure(text="座標: ---")
        self.refresh_map()

    def _reset_pin_form_widgets(self):
        self.cmb_attribute.set("(なし)")
        self.cmb_importance.set("(なし)")
        self.ent_name_jp.delete(0, "end")
        self.ent_name_en.delete(0, "end")
        if getattr(self, "ent_obj_en", None):
            self.ent_obj_en.delete(0, "end")
        if getattr(self, "ent_link_jp", None):
            self.ent_link_jp.delete(0, "end")
            self.ent_link_en.delete(0, "end")
        if getattr(self, "cmb_link_pick_jp", None):
            self.cmb_link_pick_jp.set(GUIDE_LINK_PICK_NONE)
            self.cmb_link_pick_en.set(GUIDE_LINK_PICK_NONE)
        if getattr(self, "link_settings_expanded", False) and getattr(self, "f_link_body", None):
            self.link_settings_expanded = False
            self.f_link_body.pack_forget()
            if getattr(self, "lbl_link_toggle", None):
                self.lbl_link_toggle.configure(text="▶ リンク設定")
        self.txt_memo_jp.delete("1.0", tk.END)
        self.txt_memo_en.delete("1.0", tk.END)
        if getattr(self, "cmb_parent_type", None):
            self.cmb_parent_type.set(PARENT_TYPE_LABELS[PARENT_TYPE_DEFAULT])
            self.cmb_parent_type.configure(state="disabled")
        self.obj_attr_frame.pack_forget()
        for w in self.obj_attr_frame.winfo_children():
            w.destroy()
        self.obj_attr_widgets = {}
        if getattr(self, "f_pin_special_notes", None):
            for w in self.f_pin_special_notes.winfo_children():
                w.destroy()
        self._sync_pin_special_notes_pack_order()
        rev = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev.get(self.cmb_attribute.get(), "")
        obj_type = "loot"
        if attr_id and attr_id in self.attr_mapping:
            o = self.attr_mapping[attr_id]
            if isinstance(o, dict):
                obj_type = o.get("type", "loot")
        self.update_category_list_for_pin_object(obj_type, attr_id)
        for slot in self.category_slots[:]:
            self.delete_category_slot(slot["frame"])

    def open_settings(self): SettingsWindow(self, self.config_path, self.config)

    def open_skill_name_master_window(self):
        category_special_notes.SkillNameMasterWindow(self)

    def open_category_special_notes_window(self):
        category_special_notes.CategorySpecialNotesWindow(self)

    def open_view_preset_window(self):
        ViewPresetWindow(self)

    def get_ratio(self): return ((2 ** self.zoom) * 256) / self.orig_max_dim

    def _parse_categories_for_pin(self, d):
        raw = d.get("categories")
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                data = json.loads(raw)
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                return []
        return []

    def _editor_apply_pin_marker_partial(self, pin, pm):
        if not isinstance(pm, dict):
            return
        touched = False
        sid = (pm.get("svg_icon_id") or "").strip()
        if sid:
            pin["svg_icon_id"] = sid
            touched = True
        scp = (pm.get("svg_icon_scope") or "").strip()
        if scp:
            pin["svg_icon_scope"] = scp
        ic = (pm.get("icon_color") or "").strip()
        if re.match(r"^#[0-9a-fA-F]{6}$", ic):
            pin["marker_icon_color"] = ic
            touched = True
        bg = (pm.get("background_color") or "").strip()
        if re.match(r"^#[0-9a-fA-F]{6}$", bg):
            pin["marker_bg_color"] = bg
            touched = True
        # 旧キー marker_display_style も許容
        ds = (pm.get("display_style") or pm.get("marker_display_style") or "").strip()
        if ds:
            pin["marker_display_style"] = normalize_marker_display_style(ds)
        elif touched:
            # 明示エントリで display_style が空なら standard 扱い
            pin["marker_display_style"] = "standard"

    def _merge_pin_style_from_data(self, d):
        pin = {}
        attr = (d.get("attribute") or d.get("category_pin") or "").strip()
        m_attr = self.config.get("pin_marker_by_attribute") or {}
        pm_a = m_attr.get(attr) if attr else None
        if pm_a is None and attr:
            pm_a = m_attr.get(attr.upper())
        self._editor_apply_pin_marker_partial(pin, pm_a if isinstance(pm_a, dict) else None)
        cats = self._parse_categories_for_pin(d)
        m_cat = self.config.get("pin_marker_by_category_id") or {}
        for cat in cats:
            if not isinstance(cat, dict):
                continue
            cid = (cat.get("cat_id") or "").strip()
            if cid and isinstance(m_cat.get(cid), dict):
                self._editor_apply_pin_marker_partial(pin, m_cat[cid])
                break
        m_item = self.config.get("pin_marker_by_item_id") or {}
        for cat in cats:
            if not isinstance(cat, dict):
                continue
            iid = (cat.get("item_id") or "").strip()
            if iid and isinstance(m_item.get(iid), dict):
                self._editor_apply_pin_marker_partial(pin, m_item[iid])
                break
        csv_mds = (d.get("marker_display_style") or "").strip()
        if csv_mds:
            pin["marker_display_style"] = normalize_marker_display_style(csv_mds)
        else:
            pin["marker_display_style"] = normalize_marker_display_style(pin.get("marker_display_style"))
        if pin.get("marker_display_style") != "icon_only":
            if not pin.get("marker_bg_color"):
                am = self.config.get("attr_mapping", {}).get(attr)
                if not isinstance(am, dict) and attr:
                    am = self.config.get("attr_mapping", {}).get(attr.upper())
                if isinstance(am, dict):
                    typ = str(am.get("type", "other")).lower()
                    defaults = {"loot": "#2ecc71", "landmark": "#3498db", "colony": "#e67e22", "other": "#7f8c8d"}
                    pin["marker_bg_color"] = defaults.get(typ, defaults["other"])
                else:
                    pin["marker_bg_color"] = "#7f8c8d"
        if not pin.get("marker_icon_color"):
            pin["marker_icon_color"] = "#ffffff"
        pin["importance"] = str(d.get("importance") or "").strip()
        return pin

    def _pin_hex_rgba(self, h, default="#95a5a6"):
        s = (h or "").strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", s):
            s = default
        return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), 255)

    def _importance_level(self, v) -> int:
        try:
            n = int(str(v or "").strip())
        except Exception:
            return 0
        if n < 1:
            return 0
        if n > 5:
            return 5
        return n

    def _importance_inner_symbol_scale(self, importance_val) -> float:
        """map.js の重要度スケールに寄せた内側アイコン倍率（1=ドットのため未使用）。"""
        lv = self._importance_level(importance_val)
        if lv <= 1:
            return 1.0
        return {2: 0.78, 3: 1.0, 4: 1.18, 5: 1.36}.get(lv, 1.0)

    def _dot_color_from_style(self, style) -> str:
        icon_c = str(style.get("marker_icon_color") or "").strip().lower()
        bg_c = str(style.get("marker_bg_color") or "").strip().lower()
        if re.match(r"^#[0-9a-f]{6}$", icon_c) and icon_c != "#ffffff":
            return icon_c
        if re.match(r"^#[0-9a-f]{6}$", bg_c) and bg_c != "#ffffff":
            return bg_c
        if re.match(r"^#[0-9a-f]{6}$", icon_c):
            return icon_c
        if re.match(r"^#[0-9a-f]{6}$", bg_c):
            return bg_c
        return "#7f8c8d"

    # 埋め込み map.js の PIN_SVG_LAYERS（viewBox 0 0 48 48）と同一形状。尻尾先 (24,47) を地図座標に合わせる。
    _PIN_VIEWBOX = 48
    _PIN_MARKER_PX = 56  # エディタ上の見た目（map.js 既定のマーカーpxに近い）
    _PIN_TAIL_TIP_VB = (24, 47)  # viewBox 上の尻尾先＝アンカー点

    def _editor_pin_photoimage(self, style, selected, parent_highlight=False):
        """
        戻り値: (PhotoImage, anchor_x, anchor_y) — 画像左上から見たアンカー位置。
        standard: 尻尾先。icon_only: 中央（map.js iconAnchor と同趣）。
        parent_highlight: 子ピン選択中に親ピンを示す枠（選択時の金枠と排他）。
        """
        W = self._PIN_MARKER_PX
        vb = float(self._PIN_VIEWBOX)
        s = W / vb
        sid = (style.get("svg_icon_id") or "").strip()
        icon_c = style.get("marker_icon_color") or "#ffffff"
        bg_c = style.get("marker_bg_color") or "#95a5a6"
        disp = normalize_marker_display_style(style.get("marker_display_style"))
        resolved = svg_icon_assets.resolve_svg_icon(PROJECT_ROOT, self.game_path, sid) if sid else None
        icon_px = max(14, int(round(24 * s)))
        if self._importance_level(style.get("importance")) != 1:
            isc = self._importance_inner_symbol_scale(style.get("importance"))
            if abs(isc - 1.0) > 1e-6:
                icon_px = max(10, int(round(icon_px * isc)))
        icon_pil = None
        if resolved and os.path.isfile(resolved["abs_path"]):
            icon_pil = svg_icon_assets.svg_or_placeholder_pil_rgba(resolved["abs_path"], icon_px, icon_c)

        base = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        dr = ImageDraw.Draw(base)
        gold = (241, 196, 15, 255)
        hl = (52, 152, 219, 255)

        if self._importance_level(style.get("importance")) == 1:
            dot_hex = self._dot_color_from_style(style)
            dot_rgba = self._pin_hex_rgba(dot_hex, "#7f8c8d")
            m = W // 2
            r_dot = max(3, int(round(W * 0.09)))
            dr.ellipse((m - r_dot, m - r_dot, m + r_dot, m + r_dot), fill=dot_rgba, outline=(255, 255, 255, 235), width=1)
            if selected:
                ImageDraw.Draw(base).ellipse((m - r_dot - 4, m - r_dot - 4, m + r_dot + 4, m + r_dot + 4), outline=gold, width=2)
            elif parent_highlight:
                ImageDraw.Draw(base).ellipse((m - r_dot - 4, m - r_dot - 4, m + r_dot + 4, m + r_dot + 4), outline=hl, width=2)
            return ImageTk.PhotoImage(base), W // 2, W // 2

        if disp == "icon_only":
            if icon_pil:
                ip = icon_pil.convert("RGBA")
                ox = (W - ip.width) // 2
                oy = (W - ip.height) // 2
                base.alpha_composite(ip, (ox, oy))
            else:
                m = W // 2
                dr.ellipse((4, 4, W - 4, W - 4), fill=self._pin_hex_rgba(bg_c))
            if selected:
                ImageDraw.Draw(base).ellipse((1, 1, W - 2, W - 2), outline=gold, width=3)
            elif parent_highlight:
                ImageDraw.Draw(base).ellipse((1, 1, W - 2, W - 2), outline=hl, width=3)
            ax, ay = W // 2, W // 2
            return ImageTk.PhotoImage(base), ax, ay

        cx, cy = 24 * s, 24 * s
        rf, ri = 17 * s, 15 * s
        # 白枠: 円 + 尻尾（map.js と同 path）
        dr.ellipse((cx - rf, cy - rf, cx + rf, cy + rf), fill=(255, 255, 255, 255))
        tail = [
            (24 * s, 47 * s),
            (29.1962 * s, 38.75 * s),
            (18.8038 * s, 38.75 * s),
        ]
        dr.polygon(tail, fill=(255, 255, 255, 255))
        dr.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill=self._pin_hex_rgba(bg_c))
        if icon_pil:
            ip = icon_pil.convert("RGBA")
            ox = int(round(cx - ip.width / 2))
            oy = int(round(cy - ip.height / 2))
            base.alpha_composite(ip, (ox, oy))

        if selected:
            dr2 = ImageDraw.Draw(base)
            dr2.ellipse((cx - rf, cy - rf, cx + rf, cy + rf), outline=gold, width=3)
            dr2.polygon(tail, outline=gold, width=3)
        elif parent_highlight:
            dr2 = ImageDraw.Draw(base)
            dr2.ellipse((cx - rf, cy - rf, cx + rf, cy + rf), outline=hl, width=3)
            dr2.polygon(tail, outline=hl, width=3)

        ax = int(round(self._PIN_TAIL_TIP_VB[0] * s))
        ay = int(round(self._PIN_TAIL_TIP_VB[1] * s))
        return ImageTk.PhotoImage(base), ax, ay

    def _pin_anchor_offsets(self, d: dict) -> tuple[int, int]:
        """create_image(px-ax, py-ay) と同じアンカーずれ（キャンバスピクセル）。"""
        st = self._merge_pin_style_from_data(d)
        if self._importance_level(st.get("importance")) == 1:
            W = self._PIN_MARKER_PX
            return (W // 2, W // 2)
        disp = normalize_marker_display_style(st.get("marker_display_style"))
        W = self._PIN_MARKER_PX
        s = W / float(self._PIN_VIEWBOX)
        if disp == "icon_only":
            return (W // 2, W // 2)
        return (
            int(round(self._PIN_TAIL_TIP_VB[0] * s)),
            int(round(self._PIN_TAIL_TIP_VB[1] * s)),
        )

    def _pin_hit_test_canvas(self, d: dict, r: float, mx: float, my: float) -> bool:
        """キャンバス座標 (mx,my) がピンの当たり範囲内か。icon_only は直径 hit_side の円、standard は 56×56 矩形。"""
        try:
            px = float(d["x"]) * r
            py = float(d["y"]) * r
        except (TypeError, ValueError, KeyError):
            return False
        W = self._PIN_MARKER_PX
        vb = float(self._PIN_VIEWBOX)
        s = W / vb
        st = self._merge_pin_style_from_data(d)
        disp = normalize_marker_display_style(st.get("marker_display_style"))
        if disp == "icon_only":
            sid = (st.get("svg_icon_id") or "").strip()
            if sid:
                icon_px = max(14, int(round(24 * s)))
                hit_side = float(icon_px) + 8.0
            else:
                hit_side = float(W - 8)
            rad = 0.5 * hit_side
            return (mx - px) ** 2 + (my - py) ** 2 <= rad * rad
        ax, ay = self._pin_anchor_offsets(d)
        left, top = px - ax, py - ay
        return self._canvas_point_in_rect(mx, my, (left, top, left + W, top + W))

    @staticmethod
    def _canvas_point_in_rect(mx: float, my: float, bounds) -> bool:
        if bounds is None:
            return False
        L, T, R, B = bounds
        return L <= mx <= R and T <= my <= B

    def _cancel_throttled_refresh(self):
        tid = getattr(self, "_throttle_refresh_after", None)
        if tid is not None:
            try:
                self.after_cancel(tid)
            except Exception:
                pass
            self._throttle_refresh_after = None

    def _refresh_map_throttled(self, delay_ms: int = 58):
        """パン・オートスクロール中は再描画を間引き、メインスレッドの負荷を下げる。"""
        self._cancel_throttled_refresh()
        self._throttle_refresh_after = self.after(delay_ms, self._throttled_refresh_run)

    def _throttled_refresh_run(self):
        self._throttle_refresh_after = None
        self._refresh_map_do()

    def _refresh_map_retry_tick(self):
        self._refresh_map_retry_after = None
        self.refresh_map()

    def _on_canvas_configure(self, event):
        if time.monotonic() < getattr(self, "_suppress_configure_refresh_until", 0):
            return
        if getattr(self, "_canvas_configure_after", None) is not None:
            try:
                self.after_cancel(self._canvas_configure_after)
            except Exception:
                pass
        self._canvas_configure_after = self.after(80, self._canvas_configure_refresh)

    def _canvas_configure_refresh(self):
        self._canvas_configure_after = None
        self.refresh_map()

    def refresh_map(self):
        self._refresh_map_do()

    @staticmethod
    def _blit_tile_to_viewport(vp, tile_rgba, tx, ty, ts, vl, vt, cw, ch):
        """1タイルをビューポートRGBA画像へ。キャンバス座標 (vl,vt)-(vl+cw, vt+ch) に合わせて切り出し貼り付け。"""
        tlx, tly = tx * ts, ty * ts
        ix0 = max(tlx, vl)
        iy0 = max(tly, vt)
        ix1 = min(tlx + ts, vl + cw)
        iy1 = min(tly + ts, vt + ch)
        if ix0 >= ix1 or iy0 >= iy1:
            return
        sx0 = int(ix0 - tlx)
        sy0 = int(iy0 - tly)
        sw = int(ix1 - ix0)
        sh = int(iy1 - iy0)
        dx0 = int(ix0 - vl)
        dy0 = int(iy0 - vt)
        if sw <= 0 or sh <= 0:
            return
        dx0 = max(0, dx0)
        dy0 = max(0, dy0)
        if dx0 >= vp.width or dy0 >= vp.height:
            return
        sw = min(sw, vp.width - dx0)
        sh = min(sh, vp.height - dy0)
        if sw <= 0 or sh <= 0:
            return
        crop = tile_rgba.crop((sx0, sy0, sx0 + sw, sy0 + sh))
        if crop.size != (sw, sh):
            crop = crop.resize((sw, sh), Image.Resampling.NEAREST)
        vp.paste(crop, (dx0, dy0), crop)

    def _refresh_map_do(self):
        self._cancel_throttled_refresh()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            if getattr(self, "_refresh_map_retry_after", None) is None:
                self._refresh_map_retry_after = self.after(100, self._refresh_map_retry_tick)
            return
        self._refresh_map_retry_after = None
        ps = getattr(self, "_pending_scroll_after_zoom", None)
        if ps is not None:
            self._pending_scroll_after_zoom = None
        if ps is not None:
            Wp, Hp, fx, fy = ps
            self.canvas.config(scrollregion=(0, 0, Wp, Hp))
            if Wp > 0:
                self.canvas.xview_moveto(fx)
            if Hp > 0:
                self.canvas.yview_moveto(fy)
            # update_idletasks はしない。ここで描画をflushすると、まだ古い地図画像のまま
            # 新スクロールが一瞬見えてずれる／地図を先に消した場合は真っ暗が長く見える。
        self._map_pin_photo_refs = []
        r = self.get_ratio()
        z_src = min(int(math.floor(self.zoom)), self.max_zoom)
        ts = int(256 * (2 ** (self.zoom - z_src)))
        vl, vt = self.canvas.canvasx(0), self.canvas.canvasy(0)
        tc = self.tile_cache
        tmax = getattr(self, "_tile_cache_max", 384)
        tx_a = int(vl // ts)
        tx_b = int((vl + cw) // ts) + 1
        ty_a = int(vt // ts)
        ty_b = int((vt + ch) // ts) + 1
        n_tile_slots = max(0, tx_b - tx_a) * max(0, ty_b - ty_a)
        icw, ich = int(cw), int(ch)
        use_vp = (
            icw > 0
            and ich > 0
            and icw * ich <= 8_000_000
            and n_tile_slots > 0
            and n_tile_slots <= 900
        )
        drew_vp = False
        if use_vp:
            try:
                pil_cache = self._tile_pil_cache
                pmax = getattr(self, "_tile_pil_cache_max", 320)
                vp = Image.new("RGBA", (icw, ich), (28, 29, 36, 255))
                for tx in range(tx_a, tx_b):
                    for ty in range(ty_a, ty_b):
                        path = os.path.join(self.tile_dir, str(z_src), str(tx), f"{ty}.webp")
                        if not os.path.exists(path):
                            continue
                        k = f"{path}_{ts}"
                        if k not in pil_cache:
                            pil_cache[k] = Image.open(path).convert("RGBA").resize(
                                (ts, ts), Image.Resampling.NEAREST
                            )
                        else:
                            pil_cache.move_to_end(k)
                        tile_im = pil_cache[k]
                        self._blit_tile_to_viewport(vp, tile_im, tx, ty, ts, vl, vt, cw, ch)
                        if k not in tc:
                            tc[k] = ImageTk.PhotoImage(tile_im)
                        else:
                            tc.move_to_end(k)
                while len(pil_cache) > pmax:
                    pil_cache.popitem(last=False)
                while len(tc) > tmax:
                    tc.popitem(last=False)
                self._map_viewport_photo = ImageTk.PhotoImage(vp.copy())
                self._map_pin_photo_refs.append(self._map_viewport_photo)
                drew_vp = True
            except Exception:
                drew_vp = False
                while len(tc) > tmax:
                    tc.popitem(last=False)
        # タイル合成が終わってからまとめて消す。先に地図だけ消すと合成中ずっと暗く見える。
        self.canvas.delete(
            MapEditor._CTAG_AREA,
            MapEditor._CTAG_PIN,
            MapEditor._CTAG_OVERLAY,
            MapEditor._CTAG_MAP,
        )
        if drew_vp:
            try:
                self.canvas.create_image(
                    vl,
                    vt,
                    anchor="nw",
                    image=self._map_viewport_photo,
                    tags=(MapEditor._CTAG_MAP,),
                )
            except tk.TclError:
                pass
        else:
            for tx in range(tx_a, tx_b):
                for ty in range(ty_a, ty_b):
                    path = os.path.join(self.tile_dir, str(z_src), str(tx), f"{ty}.webp")
                    if os.path.exists(path):
                        k = f"{path}_{ts}"
                        if k not in tc:
                            tc[k] = ImageTk.PhotoImage(
                                Image.open(path).resize((ts, ts), Image.Resampling.NEAREST)
                            )
                        else:
                            tc.move_to_end(k)
                        self.canvas.create_image(
                            tx * ts,
                            ty * ts,
                            anchor="nw",
                            image=tc[k],
                            tags=(MapEditor._CTAG_MAP,),
                        )
            while len(tc) > tmax:
                tc.popitem(last=False)
        # エリアをタイルの上・ピンの下に描画
        self._draw_areas(r)
        pcache = self._editor_pin_photo_cache
        pmax = getattr(self, "_editor_pin_photo_cache_max", 200)
        parent_for_highlight = ""
        cur_uid_hl = (getattr(self, "current_uid", None) or "").strip()
        if cur_uid_hl and not getattr(self, "_parent_pick_mode", False):
            for dx in self.data_list:
                if dx.get("uid") == cur_uid_hl:
                    parent_for_highlight = (dx.get("parent_uid") or "").strip()
                    break
        for d in self.data_list:
            if not self._pin_passes_display_filters(d):
                continue
            px, py = d["x"] * r, d["y"] * r
            st = self._merge_pin_style_from_data(d)
            sel = d["uid"] == self.current_uid
            par_hi = bool(parent_for_highlight) and (d.get("uid") or "") == parent_for_highlight
            try:
                pkey = (d.get("uid"), sel, par_hi, json.dumps(st, sort_keys=True, default=str))
            except TypeError:
                pkey = (d.get("uid"), sel, par_hi, str(st))
            if pkey in pcache:
                pcache.move_to_end(pkey)
                photo, ax, ay = pcache[pkey]
            else:
                photo, ax, ay = self._editor_pin_photoimage(st, sel, par_hi)
                pcache[pkey] = (photo, ax, ay)
                pcache.move_to_end(pkey)
            self._map_pin_photo_refs.append(photo)
            # 尻尾先（または icon_only の中心）を地図座標 (px,py) に一致させる
            self.canvas.create_image(
                px - ax,
                py - ay,
                image=photo,
                anchor="nw",
                tags=(MapEditor._CTAG_PIN,),
            )
        while len(pcache) > pmax:
            pcache.popitem(last=False)
        # 未保存の新規ピン（旧: temp_coords のみ。現行は data_list のドラフト行 + current_uid）
        if self.temp_coords and not self.current_uid:
            try:
                tx = float(self.temp_coords[0]) * r
                ty = float(self.temp_coords[1]) * r
            except (TypeError, ValueError, IndexError):
                tx = ty = 0.0
            try:
                preview_row = self._preview_csv_row_from_ui()
                st = self._merge_pin_style_from_data(preview_row)
                try:
                    pkey = ("__temp_pin__", False, json.dumps(st, sort_keys=True, default=str))
                except TypeError:
                    pkey = ("__temp_pin__", False, str(st))
                if pkey in pcache:
                    pcache.move_to_end(pkey)
                    photo, ax, ay = pcache[pkey]
                else:
                    photo, ax, ay = self._editor_pin_photoimage(st, selected=False)
                    pcache[pkey] = (photo, ax, ay)
                    pcache.move_to_end(pkey)
                self._map_pin_photo_refs.append(photo)
                self.canvas.create_image(
                    tx - ax,
                    ty - ay,
                    image=photo,
                    anchor="nw",
                    tags=(MapEditor._CTAG_PIN,),
                )
                while len(pcache) > pmax:
                    pcache.popitem(last=False)
            except Exception:
                pass
        if self.is_crop_mode:
            bx, by, bw, bh = self.crop_box["x"] * r, self.crop_box["y"] * r, self.crop_box["w"] * r, self.crop_box["h"] * r
            self.canvas.create_rectangle(
                bx,
                by,
                bx + bw,
                by + bh,
                outline="#2ecc71",
                width=3,
                dash=(10, 5),
                tags=(MapEditor._CTAG_OVERLAY,),
            )
            if self.here_pos:
                hx, hy = self.here_pos["x"] * r, self.here_pos["y"] * r
                self.canvas.create_oval(
                    hx - 20,
                    hy - 20,
                    hx + 20,
                    hy + 20,
                    outline="white",
                    width=4,
                    tags=(MapEditor._CTAG_OVERLAY,),
                )
                self.canvas.create_oval(
                    hx - 20,
                    hy - 20,
                    hx + 20,
                    hy + 20,
                    outline="#e74c3c",
                    width=3,
                    tags=(MapEditor._CTAG_OVERLAY,),
                )
        self.canvas.config(scrollregion=(0, 0, self.orig_w * r, self.orig_h * r))

    def _try_start_editing_pin_drag(self, cx, cy, r, event_x, event_y) -> bool:
        """ピン編集パネル表示中に、編集中のピン上でドラッグ開始できるか。"""
        if not getattr(self, "_pin_editor_panel_open", False):
            return False
        if getattr(self, "_parent_pick_mode", False):
            return False
        if (getattr(self, "current_area_uid", None) or "").strip():
            return False
        if getattr(self, "_pin_placement_active", False):
            return False
        if self.area_mode in ("create_polygon", "create_circle", "create_rect", "edit_polygon"):
            return False
        if self.is_crop_mode and self.active_tool:
            return False
        mx, my = cx * r, cy * r
        uid = (getattr(self, "current_uid", None) or "").strip()
        if uid:
            for d in self.data_list:
                if d.get("uid") != uid:
                    continue
                if self._pin_hit_test_canvas(d, r, mx, my):
                    self._editing_pin_drag_active = True
                    self.drag_start = (event_x, event_y)
                    self.has_dragged = False
                    return True
            return False
        tc = getattr(self, "temp_coords", None)
        if tc is not None:
            try:
                preview_row = self._preview_csv_row_from_ui()
                if self._pin_hit_test_canvas(preview_row, r, mx, my):
                    self._editing_pin_drag_active = True
                    self.drag_start = (event_x, event_y)
                    self.has_dragged = False
                    return True
            except Exception:
                return False
        return False

    def _apply_editing_pin_drag_position(self, cx, cy):
        uid = (getattr(self, "current_uid", None) or "").strip()
        if uid:
            for d in self.data_list:
                if d.get("uid") == uid:
                    d["x"], d["y"] = float(cx), float(cy)
                    break
        elif getattr(self, "temp_coords", None) is not None:
            self.temp_coords = (float(cx), float(cy))
        self.lbl_coords.configure(text=f"座標: ({int(cx)}, {int(cy)})")

    def on_zoom(self, event):
        d = getattr(event, "delta", 0)
        if d == 0:
            return
        self._zoom_toward_canvas_point(event.x, event.y, float(d))

    def _zoom_toward_canvas_point(self, ex: int, ey: int, wheel_delta: float):
        """ホイールは高頻度で届くため delta を短時間まとめ、再描画は1回に抑えてちらつきを減らす。"""
        if getattr(self, "_canvas_configure_after", None) is not None:
            try:
                self.after_cancel(self._canvas_configure_after)
            except Exception:
                pass
            self._canvas_configure_after = None
        self._zoom_wheel_pending_delta += wheel_delta
        self._zoom_wheel_anchor_ex, self._zoom_wheel_anchor_ey = ex, ey
        if getattr(self, "_zoom_wheel_after_id", None) is not None:
            try:
                self.after_cancel(self._zoom_wheel_after_id)
            except Exception:
                pass
        self._zoom_wheel_after_id = self.after(68, self._flush_zoom_wheel_accumulated)

    def _flush_zoom_wheel_accumulated(self):
        self._zoom_wheel_after_id = None
        d = self._zoom_wheel_pending_delta
        self._zoom_wheel_pending_delta = 0.0
        if abs(d) < 1e-6:
            return
        ex, ey = self._zoom_wheel_anchor_ex, self._zoom_wheel_anchor_ey
        self._apply_zoom_at_canvas_point(ex, ey, d)

    def _apply_zoom_at_canvas_point(self, ex: int, ey: int, wheel_delta: float):
        """カーソル下の地図点を維持したままズームする。
        スクロール適用は _refresh_map_do 内で先に行い canvasx(0) を合わせ、
        タイル合成のあとでまとめて delete→再描画する（合成中は前フレームを残して暗さを抑える）。"""
        if getattr(self, "_canvas_configure_after", None) is not None:
            try:
                self.after_cancel(self._canvas_configure_after)
            except Exception:
                pass
            self._canvas_configure_after = None
        mx = self.canvas.canvasx(ex)
        my = self.canvas.canvasy(ey)
        r_old = self.get_ratio()
        if r_old <= 0 or self.orig_w <= 0 or self.orig_h <= 0:
            return
        # まとめた delta に対して1回だけ補正（1flushあたりのズーム幅に上限）
        dz = 0.12 * (wheel_delta / 120.0)
        dz = max(-0.55, min(0.55, dz))
        self.zoom = max(0, min(self.max_zoom + 2.5, self.zoom + dz))
        r_new = self.get_ratio()
        if r_new <= 0:
            return
        mx_target = mx * (r_new / r_old)
        my_target = my * (r_new / r_old)
        W = self.orig_w * r_new
        H = self.orig_h * r_new
        try:
            self.canvas.update_idletasks()
        except tk.TclError:
            pass
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        left = mx_target - ex
        top = my_target - ey
        left = max(0, min(left, max(0, W - cw)))
        top = max(0, min(top, max(0, H - ch)))
        fx = (left / W) if W > 0 else 0.0
        fy = (top / H) if H > 0 else 0.0
        self._pending_scroll_after_zoom = (W, H, fx, fy)
        self.refresh_map()
        self._suppress_configure_refresh_until = time.monotonic() + 0.18

    def on_left_down(self, event):
        r = self.get_ratio(); mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y); cx, cy = mx/r, my/r
        if not self.area_edit_enabled.get():
            # エリア編集無効時は従来のマップ操作のみ
            if self.is_crop_mode and not self.active_tool:
                b = self.crop_box; bx, by, bw, bh = b["x"]*r, b["y"]*r, b["w"]*r, b["h"]*r
                if (bx+bw-20 <= mx <= bx+bw+5) and (by+bh-20 <= my <= by+bh+5): self.drag_mode = "resize_br"; return
                elif (b["x"] <= cx <= b["x"]+b["w"]) and (b["y"] <= cy <= b["y"]+b["h"]): self.drag_mode = "move"; self.drag_offset = (cx - b["x"], cy - b["y"]); return
            if not (self.is_crop_mode and self.active_tool):
                if self._try_start_editing_pin_drag(cx, cy, r, event.x, event.y):
                    return
            self.drag_start = (event.x, event.y); self.has_dragged = False; self.canvas.scan_mark(event.x, event.y)
            return
        if self.is_crop_mode and not self.active_tool:
            b = self.crop_box; bx, by, bw, bh = b["x"]*r, b["y"]*r, b["w"]*r, b["h"]*r
            if (bx+bw-20 <= mx <= bx+bw+5) and (by+bh-20 <= my <= by+bh+5): self.drag_mode = "resize_br"; return
            elif (b["x"] <= cx <= b["x"]+b["w"]) and (b["y"] <= cy <= b["y"]+b["h"]): self.drag_mode = "move"; self.drag_offset = (cx - b["x"], cy - b["y"]); return
        # 円/四角はドラッグで範囲作成
        if self.area_mode in ("create_circle", "create_rect"):
            self.area_drag_mode = "create_shape"
            self.area_drag_start = (cx, cy)
            self.area_preview_shape = {"shape": self.area_mode, "x0": cx, "y0": cy, "x1": cx, "y1": cy}
            return
        if not (self.is_crop_mode and self.active_tool):
            if self._try_start_editing_pin_drag(cx, cy, r, event.x, event.y):
                return
        # 選択エリアの移動（idle 時）
        if self.area_mode == "idle" and self.current_area_uid:
            area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
            if area and self.hit_test_area(cx, cy) is area:
                self.area_drag_mode = "move_area"
                self.area_drag_start = (cx, cy)
                return
        # エリア制御点ドラッグ開始判定（edit_polygon 時）
        if self.area_mode == "edit_polygon" and self.current_area_uid:
            area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
            if area and area.get("shape", "polygon") == "polygon":
                pts = area.get("points") or []
                for idx, (ax, ay) in enumerate(pts):
                    px, py = ax*r, ay*r
                    if abs(px - mx) <= 12 and abs(py - my) <= 12:
                        self.area_drag_index = idx
                        return
        self.drag_start = (event.x, event.y); self.has_dragged = False; self.canvas.scan_mark(event.x, event.y)

    def on_left_drag(self, event):
        r = self.get_ratio(); cx, cy = self.canvas.canvasx(event.x)/r, self.canvas.canvasy(event.y)/r
        if getattr(self, "_editing_pin_drag_active", False):
            self._apply_editing_pin_drag_position(cx, cy)
            self.has_dragged = True
            self.refresh_map()
            self._schedule_pin_preview_refresh()
            return
        if self.area_drag_mode == "create_shape" and self.area_preview_shape:
            self.area_preview_shape["x1"] = cx
            self.area_preview_shape["y1"] = cy
            self.has_dragged = True
            self.refresh_map()
            return
        if self.area_drag_mode == "move_area" and self.current_area_uid and self.area_drag_start:
            dx = cx - self.area_drag_start[0]
            dy = cy - self.area_drag_start[1]
            self.move_current_area(dx, dy)
            self.area_drag_start = (cx, cy)
            self.has_dragged = True
            self.refresh_map()
            return
        if self.area_drag_index is not None and self.area_mode == "edit_polygon" and self.current_area_uid:
            area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
            if area and area.get("shape", "polygon") == "polygon":
                pts = area.get("points") or []
                if 0 <= self.area_drag_index < len(pts):
                    pts[self.area_drag_index][0] = cx
                    pts[self.area_drag_index][1] = cy
                    area["points"] = pts
                    self.refresh_map()
                    return
        if self.drag_mode == "move": self.crop_box["x"], self.crop_box["y"] = cx - self.drag_offset[0], cy - self.drag_offset[1]; self.refresh_map(); return
        elif self.drag_mode == "resize_br": self.crop_box["w"], self.crop_box["h"] = max(160, cx - self.crop_box["x"]), (cx - self.crop_box["x"]) * (9/16); self.refresh_map(); return
        if abs(event.x - self.drag_start[0]) > 5 or abs(event.y - self.drag_start[1]) > 5:
            self.has_dragged = True
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self._refresh_map_throttled()

    def on_left_up(self, event):
        if self.drag_mode:
            self.drag_mode = None
            return
        if getattr(self, "_editing_pin_drag_active", False):
            self._editing_pin_drag_active = False
            if self.has_dragged:
                self.mark_dirty()
                return
        if self.area_drag_mode == "create_shape":
            self._finalize_shape_by_drag(event)
            self.area_drag_mode = None
            self.area_drag_start = None
            self.area_preview_shape = None
            return
        if self.area_drag_mode == "move_area":
            self.area_drag_mode = None
            self.area_drag_start = None
            self.mark_dirty()
            return
        if self.area_drag_index is not None:
            self.area_drag_index = None
            self.mark_dirty()
            return
        if self.has_dragged:
            self._cancel_throttled_refresh()
            self._refresh_map_do()
        if not self.has_dragged:
            r = self.get_ratio()
            mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            cx, cy = mx / r, my / r
            if self.is_crop_mode and self.active_tool:
                if self.active_tool == "here": self.here_pos = {"x": cx, "y": cy}
                elif self.active_tool == "arrow": self.arrow_pos = {"x": cx, "y": cy}
                self.refresh_map(); return
            # エリア作成モード（多角形 / 円 / 四角）
            if self.area_mode in ("create_polygon", "create_circle", "create_rect"):
                self.handle_area_creation_click(cx, cy)
                return
            # 親ピン選択モード: 別ピンをクリックして親を設定（座標は変更しない）
            if getattr(self, "_parent_pick_mode", False) and (getattr(self, "current_uid", None) or "").strip():
                for d in reversed(self.data_list):
                    if self._is_draft_pin_row(d):
                        continue
                    if not self._pin_passes_display_filters(d):
                        continue
                    if self._pin_hit_test_canvas(d, r, mx, my):
                        tid = (d.get("uid") or "").strip()
                        if tid == self.current_uid:
                            messagebox.showinfo("親ピン", "自分自身は親にできません。別のピンを選んでください。")
                        else:
                            self._apply_parent_pick(tid)
                        return
                return
            # まずピン当たり判定（後から描いたピンを優先＝描画順と一致）
            for d in reversed(self.data_list):
                if not self._pin_passes_display_filters(d):
                    continue
                if self._pin_hit_test_canvas(d, r, mx, my):
                    if not self.load_to_ui(d):
                        return
                    self._pin_placement_active = False
                    self.temp_coords = None
                    self.current_area_uid = None
                    self.refresh_map()
                    return
            # ピンがなければエリア当たり判定
            hit_area = self.hit_test_area(cx, cy)
            if hit_area is not None:
                self.load_area_to_ui(hit_area)
                self.refresh_map()
                return
            # 新規ピン設置: 「ピンを追加」後のクリックのみ
            if self._pin_placement_active:
                self._pin_placement_active = False
                self.current_area_uid = None
                self.temp_coords = None
                self._reset_pin_form_widgets()
                uid_new = self._gen_new_pin_uid()
                draft = self._make_empty_pin_row(uid_new, cx, cy, draft=True)
                self.data_list.append(draft)
                self.current_uid = uid_new
                self._sync_draft_pin_row_core_from_ui()
                self._show_pin_editor_panel()
                self.lbl_coords.configure(text=f"座標: ({int(cx)}, {int(cy)})")
                self.refresh_map()
                self._schedule_pin_preview_refresh()
                self._pin_edit_baseline = self._build_pin_compare_snapshot()
                return
            # 未保存の新規ピン編集中: 空き地クリックでは座標を変えない（マーカーのドラッグでのみ移動）。消えもしない。
            if getattr(self, "temp_coords", None) is not None and not (getattr(self, "current_uid", None) or "").strip():
                return
            if not self._confirm_pin_edit_discard_or_save():
                return
            self.current_uid = None
            self.current_area_uid = None
            self.temp_coords = None
            # 空き地クリックで編集対象を外した直後は、前ピンの baseline も破棄する。
            # これを残すと次のピン選択時に「未変更なのに差分あり」判定になる。
            self._pin_edit_baseline = None
            self.lbl_coords.configure(text=f"座標: ({int(cx)}, {int(cy)})")
            self._refresh_sidebar_top_toolbar()
            self.refresh_map()

    def toggle_crop_mode(self): self.is_crop_mode = not self.is_crop_mode; st = "normal" if self.is_crop_mode else "disabled"; self.btn_crop_exec.configure(state=st); self.refresh_map()
    def set_tool(self, t): self.active_tool = None if self.active_tool == t else t; self.refresh_map()
    def execute_crop(self):
        try: path, sdir = save_cropped_image_with_annotations(self.game_path, self.config.get("map_file", "map.png"), self.crop_box, self.orig_w, self.orig_h, self.here_pos, self.arrow_pos); messagebox.showinfo("成功", f"保存: {path}"); os.startfile(sdir)
        except Exception as e: messagebox.showerror("エラー", str(e))
    def toggle_autoscroll(self, event): self.is_autoscrolling = not self.is_autoscrolling; self.autoscroll_origin = (event.x, event.y)
    def run_autoscroll_loop(self):
        if self.is_autoscrolling:
            mx, my = self.winfo_pointerx()-self.winfo_rootx(), self.winfo_pointery()-self.winfo_rooty(); dx, dy = (mx-self.autoscroll_origin[0]), (my-self.autoscroll_origin[1])
            if abs(dx)>20 or abs(dy)>20:
                self.canvas.xview_scroll(int(dx/35), "units")
                self.canvas.yview_scroll(int(dy/35), "units")
                self._refresh_map_throttled(62)
        self.after(10, self.run_autoscroll_loop)

    def _apply_preview_sidebar_visibility(self):
        """表示メニュー: 右サイドバー（ピン表示プレビュー）の表示／非表示。"""
        if not getattr(self, "preview_sidebar", None):
            return
        if self.show_preview_sidebar_var.get():
            self.preview_sidebar.grid(row=0, column=2, sticky="nsew")
            self.grid_columnconfigure(2, weight=0, minsize=self._preview_sidebar_column_minsize)
        else:
            self.preview_sidebar.grid_remove()
            self.grid_columnconfigure(2, weight=0, minsize=0)

    def setup_menu_bar(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="保存", command=self.save_all_changes, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_close)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="ピン表示フィルタ…", command=self._open_pin_filter_window)
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="右サイドバー（ピン表示プレビュー）を表示",
            variable=self.show_preview_sidebar_var,
            command=self._apply_preview_sidebar_visibility,
        )
        menubar.add_cascade(label="表示", menu=view_menu)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="マスタ管理…", command=self.open_settings)
        settings_menu.add_command(label="スキル名マスタ…", command=self.open_skill_name_master_window)
        settings_menu.add_command(label="カテゴリ特記事項…", command=self.open_category_special_notes_window)
        settings_menu.add_command(label="サイト表示プリセット管理…", command=self.open_view_preset_window)
        menubar.add_cascade(label="設定", menu=settings_menu)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="WordPress 記事一覧（リンク候補）…", command=self._open_wp_rest_guide_picker)
        menubar.add_cascade(label="ツール", menu=tools_menu)
        # self.config は設定用dictと名称が衝突しているので configure を使う
        self.configure(menu=menubar)
        self.bind("<Control-s>", lambda e: self.save_all_changes())

    def mark_dirty(self):
        self.is_dirty = True
        self.update_title_dirty()

    def mark_clean(self):
        self.is_dirty = False
        self.update_title_dirty()

    def update_title_dirty(self):
        base_title = self.title().replace(" *", "")
        if self.is_dirty and not base_title.endswith(" *"):
            self.title(base_title + " *")
        elif not self.is_dirty:
            self.title(base_title)

    def save_all_changes(self):
        self.write_files()
        self.save_areas()
        self.mark_clean()
        messagebox.showinfo("保存", "変更内容を保存しました。")

    def on_close(self):
        if self.is_dirty:
            ans = messagebox.askyesnocancel("終了確認", "未保存の変更があります。保存して終了しますか？")
            if ans is None:
                return
            if ans:
                self.save_all_changes()
        self.destroy()
        self.master.deiconify()

    # --- エリア描画・編集ヘルパー ---
    def _get_area_fill_color(self, area):
        """エリア塗り色は、中央アイコンと同じ解決結果の背景色を使う。"""
        st = self._merge_pin_style_from_data(self._area_synthetic_pin_dict_for_marker(area))
        bg = str(st.get("marker_bg_color") or "").strip()
        if re.match(r"^#[0-9a-fA-F]{6}$", bg):
            return bg
        return "#7f8c8d"

    @staticmethod
    def _polygon_centroid_image_xy(pts):
        """画像座標ポリゴンの幾何学的重心（map.js polygonCentroidImageXY と同じ）。"""
        if not pts or len(pts) < 3:
            return None
        n = len(pts)
        twice = 0.0
        cx = 0.0
        cy = 0.0
        for i in range(n):
            j = (i + 1) % n
            try:
                xi = float(pts[i][0])
                yi = float(pts[i][1])
                xj = float(pts[j][0])
                yj = float(pts[j][1])
            except (TypeError, ValueError, IndexError):
                return None
            cross = xi * yj - xj * yi
            twice += cross
            cx += (xi + xj) * cross
            cy += (yi + yj) * cross
        if abs(twice) < 1e-9:
            sx = sy = 0.0
            for k in range(n):
                try:
                    sx += float(pts[k][0])
                    sy += float(pts[k][1])
                except (TypeError, ValueError, IndexError):
                    return None
            return (sx / n, sy / n)
        a = 3.0 * twice
        return (cx / a, cy / a)

    def _area_center_icon_image_xy(self, area):
        """エリア中央マーカー用の画像座標（円=中心・矩形=中心・多角形=重心）。map.js areaCenterIconImageXY と同じ。"""
        shape = area.get("shape") or "polygon"
        if shape == "circle":
            try:
                cx = float(area.get("x", 0))
                cy = float(area.get("y", 0))
            except (TypeError, ValueError):
                return None
            return (cx, cy)
        if shape == "rect":
            try:
                x = float(area.get("x", 0))
                y = float(area.get("y", 0))
                w = float(area.get("width", 0))
                h = float(area.get("height", 0))
            except (TypeError, ValueError):
                return None
            return (x + w / 2.0, y + h / 2.0)
        pts = area.get("points") or []
        return MapEditor._polygon_centroid_image_xy(pts)

    def _area_wants_center_icon(self, area):
        """中央マーカーを試みるか。show_center_icon が false なら出さない。それ以外は map.js に近いが、
        未設定時はマスタ解決で svg が付くオブジェクトでも出す（エディタでプレビューしやすくする）。"""
        if area.get("show_center_icon") is False:
            return False
        if area.get("show_center_icon") is True:
            return True
        if str(area.get("svg_icon_id") or "").strip():
            return True
        st = self._merge_pin_style_from_data(self._area_synthetic_pin_dict_for_marker(area))
        return bool((st.get("svg_icon_id") or "").strip())

    def _area_synthetic_pin_dict_for_marker(self, area):
        """エリアをピンと同じマスタ解決に載せるための擬似ピン辞書。"""
        cats = area.get("categories")
        if isinstance(cats, list):
            cat_field = json.dumps(cats, ensure_ascii=False) if cats else ""
        elif isinstance(cats, str):
            cat_field = cats
        else:
            cat_field = ""
        attr = (area.get("attribute") or "").strip()
        return {
            "attribute": attr,
            "category_pin": attr,
            "categories": cat_field,
            # 仕様: エリア中央アイコンは常に icon_only。
            "marker_display_style": "icon_only",
            "importance": str(area.get("importance") or "").strip(),
        }

    def _draw_area_center_icons(self, r):
        """map.js のエリア中央アイコン（マーカー）をエディタでも表示。ピン描画より手前に重ねるため _draw_areas の最後で呼ぶ。"""
        pcache = self._editor_pin_photo_cache
        pmax = getattr(self, "_editor_pin_photo_cache_max", 200)
        for area in self.area_list:
            if not self._area_wants_center_icon(area):
                continue
            st = self._merge_pin_style_from_data(self._area_synthetic_pin_dict_for_marker(area))
            if not (st.get("svg_icon_id") or "").strip():
                continue
            xy = self._area_center_icon_image_xy(area)
            if not xy:
                continue
            ix, iy = xy
            try:
                px, py = float(ix) * r, float(iy) * r
            except (TypeError, ValueError):
                continue
            uid = area.get("uid")
            try:
                pkey = ("__area_ctr__", uid, json.dumps(st, sort_keys=True, default=str))
            except TypeError:
                pkey = ("__area_ctr__", uid, str(st))
            if pkey in pcache:
                pcache.move_to_end(pkey)
                photo, ax, ay = pcache[pkey]
            else:
                photo, ax, ay = self._editor_pin_photoimage(st, selected=False)
                pcache[pkey] = (photo, ax, ay)
                pcache.move_to_end(pkey)
            self._map_pin_photo_refs.append(photo)
            self.canvas.create_image(
                px - ax,
                py - ay,
                image=photo,
                anchor="nw",
                tags=(MapEditor._CTAG_AREA,),
            )
        while len(pcache) > pmax:
            pcache.popitem(last=False)

    def _draw_areas(self, r):
        for area in self.area_list:
            shape = area.get("shape", "polygon")
            fill = self._get_area_fill_color(area)
            outline = "#ffffff"
            is_selected = area.get("uid") == self.current_area_uid
            width = 3 if is_selected else 1
            # Tk Canvas はアルファ透過色を直接扱えないため、20%相当は粗い stipple で近似する。
            stipple = "gray75"
            if shape == "circle":
                # 円もポリゴンとして描画して矩形・多角形と同じ見た目に揃える
                cx_img, cy_img = float(area.get("x", 0)), float(area.get("y", 0))
                radius_img = float(area.get("radius", 0))
                if radius_img <= 0:
                    continue
                cx, cy, radius = cx_img*r, cy_img*r, radius_img*r
                segs = 32
                flat = []
                for i in range(segs):
                    theta = (2 * math.pi * i) / segs
                    px = cx + radius * math.cos(theta)
                    py = cy + radius * math.sin(theta)
                    flat.extend([px, py])
                self.canvas.create_polygon(
                    *flat,
                    outline=outline,
                    width=width,
                    fill=fill,
                    stipple=stipple,
                    tags=(MapEditor._CTAG_AREA,),
                )
            elif shape == "rect":
                x = float(area.get("x", 0))*r
                y = float(area.get("y", 0))*r
                w = float(area.get("width", 0))*r
                h = float(area.get("height", 0))*r
                if w <= 0 or h <= 0:
                    continue
                self.canvas.create_rectangle(
                    x,
                    y,
                    x + w,
                    y + h,
                    outline=outline,
                    width=width,
                    fill=fill,
                    stipple=stipple,
                    tags=(MapEditor._CTAG_AREA,),
                )
            else:
                pts = area.get("points") or []
                if len(pts) < 3:
                    continue
                flat = []
                for (ax, ay) in pts:
                    flat.extend([ax*r, ay*r])
                self.canvas.create_polygon(
                    *flat,
                    outline=outline,
                    width=width,
                    fill=fill,
                    stipple=stipple,
                    tags=(MapEditor._CTAG_AREA,),
                )
                # 制御点の可視化（編集モード時）
                if self.area_show_points.get() and self.area_mode == "edit_polygon" and is_selected:
                    for idx, (ax, ay) in enumerate(pts):
                        px, py = ax*r, ay*r
                        c = "#ff4757" if idx == 0 else "#ffffff"
                        self.canvas.create_oval(
                            px - 7,
                            py - 7,
                            px + 7,
                            py + 7,
                            fill=c,
                            outline="#000000",
                            tags=(MapEditor._CTAG_AREA,),
                        )
        # 作成中ポリゴンのプレビュー（始点強調＋閉路ガイド）
        if self.area_mode == "create_polygon" and self.area_temp_points:
            pts = self.area_temp_points
            if len(pts) >= 2:
                flat = []
                for (ax, ay) in pts:
                    flat.extend([ax*r, ay*r])
                self.canvas.create_line(*flat, fill="#00d2d3", width=2, tags=(MapEditor._CTAG_AREA,))
                sx, sy = pts[0][0]*r, pts[0][1]*r
                ex, ey = pts[-1][0]*r, pts[-1][1]*r
                self.canvas.create_line(
                    ex,
                    ey,
                    sx,
                    sy,
                    fill="#00d2d3",
                    width=1,
                    dash=(4, 3),
                    tags=(MapEditor._CTAG_AREA,),
                )
            if self.area_show_points.get():
                for idx, (ax, ay) in enumerate(pts):
                    px, py = ax*r, ay*r
                    c = "#ff4757" if idx == 0 else "#ffffff"
                    self.canvas.create_oval(
                        px - 7,
                        py - 7,
                        px + 7,
                        py + 7,
                        fill=c,
                        outline="#000000",
                        tags=(MapEditor._CTAG_AREA,),
                    )
        # 円/四角のドラッグ作成プレビュー
        if self.area_preview_shape:
            shp = self.area_preview_shape
            x0, y0, x1, y1 = shp["x0"]*r, shp["y0"]*r, shp["x1"]*r, shp["y1"]*r
            if shp["shape"] == "create_rect":
                self.canvas.create_rectangle(
                    min(x0, x1),
                    min(y0, y1),
                    max(x0, x1),
                    max(y0, y1),
                    outline="#00d2d3",
                    width=2,
                    dash=(6, 4),
                    tags=(MapEditor._CTAG_AREA,),
                )
            elif shp["shape"] == "create_circle":
                radius = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                self.canvas.create_oval(
                    x0 - radius,
                    y0 - radius,
                    x0 + radius,
                    y0 + radius,
                    outline="#00d2d3",
                    width=2,
                    dash=(6, 4),
                    tags=(MapEditor._CTAG_AREA,),
                )
        self._draw_area_center_icons(r)

    def set_area_mode(self, mode):
        """エリア編集モードの切替"""
        if mode not in ("idle", "create_polygon", "create_circle", "create_rect", "edit_polygon"):
            mode = "idle"
        if not self.area_edit_enabled.get() and mode != "idle":
            # 編集が無効のときは強制的に idle のまま
            return
        self.area_mode = mode
        self.area_temp_points = []
        self.area_drag_index = None
        self.area_drag_mode = None
        self.area_drag_start = None
        self.area_preview_shape = None
        self.refresh_map()
        self._refresh_sidebar_top_toolbar()

    def handle_area_creation_click(self, cx, cy):
        """エリア作成モード時のクリック処理"""
        if self.area_mode == "create_polygon":
            # クリックごとに制御点を追加、3点以上で保存ボタンで確定
            self.area_temp_points.append([cx, cy])
            self.refresh_map()

    def _finalize_shape_by_drag(self, event):
        """ドラッグで作成した円/四角を確定"""
        if not self.area_preview_shape:
            return
        shp = self.area_preview_shape
        x0, y0 = shp["x0"], shp["y0"]
        x1, y1 = shp["x1"], shp["y1"]
        if shp["shape"] == "create_rect":
            x = min(x0, x1)
            y = min(y0, y1)
            w = abs(x1 - x0)
            h = abs(y1 - y0)
            if w < 3 or h < 3:
                return
            self._create_area_record(shape="rect", x=x, y=y, width=w, height=h)
        elif shp["shape"] == "create_circle":
            dx, dy = x1 - x0, y1 - y0
            radius = (dx*dx + dy*dy) ** 0.5
            if radius < 3:
                return
            self._create_area_record(shape="circle", x=x0, y=y0, radius=radius)
        self.set_area_mode("idle")

    def toggle_area_points(self):
        self.area_show_points.set(not self.area_show_points.get())
        txt = "制御点: ON" if self.area_show_points.get() else "制御点: OFF"
        btn = getattr(self, "btn_area_point_toggle", None)
        if btn is not None:
            btn.configure(text=txt)
        self.refresh_map()

    def finalize_polygon_area(self):
        if self.area_mode != "create_polygon":
            messagebox.showinfo("多角形確定", "多角形作成モードで実行してください。")
            return
        if len(self.area_temp_points) < 3:
            messagebox.showwarning("多角形確定", "制御点を3点以上指定してください。")
            return
        self._create_area_record(shape="polygon")
        self.area_temp_points = []
        self.set_area_mode("edit_polygon")

    def start_edit_polygon_mode(self):
        if not self.current_area_uid:
            messagebox.showwarning("制御点編集", "先にエリアを選択してください。")
            return
        if not self.area_edit_enabled.get():
            messagebox.showinfo("制御点編集", "エリア編集をONにしてください。")
            return
        area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
        if not area or area.get("shape", "polygon") != "polygon":
            messagebox.showinfo("制御点編集", "多角形エリアのみ制御点編集できます。")
            return
        self.set_area_mode("edit_polygon")

    def toggle_area_edit_enabled(self):
        self.area_edit_enabled.set(not self.area_edit_enabled.get())
        btn = getattr(self, "btn_area_edit_toggle", None)
        if not self.area_edit_enabled.get():
            self.set_area_mode("idle")
            if btn is not None:
                btn.configure(text="編集: OFF", fg_color="#7f8c8d")
        else:
            if btn is not None:
                btn.configure(text="編集: ON", fg_color="#2ecc71")
        self.refresh_map()
        self._refresh_sidebar_top_toolbar()

    def move_current_area(self, dx, dy):
        area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
        if not area:
            return
        shape = area.get("shape", "polygon")
        if shape == "circle":
            area["x"] = float(area.get("x", 0.0)) + dx
            area["y"] = float(area.get("y", 0.0)) + dy
        elif shape == "rect":
            area["x"] = float(area.get("x", 0.0)) + dx
            area["y"] = float(area.get("y", 0.0)) + dy
        else:
            pts = area.get("points") or []
            area["points"] = [[p[0] + dx, p[1] + dy] for p in pts]
        self.mark_dirty()

    def rotate_current_area(self, delta_deg):
        """選択中エリアを中心回りに回転（矩形は多角形に変換して扱う）"""
        import math
        if not self.current_area_uid:
            messagebox.showwarning("回転", "先にエリアを選択してください。")
            return
        if not self.area_edit_enabled.get():
            messagebox.showinfo("回転", "エリア編集をONにしてください。")
            return
        area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
        if not area:
            return
        shape = area.get("shape", "polygon")
        if shape == "circle":
            messagebox.showinfo("回転", "円エリアの回転は不要です。")
            return
        # 回転対象の頂点列を取得
        if shape == "rect":
            x = float(area.get("x", 0.0))
            y = float(area.get("y", 0.0))
            w = float(area.get("width", 0.0))
            h = float(area.get("height", 0.0))
            pts = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
        else:
            pts = area.get("points") or []
            if len(pts) < 3:
                messagebox.showwarning("回転", "回転できる頂点が足りません。")
                return
        # 中心（重心）を求める
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        rad = math.radians(delta_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        new_pts = []
        for px, py in pts:
            dx, dy = px - cx, py - cy
            rx = cx + dx * cos_a - dy * sin_a
            ry = cy + dx * sin_a + dy * cos_a
            new_pts.append([rx, ry])
        area["shape"] = "polygon"
        area["points"] = new_pts
        area["x"] = cx
        area["y"] = cy
        area["width"] = 0.0
        area["height"] = 0.0
        self.mark_dirty()
        self.refresh_map()

    def _create_area_record(self, shape="polygon", x=0.0, y=0.0, radius=0.0, width=0.0, height=0.0):
        """現在のUI内容と形状情報からエリアレコードを新規作成"""
        # attribute などはピンと同じUIから取得
        attribute = (self.cmb_attribute.get() or "").strip()
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attribute_id = rev_cat_map.get(attribute, "")
        name_jp = self.ent_name_jp.get().strip()
        name_en = self.ent_name_en.get().strip()
        memo_jp = self.txt_memo_jp.get("1.0", "end-1c").replace("\n", "<br>")
        memo_en = self.txt_memo_en.get("1.0", "end-1c").replace("\n", "<br>")
        importance = self.cmb_importance.get().strip()
        # 簡易版として categories 等はまだ使わず、将来拡張に備えてフィールドだけ用意
        area = {
            "uid": f"AREA_{len(self.area_list)+1}",
            "shape": shape,
            "x": float(x),
            "y": float(y),
            "radius": float(radius),
            "width": float(width),
            "height": float(height),
            "points": [p[:] for p in self.area_temp_points] if shape == "polygon" else [],
            "attribute": attribute_id,
            "name_jp": name_jp,
            "name_en": name_en,
            "importance": importance,
            "memo_jp": memo_jp,
            "memo_en": memo_en,
            "categories": [],
            "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        self.area_list.append(area)
        self.current_area_uid = area["uid"]
        self.mark_dirty()

    def hit_test_area(self, cx, cy):
        """クリック位置からエリア（shape問わず）を検索"""
        # 円・四角はバウンディングボックスで当たり判定
        for area in reversed(self.area_list):
            shape = area.get("shape", "polygon")
            if shape == "circle":
                ax, ay = float(area.get("x", 0.0)), float(area.get("y", 0.0))
                r = float(area.get("radius", 0.0))
                if r <= 0:
                    continue
                dx, dy = cx - ax, cy - ay
                if dx*dx + dy*dy <= r*r:
                    return area
            elif shape == "rect":
                x = float(area.get("x", 0.0))
                y = float(area.get("y", 0.0))
                w = float(area.get("width", 0.0))
                h = float(area.get("height", 0.0))
                if x <= cx <= x + w and y <= cy <= y + h:
                    return area
        # ポリゴンはポイントインポリゴン
        for area in reversed(self.area_list):
            shape = area.get("shape", "polygon")
            if shape != "polygon":
                continue
            pts = area.get("points") or []
            if len(pts) < 3:
                continue
            inside = False
            j = len(pts) - 1
            for i in range(len(pts)):
                xi, yi = pts[i]
                xj, yj = pts[j]
                intersect = ((yi > cy) != (yj > cy)) and (cx < (xj - xi) * (cy - yi) / (yj - yi + 1e-9) + xi)
                if intersect:
                    inside = not inside
                j = i
            if inside:
                return area
        return None

    def load_area_to_ui(self, area):
        """エリア選択時にUIへ反映"""
        if not self._confirm_pin_edit_discard_or_save():
            return
        self.clear_ui()
        # attribute
        attr_key = area.get("attribute") or ""
        attr_display = self._attr_display_name(attr_key)
        if attr_display:
            vals = list(self.cmb_attribute.cget("values"))
            if attr_display not in vals:
                self.cmb_attribute.configure(values=vals + [attr_display])
            self.cmb_attribute.set(attr_display)
            self.on_attribute_changed()
        # 表示名・メモ
        if area.get("name_jp"):
            self.ent_name_jp.insert(0, area.get("name_jp", ""))
        if area.get("name_en"):
            self.ent_name_en.insert(0, area.get("name_en", ""))
        if area.get("memo_jp"):
            self.txt_memo_jp.insert("1.0", area.get("memo_jp", "").replace("<br>", "\n"))
        if area.get("memo_en"):
            self.txt_memo_en.insert("1.0", area.get("memo_en", "").replace("<br>", "\n"))
        if area.get("importance"):
            self.cmb_importance.set(area.get("importance"))
        # categories（エリア）もピンと同じスロットUIへ反映
        raw_cats = area.get("categories")
        cat_rows = []
        if isinstance(raw_cats, list):
            cat_rows = raw_cats
        elif isinstance(raw_cats, str) and raw_cats.strip():
            try:
                parsed = json.loads(raw_cats)
                if isinstance(parsed, list):
                    cat_rows = parsed
            except Exception:
                cat_rows = []
        if cat_rows:
            for cat_data in cat_rows:
                if not isinstance(cat_data, dict):
                    continue
                slot = self.add_category_slot()
                cat_id = (cat_data.get("cat_id") or "").strip()
                category = ""
                if cat_id:
                    for nm, inf in self.category_master.items():
                        if isinstance(inf, dict) and (inf.get("id") or "").strip() == cat_id:
                            category = nm
                            break
                if not category:
                    category = (cat_data.get("category") or "").strip()
                if not category:
                    continue
                if category not in self.category_list:
                    self.category_list.append(category)
                self._merge_pin_category_combo_values(slot, category)
                slot["category"].set(category)
                self.on_slot_category_changed(slot["frame"])

                qty = (cat_data.get("qty") or "1")
                slot["qty"].delete(0, "end")
                slot["qty"].insert(0, str(qty))
                self._set_slot_many_mode(slot, self._is_many_qty_token(qty))

                item_id = (cat_data.get("item_id") or "").strip()
                if item_id and category in self.item_master and item_id in self.item_master[category]:
                    item_name = self.item_master[category][item_id].get("name_jp", "")
                    if item_name:
                        slot["item"].set(item_name)
                        self.on_slot_item_changed(slot["frame"])
        self.lbl_coords.configure(text=f"エリア: {area.get('uid')}")
        uid_a = (area.get("uid") or "").strip()
        self.current_area_uid = uid_a or None
        self._show_pin_editor_panel()

    def save_current_area(self):
        """現在選択中のエリアにUI内容を保存"""
        if not self.current_area_uid:
            messagebox.showwarning("エリア保存", "エリアが選択されていません。")
            return
        area = next((a for a in self.area_list if a.get("uid") == self.current_area_uid), None)
        if not area:
            messagebox.showwarning("エリア保存", "エリアが見つかりません。")
            return
        attribute = (self.cmb_attribute.get() or "").strip()
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attribute_id = rev_cat_map.get(attribute, "")
        area["attribute"] = attribute_id
        area["name_jp"] = self.ent_name_jp.get().strip()
        area["name_en"] = self.ent_name_en.get().strip()
        area["memo_jp"] = self.txt_memo_jp.get("1.0", "end-1c").replace("\n", "<br>")
        area["memo_en"] = self.txt_memo_en.get("1.0", "end-1c").replace("\n", "<br>")
        area["importance"] = self.cmb_importance.get().strip()
        # エリアもピンと同じ categories 構造で保持し、見た目解決（カテゴリ/アイテム→アイコン）に使う
        area["categories"] = self._collect_pin_categories_data()
        area["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.mark_dirty()
        self.refresh_map()
        messagebox.showinfo("エリア保存", "エリア情報を更新しました。（未保存）")

    def delete_current_area(self):
        """現在選択中のエリアを削除"""
        if not self.current_area_uid:
            messagebox.showwarning("エリア削除", "エリアが選択されていません。")
            return
        if not messagebox.askyesno("エリア削除", "選択中のエリアを削除しますか？"):
            return
        self.area_list = [a for a in self.area_list if a.get("uid") != self.current_area_uid]
        self.current_area_uid = None
        self.mark_dirty()
        self.clear_ui()
        self.refresh_map()

    def _category_special_rules_list_for_slot(self, category_jp: str):
        category_special_rules_builder.sync_category_special_rules_from_master(self.config)
        csr = self.config.get("category_special_rules") or {}
        if not isinstance(csr, dict):
            return []
        cid = (self._get_cat_id(category_jp) or "").strip()
        block = None
        if cid and isinstance(csr.get(cid), dict):
            block = csr[cid]
        if block is None and category_jp and isinstance(csr.get(category_jp), dict):
            block = csr[category_jp]
        if not isinstance(block, dict):
            return []
        rules = block.get("rules") or []
        return [r for r in rules if isinstance(r, dict)]

    def _merge_special_rule_attrs_into(self, item_attrs: dict, slot: dict) -> dict:
        out = dict(item_attrs) if item_attrs else {}
        ag = getattr(self, "_pin_special_note_aggregate", None) or {}
        for _key, info in ag.items():
            var = info.get("var")
            if var is None:
                continue
            try:
                val = bool(var.get())
            except tk.TclError:
                continue
            for b in info.get("bindings") or []:
                if not isinstance(b, (list, tuple)) or len(b) < 2:
                    continue
                s, idx = b[0], b[1]
                if s is not slot:
                    continue
                try:
                    out[f"special_rule_enabled_{int(idx)}"] = val
                except (ValueError, TypeError):
                    pass
        return out

    def _pin_special_note_label_wraplength(self) -> int:
        """サイドバー幅に合わせて特記ラベルを折り返す（長文の横はみ出しを抑える）。"""
        try:
            w = int(self.f_pin_form_card.winfo_width())
            if w > 80:
                return max(160, w - 72)
        except (tk.TclError, TypeError, ValueError):
            pass
        return 380

    def _sync_pin_special_notes_pack_order(self):
        """特記事項ブロックは中身があるときだけ表示し、カテゴリ見出しの直前に挿入する。"""
        f = getattr(self, "f_pin_special_notes", None)
        fh = getattr(self, "f_cat_header", None)
        cfs = getattr(self, "category_slots_frame", None)
        if f is None or fh is None or cfs is None:
            return
        attribute = (getattr(self, "cmb_attribute", None) and self.cmb_attribute.get() or "").strip()
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev_cat_map.get(attribute, "")
        obj_type = "loot"
        if attr_id and attr_id in self.attr_mapping:
            oi = self.attr_mapping[attr_id]
            if isinstance(oi, dict):
                obj_type = oi.get("type", "loot")
        if attr_id and obj_type == "landmark":
            return
        try:
            fh.pack_forget()
            cfs.pack_forget()
        except tk.TclError:
            pass
        try:
            f.pack_forget()
        except tk.TclError:
            pass
        try:
            after_ref = self.obj_attr_frame if self.obj_attr_frame.winfo_ismapped() else self.f_attr
        except Exception:
            after_ref = self.f_attr
        try:
            has_content = len(f.winfo_children()) > 0
        except tk.TclError:
            has_content = False
        if has_content:
            f.pack(fill="x", padx=BOX_PADX, pady=(0, 6), after=after_ref)
            fh.pack(fill="x", padx=BOX_PADX, pady=(10, 0), after=f)
        else:
            fh.pack(fill="x", padx=BOX_PADX, pady=(10, 0), after=after_ref)
        cfs.pack(fill="x", padx=BOX_PADX, pady=5, after=fh)

    def _rebuild_pin_special_notes_ui(self):
        f = getattr(self, "f_pin_special_notes", None)
        if f is None:
            return
        for w in f.winfo_children():
            w.destroy()
        prev_ui = {}
        ag_old = getattr(self, "_pin_special_note_aggregate", None) or {}
        for _k, inf in ag_old.items():
            ov = inf.get("var")
            if ov is not None:
                try:
                    prev_ui[_k] = bool(ov.get())
                except tk.TclError:
                    pass

        snm = category_special_rules_builder.skill_name_master_to_dict(self.config)
        wrap_w = self._pin_special_note_label_wraplength()

        slot_snapshots = {}
        slot_rules_rows = []
        for slot in self.category_slots:
            slot["special_note_vars"] = {}
            snap = slot.pop("_loaded_attributes", None)
            slot_snapshots[id(slot)] = snap if isinstance(snap, dict) else {}
            cat = (slot["category"].get() or "").strip()
            if not cat or cat == "(なし)":
                rules = []
            else:
                rules = self._category_special_rules_list_for_slot(cat)
            slot_rules_rows.append((slot, cat, rules))

        # プレビュー aggregate_special_fragments_for_pin と同じ「表示文」で同種を1行にまとめる
        order_keys = []
        groups = {}
        meta = {}
        seen = set()
        for slot, cat, rules in slot_rules_rows:
            for idx, r in enumerate(rules, start=1):
                if not isinstance(r, dict):
                    continue
                line_jp = pin_site_preview.special_rule_text(r, True, snm) or ""
                stripped = line_jp.strip()
                if stripped:
                    key = stripped
                    label = stripped
                else:
                    key = "\x00" + json.dumps(r, sort_keys=True, ensure_ascii=False)
                    label = (f"特記 ({cat}) #{idx}" if cat else f"特記 #{idx}").strip()
                if key not in groups:
                    groups[key] = []
                groups[key].append((slot, idx))
                if key not in seen:
                    seen.add(key)
                    order_keys.append(key)
                if key not in meta:
                    meta[key] = {
                        "default_on": bool(r.get("default_enabled", True)),
                        "label": label,
                    }
                else:
                    meta[key]["default_on"] = meta[key]["default_on"] or bool(r.get("default_enabled", True))
                    if len(label) > len(meta[key].get("label") or ""):
                        meta[key]["label"] = label

        aggregate = {}
        if order_keys:
            hdr = ctk.CTkLabel(
                f,
                text="▼ カテゴリ特記（同一内容はピン単位で1行。サイトではクリック時のポップアップのみ）",
                font=("Meiryo", 10, "bold"),
                anchor="w",
                justify="left",
                wraplength=max(wrap_w + 48, 200),
            )
            hdr.pack(anchor="w", padx=4, pady=(0, 2))

        for key in order_keys:
            bindings = groups.get(key) or []
            if not bindings:
                continue
            if key in prev_ui:
                initial = prev_ui[key]
            else:
                any_saved = False
                merged_on = False
                for slot, idx in bindings:
                    snap = slot_snapshots.get(id(slot), {})
                    sk = f"special_rule_enabled_{idx}"
                    if sk in snap:
                        any_saved = True
                        merged_on = merged_on or pin_site_preview.truthy_slot_attr(snap[sk])
                initial = merged_on if any_saved else bool(meta[key]["default_on"])
            v = tk.BooleanVar(value=initial)
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            cb = ctk.CTkCheckBox(
                row,
                text="",
                width=28,
                variable=v,
                command=self._schedule_pin_preview_refresh,
            )
            cb.pack(side="left", anchor="nw", padx=(0, 6), pady=4)
            lbl = ctk.CTkLabel(
                row,
                text=meta[key]["label"],
                font=("Meiryo", 10),
                anchor="w",
                justify="left",
                wraplength=wrap_w,
                cursor="hand2",
            )
            lbl.pack(side="left", fill="x", expand=True, anchor="nw", pady=2)

            def _toggle(ev, var=v):
                var.set(not var.get())
                self._schedule_pin_preview_refresh()

            lbl.bind("<Button-1>", _toggle)
            aggregate[key] = {"var": v, "bindings": list(bindings)}

        self._pin_special_note_aggregate = aggregate
        self._sync_pin_special_notes_pack_order()

    def _collect_pin_categories_data(self):
        """カテゴリスロットから保存用・プレビュー用の categories 配列を構築（save_data / 定型と同一ルール）。"""
        categories_data = []
        for slot in self.category_slots:
            category = slot["category"].get()
            item_name = slot["item"].get()
            is_many = bool(slot.get("qty_many_var").get()) if slot.get("qty_many_var") is not None else False
            qty = "MANY" if is_many else ((slot["qty"].get() or "").strip() or "1")
            if category == "(なし)":
                continue
            input_type = "item_select"
            if category in self.category_master:
                cat_info = self.category_master[category]
                if isinstance(cat_info, dict):
                    input_type = cat_info.get("input_type", "item_select")
            lbl_c = slot.get("lbl_slot_cat_en")
            slot_cat_en = ((lbl_c.cget("text") if lbl_c else "") or "").strip()
            if slot_cat_en in ("", "—") and category in self.category_master and isinstance(self.category_master[category], dict):
                slot_cat_en = (self.category_master[category].get("name_en", "") or self.category_master[category].get("name_jp", "") or "").strip()
            lbl_i = slot.get("lbl_slot_item_en")
            slot_item_en = ((lbl_i.cget("text") if lbl_i else "") or "").strip()
            if slot_item_en == "—":
                slot_item_en = ""
            if input_type == "qty_only":
                qty_item_en = slot_item_en or ""
                if not qty_item_en and category in self.category_master and isinstance(self.category_master[category], dict):
                    qty_item_en = self.category_master[category].get("name_en", "") or self.category_master[category].get("name_jp", "")
                categories_data.append({
                    "cat_id": self._get_cat_id(category),
                    "category": category,
                    "cat_name_en": slot_cat_en or "",
                    "item_id": "",
                    "item_name_jp": "",
                    "item_name_en": qty_item_en or "",
                    "qty": qty,
                    "attributes": self._merge_special_rule_attrs_into({}, slot),
                })
                continue
            if item_name == "(なし)":
                # 仕様: アイテム未選択でも「カテゴリのみ入力」を許容する
                categories_data.append({
                    "cat_id": self._get_cat_id(category),
                    "category": category,
                    "cat_name_en": slot_cat_en or "",
                    "item_id": "",
                    "item_name_jp": "",
                    "item_name_en": "",
                    "qty": qty,
                    "attributes": self._merge_special_rule_attrs_into({}, slot),
                })
                continue
            item_id = None
            if category in self.item_master:
                for i_id, info in self.item_master[category].items():
                    if info["name_jp"] == item_name:
                        item_id = i_id
                        break
            if not item_id:
                # 互換: マスタ不一致時もカテゴリのみとして保存を許容
                categories_data.append({
                    "cat_id": self._get_cat_id(category),
                    "category": category,
                    "cat_name_en": slot_cat_en or "",
                    "item_id": "",
                    "item_name_jp": "",
                    "item_name_en": "",
                    "qty": qty,
                    "attributes": self._merge_special_rule_attrs_into({}, slot),
                })
                continue
            item_attrs = {}
            for attr_key, widget_data in slot.get("attr_widgets", {}).items():
                if isinstance(widget_data, dict):
                    attr_type = widget_data.get("type", "select")
                    if attr_type == "fixed":
                        item_attrs[attr_key] = widget_data.get("value", "")
                    else:
                        widget = widget_data.get("widget")
                        if widget:
                            val = widget.get()
                            if val and val != "(なし)":
                                item_attrs[attr_key] = val
                else:
                    val = widget_data.get() if hasattr(widget_data, "get") else None
                    if val and val != "(なし)":
                        item_attrs[attr_key] = val
            master_item_en = self.item_master[category][item_id].get("name_en", "")
            categories_data.append({
                "cat_id": self._get_cat_id(category),
                "category": category,
                "cat_name_en": slot_cat_en or "",
                "item_id": item_id,
                "item_name_jp": self.item_master[category][item_id].get("name_jp", ""),
                "item_name_en": slot_item_en or master_item_en,
                "qty": qty,
                "attributes": self._merge_special_rule_attrs_into(item_attrs, slot),
            })
        return categories_data

    def _set_pin_preview_text(self, widget, text):
        if not widget:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text or "")
        widget.configure(state="disabled")

    def _clear_pin_site_preview(self, message="ピン編集が閉じているときはここは更新されません。"):
        for w in (
            getattr(self, "_pin_preview_hover_jp", None),
            getattr(self, "_pin_preview_hover_en", None),
            getattr(self, "_pin_preview_popup_jp", None),
            getattr(self, "_pin_preview_popup_en", None),
        ):
            self._set_pin_preview_text(w, message)

    def _preview_csv_row_from_ui(self):
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attribute = (self.cmb_attribute.get() or "").strip()
        attribute_id = rev_cat_map.get(attribute, "")
        categories_data = self._collect_pin_categories_data()
        obj_attributes = {}
        for attr_key, widget_data in self.obj_attr_widgets.items():
            if isinstance(widget_data, dict):
                widget = widget_data.get("widget")
                if widget:
                    val = widget.get()
                    if val and val != "(なし)":
                        obj_attributes[attr_key] = val
        main_category = (categories_data[0].get("category") or "") if categories_data else ""
        x, y = 0.0, 0.0
        if self.current_uid:
            for d in self.data_list:
                if d.get("uid") == self.current_uid:
                    try:
                        x, y = float(d.get("x", 0)), float(d.get("y", 0))
                    except (TypeError, ValueError):
                        x, y = 0.0, 0.0
                    break
        elif self.temp_coords:
            try:
                x, y = float(self.temp_coords[0]), float(self.temp_coords[1])
            except (TypeError, ValueError):
                x, y = 0.0, 0.0
        parent_uid = ""
        parent_type = ""
        parent_name_jp = ""
        parent_name_en = ""
        parent_obj_jp = ""
        parent_obj_en = ""
        if self.current_uid:
            cur = self._get_pin_row_by_uid(self.current_uid)
            if cur is not None:
                parent_uid = (cur.get("parent_uid") or "").strip()
                parent_type = (cur.get("parent_type") or "").strip()
        if getattr(self, "cmb_parent_type", None) and parent_uid:
            parent_type = self._parent_type_value_from_label(self.cmb_parent_type.get())
        if parent_uid:
            prow = self._get_pin_row_by_uid(parent_uid)
            if prow is not None:
                parent_name_jp = (prow.get("name_jp") or "").strip()
                parent_name_en = (prow.get("name_en") or "").strip()
                pa = (prow.get("attribute") or prow.get("category_pin") or "").strip()
                pinfo = self.attr_mapping.get(pa) if isinstance(self.attr_mapping, dict) else None
                if isinstance(pinfo, dict):
                    parent_obj_jp = (pinfo.get("name_jp") or "").strip()
                    parent_obj_en = (pinfo.get("name_en") or "").strip()
        return {
            "uid": self.current_uid or "preview",
            "x": x,
            "y": y,
            "attribute": attribute_id,
            "category_pin": attribute_id,
            "obj_name_en": (self.ent_obj_en.get() or "").strip() if getattr(self, "ent_obj_en", None) else "",
            "obj_attributes": json.dumps(obj_attributes, ensure_ascii=False) if obj_attributes else "",
            "categories": json.dumps(categories_data, ensure_ascii=False) if categories_data else "",
            "category": main_category,
            "memo_jp": self.txt_memo_jp.get("1.0", "end-1c").replace("\n", "<br>"),
            "memo_en": self.txt_memo_en.get("1.0", "end-1c").replace("\n", "<br>"),
            "parent_uid": parent_uid,
            "parent_type": parent_type,
            "parent_name_jp": parent_name_jp,
            "parent_name_en": parent_name_en,
            "parent_obj_jp": parent_obj_jp,
            "parent_obj_en": parent_obj_en,
        }

    def _refresh_pin_site_preview(self):
        self._pin_preview_after_id = None
        if not getattr(self, "_pin_preview_hover_jp", None):
            return
        try:
            if not self.f_pin_editor.winfo_ismapped():
                self._clear_pin_site_preview()
                return
        except tk.TclError:
            return
        attribute = (self.cmb_attribute.get() or "").strip()
        if not attribute or attribute == "(なし)":
            self._set_pin_preview_text(self._pin_preview_hover_jp, "オブジェクトを選ぶとプレビューが表示されます。")
            self._set_pin_preview_text(self._pin_preview_hover_en, "Select an object to see the preview.")
            self._set_pin_preview_text(self._pin_preview_popup_jp, "")
            self._set_pin_preview_text(self._pin_preview_popup_en, "")
            return
        try:
            row = self._preview_csv_row_from_ui()
            resolved = resolve_pin_for_display(row, self.config)
            bundle = pin_site_preview.build_preview_bundle(resolved, row, self.config)
            self._set_pin_preview_text(self._pin_preview_hover_jp, bundle.get("hover_tooltip_jp", ""))
            self._set_pin_preview_text(self._pin_preview_hover_en, bundle.get("hover_tooltip_en", ""))
            self._set_pin_preview_text(self._pin_preview_popup_jp, bundle.get("popup_plain_jp", ""))
            self._set_pin_preview_text(self._pin_preview_popup_en, bundle.get("popup_plain_en", ""))
        except Exception as ex:
            err = f"プレビュー生成エラー: {ex}"
            self._set_pin_preview_text(self._pin_preview_hover_jp, err)
            self._set_pin_preview_text(self._pin_preview_hover_en, err)
            self._set_pin_preview_text(self._pin_preview_popup_jp, "")
            self._set_pin_preview_text(self._pin_preview_popup_en, "")

    def _schedule_pin_preview_refresh(self):
        if not getattr(self, "_pin_preview_hover_jp", None):
            return
        if self._pin_preview_after_id is not None:
            try:
                self.after_cancel(self._pin_preview_after_id)
            except Exception:
                pass
        self._pin_preview_after_id = self.after(180, self._refresh_pin_site_preview)

    def _pin_edit_session_active(self) -> bool:
        """エリア編集中でなく、ピン編集パネルが有効なとき True（既存／新規／定型適用など）。"""
        if getattr(self, "current_area_uid", None):
            return False
        if not getattr(self, "_pin_editor_panel_open", False):
            return False
        fe = getattr(self, "f_pin_editor", None)
        if fe is None:
            return False
        # pack 直後は winfo_ismapped() が一瞬 False を返すことがあり、
        # 未保存判定の基準スナップショットが None になって確認ダイアログが出なくなる。
        # セッション判定は _pin_editor_panel_open を正として扱う。
        return True

    def _pin_xy_for_compare_snapshot(self):
        uid = (getattr(self, "current_uid", None) or "").strip()
        if uid:
            for d0 in self.data_list:
                if d0.get("uid") == uid:
                    try:
                        return round(float(d0.get("x", 0)), 6), round(float(d0.get("y", 0)), 6)
                    except (TypeError, ValueError):
                        return 0.0, 0.0
            return None, None
        tc = getattr(self, "temp_coords", None)
        if tc is not None:
            try:
                return round(float(tc[0]), 6), round(float(tc[1]), 6)
            except (TypeError, ValueError, IndexError):
                return None, None
        return None, None

    def _current_special_note_state_snapshot(self):
        """カテゴリ特記チェックの現在状態（未保存判定用）。"""
        out = {}
        ag = getattr(self, "_pin_special_note_aggregate", None) or {}
        for key, info in ag.items():
            var = info.get("var") if isinstance(info, dict) else None
            if var is None:
                continue
            try:
                out[str(key)] = bool(var.get())
            except tk.TclError:
                continue
        return out

    def _build_pin_compare_snapshot(self):
        """保存内容と同趣のフィールドを集め、未保存検出に使う。ピン編集セッション外では None。"""
        if not self._pin_edit_session_active():
            return None
        attribute = (self.cmb_attribute.get() or "").strip()
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        if not attribute or attribute == "(なし)":
            attribute_id = ""
        else:
            attribute_id = rev_cat_map.get(attribute, "")

        obj_attributes = {}
        for attr_key, widget_data in self.obj_attr_widgets.items():
            if isinstance(widget_data, dict):
                widget = widget_data.get("widget")
                if widget:
                    val = widget.get()
                    if val and val != "(なし)":
                        obj_attributes[attr_key] = val

        categories_data = self._collect_pin_categories_data()
        importance = self.cmb_importance.get()
        if importance == "(なし)":
            importance = ""

        if categories_data:
            main_category = categories_data[0]["category"]
        else:
            main_category = ""

        name_jp = (self.ent_name_jp.get() or "").strip()
        name_en = (self.ent_name_en.get() or "").strip()
        obj_name_en_override = (self.ent_obj_en.get() or "").strip() if getattr(self, "ent_obj_en", None) else ""
        raw_lj = (self.ent_link_jp.get() or "").strip() if getattr(self, "ent_link_jp", None) else ""
        raw_le = (self.ent_link_en.get() or "").strip() if getattr(self, "ent_link_en", None) else ""
        link_jp, _ = self._sanitize_saved_pin_link_url(raw_lj)
        link_en, _ = self._sanitize_saved_pin_link_url(raw_le)
        memo_jp = self.txt_memo_jp.get("1.0", "end-1c").replace("\n", "<br>")
        memo_en = self.txt_memo_en.get("1.0", "end-1c").replace("\n", "<br>")

        uid = (getattr(self, "current_uid", None) or "").strip()
        marker_display_style = ""
        parent_uid_snap = ""
        parent_type_snap = ""
        if uid:
            for d0 in self.data_list:
                if d0.get("uid") == uid:
                    marker_display_style = (d0.get("marker_display_style") or "").strip()
                    parent_uid_snap = (d0.get("parent_uid") or "").strip()
                    parent_type_snap = self._normalize_saved_parent_type(parent_uid_snap, d0.get("parent_type"))
                    break

        xy = self._pin_xy_for_compare_snapshot()
        return {
            "x": xy[0],
            "y": xy[1],
            "name_jp": name_jp,
            "name_en": name_en,
            "attribute": attribute_id,
            "obj_name_en": obj_name_en_override,
            "obj_attributes": obj_attributes,
            "category": main_category,
            "categories": categories_data,
            "importance": importance,
            "memo_jp": memo_jp,
            "memo_en": memo_en,
            "link_url_jp": link_jp,
            "link_url_en": link_en,
            "marker_display_style": marker_display_style,
            "parent_uid": parent_uid_snap,
            "parent_type": parent_type_snap,
            "special_note_state": self._current_special_note_state_snapshot(),
        }

    def _pin_edit_has_unsaved_changes(self) -> bool:
        if not self._pin_edit_session_active():
            return False
        base = getattr(self, "_pin_edit_baseline", None)
        if base is None:
            return False
        cur = self._build_pin_compare_snapshot()
        if cur is None:
            return False
        return cur != base

    def _confirm_pin_edit_discard_or_save(self) -> bool:
        """未保存のピン編集をどうするか確認。続行なら True、キャンセルで False。"""
        if not self._pin_edit_has_unsaved_changes():
            return True
        r = messagebox.askyesnocancel(
            "ピンの変更",
            "ピンに未保存の変更があります。保存しますか？\n\n"
            "「はい」: 保存して続行\n"
            "「いいえ」: 保存せず続行\n"
            "「キャンセル」: 編集を続ける",
            parent=self,
        )
        if r is None:
            return False
        if r:
            self._pin_save_last_ok = False
            self.save_data()
            if not getattr(self, "_pin_save_last_ok", False):
                return False
        else:
            # 「いいえ」: 保存せず続行。ドラフト新規ピンは data_list に残さない。
            self._remove_draft_pin_row_if_any()
            self.current_uid = None
            self.temp_coords = None
            self._pin_edit_baseline = None
        return True

    # --- 保存・読込 ---
    def save_data(self):
        self._pin_save_last_ok = False
        attribute = (self.cmb_attribute.get() or "").strip()
        if attribute == "(なし)" or attribute == "":
            messagebox.showwarning("入力エラー", "オブジェクトは必須です。")
            return

        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attribute_id = rev_cat_map.get(attribute, "")
        obj_type = "loot"
        if attribute_id and attribute_id in self.attr_mapping:
            obj_info = self.attr_mapping[attribute_id]
            if isinstance(obj_info, dict):
                obj_type = obj_info.get("type", "loot")
        if "attr_mapping" not in self.config:
            self.config["attr_mapping"] = {}
        if "category_master" not in self.config:
            self.config["category_master"] = {}
        if "item_master" not in self.config:
            self.config["item_master"] = {}
        if not isinstance(self.config.get("skill_name_master"), list):
            self.config["skill_name_master"] = []
        am, cm, im = self.config["attr_mapping"], self.config["category_master"], self.config["item_master"]
        new_objects = [attribute] if (attribute and attribute != "(なし)" and attribute not in rev_cat_map) else []
        new_categories = []
        new_items = []
        for slot in self.category_slots:
            category = (slot["category"].get() or "").strip()
            item_name = (slot["item"].get() or "").strip()
            if not category or category == "(なし)":
                continue
            if category not in cm and category not in new_categories:
                new_categories.append(category)
            input_type = "item_select"
            if category in self.category_master:
                ci = self.category_master[category]
                if isinstance(ci, dict):
                    input_type = ci.get("input_type", "item_select")
            if input_type == "item_select" and item_name and item_name != "(なし)":
                existing = category in im and any(info.get("name_jp") == item_name for info in im[category].values())
                if not existing and (category, item_name) not in new_items:
                    new_items.append((category, item_name))
        if new_objects or new_categories or new_items:
            msg = "以下の項目がマスタにありません。追加してから保存しますか？\n\n"
            if new_objects:
                msg += "【オブジェクト】\n" + "\n".join(f"・{o}" for o in new_objects) + "\n\n"
            if new_categories:
                msg += "【カテゴリ】\n" + "\n".join(f"・{c}" for c in new_categories) + "\n\n"
            if new_items:
                msg += "【アイテム】\n" + "\n".join(f"・{c} → {i}" for c, i in new_items) + "\n\n"
            msg += "追加しない場合は「キャンセル」を選び、入力内容を確認してください。"
            if not messagebox.askyesno("マスタに追加", msg, default=True):
                return
            for obj_name in new_objects:
                if obj_name:
                    oid = self._generate_obj_id(obj_name)
                    am[oid] = {"name_jp": obj_name, "name_en": obj_name, "type": "loot", "attributes": {}}
            if new_objects:
                self.config["attr_mapping"] = am
            for category in new_categories:
                if category not in cm:
                    cm[category] = {
                        "id": self._generate_cat_id(category),
                        "name_jp": category, "name_en": category,
                        "type": obj_type, "input_type": "item_select", "show_qty": True
                    }
            self.config["category_list"] = list(cm.keys())
            for category, item_name in new_items:
                if category not in im:
                    im[category] = {}
                if not any(info.get("name_jp") == item_name for info in im[category].values()):
                    new_id = self._generate_item_id(item_name)
                    im[category][new_id] = {"name_jp": item_name, "name_en": item_name, "attributes": {}}
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                self.load_config()
                self._ensure_master_updated()
            except Exception:
                pass
            # 新規追加したので attribute_id と obj_type を再取得
            rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
            attribute_id = rev_cat_map.get(attribute, "")
            if attribute_id and attribute_id in self.attr_mapping:
                o = self.attr_mapping[attribute_id]
                if isinstance(o, dict):
                    obj_type = o.get("type", "loot")

        # カテゴリスロットからデータを収集
        categories_data = self._collect_pin_categories_data()

        # 選択属性の新規値をマスタの options に追加（アイテム or カテゴリ）
        for cat_data in categories_data:
            cat, iid, attrs = cat_data.get("category"), cat_data.get("item_id"), cat_data.get("attributes", {})
            for attr_key, attr_val in attrs.items():
                if not attr_val:
                    continue
                ac = None
                # カテゴリに属性があればそこから取得
                if cat and cat in self.config.get("category_master", {}):
                    cat_entry = self.config["category_master"][cat]
                    if isinstance(cat_entry, dict) and cat_entry.get("attributes", {}).get(attr_key):
                        ac = cat_entry["attributes"][attr_key]
                # なければアイテムから
                if ac is None and iid and cat in self.config.get("item_master", {}):
                    item_entry = self.config["item_master"][cat].get(iid, {})
                    if isinstance(item_entry, dict):
                        ac = item_entry.get("attributes", {}).get(attr_key)
                if isinstance(ac, dict) and ac.get("type") == "select":
                    opts = list(ac.get("options", []))
                    if attr_val not in opts:
                        opts.append(attr_val)
                        try:
                            if cat and cat in self.config.get("category_master", {}):
                                ce = self.config["category_master"][cat]
                                if isinstance(ce, dict) and ce.get("attributes", {}).get(attr_key):
                                    ce["attributes"][attr_key] = {"type": "select", "options": opts}
                            elif iid and cat in self.config.get("item_master", {}):
                                ie = self.config["item_master"][cat].get(iid, {})
                                if isinstance(ie, dict):
                                    if "attributes" not in ie:
                                        ie["attributes"] = {}
                                    ie["attributes"][attr_key] = {"type": "select", "options": opts}
                            with open(self.config_path, "w", encoding="utf-8") as f:
                                json.dump(self.config, f, indent=4, ensure_ascii=False)
                            self.load_config()
                            self._ensure_master_updated()
                        except Exception:
                            pass
                        break

        # オブジェクト属性を収集
        obj_attributes = {}
        for attr_key, widget_data in self.obj_attr_widgets.items():
            if isinstance(widget_data, dict):
                widget = widget_data.get("widget")
                if widget:
                    val = widget.get()
                    if val and val != "(なし)":
                        obj_attributes[attr_key] = val
        
        # 重要度
        importance = self.cmb_importance.get()
        if importance == "(なし)": importance = ""
        
        # メインカテゴリ（旧互換の category 列）。アイテム表示名は categories JSON に含まれる。
        if categories_data:
            main_category = categories_data[0]["category"]
        else:
            main_category = ""
        # 地点の名称（別名）: 入力欄をそのまま保存。空のときマスタ名で埋めない（再読込で空のまま）。
        name_jp = (self.ent_name_jp.get() or "").strip()
        name_en = (self.ent_name_en.get() or "").strip()

        obj_name_en_override = (self.ent_obj_en.get() or "").strip()
        raw_lj = (self.ent_link_jp.get() or "").strip()
        raw_le = (self.ent_link_en.get() or "").strip()
        link_jp, wj = self._sanitize_saved_pin_link_url(raw_lj)
        link_en, we = self._sanitize_saved_pin_link_url(raw_le)
        if wj or we:
            messagebox.showwarning("リンクURL", "\n".join(x for x in (wj, we) if x))
        marker_display_style = ""
        if self.current_uid:
            for d0 in self.data_list:
                if d0.get("uid") == self.current_uid:
                    marker_display_style = (d0.get("marker_display_style") or "").strip()
                    break
        pin_x_for_save = pin_y_for_save = None
        if self.current_uid:
            row0 = self._get_pin_row_by_uid(self.current_uid)
            if row0 is not None:
                try:
                    pin_x_for_save = float(row0.get("x", 0))
                    pin_y_for_save = float(row0.get("y", 0))
                except (TypeError, ValueError):
                    pin_x_for_save = pin_y_for_save = None
            if pin_x_for_save is None or pin_y_for_save is None:
                tc = self.temp_coords
                if tc is not None:
                    try:
                        pin_x_for_save = float(tc[0])
                        pin_y_for_save = float(tc[1])
                    except (TypeError, ValueError, IndexError):
                        pin_x_for_save = pin_y_for_save = None
            if pin_x_for_save is None or pin_y_for_save is None:
                messagebox.showwarning(
                    "入力エラー",
                    "ピンの位置が無効です。地図上で再度クリックして指定してください。",
                )
                return
        else:
            tc = self.temp_coords
            if tc is None:
                messagebox.showwarning(
                    "入力エラー",
                    "新規ピンは地図上をクリックして位置を指定してから保存してください。",
                )
                return
            try:
                pin_x_for_save = float(tc[0])
                pin_y_for_save = float(tc[1])
            except (TypeError, ValueError, IndexError):
                messagebox.showwarning(
                    "入力エラー",
                    "ピンの位置が無効です。地図上で再度クリックして指定してください。",
                )
                return
        dr = {
            'uid': self.current_uid or f"p_{int(datetime.now().timestamp())}",
            'x': pin_x_for_save,
            'y': pin_y_for_save,
            'name_jp': name_jp,
            'name_en': name_en,
            'attribute': attribute_id,
            'obj_name_en': obj_name_en_override or "",
            'obj_attributes': json.dumps(obj_attributes, ensure_ascii=False) if obj_attributes else "",
            'category': main_category,
            'categories': json.dumps(categories_data, ensure_ascii=False) if categories_data else "",
            'importance': importance,
            'memo_jp': self.txt_memo_jp.get("1.0", "end-1c").replace("\n", "<br>"),
            'memo_en': self.txt_memo_en.get("1.0", "end-1c").replace("\n", "<br>"),
            'updated_at': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'link_url_jp': link_jp,
            'link_url_en': link_en,
            'marker_display_style': marker_display_style,
        }
        parent_uid_val = ""
        parent_type_val = ""
        if self.current_uid:
            for d0 in self.data_list:
                if d0.get("uid") == self.current_uid:
                    parent_uid_val = (d0.get("parent_uid") or "").strip()
                    parent_type_val = (d0.get("parent_type") or "").strip()
                    break
        if getattr(self, "cmb_parent_type", None):
            parent_type_val = self._parent_type_value_from_label(self.cmb_parent_type.get())
        dr["parent_uid"] = self._normalize_saved_parent_uid(self.current_uid, parent_uid_val)
        dr["parent_type"] = self._normalize_saved_parent_type(dr["parent_uid"], parent_type_val)
        dr['category_pin'] = attribute_id
        
        if self.current_uid:
            for d in self.data_list:
                if d['uid'] == self.current_uid:
                    d.update({k: v for k, v in dr.items() if v is not None})
                    if self._is_draft_pin_row(d):
                        d.pop("__draft__", None)
                    break
        else:
            self.data_list.append(dr)
        self._pin_save_last_ok = True
        self.mark_dirty(); self.current_uid = self.temp_coords = None; self.refresh_map(); self.clear_ui()

    def delete_data(self):
        if not self.current_uid or not messagebox.askyesno("確認", "削除しますか？"): return
        del_uid = self.current_uid
        self.data_list = [d for d in self.data_list if d['uid'] != del_uid]
        for d in self.data_list:
            if (d.get("parent_uid") or "").strip() == del_uid:
                d["parent_uid"] = ""
                d["parent_type"] = ""
        self.mark_dirty(); self.current_uid = None; self.clear_ui(); self.refresh_map()

    def _get_pin_row_by_uid(self, uid: str):
        u = (uid or "").strip()
        if not u:
            return None
        for d in self.data_list:
            if (d.get("uid") or "").strip() == u:
                return d
        return None

    def _gen_new_pin_uid(self) -> str:
        # 保存前の一時 UID（CSV 保存時はそのまま残る想定）。衝突しにくい短いプレフィックス。
        return f"p_{int(datetime.now().timestamp())}_{id(self) & 0xFFFF:x}"

    def _is_draft_pin_row(self, d) -> bool:
        try:
            return bool(isinstance(d, dict) and d.get("__draft__"))
        except Exception:
            return False

    def _remove_draft_pin_row_if_any(self):
        """未保存の新規ドラフト行を data_list から除去（編集中断・別操作開始時）。"""
        cu = (getattr(self, "current_uid", None) or "").strip()
        before = len(self.data_list)
        self.data_list = [d for d in self.data_list if not self._is_draft_pin_row(d)]
        if before != len(self.data_list) and cu:
            # current_uid がドラフトなら掃除後は無効
            row = self._get_pin_row_by_uid(cu)
            if row is None:
                self.current_uid = None

    def _make_empty_pin_row(self, uid: str, x: float, y: float, draft: bool = True) -> dict:
        return {
            "uid": uid,
            "x": float(x),
            "y": float(y),
            "name_jp": "",
            "name_en": "",
            "attribute": "",
            "obj_name_en": "",
            "obj_attributes": "",
            "category": "",
            "categories": "",
            "importance": "",
            "category_pin": "",
            "contents": "",
            "memo_jp": "",
            "memo_en": "",
            "updated_at": "",
            "link_url_jp": "",
            "link_url_en": "",
            "marker_display_style": "",
            "parent_uid": "",
            "parent_type": "",
            **({"__draft__": True} if draft else {}),
        }

    def _sync_draft_pin_row_core_from_ui(self):
        """ドラフト新規ピン行に、座標以外の最小フィールドを UI から反映（マップ描画・親設定の整合用）。"""
        uid = (getattr(self, "current_uid", None) or "").strip()
        if not uid:
            return
        row = self._get_pin_row_by_uid(uid)
        if row is None or not self._is_draft_pin_row(row):
            return
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        attribute = (self.cmb_attribute.get() or "").strip()
        attribute_id = rev_cat_map.get(attribute, "") if attribute and attribute != "(なし)" else ""
        row["attribute"] = attribute_id
        row["category_pin"] = attribute_id

    def _purge_stale_draft_pins(self, keep_uid: str = ""):
        """別ピンへ切り替えるなどで、取り残されたドラフト新規行を掃除する。"""
        ku = (keep_uid or "").strip()
        before = len(self.data_list)
        self.data_list = [d for d in self.data_list if (not self._is_draft_pin_row(d)) or ((d.get("uid") or "").strip() == ku)]
        if before != len(self.data_list):
            cu = (getattr(self, "current_uid", None) or "").strip()
            if cu and self._get_pin_row_by_uid(cu) is None:
                self.current_uid = None

    def _normalize_parent_type(self, raw_type, has_parent: bool) -> str:
        t = str(raw_type or "").strip().lower()
        if t in ("in the area", "in-the-area", "in_the_area", "area", "inside_area", "inside-area"):
            t = "in_area"
        if t not in PARENT_TYPE_VALUES:
            t = PARENT_TYPE_DEFAULT if has_parent else ""
        return t

    def _parent_type_label(self, type_value: str) -> str:
        t = self._normalize_parent_type(type_value, True)
        return PARENT_TYPE_LABELS.get(t, PARENT_TYPE_LABELS[PARENT_TYPE_DEFAULT])

    def _parent_type_value_from_label(self, label: str) -> str:
        s = str(label or "").strip()
        if not s:
            return PARENT_TYPE_DEFAULT
        for k, v in PARENT_TYPE_LABELS.items():
            if s == v:
                return k
        low = s.lower()
        for k in PARENT_TYPE_VALUES:
            if low == k:
                return k
        return PARENT_TYPE_DEFAULT

    def _sync_parent_type_combo_from_row(self):
        cmb = getattr(self, "cmb_parent_type", None)
        if cmb is None:
            return
        uid = (getattr(self, "current_uid", None) or "").strip()
        row = self._get_pin_row_by_uid(uid) if uid else None
        has_parent = bool(row and str(row.get("parent_uid") or "").strip())
        t = self._normalize_parent_type((row or {}).get("parent_type"), has_parent)
        try:
            cmb.set(self._parent_type_label(t))
            cmb.configure(state=("normal" if has_parent else "disabled"))
        except Exception:
            pass

    def _on_parent_type_changed(self):
        uid = (getattr(self, "current_uid", None) or "").strip()
        if not uid:
            return
        row = self._get_pin_row_by_uid(uid)
        if row is None:
            return
        puid = str(row.get("parent_uid") or "").strip()
        if not puid:
            self._sync_parent_type_combo_from_row()
            return
        raw_label = self.cmb_parent_type.get() if getattr(self, "cmb_parent_type", None) else ""
        new_type = self._normalize_parent_type(self._parent_type_value_from_label(raw_label), True)
        old_type = self._normalize_parent_type(row.get("parent_type"), True)
        if new_type == old_type:
            return
        row["parent_type"] = new_type
        self.mark_dirty()
        self._refresh_parent_pin_ui_labels()
        self.refresh_map()
        self._schedule_pin_preview_refresh()

    def _normalize_saved_parent_uid(self, child_uid, raw_parent: str) -> str:
        p = (raw_parent or "").strip()
        if not p:
            return ""
        cu = (child_uid or "").strip()
        if cu and p == cu:
            return ""
        if not self._get_pin_row_by_uid(p):
            return ""
        return p

    def _normalize_saved_parent_type(self, parent_uid: str, raw_parent_type) -> str:
        has_parent = bool(str(parent_uid or "").strip())
        return self._normalize_parent_type(raw_parent_type, has_parent)

    def _would_create_parent_cycle(self, child_uid: str, new_parent_uid: str) -> bool:
        seen = set()
        cur = (new_parent_uid or "").strip()
        c0 = (child_uid or "").strip()
        while cur:
            if cur == c0:
                return True
            if cur in seen:
                break
            seen.add(cur)
            row = self._get_pin_row_by_uid(cur)
            cur = (row.get("parent_uid") or "").strip() if row else ""
        return False

    def _refresh_parent_pin_ui_labels(self):
        if not getattr(self, "lbl_parent_info", None):
            return
        if not (getattr(self, "current_uid", None) or "").strip():
            self.lbl_parent_info.configure(text="現在: （親ピンは地図上の既存ピンから選べます）")
            self.btn_parent_pick.configure(state="disabled")
            self.btn_parent_clear.configure(state="disabled")
            self.lbl_parent_mode.configure(text="")
            self._sync_parent_type_combo_from_row()
            return
        self.btn_parent_pick.configure(state="normal")
        d = self._get_pin_row_by_uid(self.current_uid)
        puid = (d.get("parent_uid") or "").strip() if d else ""
        if puid:
            prow = self._get_pin_row_by_uid(puid)
            tx = "現在: " + self._pin_label_for_uid(puid)
            if not prow:
                tx += " （参照が無効です。保存時にクリアされます）"
            ptype = self._normalize_saved_parent_type(puid, d.get("parent_type") if d else "")
            tx += f" / タイプ: {self._parent_type_label(ptype)}"
            self.lbl_parent_info.configure(text=tx)
            self.btn_parent_clear.configure(state="normal")
        else:
            self.lbl_parent_info.configure(text="現在: （親なし）")
            self.btn_parent_clear.configure(state="disabled")
        if getattr(self, "_parent_pick_mode", False):
            self.lbl_parent_mode.configure(
                text="親にするピンを地図上でクリックしてください（Escでキャンセル）"
            )
        else:
            self.lbl_parent_mode.configure(text="")
        self._sync_parent_type_combo_from_row()

    def _pin_label_for_uid(self, uid: str) -> str:
        d = self._get_pin_row_by_uid(uid)
        if not d:
            return uid or "?"
        nj = (d.get("name_jp") or "").strip()
        ne = (d.get("name_en") or "").strip()
        u = (d.get("uid") or "").strip() or uid
        if nj:
            return f"{nj} ({u})"
        if ne:
            return f"{ne} ({u})"
        return u

    def _begin_parent_pick_mode(self):
        if not (getattr(self, "current_uid", None) or "").strip():
            messagebox.showinfo("親ピン", "先にピンを選択してください。")
            return
        self._parent_pick_mode = True
        self._refresh_parent_pin_ui_labels()
        self.refresh_map()

    def _cancel_parent_pick_mode(self):
        if getattr(self, "_parent_pick_mode", False):
            self._parent_pick_mode = False
            self._refresh_parent_pin_ui_labels()

    def _on_escape_editor(self):
        if getattr(self, "_parent_pick_mode", False):
            self._cancel_parent_pick_mode()
            self.refresh_map()

    def _clear_parent_pin(self):
        uid = (getattr(self, "current_uid", None) or "").strip()
        if not uid:
            return
        d = self._get_pin_row_by_uid(uid)
        if d is not None:
            d["parent_uid"] = ""
            d["parent_type"] = ""
        self.mark_dirty()
        self._refresh_parent_pin_ui_labels()
        self.refresh_map()
        self._schedule_pin_preview_refresh()

    def _apply_parent_pick(self, target_uid: str):
        target_uid = (target_uid or "").strip()
        cu = (getattr(self, "current_uid", None) or "").strip()
        if not cu or not target_uid or target_uid == cu:
            messagebox.showinfo("親ピン", "自分自身は親にできません。")
            return
        if not self._get_pin_row_by_uid(target_uid):
            messagebox.showwarning("親ピン", "無効なピンです。")
            return
        if self._would_create_parent_cycle(cu, target_uid):
            messagebox.showwarning("親ピン", "循環する親子関係にはできません。")
            return
        row = self._get_pin_row_by_uid(cu)
        if row is not None:
            row["parent_uid"] = target_uid
            selected_type = self._parent_type_value_from_label(
                self.cmb_parent_type.get() if getattr(self, "cmb_parent_type", None) else ""
            )
            row["parent_type"] = self._normalize_saved_parent_type(target_uid, selected_type)
        self._parent_pick_mode = False
        self.mark_dirty()
        self._refresh_parent_pin_ui_labels()
        self.refresh_map()
        self._schedule_pin_preview_refresh()

    def _sanitize_pin_parent_refs(self):
        uids = {(d.get("uid") or "").strip() for d in self.data_list if d.get("uid")}
        for d in self.data_list:
            p = (d.get("parent_uid") or "").strip()
            if not p:
                d["parent_type"] = ""
                continue
            own = (d.get("uid") or "").strip()
            if p == own or p not in uids:
                d["parent_uid"] = ""
                d["parent_type"] = ""
            else:
                d["parent_type"] = self._normalize_saved_parent_type(p, d.get("parent_type"))

    def write_files(self):
        p = os.path.join(self.game_path, self.config.get("save_file", "master_data.csv"))
        # 新しいフィールドと後方互換性のためのフィールドを含める
        flds = ["uid", "x", "y", "name_jp", "name_en", "attribute", "obj_name_en", "obj_attributes", "category", "categories", "importance", "category_pin", "contents", "memo_jp", "memo_en", "updated_at", "link_url_jp", "link_url_en", "marker_display_style", "parent_uid", "parent_type"]
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=flds, extrasaction='ignore')
            writer.writeheader(); writer.writerows(self.data_list)

    def load_csv(self):
        p = os.path.join(self.game_path, self.config.get("save_file", "master_data.csv"))
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f); rows = []
                for row in reader:
                    d = dict(row); d['x'] = float(row['x']); d['y'] = float(row['y'])
                    
                    # 後方互換性：旧形式のデータを新形式に変換
                    if 'category_main' in row and not row.get('category_pin'): 
                        d['category_pin'] = row['category_main']
                    if 'category_pin' in row and 'attribute' not in row:
                        d['attribute'] = d.get('category_pin', 'MISC_OTHER')
                    
                    if 'contents' not in row: d['contents'] = ""
                    if 'category' not in row: d['category'] = ""
                    if 'categories' not in row: d['categories'] = ""
                    if 'obj_name_en' not in row: d.setdefault('obj_name_en', '')
                    if 'importance' not in row: d['importance'] = ""
                    if 'obj_attributes' not in row: d['obj_attributes'] = ""
                    if 'updated_at' not in row: d['updated_at'] = ""
                    if 'link_url_jp' not in row: d.setdefault('link_url_jp', '')
                    if 'link_url_en' not in row: d.setdefault('link_url_en', '')
                    if 'marker_display_style' not in row: d.setdefault('marker_display_style', '')
                    if 'parent_uid' not in row: d.setdefault('parent_uid', '')
                    if 'parent_type' not in row: d.setdefault('parent_type', '')
                    rows.append(d)
                self.data_list = rows
                self._sanitize_pin_parent_refs()

    # --- エリアデータの保存・読込（areas.json） ---
    def load_areas(self):
        """areas.json からエリア情報を読み込む"""
        self.area_list = []
        if not os.path.exists(self.areas_path):
            return
        try:
            with open(self.areas_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            areas = data.get("areas", [])
            norm_areas = []
            for a in areas:
                if not isinstance(a, dict):
                    continue
                # 座標関係は float に正規化
                for key in ("x", "y", "radius", "width", "height"):
                    if key in a and a[key] is not None:
                        try:
                            a[key] = float(a[key])
                        except Exception:
                            pass
                pts = a.get("points") or []
                norm_pts = []
                for pt in pts:
                    if isinstance(pt, (list, tuple)) and len(pt) == 2:
                        try:
                            norm_pts.append([float(pt[0]), float(pt[1])])
                        except Exception:
                            continue
                a["points"] = norm_pts
                if "uid" not in a and norm_pts:
                    a["uid"] = f"AREA_{len(norm_areas)+1}"
                norm_areas.append(a)
            self.area_list = norm_areas
        except Exception:
            # 壊れていてもエディタ自体は動くようにする
            self.area_list = []

    def save_areas(self):
        """エリア情報を areas.json に保存する"""
        data = {"areas": self.area_list or []}
        try:
            with open(self.areas_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            # 保存エラーはメッセージだけに留める
            messagebox.showerror("エリア保存エラー", "areas.json の保存に失敗しました。")

    def load_to_ui(self, d) -> bool:
        if self._pin_edit_has_unsaved_changes():
            if not self._confirm_pin_edit_discard_or_save():
                return False
        self._purge_stale_draft_pins((d.get("uid") or "").strip())
        self._suppress_special_notes_rebuild = True
        self._suppress_obj_en_auto_sync = True
        try:
            self._pin_placement_active = False
            uid_early = (d.get("uid") or "").strip()
            if uid_early:
                self.temp_coords = None
            # 別ピン読込時は前ピンの特記チェック状態を引き継がない。
            self._pin_special_note_aggregate = {}
            self._reset_pin_form_widgets()
        
            # 属性を設定（後方互換性対応）— d['attribute'] は ID を想定。旧データで表示名だけの場合は ID に逆引き
            raw_attr = d.get('attribute') or d.get('category_pin') or d.get('category_main', 'MISC_OTHER')
            attr_key = raw_attr
            if raw_attr and raw_attr not in self.attr_mapping:
                rev = {v: k for k, v in self.cat_mapping.items()}
                attr_key = rev.get(raw_attr, raw_attr)
            attr_display = self._attr_display_name(attr_key)
            if attr_display:
                vals = list(self.cmb_attribute.cget("values"))
                if attr_display not in vals:
                    self.cmb_attribute.configure(values=vals + [attr_display])
                self.cmb_attribute.set(attr_display)
                self.on_attribute_changed()
        
            # オブジェクト属性を読み込み
            obj_attrs_json = d.get('obj_attributes', '')
            if obj_attrs_json:
                try:
                    obj_attrs = json.loads(obj_attrs_json)
                    for attr_key, attr_val in obj_attrs.items():
                        if attr_key in self.obj_attr_widgets:
                            widget_data = self.obj_attr_widgets[attr_key]
                            if isinstance(widget_data, dict):
                                widget = widget_data.get("widget")
                                if widget:
                                    if widget_data.get("type") == "number":
                                        widget.delete(0, "end")
                                        widget.insert(0, str(attr_val))
                                    else:
                                        widget.set(attr_val)
                except:
                    pass
        
            # 重要度を設定
            importance = d.get('importance', '')
            if importance:
                self.cmb_importance.set(importance)
        
            # カテゴリデータを読み込み（新形式）。cat_id があればマスタから表示名を解決
            category_id_to_name = {}
            for name, info in self.category_master.items():
                if isinstance(info, dict) and info.get("id"):
                    category_id_to_name[info["id"]] = name
            categories_json = d.get('categories', '')
            if categories_json:
                try:
                    categories_data = json.loads(categories_json)
                    for cat_data in categories_data:
                        slot = self.add_category_slot()
                        cat_id = cat_data.get('cat_id', '')
                        category = category_id_to_name.get(cat_id) if cat_id else cat_data.get('category', '')
                        if not category:
                            category = cat_id or cat_data.get('category', '')
                        item_id = cat_data.get('item_id', '')
                        qty = cat_data.get('qty', '1')
                        attrs = cat_data.get("attributes", {}) or {}
                        slot["_loaded_attributes"] = dict(attrs) if isinstance(attrs, dict) else {}
                    
                        if category:
                            if category not in self.category_list:
                                self.category_list.append(category)
                            self._merge_pin_category_combo_values(slot, category)
                            slot["category"].set(category)
                            self.on_slot_category_changed(slot["frame"])
                        
                            # 数量を設定
                            slot["qty"].delete(0, "end")
                            slot["qty"].insert(0, qty)
                            self._set_slot_many_mode(slot, self._is_many_qty_token(qty))
                            # 分類(EN)・アイテム(EN)はマスタ表示のみ（on_slot_category_changed / on_slot_item_changed で更新）
                        
                            # アイテム選択ありの場合
                            if item_id and category in self.item_master and item_id in self.item_master[category]:
                                item_name = self.item_master[category][item_id]["name_jp"]
                                slot["item"].set(item_name)
                                self.on_slot_item_changed(slot["frame"])
                            
                                # アイテム属性を設定
                                item_attrs = cat_data.get('attributes', {}) or cat_data.get('item_attributes', {})
                                for attr_key, attr_val in item_attrs.items():
                                    if attr_key in slot.get("attr_widgets", {}):
                                        widget_data = slot["attr_widgets"][attr_key]
                                        if isinstance(widget_data, dict):
                                            attr_type = widget_data.get("type", "select")
                                            if attr_type == "fixed":
                                                # 固定値は設定不要
                                                pass
                                            elif attr_type == "number":
                                                widget = widget_data.get("widget")
                                                if widget:
                                                    widget.delete(0, "end")
                                                    widget.insert(0, str(attr_val))
                                            else:  # select
                                                w = widget_data.get("widget")
                                                if w and hasattr(w, "set"):
                                                    w.set(attr_val)
                                        else:
                                            if hasattr(widget_data, "set"):
                                                widget_data.set(attr_val)
                except:
                    pass
        
            # 後方互換性：旧形式のデータから読み込む
            if not categories_json:
                category = d.get('category', '')
                item_id = d.get('item_id', '')
            
                if category and item_id:
                    slot = self.add_category_slot()
                    if category not in self.category_list:
                        self.category_list.append(category)
                    self._merge_pin_category_combo_values(slot, category)
                    slot["category"].set(category)
                    self.on_slot_category_changed(slot["frame"])
                    if category in self.item_master and item_id in self.item_master[category]:
                        item_name = self.item_master[category][item_id]["name_jp"]
                        slot["item"].set(item_name)
                        self.on_slot_item_changed(slot["frame"])
            
                # 旧contents形式から読み込む
                contents = d.get('contents', "")
                if contents:
                    items = contents.split("|")
                    for item_str in items:
                        parts = item_str.split(":")
                        if len(parts) > 0:
                            old_item_id = parts[0]
                            qty = parts[1] if len(parts) > 1 else "1"
                            loaded_attrs = {}
                            for p in parts[2:]:
                                if "=" in p:
                                    k, v = p.split("=", 1)
                                    loaded_attrs[k] = v
                        
                            # 旧item_idからカテゴリとアイテム名を検索
                            for grp, vals in self.item_master.items():
                                if old_item_id in vals:
                                    slot = self.add_category_slot()
                                    if grp not in self.category_list:
                                        self.category_list.append(grp)
                                    self._merge_pin_category_combo_values(slot, grp)
                                    slot["category"].set(grp)
                                    self.on_slot_category_changed(slot["frame"])
                                    slot["item"].set(vals[old_item_id]["name_jp"])
                                    self.on_slot_item_changed(slot["frame"])
                                    slot["qty"].delete(0, "end")
                                    slot["qty"].insert(0, qty)
                                    self._set_slot_many_mode(slot, self._is_many_qty_token(qty))
                                
                                    for k, v in loaded_attrs.items():
                                        if k in slot["attr_widgets"]:
                                            wd = slot["attr_widgets"][k]
                                            target = wd.get("widget", wd) if isinstance(wd, dict) else wd
                                            if hasattr(target, "set"):
                                                target.set(v)
                                    break
        
            self.txt_memo_jp.insert("1.0", d.get('memo_jp','').replace("<br>", "\n"))
            self.txt_memo_en.insert("1.0", d.get('memo_en','').replace("<br>", "\n"))
            # 表示名（上書き用）
            self.ent_name_jp.delete(0, "end")
            self.ent_name_en.delete(0, "end")
            self.ent_name_jp.insert(0, d.get('name_jp', '') or '')
            self.ent_name_en.insert(0, d.get('name_en', '') or '')
            if getattr(self, "ent_obj_en", None):
                self.ent_obj_en.delete(0, "end")
                self.ent_obj_en.insert(0, d.get('obj_name_en', '') or '')
            if getattr(self, "ent_link_jp", None):
                self.ent_link_jp.delete(0, "end")
                self.ent_link_jp.insert(0, d.get('link_url_jp', '') or '')
                self.ent_link_en.delete(0, "end")
                self.ent_link_en.insert(0, d.get('link_url_en', '') or '')
                self._sync_link_combo_values()

        finally:
            self._suppress_special_notes_rebuild = False
            self._suppress_obj_en_auto_sync = False
            self._refresh_category_slot_nav_buttons()

        self._show_pin_editor_panel()
        uid = (d.get("uid") or "").strip()
        if uid:
            self.current_uid = uid
            try:
                x, y = float(d.get("x", 0)), float(d.get("y", 0))
                self.lbl_coords.configure(text=f"座標: ({int(x)}, {int(y)})")
            except (TypeError, ValueError):
                self.lbl_coords.configure(text="座標: ---")
        else:
            self.current_uid = None
            self.lbl_coords.configure(text="座標: ---")
        self._sync_parent_type_combo_from_row()
        self._rebuild_pin_special_notes_ui()
        self._schedule_pin_preview_refresh()
        self._refresh_parent_pin_ui_labels()
        self._pin_edit_baseline = self._build_pin_compare_snapshot()
        return True

    def _templates_path(self):
        return os.path.join(self.game_path, "templates.json")

    def _load_templates(self):
        try:
            with open(self._templates_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("templates", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_templates(self, templates_list):
        with open(self._templates_path(), "w", encoding="utf-8") as f:
            json.dump({"templates": templates_list}, f, indent=2, ensure_ascii=False)

    def _get_current_as_template(self):
        """現在のフォーム内容を定型用の辞書で返す。オブジェクト未選択なら None。"""
        attribute = self.cmb_attribute.get()
        if not attribute or attribute == "(なし)":
            return None
        rev = {v: k for k, v in self.cat_mapping.items()}
        attribute_id = rev.get(attribute, "")
        obj_attributes = {}
        for attr_key, widget_data in self.obj_attr_widgets.items():
            if isinstance(widget_data, dict):
                w = widget_data.get("widget")
                if w:
                    val = w.get()
                    if val and val != "(なし)":
                        obj_attributes[attr_key] = val
        categories_data = self._collect_pin_categories_data()
        return {
            "attribute_id": attribute_id,
            "obj_attributes": obj_attributes,
            "categories": categories_data,
            "importance": self.cmb_importance.get() if self.cmb_importance.get() != "(なし)" else "",
            "link_url_jp": (self.ent_link_jp.get() or "").strip() if getattr(self, "ent_link_jp", None) else "",
            "link_url_en": (self.ent_link_en.get() or "").strip() if getattr(self, "ent_link_en", None) else "",
        }

    def _apply_template(self, tpl):
        """定型をフォームに適用（座標・メモは触らない）"""
        aid = (tpl.get("attribute_id") or "").strip()
        d = {
            "attribute": aid,
            "obj_attributes": json.dumps(tpl.get("obj_attributes", {})),
            "categories": json.dumps(tpl.get("categories", [])),
            "importance": tpl.get("importance", ""),
            "memo_jp": "",
            "memo_en": "",
            "link_url_jp": tpl.get("link_url_jp", ""),
            "link_url_en": tpl.get("link_url_en", ""),
        }
        if not self._confirm_pin_edit_discard_or_save():
            return
        self.clear_ui()
        self.load_to_ui(d)

    def open_template_dialog(self):
        templates = self._load_templates()
        if not templates:
            messagebox.showinfo(
                "定型から作成",
                "定型がありません。\nゲームフォルダ内の templates.json に templates 配列を用意してください。",
            )
            return
        win = ctk.CTkToplevel(self)
        win.title("定型から作成")
        win.geometry("340x300")
        win.attributes("-topmost", True)
        ctk.CTkLabel(win, text="定型を選んで「選択」を押すと、フォームに反映されます。", font=("Meiryo", 10)).pack(pady=8, padx=10)
        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        listbox = tk.Listbox(frame, font=("Meiryo", 11), height=10, selectmode=tk.SINGLE)
        listbox.pack(fill="both", expand=True)
        for t in templates:
            listbox.insert(tk.END, t.get("name", "(名前なし)"))
        if templates:
            listbox.selection_set(0)
        def on_select():
            cur = listbox.curselection()
            if cur:
                self._apply_template(templates[cur[0]])
                win.destroy()
        ctk.CTkButton(win, text="選択", command=on_select, fg_color="#27ae60", width=120).pack(pady=10)

    def clear_ui(self):
        self._cancel_parent_pick_mode()
        self._pin_placement_active = False
        self.temp_coords = None
        self.current_uid = None
        self.current_area_uid = None
        self._pin_edit_baseline = None
        if self.area_mode in ("create_polygon", "create_circle", "create_rect", "edit_polygon"):
            self.set_area_mode("idle")
        self._reset_pin_form_widgets()
        self._hide_pin_editor_idle()
        self.lbl_coords.configure(text="座標: ---")
        self._refresh_parent_pin_ui_labels()