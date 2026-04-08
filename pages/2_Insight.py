import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="Insight - Question-Slayer",
    page_icon="📊",
    layout="wide"
)

# 스타일
st.markdown("""
<style>
    .stat-card {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #7c3aed;
    }
    .stat-label {
        font-size: 1rem;
        color: #666;
        margin-top: 5px;
    }
    .recent-item {
        background-color: #f9f9f9;
        border-left: 4px solid #7c3aed;
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 4px;
    }
    .recent-date {
        color: #999;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("# 📊 Insight")
st.markdown("내 학습을 한눈에 확인해요")
st.write("---")

# 더미 데이터 생성 (실제로는 user_profiles/ JSON 읽기)
def get_dummy_data():
    """더미 학습 이력 데이터"""
    dates = [(datetime.now() - timedelta(days=i)).strftime("%m/%d") for i in range(7, 0, -1)]
    
    # Bloom 학습 진도
    bloom_data = {
        "개념": [10, 12, 15, 16, 18, 20, 22],
        "이해": [5, 6, 8, 10, 12, 14, 15],
        "적용": [2, 3, 3, 4, 5, 6, 7],
        "분석": [1, 1, 2, 2, 3, 3, 4],
        "평가": [0, 0, 1, 1, 1, 2, 2],
        "창작": [0, 0, 0, 1, 1, 1, 1]
    }
    
    return dates, bloom_data

dates, bloom_data = get_dummy_data()

# 통계 카드
st.markdown("## 📈 학습 통계")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-number">총 질문 수</div>
        <div class="stat-number" style="color: #4f46e5;">12</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-number">이해 안함</div>
        <div class="stat-number" style="color: #dc2626;">5</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-number">현재 레벨</div>
        <div class="stat-number" style="color: #10b981;">3</div>
    </div>
    """, unsafe_allow_html=True)

st.write("---")

# Bloom 단계별 분포
st.markdown("## 🎯 Bloom 단계 변화")

# 라인 차트 (성장 곡선)
df_bloom = pd.DataFrame({
    "날짜": dates * 6,
    "수준": ["개념"]*7 + ["이해"]*7 + ["적용"]*7 + ["분석"]*7 + ["평가"]*7 + ["창작"]*7,
    "질문 수": (
        bloom_data["개념"] + 
        bloom_data["이해"] + 
        bloom_data["적용"] + 
        bloom_data["분석"] + 
        bloom_data["평가"] + 
        bloom_data["창작"]
    )
})

fig_line = px.line(
    df_bloom,
    x="날짜",
    y="질문 수",
    color="수준",
    markers=True,
    title="Bloom 단계별 학습 성장 곡선",
    color_discrete_sequence=["#7c3aed", "#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"]
)

fig_line.update_layout(
    height=400,
    hovermode="x unified",
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig_line, use_container_width=True)

# 막대 그래프 (누적 분포)
st.markdown("## 📊 누적 분포")

latest_bloom = {k: v[-1] for k, v in bloom_data.items()}
df_bar = pd.DataFrame({
    "Bloom 단계": list(latest_bloom.keys()),
    "질문 수": list(latest_bloom.values())
})

fig_bar = px.bar(
    df_bar,
    x="Bloom 단계",
    y="질문 수",
    color="Bloom 단계",
    title="Bloom 단계별 누적 질문 분포",
    color_discrete_sequence=["#7c3aed", "#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"]
)

fig_bar.update_layout(
    height=400,
    showlegend=False,
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig_bar, use_container_width=True)

st.write("---")

# 최근 질문
st.markdown("## 🔍 최근 질문")

recent_questions = [
    ("오늘", "포인터가 뭔가요?", "✅"),
    ("어제", "API 구조 설명 부탁", "😕"),
    ("3일 전", "HTTP와 HTTPS의 차이", "🔄"),
    ("1주일 전", "데이터베이스 쿼리 최적화", "✅"),
    ("2주일 전", "메모리 관리 방법", "✅"),
]

for date, question, status in recent_questions:
    st.markdown(f"""
    <div class="recent-item">
        <div><strong>{question}</strong> {status}</div>
        <div class="recent-date">{date}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("---")

# 다음 학습 추천
st.markdown("## 🎁 다음 추천 학습")

recommendation_col1, recommendation_col2 = st.columns(2)

with recommendation_col1:
    st.info("**🏆 현재 레벨 3**\n다음 단계 도달까지 70 EXP 필요합니다!")

with recommendation_col2:
    st.success("**📚 추천 학습**\n평가 단계 질문을 해보세요!")
