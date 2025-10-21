# pages/learning.py
from dotenv import load_dotenv
load_dotenv()

from core.session import initialize_session, add_message
initialize_session()

import streamlit as st
from core.ai import get_ai_response, transcribe_audio, text_to_audio, get_hint
from streamlit_mic_recorder import mic_recorder
import core.feature_extractor as fe
import core.analyzer as an

# --- 1. 사이드바 UI 구성 ---
with st.sidebar:
    st.header("⚙️ 학습 설정")
    st.write(f"**페르소나:** {st.session_state.persona}")
    user_level = st.radio("당신의 수준을 선택하세요", ["초보자", "중급자"], index=1, horizontal=True)
    
    language_options = {'영어': 'en-US'}
    selected_language_name = st.selectbox("학습할 언어를 선택하세요.", options=list(language_options.keys()))
    selected_language_code = language_options[selected_language_name]

    st.divider()

    st.header("🎤 음성으로 대화하기")
    audio_info = mic_recorder(start_prompt="🎤 녹음 시작", stop_prompt="⏹️ 녹음 중지", key='recorder')

    if audio_info:
        st.audio(audio_info['bytes'], format="audio/wav")
        if st.button("음성 분석하기"):
            wav_bytes = audio_info['bytes']
            with st.spinner("AI가 분석 중..."):
                user_prompt_from_audio = transcribe_audio(wav_bytes)

                if user_prompt_from_audio:
                    add_message("user", user_prompt_from_audio)
                    
                    complexity = fe.get_complexity_score(user_prompt_from_audio)
                    sentiment = fe.get_sentiment(user_prompt_from_audio)
                    
                    response, feedback, score = get_ai_response(st.session_state.persona, user_prompt_from_audio, learning_language=selected_language_name)
                    
                    st.session_state.messages[-1]['features'] = {'complexity': complexity, 'sentiment': sentiment, 'score': score}
                    
                    ai_audio_bytes = text_to_audio(response)
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": feedback, "audio": ai_audio_bytes})
                    st.rerun()
                else:
                    st.error("음성을 인식하지 못했습니다.")
    
    st.divider()
    if st.button("💡 힌트 보여주기"):
        with st.spinner("힌트를 생성 중..."):
            hint = get_hint(user_level, st.session_state.messages, learning_language=selected_language_name)
            st.info(hint)

    st.divider()
    st.page_link("pages/my.py", label="**학습 종료 및 결과 보기**", icon="📊", use_container_width=True)


# --- 2. 메인 채팅 UI 구성 ---
st.title("💬 학습하기")
st.write("사이드바의 마이크를 이용해 음성으로 대화하거나, 아래 입력창에 텍스트를 입력하세요.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "feedback" in message:
            st.info(message["feedback"])
        if "audio" in message and message.get("role") == "assistant":
            st.audio(message["audio"], format="audio/mp3", autoplay=True)

if user_prompt := st.chat_input("텍스트 메시지를 입력해보세요..."):
    add_message("user", user_prompt)
    with st.spinner("AI가 분석 중..."):
        
        response, feedback, score = get_ai_response(
            st.session_state.persona, 
            user_prompt,
            learning_language=selected_language_name,
            feedback_language='Korean'
        )

        st.session_state.messages[-1]['features'] = {'score': score}
        
        ai_audio_bytes = text_to_audio(response)
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response, 
            "feedback": feedback,
            "audio": ai_audio_bytes
        })
        st.rerun()