import streamlit as st

st.set_page_config(
    page_title="Question-Slayer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 CSS - 사이드바 스타일 (단순화)
st.markdown("""
<style>
    input:focus {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
    }
    
    [data-testid="stSidebar"] {
        padding: 20px !important;
    }
    
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .sidebar-section {
        padding: 0;
        margin-bottom: 16px;
        border: none;
        box-shadow: none;
        background: transparent;
    }
    
    .sidebar-subtitle {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 전역 세션 상태 초기화 — 모든 페이지가 공유하는 공통 키
_SESSION_DEFAULTS = {
    "subject_id": None,       # 영문 과목 식별자 (graph 입력용)
    "subject_label": None,    # 한글 과목 표시명 (UI 표시용)
    "interests": [],          # 비유 설명용 관심사 목록
    "messages": [],           # 대화 이력
    "perspective": None,      # 현재 선택된 관점 (영문 키)
    "session_scope_id": None, # 세션 구분자 (uuid 기반)
}
for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

# 메인 페이지
st.title("🎯 Question-Slayer")
st.markdown("### AI 기반 NCS 자격증 학습 플랫폼")
st.markdown("---")

st.markdown("""
## 👋 Welcome to Question-Slayer!

**Question-Slayer**는 Bloom 분류학 기반의 맞춤형 학습 플랫폼입니다.

### 🚀 시작하기

1. **📚 학습 설정** → 왼쪽 메뉴에서 **Home**으로 이동하여 과목과 관심사를 설정하세요
2. **💬 채팅 시작** → **Chat** 페이지에서 질문을 입력하고 학습을 시작하세요
3. **📊 진행 상황** → 실시간 통계로 학습 진도를 확인하세요

### ✨ 주요 기능

- 🎯 **Bloom 레벨별 질문** - 기억, 이해, 적용, 분석, 평가 5단계
- 🔄 **다양한 재설명 모드** - 단순화, 비유, 단계별 설명
- 📈 **개인 학습 통계** - 진도율, 이해도, 재도전 현황
- 💾 **학습 기록 저장** - 모든 질문과 답변 기록

### 🎓 학습 팁

- 모르는 내용은 **"이해 안됨"** 버튼으로 다시 설명받으세요
- **"다른 방식"** 버튼으로 다양한 설명 방식을 경험하세요
- 이해한 후 **"이해함"** 버튼으로 진도를 기록하세요

---

**질문이 있으신가요?** Chat 페이지에서 AI 튜터와 대화하세요! 🤖
""")

# 설정 상태 확인
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.session_state.get("subject_label"):
        st.success(f"✅ 현재 학습 과목: **{st.session_state.subject_label}**")
    else:
        st.info("📚 왼쪽 사이드바에서 학습 과목을 설정해주세요")
with col2:
    if st.session_state.get("interests"):
        st.success(f"✅ 관심사 {len(st.session_state.interests)}개 저장됨")
    else:
        st.info("💡 왼쪽 사이드바에서 관심사를 입력해주세요")
