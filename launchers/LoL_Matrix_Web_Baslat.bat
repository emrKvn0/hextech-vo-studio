@echo off
title LoL Matrix & Atif Analiz Merkezi (Vite + Ses Motoru)
cd /d "%~dp0.."

echo =======================================================
echo 🎧 1. LoL JIT Ses Sunucusu Baslatiliyor (Port 8080)...
echo =======================================================
start "LoL Audio Streamer" /min python scripts/audio_server.py

timeout /t 1 /nobreak >nul

echo =======================================================
echo 🚀 2. LoL Matrix Vite Web Sitesi Baslatiliyor...
echo 🌐 Adres: http://localhost:5173
echo =======================================================
cd /d "%~dp0..\lol-matrix-web"
start "" http://localhost:5173
npm run dev
pause
