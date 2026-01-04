import os
import math
from PIL import Image

# ==========================================
# 【軽量化設定エリア】
# ==========================================
INPUT_IMAGE = "vein_map.jpg"  # あなたの元画像
OUTPUT_DIR = "tiles_webp"          # 出力先フォルダ名を変えました
TILE_SIZE = 256

# 画質設定 (0-100)
# 80くらいが「見た目キレイ」と「軽さ」のバランスが良いです
QUALITY = 80 
# ==========================================

Image.MAX_IMAGE_PIXELS = None

def generate_tiles():
    print("軽量化処理を開始します...")

    try:
        img = Image.open(INPUT_IMAGE)
    except FileNotFoundError:
        print("画像が見つかりません。")
        return

    width, height = img.size
    
    # ★ここ重要: WebPやJPGにする場合、透明情報(Alpha)があるとエラーになることがあるので
    # 背景を黒(または白)で塗りつぶしてRGBモードに変換します
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (25, 25, 25)) # 背景色(VEINっぽい黒)
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    max_dimension = max(width, height)
    max_zoom = math.ceil(math.log(max_dimension / TILE_SIZE, 2))

    for zoom in range(max_zoom, -1, -1):
        print(f"Zoom Level {zoom}...", end="", flush=True)
        
        num_tiles = 2 ** zoom
        current_canvas_size = num_tiles * TILE_SIZE
        
        # 高速化のため、リサイズ方式を少し軽いもの(BILINEAR)に変更してもOK
        # 画質優先なら LANCZOS のままで
        resized_img = img.resize((current_canvas_size, current_canvas_size), Image.Resampling.LANCZOS)
        
        for x in range(num_tiles):
            for y in range(num_tiles):
                left = x * TILE_SIZE
                upper = y * TILE_SIZE
                right = left + TILE_SIZE
                lower = upper + TILE_SIZE
                
                tile = resized_img.crop((left, upper, right, lower))
                
                save_dir = os.path.join(OUTPUT_DIR, str(zoom), str(x))
                os.makedirs(save_dir, exist_ok=True)
                
                # ★変更点: 拡張子を .webp にし、qualityオプションを追加
                save_path = os.path.join(save_dir, f"{y}.webp")
                tile.save(save_path, "WEBP", quality=QUALITY)
        
        print(" 完了")

    print(f"完了！ '{OUTPUT_DIR}' フォルダを確認してください。")

if __name__ == "__main__":
    generate_tiles()