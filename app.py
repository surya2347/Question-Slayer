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
<p style="font-size:1.15rem; color:#555; margin-bottom:2rem;">
    <b>Question-Slayer</b>는 Bloom 분류학 기반의 맞춤형 NCS 학습 플랫폼입니다.
</p>
""", unsafe_allow_html=True)

st.markdown("### 🚀 시작하기")
st.markdown("")

col_s1, col_s2, col_s3 = st.columns(3, gap="medium")
with col_s1:
    st.markdown("""
    <div style="background:#f0f4ff;border-radius:14px;padding:24px 20px;text-align:center;border:1.5px solid #c7d2fe;">
        <div style="font-size:2.2rem;margin-bottom:10px;">📚</div>
        <div style="font-size:1.15rem;font-weight:700;color:#3730a3;margin-bottom:8px;">1. 학습 설정</div>
        <div style="font-size:0.95rem;color:#555;line-height:1.6;">왼쪽 메뉴에서 <b>Home</b>으로 이동해<br>과목과 관심사를 설정하세요</div>
    </div>
    """, unsafe_allow_html=True)
with col_s2:
    st.markdown("""
    <div style="background:#f5f0ff;border-radius:14px;padding:24px 20px;text-align:center;border:1.5px solid #ddd5f5;">
        <div style="font-size:2.2rem;margin-bottom:10px;">💬</div>
        <div style="font-size:1.15rem;font-weight:700;color:#6d28d9;margin-bottom:8px;">2. 채팅 시작</div>
        <div style="font-size:0.95rem;color:#555;line-height:1.6;"><b>Chat</b> 페이지에서<br>관점을 선택하고 질문을 입력하세요</div>
    </div>
    """, unsafe_allow_html=True)
with col_s3:
    st.markdown("""
    <div style="background:#f0fdf4;border-radius:14px;padding:24px 20px;text-align:center;border:1.5px solid #bbf7d0;">
        <div style="font-size:2.2rem;margin-bottom:10px;">📊</div>
        <div style="font-size:1.15rem;font-weight:700;color:#15803d;margin-bottom:8px;">3. 진행 확인</div>
        <div style="font-size:0.95rem;color:#555;line-height:1.6;"><b>Insight</b> 페이지에서<br>학습 통계와 진도를 확인하세요</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")
st.markdown("### 🎓 학습 팁")
st.info("💡 한 질문에 한 관점을 선택해서 질문하는 것이 학습에 효과적입니다.", icon=None)

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

st.markdown("---")
st.markdown("""
<p style="font-size:0.8rem;color:#999;line-height:1.7;text-align:center;">
본 서비스는 한국산업인력공단(NCS)의 학습모듈 데이터를 출처로 명시하고 교육적 목적으로 활용하였습니다.<br>
수록된 내용 중 국가 외 제3자 저작권이 포함된 시각 자료(도표, 삽화 등)는 기술적/법적 보호를 위해 제외하고 텍스트 기반으로 재구성되었습니다.
</p>
""", unsafe_allow_html=True)
