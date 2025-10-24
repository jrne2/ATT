# pages/learning.py
from dotenv import load_dotenv
load_dotenv()
from core.session import initialize_session, add_message, clear_messages
initialize_session()
import streamlit as st
from core.ai import get_ai_response, transcribe_audio, text_to_audio, get_hint
from streamlit_mic_recorder import mic_recorder
import core.feature_extractor as fe
import core.analyzer as an # 자동 진단 함수 사용
import re

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

# --- 자동 기록 초기화 및 세션 상태 ---
if st.session_state.get('start_new_session', False):
    clear_messages(); st.session_state.start_new_session = False
    st.session_state.last_processed_audio_id = None
    st.session_state.current_diagnosed_level = "초보자" # 세션 시작 시 기본 수준 초기화
if 'last_processed_audio_id' not in st.session_state: st.session_state.last_processed_audio_id = None
if 'current_diagnosed_level' not in st.session_state: st.session_state.current_diagnosed_level = "초보자" # 페이지 로드 시 기본값

# --- 페이지 상단: 설정값 정의 ---
language_options = {'영어': 'en-US'}
selected_language_name = st.selectbox("학습 언어:", options=list(language_options.keys()), key="lang_select_main")
selected_language_code = language_options[selected_language_name]
# --- 👇 사용자 수준 선택 라디오 버튼 제거 ---
# user_level_choice = st.radio(...)

st.title("💬 학습하기")

# --- 설정 및 조작 영역 (Expander) ---
with st.expander("🎤 음성 입력 및 힌트 보기", expanded=True):
    # --- 👇 진단된 수준 표시 ---
    st.write(f"**현재 설정:** 페르소나 '{st.session_state.persona}', 언어 '{selected_language_name}', 진단된 수준 '{st.session_state.current_diagnosed_level}'")
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
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
                    complexity = fe.get_complexity_score(user_prompt_from_audio); sentiment = fe.get_sentiment(user_prompt_from_audio); keywords = fe.extract_keywords(user_prompt_from_audio)
                    # 수준 진단
                    diagnosed_level = an.diagnose_user_level(complexity, sentiment) # sentiment 인수 포함 확인
                    st.session_state.current_diagnosed_level = diagnosed_level # 진단 결과 업데이트

                    main_output_text, is_feedback, score = get_ai_response(st.session_state.persona, user_prompt_from_audio, learning_language=selected_language_name)
                    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                        st.session_state.messages[-1]['features'] = {'complexity': complexity, 'sentiment': sentiment, 'score': score, 'keywords': keywords, 'diagnosed_level': diagnosed_level} # 진단 수준 로깅

                    ai_audio_bytes = None; log_entry = {"role": "assistant"}
                    text_for_tts = ""
                    if is_feedback:
                        log_entry["feedback"] = main_output_text
                        example_match = re.search(r'✅ 추천 표현:\s*-?\s*"([^"/]+)', main_output_text)
                        if example_match:
                             english_example = example_match.group(1).strip()
                             text_for_tts = f"You can say... {english_example}"
                    elif main_output_text:
                        log_entry["content"] = main_output_text
                        text_for_tts = main_output_text
                    if text_for_tts:
                        ai_audio_bytes = text_to_audio(text_for_tts, language_code=selected_language_code)
                        if ai_audio_bytes: log_entry["audio"] = ai_audio_bytes
                    st.session_state.messages.append(log_entry)
                    st.rerun()
                else: st.error(f"음성 인식 실패/오류: {user_prompt_from_audio}")
    with col2:
        st.write("**도움 받기:**");
        if st.button("💡 힌트 보기"):
            if st.session_state.messages:
                with st.spinner("힌트를 생성 중..."):
                    # --- 👇 자동 진단된 수준 사용 ---
                    hint = get_hint(st.session_state.current_diagnosed_level, st.session_state.messages, learning_language=selected_language_name)
                    st.info(f"힌트 ({st.session_state.current_diagnosed_level} 수준): {hint}")
            else: st.warning("대화를 먼저 시작해주세요.")
st.divider()

st.write("마이크를 이용해 음성으로 대화하거나, 아래 입력창에 텍스트를 입력하세요.")
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            display_text = ""
            if message["role"] == "user":
                display_text = message.get("content", "")
                st.markdown(display_text)
                if "features" in message:
                     level_info = f", 진단 수준: {message['features'].get('diagnosed_level', 'N/A')}"
                     st.caption(f"분석: 점수({message['features'].get('score', 'N/A')}), 복잡도({message['features'].get('complexity', 0):.1f}), 감성({message['features'].get('sentiment', 0):.1f}){level_info}")
            elif message["role"] == "assistant":
                display_text = message.get("feedback") or message.get("content", "")
                if display_text: st.markdown(display_text)
                if "audio" in message and message["audio"]:
                    st.audio(message["audio"], format="audio/mp3", autoplay=True)
else: st.info("새로운 학습 세션입니다. 대화를 시작해보세요!")

if user_prompt := st.chat_input("텍스트 메시지를 입력해보세요..."):
    add_message("user", user_prompt)
    with st.spinner("AI가 분석 중..."):
        complexity = fe.get_complexity_score(user_prompt); sentiment = fe.get_sentiment(user_prompt)
        # 수준 진단
        diagnosed_level = an.diagnose_user_level(complexity, sentiment) # sentiment 인수 포함 확인
        st.session_state.current_diagnosed_level = diagnosed_level # 수준 업데이트

        main_output_text, is_feedback, score = get_ai_response(st.session_state.persona, user_prompt, learning_language=selected_language_name)
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
             st.session_state.messages[-1]['features'] = {'score': score, 'complexity': complexity, 'sentiment': sentiment, 'diagnosed_level': diagnosed_level} # 진단 수준 로깅

        ai_audio_bytes = None; log_entry = {"role": "assistant"}
        text_for_tts = ""
        if is_feedback:
            log_entry["feedback"] = main_output_text
            example_match = re.search(r'✅ 추천 표현:\s*-?\s*"([^"/]+)', main_output_text)
            if example_match:
                 english_example = example_match.group(1).strip()
                 text_for_tts = f"You can say... {english_example}"
        elif main_output_text:
            log_entry["content"] = main_output_text
            text_for_tts = main_output_text
        if text_for_tts:
            ai_audio_bytes = text_to_audio(text_for_tts, language_code=selected_language_code)
            if ai_audio_bytes: log_entry["audio"] = ai_audio_bytes
        st.session_state.messages.append(log_entry)
        st.rerun()
st.divider()
if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True): st.switch_page("app.py")