# ⚡ LLM 워크플로우 - 빠른 참조 카드

## 📍 핵심 진입점

```python
# 최상위 호출 함수 (외부 인터페이스)
from core.graph import run_question_graph

result = run_question_graph(payload)
# → 최종 응답 JSON 반환
```

---

## 🔄 9단계 요약

| # | 노드 이름 | 주요 역할 | 입력값 | 출력값 |
|----|---------|---------|-------|-------|
| 1 | `init_request_node` | 정규화 | `question`, `subject_id` | normalized 상태 |
| 2 | `prerequisite_check_node` | 필수값 검증 | 상태 | `status: ok/error` |
| 3 | `analyze_question_node` | Bloom 분석 + 의도 분류 | `question` | `bloom_level`, `bloom_label`, `question_intent` |
| 4 | `resolve_collection_node` | 컬렉션 매핑 | `subject_id` | `resolved_collection_name` |
| 5 | `retrieve_context_node` | RAG 검색 | collection, query | `retrieval_context`, `citations` |
| 6 | `route_perspective_node` | 관점 선택 (우선순위 기반) | `bloom_level`, `question_intent` | `perspective` |
| 7 | `build_prompt_input_node` | LLM 입력 조립 | 누적 상태 | `prompt_input: dict` |
| 8 | `generate_answer_node` | GPT-4o-mini 호출 | `prompt_input` | `answer_draft` |
| 9 | `finalize_response_node` | 응답 포맷팅 | 전체 상태 | 최종 JSON |

---

## 🎯 관점 선택 로직 (Step 6)

```
1️⃣ selected_perspective ≠ "auto"?
   → YES: 사용자 명시화 관점 사용 ✅

2️⃣ question_intent 매핑 가능?
   → YES: QUESTION_INTENT_TO_PERSPECTIVE 적용 ✅

3️⃣ Bloom Level별 기본값
   → Lv 1~2: "concept"
   → Lv 3:   "usage"
   → Lv 4~5: "relation"
   → Lv 6:   "caution"

4️⃣ 특수 조건 체크
   auto + Lv1~2 + interests + intent=='analogy'?
   → YES: "analogy" 강제 변경
```

---

## 📊 Bloom 판별 (Step 3)

### 키워드 테이블 (`utils.py`)

```python
BLOOM_KEYWORDS = {
    1: ["무엇", "뭐", "누가", "정의", "뜻", "나열"],
    2: ["어떻게 작동", "왜", "설명", "의미"],
    3: ["활용", "적용", "사용하면", "실무"],
    4: ["차이점", "비교", "관계", "구조"],
    5: ["결합", "설계", "새로운", "개발"],
    6: ["평가", "더 나은", "장단점", "판단"],
}
```

### 신뢰도 계산

- 매칭 0개 → `confidence = 0.0` (LLM fallback 신호)
- 매칭 1개 → `confidence = 0.6`
- 매칭 2개 → `confidence = 0.75`
- 매칭 3개+ → `confidence = 0.9`

---

## 📋 GraphState 키 필드

### 입력 필드 (사용자로부터)
```python
question: str              # 필수
subject_id: str           # 필수 (3가지)
selected_perspective: str # 선택 (기본: "auto", 7가지 중 1개)
interests: list[str]      # 선택
chat_history: list[dict]  # 선택
session_scope_id: str     # 선택
```

### 분석 결과 필드
```python
normalized_question: str
question_intent: str      # concept/principle/analogy/relation/usage/caution
bloom_level: int          # 1~6
bloom_label: str          # "지식"~"평가"
bloom_confidence: float   # 0.0~0.9
improvement_tip: str
```

### 검색 결과 필드
```python
retrieval_context: str    # 최대 2200자
citations: list[dict]     # 출처 정보
retrieval_hit: bool       # 문서 발견 여부
```

### 최종 출력 필드
```python
answer: str               # 최종 답변
perspective: str          # 선택된 관점
status: str               # "ok" or "error"
debug_trace: list[dict]   # 각 노드 실행 로그
```

---

## 🔀 병렬 실행 구간

```
prerequisite_check_node ✅
    ↓
[병렬 시작]
    ├─ Thread A: analyze_question_node (Bloom, 의도)
    └─ Thread B: resolve_collection_node (컬렉션 매핑)
[병렬 종료] → 결과 병합
    ↓
retrieve_context_node (RAG 검색)
```

---

## ⚙️ 설정값 (config.py)

```python
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.6          # 창의성
LLM_MAX_TOKENS = 1000          # 최대 답변 길이

GRAPH_CHAT_HISTORY_WINDOW = 6  # 최근 6개 대화
GRAPH_RETRIEVAL_TOP_K = 5      # 검색 결과 5개
GRAPH_CONTEXT_CHAR_LIMIT = 2200  # Context 최대 크기
BLOOM_CONFIDENCE_THRESHOLD = 0.6  # 신뢰도 한계
```

---

## 🏆 컬렉션 매핑 (Step 4)

```python
{
  "requirements_analysis": {
    "label": "요구사항 확인",
    "collection_name": "ncs_LM2001020201_23v5_________20251108"
  },
  "data_io_implementation": {
    "label": "데이터 입출력 구현",
    "collection_name": "ncs_LM2001020205_23v6____________20251108"
  },
  "server_program_implementation": {
    "label": "서버 프로그램 구현",
    "collection_name": "ncs_LM2001020211_23v6____________20251108"
  }
}
```

---

## 6️⃣ 6관점 프롬프트

| 관점 | 이름 | 스타일 | 예시 대상 |
|-----|------|-------|---------|
| `concept` | 개념 중심 | 정의·특징·분류 | 초급, Bloom Lv1~2 |
| `principle` | 원리 중심 | 작동원리·인과 | 메커니즘 분석 |
| `analogy` | 비유 중심 | 실생활·관심사 | 관심사 있는 학생 |
| `relation` | 관계 중심 | 비교·구조 | 심화 학습 |
| `usage` | 활용 중심 | 실무·구현 | 응용 문제 |
| `caution` | 주의 중심 | 함정·베스트프랙 | 상급 검증 |

---

## 🛡️ 에러 처리

### Early Exit (Step 2)
```python
prerequisite_check_node에서 에러 감지
    → status: "error" 설정
    → 분석/검색 노드 스킵
    → finalize_response_node로 직접 이동
```

### Graceful Fallback
```python
검색 없음 (retrieval_hit: False)
    → 빈 context로 LLM 호출
    → build_fallback_answer()로 보수 답변 반환

LLM 호출 실패
    → build_fallback_answer()로 context 요약 반환
    → "LLM 호출 불가, 다시 시도하세요" 메시지
```

---

## 📁 파일 위치

```
core/
├── graph.py          ← 메인 워크플로우 (모든 노드)
├── config.py         ← 설정값
├── prompts.py        ← 6관점 템플릿
├── rag.py            ← RAG 검색 (get_retriever)
└── utils.py          ← Bloom 판별, 관심사 저장

pages/
└── 1_Chat.py         ← Streamlit UI (run_question_graph 호출)
```

---

## 💡 빠른 테스트

```python
# 콘솔 테스트
python -c "
from core.graph import run_question_graph, build_mock_payload

payload = build_mock_payload(
    question='데이터베이스 정규화란?',
    subject_id='data_io_implementation'
)
result = run_question_graph(payload)
print('Bloom:', result['bloom_label'])
print('Perspective:', result['perspective'])
print('Answer:', result['answer'][:100])
"
```

---

## 🎓 학습 이름 (Bloom 분류학)

| 레벨 | 한국어 | 영어 | 정의 |
|-----|-------|------|------|
| 1 | 지식 | Knowledge | 사실·용어·기본 개념 기억 |
| 2 | 이해 | Comprehension | 사실·개념 이해 및 요약 |
| 3 | 응용 | Application | 새로운 상황에서 문제 해결 |
| 4 | 분석 | Analysis | 관계·동기·원인 파악 |
| 5 | 종합 | Synthesis | 여러 요소 결합해 창출 |
| 6 | 평가 | Evaluation | 기준에 따라 판단 |

---

## 📞 외부 호출 예제

### Streamlit에서
```python
from core.graph import run_question_graph

result = run_question_graph({
    "question": st.session_state.input,
    "subject_id": "data_io_implementation",
    "selected_perspective": "auto",
    "interests": ["쉬운 설명"],
    "chat_history": st.session_state.messages
})

st.write(result["answer"])
st.caption(f"Bloom Lv{result['bloom_level']}: {result['bloom_label']}")
```

### 테스트 스크립트에서
```python
from core.graph import run_question_graph, build_mock_payload

questions = [
    ("이 개념의 정의는?", "concept"),
    ("왜 이렇게 작동하나?", "principle"),
    ("실무에서 어떻게 써?", "usage"),
]

for q, expected_intent in questions:
    payload = build_mock_payload(q, "data_io_implementation")
    result = run_question_graph(payload)
    print(f"Q: {q}")
    print(f"Intent: {result['question_intent']} (expected: {expected_intent})")
```

