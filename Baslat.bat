@echo off
title Akilli Yaya Gecidi EDS Denetim Merkezi
cd /d "%~dp0"
echo =======================================================
echo    AKILLI YAYA GECIDI EDS DENETIM SISTEMI
echo    Yapay Zeka ve Bilgisayarli Goru Kontrol Paneli
echo =======================================================
echo.
echo Sistem baslatiliyor, lutfen bekleyiniz...
set "PY_CMD=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
)
"%PY_CMD%" gui_app.py
pause
