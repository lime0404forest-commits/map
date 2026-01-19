import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
import json
import csv
import math
from datetime import datetime
from PIL import Image, ImageTk

from .constants import GAMES_ROOT
from .utils import save_cropped_image_with_annotations

# ==========================================
# 環境設定ウィンドウ (カテゴリ & アイテム管理)
# ==========================================
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_path, current_config):
        super().__init__(parent)
        self.title("環境設定 & マスタ管理")
        self.geometry("700x800")
        self.attributes("-topmost", True)
        self.parent = parent
        self.config_path = config_path
        self.config = current_config
        
        # UI管理用リスト
        self.cat_rows = []
        self.item_rows = []
        
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.tab_cat = self.tabview.add("📌 ピンカテゴリ設定")
        self.tab_item = self.tabview.add("📦 アイテムマスタ設定")
        
        # --- タブ1: ピンカテゴリ ---
        self.setup_cat_tab()
        
        # --- タブ2: アイテムマスタ ---
        self.setup_item_tab()

        # --- フッター ---
        f_foot = ctk.CTkFrame(self, fg_color="transparent")
        f_foot.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(f_foot, text="💾 設定を保存して反映", command=self.save_settings, 
                      fg_color="#27ae60", width=200, height=40, font=("Meiryo", 12, "bold")).pack()

    def setup_cat_tab(self):
        # ヘッダー
        f_head = ctk.CTkFrame(self.tab_cat, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(f_head, text="ID (例: LOC_BASE)", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(f_head, text="表示名 (日本語)", width=200, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=5)
        
        # スクロールエリア
        self.scroll_cat = ctk.CTkScrollableFrame(self.tab_cat, fg_color="#2b2b2b")
        self.scroll_cat.pack(expand=True, fill="both", padx=5, pady=5)
        
        # 追加ボタン
        ctk.CTkButton(self.tab_cat, text="＋ カテゴリ行を追加", command=self.add_cat_row_empty, 
                      fg_color="#e67e22").pack(pady=5)

    def setup_item_tab(self):
        # ヘッダー
        f_head = ctk.CTkFrame(self.tab_item, fg_color="transparent")
        f_head.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(f_head, text="グループ (例: 設計図)", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="ID (例: BP_VALVE)", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="アイテム名 (日本語)", width=150, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)
        ctk.CTkLabel(f_head, text="英語名 (任意)", width=120, anchor="w", font=("Meiryo", 11, "bold")).pack(side="left", padx=2)

        # スクロールエリア
        self.scroll_item = ctk.CTkScrollableFrame(self.tab_item, fg_color="#2b2b2b")
        self.scroll_item.pack(expand=True, fill="both", padx=5, pady=5)
        
        # 追加ボタン
        ctk.CTkButton(self.tab_item, text="＋ アイテム行を追加", command=self.add_item_row_empty, 
                      fg_color="#3498db").pack(pady=5)

    def load_current_settings(self):
        # カテゴリ読み込み
        mapping = self.config.get("cat_mapping", {})
        if not mapping: self.add_cat_row("", "")
        for k, v in mapping.items():
            if v: self.add_cat_row(k, v) # 空文字はスキップ（整理）

        # アイテムマスタ読み込み
        # 構造: {"Group": {"ID": {"name_jp": "A", "name_en": "B"}, ...}}
        item_master = self.config.get("item_master", {})
        if not item_master: self.add_item_row("", "", "", "")
        
        for grp, items in item_master.items():
            for i_id, info in items.items():
                self.add_item_row(grp, i_id, info.get("name_jp",""), info.get("name_en",""))

    # --- カテゴリ行操作 ---
    def add_cat_row_empty(self):
        self.add_cat_row("", "")
        self.after(10, lambda: self.scroll_cat._parent_canvas.yview_moveto(1.0))

    def add_cat_row(self, code, name):
        f = ctk.CTkFrame(self.scroll_cat, fg_color="transparent")
        f.pack(fill="x", pady=2)
        
        e_code = ctk.CTkEntry(f, width=150); e_code.insert(0, code); e_code.pack(side="left", padx=2)
        e_name = ctk.CTkEntry(f, width=200); e_name.insert(0, name); e_name.pack(side="left", padx=2)
        
        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", 
                      command=lambda: self.delete_row(f, self.cat_rows)).pack(side="left", padx=5)
        
        self.cat_rows.append({"frame": f, "code": e_code, "name": e_name})

    # --- アイテム行操作 ---
    def add_item_row_empty(self):
        self.add_item_row("", "", "", "")
        self.after(10, lambda: self.scroll_item._parent_canvas.yview_moveto(1.0))

    def add_item_row(self, grp, i_id, n_jp, n_en):
        f = ctk.CTkFrame(self.scroll_item, fg_color="transparent")
        f.pack(fill="x", pady=2)
        
        e_grp = ctk.CTkEntry(f, width=120); e_grp.insert(0, grp); e_grp.pack(side="left", padx=2)
        e_id = ctk.CTkEntry(f, width=120); e_id.insert(0, i_id); e_id.pack(side="left", padx=2)
        e_jp = ctk.CTkEntry(f, width=150); e_jp.insert(0, n_jp); e_jp.pack(side="left", padx=2)
        e_en = ctk.CTkEntry(f, width=120); e_en.insert(0, n_en); e_en.pack(side="left", padx=2)
        
        ctk.CTkButton(f, text="🗑️", width=30, fg_color="#c0392b", 
                      command=lambda: self.delete_row(f, self.item_rows)).pack(side="left", padx=5)
        
        self.item_rows.append({"frame": f, "grp": e_grp, "id": e_id, "jp": e_jp, "en": e_en})

    def delete_row(self, frame, list_ref):
        frame.destroy()
        # リストからも削除 (一致するオブジェクトを探して消す)
        # ※ リスト内包表記で再構築する手法
        for i in range(len(list_ref)-1, -1, -1):
            if list_ref[i]["frame"] == frame:
                del list_ref[i]

    def save_settings(self):
        # 1. カテゴリ保存
        new_mapping = {}
        for r in self.cat_rows:
            c = r["code"].get().strip()
            n = r["name"].get().strip()
            if c and n: new_mapping[c] = n
        
        self.config["cat_mapping"] = new_mapping

        # 2. アイテムマスタ保存
        # 構造変換: list -> dict
        new_master = {}
        for r in self.item_rows:
            g = r["grp"].get().strip()
            i = r["id"].get().strip()
            nj = r["jp"].get().strip()
            ne = r["en"].get().strip()
            
            if g and i and nj:
                if g not in new_master: new_master[g] = {}
                new_master[g][i] = {"name_jp": nj, "name_en": ne}

        self.config["item_master"] = new_master

        # ファイル書き込み
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("成功", "設定を保存しました。画面を更新します。")
            self.parent.reload_config()
            self.destroy()
        except Exception as e:
            messagebox.showerror("エラー", f"保存失敗:\n{e}")

# ==========================================
# メインエディタ
# ==========================================
class MapEditor(ctk.CTkToplevel):
    def __init__(self, master, game_name, region_name):
        super().__init__(master)
        self.game_path = os.path.join(GAMES_ROOT, game_name, region_name)
        self.tile_dir = os.path.join(self.game_path, "tiles")
        self.config_path = os.path.join(self.game_path, "config.json")
        
        # 1. コンフィグ読み込み
        self.load_config()
        
        # 2. 画像サイズ確保
        if "orig_w" not in self.config:
            m_path = os.path.join(self.game_path, self.config.get("map_file", "map.png"))
            if os.path.exists(m_path):
                with Image.open(m_path) as tmp: self.config["orig_w"], self.config["orig_h"] = tmp.size
                with open(self.config_path, "w", encoding="utf-8") as f: 
                    json.dump(self.config, f, indent=4, ensure_ascii=False)

        self.orig_w, self.orig_h = self.config["orig_w"], self.config["orig_h"]
        
        # 3. ズームレベル計算
        zooms = [int(d) for d in os.listdir(self.tile_dir) if d.isdigit()]
        self.max_zoom = max(zooms) if zooms else 0
        self.zoom = float(self.max_zoom) - 0.5
        self.orig_max_dim = (2 ** self.max_zoom) * 256 
        
        self.title(f"Editor - {game_name} ({region_name})")
        self.geometry("1650x950")
        
        self.data_list = []
        self.current_uid = None
        self.temp_coords = None
        self.is_autoscrolling = False
        self.tile_cache = {}
        
        self.edit_pos_mode_uid = None
        self.is_crop_mode = False
        self.crop_box = {"x": 100, "y": 100, "w": 640, "h": 360}
        self.drag_mode = None
        self.active_tool = None
        self.here_pos = None; self.arrow_pos = None

        self.setup_ui()
        self.load_csv()
        self.update_idletasks()
        self.after(100, self.refresh_map)
        self.run_autoscroll_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f: 
                self.config = json.load(f)
        else:
            self.config = {}

    def reload_config(self):
        self.load_config()
        self.cat_mapping = self.config.get("cat_mapping", {})
        self.item_master = self.config.get("item_master", {})
        
        # カテゴリプルダウン更新
        self.display_names = list(self.cat_mapping.values())
        self.cmb_cat_main.configure(values=self.display_names)
        
        # フィルタ更新
        for widget in self.f_filter.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox) and "未完成" not in widget.cget("text"):
                widget.destroy()
        
        self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
        for n in self.display_names:
            ctk.CTkCheckBox(self.f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)
        
        # アイテムプルダウン更新
        self.update_item_selectors()
        
        self.refresh_map()

    def update_item_selectors(self):
        # アイテムマスタからグループリストを作成
        groups = ["(なし)"] + list(self.item_master.keys())
        for slot in self.item_slots:
            slot["cat"].configure(values=groups)
            # 現在の値がリストになければリセット
            if slot["cat"].get() not in groups:
                slot["cat"].set("(なし)")
                slot["val"].configure(values=["(なし)"])
                slot["val"].set("(なし)")

    def update_item_list(self, group_name, slot_index):
        # グループ選択時にアイテムリストを更新
        slot = self.item_slots[slot_index]
        if group_name == "(なし)" or group_name not in self.item_master:
            slot["val"].configure(values=["(なし)"])
            slot["val"].set("(なし)")
            return

        items = self.item_master[group_name]
        # 表示用リスト: "日本語名" を使う (裏でIDを引けるようにする)
        item_names = ["(なし)"] + [info["name_jp"] for info in items.values()]
        slot["val"].configure(values=item_names)
        slot["val"].set("(なし)")

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        
        self.sidebar = ctk.CTkFrame(self, width=450, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        f_top = ctk.CTkFrame(self.sidebar, fg_color="#34495e", corner_radius=0)
        f_top.pack(fill="x")
        self.lbl_coords = ctk.CTkLabel(f_top, text="座標: ---", font=("Meiryo", 16, "bold"))
        self.lbl_coords.pack(pady=15)
        
        self.scroll_body = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_body.pack(expand=True, fill="both", padx=10, pady=10)
        
        # フィルタ
        ctk.CTkLabel(self.scroll_body, text="表示フィルタ", font=("Meiryo", 13, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.f_filter = ctk.CTkFrame(self.scroll_body, fg_color="#161616")
        self.f_filter.pack(fill="x", padx=10, pady=5)
        
        self.cat_mapping = self.config.get("cat_mapping", {})
        self.item_master = self.config.get("item_master", {})
        self.display_names = list(self.cat_mapping.values())
        self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
        self.show_incomplete_only = tk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(self.f_filter, text="⚠️ 未完成項目のみ", variable=self.show_incomplete_only, command=self.refresh_map, text_color="#e74c3c").pack(anchor="w", padx=15, pady=8)
        for n in self.display_names:
            ctk.CTkCheckBox(self.f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)

        # ピン基本情報
        self.ent_name_jp = self.create_input("▼ 場所/ピンの名前 (任意)")
        self.ent_name_en = self.create_input("▼ Name (Optional)")
        
        ctk.CTkLabel(self.scroll_body, text="▼ ピンカテゴリ (必須)").pack(anchor="w", padx=20, pady=(10,0))
        self.cmb_cat_main = ctk.CTkComboBox(self.scroll_body, values=self.display_names)
        self.cmb_cat_main.pack(fill="x", padx=20, pady=5)

        # ★★★ アイテム（中身）選択スロット ★★★
        ctk.CTkLabel(self.scroll_body, text="▼ 格納アイテム (最大6枠)").pack(anchor="w", padx=20, pady=(20, 0))
        self.item_slots = []
        groups = ["(なし)"] + list(self.item_master.keys())
        
        for i in range(6):
            f = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=1)
            
            # グループ選択
            cmb_grp = ctk.CTkComboBox(f, values=groups, width=100, 
                                      command=lambda v, idx=i: self.update_item_list(v, idx))
            cmb_grp.pack(side="left", padx=(0,2))
            
            # アイテム選択
            cmb_itm = ctk.CTkComboBox(f, values=["(なし)"], width=150)
            cmb_itm.pack(side="left", padx=2, fill="x", expand=True)
            
            # 個数入力
            ent_qty = ctk.CTkEntry(f, width=50, placeholder_text="1")
            ent_qty.pack(side="left", padx=(2,0))
            
            self.item_slots.append({"cat": cmb_grp, "val": cmb_itm, "qty": ent_qty})


        self.txt_memo_jp = self.create_textbox("▼ 詳細メモ (日本語)")
        self.txt_memo_en = self.create_textbox("▼ Memo (English)")

        # フッター
        f_foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_foot.pack(fill="x", side=tk.BOTTOM, padx=20, pady=20)
        
        self.btn_delete = ctk.CTkButton(f_foot, text="🗑️ ピンを削除 (Delete)", command=self.delete_data, fg_color="#c0392b", hover_color="#e74c3c", height=35)
        self.btn_delete.pack(fill="x", side=tk.BOTTOM, pady=(15, 0))

        ctk.CTkButton(f_foot, text="ピン保存 (Ctrl+Enter)", command=self.save_data, fg_color="#2980b9", height=50, font=("Meiryo", 14, "bold")).pack(fill="x", pady=5)
        
        self.btn_edit_pos = ctk.CTkButton(f_foot, text="📍 ピン位置修正モード", command=self.start_edit_pos_mode, fg_color="#d35400", height=35)
        self.btn_edit_pos.pack(fill="x", pady=(5, 10))

        ctk.CTkButton(f_foot, text="⚙ 環境設定 & マスタ管理", command=self.open_settings, fg_color="#7f8c8d", height=30).pack(fill="x", pady=(5, 10))

        # クロップ/アノテーション (省略せず維持)
        f_crop = ctk.CTkFrame(f_foot, fg_color="#2c3e50")
        f_crop.pack(fill="x", pady=10)
        self.btn_crop_mode = ctk.CTkButton(f_crop, text="✂ クロップ開始", command=self.toggle_crop_mode, fg_color="#e67e22", width=140)
        self.btn_crop_mode.pack(side=tk.LEFT, padx=10, pady=10)
        self.btn_crop_exec = ctk.CTkButton(f_crop, text="保存実行", command=self.execute_crop, state="disabled", fg_color="#27ae60", width=100)
        self.btn_crop_exec.pack(side=tk.LEFT, pady=10)
        
        f_ann = ctk.CTkFrame(f_foot, fg_color="transparent")
        f_ann.pack(fill="x")
        self.btn_here = ctk.CTkButton(f_ann, text="🔴 Here!", command=lambda: self.set_tool("here"), state="disabled", width=110, fg_color="#3b8ed0")
        self.btn_here.pack(side=tk.LEFT, padx=2)
        self.btn_arrow = ctk.CTkButton(f_ann, text="🏹 矢印", command=lambda: self.set_tool("arrow"), state="disabled", width=110, fg_color="#3b8ed0")
        self.btn_arrow.pack(side=tk.LEFT, padx=2)

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
        ent = ctk.CTkEntry(self.scroll_body, height=35)
        ent.pack(fill="x", padx=20, pady=5)
        return ent

    def create_textbox(self, label):
        ctk.CTkLabel(self.scroll_body, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        txt = ctk.CTkTextbox(self.scroll_body, height=100)
        txt.pack(fill="x", padx=20, pady=5)
        return txt

    def open_settings(self):
        SettingsWindow(self, self.config_path, self.config)

    # ... (描画系メソッドは変更なし、省略) ...
    def get_ratio(self): return ((2 ** self.zoom) * 256) / self.orig_max_dim
    def start_edit_pos_mode(self):
        if not self.current_uid: messagebox.showwarning("注意", "ピンを選択してください"); return
        self.edit_pos_mode_uid = self.current_uid
        messagebox.showinfo("モード", "新しい位置をクリックしてください")
        self.refresh_map()
    
    def refresh_map(self):
        self.canvas.delete("all")
        r = self.get_ratio()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1: return
        z_src = min(int(math.floor(self.zoom)), self.max_zoom)
        s_diff = 2 ** (self.zoom - z_src)
        ts = int(256 * s_diff)
        vl, vt = self.canvas.canvasx(0), self.canvas.canvasy(0)
        
        # タイル
        for tx in range(int(vl//ts), int((vl+cw)//ts)+1):
            for ty in range(int(vt//ts), int((vt+ch)//ts)+1):
                path = os.path.join(self.tile_dir, str(z_src), str(tx), f"{ty}.webp")
                if os.path.exists(path):
                    key = f"{path}_{ts}"
                    if key not in self.tile_cache: self.tile_cache[key] = ImageTk.PhotoImage(Image.open(path).resize((ts, ts), Image.Resampling.NEAREST))
                    self.canvas.create_image(tx*ts, ty*ts, anchor="nw", image=self.tile_cache[key])
        
        # ピン
        for d in self.data_list:
            cn = self.cat_mapping.get(d.get('category_pin'), "")
            if cn in self.filter_vars and not self.filter_vars[cn].get(): continue
            if self.show_incomplete_only.get() and all([d.get('name_jp'), d.get('contents')]): continue
            
            px, py = d['x']*r, d['y']*r
            if self.edit_pos_mode_uid == d['uid']:
                self.canvas.create_oval(px-15, py-15, px+15, py+15, outline="yellow", width=2, dash=(4,2))
            else:
                self.canvas.create_oval(px-6, py-6, px+6, py+6, fill="#f1c40f" if (d['uid']==self.current_uid) else "#e67e22", outline="white", width=2)

        # 一時マーカー & クロップ枠
        if self.temp_coords and not self.current_uid:
            tx, ty = self.temp_coords[0]*r, self.temp_coords[1]*r
            self.canvas.create_oval(tx-8, ty-8, tx+8, ty+8, outline="cyan", width=2)
        
        if self.is_crop_mode:
            bx, by, bw, bh = self.crop_box["x"]*r, self.crop_box["y"]*r, self.crop_box["w"]*r, self.crop_box["h"]*r
            self.canvas.create_rectangle(bx, by, bx+bw, by+bh, outline="#2ecc71", width=3, dash=(10,5))
            if self.here_pos: 
                hx, hy = self.here_pos["x"]*r, self.here_pos["y"]*r
                self.canvas.create_oval(hx-20, hy-20, hx+20, hy+20, outline="white", width=4)
                self.canvas.create_oval(hx-20, hy-20, hx+20, hy+20, outline="#e74c3c", width=3)

        self.canvas.config(scrollregion=(0, 0, self.orig_w*r, self.orig_h*r))

    # ... (マウスイベント等は変更なし、省略) ...
    def on_zoom(self, event):
        # 既存コードと同じロジック
        view_left = self.canvas.canvasx(0); view_top = self.canvas.canvasy(0)
        mouse_canvas_x = view_left + event.x; mouse_canvas_y = view_top + event.y
        r_old = self.get_ratio()
        total_w_old = self.orig_w * r_old; total_h_old = self.orig_h * r_old
        if total_w_old == 0: return
        rx = mouse_canvas_x / total_w_old; ry = mouse_canvas_y / total_h_old
        d = 0.2 if event.delta > 0 else -0.2
        self.zoom = max(0, min(self.max_zoom + 2.5, self.zoom + d))
        self.refresh_map()
        r_new = self.get_ratio()
        total_w_new = self.orig_w * r_new; total_h_new = self.orig_h * r_new
        self.canvas.xview_moveto((total_w_new * rx - event.x) / total_w_new)
        self.canvas.yview_moveto((total_h_new * ry - event.y) / total_h_new)

    def on_left_down(self, event):
        # クロップ操作など既存ロジック
        r = self.get_ratio()
        mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        cx, cy = mx/r, my/r
        
        if self.is_crop_mode and not self.active_tool:
            b = self.crop_box
            bx, by, bw, bh = b["x"]*r, b["y"]*r, b["w"]*r, b["h"]*r
            if (bx+bw-20 <= mx <= bx+bw+5) and (by+bh-20 <= my <= by+bh+5):
                self.drag_mode = "resize_br"; return
            elif (b["x"] <= cx <= b["x"]+b["w"]) and (b["y"] <= cy <= b["y"]+b["h"]):
                self.drag_mode = "move"; self.drag_offset = (cx - b["x"], cy - b["y"]); return

        self.drag_start = (event.x, event.y)
        self.has_dragged = False
        self.canvas.scan_mark(event.x, event.y)

    def on_left_drag(self, event):
        # 既存ロジック
        r = self.get_ratio(); cx, cy = self.canvas.canvasx(event.x)/r, self.canvas.canvasy(event.y)/r
        if self.drag_mode == "move":
            self.crop_box["x"], self.crop_box["y"] = cx - self.drag_offset[0], cy - self.drag_offset[1]
            self.refresh_map(); return
        elif self.drag_mode == "resize_br":
            new_w = max(160, cx - self.crop_box["x"])
            self.crop_box["w"], self.crop_box["h"] = new_w, new_w * (9/16)
            self.refresh_map(); return
        
        if abs(event.x - self.drag_start[0]) > 5:
            self.has_dragged = True
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.refresh_map()

    def on_left_up(self, event):
        if self.drag_mode: self.drag_mode = None; return
        if not self.has_dragged:
            r = self.get_ratio(); cx, cy = self.canvas.canvasx(event.x)/r, self.canvas.canvasy(event.y)/r
            
            if self.is_crop_mode and self.active_tool:
                if self.active_tool == "here": self.here_pos = {"x": cx, "y": cy}
                elif self.active_tool == "arrow": self.arrow_pos = {"x": cx, "y": cy}
                self.refresh_map(); return

            if self.edit_pos_mode_uid:
                for d in self.data_list:
                    if d['uid'] == self.edit_pos_mode_uid:
                        d['x'], d['y'] = cx, cy
                        self.write_files()
                        break
                self.edit_pos_mode_uid = None
                self.refresh_map(); return

            for d in self.data_list:
                if abs(d['x']-cx)<(16/r) and abs(d['y']-cy)<(16/r):
                    self.current_uid = d['uid']; self.load_to_ui(d); self.refresh_map(); return
            
            self.current_uid, self.temp_coords = None, (cx, cy)
            self.lbl_coords.configure(text=f"座標: ({int(cx)}, {int(cy)})")
            self.refresh_map()

    def toggle_crop_mode(self):
        self.is_crop_mode = not self.is_crop_mode
        st = "normal" if self.is_crop_mode else "disabled"
        self.btn_crop_exec.configure(state=st)
        self.btn_here.configure(state=st); self.btn_arrow.configure(state=st)
        self.refresh_map()

    def set_tool(self, t):
        if self.active_tool == t: self.active_tool = None
        else: self.active_tool = t
        self.refresh_map()

    def execute_crop(self):
        try:
            path, sdir = save_cropped_image_with_annotations(self.game_path, self.config.get("map_file", "map.png"), self.crop_box, self.orig_w, self.orig_h, self.here_pos, self.arrow_pos)
            messagebox.showinfo("成功", f"保存: {path}"); os.startfile(sdir)
        except Exception as e: messagebox.showerror("エラー", str(e))
        self.toggle_crop_mode()
    
    def toggle_autoscroll(self, event):
        self.is_autoscrolling = not self.is_autoscrolling
        self.autoscroll_origin = (event.x, event.y)
        
    def run_autoscroll_loop(self):
        if self.is_autoscrolling:
            mx, my = self.winfo_pointerx()-self.winfo_rootx(), self.winfo_pointery()-self.winfo_rooty()
            dx, dy = (mx-self.autoscroll_origin[0]), (my-self.autoscroll_origin[1])
            if abs(dx)>20 or abs(dy)>20:
                self.canvas.xview_scroll(int(dx/35), "units"); self.canvas.yview_scroll(int(dy/35), "units")
                self.refresh_map()
        self.after(10, self.run_autoscroll_loop)
    
    def on_close(self): self.destroy(); self.master.deiconify()

    # --- データ操作系 (保存・読込) ---
    def save_data(self):
        # UIからデータを取得して保存
        # ID逆引きマップ作成
        rev_cat_map = {v: k for k, v in self.cat_mapping.items()}
        rev_cat_map["(なし)"] = ""
        
        # アイテムリスト生成 (ID:個数|...)
        contents_list = []
        for slot in self.item_slots:
            grp = slot["cat"].get()
            name_jp = slot["val"].get()
            qty = slot["qty"].get().strip() or "1"
            
            if grp != "(なし)" and name_jp != "(なし)" and grp in self.item_master:
                # 名前からIDを引く
                target_id = None
                for i_id, info in self.item_master[grp].items():
                    if info["name_jp"] == name_jp:
                        target_id = i_id
                        break
                if target_id:
                    contents_list.append(f"{target_id}:{qty}")

        contents_str = "|".join(contents_list)
        
        cat_pin = rev_cat_map.get(self.cmb_cat_main.get(), "MISC_OTHER")
        
        dr = {
            'uid': self.current_uid or f"p_{int(datetime.now().timestamp())}",
            'x': self.temp_coords[0] if not self.current_uid else None,
            'y': self.temp_coords[1] if not self.current_uid else None,
            'name_jp': self.ent_name_jp.get(),
            'name_en': self.ent_name_en.get(),
            'category_pin': cat_pin, # ★ 新カラム名
            'contents': contents_str, # ★ 新カラム
            'memo_jp': self.txt_memo_jp.get("1.0", "end-1c").replace("\n", "<br>"),
            'memo_en': self.txt_memo_en.get("1.0", "end-1c").replace("\n", "<br>")
        }
        
        if self.current_uid:
            for d in self.data_list:
                if d['uid'] == self.current_uid: 
                    d.update({k:v for k,v in dr.items() if v is not None})
        else:
            self.data_list.append(dr)
            
        self.write_files()
        self.current_uid = self.temp_coords = None
        self.refresh_map()
        self.clear_ui()

    def delete_data(self):
        if not self.current_uid: return
        if not messagebox.askyesno("確認", "削除しますか？"): return
        self.data_list = [d for d in self.data_list if d['uid'] != self.current_uid]
        self.write_files()
        self.current_uid = None; self.clear_ui(); self.refresh_map()

    def write_files(self):
        p = os.path.join(self.game_path, self.config["save_file"])
        # 新しいカラム定義
        flds = ["uid", "x", "y", "name_jp", "name_en", "category_pin", "contents", "memo_jp", "memo_en"]
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=flds, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.data_list)

    def load_csv(self):
        p = os.path.join(self.game_path, self.config["save_file"])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = []
                for row in reader:
                    # ★ データ移行ロジック: 旧カラムがあれば新カラムへ移動
                    d = dict(row)
                    d['x'] = float(row['x'])
                    d['y'] = float(row['y'])
                    
                    # 旧カラム -> 新カラムへのマッピング
                    if 'category_main' in row and not row.get('category_pin'):
                        d['category_pin'] = row['category_main']
                    
                    # contentsがなければ空文字
                    if 'contents' not in row:
                        d['contents'] = ""
                        
                    rows.append(d)
                self.data_list = rows

    def load_to_ui(self, d):
        self.clear_ui()
        self.ent_name_jp.insert(0, d.get('name_jp',''))
        self.ent_name_en.insert(0, d.get('name_en',''))
        
        cat_key = d.get('category_pin') or d.get('category_main', 'MISC_OTHER')
        self.cmb_cat_main.set(self.cat_mapping.get(cat_key, ""))
        
        # アイテムリストの展開 (ID:Qty|ID:Qty -> UI)
        contents = d.get('contents', "")
        if contents:
            items = contents.split("|")
            for idx, item_str in enumerate(items):
                if idx >= 6: break # スロット数上限
                if ":" in item_str:
                    i_id, qty = item_str.split(":")
                    # IDからグループと名前を探す
                    found_grp, found_name = None, None
                    for grp, vals in self.item_master.items():
                        if i_id in vals:
                            found_grp = grp
                            found_name = vals[i_id]["name_jp"]
                            break
                    
                    if found_grp:
                        self.item_slots[idx]["cat"].set(found_grp)
                        self.update_item_list(found_grp, idx) # リスト更新
                        self.item_slots[idx]["val"].set(found_name)
                        self.item_slots[idx]["qty"].delete(0, tk.END)
                        self.item_slots[idx]["qty"].insert(0, qty)

        self.txt_memo_jp.insert("1.0", d.get('memo_jp','').replace("<br>", "\n"))
        self.txt_memo_en.insert("1.0", d.get('memo_en','').replace("<br>", "\n"))

    def clear_ui(self):
        self.ent_name_jp.delete(0, tk.END); self.ent_name_en.delete(0, tk.END)
        self.txt_memo_jp.delete("1.0", tk.END); self.txt_memo_en.delete("1.0", tk.END)
        for s in self.item_slots:
            s["cat"].set("(なし)")
            s["val"].configure(values=["(なし)"]); s["val"].set("(なし)")
            s["qty"].delete(0, tk.END); s["qty"].insert(0, "1")