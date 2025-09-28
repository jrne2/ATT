# app.py
import streamlit as st
from core.session import initialize_session
import os
from dotenv import load_dotenv
import google.generativeai as genai

# --- API 키 설정 (가장 먼저 실행) ---
# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 로드된 API 키로 Google Generative AI를 설정합니다.
# 이 설정은 앱 전체에서 유효합니다.
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- 이하 코드는 동일 ---
# 세션 초기화는 앱 시작 시 한 번만 수행
initialize_session()

st.title("🤖 AI 페르소나 미러링 튜터")
st.write("""
안녕하세요!
자신이 원하는 모습으로 외국어를 말할 수 있도록 도와주는 AI 스피치 코치입니다.
왼쪽 사이드바에서 학습하고 싶은 페르소나를 선택하고, 'Conversation' 페이지로 이동하여 대화를 시작하세요.
""")

persona = st.sidebar.selectbox(
    "학습할 페르소나를 선택하세요.",
    ("자신감 넘치는 비즈니스 리더", "친절하고 따뜻한 친구", "지적이고 논리적인 분석가"),
    key="persona_select"
)

st.session_state.persona = persona

st.sidebar.success(f"'{persona}' 페르소나 선택 완료!")