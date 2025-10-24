# app.py
import streamlit as st
from core.session import initialize_session, clear_messages
from dotenv import load_dotenv

st.set_page_config(layout="wide", initial_sidebar_state="collapsed") # 페이지 넓게, 사이드바 기본 숨김
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
""",
    unsafe_allow_html=True,
)

load_dotenv()
initialize_session()

st.title("AI 페르소나 미러링 튜터")
st.write("""
안녕하세요!
자신이 원하는 모습으로 외국어를 말할 수 있도록 도와주는 AI 스피치 코치입니다.
먼저 학습할 페르소나를 선택하고, 아래 버튼을 눌러 학습을 시작하거나 내 정보를 확인하세요.
""")
st.divider()

# --- 페르소나 설정 (메인 화면으로 이동) ---
st.header("페르소나 설정")
persona_options = ("자신감 넘치는 비즈니스 리더", "친절하고 따뜻한 친구", "지적이고 논리적인 분석가")
default_persona_index = persona_options.index(st.session_state.persona) if st.session_state.persona in persona_options else 0

persona = st.selectbox(
    "학습할 페르소나를 선택하세요.",
    persona_options,
    index=default_persona_index,
    key="persona_select_app"
)
# 선택 변경 시 세션 상태 업데이트
if st.session_state.persona != persona:
     st.session_state.persona = persona
     st.rerun() # 페르소나 변경 시 화면 업데이트
st.info(f"현재 페르소나: '{st.session_state.persona}'")

st.divider()

# --- 페이지 이동 버튼 ---
col1, col2 = st.columns(2)
with col1:
    if st.button("**학습 시작하기**", use_container_width=True):
        st.session_state.start_new_session = True
        st.switch_page("pages/learning.py")

with col2:
    if st.button("**내 정보 보기**", use_container_width=True):
        st.switch_page("pages/my.py")

# --- 사이드바 코드는 완전히 제거 ---