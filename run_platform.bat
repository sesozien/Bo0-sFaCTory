@echo off
title 🛸 Bo0'sViDClone Launcher 🛸
echo =========================================
echo       ⚡ جاري إطلاق إمبراطورية مـنتــجـك ⚡
echo =========================================
echo.
echo [+] Checking required packages...
rem MoviePy 1.0.3 is required because the app uses moviepy.editor and set_*/fx APIs.
pip install -r requirements.txt
echo.
echo [+] Launching Streamlit Server...
streamlit run app.py
pause
