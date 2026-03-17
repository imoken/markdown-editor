import streamlit as st
import json
import requests
from googleapiclient.discovery import build

# --- ページ設定 ---
st.set_page_config(page_title="Markdown Editor", layout="wide")
st.title("Markdown Editor")

# --- セキュリティ設定 (Streamlit Secretsから読み込み) ---
# ※GitHubには書き込まず、Streamlit Cloudの管理画面で設定します
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
except KeyError:
    st.error("Secrets（CLIENT_ID, CLIENT_SECRET）が設定されていません。")
    st.stop()

REDIRECT_URI = "https://markdown-editor.streamlit.app/"

# 認証用URLの生成
auth_url = (
    f"https://accounts.google.com/o/oauth2/v2/auth?"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={REDIRECT_URI}&"
    f"response_type=code&"
    f"scope=https://www.googleapis.com/auth/drive.file%20https://www.googleapis.com/auth/drive.install"
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

# --- 関数：ファイルの中身をダウンロード ---
def download_file(file_id, access_token):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.text
    else:
        return f"エラー: ファイルの取得に失敗しました (Status: {res.status_code})"

# --- メインロジック ---
with st.sidebar:
    st.markdown("### ⚙️ 接続設定")
    st.markdown(f'[🔗 Google Driveと連携を更新]({auth_url})')

# URLパラメータ(Google Driveからの情報)を取得
query_params = st.query_params

if "state" in query_params and "code" in query_params:
    try:
        # 1. パラメータの解析
        state_dict = json.loads(query_params["state"])
        file_id = state_dict.get("ids", [None])[0]
        auth_code = query_params["code"]

        # 2. アクセストークンの取得（セッションに保存）
        if 'access_token' not in st.session_state:
            tokens = get_credentials(auth_code)
            if "access_token" in tokens:
                st.session_state.access_token = tokens["access_token"]
            else:
                st.error("認証に失敗しました。サイドバーから再連携してください。")
                st.stop()

        # 3. ファイル内容の取得（初回のみ）
        if file_id and 'markdown_content' not in st.session_state:
            with st.spinner('ファイルを読み込み中...'):
                content = download_file(file_id, st.session_state.access_token)
                st.session_state.markdown_content = content

        # 4. エディタ画面の表示
        if 'markdown_content' in st.session_state:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📝 ソース")
                # テキストエリアの変更を即反映
                new_content = st.text_area(
                    "editor", 
                    value=st.session_state.markdown_content, 
                    height=600, 
                    label_visibility="collapsed"
                )
                st.session_state.markdown_content = new_content
            with col2:
                st.markdown("### ✨ プレビュー")
                st.markdown(st.session_state.markdown_content)
                
    except Exception as e:
        st.error(f"予期せぬエラーが発生しました: {e}")
else:
    st.info("Google Driveでファイルを右クリックし、「アプリで開く」から起動してください。")
