# app.py
import streamlit as st
from core.session import initialize_session
from dotenv import load_dotenv

load_dotenv()
initialize_session()

st.title("🤖 AI 페르소나 미러링 튜터")
st.write("자신이 원하는 모습으로 외국어를 말할 수 있도록 도와주는 AI 스피치 코치입니다.")
st.write("아래 '학습 시작하기' 버튼을 눌러 튜터와 대화를 시작하세요.")
st.divider()

st.page_link("pages/learning.py", label="**학습 시작하기**", icon="💬", use_container_width=True)
st.page_link("pages/my.py", label="**내 정보 보기**", icon="📊", use_container_width=True)

with st.sidebar:
    st.header("⚙️ 페르소나 설정")
    persona = st.selectbox(
        "학습할 페르소나를 선택하세요.",
        ("자신감 넘치는 비즈니스 리더", "친절하고 따뜻한 친구", "지적이고 논리적인 분석가"),
        key="persona_select"
    )
    st.session_state.persona = persona
    st.info(f"'{persona}' 페르소나가 선택되었습니다.")