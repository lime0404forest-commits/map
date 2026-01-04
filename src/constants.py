import os

# アプリケーションのルートディレクトリ（main.pyがある場所）
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ゲームデータを保存するフォルダ
GAMES_ROOT = os.path.join(APP_DIR, "games")
os.makedirs(GAMES_ROOT, exist_ok=True)