import streamlit as st
import json
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="Question-Slayer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if "subject" not in st.session_state:
    st.session_state.subject = None
if "interests" not in st.session_state:
    st.session_state.interests = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}

# 스타일 설정
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #f8f5ff;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.markdown("# 🎓 AI 합")
    st.write("---")
    st.markdown("## 🤖 도우미")
    
    # 과목 선택
    subject = st.selectbox(
        "📚 학습 과목",
        ["선택하기", "정보처리", "데이터베이스", "네트워크", "보안"]
    )
    if subject != "선택하기":
        st.session_state.subject = subject
    
    # 관심사 입력
    st.markdown("### 💡 관심사")
    interests_input = st.text_input(
        "관심사를 입력하세요 (쉼표로 구분)",
        placeholder="예: IT, 게임, 요리"
    )
    if interests_input:
        st.session_state.interests = [i.strip() for i in interests_input.split(",")]
    
    st.write("---")
    if st.session_state.subject:
        st.success(f"✅ 과목: {st.session_state.subject}")
    if st.session_state.interests:
        st.info(f"✅ 관심사: {', '.join(st.session_state.interests)}")

# 메인 컨텐츠
st.markdown('<div class="main-header">🎯 Question-Slayer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">NCS 자격증 학습을 위한 AI 튜터</div>', unsafe_allow_html=True)

if not st.session_state.subject:
    st.warning("👈 왼쪽 사이드바에서 학습 과목을 선택해주세요!")
    
    st.markdown("---")
    st.markdown("### 🌟 주요 기능")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**💬 Smart Chat**\n질문하고 6가지 관점으로 설명 받기")
    with col2:
        st.markdown("**📊 Learning Insight**\n내 학습 성장을 시각화로 확인하기")
else:
    st.success(f"선택된 과목: **{st.session_state.subject}**")
    st.info("Chat 페이지에서 질문을 시작하세요! 💬")
