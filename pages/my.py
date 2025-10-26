# pages/my.py
import streamlit as st
from core.session import initialize_session
import pandas as pd
import altair as alt
from core.analyzer import PERSONA_EXPECTATIONS # analyzer에서 기대 지표 정의를 가져옴

# --- CSS 등 페이지 설정 ---
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="SidebarNav"], [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
# ---------------------------

initialize_session()
st.title("📊 내 정보")
st.header("학습 진행 상황 및 분석 대시보드")
st.write("---")

# --- 1. 데이터 준비 ---
user_messages_with_scores = [
    msg for msg in st.session_state.messages
    if msg.get('role') == 'user' and 'features' in msg and 'score' in msg['features']
]

if not user_messages_with_scores:
    st.warning("아직 분석할 점수 데이터가 없습니다. '학습하기' 페이지에서 대화를 진행해주세요!")
else:
    df = pd.DataFrame([msg['features'] for msg in user_messages_with_scores])
    df['session_index'] = range(1, len(df) + 1)
    df = df.fillna(0)

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
            y=alt.Y('score', title='페르소나 점수', scale=alt.Scale(domain=[0, 100])),
            tooltip=['session_index', alt.Tooltip('score', title='점수'), alt.Tooltip('complexity', title='복잡도', format='.1f'), alt.Tooltip('sentiment', title='감성', format='.1f')]
        ).properties(title='발화 순서별 페르소나 일치율 점수 변화').interactive()
        st.altair_chart(line_chart, use_container_width=True)
    st.divider()

    # --- 4. [수정된 부분] '타겟 존' 차트 ---
    st.subheader("💡 발화 스타일 분석 (타겟 존)")
    
    # 현재 페르소나의 기대 지표 가져오기
    current_persona = st.session_state.persona
    expectations = PERSONA_EXPECTATIONS.get(current_persona, {})

    # 타겟 존 좌표 설정 (없으면 기본값)
    x_min = expectations.get("complexity_min", 3.0)
    x_max = expectations.get("complexity_max", 15.0) # 최대값 없는 페르소나를 위해 기본값 설정
    y_min = expectations.get("sentiment_min", -1.0)
    y_max = expectations.get("sentiment_max", 1.0)
    
    st.info(f"현재 페르소나 **'{current_persona}'**의 이상적인 '타겟 존'은 **[복잡도: {x_min:.1f}~{x_max:.1f}, 감성: {y_min:.1f}~{y_max:.1f}]** 입니다.")

    if 'complexity' in df.columns and 'sentiment' in df.columns and 'score' in df.columns:
        # 타겟 존 배경 데이터
        target_data = pd.DataFrame([{'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max}])
        
        # 타겟 존 배경(Rect)
        target_rect = alt.Chart(target_data).mark_rect(
            opacity=0.2, color='green'
        ).encode(
            x=alt.X('x_min', title='문장 복잡도 (낮을수록 쉬움)', scale=alt.Scale(domain=[0, 20])),
            x2='x_max',
            y=alt.Y('y_min', title='감성 점수 (-1: 부정, +1: 긍정)', scale=alt.Scale(domain=[-1, 1])),
            y2='y_max'
        )

        # 사용자 발화(Scatter)
        scatter_plot = alt.Chart(df).mark_circle(size=80, opacity=0.7).encode(
            x=alt.X('complexity'),
            y=alt.Y('sentiment'),
            # 점수(score)에 따라 색상 변경 (낮으면 빨간색, 높으면 파란색)
            color=alt.Color('score', title='페르소나 점수', 
                            scale=alt.Scale(range=['#FF4B4B', '#0068C9'], domain=[0, 100])),
            size=alt.Size('score', title='페르소나 점수', legend=None),
            tooltip=['session_index', 'score', 'complexity', 'sentiment']
        ).properties(
            title='발화 스타일 분포 (녹색 영역이 타겟 존)'
        ).interactive()

        # 두 차트 합치기
        final_chart = target_rect + scatter_plot
        st.altair_chart(final_chart, use_container_width=True)
    
    st.info("각 점은 사용자의 발화입니다. 점들이 녹색 '타겟 존' 안에 위치하고, 색상이 파란색에 가까울수록(점수가 높을수록) 페르소나에 부합하는 발화입니다.")
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
if st.button("🏠 **대시보드로 돌아가기**", use_container_width=True):
    st.switch_page("app.py")