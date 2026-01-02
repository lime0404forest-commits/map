import os
import math
from PIL import Image

# ==========================================
# 【設定エリア】ここだけ書き換えてください
# ==========================================
# 1. あなたが作った「巨大な地図画像」のファイル名
# (拡張子 .jpg .png なども正確に書いてください)
INPUT_IMAGE = "VEIN_MAP.jpg" 

# 2. 出力先のフォルダ名（このままでOK）
OUTPUT_DIR = "tiles"

# 3. タイルのサイズ（基本256でOK）
TILE_SIZE = 256
# ==========================================

# 巨大画像の読み込み制限を解除（これがないとエラーになる場合があります）
Image.MAX_IMAGE_PIXELS = None

def generate_tiles():
    print("処理を開始します...")

    # 画像を開く
    try:
        img = Image.open(INPUT_IMAGE)
    except FileNotFoundError:
        print(f"エラー: '{INPUT_IMAGE}' が見つかりません。")
        print("画像ファイル名が正しいか、同じフォルダにあるか確認してください。")
        return

    width, height = img.size
    print(f"元画像のサイズ: {width} x {height}")

    # 最大ズームレベルを計算
    # (画像全体が256pxのタイル1枚に収まるまで、何回半分にできるか)
    max_dimension = max(width, height)
    max_zoom = math.ceil(math.log(max_dimension / TILE_SIZE, 2))
    print(f"最大ズームレベル: {max_zoom}")

    # ズームレベルごとに画像を縮小してカットする
    # (大きいズームから小さいズームへ順に処理)
    for zoom in range(max_zoom, -1, -1):
        print(f"ズームレベル {zoom} を処理中...", end="", flush=True)
        
        # このズームレベルでの画像サイズを計算
        num_tiles = 2 ** zoom
        current_canvas_size = num_tiles * TILE_SIZE
        
        # 画像をリサイズ（高品質なランチョス法を使用）
        # ※画像が大きいとここで少し時間がかかります
        resized_img = img.resize((current_canvas_size, current_canvas_size), Image.Resampling.LANCZOS)
        
        # タイルを縦横に切り出す
        for x in range(num_tiles):
            for y in range(num_tiles):
                # 切り出す座標を計算
                left = x * TILE_SIZE
                upper = y * TILE_SIZE
                right = left + TILE_SIZE
                lower = upper + TILE_SIZE
                
                # クロップ（切り抜き）
                tile = resized_img.crop((left, upper, right, lower))
                
                # 保存フォルダを作成 ( tiles/zoom/x/ )
                save_dir = os.path.join(OUTPUT_DIR, str(zoom), str(x))
                os.makedirs(save_dir, exist_ok=True)
                
                # 保存 ( tiles/zoom/x/y.png )
                save_path = os.path.join(save_dir, f"{y}.png")
                tile.save(save_path, "PNG")
        
        print(" 完了")

    print("-" * 30)
    print(f"すべての処理が完了しました！ '{OUTPUT_DIR}' フォルダを確認してください。")

if __name__ == "__main__":
    generate_tiles()