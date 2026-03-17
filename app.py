import streamlit as st
import json
import requests
import io
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# --- UI設定 ---
st.set_page_config(page_title="Editor", layout="wide", initial_sidebar_state="collapsed")

# モダンなデザインのためのCSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTextArea textarea {
        background-color: #161b22;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        font-family: 'Source Code Pro', monospace;
        padding: 20px;
    }
    .stMarkdown { color: #c9d1d9; }
    div[data-testid="stToolbar"] { display: none; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- セキュリティ設定 ---
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
except KeyError:
    st.error("Secrets not configured.")
    st.stop()

REDIRECT_URI = "https://markdown-editor.streamlit.app/"

# --- 関数群 ---
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

# --- メインロジック ---
query_params = st.query_params

if "state" in query_params and "code" in query_params:
    try:
        state_dict = json.loads(query_params["state"])
        file_id = state_dict.get("ids", [None])[0]
        
        if 'access_token' not in st.session_state:
            tokens = get_credentials(query_params["code"])
            st.session_state.access_token = tokens.get("access_token")

        if file_id and 'markdown_content' not in st.session_state:
            content = download_file(file_id, st.session_state.access_token)
            st.session_state.markdown_content = content if content is not None else ""

        # ヘッダーエリア
        head_col1, head_col2 = st.columns([8, 2])
        with head_col2:
            if 'last_saved' in st.session_state:
                st.caption(f"✓ Saved at {st.session_state.last_saved}")

        # エディタとプレビュー
        edit_col, prev_col = st.columns(2)
        
        with edit_col:
            edited_content = st.text_area(
                "editor", value=st.session_state.markdown_content,
                height=850, label_visibility="collapsed"
            )
            
            if edited_content != st.session_state.markdown_content:
                if save_to_drive(file_id, st.session_state.access_token, edited_content):
                    st.session_state.markdown_content = edited_content
                    st.session_state.last_saved = datetime.datetime.now().strftime("%H:%M:%S")
                    st.rerun()

        with prev_col:
            st.markdown(st.session_state.markdown_content)

        # サイドバーの設定（下部に配置）
        with st.sidebar:
            st.title("Settings")
            st.divider()
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/drive.file%20https://www.googleapis.com/auth/drive.install&access_type=offline&prompt=consent"
            st.link_button("Re-connect Google Drive", auth_url)
            st.caption("Markdown Editor v2.0")

    except Exception as e:
        st.error(f"Connection error. Please try opening the file again from Google Drive.")
else:
    st.empty()
    st.info("Please open a file from Google Drive menu 'Open with'.")
