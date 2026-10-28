import streamlit as st
import pandas as pd
from yt_utils import get_youtube_transcript, analyze_transcript_for_viral_clips

st.set_page_config(
    page_title="YouTube Viral Clip & Caption AI",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #FF4B4B;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #888;
        margin-bottom: 25px;
    }
    .clip-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 18px;
    }
    .metric-badge {
        background-color: #FF4B4B;
        color: white;
        padding: 4px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .caption-box {
        background-color: #2b2b2b;
        border-left: 4px solid #FF4B4B;
        padding: 12px 16px;
        border-radius: 5px;
        margin-top: 10px;
        font-family: monospace;
        color: #f1f1f1;
        white-space: pre-wrap;
    }
    .ai-badge {
        background-color: #2e7d32;
        color: #e8f5e9;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 15px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.title("🤖 Konfigurasi AI")
st.sidebar.markdown("""
<div class="ai-badge">⚡ AI Engine: Auto-Optimized</div>
""", unsafe_allow_html=True)

st.sidebar.write("**Spesialisasi Model:**")
st.sidebar.caption("Sistem telah otomatis mengaktifkan parameter model cerdas khusus **Short-Form Content Strategist & Hook Extractor** (30 - 90 detik).")

api_key_input = st.sidebar.text_input(
    "API Key (OpenAI / OpenRouter / Groq)",
    type="password",
    help="Opsional. Sistem akan otomatis mendeteksi provider dan memilih model terbaik (misal: GPT-4o untuk OpenAI, Gemini Flash untuk OpenRouter, Llama 3.3 untuk Groq)."
)

# Collapsible Manual Override
with st.sidebar.expander("⚙️ Pengaturan Lanjutan (Opsional)"):
    manual_model = st.selectbox(
        "Pilihan Model Override",
        [
            "Otomatis (Rekomendasi AI Terbaik)",
            "gpt-4o",
            "google/gemini-2.0-flash-001",
            "anthropic/claude-3.5-sonnet",
            "llama-3.3-70b-versatile"
        ],
        index=0
    )

st.sidebar.info("💡 Tanpa API Key? Aplikasi tetap berjalan menggunakan **Smart NLP Hook Engine bawaan** secara cerdas & gratis.")

# Main Interface
st.markdown('<div class="main-header">🎬 YouTube Viral Clip & Caption AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Tempel link YouTube, sistem akan otomatis memilih segmen paling potensial viral (30-90 detik) lengkap dengan caption pemancing interaksi!</div>', unsafe_allow_html=True)

# Input Form
with st.form("clip_form"):
    youtube_url = st.text_input("🔗 Link Video YouTube (atau Video ID):", placeholder="https://www.youtube.com/watch?v=...")
    submitted = st.form_submit_button("🚀 Analisis & Temukan Klip Viral")

if submitted:
    if not youtube_url.strip():
        st.warning("⚠️ Mohon masukkan link YouTube terlebih dahulu!")
    else:
        with st.spinner("⏳ Menganalisis transkrip, mendeteksi hook, dan menyusun saran caption..."):
            try:
                video_id, transcript = get_youtube_transcript(youtube_url)
                st.session_state['video_id'] = video_id
                st.session_state['transcript'] = transcript
                
                # Panggil analisis dengan auto-selected model
                clips = analyze_transcript_for_viral_clips(
                    transcript,
                    api_key=api_key_input,
                    manual_model=manual_model
                )
                st.session_state['clips'] = clips
                st.success("✅ Analisis selesai! Rekomendasi klip viral telah siap.")
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {str(e)}")

# Display Results if Available
if 'clips' in st.session_state and st.session_state['clips']:
    st.divider()
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📺 Video Player")
        vid_id = st.session_state.get('video_id', '')
        if vid_id:
            st.video(f"https://www.youtube.com/watch?v={vid_id}")
            
    with col2:
        st.subheader("🔥 Rekomendasi Klip & Caption Siap Upload")
        clips = st.session_state['clips']
        
        for idx, clip in enumerate(clips):
            score = clip.get('viral_score', 85)
            title = clip.get('title', f'Klip #{idx+1}')
            start_t = clip.get('start_time', '00:00')
            end_t = clip.get('end_time', '00:00')
            reason = clip.get('reason', 'Potongan momentum penting.')
            caption = clip.get('caption', 'Coba komen pendapat kalian! #fyp #viral')
            
            with st.container():
                st.markdown(f"""
                <div class="clip-card">
                    <h4 style="margin-top:0;">{title}</h4>
                    <p><b>⏱️ Durasi Pas:</b> <code>{start_t}</code> s.d. <code>{end_t}</code> &nbsp;&nbsp; 
                    <span class="metric-badge">Skor Viral: {score}/100</span></p>
                    <p><b>💡 Analisis Potensi:</b> {reason}</p>
                    <p style="margin-bottom: 5px;"><b>✍️ Rekomendasi Caption:</b></p>
                    <div class="caption-box">{caption}</div>
                </div>
                """, unsafe_allow_html=True)

    # Opsi Export Data
    st.divider()
    st.subheader("📥 Export Rekomendasi")
    df_clips = pd.DataFrame(st.session_state['clips'])
    csv = df_clips.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Semua Klip & Caption (CSV)",
        data=csv,
        file_name=f"viral_clips_{st.session_state.get('video_id', 'youtube')}.csv",
        mime='text/csv',
    )
