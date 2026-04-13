# 6가지 관점별 프롬프트 템플릿 - 실제 구현 가이드

> 📌 **상태**: 마크다운 계획서 완성 → 이제 실제 코드 작성 단계  
> 🌳 **브랜치**: feature/page  
> 📂 **핵심 파일**: core/prompts.py → core/graph.py → pages/1_Chat.py

---

## 🔍 현재 코드 상태 검토

### ✅ core/prompts.py
```python
# 현재 상태: 주석만 있음
# - 6관점 템플릿: 개념 / 원리 / 비유(관심사 주입) / 관계 / 활용 / 주의사항
# - Bloom 스코어링 프롬프트: ... (추가 기능)
# - 질문 교정 가이드 프롬프트: ... (추가 기능)
```

**해야 할 것**:
- [ ] 주석 제거
- [ ] 6개 상수 추가: `PROMPT_CONCEPT`, `PROMPT_PRINCIPLE`, `PROMPT_ANALOGY`, `PROMPT_RELATION`, `PROMPT_USAGE`, `PROMPT_CAUTION`
- [ ] `get_perspective_prompt()` 함수 구현

---

### ✅ core/graph.py
```python
# 현재 상태: 주석만 있음
# - 상태(State) 스키마 정의 (주석)
# - 노드 정의: 과목 탐지 → 관점 라우터 → RAG 검색 → 프롬프트 생성 → LLM 호출 (주석)
# - 엣지(분기) 정의: 관점별 RunnableBranch 라우팅 (주석)
```

**해야 할 것**:
- [ ] State 클래스 구현 (그래프에서 사용할 변수들)
- [ ] 노드 함수 구현: detect_subject, route_perspective, retrieve_context 등
- [ ] call_llm() 함수에서 prompts.py의 `get_perspective_prompt()` 호출
- [ ] 그래프 컴파일

---

### ✅ pages/1_Chat.py
```python
# 현재 상태: 기본 UI만 있음
# - 채팅 입력 UI: ✅ 있음
# - 사이드바 설정 표시: ✅ 있음
# - 실제 LLM 호출: ❌ 없음 (더미 리스폰스 사용)
# - 관점 선택 UI: ❌ 없음
```

**해야 할 것**:
- [ ] 사이드바에 관점 선택 UI 추가
- [ ] 질문 제출 시 graph.py 호출하도록 변경
- [ ] 응답 받아서 표시

---

## 📝 Phase별 구현 계획

### **Phase 1: core/prompts.py 구현** (반나절)

#### Step 1-1: 파일 구조 생성

```python
# core/prompts.py

"""
프롬프트 템플릿 모음 (6가지 관점)
- PROMPT_CONCEPT: 개념 설명
- PROMPT_PRINCIPLE: 원리 설명
- PROMPT_ANALOGY: 비유 설명 (관심사 주입)
- PROMPT_RELATION: 관계 설명
- PROMPT_USAGE: 활용 설명
- PROMPT_CAUTION: 주의사항 설명
"""

from typing import Optional

# ============================================================================
# 1️⃣ CONCEPT - 개념 설명
# ============================================================================

PROMPT_CONCEPT = """
당신은 {subject} 과목의 전문 튜터입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 위 개념/용어의 정확한 정의를 제시하세요 (한 문장).
2. 이 개념이 왜 필요한지, 어떤 배경에서 생겨났는지 설명하세요.
3. 개념을 이해하기 위한 핵심 3~4가지 용어를 나열하고 간단히 설명하세요.
4. 이해를 돕기 위한 간단한 예시 1~2개를 드세요.

【답변 형식】
**정의**: [한 문장 정의]

**배경 및 필요성**: [2~3문장]

**핵심 용어**:
- 용어1: [설명]
- 용어2: [설명]
- 용어3: [설명]
- 용어4: [설명]

**예시**: [간단한 예시 1~2개]
"""

# ============================================================================
# 2️⃣ PRINCIPLE - 원리 설명
# ============================================================================

PROMPT_PRINCIPLE = """
당신은 {subject} 과목의 기술 전문가입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념이 어떤 원리로 작동하는지 3~4단계의 프로세스로 설명하세요.
2. 각 단계 간의 인과관계를 명확히 하세요.
3. 텍스트 흐름도나 간단한 다이어그램으로 표현하세요.
4. 이 원리가 왜 이렇게 설계되었는지 이유를 설명하세요 (1~2문장).

【답변 형식】
**작동 원리 개요**: [한 문장 요약]

**단계별 프로세스**:
1. 단계1: [설명 및 결과]
2. 단계2: [설명 및 결과]
3. 단계3: [설명 및 결과]
4. 단계4: [설명 및 결과]

**흐름도**:
[텍스트 기반 다이어그램]

**설계 의도**: [왜 이렇게 설계되었나?]
"""

# ============================================================================
# 3️⃣ ANALOGY - 비유 설명 (관심사 주입)
# ============================================================================

PROMPT_ANALOGY = """
당신은 {subject} 과목의 친절한 튜터입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【사용자 배경】
관심사: {interests}

【지시사항】
1. 사용자의 관심사인 "{interests}"와 이 개념의 유사한 측면을 찾으세요.
2. 이 개념을 "{interests}"의 예시로 비유해서 설명하세요 (2~3문장).
3. 비유에서의 유사점 2~3가지를 명시하세요.
4. 비유가 한계를 갖는 부분(다른 점)이 있다면 언급하세요.
5. 결국 이 개념의 정확한 정의로 마무리 하세요.

【답변 형식】
**"{interests}"와의 비유**:
[비유 설명 2~3문장]

**유사점**:
1. 유사점1: [설명]
2. 유사점2: [설명]
3. 유사점3: [설명]

**비유의 한계**: [다른 점 언급]

**정확한 정의로 마무리**: [개념의 정확한 정의]
"""

# ============================================================================
# 4️⃣ RELATION - 관계 설명
# ============================================================================

PROMPT_RELATION = """
당신은 {subject} 과목의 체계적인 전문가입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념을 이해하기 위해 꼭 알아야 하는 선행 개념 2~3개를 나열하세요.
2. 이 개념과 자주 혼동되는 유사 개념 1~2개를 들어, 명확한 차이를 표로 정리하세요.
3. 이 개념 다음에 학습해야 할 후속 개념 2~3개를 나열하세요.
4. 전체 개념 간 관계를 간단한 흐름도로 표현하세요.

【답변 형식】
**선행 개념** (꼭 알아야 함):
1. 선행1: [간단 설명]
2. 선행2: [간단 설명]
3. 선행3: [간단 설명]

**유사 개념과의 차이**:
| 특성 | 현재 개념 | 유사 개념 1 | 유사 개념 2 |
|-----|---------|----------|----------|
| 특성1 | ... | ... | ... |
| 특성2 | ... | ... | ... |
| 특성3 | ... | ... | ... |

**후속 개념** (다음에 배울 것):
1. 후속1: [간단 설명]
2. 후속2: [간단 설명]
3. 후속3: [간단 설명]

**개념 흐름도**:
[선행1] → [선행2] → 【현재 개념】 → [후속1] → [후속2]
"""

# ============================================================================
# 5️⃣ USAGE - 활용 설명
# ============================================================================

PROMPT_USAGE = """
당신은 {subject} 과목의 실무 전문가입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념을 실무/실제 상황에서 어디에 활용하는지 설명하세요.
2. 구체적인 사용 사례 3~4가지를 시나리오 형식으로 제시하세요.
3. 각 사례에 대해 이 개념을 어떻게 적용하는지 단계별(Step 1, 2, 3...)로 설명하세요.
4. 각 사례의 기대 결과/효과를 명시하세요.
5. 이 개념을 사용할 때 주의할 점 2~3가지를 덧붙이세요.

【답변 형식】
**활용 분야**: [어디에 사용되나?]

**사용 사례 1: [상황]**
- 시나리오: [설명]
- Step 1: ...
- Step 2: ...
- Step 3: ...
- 기대 효과: [결과]

**사용 사례 2: [상황]**
- [동일 형식]

**사용 사례 3: [상황]**
- [동일 형식]

**사용 사례 4: [상황]**
- [동일 형식]

**주의사항**:
1. 주의1: [설명]
2. 주의2: [설명]
3. 주의3: [설명]
"""

# ============================================================================
# 6️⃣ CAUTION - 주의사항 설명
# ============================================================================

PROMPT_CAUTION = """
당신은 {subject} 과목의 철저한 품질 관리자입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념을 사용할 때 초보자들이 자주 하는 실수 3~5가지를 나열하세요.
2. 각 실수에 대해 왜 그런 실수가 나타나는지 원인을 설명하세요.
3. 각 실수를 예방하거나 바로잡는 방법을 제시하세요.
4. ❌(잘못된 예) vs ✅(올바른 예)로 대조해서 보여주세요.
5. 이 개념의 한계나 예외 상황이 있다면 언급하세요.

【답변 형식】
**주의사항 1: [실수 제목]**
- 증상: [어떤 문제가 나타나나?]
- 원인: [왜 이런 실수가 나타나나?]
- 예방법: [어떻게 예방하나?]
- ❌ 잘못된 예: [코드/설명]
- ✅ 올바른 예: [코드/설명]

**주의사항 2: [실수 제목]**
- [동일 형식]

**주의사항 3: [실수 제목]**
- [동일 형식]

**주의사항 4: [실수 제목]**
- [동일 형식]

**주의사항 5: [실수 제목]**
- [동일 형식]

**한계 및 예외**: [한계 설명]
"""


# ============================================================================
# 🔧 헬퍼 함수
# ============================================================================

def get_perspective_prompt(
    perspective: str,
    question: str,
    context: str,
    subject: str,
    interests: Optional[str] = None
) -> str:
    """
    선택된 관점에 맞는 프롬프트 템플릿을 반환하고 변수를 주입합니다.
    
    Args:
        perspective: 관점 (concept, principle, analogy, relation, usage, caution)
        question: 사용자 질문
        context: RAG 검색 결과
        subject: 학습 과목
        interests: 사용자 관심사 (analogy에서만 사용)
    
    Returns:
        변수가 주입된 프롬프트 문자열
    
    Raises:
        ValueError: 유효하지 않은 perspective
    """
    
    # 관점별 템플릿 맵핑
    templates = {
        "concept": PROMPT_CONCEPT,
        "principle": PROMPT_PRINCIPLE,
        "analogy": PROMPT_ANALOGY,
        "relation": PROMPT_RELATION,
        "usage": PROMPT_USAGE,
        "caution": PROMPT_CAUTION,
    }
    
    # 관점 검증
    perspective_lower = perspective.lower()
    if perspective_lower not in templates:
        raise ValueError(
            f"유효하지 않은 관점입니다. "
            f"선택 가능한 관점: {', '.join(templates.keys())}"
        )
    
    template = templates[perspective_lower]
    
    # 변수 주입
    try:
        if perspective_lower == "analogy":
            # ANALOGY는 interests 필수
            if not interests:
                interests = "일상생활"  # 기본값
            prompt = template.format(
                question=question,
                context=context,
                subject=subject,
                interests=interests
            )
        else:
            # 나머지 관점들
            prompt = template.format(
                question=question,
                context=context,
                subject=subject
            )
        
        return prompt
    
    except KeyError as e:
        raise ValueError(f"프롬프트 템플릿에 필수 변수가 부족합니다: {e}")


def validate_template() -> dict:
    """
    모든 프롬프트 템플릿의 변수를 검증합니다.
    
    Returns:
        검증 결과 (성공/실패)
    """
    results = {}
    
    templates = {
        "concept": PROMPT_CONCEPT,
        "principle": PROMPT_PRINCIPLE,
        "analogy": PROMPT_ANALOGY,
        "relation": PROMPT_RELATION,
        "usage": PROMPT_USAGE,
        "caution": PROMPT_CAUTION,
    }
    
    sample_data = {
        "question": "테스트 질문입니다",
        "context": "테스트 컨텍스트입니다",
        "subject": "테스트 과목",
        "interests": "테스트 관심사"
    }
    
    for name, template in templates.items():
        try:
            result = template.format(**sample_data)
            results[name] = {"status": "✅ OK", "message": "템플릿 검증 성공"}
        except KeyError as e:
            results[name] = {"status": "❌ FAIL", "message": f"부족한 변수: {e}"}
        except Exception as e:
            results[name] = {"status": "❌ ERROR", "message": str(e)}
    
    return results


# ============================================================================
# 테스트 (옵션)
# ============================================================================

if __name__ == "__main__":
    # 템플릿 검증
    print("=" * 60)
    print("프롬프트 템플릿 검증")
    print("=" * 60)
    
    test_result = validate_template()
    for perspective, result in test_result.items():
        print(f"\n[{perspective.upper()}] {result['status']}")
        print(f"  {result['message']}")
    
    # 샘플 프롬프트 생성
    print("\n" + "=" * 60)
    print("샘플 프롬프트 생성 (Concept)")
    print("=" * 60)
    
    sample_prompt = get_perspective_prompt(
        perspective="concept",
        question="Python 변수란 무엇입니까?",
        context="변수는 메모리에 데이터를 저장하는 기본 단위입니다.",
        subject="프로그래밍"
    )
    print(sample_prompt[:500] + "...")
```

#### Step 1-2: 검증

```bash
# 터미널에서 실행
cd /home/qps0211/Question-Slayer
python core/prompts.py
```

**기대 출력**:
```
============================================================
프롬프트 템플릿 검증
============================================================

[CONCEPT] ✅ OK
  템플릿 검증 성공

[PRINCIPLE] ✅ OK
  템플릿 검증 성공

[ANALOGY] ✅ OK
  템플릿 검증 성공

[RELATION] ✅ OK
  템플릿 검증 성공

[USAGE] ✅ OK
  템플릿 검증 성공

[CAUTION] ✅ OK
  템플릿 검증 성공
```

---

### **Phase 2: core/graph.py 연결** (1일)

#### Step 2-1: State 정의 + 필수 노드 구현

```python
# core/graph.py (개략)

from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import core.prompts as prompts
import core.rag as rag

class State(TypedDict):
    """LangGraph 상태 스키마"""
    question: str                    # 사용자 질문
    subject: str                     # 탐지된 학습 과목
    perspective: str                 # 선택된 관점 (concept/principle/...)
    context: List[str]              # RAG 검색 결과
    interests: str                   # 사용자 관심사
    answer: str                      # 최종 답변
    bloom_level: int                 # Bloom 수준 (1-6)

# 노드 함수들
def detect_subject(state: State) -> State:
    """과목 탐지"""
    state["subject"] = "프로그래밍"  # 예시
    return state

def retrieve_context(state: State) -> State:
    """RAG 검색"""
    # docs = rag.search(state["question"], subject=state["subject"])
    # state["context"] = docs
    state["context"] = ["mock context"]  # 예시
    return state

def call_llm(state: State) -> State:
    """LLM 호출 (get_perspective_prompt 사용)"""
    client = ChatOpenAI(model="gpt-4")
    
    # 프롬프트 생성
    prompt = prompts.get_perspective_prompt(
        perspective=state["perspective"],
        question=state["question"],
        context="\n".join(state["context"]),
        subject=state["subject"],
        interests=state["interests"]
    )
    
    # LLM 호출
    response = client.invoke(prompt)
    state["answer"] = response.content
    
    return state

# 그래프 구성
graph = StateGraph(State)
graph.add_node("detect_subject", detect_subject)
graph.add_node("retrieve_context", retrieve_context)
graph.add_node("call_llm", call_llm)

graph.add_edge("detect_subject", "retrieve_context")
graph.add_edge("retrieve_context", "call_llm")
graph.add_edge("call_llm", END)

graph.set_entry_point("detect_subject")

# 그래프 컴파일
compiled_graph = graph.compile()
```

#### Step 2-2: pages/1_Chat.py에서 호출

```python
# pages/1_Chat.py (부분)

import core.graph as graph_module

if user_input:
    # 그래프 실행
    result = graph_module.compiled_graph.invoke({
        "question": user_input,
        "perspective": selected_perspective,  # 사이드바에서 받음
        "subject": st.session_state.subject,
        "interests": ", ".join(st.session_state.interests) if st.session_state.interests else "",
        "bloom_level": 2  # 임시
    })
    
    # 응답 저장 및 표시
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "perspective": selected_perspective
    })
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "perspective": selected_perspective
    })
```

---

### **Phase 3: pages/1_Chat.py 완성** (반나절)

#### Step 3-1: 관점 선택 UI 추가

```python
# pages/1_Chat.py (사이드바 수정)

with st.sidebar:
    st.markdown('<div class="sidebar-title">🎓 AI 튜터</div>', unsafe_allow_html=True)
    st.markdown('---')
    
    # ... 기존 코드 ...
    
    # ⭐ 관점 선택 추가
    st.markdown('<div class="sidebar-subtitle">🎯 답변 관점 선택</div>', unsafe_allow_html=True)
    perspectives = {
        "개념": "concept",
        "원리": "principle",
        "비유": "analogy",
        "관계": "relation",
        "활용": "usage",
        "주의": "caution"
    }
    
    selected_perspective_label = st.radio(
        "답변 방식 선택",
        options=list(perspectives.keys()),
        key="perspective_radio",
        label_visibility="collapsed"
    )
    
    selected_perspective = perspectives[selected_perspective_label]
    st.session_state.selected_perspective = selected_perspective
```

#### Step 3-2: 메인 채팅 로직 수정

```python
# pages/1_Chat.py (채팅 입력 처리)

col_input1, col_input2 = st.columns([4, 1])
with col_input1:
    user_input = st.text_input(
        "질문을 입력하세요...",
        placeholder="예: 포인터가 뭔가요?",
        label_visibility="collapsed"
    )

with col_input2:
    submit_button = st.button("📤 제출", use_container_width=True)

if submit_button and user_input:
    # 그래프 실행
    from core.graph import compiled_graph
    
    with st.spinner("답변 생성 중..."):
        try:
            result = compiled_graph.invoke({
                "question": user_input,
                "perspective": st.session_state.selected_perspective,
                "subject": st.session_state.subject or "일반",
                "interests": ", ".join(st.session_state.interests) if st.session_state.interests else "",
                "bloom_level": 2
            })
            
            # 히스토리에 추가
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "time": datetime.now().strftime("%H:%M")
            })
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "time": datetime.now().strftime("%H:%M"),
                "perspective": st.session_state.selected_perspective
            })
            
            st.rerun()
        
        except Exception as e:
            st.error(f"오류 발생: {str(e)}")
```

---

## 📊 전체 구현 체크리스트

### Phase 1: core/prompts.py
- [ ] 6개 상수 작성 (PROMPT_CONCEPT ~ PROMPT_CAUTION)
- [ ] `get_perspective_prompt()` 함수 구현
- [ ] `validate_template()` 함수 구현
- [ ] `python core/prompts.py` 실행해 검증

### Phase 2: core/graph.py
- [ ] State TypedDict 정의
- [ ] detect_subject 노드 구현
- [ ] retrieve_context 노드 구현 (RAG 호출)
- [ ] call_llm 노드 구현 (prompts.get_perspective_prompt 호출)
- [ ] 그래프 구성 및 컴파일
- [ ] compiled_graph 외부에서 접근 가능하게 exports

### Phase 3: pages/1_Chat.py
- [ ] 사이드바에 관점 선택 UI 추가
- [ ] 질문 제출 시 compiled_graph 호출
- [ ] 응답 받아서 표시
- [ ] st.rerun()으로 UI 업데이트

---

## 🔄 Git 워크플로우

```bash
# 각 Phase 완료 후 커밋
git add -A
git commit -m "feat: Phase 1 - 6가지 관점 프롬프트 템플릿 구현"

# 최종 완성 후 PR
git push origin feature/page
# GitHub에서 PR 생성: feature/page → dev
```

---

## ✅ 검증 전략

### 로컬 테스트 (Phase별)

**Phase 1 검증**:
```bash
python core/prompts.py
# 모든 템플릿 ✅ OK 확인
```

**Phase 2 검증**:
```python
# 터미널
from core.graph import compiled_graph

result = compiled_graph.invoke({
    "question": "Python 변수란?",
    "perspective": "concept",
    "subject": "프로그래밍",
    "interests": "게임 개발",
    "bloom_level": 2
})

print(result["answer"])
```

**Phase 3 검증**:
```bash
streamlit run app.py
# 1_Chat.py 페이지 접속
# 사이드바에서 관점 선택 후 질문 제출하고 답변 확인
```

---

## 📝 예상 결과물

**프롬프트 템플릿 동작 흐름**:
```
사용자 질문 "Python 변수란?"
    ↓
사용자가 "비유" 관점 선택
    ↓
prompts.get_perspective_prompt(
    perspective="analogy",
    question="Python 변수란?",
    context="변수는 메모리 주소를 저장하는 ...",
    subject="프로그래밍",
    interests="게임 개발"
)
    ↓
PROMPT_ANALOGY 템플릿에 변수 주입
    ↓
"게임 개발"과 "변수"의 비유로 설명
    ↓
"변수는 게임의 캐릭터 스탯처럼..."
```

---

## 🎯 최종 체크

이 가이드가:
- ✅ 현재 코드 상태 반영
- ✅ Phase별 구체적 구현 방법 제시
- ✅ 테스트 방법 명시
- ✅ Git 워크플로우 포함
- ✅ 1-2일 내 구현 가능한 규모
