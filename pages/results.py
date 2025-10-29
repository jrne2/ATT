# pages/results.py
import streamlit as st
from core.session import initialize_session, clear_messages # clear_messages 추가
import pandas as pd
import altair as alt

# --- CSS 등 페이지 설정 ---
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
# ---------------------------

initialize_session() # 세션 초기화 확인

st.title("🎉 학습 결과 요약")
st.header("방금 완료한 학습 세션의 결과입니다.")
st.write("---")

# --- 1. 데이터 준비 ---
# 현재 messages가 마지막 세션의 기록임
user_messages_with_scores = [
    msg for msg in st.session_state.messages
    if msg.get('role') == 'user' and 'features' in msg and 'score' in msg['features']
]

if not user_messages_with_scores:
    st.warning("분석할 학습 데이터가 없습니다. 학습을 먼저 진행해주세요!")
    # 데이터 없을 시 대시보드로 돌아가기 버튼만 표시
    st.divider()
    if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True):
        st.switch_page("app.py")
else:
    # 분석용 데이터프레임 생성
    df = pd.DataFrame([msg['features'] for msg in user_messages_with_scores])
    df['session_index'] = range(1, len(df) + 1)
    df = df.fillna(0)

    # --- 2. 핵심 지표 표시 ---
    st.subheader("📊 이번 세션 요약")
    col1, col2, col3 = st.columns(3)
    total_utterances = len(df)
    avg_score = df['score'].mean() if not df.empty else 0
    max_score = df['score'].max() if not df.empty else 0

    col1.metric("총 발화 횟수", f"{total_utterances}회")
    col2.metric("평균 페르소나 점수", f"{avg_score:.1f}점")
    col3.metric("최고 점수", f"{max_score}점")

    # (선택) 간단한 평가 메시지
    if avg_score >= 80:
        st.success("🎉 훌륭해요! 페르소나를 잘 소화하고 계시는군요!")
    elif avg_score >= 60:
        st.info("👍 잘하고 있습니다! 조금만 더 연습하면 완벽해질 거예요.")
    else:
        st.warning("🤔 조금 더 연습이 필요해 보여요. 피드백을 다시 확인해보세요!")


    st.divider()

    # --- 3. 세션 내 점수 변화 그래프 ---
    st.subheader("📈 이번 세션 점수 변화")
    if not df.empty and 'score' in df.columns:
        line_chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X('session_index', title='발화 순서'),
            y=alt.Y('score', title='페르소나 점수', scale=alt.Scale(domain=[0, 100])),
            tooltip=['session_index', alt.Tooltip('score', title='점수')]
        ).properties(
            title='이번 세션의 발화 순서별 점수 변화'
        ).interactive()
        st.altair_chart(line_chart, use_container_width=True)
    else:
        st.info("점수 데이터가 부족하여 그래프를 표시할 수 없습니다.")



    # --- 5. 네비게이션 버튼 ---
    st.divider()
    st.subheader("다음 단계")
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        # 이 버튼은 app.py로 이동 (현재 기록 유지)
        if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True):
            st.switch_page("app.py")
    with col_nav2:
        # 이 버튼은 app.py로 이동하되, 새 세션 시작 플래그 설정 (기록 초기화 준비)
        if st.button("🔁 **새 학습 시작하기**", use_container_width=True):
            st.session_state.start_new_session = True
            st.switch_page("app.py")