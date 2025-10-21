# pages/my.py
import streamlit as st
from core.session import initialize_session
import pandas as pd

initialize_session()
st.title("📊 내 정보")
st.header("학습 진행 상황 및 분석 대시보드")
st.write("---")

user_messages = [msg for msg in st.session_state.messages if msg.get('role') == 'user' and 'features' in msg]

if not user_messages:
    st.warning("아직 분석할 학습 데이터가 없습니다. '학습하기' 페이지에서 대화를 시작해주세요!")
else:
    df = pd.DataFrame([msg['features'] for msg in user_messages])
    df['session_index'] = range(1, len(df) + 1)

    st.subheader("📈 나의 성장 요약")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 발화 횟수", f"{len(df)}회")
    if 'score' in df.columns:
        col2.metric("평균 페르소나 점수", f"{df['score'].mean():.1f}점")
        col3.metric("최고 점수", f"{df['score'].max()}점")

    st.divider()
    st.subheader("📊 페르소나 점수 변화")
    if 'score' in df.columns:
        st.line_chart(df.rename(columns={'score': '페르소나 점수'}), x='session_index', y='페르소나 점수', color="#FF4B4B")
        st.info("대화를 거듭할수록 페르소나 일치율 점수가 어떻게 변하는지 보여주는 그래프입니다.")
    
    st.divider()
    st.subheader("🤖 AI 종합 분석 리포트 (구현 예정)")
    st.info("전체 대화 기록을 바탕으로 AI가 생성해주는 나의 언어 습관, 강점, 약점 등에 대한 종합 리포트가 이곳에 표시될 예정입니다.")

    with st.expander("📚 전체 데이터 로그 보기"):
        st.dataframe(df)