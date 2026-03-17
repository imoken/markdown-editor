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

# 究極のミニマル・デザインCSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap');
    
    /* 余白を極限まで削り、キャンバスを広げる */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0 !important;
        max-width: 98% !important;
    }

    /* アプリ全体のベースカラー（純白） */
    .stApp { background-color: #ffffff; }

    /* --- エディタ側（左）のスタイル --- */
    .stTextArea textarea {
        background-color: transparent !important;
        color: #24292f !important;
        border: none !important; /* 枠線を完全に消去 */
        border-right: 1px solid #eaecef !important; /* 左右を分ける極細の線のみ */
        border-radius: 0 !important;
        box-shadow: none !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 15px !important;
        line-height: 1.8 !important;
        padding: 10px 30px 10px 10px !important;
        height: 85vh !important; /* 画面の高さに自動フィット */
        resize: none !important;
    }
    
    /* フォーカス時（入力中）は、区切り線だけが鮮やかなブルーになる */
    .stTextArea textarea:focus {
        border-right: 2px solid #0969da !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* --- プレビュー側（右）のスタイル --- */
    .stMarkdown {
        padding: 10px 10px 10px 30px !important;
        font-family: 'Inter', sans-serif !important;
        color: #374151;
        height: 85vh !important;
        overflow-y: auto;
    }
    .stMarkdown h1, .stMarkdown h2 {
        color: #111827;
        font-weight: 600;
        letter-spacing: -0.02em;
        border-bottom: none; /* 下線をなくしモダンに */
        margin-top: 1.5em;
    }
    .stMarkdown p { font-size: 16px; line-height: 1.8; }
    .stMarkdown code { background-color: #f3f4f6; color: #eb5757; border-radius: 4px; padding: 0.2em 0.4em; }

    /* --- ステータス表示（極小・控えめ） --- */
    .minimal-status {
        text-align: right;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }
    .status-active { color: #0969da; }
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

# 左サイドバー（設定の隠し場所）
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.divider()
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/drive.file%20https://www.googleapis.com/auth/drive.install&access_type=offline&prompt=consent"
    st.link_button("🔄 Re-connect Drive", auth_url, use_container_width=True)
    st.caption("Press Cmd/Ctrl + Enter to sync & preview.")

if "state" in params and "code" in params:
    try:
        state_dict = json.loads(params["state"])
        file_id = state_dict.get("ids", [None])[0]
        
        if 'access_token' not in st.session_state:
            st.session_state.access_token = get_credentials(params["code"]).get("access_token")

        if file_id and 'markdown_content' not in st.session_state:
            st.session_state.markdown_content = download_file(file_id, st.session_state.access_token) or ""

        # ヘッダー：極小のステータス表示
        if 'is_saving' in st.session_state and st.session_state.is_saving:
            st.markdown('<div class="minimal-status status-active">Syncing...</div>', unsafe_allow_html=True)
        elif 'last_saved' in st.session_state:
            st.markdown(f'<div class="minimal-status">Saved {st.session_state.last_saved}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="minimal-status">Ready</div>', unsafe_allow_html=True)

        # メイン画面：枠線のない左右分割キャンバス
        ed_col, pr_col = st.columns([1, 1])
        
        with ed_col:
            content = st.text_area(
                "editor", 
                value=st.session_state.markdown_content,
                label_visibility="collapsed"
            )
            
            # 変更検知と自動保存
            if content != st.session_state.markdown_content:
                st.session_state.is_saving = True
                if save_to_drive(file_id, st.session_state.access_token, content):
                    st.session_state.markdown_content = content
                    st.session_state.last_saved = datetime.datetime.now().strftime("%H:%M")
                    st.session_state.is_saving = False
                    st.rerun()

        with pr_col:
            st.markdown(st.session_state.markdown_content)

    except Exception as e:
        st.error("Session expired. Please reopen the file from Google Drive.")
else:
    st.info("Google Driveの「アプリで開く」から起動してください。")
