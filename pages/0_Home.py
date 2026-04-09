import streamlit as st

st.set_page_config(
    page_title="Home - Question-Slayer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    input:focus {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
    }
    
    .container {
        max-width: 1000px;
        margin: 0 auto;
    }
    
    .section-card {
        background-color: transparent;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        border: none;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 16px;
    }
    
    .form-group {
        margin-bottom: 16px;
    }
    
    .form-label {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 8px;
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "subject" not in st.session_state:
    st.session_state.subject = None
if "interests" not in st.session_state:
    st.session_state.interests = []

# 페이지 제목
st.markdown('<h1 style="text-align: center; color: #333; margin-bottom: 32px;">🎓 학습 설정</h1>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📚 학습 과목</div>', unsafe_allow_html=True)
    
    subject = st.selectbox(
        "과목 선택",
        ["선택하기", "정보처리", "데이터베이스", "네트워크", "보안"],
        label_visibility="collapsed"
    )
    if subject != "선택하기":
        st.session_state.subject = subject
        st.success(f"✅ {subject} 선택됨")
    else:
        st.warning("과목을 선택해주세요")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💡 관심사</div>', unsafe_allow_html=True)
    
    interests_input = st.text_input(
        "관심사 입력",
        placeholder="예: IT, 게임, 요리",
        label_visibility="collapsed",
        value=", ".join(st.session_state.get("interests", []))
    )
    if interests_input:
        st.session_state.interests = [i.strip() for i in interests_input.split(",")]
        st.success(f"✅ {', '.join(st.session_state.interests)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 현재 설정 상태
st.markdown("---")
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">⚙️ 현재 설정</div>', unsafe_allow_html=True)

col_status1, col_status2 = st.columns([1, 1], gap="medium")

with col_status1:
    if st.session_state.get("subject"):
        st.info(f"📚 **과목:** {st.session_state.subject}")
    else:
        st.warning("📚 **과목:** 미설정")

with col_status2:
    if st.session_state.get("interests"):
        st.info(f"💡 **관심사:** {', '.join(st.session_state.interests)}")
    else:
        st.warning("💡 **관심사:** 미설정")

st.markdown('</div>', unsafe_allow_html=True)

# 안내 메시지
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px; margin-top: 32px;">
    <p style="font-size: 1.1rem; margin-bottom: 8px;">⬅️ 좌측 메뉴에서 <strong>Chat</strong>으로 이동하여 학습을 시작하세요!</p>
    <p style="font-size: 0.9rem;">설정한 과목과 관심사는 전체 학습 경험에 반영됩니다.</p>
</div>
""", unsafe_allow_html=True)
