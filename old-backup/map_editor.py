import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import csv, json, os, sys, math, shutil
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw

# ==========================================
# 1. システム環境定義
# ==========================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
GAMES_ROOT = os.path.join(PROJECT_ROOT, "games")
os.makedirs(GAMES_ROOT, exist_ok=True)

# ==========================================
# 2. ポータル画面（タイトル選択 ➡ 地域選択）
# ==========================================
class Portal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Strategy Map Portal 2026")
        self.geometry("600x850")
        ctk.set_appearance_mode("dark")
        self.setup_main_ui()

    def setup_main_ui(self):
        for child in self.winfo_children(): child.destroy()
        ctk.CTkLabel(self, text="Game Selection", font=("Meiryo", 26, "bold")).pack(pady=25)
        
        self.scroll = ctk.CTkScrollableFrame(self, width=520, height=550)
        self.scroll.pack(pady=10, padx=20, fill="both", expand=True)

        games = [d for d in os.listdir(GAMES_ROOT) if os.path.isdir(os.path.join(GAMES_ROOT, d))]
        for g in games:
            btn = ctk.CTkButton(self.scroll, text=g, height=55, font=("Meiryo", 16),
                               fg_color="#34495e", hover_color="#2c3e50",
                               command=lambda n=g: self.show_regions(n))
            btn.pack(fill="x", pady=8, padx=15)

        ctk.CTkButton(self, text="+ 新規タイトルを登録", font=("Meiryo", 14, "bold"),
                     fg_color="#27ae60", hover_color="#219150",
                     command=self.add_game).pack(pady=25)

    def show_regions(self, game_name):
        for child in self.winfo_children(): child.destroy()
        self.current_game = game_name
        
        f_nav = ctk.CTkFrame(self, fg_color="transparent")
        f_nav.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(f_nav, text="<< Back", width=80, command=self.setup_main_ui).pack(side=tk.LEFT)
        
        ctk.CTkLabel(self, text=f"{game_name}", font=("Meiryo", 24, "bold")).pack(pady=5)
        ctk.CTkLabel(self, text="Select Region Map", font=("Meiryo", 14), text_color="gray").pack()
        
        reg_scroll = ctk.CTkScrollableFrame(self, width=520, height=450)
        reg_scroll.pack(pady=10, padx=20, fill="both", expand=True)

        game_path = os.path.join(GAMES_ROOT, game_name)
        regions = [d for d in os.listdir(game_path) if os.path.isdir(os.path.join(game_path, d))]
        for r in regions:
            btn = ctk.CTkButton(reg_scroll, text=r, height=50, font=("Meiryo", 15),
                               fg_color="#2980b9", hover_color="#2471a3",
                               command=lambda n=r: self.launch_editor(game_name, n))
            btn.pack(fill="x", pady=6, padx=15)

        ctk.CTkButton(self, text="+ 新規地域マップを追加 (Auto Tile)", font=("Meiryo", 14),
                     fg_color="#e67e22", hover_color="#d35400",
                     command=self.setup_new_region).pack(pady=25)

    def add_game(self):
        name = filedialog.askstring("新規登録", "ゲームタイトルを入力してください")
        if name:
            os.makedirs(os.path.join(GAMES_ROOT, name), exist_ok=True)
            self.setup_main_ui()

    def setup_new_region(self):
        reg_name = filedialog.askstring("新規マップ", "地域名（マップ名）を入力してください\n(例: Valley, Oxbow)")
        if not reg_name: return
        img_path = filedialog.askopenfilename(title="高解像度の地図画像を選択")
        if not img_path: return
        
        target_dir = os.path.join(GAMES_ROOT, self.current_game, reg_name)
        os.makedirs(target_dir, exist_ok=True)
        self.process_new_map(img_path, target_dir)
        self.show_regions(self.current_game)

    def process_new_map(self, src_img, target_dir):
        popup = ctk.CTkToplevel(self)
        popup.geometry("350x180")
        popup.title("Processing...")
        popup.attributes("-topmost", True)
        ctk.CTkLabel(popup, text="タイル化を実行中です...\n完了までそのままお待ちください", font=("Meiryo", 14)).pack(expand=True)
        self.update()

        try:
            img = Image.open(src_img).convert('RGB')
            w, h = img.size
            max_dim = max(w, h)
            shutil.copy(src_img, os.path.join(target_dir, "map.png"))
            
            config = {
                "orig_w": w, "orig_h": h,
                "map_file": "map.png",
                "save_file": "master_data.csv",
                "cat_mapping": {"LOC_BASE":"拠点", "RES_MINERAL":"鉱物", "LOC_POI":"ランドマーク"}
            }
            with open(os.path.join(target_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            square_bg = Image.new('RGB', (max_dim, max_dim), (0, 0, 0))
            square_bg.paste(img, (0, 0))
            max_zoom = math.ceil(math.log(max_dim / 256, 2))
            tile_dir = os.path.join(target_dir, "tiles")

            for zoom in range(max_zoom, -1, -1):
                num_tiles = 2 ** zoom
                c_size = num_tiles * 256
                resized = square_bg.resize((c_size, c_size), Image.Resampling.BILINEAR)
                for x in range(num_tiles):
                    for y in range(num_tiles):
                        tile = resized.crop((x*256, y*256, (x+1)*256, (y+1)*256))
                        p = os.path.join(tile_dir, str(zoom), str(x))
                        os.makedirs(p, exist_ok=True)
                        tile.save(os.path.join(p, f"{y}.webp"), "WEBP", quality=80)
            messagebox.showinfo("完了", "地図の最適化（タイル化）が成功しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"タイル化に失敗しました: {e}")
        finally:
            popup.destroy()

    def launch_editor(self, game, region):
        self.withdraw()
        MapEditor(self, game, region)

# ==========================================
# 3. メインエディタ
# ==========================================
class MapEditor(ctk.CTkToplevel):
    def __init__(self, master, game_name, region_name):
        super().__init__(master)
        self.game_path = os.path.join(GAMES_ROOT, game_name, region_name)
        self.tile_dir = os.path.join(self.game_path, "tiles")
        
        # 設定の読み込みと自動修復
        config_p = os.path.join(self.game_path, "config.json")
        with open(config_p, "r", encoding="utf-8") as f: self.config = json.load(f)
        
        if "orig_w" not in self.config:
            m_path = os.path.join(self.game_path, self.config.get("map_file", "map.png"))
            if os.path.exists(m_path):
                with Image.open(m_path) as tmp: self.config["orig_w"], self.config["orig_h"] = tmp.size
                with open(config_p, "w", encoding="utf-8") as f: 
                    json.dump(self.config, f, indent=4, ensure_ascii=False)

        self.orig_w, self.orig_h = self.config["orig_w"], self.config["orig_h"]
        self.orig_max_dim = max(self.orig_w, self.orig_h)
        
        zooms = [int(d) for d in os.listdir(self.tile_dir) if d.isdigit()]
        self.max_zoom = max(zooms) if zooms else 0
        self.zoom = float(self.max_zoom) - 0.5
        
        self.title(f"Editor - {game_name} ({region_name})")
        self.geometry("1680x980")
        
        # 内部変数
        self.data_list, self.current_uid, self.temp_coords = [], None, None
        self.is_autoscrolling, self.tile_cache = False, {}
        
        # クロップ/アノテーション関連
        self.is_crop_mode = False
        self.crop_box = {"x": 100, "y": 100, "w": 640, "h": 360} # 初期16:9
        self.drag_mode = None # "move" or "resize_br"
        self.active_tool = None
        self.here_pos = None
        self.arrow_pos = None

        self.setup_ui()
        self.load_csv()
        
        # 起動時の描画タイミング補正
        self.update_idletasks()
        self.after(100, self.refresh_map)
        
        self.run_autoscroll_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        
        # キャンバス
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        
        # サイドバー
        self.sidebar = ctk.CTkFrame(self, width=450, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # --- サイドバー内容 ---
        f_top = ctk.CTkFrame(self.sidebar, fg_color="#34495e", corner_radius=0)
        f_top.pack(fill="x")
        self.lbl_coords = ctk.CTkLabel(f_top, text="座標: ---", font=("Meiryo", 16, "bold"))
        self.lbl_coords.pack(pady=15)
        
        self.scroll_body = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_body.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 表示フィルタ
        ctk.CTkLabel(self.scroll_body, text="表示フィルタ", font=("Meiryo", 13, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        f_filter = ctk.CTkFrame(self.scroll_body, fg_color="#161616")
        f_filter.pack(fill="x", padx=10, pady=5)
        
        self.cat_mapping = self.config.get("cat_mapping", {})
        self.display_names = [v for v in self.cat_mapping.values() if v.strip()]
        self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
        self.show_incomplete_only = tk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(f_filter, text="⚠️ 未完成項目のみ", variable=self.show_incomplete_only, 
                       command=self.refresh_map, text_color="#e74c3c").pack(anchor="w", padx=15, pady=8)
        for n in self.display_names:
            ctk.CTkCheckBox(f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)

        # 入力フォーム
        self.ent_name_jp = self.create_input("▼ 日本語名 (表示タイトル)")
        self.ent_name_en = self.create_input("▼ 英語名 (English Name)")
        
        ctk.CTkLabel(self.scroll_body, text="▼ カテゴリ").pack(anchor="w", padx=20, pady=(10,0))
        self.cmb_cat = ctk.CTkComboBox(self.scroll_body, values=self.display_names)
        self.cmb_cat.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(self.scroll_body, text="▼ 重要度 (5が最高)").pack(anchor="w", padx=20, pady=(5,0))
        self.cmb_imp = ctk.CTkComboBox(self.scroll_body, values=["1","2","3","4","5"])
        self.cmb_imp.set("1")
        self.cmb_imp.pack(fill="x", padx=20, pady=5)
        
        self.txt_memo_jp = self.create_textbox("▼ 詳細メモ (日本語)")
        self.txt_memo_en = self.create_textbox("▼ Description (English)")

        # フッターボタン
        f_foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_foot.pack(fill="x", side=tk.BOTTOM, padx=20, pady=20)
        
        ctk.CTkButton(f_foot, text="ピン情報を保存 (Ctrl+Enter)", command=self.save_data, 
                     fg_color="#2980b9", hover_color="#2471a3", height=50, font=("Meiryo", 14, "bold")).pack(fill="x", pady=5)
        
        # クロップツール
        f_crop = ctk.CTkFrame(f_foot, fg_color="#2c3e50")
        f_crop.pack(fill="x", pady=10)
        self.btn_crop_mode = ctk.CTkButton(f_crop, text="✂ クロップ開始", command=self.toggle_crop_mode, 
                                          fg_color="#e67e22", hover_color="#d35400", width=140)
        self.btn_crop_mode.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.btn_crop_exec = ctk.CTkButton(f_crop, text="保存実行", command=self.execute_crop, 
                                          state="disabled", fg_color="#27ae60", hover_color="#219150", width=100)
        self.btn_crop_exec.pack(side=tk.LEFT, pady=10)

        # アノテーションツール
        f_ann = ctk.CTkFrame(f_foot, fg_color="transparent")
        f_ann.pack(fill="x")
        self.btn_here = ctk.CTkButton(f_ann, text="🔴 Here!", command=lambda: self.set_tool("here"), 
                                     state="disabled", width=110, fg_color="#3b8ed0")
        self.btn_here.pack(side=tk.LEFT, padx=2)
        
        self.btn_arrow = ctk.CTkButton(f_ann, text="🏹 矢印", command=lambda: self.set_tool("arrow"), 
                                      state="disabled", width=110, fg_color="#3b8ed0")
        self.btn_arrow.pack(side=tk.LEFT, padx=2)

        # イベントバインド
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        self.canvas.bind("<Button-2>", self.toggle_autoscroll)
        self.bind("<Control-Return>", lambda e: self.save_data())
        self.canvas.bind("<Configure>", lambda e: self.refresh_map())

    def create_input(self, label):
        ctk.CTkLabel(self.scroll_body, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        ent = ctk.CTkEntry(self.scroll_body, height=35)
        ent.pack(fill="x", padx=20, pady=5)
        return ent

    def create_textbox(self, label):
        ctk.CTkLabel(self.scroll_body, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        txt = ctk.CTkTextbox(self.scroll_body, height=100, font=("Meiryo", 12))
        txt.pack(fill="x", padx=20, pady=5)
        return txt

    def get_ratio(self):
        return ((2 ** self.zoom) * 256) / self.orig_max_dim

    def refresh_map(self):
        self.canvas.delete("all")
        r = self.get_ratio()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1: return # ウィンドウサイズ確定まで待機

        z_src = min(int(math.floor(self.zoom)), self.max_zoom)
        s_diff = 2 ** (self.zoom - z_src)
        ts = int(256 * s_diff)
        vl, vt = self.canvas.canvasx(0), self.canvas.canvasy(0)
        
        # タイルレンダリング
        for tx in range(int(vl//ts), int((vl+cw)//ts)+1):
            for ty in range(int(vt//ts), int((vt+ch)//ts)+1):
                path = os.path.join(self.tile_dir, str(z_src), str(tx), f"{ty}.webp")
                if os.path.exists(path):
                    key = f"{path}_{ts}"
                    if key not in self.tile_cache:
                        self.tile_cache[key] = ImageTk.PhotoImage(Image.open(path).resize((ts, ts), Image.Resampling.NEAREST))
                    self.canvas.create_image(tx*ts, ty*ts, anchor="nw", image=self.tile_cache[key])

        # ピン描画
        for d in self.data_list:
            cn = self.cat_mapping.get(d['category'], "")
            if cn in self.filter_vars and not self.filter_vars[cn].get(): continue
            if self.show_incomplete_only.get() and all([d.get('name_jp'), d.get('memo_jp')]): continue
            
            px, py = d['x']*r, d['y']*r
            is_sel = (d['uid'] == self.current_uid)
            self.canvas.create_oval(px-7, py-7, px+7, py+7, fill="#f1c40f" if is_sel else "#e67e22", outline="white", width=2)
            if is_sel:
                self.canvas.create_oval(px-12, py-12, px+12, py+12, outline="#f1c40f", width=2)

        # ターゲット/クロップ関連描画
        if self.is_crop_mode:
            bx, by, bw, bh = self.crop_box["x"]*r, self.crop_box["y"]*r, self.crop_box["w"]*r, self.crop_box["h"]*r
            self.canvas.create_rectangle(bx, by, bx+bw, by+bh, outline="#2ecc71", width=3, dash=(10,5))
            # 拡縮ハンドル
            self.canvas.create_rectangle(bx+bw-12, by+bh-12, bx+bw, by+bh, fill="white", outline="#2ecc71")
            
            if self.here_pos:
                hx, hy = self.here_pos["x"]*r, self.here_pos["y"]*r
                self.canvas.create_oval(hx-20, hy-20, hx+20, hy+20, outline="red", width=5)
                self.canvas.create_text(hx, hy-38, text="HERE", fill="red", font=("Arial Black", 16, "bold"))
            if self.arrow_pos:
                ax, ay = self.arrow_pos["x"]*r, self.arrow_pos["y"]*r
                self.canvas.create_line(ax+50, ay+50, ax+10, ay+10, fill="red", width=8, arrow=tk.LAST, arrowshape=(20,25,10))

        if self.temp_coords and not self.current_uid:
            tx, ty = self.temp_coords[0]*r, self.temp_coords[1]*r
            self.canvas.create_line(tx-15, ty, tx+15, ty, fill="cyan", width=2)
            self.canvas.create_line(tx, ty-15, tx, ty+15, fill="cyan", width=2)
            self.canvas.create_oval(tx-8, ty-8, tx+8, ty+8, outline="cyan", width=2)

        self.canvas.config(scrollregion=(0, 0, self.orig_w*r, self.orig_h*r))

    def on_left_down(self, event):
        r = self.get_ratio()
        mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        cx, cy = mx/r, my/r
        
        if self.is_crop_mode and not self.active_tool:
            b = self.crop_box
            bx, by, bw, bh = b["x"]*r, b["y"]*r, b["w"]*r, b["h"]*r
            # ハンドル判定
            if (bx+bw-20 <= mx <= bx+bw+5) and (by+bh-20 <= my <= by+bh+5):
                self.drag_mode = "resize_br"
                return
            # 枠内移動判定
            elif (b["x"] <= cx <= b["x"]+b["w"]) and (b["y"] <= cy <= b["y"]+b["h"]):
                self.drag_mode = "move"
                self.drag_offset = (cx - b["x"], cy - b["y"])
                return

        self.drag_start = (event.x, event.y)
        self.has_dragged = False
        self.canvas.scan_mark(event.x, event.y)

    def on_left_drag(self, event):
        r = self.get_ratio()
        cx, cy = self.canvas.canvasx(event.x)/r, self.canvas.canvasy(event.y)/r
        
        if self.drag_mode == "move":
            self.crop_box["x"], self.crop_box["y"] = cx - self.drag_offset[0], cy - self.drag_offset[1]
            self.refresh_map(); return
        elif self.drag_mode == "resize_br":
            new_w = max(160, cx - self.crop_box["x"])
            # 16:9 比率固定
            self.crop_box["w"], self.crop_box["h"] = new_w, new_w * (9/16)
            self.refresh_map(); return

        if abs(event.x - self.drag_start[0]) > 5 or abs(event.y - self.drag_start[1]) > 5:
            self.has_dragged = True
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.refresh_map()

    def on_left_up(self, event):
        if self.drag_mode: self.drag_mode = None; return
        if not self.has_dragged:
            r = self.get_ratio()
            cx, cy = self.canvas.canvasx(event.x)/r, self.canvas.canvasy(event.y)/r
            
            if self.is_crop_mode and self.active_tool:
                if self.active_tool == "here": self.here_pos = {"x": cx, "y": cy}
                if self.active_tool == "arrow": self.arrow_pos = {"x": cx, "y": cy}
                self.refresh_map(); return

            for d in self.data_list:
                if abs(d['x']-cx)<(16/r) and abs(d['y']-cy)<(16/r):
                    self.current_uid = d['uid']; self.load_to_ui(d); self.refresh_map(); return
            
            self.current_uid, self.temp_coords = None, (cx, cy)
            self.lbl_coords.configure(text=f"座標: ({int(cx)}, {int(cy)})")
            self.refresh_map()

    def on_zoom(self, event):
        old_r, mx, my = self.get_ratio(), self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.zoom = max(0, min(self.zoom + (0.2 if event.delta > 0 else -0.2), float(self.max_zoom) + 2.5))
        self.refresh_map()
        new_r = self.get_ratio()
        f = new_r / old_r
        self.canvas.xview_moveto((mx*f - event.x)/(self.orig_max_dim * new_r))
        self.canvas.yview_moveto((my*f - event.y)/(self.orig_max_dim * new_r))

    def toggle_crop_mode(self):
        self.is_crop_mode = not self.is_crop_mode
        self.active_tool = self.drag_mode = None
        st = "normal" if self.is_crop_mode else "disabled"
        self.btn_crop_exec.configure(state=st)
        self.btn_here.configure(state=st, fg_color="#3b8ed0")
        self.btn_arrow.configure(state=st, fg_color="#3b8ed0")
        self.btn_crop_mode.configure(text="✂ クロップ終了" if self.is_crop_mode else "✂ クロップ開始")
        if not self.is_crop_mode: self.here_pos = self.arrow_pos = None
        self.refresh_map()

    def set_tool(self, t):
        if self.active_tool == t:
            self.active_tool = None
            if t == "here": self.here_pos = None
            if t == "arrow": self.arrow_pos = None
        else:
            if t == "here" and self.here_pos: self.here_pos = None; self.active_tool = None
            elif t == "arrow" and self.arrow_pos: self.arrow_pos = None; self.active_tool = None
            else: self.active_tool = t
        self.btn_here.configure(fg_color="#e74c3c" if self.active_tool=="here" else "#3b8ed0")
        self.btn_arrow.configure(fg_color="#e74c3c" if self.active_tool=="arrow" else "#3b8ed0")
        self.refresh_map()

    def execute_crop(self):
        # 1. 保存先フォルダの準備
        save_dir = os.path.join(self.game_path, "screenshots")
        os.makedirs(save_dir, exist_ok=True)
        
        # 2. ファイル名の生成 (日時)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(save_dir, f"crop_{timestamp}.png")
        
        try:
            # 3. 元画像を開く
            map_full_path = os.path.join(self.game_path, self.config.get("map_file", "map.png"))
            if not os.path.exists(map_full_path):
                messagebox.showerror("エラー", "元画像が見つかりません。")
                return
            
            with Image.open(map_full_path).convert("RGB") as full_img:
                # 4. クロップ範囲の計算
                b = self.crop_box
                left = max(0, int(b["x"]))
                top = max(0, int(b["y"]))
                right = min(self.orig_w, int(left + b["w"]))
                bottom = min(self.orig_h, int(top + b["h"]))
                
                # 切り抜き実行
                cropped_img = full_img.crop((left, top, right, bottom))
                
                # 5. アノテーション合成
                draw = ImageDraw.Draw(cropped_img)
                
                # HERE マーカー
                if self.here_pos:
                    hx = self.here_pos["x"] - left
                    hy = self.here_pos["y"] - top
                    draw.ellipse([hx-20, hy-20, hx+20, hy+20], outline="red", width=6)
                    draw.text((hx-15, hy-40), "HERE", fill="red")
                
                # 矢印マーカー
                if self.arrow_pos:
                    ax = self.arrow_pos["x"] - left
                    ay = self.arrow_pos["y"] - top
                    draw.line([ax+50, ay+50, ax+8, ay+8], fill="red", width=10)
                    draw.polygon([ax+5, ay+5, ax+25, ay+5, ax+5, ay+25], fill="red")

                # 6. 保存
                cropped_img.save(save_path, "PNG")
            
            messagebox.showinfo("成功", f"画像を保存しました！\n場所: {save_path}")
            os.startfile(save_dir)
            
        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました: {e}")
        
        self.toggle_crop_mode()

    def save_data(self):
        n_jp = self.ent_name_jp.get()
        if not n_jp and not self.current_uid: return
        rev_map = {v: k for k, v in self.cat_mapping.items()}
        dr = {
            'uid': self.current_uid or f"p_{int(datetime.now().timestamp())}",
            'x': self.temp_coords[0] if not self.current_uid else None,
            'y': self.temp_coords[1] if not self.current_uid else None,
            'name_jp': n_jp,
            'name_en': self.ent_name_en.get(),
            'category': rev_map.get(self.cmb_cat.get(), "MISC_OTHER"),
            'importance': self.cmb_imp.get(),
            'memo_jp': self.txt_memo_jp.get("1.0", "end-1c"),
            'memo_en': self.txt_memo_en.get("1.0", "end-1c")
        }
        if self.current_uid:
            for d in self.data_list:
                if d['uid'] == self.current_uid: d.update({k:v for k,v in dr.items() if v is not None})
        else:
            self.data_list.append(dr)
        self.write_files()
        self.current_uid = self.temp_coords = None
        self.refresh_map()
        self.clear_ui()

    def write_files(self):
        p = os.path.join(self.game_path, self.config["save_file"])
        flds = ["uid", "x", "y", "name_jp", "name_en", "category", "importance", "memo_jp", "memo_en"]
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=flds, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.data_list)

    def load_csv(self):
        p = os.path.join(self.game_path, self.config["save_file"])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8-sig") as f:
                self.data_list = [dict(row, x=float(row['x']), y=float(row['y'])) for row in csv.DictReader(f)]

    def load_to_ui(self, d):
        self.clear_ui()
        self.ent_name_jp.insert(0, d.get('name_jp',''))
        self.ent_name_en.insert(0, d.get('name_en',''))
        self.cmb_cat.set(self.cat_mapping.get(d.get('category',''), ""))
        self.cmb_imp.set(d.get('importance','1'))
        self.txt_memo_jp.insert("1.0", d.get('memo_jp',''))
        self.txt_memo_en.insert("1.0", d.get('memo_en',''))

    def clear_ui(self):
        self.ent_name_jp.delete(0, tk.END)
        self.ent_name_en.delete(0, tk.END)
        self.txt_memo_jp.delete("1.0", tk.END)
        self.txt_memo_en.delete("1.0", tk.END)

    def toggle_autoscroll(self, event):
        self.is_autoscrolling = not self.is_autoscrolling
        self.autoscroll_origin = (event.x, event.y)
        
    def run_autoscroll_loop(self):
        if self.is_autoscrolling:
            mx, my = self.winfo_pointerx()-self.winfo_rootx(), self.winfo_pointery()-self.winfo_rooty()
            dx, dy = (mx-self.autoscroll_origin[0]), (my-self.autoscroll_origin[1])
            if abs(dx)>20 or abs(dy)>20:
                self.canvas.xview_scroll(int(dx/35), "units")
                self.canvas.yview_scroll(int(dy/35), "units")
                self.refresh_map()
        self.after(10, self.run_autoscroll_loop)

    def on_close(self):
        self.destroy()
        self.master.deiconify()

# ==========================================
# 4. メイン実行
# ==========================================
if __name__ == "__main__":
    app = Portal()
    app.mainloop()