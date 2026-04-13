import streamlit as st

from core.graph import SUBJECT_COLLECTION_MAP
from core.utils import save_interests, load_interests

# 고정 user_id (로그인 없는 단일 사용자 구조)
_USER_ID = "user_default"

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

# 세션 상태 초기화 (app.py 전역 초기화 보완)
if "subject_id" not in st.session_state:
    st.session_state.subject_id = None
if "subject_label" not in st.session_state:
    st.session_state.subject_label = None
if "interests" not in st.session_state:
    # 저장된 관심사가 있으면 파일에서 복원
    st.session_state.interests = load_interests(_USER_ID)

# 페이지 제목
st.markdown('<h1 style="text-align: center; color: #333; margin-bottom: 32px;">🎓 학습 설정</h1>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📚 학습 과목</div>', unsafe_allow_html=True)

    # SUBJECT_COLLECTION_MAP 기반 과목 선택 (영문 키 → 한글 표시명)
    _subject_ids = list(SUBJECT_COLLECTION_MAP.keys())
    _subject_labels = [SUBJECT_COLLECTION_MAP[k]["label"] for k in _subject_ids]
    subject_options = ["선택하기"] + _subject_labels
    current_idx = (
        _subject_labels.index(st.session_state.subject_label) + 1
        if st.session_state.subject_label in _subject_labels
        else 0
    )
    subject = st.selectbox(
        "과목 선택",
        subject_options,
        index=current_idx,
        label_visibility="collapsed",
    )
    if subject != "선택하기":
        # 한글 표시명으로부터 영문 키 역산
        _selected_idx = _subject_labels.index(subject)
        st.session_state.subject_id = _subject_ids[_selected_idx]
        st.session_state.subject_label = subject
        st.success(f"✅ {subject} 선택됨")
    else:
        st.session_state.subject_id = None
        st.session_state.subject_label = None
        st.warning("과목을 선택해주세요")

    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💡 관심사</div>', unsafe_allow_html=True)
    st.caption("비유 설명에 활용됩니다. 쉼표로 구분해 3개 이상 입력하세요.")

    interests_input = st.text_input(
        "관심사 입력",
        placeholder="예: 게임, 축구, 요리",
        label_visibility="collapsed",
        value=", ".join(st.session_state.get("interests", [])),
    )

    if st.button("관심사 저장", use_container_width=True):
        parsed = [i.strip() for i in interests_input.split(",") if i.strip()]
        if len(parsed) < 3:
            st.warning("관심사를 3개 이상 입력해주세요.")
        else:
            st.session_state.interests = parsed
            save_interests(_USER_ID, parsed)
            st.success(f"✅ {', '.join(parsed)} 저장 완료!")

    st.markdown('</div>', unsafe_allow_html=True)

# 현재 설정 상태
st.markdown("---")
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">⚙️ 현재 설정</div>', unsafe_allow_html=True)

col_status1, col_status2 = st.columns([1, 1], gap="medium")

with col_status1:
    if st.session_state.get("subject_label"):
        st.info(f"📚 **과목:** {st.session_state.subject_label}")
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
