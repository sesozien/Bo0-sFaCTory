@echo off
title 🛸 Bo0'sViDClone Launcher 🛸
echo =========================================
echo       ⚡ جاري إطلاق إمبراطورية مـنتــجـك ⚡
echo =========================================
echo.
echo [+] Checking required packages...
pip install streamlit pillow moviepy yt-dlp requests beautifulsoup4 opencv-python numpy
echo.
echo [+] Launching Streamlit Server...
streamlit run app.py
pause