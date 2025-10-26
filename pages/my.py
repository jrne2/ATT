# pages/my.py
import streamlit as st
from core.session import initialize_session
import pandas as pd
import altair as alt

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

initialize_session()
st.title("📊 내 정보")
st.header("학습 진행 상황 및 분석 대시보드")
st.write("---")

user_messages_with_scores = [msg for msg in st.session_state.messages if msg.get('role') == 'user' and 'features' in msg and 'score' in msg['features']]

if not user_messages_with_scores:
    st.warning("아직 분석할 점수 데이터가 없습니다. '학습하기' 페이지에서 대화를 진행해주세요!")
else:
    df = pd.DataFrame([msg['features'] for msg in user_messages_with_scores])
    df['session_index'] = range(1, len(df) + 1)
    df = df.fillna(0)

    st.subheader("📈 나의 성장 요약")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 발화 횟수", f"{len(df)}회")
    if 'score' in df.columns: col2.metric("평균 페르소나 점수", f"{df['score'].mean():.1f}점"); col3.metric("최고 점수", f"{df['score'].max()}점")
    st.divider()

    st.subheader("📊 페르소나 점수 변화 추이")
    if 'score' in df.columns:
        line_chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(x=alt.X('session_index', title='발화 순서'), y=alt.Y('score', title='페르소나 점수', scale=alt.Scale(domain=[0, 100])), tooltip=['session_index', alt.Tooltip('score', title='점수'), alt.Tooltip('complexity', title='복잡도', format='.1f'), alt.Tooltip('sentiment', title='감성', format='.1f')]).properties(title='발화 순서별 페르소나 일치율 점수 변화').interactive()
        st.altair_chart(line_chart, use_container_width=True)
        st.info("각 점은 한번의 발화를 의미합니다.")
    st.divider()

    st.subheader("💡 발화 특징 분석")
    if 'complexity' in df.columns and 'sentiment' in df.columns and 'score' in df.columns:
        scatter_chart = alt.Chart(df).mark_circle(size=80, opacity=0.7).encode(x=alt.X('complexity', title='문장 복잡도 (낮을수록 쉬움)'), y=alt.Y('score', title='페르소나 점수'), color=alt.Color('sentiment', scale=alt.Scale(scheme='redyellowgreen', domain=[-1, 1]), title='감성 점수'), size=alt.Size('score', title='페르소나 점수', legend=None), tooltip=['session_index', 'score', 'complexity', 'sentiment']).properties(title='문장 복잡도, 감성 점수와 페르소나 점수의 관계').interactive()
        st.altair_chart(scatter_chart, use_container_width=True)
        st.info("가로축은 문장 복잡도, 세로축은 페르소나 점수, 점 색깔은 감성, 점 크기는 페르소나 점수입니다.")
    st.divider()

    # --- 👇 [수정된 부분] 저장된 추천 표현 표시 ---
    st.subheader("📖 학습한 추천 표현")
    if 'learned_expressions' in st.session_state and st.session_state.learned_expressions:
        st.write("학습 중 AI가 추천한 표현들입니다. 복습에 활용해보세요.")
        # 리스트를 번호 매겨서 표시
        for i, expr in enumerate(st.session_state.learned_expressions):
            st.markdown(f"{i+1}. `{expr}`")
    else:
        st.info("아직 학습한 추천 표현이 없습니다.")
    # --- 수정 끝 ---

    st.divider()
    st.subheader("🤖 AI 종합 분석 리포트 (구현 예정)")
    st.info("향후 이 섹션에서는 전체 대화 기록을 바탕으로 AI가 생성해주는 종합 분석 리포트가 표시될 예정입니다.")

    with st.expander("📚 전체 데이터 로그 보기"):
        st.dataframe(df)
        st.write("전체 대화 기록 (JSON):")
        st.json(st.session_state.messages)

st.divider()
if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True): st.switch_page("app.py")