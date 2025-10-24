# core/session.py
import streamlit as st

def initialize_session():
    """세션 상태 변수가 없으면 초기화합니다."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "persona" not in st.session_state:
        st.session_state.persona = "자신감 넘치는 비즈니스 리더" # 기본 페르소나
    # learning.py의 초기화 로직을 위한 플래그
    if 'start_new_session' not in st.session_state:
        st.session_state.start_new_session = False

def add_message(role, content):
    """세션의 메시지 기록에 메시지를 추가합니다."""
    st.session_state.messages.append({"role": role, "content": content})

def clear_messages():
    """세션 상태에서 메시지 기록만 지웁니다."""
    if "messages" in st.session_state:
        st.session_state.messages = []