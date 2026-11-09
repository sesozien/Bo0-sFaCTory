@echo off
setlocal
cd /d "%~dp0"
title Bo0 Factory - Offline Launcher

set "VENV=.venv"
set "PYTHON=%VENV%\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [1/2] إنشاء بيئة التشغيل لأول مرة...
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3 -m venv "%VENV%"
    ) else (
        python -m venv "%VENV%"
    )
    if errorlevel 1 (
        echo تعذر إنشاء البيئة. ثبت Python 3.10 أو أحدث ثم أعد المحاولة.
        pause
        exit /b 1
    )
    echo [2/2] تثبيت المكتبات مرة واحدة فقط...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo فشل تثبيت المكتبات. تأكد من وجود الإنترنت أثناء أول تشغيل.
        pause
        exit /b 1
    )
    echo تم التثبيت. لن يتم تنزيل المكتبات في التشغيلات القادمة.
)

set "BO0_OFFLINE_MODE=1"
echo تشغيل Bo0 Factory محليًا بدون إعادة تثبيت المكتبات...
"%PYTHON%" -m streamlit run app.py --server.headless false
pause
