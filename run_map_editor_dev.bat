@echo off
cd /d %~dp0

rem 開発用: 常にソースを Python で起動（再ビルド不要）
start "" py main.py
