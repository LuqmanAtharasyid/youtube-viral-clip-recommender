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
    """Mengambil transkrip YouTube dengan metode cadangan ganda (Robust fallback)."""
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("URL YouTube tidak valid!")
    
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

def auto_detect_ai_config(api_key: str, manual_model: str = None):
    """
    Otomatis mendeteksi provider dan memilih model AI paling cocok untuk klip viral:
    - OpenRouter (sk-or-...): google/gemini-2.0-flash-001 atau anthropic/claude-3.5-sonnet
    - Groq (gsk_...): llama-3.3-70b-versatile
    - OpenAI (sk-...): gpt-4o
    """
    api_key = api_key.strip()
    if not api_key:
        return None, None, None

    if api_key.startswith("sk-or-"):
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        best_model = "google/gemini-2.0-flash-001"
        provider_name = "OpenRouter (Gemini Flash Optimized)"
    elif api_key.startswith("gsk_"):
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        best_model = "llama-3.3-70b-versatile"
        provider_name = "Groq (Llama 3.3 Fast)"
    else:
        endpoint = "https://api.openai.com/v1/chat/completions"
        best_model = "gpt-4o"
        provider_name = "OpenAI (GPT-4o Viral Specialist)"

    # Jika pengguna memilih model spesifik secara manual (bukan 'Auto')
    chosen_model = manual_model if (manual_model and manual_model != "Otomatis (Rekomendasi AI Terbaik)") else best_model
    return endpoint, chosen_model, provider_name

def analyze_transcript_for_viral_clips(transcript, api_key: str = None, manual_model: str = None):
    """
    Menganalisis transkrip untuk mencari segmen berpotensi viral (30s-90s)
    lengkap dengan saran caption sosmed bernuansa viral.
    Model AI secara otomatis dipilih yang paling cocok untuk tugas ini.
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
    Anda adalah seorang ahli strategi konten sosial media kelas dunia (TikTok, Reels, YouTube Shorts). 
    Analisis transkrip video YouTube berikut dan berikan 3 hingga 5 rekomendasi segmen (klip) yang memiliki potensi PALING TINGGI untuk viral.
    
    ATURAN DURASI KETAT:
    - Setiap klip DURASINYA HARUS BERKISAR ANTARA 30 DETIK HINGGA 90 DETIK (maksimal 1.5 menit).
    
    KRITERIA KLIP VIRAL:
    1. Hook Kuat: 3-5 detik pertama langsung memancing rasa penasaran / kejutan / masalah besar.
    2. Value/Emosi Padat: Menjelaskan 1 poin penting secara tuntas, lucu, atau provokatif.
    3. Standalone: Bisa dipahami tanpa harus menonton keseluruhan video panjangnya.
    
    UNTUK SETIAP KLIP, BERIKAN:
    1. title: Judul klip yang clickbait sehat & bikin penasaran.
    2. start_time: Format MM:SS.
    3. end_time: Format MM:SS.
    4. start_seconds: Detik mulai (integer).
    5. end_seconds: Detik selesai (integer).
    6. viral_score: Skor potensi viral (angka 80 - 99).
    7. reason: Alasan mengapa bagian ini sangat potensial viral.
    8. caption: Saran caption sosial media (TikTok/Reels/Shorts) pemancing interaksi/komentar, lengkap dengan hashtag relevan.
    
    Format output HARUS JSON valid berupa list of object:
    [
      {{
        "title": "...",
        "start_time": "01:20",
        "end_time": "02:10",
        "start_seconds": 80,
        "end_seconds": 130,
        "viral_score": 95,
        "reason": "...",
        "caption": "..."
      }}
    ]

    Transkrip Video:
    {formatted_text[:14000]}
    """

    if api_key and api_key.strip():
        endpoint, model, provider_name = auto_detect_ai_config(api_key, manual_model)
        try:
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a professional social media content strategist specializing in short-form viral hooks. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                res_json = response.json()
                content = res_json['choices'][0]['message']['content']
                # Bersihkan markdown formatting jika ada (```json ... ```)
                clean_content = re.sub(r'^```json\s*|\s*```$', '', content.strip(), flags=re.MULTILINE)
                parsed = json.loads(clean_content)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            parsed = v
                            break
                if isinstance(parsed, list):
                    validated = []
                    for clip in parsed:
                        dur = clip.get('end_seconds', 0) - clip.get('start_seconds', 0)
                        if not (30 <= dur <= 90):
                            clip['end_seconds'] = clip.get('start_seconds', 0) + 60
                            m_end, s_end = divmod(clip['end_seconds'], 60)
                            clip['end_time'] = f"{m_end:02d}:{s_end:02d}"
                        validated.append(clip)
                    if validated:
                        return validated
        except Exception:
            pass

    # Mode Smart Content Scorer Cerdas (Heuristik Berbasis NLP & Hook Detection)
    return generate_smart_heuristic_clips(transcript)

def generate_smart_heuristic_clips(transcript):
    """
    Algoritma NLP Heuristik Cerdas untuk mendeteksi segmen paling bernilai tinggi
    berdasarkan kepadatan kata kunci viral, hook, dan momentum bicara.
    """
    if not transcript:
        return []
        
    total_time = transcript[-1].get('start', 0)
    if total_time < 30:
        return [{
            "title": "Highlight Utama Video",
            "start_time": "00:00",
            "end_time": f"00:{int(total_time):02d}",
            "start_seconds": 0,
            "end_seconds": int(total_time),
            "viral_score": 85,
            "reason": "Video berdurasi pendek, cocok langsung dipotong utuh.",
            "caption": "Tonton sampai habis untuk insight lengkapnya! 🔥 #ViralShorts #fyp"
        }]

    VIRAL_KEYWORDS = {
        'rahasia': 6, 'fakta': 6, 'ternyata': 6, 'kesalahan': 6, 'jangan': 5,
        'bahaya': 5, 'penting': 5, 'juta': 5, 'miliar': 5, 'uang': 5,
        'kaya': 4, 'miskin': 4, 'gagal': 5, 'sukses': 5, 'investasi': 5,
        'rugi': 5, 'untung': 4, 'persen': 4, '%': 4, 'trik': 5, 'tips': 5,
        'secret': 6, 'fact': 6, 'million': 5, 'billion': 5, 'money': 5,
        'mistake': 6, 'never': 5, 'warning': 6, 'truth': 6, 'why': 5, 'problem': 5
    }

    # Evaluasi jendela waktu dinamis berdurasi 45-60 detik
    window_duration = 60
    step = 20
    candidate_windows = []

    curr_time = 0
    while curr_time + 30 <= total_time:
        end_time = min(curr_time + window_duration, total_time)
        entries = [e for e in transcript if curr_time <= e.get('start', 0) < end_time]
        
        if entries and len(entries) >= 4:
            combined_text = " ".join(e.get('text', '') for e in entries)
            words = combined_text.lower().split()
            
            # Skor dasar
            score = 70
            for w in words:
                for kw, pts in VIRAL_KEYWORDS.items():
                    if kw in w:
                        score += pts
                        
            # Cek Hook di kalimat pertama
            first_sentence = entries[0].get('text', '').lower()
            if any(h in first_sentence for h in ['okay', 'jadi', 'kenapa', 'mengapa', 'tahukah', 'apakah', 'so', 'why', 'how', 'ternyata', 'pernah']):
                score += 8
                
            candidate_windows.append({
                'start_sec': int(curr_time),
                'end_sec': int(end_time),
                'score': min(score, 97),
                'text': combined_text,
                'first_line': entries[0].get('text', '').strip()
            })
            
        curr_time += step

    # Urutkan berdasarkan skor tertinggi
    candidate_windows.sort(key=lambda x: x['score'], reverse=True)

    # Pilih 3-4 klip terbaik yang tidak tumpang tindih (non-overlapping)
    selected_clips = []
    for cand in candidate_windows:
        overlap = False
        for sel in selected_clips:
            # Cegah tumpang tindih segmen
            if not (cand['end_sec'] <= sel['start_seconds'] or cand['start_sec'] >= sel['end_seconds']):
                overlap = True
                break
        if not overlap:
            m_start, s_start = divmod(cand['start_sec'], 60)
            m_end, s_end = divmod(cand['end_sec'], 60)
            
            # Buat judul spesifik berdasarkan konteks kalimat pembuka
            title_clean = re.sub(r'[^a-zA-Z0-9\s]', '', cand['first_line']).title()
            if len(title_clean.split()) > 7:
                title_clean = " ".join(title_clean.split()[:7]) + "..."
            if len(title_clean) < 6:
                title_clean = f"Momen Kunci #{len(selected_clips)+1}"

            # Cuplikan topik untuk caption
            snippet = cand['text'][:90].strip().replace('\n', ' ')
            
            selected_clips.append({
                "title": f"🔥 {title_clean}",
                "start_time": f"{m_start:02d}:{s_start:02d}",
                "end_time": f"{m_end:02d}:{s_end:02d}",
                "start_seconds": cand['start_sec'],
                "end_seconds": cand['end_sec'],
                "viral_score": cand['score'],
                "reason": "Segmen ini memiliki konsentrasi poin kunci dan pancingan rasa penasaran yang sangat tinggi.",
                "caption": f'"{snippet}..."\n\nSetuju gak sama poin ini? Tulis pendapat kalian di kolom komentar! 👇💥 #InsightViral #fyp #Trending'
            })
            if len(selected_clips) >= 4:
                break

    return selected_clips
