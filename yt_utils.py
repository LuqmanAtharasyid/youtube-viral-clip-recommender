import os
import re
import subprocess
import json
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi
import requests

def extract_video_id(url: str) -> str:
    """Ekstrak video ID dari berbagai format URL YouTube."""
    patterns = [
        r'(?:v=|\/v\/|embed\/|youtu\.be\/|\/shorts\/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if len(url.strip()) == 11:
        return url.strip()
    return None

def get_youtube_transcript(video_url: str):
    """
    Mengambil transkrip YouTube dengan metode cadangan ganda (Robust fallback):
    1. Menggunakan youtube-transcript-api standar.
    2. Jika diblokir (IP Blocked), fallback mengambil subtitle otomatis via yt-dlp.
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("URL YouTube tidak valid!")
    
    # Metode 1: Coba via youtube-transcript-api
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        transcript_data = []
        for snippet in fetched.snippets:
            transcript_data.append({
                'text': snippet.text,
                'start': snippet.start,
                'duration': snippet.duration
            })
        return video_id, transcript_data
    except Exception as e_api:
        # Jika gagal karena blokir IP atau tidak ada subtitle resmi, gunakan Metode 2 (yt-dlp subtitle dump)
        try:
            return get_transcript_via_ytdlp(video_url, video_id)
        except Exception as e_ytdlp:
            raise RuntimeError(
                f"Gagal mengambil transkrip. YouTube memblokir akses atau video tidak memiliki subtitle. "
                f"Detail Error: {str(e_api)} | Fallback Error: {str(e_ytdlp)}"
            )

def get_transcript_via_ytdlp(video_url: str, video_id: str):
    """Fallback menggunakan yt-dlp untuk mengunduh subtitle otomatis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Command yt-dlp untuk menulis subtitle ke file json3/vtt
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "id,en,en-US",
            "--sub-format", "json3",
            "-o", os.path.join(tmpdir, "%(id)s"),
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Cari file subtitle yang dihasilkan
        for file in os.listdir(tmpdir):
            if file.endswith('.json3'):
                filepath = os.path.join(tmpdir, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    transcript_data = []
                    events = data.get('events', [])
                    for ev in events:
                        segs = ev.get('segs', [])
                        text = "".join([s.get('utf8', '') for s in segs]).strip()
                        if text and text != '\n':
                            start_ms = ev.get('tStartMs', 0)
                            dur_ms = ev.get('dDurationMs', 2000)
                            transcript_data.append({
                                'text': text,
                                'start': start_ms / 1000.0,
                                'duration': dur_ms / 1000.0
                            })
                    if transcript_data:
                        return video_id, transcript_data
                        
        raise RuntimeError("yt-dlp tidak dapat menemukan subtitle atau teks transkrip untuk video ini.")

def analyze_transcript_for_viral_clips(transcript, api_key: str = None, model: str = "gpt-4o"):
    """
    Menganalisis transkrip untuk mencari segmen berpotensi viral dengan durasi ketat (30 detik - 90 detik).
    """
    formatted_text = ""
    for entry in transcript:
        start_sec = int(entry.get('start', 0))
        text = entry.get('text', '')
        minutes = start_sec // 60
        seconds = start_sec % 60
        time_str = f"[{minutes:02d}:{seconds:02d}]"
        formatted_text += f"{time_str} {text}\n"
    
    prompt = f"""
    Anda adalah seorang ahli strategi konten sosial media (TikTok, Reels, YouTube Shorts). 
    Analisis transkrip video YouTube berikut dan berikan 3 hingga 5 rekomendasi segmen (klip) yang memiliki potensi PALING TINGGI untuk viral.
    
    ATURAN DURASI KETAT:
    - Setiap klip DURASINYA HARUS BERKISAR ANTARA 30 DETIK HINGGA 90 DETIK (maksimal 1.5 menit). JANGAN ADA YANG LEBIH DARI 90 DETIK.
    
    Kriteria klip viral:
    1. Memiliki "hook" (pancingan) yang kuat di awal.
    2. Menyampaikan satu poin emosional, kontroversial, lucu, atau insight bernilai tinggi secara utuh dalam rentang 30 - 90 detik tersebut.
    
    Berikan output dalam format JSON valid berupa list of object dengan struktur berikut:
    [
      {{
        "title": "Judul klip yang menarik/clickbait sehat",
        "start_time": "MM:SS",
        "end_time": "MM:SS",
        "start_seconds": 120,
        "end_seconds": 175,
        "viral_score": 92,
        "reason": "Alasan singkat mengapa bagian ini sangat potensial viral"
      }}
    ]

    Transkrip Video:
    {formatted_text[:12000]}
    """

    if api_key:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful AI content strategist. Output must be valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                res_json = response.json()
                content = res_json['choices'][0]['message']['content']
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            validated = []
                            for clip in v:
                                dur = clip.get('end_seconds', 0) - clip.get('start_seconds', 0)
                                if 30 <= dur <= 90:
                                    validated.append(clip)
                                else:
                                    clip['end_seconds'] = clip.get('start_seconds', 0) + 60
                                    m_end, s_end = divmod(clip['end_seconds'], 60)
                                    clip['end_time'] = f"{m_end:02d}:{s_end:02d}"
                                    validated.append(clip)
                            return validated if validated else generate_heuristic_clips(transcript)
                return parsed
        except Exception as e:
            pass

    return generate_heuristic_clips(transcript)

def generate_heuristic_clips(transcript):
    """Algoritma pintar berbasis heuristik dengan durasi ketat 45-60 detik."""
    clips = []
    total_entries = len(transcript)
    if total_entries == 0:
        return []
    
    step = max(1, total_entries // 5)
    for i in range(1, 5):
        idx = i * step
        if idx >= total_entries:
            idx = total_entries - 1
            
        start_sec = int(transcript[idx].get('start', 0))
        end_sec = start_sec + 60
        
        m_start, s_start = divmod(start_sec, 60)
        m_end, s_end = divmod(end_sec, 60)
        
        clips.append({
            "title": f"Viral Highlight Potensial #{i}",
            "start_time": f"{m_start:02d}:{s_start:02d}",
            "end_time": f"{m_end:02d}:{s_end:02d}",
            "start_seconds": start_sec,
            "end_seconds": end_sec,
            "viral_score": 88 - (i * 3),
            "reason": "Segmen ini diambil dengan durasi pas 60 detik yang ideal untuk Shorts/Reels/TikTok."
        })
        if len(clips) >= 4:
            break
    return clips
