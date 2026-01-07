import os
import math
import shutil
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def create_tiles_from_image(src_img_path, target_dir):
    """
    画像を読み込み、正方形の台紙の左上に貼り付けてからタイル化する。
    また、タイル画像がGit管理対象にならないよう .gitignore を自動生成する。
    """
    img = Image.open(src_img_path).convert('RGB')
    original_w, original_h = img.size
    
    # 元画像をそのままコピー（config生成やエディタでの読み込みに使用）
    shutil.copy(src_img_path, os.path.join(target_dir, "map.png"))
    
    # 1. 必要なキャンバスサイズ（2の累乗）を計算
    max_dim = max(original_w, original_h)
    max_zoom = math.ceil(math.log(max_dim / 256, 2))
    canvas_size = (2 ** max_zoom) * 256
    
    print(f"--- タイル生成開始 ---")
    print(f"元サイズ: {original_w}x{original_h} -> 台紙サイズ: {canvas_size}x{canvas_size} (MaxZoom: {max_zoom})")

    # 2. 黒い背景を作成し、元画像を「左上(0,0)」に貼り付ける
    base_image = Image.new('RGB', (canvas_size, canvas_size), (0, 0, 0))
    base_image.paste(img, (0, 0)) 
    
    tile_dir = os.path.join(target_dir, "tiles")
    
    # ★修正箇所: ファイルを書き込む前にディレクトリを作成する
    os.makedirs(tile_dir, exist_ok=True) 

    # --- .gitignore の生成 ---
    gitignore_path = os.path.join(tile_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("# Ignore all tiles in this directory\n")
            f.write("*\n")
            f.write("!.gitignore\n")
        print(f"Notice: .gitignore generated in {tile_dir}")

    # 3. ズームレベルごとに縮小してタイル分割
    for zoom in range(max_zoom, -1, -1):
        num_tiles = 2 ** zoom
        current_dim = num_tiles * 256
        
        # リサイズ（高品質なLANCZOSフィルタを使用）
        if zoom == max_zoom:
            resized_img = base_image
        else:
            resized_img = base_image.resize((current_dim, current_dim), Image.Resampling.LANCZOS)
        
        z_dir = os.path.join(tile_dir, str(zoom))
        os.makedirs(z_dir, exist_ok=True)
        
        for x in range(num_tiles):
            x_dir = os.path.join(z_dir, str(x))
            os.makedirs(x_dir, exist_ok=True)
            
            for y in range(num_tiles):
                box = (
                    x * 256, 
                    y * 256, 
                    (x + 1) * 256, 
                    (y + 1) * 256
                )
                tile = resized_img.crop(box)
                # 保存（webp形式）
                tile.save(os.path.join(x_dir, f"{y}.webp"), "WEBP", quality=80)
        
        print(f"Zoom level {zoom} 完了")

    print(f"--- すべてのタイル生成が完了しました ---")
    return original_w, original_h

def save_cropped_image_with_annotations(game_path, map_file, crop_box, orig_w, orig_h, here_pos, arrow_pos):
    """
    指定範囲をクロップし、注釈を描画して保存する
    """
    save_dir = os.path.join(game_path, "screenshots")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(save_dir, f"crop_{timestamp}.png")
    map_full_path = os.path.join(game_path, map_file)
    
    if not os.path.exists(map_full_path):
        raise FileNotFoundError(f"元画像が見つかりません: {map_full_path}")

    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font = ImageFont.load_default()

    with Image.open(map_full_path).convert("RGB") as full_img:
        left = max(0, int(crop_box["x"]))
        top = max(0, int(crop_box["y"]))
        right = min(orig_w, int(left + crop_box["w"]))
        bottom = min(orig_h, int(top + crop_box["h"]))
        
        cropped = full_img.crop((left, top, right, bottom))
        draw = ImageDraw.Draw(cropped)
        
        if here_pos:
            hx, hy = here_pos["x"] - left, here_pos["y"] - top
            r_in, r_out = 18, 20
            draw.ellipse([hx-r_out, hy-r_out, hx+r_out, hy+r_out], outline="white", width=4)
            draw.ellipse([hx-r_in, hy-r_in, hx+r_in, hy+r_in], outline="#e74c3c", width=4)
            draw.text((hx, hy-30), "HERE", font=font, fill="#e74c3c", stroke_width=2, stroke_fill="white", anchor="md")
        
        if arrow_pos:
            ax, ay = arrow_pos["x"] - left, arrow_pos["y"] - top
            start, end = (ax + 70, ay + 70), (ax + 15, ay + 15)
            draw.line([start, end], fill="white", width=16)
            draw.line([start, end], fill="#e74c3c", width=12)
            draw.polygon([(ax + 2, ay + 2), (ax + 40, ay + 10), (ax + 10, ay + 40)], fill="white")
            draw.polygon([(ax + 5, ay + 5), (ax + 35, ay + 12), (ax + 12, ay + 35)], fill="#e74c3c")
            
        cropped.save(save_path, "PNG")
        
    return save_path, save_dir