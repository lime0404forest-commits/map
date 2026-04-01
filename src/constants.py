import os
import sys

# srcフォルダのパス
SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# プロジェクトルート
# 通常: src の一つ上
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# PyInstaller で exe 化された場合:
#   dist/MapEditor/MapEditor.exe の想定なので、exe の親の親をプロジェクトルートとみなす
if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    # 期待配置: <project>\dist\MapEditor\MapEditor.exe
    # この場合の project は exe_dir の2つ上
    PROJECT_ROOT = os.path.dirname(os.path.dirname(exe_dir))
    # もし構成が異なる場合は、games が存在する候補を優先
    if not os.path.isdir(os.path.join(PROJECT_ROOT, "games")):
        alt_root = os.path.dirname(exe_dir)
        if os.path.isdir(os.path.join(alt_root, "games")):
            PROJECT_ROOT = alt_root

# ゲームデータ保存フォルダ
GAMES_ROOT = os.path.join(PROJECT_ROOT, "games")

# 必要があればフォルダ作成
os.makedirs(GAMES_ROOT, exist_ok=True)