import subprocess
import sys
import os

def build_exe():
    print("Mempersiapkan pembuatan aplikasi Desktop (.exe)...")
    
    # Pastikan pyinstaller terinstal
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Perintah PyInstaller untuk membuat single file / folder standalone
    # Menggunakan mode --onedir dengan streamlit agar stabil
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--clean",
        "--name=YouTubeViralClips",
        "--add-data=app.py;.",
        "--add-data=yt_utils.py;.",
        "app.py"
    ]
    
    # Jalankan pyinstaller
    print("Menjalankan PyInstaller...")
    subprocess.run(cmd, check=True)
    print("Selesai! Folder aplikasi desktop berada di folder /dist/YouTubeViralClips/")

if __name__ == "__main__":
    build_exe()
