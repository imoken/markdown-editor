import streamlit as st
import json

# ページ設定（名前をMarkdown Editorに変更）
st.set_page_config(page_title="Markdown Editor", layout="wide")
st.title("Markdown Editor")
st.markdown("---")

# URLのパラメータを取得（Google Driveから渡される情報）
query_params = st.query_params

# URLに "state" というパラメータが含まれているかチェック
if "state" in query_params:
    state_str = query_params["state"]
    
    try:
        # JSON形式の文字列を辞書（辞書型データ）に変換
        state_dict = json.loads(state_str)
        file_ids = state_dict.get("ids", [])
        
        if file_ids:
            file_id = file_ids[0]
            st.success(f"✅ Google Driveからファイルを受け付けました！ (ファイルID: {file_id})")
            
            # ---------------------------------------------------------
            # ※本来はここでGoogle Drive APIを使ってテキストをダウンロードします
            # 今回はテストとして、仮のテキストを表示します
            # ---------------------------------------------------------
            dummy_content = f"# 成功！\nこれはファイルID `{file_id}` のプレビュー画面です。\n\n**次のステップ**で、Drive APIを使って実際のファイルの中身をここに読み込みます。"
            
            # セッション状態の初期化
            if 'markdown_content' not in st.session_state:
                st.session_state.markdown_content = dummy_content

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### マークダウンソース")
                # 編集エリア
                edited_text = st.text_area(
                    label="", 
                    value=st.session_state.markdown_content, 
                    height=400, 
                    label_visibility="collapsed"
                )
                st.session_state.markdown_content = edited_text
                
            with col2:
                st.markdown("### プレビュー")
                st.markdown(st.session_state.markdown_content)

    except json.JSONDecodeError:
        st.error("Google Driveからのデータ読み込みに失敗しました。")

else:
    # URLに情報がない場合（普通にアクセスした場合）
    st.info("Google Drive上でファイルを選択し、「アプリで開く」から起動してください。")
    st.write("※現在はテスト中につき、直接アクセスした場合は表示されません。")