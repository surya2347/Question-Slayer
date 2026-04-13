import streamlit as st
from datetime import datetime

from core.graph import run_question_graph

st.set_page_config(
    page_title="Chat - Question-Slayer",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 CSS
st.markdown("""
<style>
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
    
    .sidebar-subtitle {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 사이드바 - 현재 설정만 표시 (읽기 전용)
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎓 AI 튜터</div>', unsafe_allow_html=True)
    st.markdown('---')
    
    st.markdown('<div class="sidebar-subtitle">📚 현재 학습 과목</div>', unsafe_allow_html=True)
    if st.session_state.get("subject_label"):
        st.info(f"✅ {st.session_state.subject_label}")
    else:
        st.warning("⚙️ 과목 미설정")
    
    st.markdown('<div class="sidebar-subtitle">💡 관심사</div>', unsafe_allow_html=True)
    if st.session_state.get("interests"):
        st.info(f"✅ {', '.join(st.session_state.interests)}")
    else:
        st.warning("⚙️ 관심사 미설정")

    st.markdown('---')
    st.markdown('<div class="sidebar-subtitle">📊 학습 현황</div>', unsafe_allow_html=True)
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("총 질문 수", st.session_state.get("totalQuestions", 0))
    with col_sb2:
        st.metric("현재 레벨", st.session_state.get("currentLevel", 1))

# CSS 스타일 - 단순화 버전
st.markdown("""
<style>
    /* 입력창 기본 테두리: 검정 */
    [data-testid="stTextInput"] div[data-baseweb="input"] {
        border: 1.5px solid #333 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    /* 포커스 시: 파란색 테두리 */
    [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important;
    }
    
    .card {
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        border: 1px solid #e0e0e0;
    }
    
    .card-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    .card-subtitle {
        font-size: 0.95rem;
        color: #666;
        margin-bottom: 1rem;
    }
    
    .quest-card {
        background-color: #f3e8ff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid #ddd5e8;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .message {
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        border: none;
        border-left: 4px solid;
        animation: fadeIn 0.4s ease-in;
    }
    
    .message-user {
        background-color: #f3e8ff;
        border-left-color: #7c3aed;
    }
    
    .message-assistant {
        background-color: #f5f5f5;
        border-left-color: #4f46e5;
    }
    
    .stat {
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 8px;
        text-align: center;
        background-color: #f9f9f9;
    }
    
    .label {
        font-size: 0.85rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화 (Chat 페이지 고유 키만 — 공통 키는 app.py에서 초기화)
if "retryCount" not in st.session_state:
    st.session_state.retryCount = 0
if "understandingLevel" not in st.session_state:
    st.session_state.understandingLevel = 0
if "totalQuestions" not in st.session_state:
    st.session_state.totalQuestions = 0
if "notUnderstanding" not in st.session_state:
    st.session_state.notUnderstanding = 0
if "currentLevel" not in st.session_state:
    st.session_state.currentLevel = 1

# 관점 옵션 (key → 표시 라벨)
PERSPECTIVES: dict[str, str] = {
    "concept":   "💡 개념",
    "principle": "⚙️ 원리",
    "analogy":   "🎭 비유",
    "relation":  "🔗 관계",
    "usage":     "🛠️ 활용",
    "caution":   "⚠️ 주의사항",
}

# Bloom 단계별 뱃지 색상 (bg, text_color, name_ko)
BLOOM_BADGE: dict[int, tuple] = {
    1: ("#e8f4fd", "#1e88e5", "지식"),
    2: ("#e8f5e9", "#43a047", "이해"),
    3: ("#fff8e1", "#fb8c00", "응용"),
    4: ("#fce4ec", "#e53935", "분석"),
    5: ("#f3e5f5", "#8e24aa", "종합"),
    6: ("#e0f2f1", "#00897b", "평가"),
}



st.markdown('<div class="card-header">💬 Chat</div>', unsafe_allow_html=True)
st.markdown('<div class="card-subtitle">질문하고, 더 깊이 이해해보세요</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("**대화 내역**")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""<div class="message message-user">
            <b>👤 You</b><br>{msg['content']}
            <div style="font-size:0.75rem;color:#999;margin-top:4px;">{msg.get('time', '')}</div>
        </div>""", unsafe_allow_html=True)
    else:
        # Bloom 뱃지 렌더링
        b_level = msg.get("bloom_level", 1)
        b_bg, b_color, b_name = BLOOM_BADGE.get(b_level, BLOOM_BADGE[1])
        badge = (
            f'<span style="background:{b_bg};color:{b_color};'
            f'border:1px solid {b_color};border-radius:6px;'
            f'padding:2px 8px;font-size:0.75rem;font-weight:bold;'
            f'margin-left:6px;">Lv{b_level} {b_name}</span>'
        )
        st.markdown(f"""<div class="message message-assistant">
            <b>🤖 AI 튜터</b>{badge}<br>{msg['content']}
            <div style="font-size:0.75rem;color:#999;margin-top:4px;">{msg.get('time', '')}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# 관점 선택 버튼 (토글 방식: 다시 누르면 해제 → auto)
p_labels = list(PERSPECTIVES.values())
p_keys   = list(PERSPECTIVES.keys())
current_p = st.session_state.perspective

perspective_cols = st.columns(len(PERSPECTIVES))
for i, (key, label) in enumerate(PERSPECTIVES.items()):
    with perspective_cols[i]:
        btn_type = "primary" if current_p == key else "secondary"
        if st.button(label, use_container_width=True, key=f"perspective_{key}", type=btn_type):
            # 같은 버튼 다시 누르면 해제 (auto)
            if current_p == key:
                st.session_state.perspective = None
            else:
                st.session_state.perspective = key
            st.rerun()

col_input1, col_input2 = st.columns([6, 1])
with col_input1:
    user_input = st.text_input("질문을 입력하세요...", placeholder="예: 포인터가 뭔가요?", label_visibility="collapsed")
with col_input2:
    send_btn = st.button("➤", use_container_width=True)

if send_btn and user_input:
    # subject_id 미설정 방어
    if not st.session_state.get("subject_id"):
        st.warning("⚙️ Home 페이지에서 과목을 먼저 선택해주세요.")
    else:
        time_str = datetime.now().strftime("%H:%M")
        # 관점 미선택 시 기본값 "auto" 적용
        used_perspective = st.session_state.perspective or "auto"
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "time": time_str,
            "selected_perspective": used_perspective,
        })

        # graph 실행 — payload 구성
        payload = {
            "question": user_input,
            "subject_id": st.session_state.subject_id,
            "selected_perspective": used_perspective,
            "interests": st.session_state.get("interests", []),
            "chat_history": [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            "session_scope_id": st.session_state.get("session_scope_id"),
        }
        result = run_question_graph(payload)

        # graph 결과를 assistant 메시지로 저장
        answer_text = result.get("answer", "")
        if result.get("status") == "error" and not answer_text:
            answer_text = result.get("error_message") or "요청을 처리하지 못했습니다."

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_text,
            "time": time_str,
            "perspective": result.get("perspective"),
            "bloom_level": result.get("bloom_level"),
            "bloom_label": result.get("bloom_label"),
            "improvement_tip": result.get("improvement_tip"),
            "citations": result.get("citations", []),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
        })
        st.session_state.retryCount = 0
        st.session_state.totalQuestions += 1
        # 전송 후 관점 선택 초기화 (재선택 유도)
        st.session_state.perspective = None
        st.rerun()
