# LLM 워크플로우 구조 가이드

> **기준**: 실제 코드 기반 (`core/graph.py`)  
> **작성일**: 2026-04-12

---

## 📍 진입점 (Entry Point)

### 1. 사용자 요청 → Payload 생성

```python
# app.py 또는 pages/1_Chat.py에서 호출
payload = {
    "question": "데이터베이스 정규화란 무엇인가요?",      # 필수
    "subject_id": "data_io_implementation",               # 필수
    "selected_perspective": "auto",                       # 선택 (기본값: "auto")
    "interests": ["쉬운 설명", "예제"],                    # 선택
    "chat_history": [...],                                # 선택
    "session_scope_id": "session-xxx"                      # 선택
}
```

### 2. 그래프 실행 (진입점 진입)

```python
# core/graph.py
result = run_question_graph(payload)
```

---

## 🔄 워크플로우 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                      WORKFLOW START                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  init_request_node     │  [1/9]
        │  ─ 요청 정규화          │
        │  ─ 상태 초기화          │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  prerequisite_check    │  [2/9]
        │  ─ 필수값 검증          │
        │  ─ 에러 조기 종료        │
        └────────┬───────┬───────┘
                 │       │
        ┌────────▼┐     │ prerequisite_check_node
        │  (병렬)  │  (병렬) analyze_question_node
        │         │    resolve_collection_node
        │         │
        ▼         ▼
    ┌───────────────────────┐
    │ analyze_question_node │  [3/9]
    │ ─ 질문 정규화           │
    │ ─ 질문 의도 분류         │
    │ ─ Bloom 단계 판별 (1~6) │
    │ ─ 개선 팁 생성           │
    └───────────┬───────────┘
                │
    ┌──────────▼────────────┐
    │ resolve_collection    │  [4/9]
    │ ─ subject_id 해석      │
    │ ─ 컬렉션명 매핑         │
    └──────────┬────────────┘
                │
                ▼
    ┌────────────────────────┐
    │ retrieve_context_node  │  [5/9]
    │ ─ RAG 검색             │
    │ ─ 적중도 판별           │
    │ ─ Citation 추출         │
    └────────────┬───────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ route_perspective_node │  [6/9]
    │ ─ 우선순위 기반 관점 선택 │
    │  (auto 또는 명시화)      │
    └────────────┬───────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ build_prompt_input_node│  [7/9]
    │ ─ LLM 호출용 입력 조립   │
    │ ─ Context 크기 제한     │
    │ ─ Chat history 윈도우    │
    └────────────┬───────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ generate_answer_node   │  [8/9]
    │ ─ 프롬프트 구성         │
    │ ─ LLM 호출 (GPT-4o-mini) │
    │ ─ Fallback 처리         │
    └────────────┬───────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ finalize_response_node │  [9/9]
    │ ─ 최종 응답 포맷팅       │
    │ ─ 메타데이터 정리        │
    └────────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │   WORKFLOW END     │
        └────────────────────┘
```

---

## 📊 각 노드 상세 설명

### **[1] init_request_node** → 정규화
- **입력**: Raw payload
- **처리**:
  - 문자열 공백 정리
  - 관심사 리스트 정규화
  - Chat history 포맷 검증
- **출력**: `normalized_question`, `interests`, `chat_history` (정규화됨)
- **상태 키**: 
  - `status`: "ok" (기본)
  - `retry_count`, `error_code`: 초기화

---

### **[2] prerequisite_check_node** → 필수값 검증
- **입력**: 정규화된 상태
- **검증**:
  - ✓ `question` 필수 (길이 > 0)
  - ✓ `subject_id` 필수
  - ✓ `selected_perspective` ∈ `ALLOWED_PERSPECTIVES` (7가지)
- **에러 조기 종료**:
  - 검증 실패 → `status: "error"` → 바로 `finalize_response_node` 진입
- **출력**: `status: "ok"` 또는 에러 정보

---

### **[3-4] 병렬 노드** → 분석 단계

#### **(3a) analyze_question_node** → 질문 분석
- **입력**: `question`, `interests`
- **처리**:
  1. **정규화**: `_normalize_question()` → 중복 공백 제거
  2. **Bloom 판별**: `score_bloom_by_keyword()`
     - 키워드 매칭 기반 (1차)
     - 결과: `level` (1~6), `confidence` (0.0~0.9)
  3. **질문 의도 분류**: `_infer_question_intent()`
     - 키워드 → 의도 맵핑
     - "비유" + 관심사 있음 → `"analogy"`
     - "왜" 키워드 → `"principle"`
     - 기본값 → `"concept"`
  4. **개선 팁 생성**: `_build_improvement_tip()`
- **출력**: 
  ```python
  normalized_question: str
  question_intent: str  # concept/principle/analogy/relation/usage/caution
  bloom_level: int      # 1~6
  bloom_label: str      # "지식"/"이해"/"응용"/"분석"/"종합"/"평가"
  bloom_confidence: float
  bloom_reason: str
  improvement_tip: str
  ```

#### **(3b) resolve_collection_node** → 컬렉션 해석
- **입력**: `subject_id` (예: "data_io_implementation")
- **처리**: `_resolve_collection_name()`
  1. **매핑 테이블 확인**: `SUBJECT_COLLECTION_MAP`
     ```python
     "data_io_implementation" → 
       collection_name: "ncs_LM2001020205_23v6____________20251108"
       label: "데이터 입출력 구현"
     ```
  2. **별칭 매칭**: `SUBJECT_ALIASES` (예: "데이터입출력구현" → "data_io_implementation")
  3. **ChromaDB 목록 검색**: 정확한 컬렉션 존재 확인
  4. **적중 없음**: `retrieval_hit: False` 설정 (RAG 스킵)
- **출력**:
  ```python
  resolved_collection_name: str  # 또는 None
  collection_resolution_reason: str
  collection_candidates: list[str]
  ```

---

### **[5] retrieve_context_node** → RAG 검색
- **입력**: `resolved_collection_name`, `normalized_question`
- **처리**:
  1. **Retriever 초기화**: `get_retriever()` (from `core/rag.py`)
     - ChromaDB + OpenAI Embeddings 사용
     - `top_k=5` (config.py)
  2. **유사도 검색**: `retriever.get_relevant_documents()`
  3. **Context 구성**: `_build_context_and_citations()`
     - 문서 수합
     - 최대 길이 제한: 2200자 (config.py)
     - Citation 메타데이터 추출 (PDF 페이지 번호 등)
- **출력**:
  ```python
  retrieved_docs: list[Any]  # 검색된 문서 리스트
  retrieval_context: str      # 합쳐진 텍스트
  citations: list[dict]       # [{"source": "...", "page": 5}, ...]
  retrieval_hit: bool         # True = 문서 발견
  ```
- **에러 처리**:
  - 컬렉션 없음 → Fallback 텍스트 생성
  - 검색 실패 → 빈 context로 계속

---

### **[6] route_perspective_node** → 최종 관점 선택
- **입력**: `selected_perspective`, `question_intent`, `bloom_level`, `interests`
- **우선순위 로직**:
  ```
  1️⃣ selected_perspective ≠ "auto"
      → 사용자 명시화 관점 사용
  
  2️⃣ question_intent → QUESTION_INTENT_TO_PERSPECTIVE 맵핑
      → "principle" / "analogy" / "relation" 등
  
  3️⃣ Bloom 수준별 기본값
      - Lv1~2 ("지식"/"이해"): "concept"
      - Lv3 ("응용"): "usage"
      - Lv4 ("분석"~): "relation"
      - Lv5~6 ("종합"/"평가"): "caution"
  
  4️⃣ 특수 조건
      - selected_perspective == "auto" 
        + Bloom Lv1~2 
        + interests 있음
        + question_intent == "analogy"
        → "analogy" 강제
  ```
- **출력**:
  ```python
  perspective: str  # 최종 선택된 관점 (7가지 중 1개)
  routing_reason: str  # 선택 이유
  ```

---

### **[7] build_prompt_input_node** → 프롬프트 입력 조립
- **입력**: 지금까지 누적된 모든 상태
- **처리**:
  ```python
  prompt_input = {
      "question": "...",
      "normalized_question": "...",
      "subject_id": "...",
      "subject_label": "데이터 입출력 구현",
      "perspective": "usage",  # ← [6]에서 선택됨
      "retrieval_context": "...",  # ← [5]에서 검색됨
      "retrieval_hit": True,  # ← 문서 발견 여부
      "citations": [...],
      "interests": ["쉬운 설명"],  # ← perspective=="analogy" 일 때만
      "improvement_tip": "...",
      "bloom_label": "응용",
      "chat_history": [...]  # ← 최근 6개 (GRAPH_CHAT_HISTORY_WINDOW)
  }
  ```
- **출력**: `prompt_input: dict`

---

### **[8] generate_answer_node** → LLM 호출
- **입력**: `prompt_input`
- **처리**:
  1. **프롬프트 구성**: `get_perspective_prompt()`
     - 관점별 템플릿 선택
     - Context, Chat history, Bloom label 주입
  2. **LLM 호출**: `ChatOpenAI()` (GPT-4o-mini)
     - Temperature: 0.6
     - Max tokens: 1000
  3. **Fallback**:
     - LLM 호출 실패 → `build_fallback_answer()`
     - Context 미리보기 + 학습 팁 반환
- **출력**:
  ```python
  answer_draft: str  # LLM 응답 (또는 fallback)
  status: "ok" or "error"
  ```

---

### **[9] finalize_response_node** → 최종 응답 포맷팅
- **입력**: 전체 그래프 상태
- **처리**:
  - 외부 API 응답용 최종 구조 조립
  - 불필요한 중간 상태 제거
  - Debug trace 정리
- **출력**:
  ```python
  {
    "status": "ok",
    "answer": "최종 답변 텍스트",
    "perspective": "usage",
    "bloom_level": 3,
    "bloom_label": "응용",
    "improvement_tip": "...",
    "citations": [...],
    "error_code": None,
    "error_message": None,
    "debug_trace": [...]  # ← 각 노드별 실행 로그
  }
  ```

---

## 🌳 GraphState (상태 스키마)

```python
class GraphState(TypedDict, total=False):
    # 📥 입력 (사용자로부터)
    question: str
    subject_id: str
    selected_perspective: str  # "auto" 포함 7가지
    interests: list[str]
    chat_history: list[dict]
    session_scope_id: Optional[str]
    
    # 📊 분석 중간값
    normalized_question: str
    question_intent: str
    bloom_level: int          # 1~6
    bloom_label: str          # "지식"~"평가"
    bloom_confidence: float   # 0.0~0.9
    
    # 🔍 검색 중간값
    collection_candidates: list[str]
    resolved_collection_name: Optional[str]
    retrieval_query: str
    retrieved_docs: list[Any]
    retrieval_context: str
    citations: list[dict]
    retrieval_hit: bool
    
    # 🎯 라우팅 중간값
    perspective: Optional[str]
    routing_reason: str
    
    # 🔧 생성 중간값
    prompt_input: dict
    answer_draft: str
    
    # ✅ 최종값
    answer_final: str
    
    # ⚠️ 제어값
    status: str  # "ok" / "error"
    error_code: Optional[str]
    error_message: Optional[str]
    retry_count: int
    debug_trace: list[dict]
```

---

## 🎛️ 설정값 (config.py)

```python
# LLM 설정
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.6          # 창의성 (0~1)
LLM_MAX_TOKENS = 1000          # 최대 답변 길이

# 그래프 실행 설정
GRAPH_CHAT_HISTORY_WINDOW = 6  # 최근 N개 대화만 포함
GRAPH_RETRIEVAL_TOP_K = 5      # RAG 검색 결과 개수
GRAPH_CONTEXT_CHAR_LIMIT = 2200  # Context 최대 크기
BLOOM_CONFIDENCE_THRESHOLD = 0.6  # 신뢰도 한계
```

---

## 📞 호출 인터페이스

### **스크립트에서 직접 호출** (테스트용)
```python
from core.graph import run_question_graph, build_mock_payload

payload = build_mock_payload(
    question="TCP와 UDP의 차이점은?",
    subject_id="server_program_implementation",
    interests=["쉬운 비유"]
)
result = run_question_graph(payload)
print(result["answer"])
```

### **Streamlit에서 호출** (pages/1_Chat.py)
```python
from core.graph import run_question_graph

result = run_question_graph({
    "question": st.session_state.user_input,
    "subject_id": st.session_state.subject,
    "selected_perspective": st.session_state.perspective,
    "interests": st.session_state.interests,
    "chat_history": st.session_state.chat,
})

st.write(result["answer"])
st.caption(f"Bloom: {result['bloom_label']}")
```

---

## 🚨 에러 핸들링 경로

```
❌ 필수값 검증 실패 (prerequisite_check_node)
    ↓
status: "error" 설정
    ↓
분석 노드들 스킵
    ↓
finalize_response_node로 바로 점프
    ↓
에러 메시지 반환

❌ 검색 실패 (retrieve_context_node)
    ↓
retrieval_hit: False
    ↓
빈 context로 계속 진행
    ↓
build_fallback_answer() 호출
    ↓
검색 근거 없이 보수적 답변 반환

❌ LLM 호출 실패 (generate_answer_node)
    ↓
build_fallback_answer() 호출
    ↓
최후의 보수적 답변 반환
```

---

## 💡 핵심 정리

| **단계** | **함수** | **핵심 역할** | **입력** | **출력** |
|---------|---------|------------|--------|--------|
| 1 | `init_request_node` | 정규화 | Raw payload | 정규화된 상태 |
| 2 | `prerequisite_check_node` | 검증 | - | 에러 또는 OK |
| 3 | `analyze_question_node` | 질문 분석 | question | bloom_level, intent |
| 4 | `resolve_collection_node` | 컬렉션 매핑 | subject_id | collection_name |
| 5 | `retrieve_context_node` | RAG 검색 | collection_name | retrieval_context |
| 6 | `route_perspective_node` | 관점 선택 | bloom_level, intent | perspective |
| 7 | `build_prompt_input_node` | 입력 조립 | 누적 상태 | prompt_input |
| 8 | `generate_answer_node` | LLM 호출 | prompt_input | answer_draft |
| 9 | `finalize_response_node` | 응답 구성 | answer_draft | 최종 응답 |

---

## 📍 코드 파일 위치

```
core/
├── graph.py                    # ← 워크플로우 정의 (모든 노드)
├── config.py                   # ← 설정값
├── prompts.py                  # ← 6관점 프롬프트 템플릿
├── rag.py                      # ← RAG 검색 (get_retriever)
└── utils.py                    # ← 헬퍼 (Bloom 판별, 관심사 저장)

pages/
└── 1_Chat.py                   # ← Streamlit UI → run_question_graph() 호출
```

