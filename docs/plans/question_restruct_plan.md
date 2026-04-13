# 질문 재구성 기능 구현 계획 (Question Restructuring)

## 개요 및 목표

**목적**: 매 답변 시작 전에 사용자 질문을 정확한 용어와 개념 기반으로 한 줄 재해석하여 표시.

**효과**:
- 사용자가 자신의 질문이 어떻게 이해되었는지 명확히 인식.
- RAG 검색 쿼리 최적화 (명확한 표현 → 더 정확한 검색).
- 자연스러운 대화 흐름 (UI 박스 대신 답변 내용과 매끄럽게 연결).

**범위** (핵심만):
- 제품 기능 변경 없음, 프롬프트 + 노드 추가만 진행.
- core/ 파일만 수정 (graph.py, prompts.py).
- test_graph.py로 단위 테스트만 진행 (UI 작업 제외).
---

## 디렉토리 구조

기존 파일만 수정 (새 파일 추가 없음):
```
core/
├── prompts.py        # 프롬프트 1개 추가 (PROMPT_RESTRUCTURE_QUESTION)
└── graph.py          # 상태 필드 2개 + 노드 1개 추가
```

---

## 핵심 플로우

```
1. prerequisite_check_node 통과
                ↓
2. analyze_question_node
   └─ 출력: state.normalized_question ✅ (사용자 질문을 정규화해 반환)
                ↓
3. [NEW] restructure_question_node
   ├─ 입력: state.normalized_question (← analyze_question_node에서 받음)
   ├─ LLM 호출: 정규화된 질문을 정확한 용어로 한 줄 재해석
   ├─ 출력: state.restructured_question ("~~~가 궁금하신 거죠?" 형식)
   └─ 실패 시: restructure_failed=True, restructured_question="" (원본 사용)
                ↓
4. 기존 파이프라인: resolve_collection_node → retrieve_context_node 
   → route_perspective_node → build_prompt_input_node
                ↓
5. generate_answer_node
   ├─ 프롬프트 구성 및 LLM 호출
   ├─ answer_text 획득
   ├─ [NEW] 재구성 한 줄 앞에 붙이기
   └─ answer_draft에 저장: "~~~가 궁금하신 거죠?\n\n[6관점 답변 내용]"
                ↓
6. finalize_response_node → answer_final로 전달
```

---

## 모듈별 구현 명세

### 1. `core/prompts.py` — 질문 재구성 프롬프트 추가

**위치**: 파일 맨 뒤에 추가

**상수명**: `PROMPT_RESTRUCTURE_QUESTION`

**역할**: 사용자 질문을 정확한 용어/개념으로 한 줄 요약 및 재해석.
[//] 이전 대화 기록을 참고해서 질문을 재정의 할 수 있도록 하기.
**형식**:
```python
PROMPT_RESTRUCTURE_QUESTION = """\
당신은 사용자의 질문을 정확한 기술 용어와 개념으로 재해석하는 전문가입니다.

【사용자 질문】
{normalized_question}

【지시사항】
1. 사용자 질문의 핵심 의도를 파악하세요.
2. 질문에 담긴 개념/기술 용어를 명확히 하세요.
3. 한 문장으로 재해석하세요: "~~~가 궁금하신 거죠?"
4. 형식: "~~~가 궁금하신 거죠?" (자연스러운 한국어 표현)
5. 원본 질문이 이미 명확하면 원본 그대로 사용.

【응답 형식】
한 줄만 반환. 추가 설명 금지. [//] 100자 내로 작성
예) "데이터베이스의 정규화 개념 중 BCNF가 궁금하신 거죠?"
"""
```

**특징**:
- JSON이 아닌 단순 한 줄 텍스트만 반환 (파싱 간단).
- 정확한 용어로 사용자 의도 명확화.
- 자연스러운 말투 ("~~~가 궁금하신 거죠?").

---

### 2. `core/graph.py` — 상태 필드 + 노드 추가

#### 2.1 GraphState 필드 추가

**추가 필드** (class GraphState 내, "분석 상태" 섹션):
```python
class GraphState(TypedDict, total=False):
    # ... 기존 필드 ...
    
    # 질문 재구성 (새 섹션)
    restructured_question: str       # "~~~가 궁금하신 거죠?" 형식
    restructure_failed: bool         # LLM 호출 실패 시 True
    
    # ... 기타 필드 ...
```

#### 2.2 노드 함수: `restructure_question_node()`

**위치**: graph.py 내 기존 노드 함수들과 함께 추가

**실행 조건**: 
- `prerequisite_check_node` 통과 후
- `analyze_question_node` 에서 `normalized_question` 완성 후

**입력**: 
- `state.normalized_question`

**출력**: 
- `state.restructured_question` (한 줄, "~~~가 궁금한 거죠?" 형식)
- `state.restructure_failed` (bool, 실패 여부)

**세부 로직**:
```
1. normalized_question 확인 (비어있으면 에러)
2. 프롬프트 구성: {normalized_question 대입}
3. LLM 호출 (기존 _create_llm() 객체 재사용)
4. 응답 정리: strip() + 첫 줄만 추출 (줄바꿈 제거)
5. 길이 제한: 100글자 초과시 절단 (optional)
6. 오류 시 원본 반환
7. debug_trace 기록
```

**예외 처리**:
- LLM 호출 실패 → `restructured_question = normalized_question`, `restructure_failed = True`
- 빈 응답 → `restructure_failed = True`, 원본 사용
- timeout → 기존 LLM 재시도 정책 적용

---

#### 2.3 워크플로우 수정 (build_question_graph 함수)

**데이터 흐름 확인**:
- `analyze_question_node()` 함수는 **`state.normalized_question` 반환**함 ✅
- 따라서 `restructure_question_node()` 입력에 사용 가능

**노드 추가** (build_question_graph 함수 내):
```python
builder.add_node("restructure_question_node", restructure_question_node)
```

**엣지 연결** (실행 순서 확정):
```python
# 기존 엣지 (수정 필요)
# builder.add_edge("analyze_question_node", "resolve_collection_node")

# 변경: analyze_question_node → restructure_question_node → resolve_collection_node
builder.add_edge("analyze_question_node", "restructure_question_node")
builder.add_edge("restructure_question_node", "resolve_collection_node")
```

**최종 파이프라인 순서**:
```
init_request_node 
  → prerequisite_check_node 
  → analyze_question_node (출력: normalized_question ✅)
  → [NEW] restructure_question_node (입력: normalized_question, 출력: restructured_question)
  → resolve_collection_node
  → retrieve_context_node
  → route_perspective_node 
  → build_prompt_input_node 
  → generate_answer_node (수정: 재구성 한 줄 붙이기)
  → finalize_response_node
  → END
```

---

#### 2.4 generate_answer_node 함수 수정

**함수명**: `generate_answer_node()` (core/graph.py)

**수정 위치**: 함수 내부 - LLM 호출 후 answer_text 완성 후, `return` 직전

**기존 구조**:
```
try:
    llm 호출 → response 획득
    answer_text = getattr(response, "content", "") or str(response)
    if not str(answer_text).strip():
        raise ValueError(...)
    
    return {
        "answer_draft": str(answer_text).strip(),  ← 여기가 수정 포인트
        "debug_trace": ...
    }
except Exception as exc:
    fallback 처리
```

**수정 로직** (return 전에 답변 앞에 붙이기):
```python
# [NEW] 재구성 한 줄 앞에 붙이기
restructured = state.get("restructured_question", "").strip()
if restructured:
    answer_text = f"{restructured}\n\n{str(answer_text).strip()}"
else:
    answer_text = str(answer_text).strip()

return {
    "answer_draft": answer_text,
    "debug_trace": _append_trace(
        state,
        "generate_answer_node",
        "LLM 호출로 답변 초안을 생성했습니다.",
        llm_model=LLM_MODEL,
    ),
}
```

**특징**:
- 재구성 실패 or 빈 값 → 원본 answer_text만 반환.
- 재구성 성공 → 두 줄 띄어쓰기(`\n\n`)로 자연스럽게 구분.
- 예외 처리 로직(fallback)은 그대로 유지.

---

## 예외 처리 및 방어 로직

| 케이스 | 입력 상태 | 처리 방식 | 결과 |
|--------|---------|---------|------|
| normalized_question 비어있음 | `state.normalized_question == ""` | 재구성 스킵 | `restructure_failed = True` |
| LLM 호출 실패 (timeout/API 오류) | 네트워크 오류 또는 API 한도 초과 | 기존 LLM 재시도 정책 적용 (3회) | 실패 시 원본 사용 |
| 응답이 비어있음 | LLM이 빈 응답 반환 | fallback: 원본 사용 | `restructure_failed = True` |
| 응답 너무 김 | `len(response) > 150글자` | 첫 150글자만 사용 + 한 문장 완성 | 자동 절단 |

**핵심 원칙**:
- 재구성 실패 시 **원본이나 기존 로직으로 복귀** (파이프라인 중단 금지).
- `restructure_failed` 플래그로 실패 추적 (debug_trace 기록).
- generate_answer_node에서 `restructured_question` 미검출 시 원본 답변만 반환.

---

## 체크리스트

### Phase 1: 코드 구현
- [ ] `core/prompts.py` 에 `PROMPT_RESTRUCTURE_QUESTION` 상수 추가
- [ ] `core/graph.py` 에 GraphState 필드 2개 추가 (`restructured_question`, `restructure_failed`)
- [ ] `core/graph.py` 에 `restructure_question_node()` 함수 구현
- [ ] `core/graph.py` 에서 builder에 노드 추가 + 엣지 연결
- [ ] `core/graph.py` 의 `generate_answer_node()` 수정 (재구성 한 줄 붙이기)

### Phase 2: 테스트 (test_graph.py)
- [ ] 명확한 질문 입력 → 재구성도 명확하게 반환되는지 확인
- [ ] 모호한 질문 입력 → 명확한 재구성 생성되는지 확인
- [ ] 오류 케이스 (빈 질문, 매우 긴 질문) 처리 확인
- [ ] 재구성 한 줄이 답변 맨 앞에 붙는지 확인 (`restructured_question\n\n[답변]` 형식)

---

## 기술 스택

- **Python 3.11**, **LangGraph**, **OpenAI API**
- **LLM**: 기존 설정 (config.py의 `LLM_MODEL` 변수 사용)
- **응답 형식**: 단순 텍스트 (JSON 파싱 불필요)

---

## 구현 기록

| 날짜 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-13 | 계획 수립 | ✅ Done | 간단함 원칙 적용 |
| - | `prompts.py` 추가 | ⏳ Not Started | 한 줄 재해석 프롬프트 |
| - | `graph.py` 상태/노드 | ⏳ Not Started | 2개 필드 + 1개 노드 |
| - | `graph.py` 엣지 연결 | ⏳ Not Started | 워크플로우 순서 조정 |
| - | `generate_answer_node` 수정 | ⏳ Not Started | 앞에 재구성 붙이기 |
| - | `test_graph.py` 테스트 | ⏳ Not Started | 4가지 케이스 검증
