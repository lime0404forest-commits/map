import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import customtkinter as ctk
import os
import json
import csv
import math
import re  # 追加
from datetime import datetime
from PIL import Image, ImageTk

from .constants import GAMES_ROOT
from .utils import save_cropped_image_with_annotations
from .export_utils import export_pins_to_json

# 入力ボックス共通スタイル（枠ではなく「ボックス本体」の見た目を統一）
BOX_FG = "#2e4053"           # やや柔らかい青系の塗り
BOX_CORNER = 8               # 角丸でカード風に
BOX_BORDER_WIDTH = 1
BOX_BORDER_COLOR = "#3d5166" # 控えめな縁で立体感
BOX_PADX, BOX_PADY = 12, 10 # 内側の余白

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
        self.geometry("1100x850") # 英語欄が増えたので幅を拡大
        self.attributes("-topmost", True)
        self.parent = parent
        self.config_path = config_path
        self.config = current_config
        
        self.attr_rows = []
        self.cat_rows = []
        self.item_rows = []
        
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.tab_attr = self.tabview.add("🏷️ オブジェクト設定")
        self.tab_cat = self.tabview.add("📋 カテゴリリスト設定")
        self.tab_item = self.tabview.add("📦 アイテムマスタ設定")
        self.tab_en = self.tabview.add("🌐 EN未設定確認")
        
        self.setup_attr_tab()
        self.setup_cat_tab()
        self.setup_item_tab()
        self.setup_en_tab()

        f_foot = ctk.CTkFrame(self, fg_color="transparent")
        f_foot.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(f_foot, text="💾 設定を保存して反映", command=self.save_settings, 
                      fg_color="#27ae60", width=200, height=40, font=("Meiryo", 12, "bold")).pack()

    def setup_attr_tab(self):
        # オブジェクト種類リスト
        self.object_types = ["loot", "landmark", "colony", "other"]
        self.object_type_names = {
            "loot": "アイテムルート源",
            "landmark": "ランドマーク",
            "colony": "群生地",
            "other": "その他"
        }
        
        f_head = ctk.CTkFrame(self.tab_attr, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(f_head, text="表示名(JP)", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="表示名(EN)", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="種類", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="属性項目", width=100, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="自動生成ID", width=120, anchor="w", font=("Meiryo", 11, "bold"), text_color="#888888").pack(side="left", padx=2)
        self.scroll_attr = ctk.CTkScrollableFrame(self.tab_attr, fg_color="#2b2b2b")
        self.scroll_attr.pack(expand=True, fill="both", padx=5, pady=5)
        ctk.CTkButton(self.tab_attr, text="＋ オブジェクト行を追加", command=self.add_attr_row_empty, fg_color="#e67e22").pack(pady=5)

    def setup_cat_tab(self):
        f_head = ctk.CTkFrame(self.tab_cat, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(f_head, text="カテゴリ名(JP)", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=3)
        ctk.CTkLabel(f_head, text="カテゴリ名(EN)", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=3)
        ctk.CTkLabel(f_head, text="対応種類", width=100, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=3)
        ctk.CTkLabel(f_head, text="入力形式", width=100, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=3)
        ctk.CTkLabel(f_head, text="数量", width=50, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=3)
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
        ctk.CTkLabel(f_head, text="グループ", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="ID", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="名前(JP)", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="名前(EN)", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2) # ★追加
        ctk.CTkLabel(f_head, text="属性・操作", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)

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
        # オブジェクト設定（JP/EN + type + attributes対応）
        attr_mapping = self.config.get("attr_mapping", {})
        # 後方互換性：旧cat_mappingから変換
        if not attr_mapping:
            old_mapping = self.config.get("cat_mapping", {})
            if old_mapping:
                attr_mapping = {}
                for k, v in old_mapping.items():
                    attr_mapping[k] = {"name_jp": v, "name_en": k, "type": "loot", "attributes": {}}
        
        if not attr_mapping: self.add_attr_row("", "", "loot", {})
        for k, v in attr_mapping.items():
            if isinstance(v, dict):
                self.add_attr_row(
                    v.get("name_jp", ""), 
                    v.get("name_en", ""),
                    v.get("type", "loot"),
                    v.get("attributes", {})
                )
            else:
                # 旧形式
                self.add_attr_row(v, k, "loot", {})

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
        
        if not category_master: self.add_cat_row("", "", "loot", "item_select", True, "")
        for cat_key, cat_info in category_master.items():
            if isinstance(cat_info, dict):
                self.add_cat_row(
                    cat_info.get("name_jp", cat_key),
                    cat_info.get("name_en", ""),
                    cat_info.get("type", "loot"),
                    cat_info.get("input_type", "item_select"),
                    cat_info.get("show_qty", True),
                    cat_info.get("id", "")
                )
            else:
                self.add_cat_row(cat_info, "", "loot", "item_select", True, "")

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

    def add_attr_row_empty(self):
        self.add_attr_row("", "", "loot", {})
        self.after(10, lambda: self.scroll_attr._parent_canvas.yview_moveto(1.0))

    def add_attr_row(self, name_jp, name_en, obj_type="loot", attributes=None):
        if attributes is None:
            attributes = {}
        
        f = ctk.CTkFrame(self.scroll_attr, fg_color="transparent")
        f.pack(fill="x", pady=2)
        e_name_jp = ctk.CTkEntry(f, width=150); e_name_jp.insert(0, name_jp); e_name_jp.pack(side="left", padx=2)
        e_name_en = ctk.CTkEntry(f, width=150); e_name_en.insert(0, name_en); e_name_en.pack(side="left", padx=2)
        
        # 種類選択
        type_display_list = [self.object_type_names.get(t, t) for t in self.object_types]
        cmb_type = ctk.CTkComboBox(f, values=type_display_list, width=120)
        cmb_type.set(self.object_type_names.get(obj_type, "アイテムルート源"))
        cmb_type.pack(side="left", padx=2)
        
        # 属性項目ボタン
        attr_var = {"data": attributes if attributes else {}}
        btn_attr = ctk.CTkButton(f, text=f"属性({len(attr_var['data'])})", width=80, fg_color="#8e44ad",
                                 command=lambda: self.edit_obj_attributes(attr_var, btn_attr))
        btn_attr.pack(side="left", padx=2)
        
        # 自動生成IDラベル（読み取り専用）
        lbl_id = ctk.CTkLabel(f, text=self.generate_id_from_en(name_en), width=120, text_color="#888888", anchor="w")
        lbl_id.pack(side="left", padx=2)
        
        # 英語名変更時にIDを更新
        def on_en_change(*args):
            lbl_id.configure(text=self.generate_id_from_en(e_name_en.get()))
        e_name_en.bind("<KeyRelease>", on_en_change)
        
        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", command=lambda: self.delete_row(f, self.attr_rows)).pack(side="left", padx=5)
        self.attr_rows.append({"frame": f, "name_jp": e_name_jp, "name_en": e_name_en, "type": cmb_type, "attr_var": attr_var})

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
        self.add_cat_row("", "", "loot", "item_select", True, "")
        self.after(10, lambda: self.scroll_cat._parent_canvas.yview_moveto(1.0))

    def add_cat_row(self, name_jp, name_en, cat_type="loot", input_type="item_select", show_qty=True, cat_id=""):
        f = ctk.CTkFrame(self.scroll_cat, fg_color="transparent")
        f.pack(fill="x", pady=2)
        e_name_jp = ctk.CTkEntry(f, width=120); e_name_jp.insert(0, name_jp); e_name_jp.pack(side="left", padx=3)
        e_name_en = ctk.CTkEntry(f, width=120); e_name_en.insert(0, name_en); e_name_en.pack(side="left", padx=3)
        e_id = ctk.CTkEntry(f, width=100, placeholder_text="ID"); e_id.insert(0, cat_id); e_id.pack(side="left", padx=3)
        type_display_list = [self.object_type_names.get(t, t) for t in self.object_types]
        cmb_type = ctk.CTkComboBox(f, values=type_display_list, width=100)
        cmb_type.set(self.object_type_names.get(cat_type, "アイテムルート源"))
        cmb_type.pack(side="left", padx=3)
        input_type_options = ["item_select", "qty_only"]
        input_type_names = {"item_select": "アイテム選択", "qty_only": "数量のみ"}
        cmb_input = ctk.CTkComboBox(f, values=[input_type_names[t] for t in input_type_options], width=100)
        cmb_input.set(input_type_names.get(input_type, "アイテム選択"))
        cmb_input.pack(side="left", padx=3)
        show_qty_var = tk.BooleanVar(value=show_qty)
        chk_qty = ctk.CTkCheckBox(f, text="", variable=show_qty_var, width=30)
        chk_qty.pack(side="left", padx=3)
        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", command=lambda: self.delete_row(f, self.cat_rows)).pack(side="left", padx=3)
        self.cat_rows.append({
            "frame": f,
            "name_jp": e_name_jp,
            "name_en": e_name_en,
            "id": e_id,
            "type": cmb_type,
            "input_type": cmb_input,
            "show_qty": show_qty_var
        })

    def add_item_row_empty(self):
        self.add_item_row("", "", "", "", {})
        self.after(10, lambda: self.scroll_item._parent_canvas.yview_moveto(1.0))

    def add_item_row(self, grp, i_id, n_jp, n_en, attrs):
        f = ctk.CTkFrame(self.scroll_item, fg_color="transparent")
        f.pack(fill="x", pady=2)
        
        current_groups = sorted(list(set([r["grp"].get() for r in self.item_rows if r["grp"].get()] + [grp] + ["設計図", "LEM", "その他"])))
        e_grp = ctk.CTkComboBox(f, values=current_groups, width=120)
        e_grp.set(grp)
        e_grp.pack(side="left", padx=2)

        e_id = ctk.CTkEntry(f, width=120); e_id.insert(0, i_id); e_id.pack(side="left", padx=2)
        e_jp = ctk.CTkEntry(f, width=150); e_jp.insert(0, n_jp); e_jp.pack(side="left", padx=2)
        e_en = ctk.CTkEntry(f, width=150); e_en.insert(0, n_en); e_en.pack(side="left", padx=2) # ★追加
        
        attr_var = {"data": attrs} 
        btn_attr = ctk.CTkButton(f, text=f"属性 ({len(attrs)})", width=80, fg_color="#8e44ad",
                                 command=lambda: self.edit_attributes(attr_var, btn_attr))
        btn_attr.pack(side="left", padx=2)

        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", 
                      command=lambda: self.delete_row(f, self.item_rows)).pack(side="left", padx=5)
        
        self.item_rows.append({"frame": f, "grp": e_grp, "id": e_id, "jp": e_jp, "en": e_en, "attr_var": attr_var})

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
            
        csv_path = os.path.join(self.parent.game_path, self.config["save_file"])
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

    def save_settings(self):
        # 種類表示名→ID変換マップ
        type_name_to_id = {v: k for k, v in self.object_type_names.items()}
        
        # オブジェクト設定（JP/EN + type + attributes対応）
        new_attr_mapping = {}
        for r in self.attr_rows:
            n_jp = r["name_jp"].get().strip()
            n_en = r["name_en"].get().strip()
            if n_jp and n_en:
                auto_id = self.generate_id_from_en(n_en)
                if auto_id:
                    # 種類を取得
                    type_display = r["type"].get()
                    obj_type = type_name_to_id.get(type_display, "loot")
                    # 属性を取得
                    attrs = r.get("attr_var", {}).get("data", {})
                    new_attr_mapping[auto_id] = {
                        "name_jp": n_jp, 
                        "name_en": n_en,
                        "type": obj_type,
                        "attributes": attrs
                    }
        self.config["attr_mapping"] = new_attr_mapping
        # 後方互換性のためcat_mappingも設定
        self.config["cat_mapping"] = {k: v["name_jp"] for k, v in new_attr_mapping.items()}

        # カテゴリマスタ（id + JP/EN + type + input_type + show_qty）
        input_type_name_to_id = {"アイテム選択": "item_select", "数量のみ": "qty_only"}
        new_category_master = {}
        for r in self.cat_rows:
            n_jp = r["name_jp"].get().strip()
            n_en = r["name_en"].get().strip()
            cid = r["id"].get().strip() if r.get("id") else ""
            if not cid and n_en:
                cid = self.generate_id_from_en(n_en)
            if not cid and n_jp:
                cid = re.sub(r'[^a-zA-Z0-9_\u3040-\u9fff]', '_', n_jp)[:30].strip('_') or ("cat_" + str(abs(hash(n_jp)))[:8])
            type_display = r["type"].get()
            cat_type = type_name_to_id.get(type_display, "loot")
            input_display = r["input_type"].get()
            input_type = input_type_name_to_id.get(input_display, "item_select")
            show_qty = r["show_qty"].get()
            if n_jp:
                new_category_master[n_jp] = {
                    "id": cid,
                    "name_jp": n_jp,
                    "name_en": n_en,
                    "type": cat_type,
                    "input_type": input_type,
                    "show_qty": show_qty
                }
        self.config["category_master"] = new_category_master
        # 後方互換性のためcategory_listも設定
        self.config["category_list"] = list(new_category_master.keys())

        # アイテムマスタ
        new_master = {}
        for r in self.item_rows:
            g, i, nj, ne = r["grp"].get().strip(), r["id"].get().strip(), r["jp"].get().strip(), r["en"].get().strip()
            attrs = r["attr_var"]["data"]
            if g and i and nj:
                if g not in new_master: new_master[g] = {}
                new_master[g][i] = {"name_jp": nj, "name_en": ne, "attributes": attrs}

        self.config["item_master"] = new_master

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", "設定を保存しました。画面を更新します。")
            self.parent.reload_config()
            self.destroy()
        except Exception as e:
            messagebox.showerror("エラー", f"保存失敗:\n{e}")

# ==========================================
# メインエディタ (変更なし)
# ==========================================
class MapEditor(ctk.CTkToplevel):
    def __init__(self, master, game_name, region_name):
        super().__init__(master)
        self.game_path = os.path.join(GAMES_ROOT, game_name, region_name)
        self.tile_dir = os.path.join(self.game_path, "tiles")
        self.config_path = os.path.join(self.game_path, "config.json")
        self.areas_path = os.path.join(self.game_path, "areas.json")
        
        self.load_config()
        
        if "orig_w" not in self.config:
            m_path = os.path.join(self.game_path, self.config.get("map_file", "map.png"))
            if os.path.exists(m_path):
                with Image.open(m_path) as tmp: self.config["orig_w"], self.config["orig_h"] = tmp.size
                with open(self.config_path, "w", encoding="utf-8") as f: 
                    json.dump(self.config, f, indent=4, ensure_ascii=False)

        self.orig_w, self.orig_h = self.config["orig_w"], self.config["orig_h"]
        zooms = [int(d) for d in os.listdir(self.tile_dir) if d.isdigit()]
        self.max_zoom = max(zooms) if zooms else 0
        self.zoom = float(self.max_zoom) - 0.5
        self.orig_max_dim = (2 ** self.max_zoom) * 256 
        
        self.title(f"Editor - {game_name} ({region_name})")
        self.geometry("1650x950")
        
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
        self.tile_cache = {}
        self.category_slots = []
        
        self.edit_pos_mode_uid = None
        self.is_crop_mode = False
        self.crop_box = {"x": 100, "y": 100, "w": 640, "h": 360}
        self.drag_mode = None
        self.has_dragged = False
        self.drag_start = (0, 0)
        self.active_tool = None
        self.here_pos = None; self.arrow_pos = None

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

    def _toggle_filter(self):
        """ピン表示フィルタの開閉（▼/▶）"""
        self.filter_expanded = not self.filter_expanded
        if self.filter_expanded:
            self.f_filter.pack(fill="x", pady=(0, 4))
            self.lbl_filter_toggle.configure(text="▼ ピン表示フィルタ")
        else:
            self.f_filter.pack_forget()
            self.lbl_filter_toggle.configure(text="▶ ピン表示フィルタ")

    def _ensure_master_updated(self):
        """config 変更後にメモリ上のマスタ参照を更新（オブジェクト・カテゴリ・アイテム・フィルタ）"""
        self.attr_mapping = self.config.get("attr_mapping", {})
        if not self.attr_mapping:
            old_cat_mapping = self.config.get("cat_mapping", {})
            if old_cat_mapping:
                self.attr_mapping = {k: {"name_jp": v, "name_en": ""} for k, v in old_cat_mapping.items()}
        self.cat_mapping = {k: v["name_jp"] if isinstance(v, dict) else v for k, v in self.attr_mapping.items()}
        self.display_names = list(self.cat_mapping.values())
        if hasattr(self, "cmb_attribute"):
            self.cmb_attribute.configure(values=["(なし)"] + self.display_names)
        self.category_master = self.config.get("category_master", {})
        self.category_list = list(self.category_master.keys())
        self.item_master = self.config.get("item_master", {})
        # フィルタチェックボックスを更新（新規オブジェクト分を追加）
        if hasattr(self, "f_filter"):
            for widget in self.f_filter.winfo_children():
                if isinstance(widget, ctk.CTkCheckBox) and "未完成" not in widget.cget("text"):
                    widget.destroy()
            self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
            for n in self.display_names:
                ctk.CTkCheckBox(self.f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)
        # フィルタリストとスロットのコンボボックスを更新
        rev = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev.get(self.cmb_attribute.get(), "")
        obj_type = "loot"
        if attr_id and attr_id in self.attr_mapping:
            o = self.attr_mapping[attr_id]
            if isinstance(o, dict):
                obj_type = o.get("type", "loot")
        self.update_category_list_by_type(obj_type)

    def reload_config(self):
        self.load_config()
        # 属性マッピング（JP/EN対応）- 入れ物（宝箱、洞窟など）
        self.attr_mapping = self.config.get("attr_mapping", {})
        if not self.attr_mapping:
            old_cat_mapping = self.config.get("cat_mapping", {})
            if old_cat_mapping:
                self.attr_mapping = {k: {"name_jp": v, "name_en": ""} for k, v in old_cat_mapping.items()}
        
        self.cat_mapping = {k: v["name_jp"] if isinstance(v, dict) else v for k, v in self.attr_mapping.items()}
        
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
        
        for widget in self.f_filter.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox) and "未完成" not in widget.cget("text"):
                widget.destroy()
        self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
        for n in self.display_names:
            ctk.CTkCheckBox(self.f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)
        
        # フィルタリングされたカテゴリリストを初期化
        self.filtered_category_list = self.category_list[:]
        
        # カテゴリスロットのカテゴリリストを更新
        for slot in self.category_slots:
            slot["category"].configure(values=["(なし)"] + self.category_list)
        
        self.refresh_map()

    def on_attribute_changed(self, *args):
        """オブジェクト（見た目）選択時: ルール①で中身エリアの表示/非表示・追加ボタン制御。オブジェクト属性表示。カテゴリを type でフィルタ。"""
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
            self.f_cat_header.pack_forget()
            self.category_slots_frame.pack_forget()
            if getattr(self, "btn_add_category", None):
                self.btn_add_category.configure(state="disabled")
        else:
            # カテゴリエリアは「オブジェクト＋オブジェクト属性」の直後に表示（表示順を保つ）
            try:
                after_ref = self.obj_attr_frame if self.obj_attr_frame.winfo_ismapped() else self.f_attr
            except Exception:
                after_ref = self.f_attr
            self.f_cat_header.pack(fill="x", padx=20, pady=(10,0), after=after_ref)
            self.category_slots_frame.pack(fill="x", padx=20, pady=5, after=self.f_cat_header)
            if getattr(self, "btn_add_category", None):
                self.btn_add_category.configure(state="normal")
            self.update_category_list_by_type(obj_type)
        # 表示名欄が空ならマスタから初期値を入れる
        self._update_display_name_from_master()
    
    def _update_display_name_from_master(self):
        """表示名（JP/EN）欄を、現在のオブジェクト／先頭スロットのマスタ値で更新する。"""
        if not getattr(self, "ent_name_jp", None) or not getattr(self, "ent_name_en", None):
            return
        rev = {v: k for k, v in self.cat_mapping.items()}
        attr_id = rev.get((self.cmb_attribute.get() or "").strip(), "")
        name_jp, name_en = "", ""
        if self.category_slots:
            slot = self.category_slots[0]
            cat = (slot["category"].get() or "").strip()
            item_name = (slot["item"].get() or "").strip()
            if cat and cat != "(なし)" and item_name and item_name != "(なし)" and cat in self.item_master:
                for iid, info in self.item_master[cat].items():
                    if isinstance(info, dict) and info.get("name_jp") == item_name:
                        name_jp = info.get("name_jp", "")
                        name_en = info.get("name_en", "") or info.get("name_jp", "")
                        break
        if not name_jp and attr_id and attr_id in self.attr_mapping:
            o = self.attr_mapping[attr_id]
            if isinstance(o, dict):
                name_jp = o.get("name_jp", "")
                name_en = o.get("name_en", "") or o.get("name_jp", "")
        self.ent_name_jp.delete(0, "end")
        self.ent_name_en.delete(0, "end")
        if name_jp:
            self.ent_name_jp.insert(0, name_jp)
        if name_en:
            self.ent_name_en.insert(0, name_en)
        # オブジェクト(EN)が空ならマスタの値で埋める
        if getattr(self, "ent_obj_en", None) and not (self.ent_obj_en.get() or "").strip() and attr_id and attr_id in self.attr_mapping:
            o = self.attr_mapping[attr_id]
            if isinstance(o, dict):
                obj_en = o.get("name_en", "") or o.get("name_jp", "")
                self.ent_obj_en.delete(0, "end")
                if obj_en:
                    self.ent_obj_en.insert(0, obj_en)
    
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
        self.obj_attr_frame.pack(fill="x", padx=20, pady=5, after=self.f_attr)
        
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
    
    def update_category_list_by_type(self, obj_type):
        """オブジェクトのtypeに基づいてカテゴリリストをフィルタリング。下位不要な場合は(なし)のみ"""
        # 下位項目が不要なタイプ（landmark等）は(なし)のみ
        if obj_type == "landmark":
            filtered_categories = []
        else:
            # 同じtypeのカテゴリのみ抽出
            filtered_categories = []
            for cat_name, cat_info in self.category_master.items():
                if isinstance(cat_info, dict):
                    cat_type = cat_info.get("type", "loot")
                    if cat_type == obj_type:
                        filtered_categories.append(cat_name)
                else:
                    if obj_type == "loot":
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

    def add_category_slot(self):
        # 入力ボックスと同じ塗りで統一（tk.FrameでCTk相性を回避）
        slot_frame = tk.Frame(self.category_slots_frame, bg=BOX_FG, relief="ridge", bd=1)
        slot_frame.pack(fill="x", padx=5, pady=5)
        
        # 1行目：カテゴリ選択と削除ボタン（場所などと同じ CTk で統一）
        f_row1 = tk.Frame(slot_frame, bg=BOX_FG)
        f_row1.pack(fill="x", padx=BOX_PADX, pady=(BOX_PADY,2))
        
        lbl_cat = ctk.CTkLabel(f_row1, text="分類:", width=60, anchor="w", font=("Meiryo", 10))
        lbl_cat.pack(side="left", padx=5)
        cat_list = getattr(self, 'filtered_category_list', self.category_list)
        
        cmb_cat = ctk.CTkComboBox(f_row1, values=["(なし)"] + cat_list, width=180, command=lambda v, sf=slot_frame: self.on_slot_category_changed(sf))
        cmb_cat.pack(side="left", padx=5)
        cmb_cat.set("(なし)")
        
        btn_delete = ctk.CTkButton(f_row1, text="🗑️", width=40, fg_color="#c0392b", hover_color="#e74c3c", command=lambda: self.delete_category_slot(slot_frame))
        btn_delete.pack(side="right", padx=5)
        
        # 2行目：アイテム選択と数量
        f_row2 = tk.Frame(slot_frame, bg=BOX_FG)
        f_row2.pack(fill="x", padx=BOX_PADX, pady=(2,BOX_PADY))
        
        lbl_item = ctk.CTkLabel(f_row2, text="アイテム:", width=60, anchor="w", font=("Meiryo", 10))
        lbl_item.pack(side="left", padx=5)
        cmb_item = ctk.CTkComboBox(f_row2, values=["(なし)"], width=220, command=lambda v, sf=slot_frame: self.on_slot_item_changed(sf))
        cmb_item.pack(side="left", padx=5)
        cmb_item.set("(なし)")
        
        lbl_qty = ctk.CTkLabel(f_row2, text="数量:", width=50, anchor="w", font=("Meiryo", 10))
        lbl_qty.pack(side="left", padx=5)
        ent_qty = ctk.CTkEntry(f_row2, width=70, height=28)
        ent_qty.pack(side="left", padx=5)
        ent_qty.insert(0, "1")
        
        # 3行目：分類(EN)・アイテム(EN)（任意・空ならマスタの値）— オブジェクト(EN)と同じ仕様
        f_row_cat_en = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_cat_en.pack(fill="x", padx=BOX_PADX, pady=(2,2))
        lbl_cat_en = ctk.CTkLabel(f_row_cat_en, text="分類(EN):", width=80, anchor="w", font=("Meiryo", 10))
        lbl_cat_en.pack(side="left", padx=5)
        ent_slot_cat_en = ctk.CTkEntry(f_row_cat_en, height=28, placeholder_text="空ならマスタの値を使用")
        ent_slot_cat_en.pack(side="left", fill="x", expand=True)
        f_row_item_en = tk.Frame(slot_frame, bg=BOX_FG)
        f_row_item_en.pack(fill="x", padx=BOX_PADX, pady=(2,BOX_PADY))
        lbl_item_en = ctk.CTkLabel(f_row_item_en, text="アイテム(EN):", width=80, anchor="w", font=("Meiryo", 10))
        lbl_item_en.pack(side="left", padx=5)
        ent_slot_item_en = ctk.CTkEntry(f_row_item_en, height=28, placeholder_text="空ならマスタの値を使用")
        ent_slot_item_en.pack(side="left", fill="x", expand=True)
        
        # 属性設定フレーム（動的に生成、packしない - 属性がある場合のみ表示）
        attr_frame = tk.Frame(slot_frame, bg=BOX_FG)
        
        slot_data = {
            "frame": slot_frame,
            "row_frame": f_row1,
            "row_frame2": f_row2,
            "row_frame_item_en": f_row_item_en,
            "lbl_cat": lbl_cat,
            "category": cmb_cat,
            "lbl_cat_en": lbl_cat_en,
            "ent_slot_cat_en": ent_slot_cat_en,
            "lbl_item": lbl_item,
            "item": cmb_item,
            "lbl_qty": lbl_qty,
            "qty": ent_qty,
            "lbl_item_en": lbl_item_en,
            "ent_slot_item_en": ent_slot_item_en,
            "btn_delete": btn_delete,
            "attr_frame": attr_frame,
            "attr_widgets": {}
        }
        self.category_slots.append(slot_data)
        return slot_data

    def delete_category_slot(self, slot_frame):
        for i, slot in enumerate(self.category_slots):
            if slot["frame"] == slot_frame:
                slot["frame"].destroy()
                del self.category_slots[i]
                break

    def on_slot_category_changed(self, slot_frame):
        """スロットのカテゴリ変更時: 属性エリアをクリア。input_type（qty_only/item_select）・show_qty に応じてアイテム選択・数量の表示を切り替え、アイテム一覧をセット。"""
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
        
        if category == "(なし)" or not category:
            slot["item"].configure(values=["(なし)"])
            slot["item"].set("(なし)")
            # アイテム行を表示
            slot["row_frame2"].pack(fill="x", padx=BOX_PADX, pady=(2,BOX_PADY))
            slot["lbl_item"].pack(side="left", padx=5)
            slot["item"].pack(side="left", padx=5)
            if slot.get("row_frame_item_en"):
                slot["row_frame_item_en"].pack(fill="x", padx=BOX_PADX, pady=(2,BOX_PADY))
            return
        
        # カテゴリの設定を取得
        input_type = "item_select"  # デフォルト
        show_qty = True  # デフォルト
        if category in self.category_master:
            cat_info = self.category_master[category]
            if isinstance(cat_info, dict):
                input_type = cat_info.get("input_type", "item_select")
                show_qty = cat_info.get("show_qty", True)
        
        # input_typeに応じてUIを切り替え
        if input_type == "qty_only":
            slot["lbl_item"].pack_forget()
            slot["item"].pack_forget()
            slot["item"].set("(なし)")
            slot["item"].configure(values=["(なし)"])
            if slot.get("row_frame_item_en"):
                slot["row_frame_item_en"].pack_forget()
        else:
            slot["lbl_item"].pack(side="left", padx=5)
            slot["item"].pack(side="left", padx=5)
            if slot.get("row_frame_item_en"):
                slot["row_frame_item_en"].pack(fill="x", padx=BOX_PADX, pady=(2,BOX_PADY))
            if category in self.item_master:
                items = self.item_master[category]
                item_names = ["(なし)"] + [info["name_jp"] for info in items.values()]
                slot["item"].configure(values=item_names)
                slot["item"].set("(なし)")
            else:
                slot["item"].configure(values=["(なし)"])
                slot["item"].set("(なし)")
        
        # show_qtyに応じて数量入力の表示/非表示を切り替え
        if show_qty:
            slot["lbl_qty"].pack(side="left", padx=5)
            slot["qty"].pack(side="left", padx=5)
        else:
            slot["lbl_qty"].pack_forget()
            slot["qty"].pack_forget()
            slot["qty"].delete(0, "end")
            slot["qty"].insert(0, "1")
        # 分類(EN)は選択中のJPに応じてマスタの値で常に更新する
        if slot.get("ent_slot_cat_en"):
            slot["ent_slot_cat_en"].delete(0, "end")
            if category and category != "(なし)":
                cat_info = self.category_master.get(category)
                if isinstance(cat_info, dict):
                    cat_en = cat_info.get("name_en", "") or cat_info.get("name_jp", "")
                    if cat_en:
                        slot["ent_slot_cat_en"].insert(0, cat_en)
        
        # カテゴリレベルで属性がある場合（例: LEMのランク）はここでウィジェット生成
        if input_type == "item_select" and category and category != "(なし)":
            cat_info = self.category_master.get(category)
            if isinstance(cat_info, dict) and cat_info.get("attributes"):
                attrs = cat_info["attributes"]
                if attrs:
                    slot["attr_frame"].pack(fill="x", padx=BOX_PADX, pady=(0,BOX_PADY))
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
                            slot["attr_widgets"][attr_key] = {"type": "number", "widget": ent}
                        else:
                            options = attr_data.get("options", []) if isinstance(attr_data, dict) else attr_data
                            cmb = ctk.CTkComboBox(attr_item_frame, values=["(なし)"] + options, width=120)
                            cmb.set("(なし)")
                            cmb.pack(side="left", padx=2)
                            slot["attr_widgets"][attr_key] = {"type": "select", "widget": cmb}

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
            # カテゴリ属性は on_slot_category_changed で設定済み。item_en の更新のみ
            if slot.get("ent_slot_item_en"):
                slot["ent_slot_item_en"].delete(0, "end")
                if category and item_name and item_name != "(なし)" and category in self.item_master:
                    for iid, info in self.item_master[category].items():
                        if isinstance(info, dict) and info.get("name_jp") == item_name:
                            item_en = info.get("name_en", "") or info.get("name_jp", "")
                            if item_en:
                                slot["ent_slot_item_en"].insert(0, item_en)
                            break
            self._update_display_name_from_master()
            return
        
        # 属性フレームをクリア（カテゴリ属性はないのでアイテム属性用）
        slot["attr_frame"].pack_forget()
        for w in slot["attr_frame"].winfo_children(): w.destroy()
        slot["attr_widgets"] = {}
        
        if category == "(なし)" or item_name == "(なし)" or not category or not item_name:
            return
        if category not in self.item_master:
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
                slot["attr_frame"].pack(fill="x", padx=BOX_PADX, pady=(0,BOX_PADY))
                
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
                        slot["attr_widgets"][attr_key] = {"type": "number", "widget": ent}
                    else:  # select
                        options = attr_data.get("options", []) if isinstance(attr_data, dict) else attr_data
                        cmb = ctk.CTkComboBox(attr_item_frame, values=["(なし)"] + options, width=120)
                        cmb.set("(なし)")
                        cmb.pack(side="left", padx=2)
                        slot["attr_widgets"][attr_key] = {"type": "select", "widget": cmb}
        # アイテム(EN)は選択中のJPに応じてマスタの値で常に更新する
        if slot.get("ent_slot_item_en"):
            slot["ent_slot_item_en"].delete(0, "end")
            if category and category != "(なし)" and item_name and item_name != "(なし)" and category in self.item_master:
                for iid, info in self.item_master[category].items():
                    if isinstance(info, dict) and info.get("name_jp") == item_name:
                        item_en = info.get("name_en", "") or info.get("name_jp", "")
                        if item_en:
                            slot["ent_slot_item_en"].insert(0, item_en)
                        break
        self._update_display_name_from_master()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        # サイドバーはやや細くして、マップエリアを広く確保
        self.sidebar = ctk.CTkFrame(self, width=420, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        f_top = ctk.CTkFrame(self.sidebar, fg_color="#34495e", corner_radius=0)
        f_top.pack(fill="x")
        self.lbl_coords = ctk.CTkLabel(f_top, text="座標: ---", font=("Meiryo", 16, "bold"))
        self.lbl_coords.pack(pady=15)
        
        self.scroll_body = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_body.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 属性マッピング（JP/EN対応）
        self.attr_mapping = self.config.get("attr_mapping", {})
        # 後方互換性
        if not self.attr_mapping:
            old_cat_mapping = self.config.get("cat_mapping", {})
            if old_cat_mapping:
                self.attr_mapping = {k: {"name_jp": v, "name_en": ""} for k, v in old_cat_mapping.items()}
        
        self.cat_mapping = {k: v["name_jp"] if isinstance(v, dict) else v for k, v in self.attr_mapping.items()}
        
        # カテゴリマスタ（JP/EN + 属性項目）
        self.category_master = self.config.get("category_master", {})
        if not self.category_master:
            old_list = self.config.get("category_list", [])
            if old_list:
                self.category_master = {cat: {"name_jp": cat, "name_en": "", "attributes": {}} for cat in old_list if cat}
        self.category_list = list(self.category_master.keys())
        
        self.item_master = self.config.get("item_master", {})
        self.display_names = list(self.cat_mapping.values())
        self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
        self.show_incomplete_only = tk.BooleanVar(value=False)
        # フィルタを開閉可能に（▼/▶）。初期は閉じる
        self.f_filter_wrapper = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        self.f_filter_wrapper.pack(fill="x", padx=10, pady=5)
        self.f_filter_header = ctk.CTkFrame(self.f_filter_wrapper, fg_color="#1a1f26", corner_radius=6, border_width=1, border_color="#2a3038")
        self.f_filter_header.pack(fill="x")
        self.filter_expanded = False
        self.lbl_filter_toggle = ctk.CTkLabel(
            self.f_filter_header, text="▶ ピン表示フィルタ", font=("Meiryo", 11, "bold"),
            cursor="hand2", text_color="#eee"
        )
        self.lbl_filter_toggle.pack(side="left", padx=15, pady=8)
        self.lbl_filter_toggle.bind("<Button-1>", lambda e: self._toggle_filter())
        self.f_filter_header.bind("<Button-1>", lambda e: self._toggle_filter())
        self.f_filter = ctk.CTkFrame(self.f_filter_wrapper, fg_color="#1a1f26", corner_radius=6, border_width=1, border_color="#2a3038")
        # 初期は閉じているので pack しない
        ctk.CTkCheckBox(self.f_filter, text="⚠️ 未完成のみ", variable=self.show_incomplete_only, command=self.refresh_map, text_color="#e74c3c").pack(anchor="w", padx=15, pady=8)
        for n in self.display_names:
            ctk.CTkCheckBox(self.f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)

        # 新しいUI構造：オブジェクト（見た目）→オブジェクト属性→中身スロット（カテゴリ・アイテム）→重要度→メモ
        # 入力ボックス — 共通スタイル（塗り・角丸・控えめな縁）
        ctk.CTkLabel(self.scroll_body, text="▼ オブジェクト（見た目・外形）", font=("Meiryo", 12, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        self.f_attr = ctk.CTkFrame(self.scroll_body, fg_color=BOX_FG, corner_radius=BOX_CORNER, border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR)
        self.f_attr.pack(fill="x", padx=20, pady=5)
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
        
        # オブジェクト属性フレーム（遺体の場所など）- 初期は非表示
        self.obj_attr_frame = ctk.CTkFrame(self.scroll_body, fg_color=BOX_FG, corner_radius=BOX_CORNER, border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR)
        # packしない - 属性がある場合のみshow_object_attributesで表示
        self.obj_attr_widgets = {}

        # カテゴリスロット（複数選択可能）
        self.f_cat_header = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        self.f_cat_header.pack(fill="x", padx=20, pady=(10,0))
        ctk.CTkLabel(self.f_cat_header, text="▼ 中身の分類（カテゴリ）", font=("Meiryo", 12, "bold")).pack(side="left")
        # ボタンは左側ラベルと重ならないよう右側にまとめ、幅を十分に取る
        f_cat_btns = ctk.CTkFrame(self.f_cat_header, fg_color="transparent")
        f_cat_btns.pack(side="right")
        self.btn_add_category = ctk.CTkButton(f_cat_btns, text="＋ 追加", command=self.add_category_slot, width=100, fg_color="#3498db", height=28)
        self.btn_add_category.pack(side="left", padx=2)
        ctk.CTkButton(f_cat_btns, text="📋 定型から作成", command=self.open_template_dialog, width=130, fg_color="#8e44ad", height=28).pack(side="left", padx=2)
        
        self.category_slots_frame = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        self.category_slots_frame.pack(fill="x", padx=20, pady=5)
        self.category_slots = []
        self.filtered_category_list = self.category_list[:]  # フィルタリングされたカテゴリリスト

        # 重要度選択
        f_importance = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        f_importance.pack(fill="x", padx=20, pady=(10,0))
        ctk.CTkLabel(f_importance, text="▼ 重要度", font=("Meiryo", 12, "bold")).pack(side="left")
        self.cmb_importance = ctk.CTkComboBox(f_importance, values=["(なし)", "1", "2", "3", "4", "5"], width=100)
        self.cmb_importance.pack(side="left", padx=10)
        self.cmb_importance.set("(なし)")

        # 表示名の例外入力 — 同じボックススタイル
        ctk.CTkLabel(self.scroll_body, text="▼ 表示名の例外入力", font=("Meiryo", 12, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        self.f_display_name_slot = ctk.CTkFrame(self.scroll_body, fg_color=BOX_FG, corner_radius=BOX_CORNER, border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR)
        self.f_display_name_slot.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self.f_display_name_slot, text="このピンだけ別名にするときだけ入力。",
                     font=("Meiryo", 9), text_color="#bdc3c7").pack(anchor="w", padx=BOX_PADX, pady=(BOX_PADY,0))
        ctk.CTkLabel(self.f_display_name_slot, text="通常は空でOK。",
                     font=("Meiryo", 9), text_color="#bdc3c7").pack(anchor="w", padx=BOX_PADX, pady=(0,4))
        f_row_jp = ctk.CTkFrame(self.f_display_name_slot, fg_color="transparent")
        f_row_jp.pack(fill="x", padx=BOX_PADX, pady=2)
        ctk.CTkLabel(f_row_jp, text="JP:", width=32, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(0,5))
        self.ent_name_jp = ctk.CTkEntry(f_row_jp, height=28, placeholder_text="空ならマスタの値を使用")
        self.ent_name_jp.pack(side="left", fill="x", expand=True)
        f_row_en = ctk.CTkFrame(self.f_display_name_slot, fg_color="transparent")
        f_row_en.pack(fill="x", padx=BOX_PADX, pady=(2,BOX_PADY))
        ctk.CTkLabel(f_row_en, text="EN:", width=32, anchor="w", font=("Meiryo", 10)).pack(side="left", padx=(0,5))
        self.ent_name_en = ctk.CTkEntry(f_row_en, height=28, placeholder_text="空ならマスタの値を使用")
        self.ent_name_en.pack(side="left", fill="x", expand=True)

        self.txt_memo_jp = self.create_textbox("▼ 詳細メモ（日本語）")
        self.txt_memo_en = self.create_textbox("▼ Memo (English)")

        f_foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_foot.pack(fill="x", side=tk.BOTTOM, padx=20, pady=20)
        self.setup_menu_bar()
        # エリア編集ボタン群（アコーディオン、初期は閉）
        self.area_panel_expanded = False
        f_area = ctk.CTkFrame(f_foot, fg_color=BOX_FG, corner_radius=BOX_CORNER, border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR)
        f_area.pack(fill="x", pady=(0, 10))
        header_row = ctk.CTkFrame(f_area, fg_color="transparent")
        header_row.pack(fill="x", padx=BOX_PADX, pady=(BOX_PADY, 5))
        self.lbl_area_toggle = ctk.CTkLabel(header_row, text="▶ エリア編集", font=("Meiryo", 11, "bold"), cursor="hand2")
        self.lbl_area_toggle.pack(side="left")
        self.lbl_area_toggle.bind("<Button-1>", lambda e: self.toggle_area_panel())
        header_row.bind("<Button-1>", lambda e: self.toggle_area_panel())
        self.btn_area_edit_toggle = ctk.CTkButton(
            header_row,
            text="編集: ON",
            command=self.toggle_area_edit_enabled,
            width=80,
            height=26,
            fg_color="#2ecc71"
        )
        self.btn_area_edit_toggle.pack(side="right")
        self.f_area_body = ctk.CTkFrame(f_area, fg_color="transparent")
        f_area_btns = ctk.CTkFrame(self.f_area_body, fg_color="transparent")
        f_area_btns.pack(fill="x", padx=BOX_PADX, pady=(0, 4))
        self.btn_area_poly = ctk.CTkButton(f_area_btns, text="多角形エリア作成", command=lambda: self.set_area_mode("create_polygon"), fg_color="#1abc9c", height=28)
        self.btn_area_poly.pack(fill="x", pady=1)
        self.btn_area_circle = ctk.CTkButton(f_area_btns, text="円エリア作成", command=lambda: self.set_area_mode("create_circle"), fg_color="#2980b9", height=28)
        self.btn_area_circle.pack(fill="x", pady=1)
        self.btn_area_rect = ctk.CTkButton(f_area_btns, text="四角エリア作成", command=lambda: self.set_area_mode("create_rect"), fg_color="#8e44ad", height=28)
        self.btn_area_rect.pack(fill="x", pady=1)
        f_area_actions = ctk.CTkFrame(self.f_area_body, fg_color="transparent")
        f_area_actions.pack(fill="x", padx=BOX_PADX, pady=(0, 4))
        self.btn_area_point_toggle = ctk.CTkButton(
            f_area_actions, text="制御点: ON", command=self.toggle_area_points, fg_color="#34495e", height=30
        )
        self.btn_area_point_toggle.pack(fill="x", pady=1)
        self.btn_area_close_poly = ctk.CTkButton(
            f_area_actions, text="多角形を確定", command=self.finalize_polygon_area, fg_color="#16a085", height=30
        )
        self.btn_area_close_poly.pack(fill="x", pady=1)
        self.btn_area_edit_points = ctk.CTkButton(
            f_area_actions, text="制御点編集", command=self.start_edit_polygon_mode, fg_color="#2c3e50", height=30
        )
        self.btn_area_edit_points.pack(fill="x", pady=1)
        f_area_rotate = ctk.CTkFrame(self.f_area_body, fg_color="transparent")
        f_area_rotate.pack(fill="x", padx=BOX_PADX, pady=(0, 4))
        self.btn_area_rot_ccw = ctk.CTkButton(
            f_area_rotate, text="↺10°", command=lambda: self.rotate_current_area(-10), fg_color="#7f8c8d", height=30
        )
        self.btn_area_rot_ccw.pack(side="left", padx=2)
        self.btn_area_rot_cw = ctk.CTkButton(
            f_area_rotate, text="↻10°", command=lambda: self.rotate_current_area(10), fg_color="#7f8c8d", height=30
        )
        self.btn_area_rot_cw.pack(side="left", padx=2)
        f_area_save = ctk.CTkFrame(self.f_area_body, fg_color="transparent")
        f_area_save.pack(fill="x", padx=BOX_PADX, pady=(0, BOX_PADY))
        self.btn_area_save = ctk.CTkButton(f_area_save, text="💾 エリア保存", command=self.save_current_area, fg_color="#27ae60", height=30)
        self.btn_area_save.pack(fill="x", pady=1)
        self.btn_area_delete = ctk.CTkButton(f_area_save, text="🗑️ エリア削除", command=self.delete_current_area, fg_color="#c0392b", height=30)
        self.btn_area_delete.pack(fill="x", pady=1)

        self.btn_delete = ctk.CTkButton(f_foot, text="🗑️ ピン削除", command=self.delete_data, fg_color="#c0392b", hover_color="#e74c3c", height=35)
        self.btn_delete.pack(fill="x", side=tk.BOTTOM, pady=(15, 0))
        ctk.CTkButton(f_foot, text="ピン保存 (Ctrl+Enter)", command=self.save_data, fg_color="#2980b9", height=50, font=("Meiryo", 14, "bold")).pack(fill="x", pady=5)
        self.btn_edit_pos = ctk.CTkButton(f_foot, text="📍 位置修正", command=self.start_edit_pos_mode, fg_color="#d35400", height=35)
        self.btn_edit_pos.pack(fill="x", pady=(5, 10))
        ctk.CTkButton(f_foot, text="📋 定型に保存", command=self.save_as_template_dialog, fg_color="#8e44ad", height=30).pack(fill="x", pady=(2, 5))
        ctk.CTkButton(f_foot, text="📤 ブログ用エクスポート", command=self.export_for_blog, fg_color="#16a085", height=30).pack(fill="x", pady=(2, 5))
        ctk.CTkButton(f_foot, text="⚙ マスタ管理", command=self.open_settings, fg_color="#7f8c8d", height=30).pack(fill="x", pady=(5, 10))

        f_crop = ctk.CTkFrame(f_foot, fg_color=BOX_FG, corner_radius=BOX_CORNER, border_width=BOX_BORDER_WIDTH, border_color=BOX_BORDER_COLOR)
        f_crop.pack(fill="x", pady=10)
        self.btn_crop_mode = ctk.CTkButton(f_crop, text="✂ クロップ開始", command=self.toggle_crop_mode, fg_color="#e67e22", width=140); self.btn_crop_mode.pack(side=tk.LEFT, padx=10, pady=10)
        self.btn_crop_exec = ctk.CTkButton(f_crop, text="保存実行", command=self.execute_crop, state="disabled", fg_color="#27ae60", width=100); self.btn_crop_exec.pack(side=tk.LEFT, pady=10)
        f_ann = ctk.CTkFrame(f_foot, fg_color="transparent"); f_ann.pack(fill="x")
        self.btn_here = ctk.CTkButton(f_ann, text="Here!", command=lambda: self.set_tool("here"), state="disabled", width=100, fg_color="#3b8ed0"); self.btn_here.pack(side=tk.LEFT, padx=2)
        self.btn_arrow = ctk.CTkButton(f_ann, text="矢印", command=lambda: self.set_tool("arrow"), state="disabled", width=100, fg_color="#3b8ed0"); self.btn_arrow.pack(side=tk.LEFT, padx=2)

        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        self.canvas.bind("<Button-2>", self.toggle_autoscroll)
        self.bind("<Control-Return>", lambda e: self.save_data())
        self.bind("<Delete>", lambda e: self.delete_data())
        self.canvas.bind("<Configure>", lambda e: self.refresh_map())

    def create_input(self, label):
        ctk.CTkLabel(self.scroll_body, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        ent = ctk.CTkEntry(self.scroll_body, height=35); ent.pack(fill="x", padx=20, pady=5)
        return ent
    def create_textbox(self, label):
        ctk.CTkLabel(self.scroll_body, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        txt = ctk.CTkTextbox(self.scroll_body, height=100); txt.pack(fill="x", padx=20, pady=5)
        return txt
    def open_settings(self): SettingsWindow(self, self.config_path, self.config)

    def export_for_blog(self):
        """ブログ用にピンデータを ID→表示名 解決して JSON にエクスポート"""
        try:
            out_path, count = export_pins_to_json(self.game_path)
            if out_path and count > 0:
                messagebox.showinfo("ブログ用エクスポート", f"pins_export.json に {count} 件のピンを保存しました。\n\n{out_path}")
            elif count == 0:
                messagebox.showinfo("ブログ用エクスポート", "ピンデータがありません。")
            else:
                messagebox.showerror("ブログ用エクスポート", "エクスポートに失敗しました。")
        except Exception as e:
            messagebox.showerror("ブログ用エクスポート", str(e))
    def get_ratio(self): return ((2 ** self.zoom) * 256) / self.orig_max_dim
    def start_edit_pos_mode(self):
        if not self.current_uid: messagebox.showwarning("注意", "ピンを選択"); return
        self.edit_pos_mode_uid = self.current_uid; messagebox.showinfo("モード", "クリックで位置更新"); self.refresh_map()
    
    def refresh_map(self):
        self.canvas.delete("all")
        r = self.get_ratio(); cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1: return
        z_src = min(int(math.floor(self.zoom)), self.max_zoom)
        ts = int(256 * (2 ** (self.zoom - z_src)))
        vl, vt = self.canvas.canvasx(0), self.canvas.canvasy(0)
        for tx in range(int(vl//ts), int((vl+cw)//ts)+1):
            for ty in range(int(vt//ts), int((vt+ch)//ts)+1):
                path = os.path.join(self.tile_dir, str(z_src), str(tx), f"{ty}.webp")
                if os.path.exists(path):
                    k = f"{path}_{ts}"
                    if k not in self.tile_cache: self.tile_cache[k] = ImageTk.PhotoImage(Image.open(path).resize((ts, ts), Image.Resampling.NEAREST))
                    self.canvas.create_image(tx*ts, ty*ts, anchor="nw", image=self.tile_cache[k])
        # エリアをタイルの上・ピンの下に描画
        self._draw_areas(r)
        for d in self.data_list:
            # 後方互換性：attributeまたはcategory_pinから属性を取得
            attr_key = d.get('attribute') or d.get('category_pin', 'MISC_OTHER')
            cn = self.cat_mapping.get(attr_key, "")
            if cn in self.filter_vars and not self.filter_vars[cn].get(): continue
            # 未完成チェック：name_jpとcategoriesの両方が存在するか
            has_name = bool(d.get('name_jp'))
            has_categories = bool(d.get('categories'))
            if self.show_incomplete_only.get() and has_name and has_categories: continue
            px, py = d['x']*r, d['y']*r
            col = "#f1c40f" if (d['uid']==self.current_uid) else "#e67e22"
            if self.edit_pos_mode_uid == d['uid']: self.canvas.create_oval(px-15, py-15, px+15, py+15, outline="yellow", width=2, dash=(4,2))
            else: self.canvas.create_oval(px-6, py-6, px+6, py+6, fill=col, outline="white", width=2)
        if self.temp_coords and not self.current_uid:
            tx, ty = self.temp_coords[0]*r, self.temp_coords[1]*r
            self.canvas.create_oval(tx-8, ty-8, tx+8, ty+8, outline="cyan", width=2)
        if self.is_crop_mode:
            bx, by, bw, bh = self.crop_box["x"]*r, self.crop_box["y"]*r, self.crop_box["w"]*r, self.crop_box["h"]*r
            self.canvas.create_rectangle(bx, by, bx+bw, by+bh, outline="#2ecc71", width=3, dash=(10,5))
            if self.here_pos: 
                hx, hy = self.here_pos["x"]*r, self.here_pos["y"]*r
                self.canvas.create_oval(hx-20, hy-20, hx+20, hy+20, outline="white", width=4); self.canvas.create_oval(hx-20, hy-20, hx+20, hy+20, outline="#e74c3c", width=3)
        self.canvas.config(scrollregion=(0, 0, self.orig_w*r, self.orig_h*r))

    def on_zoom(self, event):
        view_left = self.canvas.canvasx(0); view_top = self.canvas.canvasy(0)
        mouse_canvas_x = view_left + event.x; mouse_canvas_y = view_top + event.y
        r_old = self.get_ratio(); total_w_old = self.orig_w * r_old
        if total_w_old == 0: return
        rx = mouse_canvas_x / total_w_old; ry = mouse_canvas_y / (self.orig_h * r_old)
        d = 0.2 if event.delta > 0 else -0.2
        self.zoom = max(0, min(self.max_zoom + 2.5, self.zoom + d))
        self.refresh_map()
        r_new = self.get_ratio()
        self.canvas.xview_moveto((self.orig_w * r_new * rx - event.x) / (self.orig_w * r_new))
        self.canvas.yview_moveto((self.orig_h * r_new * ry - event.y) / (self.orig_h * r_new))

    def on_left_down(self, event):
        r = self.get_ratio(); mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y); cx, cy = mx/r, my/r
        if not self.area_edit_enabled.get():
            # エリア編集無効時は従来のマップ操作のみ
            if self.is_crop_mode and not self.active_tool:
                b = self.crop_box; bx, by, bw, bh = b["x"]*r, b["y"]*r, b["w"]*r, b["h"]*r
                if (bx+bw-20 <= mx <= bx+bw+5) and (by+bh-20 <= my <= by+bh+5): self.drag_mode = "resize_br"; return
                elif (b["x"] <= cx <= b["x"]+b["w"]) and (b["y"] <= cy <= b["y"]+b["h"]): self.drag_mode = "move"; self.drag_offset = (cx - b["x"], cy - b["y"]); return
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
        if abs(event.x - self.drag_start[0]) > 5: self.has_dragged = True; self.canvas.scan_dragto(event.x, event.y, gain=1); self.refresh_map()

    def on_left_up(self, event):
        if self.drag_mode:
            self.drag_mode = None
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
        if not self.has_dragged:
            r = self.get_ratio(); cx, cy = self.canvas.canvasx(event.x)/r, self.canvas.canvasy(event.y)/r
            if self.is_crop_mode and self.active_tool:
                if self.active_tool == "here": self.here_pos = {"x": cx, "y": cy}
                elif self.active_tool == "arrow": self.arrow_pos = {"x": cx, "y": cy}
                self.refresh_map(); return
            # エリア作成モード（多角形 / 円 / 四角）
            if self.area_mode in ("create_polygon", "create_circle", "create_rect"):
                self.handle_area_creation_click(cx, cy)
                return
            if self.edit_pos_mode_uid:
                for d in self.data_list:
                    if d['uid'] == self.edit_pos_mode_uid: d['x'], d['y'] = cx, cy; self.mark_dirty(); break
                self.edit_pos_mode_uid = None; self.refresh_map(); return
            # まずピン当たり判定（ピン優先）
            for d in self.data_list:
                if abs(d['x']-cx)<(16/r) and abs(d['y']-cy)<(16/r):
                    self.current_uid = d['uid']
                    self.current_area_uid = None
                    self.load_to_ui(d)
                    self.refresh_map()
                    return
            # ピンがなければエリア当たり判定
            hit_area = self.hit_test_area(cx, cy)
            if hit_area is not None:
                self.current_area_uid = hit_area.get("uid")
                self.current_uid = None
                self.load_area_to_ui(hit_area)
                self.refresh_map()
                return
            # どちらもヒットしない場合は新規ピン座標として記録
            self.current_uid = None
            self.current_area_uid = None
            self.temp_coords = (cx, cy)
            self.lbl_coords.configure(text=f"座標: ({int(cx)}, {int(cy)})")
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
            if abs(dx)>20 or abs(dy)>20: self.canvas.xview_scroll(int(dx/35), "units"); self.canvas.yview_scroll(int(dy/35), "units"); self.refresh_map()
        self.after(10, self.run_autoscroll_loop)
    def setup_menu_bar(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="保存", command=self.save_all_changes, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_close)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        # self.config は設定用dictと名称が衝突しているので configure を使う
        self.configure(menu=menubar)
        self.bind("<Control-s>", lambda e: self.save_all_changes())

    def toggle_area_panel(self):
        self.area_panel_expanded = not self.area_panel_expanded
        if self.area_panel_expanded:
            self.f_area_body.pack(fill="x")
            self.lbl_area_toggle.configure(text="▼ エリア編集")
        else:
            self.f_area_body.pack_forget()
            self.lbl_area_toggle.configure(text="▶ エリア編集")

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
        """エリアの色を attribute の type などから決定"""
        attr_id = area.get("attribute") or ""
        obj_type = "other"
        if attr_id and attr_id in self.attr_mapping:
            info = self.attr_mapping[attr_id]
            if isinstance(info, dict):
                obj_type = info.get("type", "other")
        color_map = {
            "loot": "#2ecc71",
            "landmark": "#3498db",
            "colony": "#e67e22",
            "other": "#7f8c8d"
        }
        base = color_map.get(obj_type, "#7f8c8d")
        # 半透明風に見えるよう淡い塗りを使う
        return base

    def _draw_areas(self, r):
        for area in self.area_list:
            shape = area.get("shape", "polygon")
            fill = self._get_area_fill_color(area)
            outline = "#ffffff"
            is_selected = area.get("uid") == self.current_area_uid
            width = 3 if is_selected else 1
            stipple = "gray25" if is_selected else "gray50"
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
                self.canvas.create_polygon(*flat, outline=outline, width=width, fill=fill, stipple=stipple)
            elif shape == "rect":
                x = float(area.get("x", 0))*r
                y = float(area.get("y", 0))*r
                w = float(area.get("width", 0))*r
                h = float(area.get("height", 0))*r
                if w <= 0 or h <= 0:
                    continue
                self.canvas.create_rectangle(x, y, x+w, y+h,
                                             outline=outline, width=width, fill=fill, stipple=stipple)
            else:
                pts = area.get("points") or []
                if len(pts) < 3:
                    continue
                flat = []
                for (ax, ay) in pts:
                    flat.extend([ax*r, ay*r])
                self.canvas.create_polygon(*flat, outline=outline, width=width, fill=fill, stipple=stipple)
                # 制御点の可視化（編集モード時）
                if self.area_show_points.get() and self.area_mode == "edit_polygon" and is_selected:
                    for idx, (ax, ay) in enumerate(pts):
                        px, py = ax*r, ay*r
                        c = "#ff4757" if idx == 0 else "#ffffff"
                        self.canvas.create_oval(px-7, py-7, px+7, py+7, fill=c, outline="#000000")
        # 作成中ポリゴンのプレビュー（始点強調＋閉路ガイド）
        if self.area_mode == "create_polygon" and self.area_temp_points:
            pts = self.area_temp_points
            if len(pts) >= 2:
                flat = []
                for (ax, ay) in pts:
                    flat.extend([ax*r, ay*r])
                self.canvas.create_line(*flat, fill="#00d2d3", width=2)
                sx, sy = pts[0][0]*r, pts[0][1]*r
                ex, ey = pts[-1][0]*r, pts[-1][1]*r
                self.canvas.create_line(ex, ey, sx, sy, fill="#00d2d3", width=1, dash=(4, 3))
            if self.area_show_points.get():
                for idx, (ax, ay) in enumerate(pts):
                    px, py = ax*r, ay*r
                    c = "#ff4757" if idx == 0 else "#ffffff"
                    self.canvas.create_oval(px-7, py-7, px+7, py+7, fill=c, outline="#000000")
        # 円/四角のドラッグ作成プレビュー
        if self.area_preview_shape:
            shp = self.area_preview_shape
            x0, y0, x1, y1 = shp["x0"]*r, shp["y0"]*r, shp["x1"]*r, shp["y1"]*r
            if shp["shape"] == "create_rect":
                self.canvas.create_rectangle(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1),
                                             outline="#00d2d3", width=2, dash=(6, 4))
            elif shp["shape"] == "create_circle":
                radius = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                self.canvas.create_oval(x0-radius, y0-radius, x0+radius, y0+radius,
                                        outline="#00d2d3", width=2, dash=(6, 4))

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
        self.btn_area_point_toggle.configure(text=txt)
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
        if not self.area_edit_enabled.get():
            self.set_area_mode("idle")
            self.btn_area_edit_toggle.configure(text="編集: OFF", fg_color="#7f8c8d")
        else:
            self.btn_area_edit_toggle.configure(text="編集: ON", fg_color="#2ecc71")
        self.refresh_map()

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
        self.clear_ui()
        # attribute
        attr_key = area.get("attribute") or ""
        attr_display = self.cat_mapping.get(attr_key, "")
        if attr_display:
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
        self.lbl_coords.configure(text=f"エリア: {area.get('uid')}")

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

    # --- 保存・読込 ---
    def save_data(self):
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
        if obj_type != "landmark" and not self.category_slots:
            messagebox.showwarning("入力エラー", "少なくとも1つの中身（カテゴリ）を追加してください。")
            return

        if "attr_mapping" not in self.config:
            self.config["attr_mapping"] = {}
        if "category_master" not in self.config:
            self.config["category_master"] = {}
        if "item_master" not in self.config:
            self.config["item_master"] = {}
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
        categories_data = []
        for slot in self.category_slots:
            category = slot["category"].get()
            item_name = slot["item"].get()
            qty = (slot["qty"].get() or "").strip() or "1"
            
            if category == "(なし)":
                continue
            
            # カテゴリのinput_typeを取得
            input_type = "item_select"
            if category in self.category_master:
                cat_info = self.category_master[category]
                if isinstance(cat_info, dict):
                    input_type = cat_info.get("input_type", "item_select")
            slot_cat_en = (slot.get("ent_slot_cat_en") and slot["ent_slot_cat_en"].get() or "").strip()
            if not slot_cat_en and category in self.category_master and isinstance(self.category_master[category], dict):
                slot_cat_en = self.category_master[category].get("name_en", "") or self.category_master[category].get("name_jp", "")
            slot_item_en = (slot.get("ent_slot_item_en") and slot["ent_slot_item_en"].get() or "").strip()
            
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
                    "attributes": {}
                })
                continue
            
            # アイテム選択ありの場合
            if item_name == "(なし)":
                continue
            
            # アイテムIDを取得（マスタに追加済みの場合は必ず見つかる）
            item_id = None
            if category in self.item_master:
                for i_id, info in self.item_master[category].items():
                    if info["name_jp"] == item_name:
                        item_id = i_id
                        break
            
            if not item_id:
                continue
            
            # アイテム属性を収集
            item_attrs = {}
            for attr_key, widget_data in slot.get("attr_widgets", {}).items():
                if isinstance(widget_data, dict):
                    attr_type = widget_data.get("type", "select")
                    if attr_type == "fixed":
                        # 固定値はそのまま保存
                        item_attrs[attr_key] = widget_data.get("value", "")
                    else:
                        widget = widget_data.get("widget")
                        if widget:
                            val = widget.get()
                            if val and val != "(なし)":
                                item_attrs[attr_key] = val
                else:
                    # 後方互換性
                    val = widget_data.get() if hasattr(widget_data, 'get') else None
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
                "attributes": item_attrs
            })

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
        
        # landmarkの場合はカテゴリなしでOK
        if not categories_data and obj_type != "landmark":
            messagebox.showwarning("入力エラー", "有効なカテゴリとアイテムを選択してください。")
            return
        
        # 重要度
        importance = self.cmb_importance.get()
        if importance == "(なし)": importance = ""
        
        # メインカテゴリとアイテム名（表示名は入力欄で上書き可能）
        if categories_data:
            main_category = categories_data[0]["category"]
            name_jp = categories_data[0]["item_name_jp"]
            name_en = categories_data[0]["item_name_en"]
        else:
            main_category = ""
            obj_info = self.attr_mapping.get(attribute_id, {})
            name_jp = obj_info.get("name_jp", attribute) if isinstance(obj_info, dict) else attribute
            name_en = obj_info.get("name_en", "") if isinstance(obj_info, dict) else ""
        # 表示名入力欄が入力されていればそちらを優先
        override_jp = (self.ent_name_jp.get() or "").strip()
        override_en = (self.ent_name_en.get() or "").strip()
        if override_jp:
            name_jp = override_jp
        if override_en:
            name_en = override_en
        
        obj_name_en_override = (self.ent_obj_en.get() or "").strip()
        dr = {
            'uid': self.current_uid or f"p_{int(datetime.now().timestamp())}",
            'x': self.temp_coords[0] if not self.current_uid else None,
            'y': self.temp_coords[1] if not self.current_uid else None,
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
            'updated_at': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        dr['category_pin'] = attribute_id
        
        if self.current_uid:
            for d in self.data_list:
                if d['uid'] == self.current_uid: d.update({k:v for k,v in dr.items() if v is not None})
        else: self.data_list.append(dr)
        self.mark_dirty(); self.current_uid = self.temp_coords = None; self.refresh_map(); self.clear_ui()

    def delete_data(self):
        if not self.current_uid or not messagebox.askyesno("確認", "削除しますか？"): return
        self.data_list = [d for d in self.data_list if d['uid'] != self.current_uid]
        self.mark_dirty(); self.current_uid = None; self.clear_ui(); self.refresh_map()

    def write_files(self):
        p = os.path.join(self.game_path, self.config["save_file"])
        # 新しいフィールドと後方互換性のためのフィールドを含める
        flds = ["uid", "x", "y", "name_jp", "name_en", "attribute", "obj_name_en", "obj_attributes", "category", "categories", "importance", "category_pin", "contents", "memo_jp", "memo_en", "updated_at"]
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=flds, extrasaction='ignore')
            writer.writeheader(); writer.writerows(self.data_list)

    def load_csv(self):
        p = os.path.join(self.game_path, self.config["save_file"])
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
                    rows.append(d)
                self.data_list = rows

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

    def load_to_ui(self, d):
        self.clear_ui()
        
        # 属性を設定（後方互換性対応）
        attr_key = d.get('attribute') or d.get('category_pin') or d.get('category_main', 'MISC_OTHER')
        attr_display = self.cat_mapping.get(attr_key, "")
        if attr_display:
            self.cmb_attribute.set(attr_display)
            # オブジェクト変更時の処理を呼び出し
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
                    attrs = cat_data.get('attributes', {})
                    
                    if category:
                        # カテゴリリストにない場合は追加
                        if category not in self.category_list:
                            self.category_list.append(category)
                            # 全てのスロットのカテゴリリストを更新
                            for s in self.category_slots:
                                s["category"].configure(values=["(なし)"] + self.category_list)
                        
                        slot["category"].set(category)
                        self.on_slot_category_changed(slot["frame"])
                        
                        # 数量を設定
                        slot["qty"].delete(0, "end")
                        slot["qty"].insert(0, qty)
                        # 分類(EN)・アイテム(EN)を設定（保存値がなければマスタから）
                        if slot.get("ent_slot_cat_en"):
                            slot["ent_slot_cat_en"].delete(0, "end")
                            saved_cat_en = (cat_data.get("cat_name_en") or "").strip()
                            master_cat_en = ""
                            if category and isinstance(self.category_master.get(category), dict):
                                master_cat_en = self.category_master[category].get("name_en", "") or self.category_master[category].get("name_jp", "")
                            slot["ent_slot_cat_en"].insert(0, saved_cat_en or master_cat_en)
                        if slot.get("ent_slot_item_en"):
                            slot["ent_slot_item_en"].delete(0, "end")
                            slot["ent_slot_item_en"].insert(0, cat_data.get("item_name_en", "") or "")
                        
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
                # カテゴリリストにない場合は追加
                if category not in self.category_list:
                    self.category_list.append(category)
                    # 全てのスロットのカテゴリリストを更新
                    for s in self.category_slots:
                        s["category"].configure(values=["(なし)"] + self.category_list)
                
                slot["category"].set(category)
                self.on_slot_category_changed(slot["frame"])
                if category in self.item_master and item_id in self.item_master[category]:
                    item_name = self.item_master[category][item_id]["name_jp"]
                    slot["item"].set(item_name)
                    self.on_slot_item_changed(slot["frame"])
                    if slot.get("ent_slot_cat_en"):
                        slot["ent_slot_cat_en"].delete(0, "end")
                        slot["ent_slot_cat_en"].insert(0, self.category_master.get(category, {}).get("name_en", "") if isinstance(self.category_master.get(category), dict) else "")
                    if slot.get("ent_slot_item_en"):
                        slot["ent_slot_item_en"].delete(0, "end")
                        slot["ent_slot_item_en"].insert(0, self.item_master[category][item_id].get("name_en", "") or "")
            
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
                                # カテゴリリストにない場合は追加
                                if grp not in self.category_list:
                                    self.category_list.append(grp)
                                    # 全てのスロットのカテゴリリストを更新
                                    for s in self.category_slots:
                                        s["category"].configure(values=["(なし)"] + self.category_list)
                                
                                slot["category"].set(grp)
                                self.on_slot_category_changed(slot["frame"])
                                slot["item"].set(vals[old_item_id]["name_jp"])
                                self.on_slot_item_changed(slot["frame"])
                                slot["qty"].delete(0, "end")
                                slot["qty"].insert(0, qty)
                                
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
        categories_data = []
        for slot in self.category_slots:
            category = slot["category"].get()
            item_name = slot["item"].get()
            qty = (slot["qty"].get() or "").strip() or "1"
            if not category or category == "(なし)":
                continue
            input_type = "item_select"
            if category in self.category_master:
                ci = self.category_master[category]
                if isinstance(ci, dict):
                    input_type = ci.get("input_type", "item_select")
            slot_cat_en_tpl = (slot.get("ent_slot_cat_en") and slot["ent_slot_cat_en"].get() or "").strip()
            if not slot_cat_en_tpl and category in self.category_master and isinstance(self.category_master[category], dict):
                slot_cat_en_tpl = self.category_master[category].get("name_en", "") or self.category_master[category].get("name_jp", "")
            slot_item_en_tpl = (slot.get("ent_slot_item_en") and slot["ent_slot_item_en"].get() or "").strip()
            if input_type == "qty_only":
                qty_item_en_tpl = slot_item_en_tpl or ""
                if not qty_item_en_tpl and category in self.category_master and isinstance(self.category_master[category], dict):
                    qty_item_en_tpl = self.category_master[category].get("name_en", "") or self.category_master[category].get("name_jp", "")
                categories_data.append({
                    "cat_id": self._get_cat_id(category),
                    "category": category,
                    "cat_name_en": slot_cat_en_tpl or "",
                    "item_id": "",
                    "item_name_jp": "",
                    "item_name_en": qty_item_en_tpl or "",
                    "qty": qty,
                    "attributes": {}
                })
                continue
            if not item_name or item_name == "(なし)":
                continue
            item_id = None
            if category in self.item_master:
                for iid, info in self.item_master[category].items():
                    if info.get("name_jp") == item_name:
                        item_id = iid
                        break
            if not item_id:
                continue
            item_attrs = {}
            for attr_key, widget_data in slot.get("attr_widgets", {}).items():
                if isinstance(widget_data, dict):
                    if widget_data.get("type") == "fixed":
                        item_attrs[attr_key] = widget_data.get("value", "")
                    else:
                        w = widget_data.get("widget")
                        if w:
                            v = w.get()
                            if v and v != "(なし)":
                                item_attrs[attr_key] = v
            master_item_en_tpl = self.item_master[category][item_id].get("name_en", "")
            categories_data.append({
                "cat_id": self._get_cat_id(category),
                "category": category,
                "cat_name_en": slot_cat_en_tpl or "",
                "item_id": item_id,
                "item_name_jp": self.item_master[category][item_id].get("name_jp", ""),
                "item_name_en": slot_item_en_tpl or master_item_en_tpl,
                "qty": qty,
                "attributes": item_attrs
            })
        return {
            "attribute_id": attribute_id,
            "obj_attributes": obj_attributes,
            "categories": categories_data,
            "importance": self.cmb_importance.get() if self.cmb_importance.get() != "(なし)" else ""
        }

    def _apply_template(self, tpl):
        """定型をフォームに適用（座標・メモは触らない）"""
        attr_display = self.cat_mapping.get(tpl.get("attribute_id", ""), tpl.get("attribute_id", ""))
        if not attr_display:
            attr_display = tpl.get("attribute_id", "")
        d = {
            "attribute": attr_display,
            "obj_attributes": json.dumps(tpl.get("obj_attributes", {})),
            "categories": json.dumps(tpl.get("categories", [])),
            "importance": tpl.get("importance", ""),
            "memo_jp": "",
            "memo_en": ""
        }
        self.clear_ui()
        self.load_to_ui(d)

    def open_template_dialog(self):
        templates = self._load_templates()
        if not templates:
            messagebox.showinfo("定型から作成", "定型がありません。\n現在の内容を「定型に保存」で登録できます。")
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

    def save_as_template_dialog(self):
        tpl = self._get_current_as_template()
        if not tpl:
            messagebox.showwarning("定型に保存", "オブジェクトを選択してください。")
            return
        name = simpledialog.askstring("定型に保存", "定型の名前を入力してください:", initialvalue="")
        if not name or not name.strip():
            return
        name = name.strip()
        tpl_save = {**tpl, "name": name}
        templates = self._load_templates()
        templates.append(tpl_save)
        self._save_templates(templates)
        messagebox.showinfo("定型に保存", f"「{name}」を定型に登録しました。")

    def clear_ui(self):
        self.cmb_attribute.set("(なし)")
        self.cmb_importance.set("(なし)")
        self.ent_name_jp.delete(0, "end")
        self.ent_name_en.delete(0, "end")
        if getattr(self, "ent_obj_en", None):
            self.ent_obj_en.delete(0, "end")
        self.txt_memo_jp.delete("1.0", tk.END); self.txt_memo_en.delete("1.0", tk.END)
        # オブジェクト属性フレームを非表示にしてクリア
        self.obj_attr_frame.pack_forget()
        for w in self.obj_attr_frame.winfo_children():
            w.destroy()
        self.obj_attr_widgets = {}
        # カテゴリエリアを表示状態にリセット
        self.f_cat_header.pack(fill="x", padx=20, pady=(10,0), after=self.f_attr)
        self.category_slots_frame.pack(fill="x", padx=20, pady=5, after=self.f_cat_header)
        self.filtered_category_list = self.category_list[:]
        # カテゴリスロットを全て削除
        for slot in self.category_slots[:]:
            self.delete_category_slot(slot["frame"])