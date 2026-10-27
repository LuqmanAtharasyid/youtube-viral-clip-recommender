import streamlit as st
import pandas as pd
from yt_utils import get_youtube_transcript, analyze_transcript_for_viral_clips, extract_video_id

st.set_page_config(
    page_title="YouTube Viral Clip Recommender",
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
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 30px;
    }
    .clip-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .metric-badge {
        background-color: #FF4B4B;
        color: white;
        padding: 4px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.title("⚙️ Pengaturan AI")
api_key_input = st.sidebar.text_input("OpenAI / OpenRouter API Key (Opsional)", type="password", help="Kosongkan untuk menggunakan mode Heuristik cerdas bawaan.")
model_choice = st.sidebar.selectbox("Pilih Model AI", ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"], index=0)
st.sidebar.info("💡 Aplikasi ini mendeteksi transkrip YouTube secara otomatis dan memberikan rekomendasi timestamp klip terbaik untuk TikTok / Shorts / Reels.")

# Main Interface
st.markdown('<div class="main-header">🎬 YouTube Viral Clip Recommender</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Masukkan link video YouTube, biarkan AI menganalisis bagian paling menarik dan potensial viral!</div>', unsafe_allow_html=True)

# Input Form
with st.form("clip_form"):
    youtube_url = st.text_input("🔗 Link Video YouTube (atau Video ID):", placeholder="https://www.youtube.com/watch?v=...")
    submitted = st.form_submit_button("🔍 Analisis Video & Cari Klip Viral")

if submitted:
    if not youtube_url.strip():
        st.warning("⚠️ Mohon masukkan link YouTube terlebih dahulu!")
    else:
        with st.spinner("⏳ Sedang mengambil transkrip dan menganalisis konten..."):
            try:
                video_id, transcript = get_youtube_transcript(youtube_url)
                st.session_state['video_id'] = video_id
                st.session_state['transcript'] = transcript
                
                # Analisis AI / Heuristik
                clips = analyze_transcript_for_viral_clips(transcript, api_key=api_key_input, model=model_choice)
                st.session_state['clips'] = clips
                st.success("✅ Analisis selesai!")
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {str(e)}")

# Display Results if Available
if 'clips' in st.session_state and st.session_state['clips']:
    st.divider()
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📺 Preview Video")
        vid_id = st.session_state.get('video_id', '')
        if vid_id:
            st.video(f"https://www.youtube.com/watch?v={vid_id}")
            
    with col2:
        st.subheader("🔥 Rekomendasi Klip Potensi Viral")
        clips = st.session_state['clips']
        
        for idx, clip in enumerate(clips):
            score = clip.get('viral_score', 80)
            title = clip.get('title', f'Klip #{idx+1}')
            start_t = clip.get('start_time', '00:00')
            end_t = clip.get('end_time', '00:00')
            reason = clip.get('reason', 'Potongan menarik dari video.')
            
            with st.container():
                st.markdown(f"""
                <div class="clip-card">
                    <h4>#{idx+1}: {title}</h4>
                    <p><b>⏱️ Timestamp:</b> <code>{start_t}</code> s.d. <code>{end_t}</code> &nbsp;&nbsp; 
                    <span class="metric-badge">Skor Viral: {score}/100</span></p>
                    <p><b>💡 Alasan:</b> {reason}</p>
                </div>
                """, unsafe_allow_html=True)

    # Opsi Export Data
    st.divider()
    st.subheader("📥 Export Rekomendasi")
    df_clips = pd.DataFrame(st.session_state['clips'])
    csv = df_clips.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Jadwal Timestamp (CSV)",
        data=csv,
        file_name=f"viral_clips_{st.session_state.get('video_id', 'youtube')}.csv",
        mime='text/csv',
    )
