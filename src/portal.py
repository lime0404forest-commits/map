import os
import json
import shutil
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from .constants import GAMES_ROOT
from .editor import MapEditor
from .utils import create_tiles_from_image

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
        name = filedialog.askstring("新規登録", "ゲームタイトルを入力")
        if name:
            os.makedirs(os.path.join(GAMES_ROOT, name), exist_ok=True)
            self.setup_main_ui()

    def setup_new_region(self):
        reg_name = filedialog.askstring("新規マップ", "地域名 (例: Valley)")
        if not reg_name: return
        img_path = filedialog.askopenfilename(title="地図画像を選択")
        if not img_path: return
        
        target_dir = os.path.join(GAMES_ROOT, self.current_game, reg_name)
        os.makedirs(target_dir, exist_ok=True)
        
        self.process_new_map(img_path, target_dir)
        self.show_regions(self.current_game)

    def process_new_map(self, src_img, target_dir):
        popup = ctk.CTkToplevel(self)
        popup.geometry("300x150")
        popup.attributes("-topmost", True)
        ctk.CTkLabel(popup, text="タイル化を実行中...\n完了までお待ちください", font=("Meiryo", 14)).pack(expand=True)
        self.update()

        try:
            # Utilsの関数を呼び出し
            w, h = create_tiles_from_image(src_img, target_dir)
            
            # 設定ファイルの保存
            config = {
                "orig_w": w, "orig_h": h,
                "map_file": "map.png",
                "save_file": "master_data.csv",
                "cat_mapping": {"LOC_BASE":"拠点", "RES_MINERAL":"鉱物", "LOC_POI":"ランドマーク"}
            }
            with open(os.path.join(target_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
            messagebox.showinfo("完了", "タイル化が完了しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"失敗しました: {e}")
        finally:
            popup.destroy()

    def launch_editor(self, game, region):
        self.withdraw()
        MapEditor(self, game, region)