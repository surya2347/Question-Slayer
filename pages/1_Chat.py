import streamlit as st
import json
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="Chat - Question-Slayer",
    page_icon="💬",
    layout="wide"
)

# 세션 상태 확인
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 스타일
st.markdown("""
<style>
    .chat-container {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .question-box {
        background-color: #e8d4f8;
        border-left: 4px solid #7c3aed;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .answer-box {
        background-color: #f0f0f0;
        border-left: 4px solid #4f46e5;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .bloom-badge {
        display: inline-block;
        background-color: #7c3aed;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        margin-right: 8px;
    }
    .action-button {
        margin-top: 10px;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("# 💬 Chat")
st.markdown("질문하고, 더 깊이 이해해보세요")
st.write("---")

# 현재 퀘스트 섹션
with st.container():
    st.markdown("## ⭐ 현재 퀘스트")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("**단중 생성 원리를 이해하라!**")
    with col2:
        st.markdown("**Level 2**")
    with col3:
        # 진행률 표시
        progress = 80 / 150
        st.progress(progress)
        st.caption("80 / 150 점")

st.write("---")

# 채팅 히스토리 표시
if st.session_state.chat_history:
    st.markdown("## 대화 내역")
    for chat in st.session_state.chat_history:
        # 사용자 질문
        st.markdown('<div class="question-box">', unsafe_allow_html=True)
        st.markdown(f"**👤 User ({chat['timestamp']})**")
        st.write(chat['question'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # AI 답변
        st.markdown('<div class="answer-box">', unsafe_allow_html=True)
        st.markdown("**🤖 AI 튜터**")
        st.write(chat['answer'])
        
        # Bloom 단계 표시
        st.markdown('<span class="bloom-badge">' + f"Lv. {chat['bloom_level']}: {chat['bloom_stage']}" + '</span>', unsafe_allow_html=True)
        
        # 액션 버튼
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("😕 이해 안함", key=f"not_{chat['id']}"):
                st.info("다른 설명 방식을 요청하세요!")
        with col2:
            if st.button("🔄 다른 방식", key=f"diff_{chat['id']}"):
                st.info("비유를 요청하거나 다른 예시를 해달라고 해보세요!")
        with col3:
            if st.button("✅ 이해함", key=f"understood_{chat['id']}"):
                st.success("좋습니다! 다음 질문으로 진행하세요!")
        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")

st.write("---")

# 질문 입력 섹션
st.markdown("## 새로운 질문")

col1, col2 = st.columns([5, 1])
with col1:
    question = st.text_input(
        "질문을 입력하세요...",
        placeholder="예: 포인터가 뭔가요?"
    )

with col2:
    send_button = st.button("➤", use_container_width=True, key="send_question")

if send_button and question:
    # 더미 응답 (실제로는 core/graph.py 호출)
    new_chat = {
        "id": len(st.session_state.chat_history),
        "timestamp": datetime.now().strftime("%H:%M"),
        "question": question,
        "answer": "캐릭터를 구성할 때 원리는 다음과 같습니다. 컴퓨터 메모리에 저장된 값을 참조하기 위해 사용하며, 주소를 직접 저장합니다.",
        "bloom_level": 2,
        "bloom_stage": "이해(Comprehension)",
        "perspectives": ["개념", "원리", "비유"]
    }
    st.session_state.chat_history.append(new_chat)
    st.rerun()

# 과목 확인
if st.session_state.get("subject"):
    st.info(f"✅ 현재 학습 과목: {st.session_state.subject}")
