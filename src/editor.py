import tkinter as tk
import customtkinter as ctk
import os
import json
import csv
import math
from datetime import datetime
from PIL import Image, ImageTk
from tkinter import messagebox
from .constants import GAMES_ROOT
from .utils import save_cropped_image_with_annotations

class MapEditor(ctk.CTkToplevel):
    def __init__(self, master, game_name, region_name):
        super().__init__(master)
        self.game_path = os.path.join(GAMES_ROOT, game_name, region_name)
        self.tile_dir = os.path.join(self.game_path, "tiles")
        
        # 設定ロードと自動修復
        config_p = os.path.join(self.game_path, "config.json")
        with open(config_p, "r", encoding="utf-8") as f: self.config = json.load(f)
        
        if "orig_w" not in self.config:
            m_path = os.path.join(self.game_path, self.config.get("map_file", "map.png"))
            if os.path.exists(m_path):
                with Image.open(m_path) as tmp: self.config["orig_w"], self.config["orig_h"] = tmp.size
                with open(config_p, "w", encoding="utf-8") as f: json.dump(self.config, f, indent=4, ensure_ascii=False)

        self.orig_w = self.config["orig_w"]
        self.orig_h = self.config["orig_h"]
        self.orig_max_dim = max(self.orig_w, self.orig_h)
        
        zooms = [int(d) for d in os.listdir(self.tile_dir) if d.isdigit()]
        self.max_zoom = max(zooms) if zooms else 0
        self.zoom = float(self.max_zoom) - 0.5
        
        self.title(f"Editor - {game_name} ({region_name})")
        self.geometry("1650x950")
        
        # 内部変数
        self.data_list = []
        self.current_uid = None
        self.temp_coords = None
        self.is_autoscrolling = False
        self.tile_cache = {}
        
        # クロップ/アノテーション関連
        self.is_crop_mode = False
        self.crop_box = {"x": 100, "y": 100, "w": 640, "h": 360}
        self.drag_mode = None
        self.active_tool = None
        self.here_pos = None
        self.arrow_pos = None

        self.setup_ui()
        self.load_csv()
        
        # 起動時の描画安定化
        self.update_idletasks()
        self.after(100, self.refresh_map)
        
        self.run_autoscroll_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        
        self.sidebar = ctk.CTkFrame(self, width=450, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # 座標表示
        f_top = ctk.CTkFrame(self.sidebar, fg_color="#34495e", corner_radius=0)
        f_top.pack(fill="x")
        self.lbl_coords = ctk.CTkLabel(f_top, text="座標: ---", font=("Meiryo", 16, "bold"))
        self.lbl_coords.pack(pady=15)
        
        self.scroll_body = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_body.pack(expand=True, fill="both", padx=10, pady=10)
        
        # フィルタ
        ctk.CTkLabel(self.scroll_body, text="表示フィルタ", font=("Meiryo", 13, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        f_filter = ctk.CTkFrame(self.scroll_body, fg_color="#161616")
        f_filter.pack(fill="x", padx=10, pady=5)
        
        self.cat_mapping = self.config.get("cat_mapping", {})
        self.display_names = [v for v in self.cat_mapping.values() if v.strip()]
        self.filter_vars = {n: tk.BooleanVar(value=True) for n in self.display_names}
        self.show_incomplete_only = tk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(f_filter, text="⚠️ 未完成のみ", variable=self.show_incomplete_only, command=self.refresh_map, text_color="#e74c3c").pack(anchor="w", padx=15, pady=8)
        for n in self.display_names:
            ctk.CTkCheckBox(f_filter, text=n, variable=self.filter_vars[n], command=self.refresh_map).pack(anchor="w", padx=15, pady=3)

        # フォーム
        self.ent_name_jp = self.create_input("▼ 日本語名")
        self.ent_name_en = self.create_input("▼ 英語名")
        ctk.CTkLabel(self.scroll_body, text="▼ カテゴリ").pack(anchor="w", padx=20, pady=(10,0))
        self.cmb_cat = ctk.CTkComboBox(self.scroll_body, values=self.display_names)
        self.cmb_cat.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self.scroll_body, text="▼ 重要度 (1-5)").pack(anchor="w", padx=20, pady=(5,0))
        self.cmb_imp = ctk.CTkComboBox(self.scroll_body, values=["1","2","3","4","5"])
        self.cmb_imp.set("1")
        self.cmb_imp.pack(fill="x", padx=20, pady=5)
        self.txt_memo_jp = self.create_textbox("▼ 詳細メモ (日本語)")
        self.txt_memo_en = self.create_textbox("▼ Memo (English)")

        # ボタン類
        f_foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_foot.pack(fill="x", side=tk.BOTTOM, padx=20, pady=20)
        ctk.CTkButton(f_foot, text="ピン保存 (Ctrl+Enter)", command=self.save_data, fg_color="#2980b9", height=50, font=("Meiryo", 14, "bold")).pack(fill="x", pady=5)
        
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

        # バインド
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
        txt = ctk.CTkTextbox(self.scroll_body, height=100)
        txt.pack(fill="x", padx=20, pady=5)
        return txt

    def get_ratio(self):
        return ((2 ** self.zoom) * 256) / self.orig_max_dim

    def refresh_map(self):
        self.canvas.delete("all")
        r = self.get_ratio()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1: return

        z_src = min(int(math.floor(self.zoom)), self.max_zoom)
        s_diff = 2 ** (self.zoom - z_src)
        ts = int(256 * s_diff)
        vl, vt = self.canvas.canvasx(0), self.canvas.canvasy(0)
        
        for tx in range(int(vl//ts), int((vl+cw)//ts)+1):
            for ty in range(int(vt//ts), int((vt+ch)//ts)+1):
                path = os.path.join(self.tile_dir, str(z_src), str(tx), f"{ty}.webp")
                if os.path.exists(path):
                    key = f"{path}_{ts}"
                    if key not in self.tile_cache:
                        self.tile_cache[key] = ImageTk.PhotoImage(Image.open(path).resize((ts, ts), Image.Resampling.NEAREST))
                    self.canvas.create_image(tx*ts, ty*ts, anchor="nw", image=self.tile_cache[key])

        for d in self.data_list:
            cn = self.cat_mapping.get(d['category'], "")
            if cn in self.filter_vars and not self.filter_vars[cn].get(): continue
            px, py = d['x']*r, d['y']*r
            self.canvas.create_oval(px-6, py-6, px+6, py+6, fill="#f1c40f" if (d['uid']==self.current_uid) else "#e67e22", outline="white", width=2)

        if self.is_crop_mode:
            bx, by, bw, bh = self.crop_box["x"]*r, self.crop_box["y"]*r, self.crop_box["w"]*r, self.crop_box["h"]*r
            self.canvas.create_rectangle(bx, by, bx+bw, by+bh, outline="#2ecc71", width=3, dash=(10,5))
            self.canvas.create_rectangle(bx+bw-12, by+bh-12, bx+bw, by+bh, fill="white", outline="#2ecc71")
            
            if self.here_pos:
                hx, hy = self.here_pos["x"]*r, self.here_pos["y"]*r
                self.canvas.create_oval(hx-20, hy-20, hx+20, hy+20, outline="red", width=5)
                self.canvas.create_text(hx, hy-38, text="HERE", fill="red", font=("Arial Black", 16, "bold"))
            if self.arrow_pos:
                ax, ay = self.arrow_pos["x"]*r, self.arrow_pos["y"]*r
                self.canvas.create_line(ax+50, ay+50, ax+10, ay+10, fill="red", width=8, arrow=tk.LAST, arrowshape=(20,25,10))

        self.canvas.config(scrollregion=(0, 0, self.orig_w*r, self.orig_h*r))

    def on_left_down(self, event):
        r = self.get_ratio()
        mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        cx, cy = mx/r, my/r
        
        if self.is_crop_mode and not self.active_tool:
            b = self.crop_box
            bx, by, bw, bh = b["x"]*r, b["y"]*r, b["w"]*r, b["h"]*r
            if (bx+bw-20 <= mx <= bx+bw+5) and (by+bh-20 <= my <= by+bh+5):
                self.drag_mode = "resize_br"
                return
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
            self.crop_box["w"], self.crop_box["h"] = new_w, new_w * (9/16)
            self.refresh_map(); return

        if abs(event.x - self.drag_start[0]) > 5:
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
                elif self.active_tool == "arrow": self.arrow_pos = {"x": cx, "y": cy}
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
        self.active_tool = None
        st = "normal" if self.is_crop_mode else "disabled"
        self.btn_crop_exec.configure(state=st)
        self.btn_here.configure(state=st, fg_color="#3b8ed0")
        self.btn_arrow.configure(state=st, fg_color="#3b8ed0")
        self.btn_crop_mode.configure(text="✂ 終了" if self.is_crop_mode else "✂ クロップ開始")
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
        # 委譲した処理を呼び出す
        try:
            path, sdir = save_cropped_image_with_annotations(
                self.game_path, 
                self.config.get("map_file", "map.png"),
                self.crop_box, self.orig_w, self.orig_h, 
                self.here_pos, self.arrow_pos
            )
            messagebox.showinfo("成功", f"保存完了: {path}")
            os.startfile(sdir)
        except Exception as e:
            messagebox.showerror("エラー", str(e))
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