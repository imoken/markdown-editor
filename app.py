import streamlit as st
import json

# ページ設定
st.set_page_config(page_title="Markdown Editor", layout="wide")
st.title("Markdown Editor")
st.markdown("---")

# ==========================================
# 連携ボタン（サイドバーに表示）
# ==========================================
CLIENT_ID = "324958658358-qjhl7skb65l425pv35k75g18p16768e2.apps.googleusercontent.com"
REDIRECT_URI = "https://markdown-editor.streamlit.app/"

# 完璧な連携URLを自動生成（drive.install権限を含む）
auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/drive.install%20https://www.googleapis.com/auth/drive.file"

with st.sidebar:
    st.markdown("### ⚙️ 初回設定")
    st.markdown("アプリを右クリックメニューに出すためのボタンです。")
    # リンクボタンを表示
    st.markdown(f'<a href="{auth_url}" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #4285F4; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">🔗 Google Driveと連携する</a>', unsafe_allow_html=True)
# ==========================================

# URLのパラメータを取得（Google Driveから渡される情報）
query_params = st.query_params

if "state" in query_params:
    state_str = query_params["state"]
    try:
        state_dict = json.loads(state_str)
        file_ids = state_dict.get("ids", [])
        
        if file_ids:
            file_id = file_ids[0]
            st.success(f"✅ Google Driveからファイルを受け付けました！ (ファイルID: {file_id})")
            
            dummy_content = f"# 成功！\nこれはファイルID `{file_id}` のプレビュー画面です。"
            
            if 'markdown_content' not in st.session_state:
                st.session_state.markdown_content = dummy_content

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### マークダウンソース")
                edited_text = st.text_area(label="", value=st.session_state.markdown_content, height=400, label_visibility="collapsed")
                st.session_state.markdown_content = edited_text
                
            with col2:
                st.markdown("### プレビュー")
                st.markdown(st.session_state.markdown_content)

    except json.JSONDecodeError:
        st.error("Google Driveからのデータ読み込みに失敗しました。")

else:
    st.info("👈 左のサイドバーから「Google Driveと連携する」をクリックして初回設定を完了させてください。完了後、Googleドライブ上でファイルを選択し「アプリで開く」から起動できます。")
