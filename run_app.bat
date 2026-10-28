@echo off
TITLE YouTube Viral Clip Recommender
COLOR 0A
echo ========================================================
echo   MENJALANKAN APLIKASI DESKTOP YOUTUBE VIRAL CLIPS
echo ========================================================
echo Membuka aplikasi di browser default Anda...
start http://localhost:8501
py -m streamlit run app.py --server.headless=true
pause
