# core/session.py
import streamlit as st

def initialize_session():
    """세션 상태 변수가 없으면 초기화합니다."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "persona" not in st.session_state:
        st.session_state.persona = "자신감 넘치는 비즈니스 리더"
    if 'start_new_session' not in st.session_state:
        st.session_state.start_new_session = False
    if 'last_processed_audio_id' not in st.session_state:
        st.session_state.last_processed_audio_id = None
    if 'current_diagnosed_level' not in st.session_state:
        st.session_state.current_diagnosed_level = "초보자"
    if 'previous_score' not in st.session_state:
        st.session_state.previous_score = None
    if 'recommendation_given_last_turn' not in st.session_state:
        st.session_state.recommendation_given_last_turn = False
    if 'learned_expressions' not in st.session_state:
        st.session_state.learned_expressions = []
    # --- 👇 [수정된 부분] 현재 토픽 변수 추가 ---
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = ""
    # --- 수정 끝 ---

def add_message(role, content):
    """세션의 메시지 기록에 메시지를 추가합니다."""
    st.session_state.messages.append({"role": role, "content": content})

def clear_messages():
    """학습 세션 시작 시 관련 기록을 초기화합니다."""
    if "messages" in st.session_state:
        st.session_state.messages = []
    # --- 👇 [수정된 부분] 추천 표현 및 토픽도 함께 초기화 ---
    if 'learned_expressions' in st.session_state:
        st.session_state.learned_expressions = []
    if 'current_topic' in st.session_state:
        st.session_state.current_topic = ""
    # --- 수정 끝 ---