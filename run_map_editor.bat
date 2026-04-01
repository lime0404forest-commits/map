@echo off
cd /d %~dp0

rem 先に exe 版があればそれを起動（別プロセスとして実行）
if exist "%~dp0dist\MapEditor\MapEditor.exe" (
    start "" "%~dp0dist\MapEditor\MapEditor.exe"
) else (
    rem exe がまだ無い場合は従来どおり Python で起動
    start "" py main.py
)