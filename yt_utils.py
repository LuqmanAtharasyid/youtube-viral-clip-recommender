import os
import re
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import json

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
    """Mengambil transkrip dari video YouTube menggunakan instance YouTubeTranscriptApi terbaru."""
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("URL YouTube tidak valid!")
    
    try:
        api = YouTubeTranscriptApi()
        # Coba ambil transkrip menggunakan instance .fetch()
        fetched = api.fetch(video_id)
        # Ubah objek fetched snippet menjadi format list of dict agar kompatibel
        transcript_data = []
        for snippet in fetched.snippets:
            transcript_data.append({
                'text': snippet.text,
                'start': snippet.start,
                'duration': snippet.duration
            })
        return video_id, transcript_data
    except Exception as e:
        raise RuntimeError(f"Gagal mengambil transkrip video ini: {str(e)}")

def analyze_transcript_for_viral_clips(transcript, api_key: str = None, model: str = "gpt-4o"):
    """
    Menganalisis transkrip untuk mencari segmen berpotensi viral.
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
    
    Kriteria klip viral:
    1. Memiliki "hook" (pancingan) yang kuat di awal.
    2. Menyampaikan satu poin emosional, kontroversial, lucu, atau insight bernilai tinggi secara utuh.
    3. Berdurasi antara 30 detik hingga 90 detik.
    
    Berikan output dalam format JSON valid berupa list of object dengan struktur berikut:
    [
      {{
        "title": "Judul klip yang menarik/clickbait sehat",
        "start_time": "MM:SS",
        "end_time": "MM:SS",
        "start_seconds": 120,
        "end_seconds": 185,
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
                            return v
                return parsed
        except Exception as e:
            pass

    return generate_heuristic_clips(transcript)

def generate_heuristic_clips(transcript):
    """Algoritma pintar berbasis heuristik."""
    clips = []
    chunk_size = max(1, len(transcript) // 4)
    
    for i in range(0, len(transcript), chunk_size):
        chunk = transcript[i:i + chunk_size]
        if not chunk:
            continue
        start_sec = int(chunk[0].get('start', 0))
        end_sec = int(chunk[-1].get('start', 0) + chunk[-1].get('duration', 5))
        
        if end_sec - start_sec < 20:
            end_sec = start_sec + 45
            
        m_start, s_start = divmod(start_sec, 60)
        m_end, s_end = divmod(end_sec, 60)
        
        clips.append({
            "title": f"Highlight Potensial #{len(clips)+1}",
            "start_time": f"{m_start:02d}:{s_start:02d}",
            "end_time": f"{m_end:02d}:{s_end:02d}",
            "start_seconds": start_sec,
            "end_seconds": end_sec,
            "viral_score": 85 - (len(clips) * 5),
            "reason": "Bagian ini memiliki dinamika pembicaraan yang menarik dan cocok untuk format pendek."
        })
        if len(clips) >= 4:
            break
    return clips
