import streamlit as st
import pandas as pd
from yt_utils import get_youtube_transcript, analyze_transcript_for_viral_clips

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
    .caption-box {
        background-color: #2b2b2b;
        border-left: 4px solid #FF4B4B;
        padding: 10px 15px;
        border-radius: 4px;
        margin-top: 10px;
        font-family: monospace;
        color: #f1f1f1;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.title("⚙️ Pengaturan AI")
api_key_input = st.sidebar.text_input("OpenAI / OpenRouter API Key (Opsional)", type="password", help="Kosongkan untuk menggunakan mode Heuristik cerdas bawaan.")
model_choice = st.sidebar.selectbox("Pilih Model AI", ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"], index=0)
st.sidebar.info("💡 Aplikasi ini mendeteksi transkrip YouTube, memberikan rekomendasi klip berdurasi 30-90 detik, lengkap dengan saran caption pemancing interaksi.")

# Main Interface
st.markdown('<div class="main-header">🎬 YouTube Viral Clip Recommender & Caption Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Masukkan link video YouTube, dapatkan rekomendasi timestamp klip pendek (30-90 detik) beserta saran caption siap post!</div>', unsafe_allow_html=True)

# Input Form
with st.form("clip_form"):
    youtube_url = st.text_input("🔗 Link Video YouTube (atau Video ID):", placeholder="https://www.youtube.com/watch?v=...")
    submitted = st.form_submit_button("🔍 Analisis Video & Generate Klip Viral")

if submitted:
    if not youtube_url.strip():
        st.warning("⚠️ Mohon masukkan link YouTube terlebih dahulu!")
    else:
        with st.spinner("⏳ Sedang mengambil transkrip dan menganalisis klip viral & caption..."):
            try:
                video_id, transcript = get_youtube_transcript(youtube_url)
                st.session_state['video_id'] = video_id
                st.session_state['transcript'] = transcript
                
                clips = analyze_transcript_for_viral_clips(transcript, api_key=api_key_input, model=model_choice)
                st.session_state['clips'] = clips
                st.success("✅ Analisis berhasil diselesaikan!")
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
        st.subheader("🔥 Rekomendasi Klip & Saran Caption")
        clips = st.session_state['clips']
        
        for idx, clip in enumerate(clips):
            score = clip.get('viral_score', 85)
            title = clip.get('title', f'Klip #{idx+1}')
            start_t = clip.get('start_time', '00:00')
            end_t = clip.get('end_time', '00:00')
            reason = clip.get('reason', 'Potongan menarik.')
            caption = clip.get('caption', 'Coba komen pendapat kalian! #fyp #viral')
            
            with st.container():
                st.markdown(f"""
                <div class="clip-card">
                    <h4>#{idx+1}: {title}</h4>
                    <p><b>⏱️ Durasi (30s - 90s):</b> <code>{start_t}</code> s.d. <code>{end_t}</code> &nbsp;&nbsp; 
                    <span class="metric-badge">Skor: {score}/100</span></p>
                    <p><b>💡 Alasan:</b> {reason}</p>
                    <p style="margin-bottom: 5px;"><b>✍️ Saran Caption Viral:</b></p>
                    <div class="caption-box">{caption}</div>
                </div>
                """, unsafe_allow_html=True)

    # Opsi Export Data
    st.divider()
    st.subheader("📥 Export Rekomendasi")
    df_clips = pd.DataFrame(st.session_state['clips'])
    csv = df_clips.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Data Klip & Caption (CSV)",
        data=csv,
        file_name=f"viral_clips_with_captions_{st.session_state.get('video_id', 'youtube')}.csv",
        mime='text/csv',
    )
