@echo off
chcp 65001 >nul
title LoLdle TR - League of Legends Turkce Tahmin Oyunu
cd /d "%~dp0.."

echo ======================================================================
echo          ⚔️  LoLdle TR - Hextech Web Uygulamasi Baslatiliyor  ⚔️
echo ======================================================================
echo.

:: Python kontrolü (python veya py)
set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=py
    ) else (
        echo [HATA] Python veya py bulunamadi! Lutfen Python'in kurulu ve PATH'e ekli oldugundan emin olun.
        pause
        exit /b 1
    )
)

:: Tarayıcıyı 2 saniye sonra aç
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

echo [BILGI] LoLdle Sunucusu baslatiliyor: http://127.0.0.1:8000
echo [BILGI] Tarayiciniz otomatik olarak acilacaktir...
echo.
echo Sunucuyu kapatmak icin bu pencereyi kapatabilir veya Ctrl+C yapabilirsiniz.
echo.

%PYTHON_CMD% loldle_server.py

pause
