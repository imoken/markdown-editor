import streamlit as st
import json
import requests
import io
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# --- UI / Page Config ---
# initial_sidebar_state="expanded" にして設定（歯車）を見えやすくします
st.set_page_config(page_title="Editor", layout="wide", initial_sidebar_state="expanded")

# GitHub Light風のモダンCSS（白基調をデフォルトに）
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap');
    
    /* 背景と文字色（白基調） */
    .stApp {
        background-color: #ffffff;
        color: #24292f;
    }

    /* エディタのスタイリング（枠線を青に固定） */
    .stTextArea textarea {
        background-color: #f6f8fa !important;
        color: #24292f !important;
        border: 1px solid #d0d7de !important;
        border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        padding: 24px !important;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    
    /* 入力中の青い枠線（赤色を上書き） */
    .stTextArea textarea:focus {
        border-color: #0969da !important;
        box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.3) !important;
        outline: none !important;
    }

    /* プレビューエリア */
    .stMarkdown { color: #24292f; }
    .stMarkdown h1, .stMarkdown h2 { border-bottom: 1px solid #d8dee4; padding-bottom: 8px; }

    /* ステータス表示 */
    .status-box {
        display: flex; align-items: center; justify-content: flex-end;
        gap: 6px; font-size: 12px; margin-bottom: 8px;
    }
    .status-dot { height: 8px; width: 8px; border-radius: 50%; }
    .dot-sync { background-color: #bf8700; animation: blink 1s infinite; }
    .dot-done { background-color: #1a7f37; }
    @keyframes blink { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }

    /* サイドバーのスタイル */
    section[data-testid="stSidebar"] {
        background-color: #f6f8fa !important;
        border-right: 1px solid #d0d7de;
    }
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

# サイドバーに歯車アイコンと設定を配置
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.divider()
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/drive.file%20https://www.googleapis.com/auth/drive.install&access_type=offline&prompt=consent"
    st.link_button("🔄 Re-connect Drive", auth_url, use_container_width=True)
    st.info("Files are auto-synced to Google Drive.")

if "state" in params and "code" in params:
    try:
        state_dict = json.loads(params["state"])
        file_id = state_dict.get("ids", [None])[0]
        
        if 'access_token' not in st.session_state:
            st.session_state.access_token = get_credentials(params["code"]).get("access_token")

        if file_id and 'markdown_content' not in st.session_state:
            st.session_state.markdown_content = download_file(file_id, st.session_state.access_token) or ""

        # 保存ステータス（右上に配置）
        col_st = st.columns([1])[0]
        with col_st:
            if 'is_saving' in st.session_state and st.session_state.is_saving:
                st.markdown('<div class="status-box"><span class="status-dot dot-sync"></span><span style="color:#bf8700">Saving...</span></div>', unsafe_allow_html=True)
            elif 'last_saved' in st.session_state:
                st.markdown(f'<div class="status-box"><span class="status-dot dot-done"></span><span style="color:#1a7f37">Synced at {st.session_state.last_saved}</span></div>', unsafe_allow_html=True)

        # エディタ & プレビュー
        ed_col, pr_col = st.columns([1, 1], gap="medium")
        
        with ed_col:
            content = st.text_area(
                "editor", value=st.session_state.markdown_content,
                height=850, label_visibility="collapsed"
            )
            
            if content != st.session_state.markdown_content:
                st.session_state.is_saving = True
                if save_to_drive(file_id, st.session_state.access_token, content):
                    st.session_state.markdown_content = content
                    st.session_state.last_saved = datetime.datetime.now().strftime("%H:%M:%S")
                    st.session_state.is_saving = False
                    st.rerun()

        with pr_col:
            st.markdown(st.session_state.markdown_content)

    except Exception as e:
        st.error("Authentication error. Please reopen from Google Drive.")
else:
    st.info("Google Driveの「アプリで開く」から起動してください。")
