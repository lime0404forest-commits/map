import tkinter as tk
from tkinter import ttk, messagebox, font
import customtkinter as ctk
import csv, json, os
import math
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ==========================================
# 1. システム定義 & ファイル設定
# ==========================================
CONFIG_FILE = "config.json"
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 役割固定（セマンティックID）の定義
BASE_SLOTS = {
    "資源系": ["RES_PLANT", "RES_MINERAL", "RES_OTHER"],
    "アイテム系": ["ITEM_WEAPON", "ITEM_GEAR", "ITEM_OTHER"],
    "場所・施設": ["LOC_BASE", "LOC_SETTLE", "LOC_POI"],
    "人物系": ["CHAR_NPC", "CHAR_TRADER", "CHAR_OTHER"], # ← 人物系を追加
    "その他": ["MISC_ENEMY", "MISC_QUEST", "MISC_OTHER"]
}
BASE_CATEGORIES = [item for sublist in BASE_SLOTS.values() for item in sublist]

def load_config():
    # デフォルトの表示名設定
    default_mapping = {
        "RES_PLANT": "植物",
        "RES_MINERAL": "鉱物",
        "ITEM_GEAR": "ツール類",
        "ITEM_OTHER": "その他アイテム",
        "LOC_BASE": "拠点",
        "LOC_POI": "ランドマーク",
        "CHAR_NPC": "重要NPC",   
        "CHAR_TRADER": "",  
        "MISC_ENEMY": "敵",
        "MISC_QUEST": "クエスト"
    }
    # ※設定していない LOC_SETTLE（村）などは空欄になり、UIには出ません。
    
    default = {
        "title": "Strategy Map Editor v5.2",
        "map_file": "valley.webp",
        "save_file": "master_data.csv",
        "cat_mapping": default_mapping,
        "flag1_label": "", "flag2_label": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default, **data}
        except: return default
    return default

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

ctk.set_appearance_mode("dark")

# ==========================================
# 2. 環境設定ウィンドウ クラス
# ==========================================
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("環境設定 - カテゴリ定義")
        self.geometry("550x850")
        self.attributes("-topmost", True)
        self.focus_force()
        self.parent = parent
        self.config = load_config()
        self.setup_ui()

    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(expand=True, fill="both", padx=10, pady=10)
        lbl_f = ("Meiryo", 12, "bold")
        
        ctk.CTkLabel(scroll, text="■ 基本設定", font=lbl_f).pack(anchor="w", pady=5)
        self.ent_title = self.create_input(scroll, "タイトル", self.config.get("title", ""))

        self.cat_entries = {}
        for group, slots in BASE_SLOTS.items():
            ctk.CTkLabel(scroll, text=f"■ {group}", font=lbl_f).pack(anchor="w", pady=(20, 5))
            for slot_id in slots:
                val = self.config.get("cat_mapping", {}).get(slot_id, "")
                self.cat_entries[slot_id] = self.create_mapping_input(scroll, slot_id, val)

        ctk.CTkLabel(scroll, text="■ 特殊フラグ", font=lbl_f).pack(anchor="w", pady=(20, 5))
        self.ent_f1 = self.create_input(scroll, "フラグ1名", self.config.get("flag1_label", ""))
        self.ent_f2 = self.create_input(scroll, "フラグ2名", self.config.get("flag2_label", ""))
        
        ctk.CTkButton(self, text="設定を保存", command=self.apply, fg_color="#27ae60", height=45).pack(pady=20)

    def create_input(self, m, l, v):
        f = ctk.CTkFrame(m, fg_color="transparent"); f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=l, width=120, anchor="w").pack(side=tk.LEFT)
        ent = ctk.CTkEntry(f, width=300); ent.insert(0, v); ent.pack(side=tk.LEFT, padx=5); return ent

    def create_mapping_input(self, m, slot_id, v):
        f = ctk.CTkFrame(m, fg_color="transparent"); f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=f"{slot_id} :", width=120, anchor="e", font=("Consolas", 10)).pack(side=tk.LEFT)
        ent = ctk.CTkEntry(f, width=280, placeholder_text="未設定なら非表示"); ent.insert(0, v); ent.pack(side=tk.LEFT, padx=5); return ent

    def apply(self):
        new_cfg = {
            "title": self.ent_title.get(), "map_file": self.config["map_file"], "save_file": self.config["save_file"],
            "cat_mapping": {slot: ent.get() for slot, ent in self.cat_entries.items()},
            "flag1_label": self.ent_f1.get(), "flag2_label": self.ent_f2.get()
        }
        save_config(new_cfg)
        messagebox.showinfo("完了", "設定を保存しました。反映には再起動してください。")
        self.destroy()

# ==========================================
# 3. メインエディタ クラス
# ==========================================
class MapEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 1. データの読み込み
        self.config = load_config()
        self.orig_img = Image.open(self.config["map_file"]).convert("RGB")
        
        # 2. 変数初期化
        self.title(f"Data Factory v5.2 - {self.config['title']}")
        self.geometry("1650x950")
        self.scale = 1.0
        self.data_list = []
        self.current_uid = None
        self.temp_coords = None
        self.is_autoscrolling = False
        
        # カテゴリ・マッピング
        self.cat_mapping = self.config.get("cat_mapping", {})
        self.active_slots = {k: v for k, v in self.cat_mapping.items() if v.strip()}
        self.display_names = list(self.active_slots.values())
        self.filter_vars = {name: tk.BooleanVar(value=True) for name in self.display_names}
        self.show_incomplete_only = tk.BooleanVar(value=False)
        
        # クロップ/マーカー設定
        self.is_crop_mode = False
        self.crop_box = {"x": 500, "y": 500, "w": 640, "h": 360} 
        self.drag_target = None
        self.handle_size = 30
        self.crop_markers = [] 
        self.active_tool = None

        # 3. UI構築
        self.setup_ui()
        self.load_csv()
        
        # 4. 描画 & ループ
        self.refresh_map()
        self.run_autoscroll_loop()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        
        # キャンバス（視覚効果用のフレーム）
        self.canvas_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=0)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        
        self.sidebar = ctk.CTkFrame(self, width=450, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")

        # ステータスバー (カラーチェンジ仕様)
        self.f_status = ctk.CTkFrame(self.sidebar, fg_color="#34495e", corner_radius=0)
        self.f_status.pack(fill="x", side=tk.TOP)
        self.lbl_mode_title = ctk.CTkLabel(self.f_status, text="待機中", font=("Meiryo", 14, "bold")); self.lbl_mode_title.pack(pady=(8, 0))
        self.lbl_coords = ctk.CTkLabel(self.f_status, text="座標: (---, ---)", font=("Consolas", 12)); self.lbl_coords.pack(pady=(0, 8))

        self.scroll_body = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent"); self.scroll_body.pack(expand=True, fill="both", padx=5, pady=5)

        # フィルターエリア
        self.f_filter = ctk.CTkFrame(self.scroll_body, fg_color="#2c3e50"); self.f_filter.pack(fill="x", padx=10, pady=5)
        ctk.CTkCheckBox(self.f_filter, text="⚠️ 未完成のみ表示", variable=self.show_incomplete_only, text_color="#e74c3c", command=self.refresh_map).pack(anchor="w", padx=15, pady=5)
        for name in self.display_names:
            ctk.CTkCheckBox(self.f_filter, text=name, variable=self.filter_vars[name], command=self.refresh_map).pack(anchor="w", padx=15)

        ctk.CTkButton(self.scroll_body, text="⚙ 環境設定", command=self.open_settings, fg_color="#5d6d7e").pack(pady=10, padx=10, fill="x")

        # 入力フォーム
        ctk.CTkLabel(self.scroll_body, text="▼ 日本語名", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=20)
        self.ent_name_jp = ctk.CTkEntry(self.scroll_body); self.ent_name_jp.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(self.scroll_body, text="▼ 英語名", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=20)
        self.ent_name_en = ctk.CTkEntry(self.scroll_body); self.ent_name_en.pack(fill="x", padx=20, pady=2)
        
        ctk.CTkLabel(self.scroll_body, text="▼ カテゴリ", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        self.cmb_cat = ctk.CTkComboBox(self.scroll_body, values=self.display_names); self.cmb_cat.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(self.scroll_body, text="▼ 重要度", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=20)
        self.cmb_imp = ctk.CTkComboBox(self.scroll_body, values=["1","2","3","4","5"]); self.cmb_imp.set("1"); self.cmb_imp.pack(fill="x", padx=20, pady=2)

        self.flag_f = ctk.CTkFrame(self.scroll_body, fg_color="transparent"); self.flag_f.pack(fill="x", padx=20, pady=10)
        self.flag1_var, self.flag2_var = tk.BooleanVar(), tk.BooleanVar()
        if self.config.get("flag1_label"): ctk.CTkCheckBox(self.flag_f, text=self.config["flag1_label"], variable=self.flag1_var).pack(side=tk.LEFT, padx=5)
        if self.config.get("flag2_label"): ctk.CTkCheckBox(self.flag_f, text=self.config["flag2_label"], variable=self.flag2_var).pack(side=tk.LEFT, padx=5)

        ctk.CTkLabel(self.scroll_body, text="▼ 詳細メモ (JP)", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=20)
        self.txt_memo_jp = ctk.CTkTextbox(self.scroll_body, height=100); self.txt_memo_jp.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(self.scroll_body, text="▼ Detailed Memo (EN)", font=("Meiryo", 10, "bold")).pack(anchor="w", padx=20)
        self.txt_memo_en = ctk.CTkTextbox(self.scroll_body, height=100); self.txt_memo_en.pack(fill="x", padx=20, pady=2)

        # 固定フッター
        self.f_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent"); self.f_footer.pack(fill="x", side=tk.BOTTOM, padx=10, pady=10)
        ctk.CTkButton(self.f_footer, text="保存 (Ctrl+Enter)", command=self.save_data, height=45, font=("Meiryo", 14, "bold"), fg_color="#2980b9").pack(fill="x", pady=5)
        
        # クロップツール
        f_crop_main = ctk.CTkFrame(self.f_footer, fg_color="#2c3e50"); f_crop_main.pack(fill="x", pady=5)
        self.btn_crop_mode = ctk.CTkButton(f_crop_main, text="✂ クロップ開始", command=self.toggle_crop_mode, fg_color="#e67e22", width=120); self.btn_crop_mode.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_crop_exec = ctk.CTkButton(f_crop_main, text="クロップ", command=self.execute_crop, state="disabled", fg_color="#27ae60", width=100); self.btn_crop_exec.pack(side=tk.LEFT, padx=5, pady=5)

        # アノテーションツール
        self.f_crop_tools = ctk.CTkFrame(self.f_footer, fg_color="transparent"); self.f_crop_tools.pack(fill="x")
        self.btn_tool_here = ctk.CTkButton(self.f_crop_tools, text="🔴 Here!", command=lambda: self.set_tool("here"), state="disabled", width=110, fg_color="#5d6d7e"); self.btn_tool_here.pack(side=tk.LEFT, padx=2)
        self.btn_tool_arrow = ctk.CTkButton(self.f_crop_tools, text="🏹 矢印", command=lambda: self.set_tool("arrow"), state="disabled", width=110, fg_color="#5d6d7e"); self.btn_tool_arrow.pack(side=tk.LEFT, padx=2)
        self.btn_tool_clear = ctk.CTkButton(self.f_crop_tools, text="リセット", command=self.clear_markers, state="disabled", width=60, fg_color="#34495e"); self.btn_tool_clear.pack(side=tk.LEFT, padx=2)

        # イベントバインド
        self.canvas.bind("<Button-1>", self.on_left_down); self.canvas.bind("<B1-Motion>", self.on_left_drag); self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        self.canvas.bind("<MouseWheel>", self.on_zoom); self.canvas.bind("<Button-2>", self.toggle_autoscroll); self.bind("<Control-Return>", lambda e: self.save_data())
        self.txt_memo_jp.bind("<Tab>", self.focus_next_widget); self.txt_memo_en.bind("<Tab>", self.focus_next_widget); self.txt_memo_en.bind("<Return>", self.handle_enter_save)

    # --- ビジュアル・フィードバック ---
    def update_visual_state(self):
        if not self.is_crop_mode:
            self.f_status.configure(fg_color="#34495e"); self.lbl_mode_title.configure(text="待機中 (通常モード)")
            self.canvas_frame.configure(border_width=0); return
        self.canvas_frame.configure(border_width=2, border_color="#2ecc71")
        if self.active_tool == "here":
            self.f_status.configure(fg_color="#e74c3c"); self.lbl_mode_title.configure(text="【Here! 配置中】クリックで更新")
            self.btn_tool_here.configure(fg_color="#e74c3c"); self.btn_tool_arrow.configure(fg_color="#5d6d7e")
        elif self.active_tool == "arrow":
            self.f_status.configure(fg_color="#e67e22"); self.lbl_mode_title.configure(text="【矢印 配置中】クリックで更新")
            self.btn_tool_arrow.configure(fg_color="#e67e22"); self.btn_tool_here.configure(fg_color="#5d6d7e")
        else:
            self.f_status.configure(fg_color="#2ecc71"); self.lbl_mode_title.configure(text="【範囲調整中】ドラッグで枠移動")
            self.btn_tool_here.configure(fg_color="#5d6d7e"); self.btn_tool_arrow.configure(fg_color="#5d6d7e")

    # --- クロップ・ツール処理 ---
    def toggle_crop_mode(self):
        self.is_crop_mode = not self.is_crop_mode
        self.crop_markers = []; self.active_tool = None
        if self.is_crop_mode:
            self.btn_crop_mode.configure(text="✖ 中止", fg_color="#c0392b")
            self.btn_crop_exec.configure(state="normal")
            self.btn_tool_here.configure(state="normal"); self.btn_tool_arrow.configure(state="normal"); self.btn_tool_clear.configure(state="normal")
        else:
            self.btn_crop_mode.configure(text="✂ クロップ開始", fg_color="#e67e22")
            self.btn_crop_exec.configure(state="disabled")
            self.btn_tool_here.configure(state="disabled"); self.btn_tool_arrow.configure(state="disabled"); self.btn_tool_clear.configure(state="disabled")
        self.update_visual_state(); self.refresh_map()

    def set_tool(self, tool_type):
        self.active_tool = tool_type if self.active_tool != tool_type else None
        self.update_visual_state()

    def clear_markers(self): self.crop_markers = []; self.refresh_map()

    # --- 操作ロジック（ズーム対応座標変換） ---
    def on_left_down(self, event):
        cx, cy = self.canvas.canvasx(event.x) / self.scale, self.canvas.canvasy(event.y) / self.scale
        if self.is_crop_mode:
            b = self.crop_box; sh = self.handle_size / self.scale
            if (b["x"]+b["w"]-sh <= cx <= b["x"]+b["w"]+sh) and (b["y"]+b["h"]-sh <= cy <= b["y"]+b["h"]+sh):
                self.drag_target = "resize"; return
            elif b["x"] <= cx <= b["x"]+b["w"] and b["y"] <= cy <= b["y"]+b["h"] and not self.active_tool:
                self.drag_target = "move"; self.drag_offset = (cx - b["x"], cy - b["y"]); return
        self.drag_target = None; self.is_autoscrolling = False; self.drag_start_pos = (event.x, event.y); self.has_dragged = False
        self.canvas.scan_mark(event.x, event.y); self.canvas.config(cursor="fleur")

    def on_left_drag(self, event):
        cx, cy = self.canvas.canvasx(event.x) / self.scale, self.canvas.canvasy(event.y) / self.scale
        if self.is_crop_mode and self.drag_target:
            b = self.crop_box
            if self.drag_target == "move": b["x"], b["y"] = cx - self.drag_offset[0], cy - self.drag_offset[1]
            elif self.drag_target == "resize": b["w"] = max(100, cx - b["x"]); b["h"] = int(b["w"] * 9 / 16)
            self.refresh_map(); return
        if abs(event.x - self.drag_start_pos[0]) > 5 or abs(event.y - self.drag_start_pos[1]) > 5:
            self.has_dragged = True; self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_left_up(self, event):
        self.canvas.config(cursor="cross" if not self.is_crop_mode else "arrow")
        if self.is_crop_mode and self.active_tool and not self.has_dragged:
            cx, cy = self.canvas.canvasx(event.x) / self.scale, self.canvas.canvasy(event.y) / self.scale
            self.crop_markers = [m for m in self.crop_markers if m["type"] != self.active_tool]
            self.crop_markers.append({"type": self.active_tool, "x": cx, "y": cy})
            self.refresh_map(); self.drag_target = None; return
        self.drag_target = None
        if not self.has_dragged: self.handle_selection(event)

    # --- 描画ロジック ---
    def refresh_map(self):
        w, h = self.orig_img.size; ns = (int(w * self.scale), int(h * self.scale))
        self.display_img = self.orig_img.resize(ns, Image.Resampling.LANCZOS); self.tk_img = ImageTk.PhotoImage(self.display_img)
        self.canvas.delete("all"); self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=(0, 0, ns[0], ns[1]))
        
        for d in self.data_list:
            slot_id = d.get('category', '')
            dname = self.cat_mapping.get(slot_id, slot_id)
            if dname in self.filter_vars and not self.filter_vars[dname].get(): continue
            if self.show_incomplete_only.get() and not any([not d.get('name_jp'), not d.get('name_en'), not d.get('memo_jp'), not d.get('memo_en')]): continue
            px, py = d['x'] * self.scale, d['y'] * self.scale
            c = "#ff4757" if self.show_incomplete_only.get() else ("#f1c40f" if d['uid'] == self.current_uid else "#e67e22")
            self.canvas.create_oval(px-6, py-6, px+6, py+6, fill=c, outline="white", width=2 if d['uid']==self.current_uid else 1)
        
        if self.is_crop_mode:
            b = self.crop_box; x, y, ww, hh = b["x"]*self.scale, b["y"]*self.scale, b["w"]*self.scale, b["h"]*self.scale
            self.canvas.create_rectangle(x, y, x+ww, y+hh, outline="#2ecc71", width=3, dash=(10,5))
            s = self.handle_size; self.canvas.create_rectangle(x+ww-s, y+hh-s, x+ww, y+hh, fill="#2ecc71")
            for m in self.crop_markers:
                mx, my = m["x"]*self.scale, m["y"]*self.scale
                if m["type"]=="here":
                    self.canvas.create_oval(mx-15, my-15, mx+15, my+15, outline="#ff0000", width=4)
                    self.canvas.create_text(mx+22, my, text="Here!", fill="#ff0000", font=("Arial", 14, "bold"), anchor="w")
                elif m["type"]=="arrow":
                    self.canvas.create_line(mx+40, my+40, mx+5, my+5, fill="#ff0000", width=6, arrow=tk.LAST, arrowshape=(16,20,8))
        if self.temp_coords and not self.current_uid and not self.is_crop_mode:
            tx, ty = self.temp_coords[0] * self.scale, self.temp_coords[1] * self.scale
            self.canvas.create_line(tx-15, ty, tx+15, ty, fill="cyan", width=2); self.canvas.create_line(tx, ty-15, tx, ty+15, fill="cyan", width=2)

    # --- データ入出力・管理 ---
    def save_data(self, event=None):
        n_jp = self.ent_name_jp.get()
        if not n_jp and not self.current_uid: return
        if not messagebox.askyesno("保存確認", f"'{n_jp}' を保存しますか？"): return
        disp_to_slot = {v: k for k, v in self.active_slots.items()}
        slot_id = disp_to_slot.get(self.cmb_cat.get(), "MISC_OTHER")
        dr = {'uid': self.current_uid or f"p_{int(datetime.now().timestamp())}", 'x': self.temp_coords[0] if not self.current_uid else None, 'y': self.temp_coords[1] if not self.current_uid else None, 'name_jp': n_jp, 'name_en': self.ent_name_en.get(), 'category': slot_id, 'importance': self.cmb_imp.get(), 'f1': 1 if self.flag1_var.get() else 0, 'f2': 1 if self.flag2_var.get() else 0, 'memo_jp': self.txt_memo_jp.get("1.0", "end-1c"), 'memo_en': self.txt_memo_en.get("1.0", "end-1c"), 'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        if self.current_uid:
            for d in self.data_list:
                if d['uid'] == self.current_uid: d.update({k:v for k,v in dr.items() if v is not None})
        else: self.data_list.append(dr)
        # CSVとJSONの両方を書き出す
        self.write_csv()
        self.write_json() 
        
        self.current_uid=None; self.temp_coords=None; self.refresh_map(); self.clear_ui()

    def load_to_ui(self, data):
        self.clear_ui(); self.ent_name_jp.insert(0, data.get('name_jp', '')); self.ent_name_en.insert(0, data.get('name_en', ''))
        slot_id = data.get('category', ''); disp_name = self.cat_mapping.get(slot_id, "")
        if disp_name in self.display_names: self.cmb_cat.set(disp_name)
        self.cmb_imp.set(data.get('importance', '1'))
        self.flag1_var.set(str(data.get('f1', '0')) == '1'); self.flag2_var.set(str(data.get('f2', '0')) == '1')
        self.txt_memo_jp.insert("1.0", data.get('memo_jp', '')); self.txt_memo_en.insert("1.0", data.get('memo_en', ''))

    def execute_crop(self):
        b = self.crop_box; box = (b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"])
        cropped = self.orig_img.crop(box); draw = ImageDraw.Draw(cropped)
        for d in self.data_list:
            slot_id = d.get('category', '')
            dname = self.cat_mapping.get(slot_id, slot_id)
            if dname in self.filter_vars and not self.filter_vars[dname].get(): continue
            px, py = d['x']-b["x"], d['y']-b["y"]
            if 0<=px<cropped.width and 0<=py<cropped.height: draw.ellipse((px-5, py-5, px+5, py+5), fill="#e67e22", outline="white", width=2)
        try: fnt = ImageFont.truetype("arialbd.ttf", 24)
        except: fnt = ImageFont.load_default()
        for m in self.crop_markers:
            mx, my = m["x"]-b["x"], m["y"]-b["y"]
            if 0<=mx<cropped.width and 0<=my<cropped.height:
                if m["type"] == "here":
                    draw.ellipse((mx-15, my-15, mx+15, my+15), outline="#ff0000", width=4)
                    draw.text((mx+20, my-15), "Here!", font=fnt, fill="#ff0000", stroke_width=2, stroke_fill="white")
                elif m["type"] == "arrow":
                    draw.line((mx+40, my+40, mx+5, my+5), fill="#ff0000", width=6)
                    draw.polygon([(mx, my), (mx+15, my+5), (mx+5, my+15)], fill="#ff0000")
        fname = f"crop_{datetime.now().strftime('%m%d_%H%M%S')}.png"
        cropped.save(os.path.join(SCREENSHOT_DIR, fname)); messagebox.showinfo("保存完了", fname); self.toggle_crop_mode()

    def write_csv(self):
        fields = ["uid", "x", "y", "name_jp", "name_en", "category", "importance", "tags", "memo_jp", "memo_en", "updated_at", "f1", "f2"]
        with open(self.config["save_file"], "w", newline="", encoding="utf-8-sig") as f: writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(self.data_list)
    def write_json(self):
        # CSVのファイル名（master_data.csv）を map_data.json に置換してパスを作成
        json_file = self.config["save_file"].replace(".csv", ".json")
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(self.data_list, f, indent=4, ensure_ascii=False)
            print(f"JSON saved to {json_file}")
        except Exception as e:
            messagebox.showerror("JSON保存エラー", f"JSONの書き出しに失敗しました: {e}")
    def load_csv(self):
        if os.path.exists(self.config["save_file"]):
            with open(self.config["save_file"], "r", encoding="utf-8-sig") as f: self.data_list = [dict(row, x=int(row['x']), y=int(row['y'])) for row in csv.DictReader(f)]
    def handle_selection(self, event):
        x, y = int(self.canvas.canvasx(event.x)/self.scale), int(self.canvas.canvasy(event.y)/self.scale); self.lbl_coords.configure(text=f"座標: ({x}, {y})")
        if self.is_crop_mode: return
        for d in self.data_list:
            if abs(d['x']-x)<(20/self.scale) and abs(d['y']-y)<(20/self.scale):
                self.current_uid=d['uid']; self.lbl_mode_title.configure(text=f"編集: {d['name_jp']}", text_color="#f39c12"); self.load_to_ui(d); self.refresh_map(); return
        self.current_uid=None; self.temp_coords=(x,y); self.lbl_mode_title.configure(text="新規地点を選択中", text_color="#3498db"); self.clear_ui(); self.ent_name_jp.focus(); self.refresh_map()
    def clear_ui(self):
        self.ent_name_jp.delete(0, tk.END); self.ent_name_en.delete(0, tk.END); self.txt_memo_jp.delete("1.0", tk.END); self.txt_memo_en.delete("1.0", tk.END); self.flag1_var.set(False); self.flag2_var.set(False)
    def open_settings(self): SettingsWindow(self)
    def on_zoom(self, event): self.scale = max(0.1, min(self.scale * (1.1 if event.delta > 0 else 0.9), 10.0)); self.refresh_map()
    def focus_next_widget(self, event): event.widget.tk_focusNext().focus(); return "break"
    def handle_enter_save(self, event):
        if not (event.state & 0x0001): self.save_data(); return "break"
        return None
    def toggle_autoscroll(self, event):
        self.is_autoscrolling = not self.is_autoscrolling
        if self.is_autoscrolling:
            self.autoscroll_origin = (event.x, event.y); self.canvas.create_oval(event.x-4, event.y-4, event.x+4, event.y+4, fill="white", tags="as_origin")
        else: self.canvas.delete("as_origin")
    def run_autoscroll_loop(self):
        if self.is_autoscrolling:
            mx, my = self.winfo_pointerx()-self.winfo_rootx(), self.winfo_pointery()-self.winfo_rooty()
            dx, dy = (mx-self.autoscroll_origin[0]), (my-self.autoscroll_origin[1]); dz = 20; sx, sy = 0, 0
            if abs(dx)>dz: sx = (dx-(dz if dx>0 else -dz))/30
            if abs(dy)>dz: sy = (dy-(dz if dy>0 else -dz))/30
            if sx!=0 or sy!=0: self.canvas.xview_scroll(int(sx), "units"); self.canvas.yview_scroll(int(sy), "units")
        self.after(10, self.run_autoscroll_loop)

if __name__ == "__main__":
    app = MapEditor(); app.mainloop()