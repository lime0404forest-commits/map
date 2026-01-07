import os
import math
import shutil
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def create_tiles_from_image(src_img_path, target_dir):
    """
    画像を読み込み、正方形の台紙の左上に貼り付けてからタイル化する。
    （画像を無理やり引き伸ばさず、余白を黒で埋めることで座標ズレを防ぐ）
    """
    img = Image.open(src_img_path).convert('RGB')
    original_w, original_h = img.size
    
    # 元画像をそのままコピー（config生成などで使うため）
    shutil.copy(src_img_path, os.path.join(target_dir, "map.png"))
    
    # 1. 必要なキャンバスサイズ（2の累乗）を計算
    # 例: 3155pxなら -> 4096pxの台紙が必要
    max_dim = max(original_w, original_h)
    max_zoom = math.ceil(math.log(max_dim / 256, 2))
    canvas_size = (2 ** max_zoom) * 256
    
    # 2. 黒い背景を作成し、元画像を「左上(0,0)」に貼り付ける
    # ★修正点: 最初から4096pxの台紙を作り、そこに画像を置く（拡大しない）
    base_image = Image.new('RGB', (canvas_size, canvas_size), (0, 0, 0))
    base_image.paste(img, (0, 0))
    
    tile_dir = os.path.join(target_dir, "tiles")
    
    # 3. ズームレベルごとに縮小してタイル分割
    for zoom in range(max_zoom, -1, -1):
        # このズームレベルでの一辺のピクセル数
        num_tiles = 2 ** zoom
        current_dim = num_tiles * 256
        
        # 台紙全体をリサイズ
        # MaxZoomのときはリサイズ不要（base_imageそのまま）
        if zoom == max_zoom:
            resized_img = base_image
        else:
            resized_img = base_image.resize((current_dim, current_dim), Image.Resampling.LANCZOS)
        
        # フォルダ作成 & 切り出し
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
                
                # 保存（webp）
                tile.save(os.path.join(x_dir, f"{y}.webp"), "WEBP", quality=80)
        
        print(f"Zoom level {zoom} generated.")

    return original_w, original_h

def save_cropped_image_with_annotations(game_path, map_file, crop_box, orig_w, orig_h, here_pos, arrow_pos):
    """
    指定範囲をクロップし、注釈（HEREピンや矢印）を描画して保存する
    """
    save_dir = os.path.join(game_path, "screenshots")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(save_dir, f"crop_{timestamp}.png")
    map_full_path = os.path.join(game_path, map_file)
    
    if not os.path.exists(map_full_path):
        raise FileNotFoundError("元画像が見つかりません")

    try:
        # フォント読み込み（Windows標準のArialなどを想定）
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font = ImageFont.load_default()

    with Image.open(map_full_path).convert("RGB") as full_img:
        # クロップ範囲の計算
        left, top = max(0, int(crop_box["x"])), max(0, int(crop_box["y"]))
        right = min(orig_w, int(left + crop_box["w"]))
        bottom = min(orig_h, int(top + crop_box["h"]))
        
        cropped = full_img.crop((left, top, right, bottom))
        draw = ImageDraw.Draw(cropped)
        
        # --- HEREマーカー ---
        if here_pos:
            hx, hy = here_pos["x"] - left, here_pos["y"] - top
            r_in = 18   # 赤
            r_out = 20  # 白枠
            
            draw.ellipse([hx-r_out, hy-r_out, hx+r_out, hy+r_out], outline="white", width=4)
            draw.ellipse([hx-r_in, hy-r_in, hx+r_in, hy+r_in], outline="#e74c3c", width=4)
            # 文字
            draw.text((hx, hy-30), "HERE", font=font, fill="#e74c3c", stroke_width=2, stroke_fill="white", anchor="md")
        
        # --- 矢印マーカー ---
        if arrow_pos:
            ax, ay = arrow_pos["x"] - left, arrow_pos["y"] - top
            start = (ax + 70, ay + 70)
            end   = (ax + 15, ay + 15)
            
            # 棒
            draw.line([start, end], fill="white", width=16)
            draw.line([start, end], fill="#e74c3c", width=12)
            
            # 三角形（白枠）
            draw.polygon([
                (ax + 2, ay + 2),    # 先端
                (ax + 40, ay + 10),  # 右翼
                (ax + 10, ay + 40)   # 左翼
            ], fill="white")
            
            # 三角形（赤中身）
            draw.polygon([
                (ax + 5, ay + 5),    # 先端
                (ax + 35, ay + 12),  # 右翼
                (ax + 12, ay + 35)   # 左翼
            ], fill="#e74c3c")
            
        cropped.save(save_path, "PNG")
        
    return save_path, save_dir