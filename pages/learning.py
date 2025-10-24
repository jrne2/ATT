# pages/learning.py
from dotenv import load_dotenv
load_dotenv() # 페이지 시작 시 환경 변수 로드

from core.session import initialize_session, add_message, clear_messages
initialize_session() # 세션 초기화 확인

import streamlit as st
from core.ai import get_ai_response, transcribe_audio, text_to_audio, get_hint
from streamlit_mic_recorder import mic_recorder
import core.feature_extractor as fe
import core.analyzer as an # analyzer 모듈 import

# --- CSS 주입 코드 (사이드바 숨김) ---
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
<style>
    [data-testid="SidebarNav"] {
        display: none;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
""",
    unsafe_allow_html=True,
)
# ---------------------------

# --- 자동 기록 초기화 로직 ---
if st.session_state.get('start_new_session', False):
    clear_messages()
    st.session_state.start_new_session = False
    st.session_state.last_processed_audio_id = None
    st.session_state.current_diagnosed_level = "초보자" # 세션 시작 시 기본 수준 초기화

# --- 세션 상태 초기화 (처음 로드 시) ---
if 'last_processed_audio_id' not in st.session_state:
    st.session_state.last_processed_audio_id = None
if 'current_diagnosed_level' not in st.session_state:
    st.session_state.current_diagnosed_level = "초보자" # 기본 수준

# --- 페이지 상단: 설정값 정의 ---
language_options = {'영어': 'en-US'}
selected_language_name = st.selectbox(
    "학습할 언어를 선택하세요:",
    options=list(language_options.keys()),
    key="lang_select_main"
)
selected_language_code = language_options[selected_language_name]
# [수정] 사용자 직접 선택 라디오 버튼 제거

st.title("💬 학습하기")

# --- 1. 설정 및 조작 영역 (Expander 사용) ---
with st.expander("🎤 음성 입력 및 힌트 보기", expanded=True):
    # [수정] 자동으로 진단된 현재 수준을 표시
    st.write(f"**현재 설정:** 페르소나 '{st.session_state.persona}', **진단된 수준 '{st.session_state.current_diagnosed_level}'**, 언어 '{selected_language_name}'")
    st.divider()

    col1, col2 = st.columns([3, 1])

    with col1: # 음성 입력 컬럼
        st.write("**음성 입력 (녹음 중지 시 자동 분석):**")
        audio_info = mic_recorder(start_prompt="🎤 녹음 시작", stop_prompt="⏹️ 녹음 중지", key='recorder', format="wav", use_container_width=True)

        if audio_info and audio_info['id'] != st.session_state.get('last_processed_audio_id'):
            st.audio(audio_info['bytes'], format="audio/wav")
            wav_bytes = audio_info['bytes']
            st.session_state.last_processed_audio_id = audio_info['id']

            with st.spinner("AI가 분석 중..."):
                user_prompt_from_audio = transcribe_audio(wav_bytes, language_code=selected_language_code)
                if user_prompt_from_audio and not user_prompt_from_audio.startswith("[음성 인식"):
                    add_message("user", user_prompt_from_audio)

                    # 1. 특징 추출
                    complexity = fe.get_complexity_score(user_prompt_from_audio)
                    sentiment = fe.get_sentiment(user_prompt_from_audio)
                    keywords = fe.extract_keywords(user_prompt_from_audio)

                    # [수정] 2. 자동 수준 진단
                    diagnosed_level = an.diagnose_user_level(complexity, sentiment)
                    # 진단된 수준을 세션 상태에 저장하여 다음 힌트 생성 시 사용
                    st.session_state.current_diagnosed_level = diagnosed_level

                    # 3. AI 응답, 피드백, 점수 받기
                    response, feedback, score = get_ai_response(st.session_state.persona, user_prompt_from_audio, learning_language=selected_language_name)

                    # 사용자 메시지 로그에 특징, 점수, '진단된 수준' 추가
                    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                        st.session_state.messages[-1]['features'] = {
                            'complexity': complexity,
                            'sentiment': sentiment,
                            'score': score,
                            'keywords': keywords,
                            'diagnosed_level': diagnosed_level # 진단된 수준 기록
                        }

                    ai_audio_bytes = text_to_audio(response)
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": feedback, "audio": ai_audio_bytes})
                    st.rerun()
                else:
                    st.error(f"음성 인식 실패 또는 오류: {user_prompt_from_audio}")


    with col2: # 힌트 버튼 컬럼
        st.write("**도움 받기:**")
        if st.button("💡 힌트 보기"):
            if st.session_state.messages:
                with st.spinner("힌트를 생성 중..."):
                    # [수정] 사용자가 선택한 수준 대신, '자동으로 진단된 현재 수준'을 사용
                    hint = get_hint(st.session_state.current_diagnosed_level, st.session_state.messages, learning_language=selected_language_name)
                    st.info(f"힌트 ({st.session_state.current_diagnosed_level} 수준): {hint}")
            else:
                st.warning("대화를 먼저 시작해주세요.")

st.divider() # 설정 영역과 채팅창 분리

# --- 2. 메인 채팅 UI ---
st.write("마이크를 이용해 음성으로 대화하거나, 아래 입력창에 텍스트를 입력하세요.")

if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "feedback" in message and message["role"] == "assistant":
                st.info(message["feedback"])
            if "audio" in message and message["role"] == "assistant" and message["audio"]:
                st.audio(message["audio"], format="audio/mp3", autoplay=True)
            if "features" in message and message["role"] == "user":
                 # 진단된 레벨도 함께 표시 (옵션)
                 level_info = f", 진단 수준: {message['features'].get('diagnosed_level', 'N/A')}"
                 st.caption(f"분석: 점수({message['features'].get('score', 'N/A')}), 복잡도({message['features'].get('complexity', 0):.1f}), 감성({message['features'].get('sentiment', 0):.1f}){level_info}")
else:
    st.info("새로운 학습 세션입니다. 대화를 시작해보세요!")

if user_prompt := st.chat_input("텍스트 메시지를 입력해보세요..."):
    add_message("user", user_prompt)
    with st.spinner("AI가 분석 중..."):
        # 텍스트 입력 시에도 특징 추출 및 수준 진단 (옵션)
        complexity = fe.get_complexity_score(user_prompt)
        sentiment = fe.get_sentiment(user_prompt)
        diagnosed_level = an.diagnose_user_level(complexity, sentiment)
        st.session_state.current_diagnosed_level = diagnosed_level # 수준 업데이트

        response, feedback, score = get_ai_response(
            st.session_state.persona,
            user_prompt,
            learning_language=selected_language_name,
            feedback_language='Korean'
        )

        # 텍스트 입력 시 사용자 메시지 로그에도 특징과 점수, 진단 수준 추가
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
             st.session_state.messages[-1]['features'] = {'score': score, 'complexity': complexity, 'sentiment': sentiment, 'diagnosed_level': diagnosed_level}

        ai_audio_bytes = text_to_audio(response)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "feedback": feedback,
            "audio": ai_audio_bytes
        })
        st.rerun()

# --- 3. 대시보드로 돌아가기 버튼 ---
st.divider()
if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True):
    st.switch_page("app.py")