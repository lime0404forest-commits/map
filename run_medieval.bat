@echo off
rem バッチファイルがある場所にカレントディレクトリを移動
cd /d %~dp0

rem python プログラムの場所 ゲームフォルダ名
py src\map_editor.py medieval

pause