import os

# srcフォルダのパス
SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# プロジェクトルート（srcの一つ上）
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# ゲームデータ保存フォルダ
GAMES_ROOT = os.path.join(PROJECT_ROOT, "games")

# 必要があればフォルダ作成
os.makedirs(GAMES_ROOT, exist_ok=True)