# pages/learning.py
from dotenv import load_dotenv
load_dotenv()
from core.session import initialize_session, add_message, clear_messages
initialize_session()
import streamlit as st
from core.ai import get_ai_response, transcribe_audio, text_to_audio, get_hint
from streamlit_mic_recorder import mic_recorder
import core.feature_extractor as fe
import re

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

# --- 자동 기록 초기화 및 세션 상태 ---
if st.session_state.get('start_new_session', False):
    clear_messages(); st.session_state.start_new_session = False
    st.session_state.last_processed_audio_id = None
    st.session_state.previous_score = None # 이전 점수 초기화
    st.session_state.recommendation_given_last_turn = False # 추천 여부 초기화
if 'last_processed_audio_id' not in st.session_state: st.session_state.last_processed_audio_id = None
if 'previous_score' not in st.session_state: st.session_state.previous_score = None
if 'recommendation_given_last_turn' not in st.session_state: st.session_state.recommendation_given_last_turn = False

# --- 페이지 상단 설정값 정의 ---
language_options = {'영어': 'en-US'}
selected_language_name = st.selectbox("학습 언어:", options=list(language_options.keys()), key="lang_select_main")
selected_language_code = language_options[selected_language_name]
user_level_choice = st.radio("힌트 수준:", ["초보자", "중급자"], index=1, horizontal=True, key="level_radio_main")

st.title("💬 학습하기")

with st.expander("🎤 음성 입력 및 힌트 보기", expanded=True):
    st.write(f"**현재 설정:** 페르소나 '{st.session_state.persona}', 언어 '{selected_language_name}', 힌트 수준 '{user_level_choice}'")
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

                    main_output_text, is_feedback, current_score = get_ai_response(st.session_state.persona, user_prompt_from_audio, learning_language=selected_language_name)

                    # --- 👇 [수정된 부분] 점수 보정 로직 ---
                    final_score = current_score # 기본값은 AI가 준 점수
                    mimicking_penalty = False # 패널티 적용 여부 플래그
                    if st.session_state.recommendation_given_last_turn and st.session_state.previous_score >= 80 and current_score < 80:
                        # 이전 턴 추천 따라해서 점수 높았는데 이번 턴에 낮으면 패널티 고려
                        # 예시: 점수를 20% 깎음 (조정 가능)
                        # final_score = int(current_score * 0.8)
                        mimicking_penalty = True # 실제 점수 대신 플래그만 기록할 수도 있음
                        print(f"--- DEBUG: Mimicking Penalty Applied (Original: {current_score}) ---")
                    # --- 수정 끝 ---

                    # 사용자 로그에 특징과 '최종' 점수 기록
                    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                        st.session_state.messages[-1]['features'] = {
                            'complexity': complexity, 'sentiment': sentiment, 'score': final_score, # 최종 점수 기록
                            'keywords': keywords, 'mimicking_penalty': mimicking_penalty # 패널티 여부 기록
                        }

                    ai_audio_bytes = None; log_entry = {"role": "assistant"}
                    text_for_tts = ""
                    recommendation_provided_this_turn = False # 이번 턴 추천 여부 초기화

                    if is_feedback:
                        log_entry["feedback"] = main_output_text
                        example_match = re.search(r'✅ 추천 표현:\s*-?\s*"([^"/]+)', main_output_text)
                        if example_match:
                             english_example = example_match.group(1).strip()
                             text_for_tts = f"You can say... {english_example}"
                             recommendation_provided_this_turn = True # 추천 표현 제공됨
                    elif main_output_text:
                        log_entry["content"] = main_output_text
                        text_for_tts = main_output_text

                    if text_for_tts:
                        ai_audio_bytes = text_to_audio(text_for_tts, language_code=selected_language_code)
                        if ai_audio_bytes: log_entry["audio"] = ai_audio_bytes

                    # 다음 턴을 위해 현재 턴의 점수와 추천 여부 기록
                    st.session_state.previous_score = final_score
                    st.session_state.recommendation_given_last_turn = recommendation_provided_this_turn

                    st.session_state.messages.append(log_entry)
                    st.rerun()
                else: st.error(f"음성 인식 실패/오류: {user_prompt_from_audio}")
    with col2:
        st.write("**도움 받기:**");
        if st.button("💡 힌트 보기"):
            if st.session_state.messages:
                with st.spinner("힌트 생성 중..."): hint = get_hint(user_level_choice, st.session_state.messages, learning_language=selected_language_name); st.info(f"힌트 ({user_level_choice}): {hint}")
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
                     penalty_info = " (추천 의존도 높음!)" if message['features'].get('mimicking_penalty') else "" # 패널티 정보 표시
                     st.caption(f"분석: 점수({message['features'].get('score', 'N/A')}{penalty_info}), 복잡도({message['features'].get('complexity', 0):.1f}), 감성({message['features'].get('sentiment', 0):.1f})")
            elif message["role"] == "assistant":
                display_text = message.get("feedback") or message.get("content", "")
                if display_text: st.markdown(display_text)
                if "audio" in message and message["audio"]: st.audio(message["audio"], format="audio/mp3", autoplay=True)
else: st.info("새로운 학습 세션입니다. 대화를 시작해보세요!")

if user_prompt := st.chat_input("텍스트 메시지를 입력해보세요..."):
    add_message("user", user_prompt)
    with st.spinner("AI가 분석 중..."):
        complexity = fe.get_complexity_score(user_prompt); sentiment = fe.get_sentiment(user_prompt)
        main_output_text, is_feedback, current_score = get_ai_response(st.session_state.persona, user_prompt, learning_language=selected_language_name)

        # --- 👇 [수정된 부분] 점수 보정 로직 (텍스트 입력) ---
        final_score = current_score
        mimicking_penalty = False
        if st.session_state.recommendation_given_last_turn and st.session_state.previous_score >= 80 and current_score < 80:
            # final_score = int(current_score * 0.8)
            mimicking_penalty = True
            print(f"--- DEBUG: Mimicking Penalty Applied (Text - Original: {current_score}) ---")
        # --- 수정 끝 ---

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
             st.session_state.messages[-1]['features'] = {'score': final_score, 'complexity': complexity, 'sentiment': sentiment, 'mimicking_penalty': mimicking_penalty} # 최종 점수, 패널티 기록

        ai_audio_bytes = None; log_entry = {"role": "assistant"}
        text_for_tts = ""
        recommendation_provided_this_turn = False
        if is_feedback:
            log_entry["feedback"] = main_output_text
            example_match = re.search(r'✅ 추천 표현:\s*-?\s*"([^"/]+)', main_output_text)
            if example_match: text_for_tts = f"You can say... {example_match.group(1).strip()}"; recommendation_provided_this_turn = True
        elif main_output_text:
            log_entry["content"] = main_output_text
            text_for_tts = main_output_text
        if text_for_tts:
            ai_audio_bytes = text_to_audio(text_for_tts, language_code=selected_language_code)
            if ai_audio_bytes: log_entry["audio"] = ai_audio_bytes

        # 다음 턴을 위해 기록
        st.session_state.previous_score = final_score
        st.session_state.recommendation_given_last_turn = recommendation_provided_this_turn

        st.session_state.messages.append(log_entry)
        st.rerun()
st.divider()
# --- 👇 [수정된 부분] 학습 종료 버튼 ---
# '학습 종료 및 결과 보기' 버튼을 누르면 results.py로 이동
if st.button("📊 **학습 종료 및 결과 보기**", use_container_width=True):
    st.switch_page("pages/results.py") # 이동할 페이지 변경