# pages/1_💬_Conversation.py
import streamlit as st
from core.session import add_message
from core.ai import get_ai_response, transcribe_audio # transcribe_audio 함수 import
from streamlit_mic_recorder import mic_recorder

st.title("💬 Conversation")
st.write(f"현재 **'{st.session_state.persona}'** 페르소나로 대화 연습을 진행합니다.")

# --- 음성 녹음 UI ---
st.write("### 🎤 음성으로 대화하기")
st.info("아래 아이콘을 클릭하여 녹음을 시작하고, 다시 클릭하여 녹음을 중지하세요.")

audio_info = mic_recorder(
    start_prompt="🎤 녹음 시작",
    stop_prompt="⏹️ 녹음 중지",
    key='recorder'
)

if audio_info:
    st.write("---")
    st.subheader("음성 분석 요청")
    st.audio(audio_info['bytes'], format="audio/wav")

    if st.button("방금 녹음한 내용으로 AI 분석하기"):
        wav_bytes = audio_info['bytes']
        
        with st.spinner("AI가 듣고 분석하는 중..."):
            # 1. 음성을 텍스트로 변환 (STT)
            user_prompt_from_audio = transcribe_audio(wav_bytes)

            # 2. 변환된 텍스트를 채팅창에 사용자의 메시지로 추가
            add_message("user", user_prompt_from_audio)

            # 3. 변환된 텍스트로 AI의 답변과 피드백 생성 (기존 로직 재사용)
            response, feedback = get_ai_response(st.session_state.persona, user_prompt_from_audio)
            
            # 4. AI의 답변을 채팅창에 추가
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response, 
                "feedback": feedback
            })

            # 5. 화면을 새로고침하여 채팅 내역을 즉시 표시
            st.rerun()


# --- 채팅 UI ---
st.write("---")
st.write("### 💬 대화 내용")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "feedback" in message:
            with st.expander("피드백 보기"):
                st.info(message["feedback"])
                
if user_prompt := st.chat_input("텍스트 메시지를 입력해보세요..."):
    add_message("user", user_prompt)
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI가 분석 중입니다..."):
            response, feedback = get_ai_response(st.session_state.persona, user_prompt)
            st.markdown(response)
            with st.expander("피드백 보기"):
                st.info(feedback)
    
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response, 
        "feedback": feedback
    })