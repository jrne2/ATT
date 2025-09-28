# core/session.py
import streamlit as st

def initialize_session():
    """세션 상태를 초기화합니다."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "persona" not in st.session_state:
        st.session_state.persona = "자신감 넘치는 비즈니스 리더" # 기본값

def add_message(role, content):
    """메시지를 세션 기록에 추가합니다."""
    st.session_state.messages.append({"role": role, "content": content})