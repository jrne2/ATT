# pages/my.py
import streamlit as st
from core.session import initialize_session
import pandas as pd
import altair as alt
# 'core/analyzer'는 이제 이 파일에서 직접 필요하지 않습니다.
# from core.analyzer import PERSONA_EXPECTATIONS 

# --- CSS 등 페이지 설정 ---
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
# ---------------------------

initialize_session()
st.title("📊 내 정보")
st.header("학습 진행 상황 및 분석 대시보드")
st.write("---")

# --- 1. 데이터 준비 ---
# 'user' 역할이고, 'features' 키와 'score_llm', 'score_features'가 모두 있는 메시지만 필터링
user_messages_with_scores = [
    msg for msg in st.session_state.messages
    if msg.get('role') == 'user' 
    and 'features' in msg 
    and 'score_llm' in msg['features']
    and 'score_features' in msg['features']
]

if not user_messages_with_scores:
    st.warning("아직 분석할 학습 데이터가 없습니다. '학습하기' 페이지에서 대화를 진행해주세요!")
else:
    df = pd.DataFrame([msg['features'] for msg in user_messages_with_scores])
    df['session_index'] = range(1, len(df) + 1)
    df = df.fillna(0) # 혹시 모를 NaN 값을 0으로 채움

    # --- 2. 핵심 지표 ---
    st.subheader("📈 나의 성장 요약")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 발화 횟수", f"{len(df)}회")
    if 'score' in df.columns:
        col2.metric("평균 페르소나 점수", f"{df['score'].mean():.1f}점")
        col3.metric("최고 점수", f"{df['score'].max()}점")
    st.divider()

    # --- 3. 성장 그래프 (라인 차트) ---
    st.subheader("📊 페르소나 점수 변화 추이")
    if 'score' in df.columns:
        line_chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X('session_index', title='발화 순서'),
            y=alt.Y('score', title='최종 점수', scale=alt.Scale(domain=[0, 100])),
            tooltip=['session_index', alt.Tooltip('score', title='최종 점수'), alt.Tooltip('score_llm', title='뉘앙스 점수'), alt.Tooltip('score_features', title='규칙 점수')]
        ).properties(title='발화 순서별 페르소나 일치율 점수 변화').interactive()
        st.altair_chart(line_chart, use_container_width=True)
    st.divider()

    # --- 4. [수정된 부분] 'AI 평가 매트릭스' 차트 ---
    st.subheader("💡 발화 스타일 분석 (AI 평가 매트릭스)")
    
    # '타겟 존' 정의: 규칙 점수 70점 이상, 뉘앙스 점수 80점 이상 (조정 가능)
    target_x_min = 70
    target_y_min = 80
    
    st.info(f"현재 페르소나 **'{st.session_state.persona}'**의 이상적인 '타겟 존'은 **[규칙 점수: {target_x_min}점 이상, 뉘앙스 점수: {target_y_min}점 이상]** 입니다.")

    if 'score_features' in df.columns and 'score_llm' in df.columns and 'score' in df.columns:
        # 타겟 존 배경 데이터
        target_data = pd.DataFrame([{'x_min': target_x_min, 'x_max': 100, 'y_min': target_y_min, 'y_max': 100}])
        
        # 타겟 존 배경(Rect)
        target_rect = alt.Chart(target_data).mark_rect(
            opacity=0.2, color='green'
        ).encode(
            x=alt.X('x_min', title='규칙 점수 (객관적)', scale=alt.Scale(domain=[0, 100])),
            x2='x_max',
            y=alt.Y('y_min', title='뉘앙스 점수 (AI 주관적)', scale=alt.Scale(domain=[0, 100])),
            y2='y_max'
        )

        # 사용자 발화(Scatter)
        scatter_plot = alt.Chart(df).mark_circle(size=80, opacity=0.7).encode(
            x=alt.X('score_features'), # X축: 객관적 규칙 점수
            y=alt.Y('score_llm'), # Y축: AI 주관적 뉘앙스 점수
            # 색깔을 '최종 점수'로
            color=alt.Color('score', title='최종 점수', 
                            scale=alt.Scale(range=['#FF4B4B', '#0068C9'], domain=[0, 100])),
            size=alt.Size('score', title='최종 점수', legend=None),
            tooltip=['session_index', 'score', 'score_llm', 'score_features', 'complexity', 'sentiment']
        ).properties(
            title='발화 스타일 분포 (녹색 영역이 타겟 존)'
        ).interactive()

        # 두 차트 합치기
        final_chart = target_rect + scatter_plot
        st.altair_chart(final_chart, use_container_width=True)
    
    st.info("""
    이 차트는 사용자의 발화가 어떻게 평가되었는지 보여줍니다:
    * **가로축 (규칙 점수):** '자신감', '어휘' 등 우리가 정한 객관적 규칙을 얼마나 잘 지켰는지 입니다.
    * **세로축 (뉘앙스 점수):** AI가 판단한 '재치', '톤' 등 주관적인 느낌입니다.
    * **녹색 '타겟 존':** 규칙과 뉘앙스를 모두 만족시킨 이상적인 영역입니다. 점들을 이 영역으로 이동시키는 것이 목표입니다!
    """)
    # --- 수정 끝 ---

    st.divider()

    # --- 5. 학습한 추천 표현 ---
    st.subheader("📖 학습한 추천 표현")
    if 'learned_expressions' in st.session_state and st.session_state.learned_expressions:
        st.write("학습 중 AI가 추천한 표현들입니다. 복습에 활용해보세요.")
        for i, expr in enumerate(st.session_state.learned_expressions):
            st.markdown(f"{i+1}. `{expr}`")
    else:
        st.info("아직 학습한 추천 표현이 없습니다.")
    
    st.divider()
    
    # --- 6. 상세 데이터 로그 ---
    with st.expander("📚 전체 데이터 로그 보기"):
        st.dataframe(df)
        st.write("전체 대화 기록 (JSON):")
        st.json(st.session_state.messages)

st.divider()
# --- 7. 페이지 이동 버튼 ---
if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True):
    st.switch_page("app.py")