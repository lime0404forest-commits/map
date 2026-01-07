import os
import math
import shutil
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def create_tiles_from_image(src_img_path, target_dir):
    img = Image.open(src_img_path).convert('RGB')
    w, h = img.size
    max_dim = max(w, h)
    shutil.copy(src_img_path, os.path.join(target_dir, "map.png"))
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
                p = os.path.join(tile_dir, str(zoom), str(x))
                os.makedirs(p, exist_ok=True)
                tile = resized.crop((x * 256, y * 256, (x + 1) * 256, (y + 1) * 256))
                tile.save(os.path.join(p, f"{y}.webp"), "WEBP", quality=80)
    return w, h

def save_cropped_image_with_annotations(game_path, map_file, crop_box, orig_w, orig_h, here_pos, arrow_pos):
    save_dir = os.path.join(game_path, "screenshots")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(save_dir, f"crop_{timestamp}.png")
    map_full_path = os.path.join(game_path, map_file)
    
    if not os.path.exists(map_full_path):
        raise FileNotFoundError("元画像が見つかりません")

    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font = ImageFont.load_default()

    with Image.open(map_full_path).convert("RGB") as full_img:
        left, top = max(0, int(crop_box["x"])), max(0, int(crop_box["y"]))
        right = min(orig_w, int(left + crop_box["w"]))
        bottom = min(orig_h, int(top + crop_box["h"]))
        cropped = full_img.crop((left, top, right, bottom))
        draw = ImageDraw.Draw(cropped)
        
        # --- HEREマーカー (細い縁取りですっきり) ---
        if here_pos:
            hx, hy = here_pos["x"] - left, here_pos["y"] - top
            
            # 半径の差を2pxにして、細い縁取りにする
            r_in = 18  # 赤
            r_out = 20 # 白 (18+2)
            
            draw.ellipse([hx-r_out, hy-r_out, hx+r_out, hy+r_out], outline="white", width=4) # 実際には塗りつぶされるので枠として機能
            draw.ellipse([hx-r_in, hy-r_in, hx+r_in, hy+r_in], outline="#e74c3c", width=4)
            
            # 文字の縁取りも細く (stroke_width=2)
            draw.text((hx, hy-30), "HERE", font=font, fill="#e74c3c", stroke_width=2, stroke_fill="white", anchor="md")
        
        # --- 矢印マーカー (細い縁取りですっきり) ---
        if arrow_pos:
            ax, ay = arrow_pos["x"] - left, arrow_pos["y"] - top
            
            start = (ax + 70, ay + 70)
            end   = (ax + 15, ay + 15)
            
            # 棒: 赤12pxに対し、白16px (片側2pxの縁)
            draw.line([start, end], fill="white", width=16)
            draw.line([start, end], fill="#e74c3c", width=12)
            
            # 三角形
            # 白（外枠）: 赤よりわずかに大きく
            draw.polygon([
                (ax + 2, ay + 2),    # 先端
                (ax + 40, ay + 10),  # 右翼
                (ax + 10, ay + 40)   # 左翼
            ], fill="white")
            
            # 赤（中身）
            draw.polygon([
                (ax + 5, ay + 5),    # 先端
                (ax + 35, ay + 12),  # 右翼
                (ax + 12, ay + 35)   # 左翼
            ], fill="#e74c3c")
            
        cropped.save(save_path, "PNG")
        
    return save_path, save_dir