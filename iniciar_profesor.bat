@echo off
title Profesor MiniMax - Matematicas y Fisica
echo ============================================================
echo   Iniciando Servidor del Profesor MiniMax...
echo ============================================================
cd /d "%~dp0"
echo Abriendo navegador en http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
