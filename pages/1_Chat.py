import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Chat - Question-Slayer",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    * {
        box-sizing: border-box;
    }
    
    [data-testid="stMainBlockContainer"] {
        background: linear-gradient(135deg, #0F1117 0%, #1a1f2e 100%);
        color: #e0e0e0;
    }
    
    [data-testid="stSidebar"] {
        background: #1a1f2e;
    }
    
    .main-title {
        background: linear-gradient(90deg, #7c3aed, #4f46e5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem !important;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .subtitle {
        text-align: center;
        color: #a0aec0;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .level-badge {
        background: linear-gradient(135deg, #7c3aed, #4f46e5);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
    }
    
    .level-number {
        font-size: 2rem;
        display: block;
        margin-top: 8px;
    }
    
    .chat-container {
        background: #1a1f2e;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #2d3748;
    }
    
    .message-user {
        background: rgba(124, 58, 237, 0.15);
        border-left: 4px solid #7c3aed;
    }
    
    .message-assistant {
        background: rgba(79, 70, 229, 0.1);
        border-left: 4px solid #4f46e5;
    }
    
    .response-section {
        background: #0F1117;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        border-left: 3px solid #7c3aed;
    }
    
    .button-group {
        display: flex;
        gap: 10px;
        margin-top: 15px;
        flex-wrap: wrap;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 20px !important;
        border: none !important;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(124, 58, 237, 0.3);
    }
    
    .btn-positive {
        background: linear-gradient(135deg, #10b981, #059669) !important;
        color: white !important;
    }
    
    .btn-negative {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
        color: white !important;
    }
    
    .progress-container {
        background: #1a1f2e;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 1.5rem;
        border: 1px solid #2d3748;
    }
    
    .progress-label {
        font-size: 0.9rem;
        color: #a0aec0;
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .input-container {
        background: #1a1f2e;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #2d3748;
        margin-top: 20px;
    }
    
    .mode-badge {
        display: inline-block;
        background: rgba(124, 58, 237, 0.2);
        color: #7c3aed;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 8px;
    }
    
    .retry-warning {
        background: rgba(239, 68, 68, 0.1);
        border-left: 3px solid #ef4444;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #fca5a5;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "retryCount" not in st.session_state:
    st.session_state.retryCount = 0
if "progress" not in st.session_state:
    st.session_state.progress = 0
if "totalQuestionsAnswered" not in st.session_state:
    st.session_state.totalQuestionsAnswered = 0

def get_level(progress):
    """진행도에 따른 레벨 계산"""
    return max(1, (progress // 20) + 1)

def get_mode_from_retry(retry_count):
    """재시도 횟수에 따른 모드 결정"""
    modes = {
        0: "default",
        1: "simplify",
        2: "analogy_new",
        3: "step",
    }
    return modes.get(min(retry_count, 4), "summary") if retry_count < 4 else "summary"

def get_dummy_response(mode, question):
    """모드에 따른 더미 답변"""
    responses = {
        "default": {
            "answer": "포인터는 메모리 주소를 저장하는 변수입니다. 일반 변수가 값을 저장한다면, 포인터는 그 값이 저장된 위치(주소)를 저장합니다.",
            "analogy": "🎨 비유: 포인터는 택배의 '주소'와 같습니다. 주소를 알면 실제 물건이 어디 있는지 찾아갈 수 있죠.",
            "relation": "🔗 대응 관계: 일반 변수 (값) ↔ 포인터 (주소) → 역참조 (주소가 가리키는 값)",
            "limit": "⚠️ 한계: 포인터가 가리키는 메모리가 해제되면 오류(dangling pointer)가 발생합니다."
        },
        "simplify": {
            "answer": "포인터 = 메모리 주소",
            "analogy": "🎨 비유: 친구의 집 주소를 써놓은 메모같은 거예요.",
            "relation": "🔗 대응 관계: 메모에 주소 적음 → 그 주소로 찾아감",
            "limit": "⚠️ 한계: 주소가 틀리면 찾을 수 없어요."
        },
        "analogy_new": {
            "answer": "포인터: 책에 있는 '참고 페이지 번호'처럼 생각하세요. 실제 내용은 가리킨 페이지에 있어요.",
            "analogy": "🎨 비유: 포인터는 도서관 책의 '목차'와 같습니다. 목차는 실제 내용의 '위치'를 가리킵니다.",
            "relation": "🔗 대응 관계: 목차 (포인터) → 실제 페이지 (메모리) → 그곳의 데이터",
            "limit": "⚠️ 한계: 잘못된 페이지로 가면 원하는 정보를 못 찾습니다."
        },
        "step": {
            "answer": "Step-by-step:\n1️⃣ 메모리는 주소로 구분됩니다.\n2️⃣ 포인터는 그 주소를 저장합니다.\n3️⃣ * (역참조 연산자)로 주소가 가리키는 값을 얻습니다.",
            "analogy": "🎨 비유: 1) 우편함이 있다 (메모리) → 2) 우편함 위치 적기 (포인터) → 3) 그 위치로 가서 편지 꺼내기 (역참조)",
            "relation": "🔗 대응 관계: int x = 5; int *p = &x; (포인터 p는 x의 주소를 저장)",
            "limit": "⚠️ 한계: NULL 포인터나 유효하지 않은 주소에 접근하면 프로그램이 충돌합니다."
        },
        "summary": {
            "answer": "지금까지의 설명을 정리하면:\n- 포인터 = 메모리 주소를 저장하는 변수\n- 주소로 변수에 접근 가능\n- 함수의 인자로 주소 전달 가능\n- 동적 메모리 할당에 필수",
            "analogy": "🎨 비유: 포인터는 지도 위의 GPS 좌표와 같습니다. 좌표를 알면 원하는 장소를 정확히 찾을 수 있습니다.",
            "relation": "🔗 대응 관계: 변수 → 주소 → 포인터 → 역참조 → 값 접근",
            "limit": "⚠️ 한계: C/C++에서만 포인터를 직접 사용하며, Python/Java는 내부적으로 처리합니다."
        }
    }
    return responses.get(mode, responses["default"])

# 헤더
st.markdown('<div class="main-title">💬 Chat</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">질문하고 더 깊이 이해해보세요</div>', unsafe_allow_html=True)

# 레벨 및 진행도
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    level = get_level(st.session_state.progress)
    st.markdown(f'<div class="level-badge">이해도 레벨<div class="level-number">Lv. {level}</div></div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="progress-container"><div class="progress-label">학습 진행도</div>', unsafe_allow_html=True)
    st.progress(st.session_state.progress / 100)
    st.markdown(f'<div class="progress-label" style="margin-top: 8px; text-align: right;">{st.session_state.progress}% 완료</div></div>', unsafe_allow_html=True)

with col3:
    st.markdown(f'<div class="level-badge">질문 답변<div class="level-number">{st.session_state.totalQuestionsAnswered}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# 채팅 영역
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🤖"):
        st.write(message["content"])
        
        if message["role"] == "assistant" and "mode" in message:
            st.markdown(f'<span class="mode-badge">{message["mode"].upper()}</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 채팅 입력
user_input = st.chat_input("질문을 입력하세요...")

if user_input:
    # 사용자 메시지 추가
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # 응답 생성
    mode = get_mode_from_retry(st.session_state.retryCount)
    response_data = get_dummy_response(mode, user_input)
    
    assistant_response = f"""{response_data['answer']}

{response_data['analogy']}

{response_data['relation']}

{response_data['limit']}"""
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_response,
        "mode": mode
    })
    
    st.session_state.retryCount = 0
    st.session_state.totalQuestionsAnswered += 1
    st.rerun()

# 액션 버튼
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("❌ 이해 안됨", use_container_width=True, key="not_understand"):
            st.session_state.retryCount += 1
            if st.session_state.retryCount >= 4:
                st.markdown('<div class="retry-warning">💡 재시도가 많습니다. 요점만 간단히 정리해드려요.</div>', unsafe_allow_html=True)
            st.rerun()
    
    with col_btn2:
        if st.button("🤔 다른 설명", use_container_width=True, key="different"):
            st.session_state.retryCount = 2
            st.rerun()
    
    with col_btn3:
        if st.button("✅ 이해함", use_container_width=True, key="understood"):
            new_progress = min(100, st.session_state.progress + 10)
            st.session_state.progress = new_progress
            st.session_state.retryCount = 0
            st.success("🎉 좋습니다! 다음 질문으로 진행하세요!")
            st.rerun()
