import os
import math
import shutil
from PIL import Image, ImageDraw
from datetime import datetime

def create_tiles_from_image(src_img_path, target_dir):
    """
    元画像からタイル画像を生成し、config.jsonの雛形を作成する
    """
    img = Image.open(src_img_path).convert('RGB')
    w, h = img.size
    max_dim = max(w, h)
    
    # 元画像のバックアップ保存
    shutil.copy(src_img_path, os.path.join(target_dir, "map.png"))
    
    # 正方形の台紙を用意
    square_bg = Image.new('RGB', (max_dim, max_dim), (0, 0, 0))
    square_bg.paste(img, (0, 0))
    
    max_zoom = math.ceil(math.log(max_dim / 256, 2))
    tile_dir = os.path.join(target_dir, "tiles")

    # タイル生成ループ
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
    """
    指定範囲を切り抜き、アノテーションを合成して保存する
    """
    save_dir = os.path.join(game_path, "screenshots")
    os.makedirs(save_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(save_dir, f"crop_{timestamp}.png")
    
    map_full_path = os.path.join(game_path, map_file)
    
    if not os.path.exists(map_full_path):
        raise FileNotFoundError("元画像(map.png)が見つかりません")

    with Image.open(map_full_path).convert("RGB") as full_img:
        # クロップ範囲の計算
        left = max(0, int(crop_box["x"]))
        top = max(0, int(crop_box["y"]))
        # 範囲外にはみ出さないように制限
        right = min(orig_w, int(left + crop_box["w"]))
        bottom = min(orig_h, int(top + crop_box["h"]))
        
        # 切り抜き
        cropped = full_img.crop((left, top, right, bottom))
        draw = ImageDraw.Draw(cropped)
        
        # HEREマーカーの合成
        if here_pos:
            # 切り抜いた画像内での相対座標に変換
            hx = here_pos["x"] - left
            hy = here_pos["y"] - top
            draw.ellipse([hx-20, hy-20, hx+20, hy+20], outline="red", width=6)
            # 簡易テキスト描画 (フォント指定なしでも動くように)
            # より高度にするならここでImageFontを使いますが、まずはデフォルトで
            draw.text((hx-15, hy-40), "HERE", fill="red")
        
        # 矢印マーカーの合成
        if arrow_pos:
            ax = arrow_pos["x"] - left
            ay = arrow_pos["y"] - top
            # 線
            draw.line([ax+50, ay+50, ax+10, ay+10], fill="red", width=10)
            # 三角形（矢印の先）
            # 座標計算は簡易版ですが、エディタ上の見た目と合わせる
            draw.polygon([ax+5, ay+5, ax+25, ay+5, ax+5, ay+25], fill="red")
            
        cropped.save(save_path, "PNG")
        
    return save_path, save_dir