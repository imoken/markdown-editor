import streamlit as st
import json
import requests
import io
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# --- UI / Page Config ---
st.set_page_config(page_title="Editor", layout="wide", initial_sidebar_state="collapsed")

# カスタムCSS（洗練されたダークテーマ）
st.markdown("""
    <style>
    /* 全体背景とフォント */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono&display=swap');
    
    .main { background-color: #0d1117; color: #adbac7; font-family: 'Inter', sans-serif; }
    
    /* エディタのスタイリング */
    .stTextArea textarea {
        background-color: #161b22 !important;
        color: #adbac7 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        padding: 30px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* フォーカス時の青いネオンエフェクト */
    .stTextArea textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 4px rgba(88, 166, 255, 0.15) !important;
        outline: none !important;
    }

    /* プレビューエリア */
    .stMarkdown { padding: 10px 20px; line-height: 1.8; }
    h1, h2, h3 { color: #58a6ff !important; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
    code { background-color: #2d333b !important; padding: 2px 4px; border-radius: 4px; }

    /* ステータスバッジ */
    .status-container {
        display: flex; align-items: center; justify-content: flex-end;
        gap: 8px; margin-bottom: 15px; font-size: 12px;
    }
    .dot { height: 8px; width: 8px; border-radius: 50%; display: inline-block; }
    .dot-saving { background-color: #f2cc60; animation: blink 1s infinite; }
    .dot-saved { background-color: #3fb950; }

    @keyframes blink { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }

    /* 不要なUIを隠す */
    div[data-testid="stToolbar"] { display: none; }
    footer { visibility: hidden; }
    section[data-testid="stSidebar"] { background-color: #010409 !important; border-right: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic ---
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
except KeyError:
    st.error("Secrets missing.")
    st.stop()

REDIRECT_URI = "https://markdown-editor.streamlit.app/"

def get_credentials(auth_code):
    res = requests.post("https://oauth2.googleapis.com/token", data={
        "code": auth_code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code",
    })
    return res.json()

def download_file(file_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers)
    return res.content.decode('utf-8') if res.status_code == 200 else None

def save_to_drive(file_id, access_token, content):
    creds = Credentials(access_token)
    service = build('drive', 'v3', credentials=creds)
    fh = io.BytesIO(content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/markdown', resumable=True)
    try:
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except:
        return False

# --- App Layout ---
params = st.query_params

if "state" in params and "code" in params:
    try:
        state_dict = json.loads(params["state"])
        file_id = state_dict.get("ids", [None])[0]
        
        if 'access_token' not in st.session_state:
            st.session_state.access_token = get_credentials(params["code"]).get("access_token")

        if file_id and 'markdown_content' not in st.session_state:
            st.session_state.markdown_content = download_file(file_id, st.session_state.access_token) or ""

        # Header: Status Display
        status_col1, status_col2 = st.columns([1, 1])
        with status_col2:
            if 'is_saving' in st.session_state and st.session_state.is_saving:
                st.markdown('<div class="status-container"><span class="dot dot-saving"></span><span style="color:#f2cc60">Syncing...</span></div>', unsafe_allow_html=True)
            elif 'last_saved' in st.session_state:
                st.markdown(f'<div class="status-container"><span class="dot dot-saved"></span><span style="color:#3fb950">Cloud Synced ({st.session_state.last_saved})</span></div>', unsafe_allow_html=True)

        # Main: Editor & Preview
        ed_col, pr_col = st.columns([1, 1], gap="large")
        
        with ed_col:
            # ブラウザの高さに合わせて自動調整 (vh = viewport height)
            content = st.text_area(
                "editor", value=st.session_state.markdown_content,
                height=800, label_visibility="collapsed"
            )
            
            if content != st.session_state.markdown_content:
                st.session_state.is_saving = True
                if save_to_drive(file_id, st.session_state.access_token, content):
                    st.session_state.markdown_content = content
                    st.session_state.last_saved = datetime.datetime.now().strftime("%H:%M")
                    st.session_state.is_saving = False
                    st.rerun()

        with pr_col:
            st.markdown(st.session_state.markdown_content)

        # Sidebar Settings (Gear Icon functionality)
        with st.sidebar:
            st.markdown("### ⚙️ Editor Settings")
            st.divider()
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/drive.file%20https://www.googleapis.com/auth/drive.install&access_type=offline&prompt=consent"
            st.link_button("🔄 Reset Connection", auth_url, use_container_width=True)
            st.info("Files are automatically synced to Google Drive on every change.")

    except Exception as e:
        st.error("Authentication expired. Please reopen from Google Drive.")
else:
    st.info("Google Driveの「アプリで開く」から起動してください。")
