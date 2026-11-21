@echo off
title League of Legends Ses ^& Video Studyosu
cd /d "%~dp0.."
pythonw main_gui.py
if errorlevel 1 (
    python main_gui.py
    pause
)
