import streamlit as st
import json
import requests
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# --- ページ設定 ---
st.set_page_config(page_title="Markdown Editor", layout="wide")

# --- セキュリティ設定 (Streamlit Secrets) ---
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
except KeyError:
    st.error("Secrets（CLIENT_ID, CLIENT_SECRET）が設定されていません。")
    st.stop()

REDIRECT_URI = "https://markdown-editor.streamlit.app/"

# 認証用URL（書き込み権限 drive.file を含む）
auth_url = (
    f"https://accounts.google.com/o/oauth2/v2/auth?"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={REDIRECT_URI}&"
    f"response_type=code&"
    f"scope=https://www.googleapis.com/auth/drive.file%20https://www.googleapis.com/auth/drive.install"
    f"&access_type=offline&prompt=consent"
)

# --- 関数：認証コードをトークンに変換 ---
def get_credentials(auth_code):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    res = requests.post(token_url, data=data)
    return res.json()

# --- 関数：ファイル読み込み（UTF-8） ---
def download_file(file_id, access_token):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.content.decode('utf-8')
    return None

# --- 関数：Googleドライブへ自動保存 ---
def save_to_drive(file_id, access_token, content):
    metadata = {'credentials': Credentials(access_token)}
    service = build('drive', 'v3', credentials=metadata['credentials'])
    
    fh = io.BytesIO(content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/markdown', resumable=True)
    
    try:
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False

# --- メインロジック ---
with st.sidebar:
    st.markdown("### ⚙️ 接続設定")
    st.markdown(f'[🔗 Google Driveと連携を更新]({auth_url})')
    if 'last_saved' in st.session_state:
        st.info(f"最終保存: {st.session_state.last_saved}")

query_params = st.query_params

if "state" in query_params and "code" in query_params:
    try:
        state_dict = json.loads(query_params["state"])
        file_id = state_dict.get("ids", [None])[0]
        auth_code = query_params["code"]

        # トークン取得
        if 'access_token' not in st.session_state:
            tokens = get_credentials(auth_code)
            st.session_state.access_token = tokens.get("access_token")

        # 初回ファイル読み込み
        if file_id and 'markdown_content' not in st.session_state:
            content = download_file(file_id, st.session_state.access_token)
            st.session_state.markdown_content = content if content is not None else ""

        # 編集とプレビューの2カラム構成
        if 'markdown_content' in st.session_state:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📝 編集 (自動保存)")
                # テキストエリアの内容が変化したら save_to_drive を実行
                edited_content = st.text_area(
                    "editor",
                    value=st.session_state.markdown_content,
                    height=700,
                    label_visibility="collapsed"
                )
                
                # 内容が変更された場合のみ保存処理を実行
                if edited_content != st.session_state.markdown_content:
                    if save_to_drive(file_id, st.session_state.access_token, edited_content):
                        st.session_state.markdown_content = edited_content
                        import datetime
                        st.session_state.last_saved = datetime.datetime.now().strftime("%H:%M:%S")
                        st.rerun()

            with col2:
                st.markdown("### ✨ プレビュー")
                st.markdown(st.session_state.markdown_content)
                
    except Exception as e:
        st.error(f"エラー: {e}")
else:
    st.info("Google Driveの「アプリで開く」から起動してください。")
