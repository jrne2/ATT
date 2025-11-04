# pages/learning.py
from dotenv import load_dotenv
load_dotenv()
from core.session import initialize_session, add_message, clear_messages
initialize_session()
import streamlit as st
from core.ai import get_ai_response, transcribe_audio, text_to_audio, get_hint
from streamlit_mic_recorder import mic_recorder
import core.feature_extractor as fe
import core.analyzer as an
import re
import random

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

# --- 2. 세션 초기화 로직 ---
if st.session_state.get('start_new_session', False):
    clear_messages(); st.session_state.start_new_session = False
    st.session_state.last_processed_audio_id = None
    st.session_state.current_diagnosed_level = "초보자"
    st.session_state.previous_score = None
    st.session_state.recommendation_given_last_turn = False
    st.session_state.last_recommendation = None
if 'last_processed_audio_id' not in st.session_state: st.session_state.last_processed_audio_id = None
if 'current_diagnosed_level' not in st.session_state: st.session_state.current_diagnosed_level = "초보자"
if 'previous_score' not in st.session_state: st.session_state.previous_score = None
if 'recommendation_given_last_turn' not in st.session_state: st.session_state.recommendation_given_last_turn = False
if 'current_topic' not in st.session_state: st.session_state.current_topic = ""
if 'last_recommendation' not in st.session_state: st.session_state.last_recommendation = None

# --- 3. 페이지 상단 설정 (언어 선택) ---
language_options = {'영어': 'en-US'}
selected_language_name = st.selectbox("학습 언어:", options=list(language_options.keys()), key="lang_select_main")
selected_language_code = language_options[selected_language_name]

st.title("💬 학습하기")

# --- 👇 [수정된 부분] 페르소나별 '연기 가이드' 팁 ---
persona_guide_texts = {
    "토니 스타크": "💡 **Tip:** 토니 스타크처럼 **재치있고 자신감 넘치는** 느낌을 살려 말해보세요. (약간의 유머와 냉소 포함)",
    "친절하고 따뜻한 친구": "💡 **Tip:** 상대방에게 **공감하며, 따뜻하고 친절한** 느낌으로 말해보세요.",
    "자신감 넘치는 비즈니스 리더": "💡 **Tip:** **명확하고, 간결하며, 자신감 넘치는** 리더의 어조로 말해보세요."
}
current_persona = st.session_state.get("persona", "자신감 넘치는 비즈니스 리더") # app.py에서 설정된 페르소나 가져오기
guide_text = persona_guide_texts.get(current_persona, "💡 **Tip:** 선택한 페르소나의 특징을 살려 말해보세요.")
st.info(guide_text)
# --- 수정 끝 ---

# --- 4. 조작 영역 (Expander) ---
with st.expander("🎤 음성 입력 및 힌트 보기", expanded=True):
    st.write(f"**현재 설정:** 페르소나 '{current_persona}', 언어 '{selected_language_name}', 진단된 수준 '{st.session_state.current_diagnosed_level}'")
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
                    
                    # 1. 특징 추출 (복잡도, 감성, 키워드, 회피표현)
                    features = fe.analyze_text_features(current_persona, user_prompt_from_audio)
                    complexity = features.get("complexity", 0)
                    sentiment = features.get("sentiment", 0)
                    keywords = features.get("keywords_list", []) # 키워드 리스트 (analyzer.py 업데이트 필요)
                    hedges = features.get("hedges", 0)

                    # 2. AI 주관적 평가 (복잡도 필터 인수 전달)
                    last_rec = st.session_state.get('last_recommendation', None)
                    main_output_text, is_feedback, score_llm = get_ai_response(
                        current_persona, 
                        user_prompt_from_audio,
                        complexity_score=complexity, # 복잡도 필터용
                        last_recommendation=last_rec,
                        learning_language=selected_language_name
                    )
                    
                    # 3. 객관적 점수 계산 (features 딕셔너리 전달)
                    score_features = an.calculate_feature_score(current_persona, features)
                    
                    # 4. 최종 점수 (하이브리드)
                    final_score = int(score_llm * 0.5 + score_features * 0.5)
                    
                    # 5. 수준 진단 (최종 점수 기반)
                    diagnosed_level = an.diagnose_user_level(final_score)
                    st.session_state.current_diagnosed_level = diagnosed_level
                    
                    # 6. '따라하기' 패널티 적용
                    mimicking_penalty = False
                    if st.session_state.recommendation_given_last_turn and st.session_state.previous_score >= 80 and final_score < 80: mimicking_penalty = True

                    # 7. 사용자 로그에 모든 분석 결과 저장
                    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                        features_to_log = features.copy()
                        features_to_log.update({
                            'score_llm': score_llm, 'score_features': score_features, 'score': final_score, 
                            'diagnosed_level': diagnosed_level, 'mimicking_penalty': mimicking_penalty
                        })
                        st.session_state.messages[-1]['features'] = features_to_log

                    # 8. TTS 대상 결정 및 로그 기록
                    ai_audio_bytes = None; log_entry = {"role": "assistant"}
                    text_for_tts = ""; recommendation_provided_this_turn = False
                    if is_feedback:
                        log_entry["feedback"] = main_output_text
                        example_match = re.search(r'✅ 추천 표현:\s*-?\s*"([^"/]+)', main_output_text)
                        if example_match:
                             english_example = example_match.group(1).strip()
                             text_for_tts = f"You can say... {english_example}"
                             recommendation_provided_this_turn = True
                             if english_example not in st.session_state.learned_expressions: st.session_state.learned_expressions.append(english_example)
                        else: st.session_state.last_recommendation = None
                    elif main_output_text:
                        log_entry["content"] = main_output_text
                        text_for_tts = main_output_text.split('\n')[0].strip() # 영어 응답 (첫 줄)만
                        st.session_state.last_recommendation = None
                    
                    if text_for_tts:
                        ai_audio_bytes = text_to_audio(text_for_tts, language_code=selected_language_code)
                        if ai_audio_bytes: log_entry["audio"] = ai_audio_bytes
                    
                    # 9. 다음 턴을 위한 상태 업데이트
                    st.session_state.previous_score = final_score
                    st.session_state.recommendation_given_last_turn = recommendation_provided_this_turn
                    
                    st.session_state.messages.append(log_entry)
                    st.rerun()
                else: st.error(f"음성 인식 실패/오류: {user_prompt_from_audio}")
    with col2:
        st.write("**도움 받기:**");
        if st.button("💡 힌트 보기"):
            if st.session_state.messages:
                with st.spinner("힌트를 생성 중..."):
                    hint = get_hint(st.session_state.current_diagnosed_level, st.session_state.messages, learning_language=selected_language_name)
                    st.info(f"힌트 ({st.session_state.current_diagnosed_level} 수준): {hint}")
            else: st.warning("대화를 먼저 시작해주세요.")
st.divider()

# --- 5. 채팅 UI ---
st.write("마이크를 이용해 음성으로 대화하거나, 아래 입력창에 텍스트를 입력하세요.")

# [수정] 랜덤 주제어 표시 (채팅 기록 없을 때)
if not st.session_state.messages:
    if st.session_state.current_topic == "":
        topic_list_default = ["a recent movie you watched", "your weekend plans", "your favorite hobby", "what you had for lunch", "your favorite season"]
        topic_list_ironman = ["your latest gadget or tech toy", "your (over-the-top) weekend plans", "the problem you most recently solved", "your favorite (or least favorite) new trend"]
        if current_persona == "토니 스타크":
            st.session_state.current_topic = random.choice(topic_list_ironman)
        else:
            st.session_state.current_topic = random.choice(topic_list_default)
    st.info(f"💡 대화 시작 주제: **{st.session_state.current_topic}**에 대해 말해보세요.")

# 채팅 기록 표시
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            display_text = ""
            if message["role"] == "user":
                display_text = message.get("content", "")
                st.markdown(display_text)
                if "features" in message:
                     penalty_info = " (추천 의존도 높음!)" if message['features'].get('mimicking_penalty') else ""
                     level_info = f", 진단 수준: {message['features'].get('diagnosed_level', 'N/A')}"
                     # [수정] 캡션에 'similarity' 추가 (analyzer.py 수정 필요)
                     st.caption(f"분석: 점수({message['features'].get('score', 'N/A')}{penalty_info}), LLM({message['features'].get('score_llm', 'N/A')}), 특징({message['features'].get('score_features', 'N/A')}), 복잡도({message['features'].get('complexity', 0):.1f}), 감성({message['features'].get('sentiment', 0):.1f}), 유사도({message['features'].get('similarity', 0):.1f}){level_info}")
            elif message["role"] == "assistant":
                display_text = message.get("feedback") or message.get("content", "")
                if display_text: st.markdown(display_text)
                if "audio" in message and message["audio"]:
                    st.audio(message["audio"], format="audio/mp3", autoplay=True)
else:
    pass # st.info(랜덤 주제어)가 이미 표시됨

# --- 6. 텍스트 입력 처리 ---
if user_prompt := st.chat_input("텍스트 메시지를 입력해보세요..."):
    add_message("user", user_prompt)
    with st.spinner("AI가 분석 중..."):
        
        # [수정] 특징 추출 (한번에)
        features = fe.analyze_text_features(current_persona, user_prompt)
        complexity = features.get("complexity", 0)
        sentiment = features.get("sentiment", 0)
        keywords = features.get("keywords_list", []) # analyzer.py 업데이트 필요
        hedges = features.get("hedges", 0)
        
        last_rec = st.session_state.get('last_recommendation', None)
        main_output_text, is_feedback, score_llm = get_ai_response(
            current_persona, 
            user_prompt,
            complexity_score=complexity,
            last_recommendation=last_rec,
            learning_language=selected_language_name
        )
        
        # [수정] 객관적 점수 계산 (features 딕셔너리 전달)
        score_features = an.calculate_feature_score(current_persona, features)
        
        final_score = int(score_llm * 0.7 + score_features * 0.3)
        diagnosed_level = an.diagnose_user_level(final_score)
        st.session_state.current_diagnosed_level = diagnosed_level
        mimicking_penalty = False
        if st.session_state.recommendation_given_last_turn and st.session_state.previous_score >= 80 and final_score < 80: mimicking_penalty = True
        
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
             features_to_log = features.copy()
             features_to_log.update({
                 'score_llm': score_llm, 'score_features': score_features, 'score': final_score, 
                 'diagnosed_level': diagnosed_level, 'mimicking_penalty': mimicking_penalty
             })
             st.session_state.messages[-1]['features'] = features_to_log

        ai_audio_bytes = None; log_entry = {"role": "assistant"}
        text_for_tts = ""; recommendation_provided_this_turn = False
        if is_feedback:
            log_entry["feedback"] = main_output_text
            example_match = re.search(r'✅ 추천 표현:\s*-?\s*"([^"/]+)', main_output_text)
            if example_match:
                 english_example = example_match.group(1).strip()
                 text_for_tts = f"You can say... {english_example}"
                 recommendation_provided_this_turn = True
                 st.session_state.last_recommendation = english_example
                 if english_example not in st.session_state.learned_expressions: st.session_state.learned_expressions.append(english_example)
            else: st.session_state.last_recommendation = None
        elif main_output_text:
            log_entry["content"] = main_output_text
            text_for_tts = main_output_text.split('\n')[0].strip() # 영어 응답 (첫 줄)만
            st.session_state.last_recommendation = None
        
        if text_for_tts:
            ai_audio_bytes = text_to_audio(text_for_tts, language_code=selected_language_code)
            if ai_audio_bytes: log_entry["audio"] = ai_audio_bytes
        
        st.session_state.previous_score = final_score
        st.session_state.recommendation_given_last_turn = recommendation_provided_this_turn
        st.session_state.messages.append(log_entry)
        st.rerun()

# --- 7. 학습 종료 버튼 ---
st.divider()
if st.button("📊 **학습 종료 및 결과 보기**", use_container_width=True):
    st.switch_page("pages/results.py")