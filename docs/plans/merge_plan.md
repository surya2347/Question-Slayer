# Streamlit-core 통합 계획서

### 날짜
2026-04-13

---

## 개요 및 목표

- 목적: `core/` 기능과 `app.py`, `pages/`(Streamlit 화면)을 하나의 데이터 계약으로 연결하는 통합 계획 수립
- 범위:
  - `core/rag.py` ↔ `core/graph.py` 연결 확인
  - `core/utils.py` ↔ `core/graph.py` 연결 확인
  - `core/prompts.py` ↔ `core/graph.py` 연결 확인
  - `app.py`, `pages/0_Home.py`, `pages/1_Chat.py`, `pages/2_Insight.py` ↔ `core/` 연결 계획 구체화
- 원칙:
  - 구현 금지
  - 함수 시그니처, 입력/출력 타입, 필수/선택 여부, 상태 키 이름을 먼저 고정
  - 화면용 변수명과 그래프용 변수명을 구분
  - `subject`와 `subject_id`, `perspective`와 `selected_perspective`, `messages`와 `chat_history`를 혼용하지 않음

### 현재 확인된 연결 상태

- `core/graph.py`는 이미 다음과 연결됨
  - `core.utils.score_bloom_by_keyword()`
  - `core.rag.get_retriever()`
  - `core.prompts.get_perspective_prompt()`
  - `core.prompts.build_fallback_answer()`
- `core/graph.py`의 공개 실행 진입점은 이미 존재함
  - `build_question_graph()`
  - `build_mock_payload()`
  - `run_question_graph()`
- `pages/1_Chat.py`는 아직 더미 응답과 더미 Bloom 판별을 사용 중임
- `pages/0_Home.py`는 과목 선택 UI는 있으나 `subject_id` 변환 계약이 없음
- `pages/2_Insight.py`는 `session_state.messages`를 읽는 구조는 갖추었으나, 그래프 결과 기준 통계로 고정할 계약이 더 필요함

---

## 디렉토리 구조

| 경로 | 역할 | 통합 관점 메모 |
|---|---|---|
| `app.py` | Streamlit 앱 진입, 전역 세션 상태 초기화 | 공통 세션 키 표준화 필요 |
| `pages/0_Home.py` | 과목/관심사 설정 화면 | 과목 표시명과 `subject_id` 분리 필요 |
| `pages/1_Chat.py` | 질문 입력 및 답변 렌더링 화면 | `run_question_graph()` 호출 지점 |
| `pages/2_Insight.py` | 학습 통계 시각화 화면 | `messages`의 assistant 메타데이터 집계 필요 |
| `core/graph.py` | LangGraph 워크플로우 | UI와 core를 잇는 핵심 계약점 |
| `core/rag.py` | 청킹/임베딩/검색 | `get_retriever()`가 graph 검색 단계의 직접 의존성 |
| `core/prompts.py` | 관점별 프롬프트 | `get_perspective_prompt()`가 생성 단계의 직접 의존성 |
| `core/utils.py` | Bloom, 관심사, 과목 탐지, 저장 유틸 | `score_bloom_by_keyword()`와 관심사 저장이 핵심 |
| `data/user_profiles/` | 사용자 관심사 JSON | `load_interests()`, `save_interests()`의 저장 위치 |
| `data/chroma_db/` | 벡터 DB | `subject_id -> collection_name` 해석의 근거 |

---

## 핵심 플로우

### 1. 홈 설정 플로우

1. `pages/0_Home.py`에서 과목 선택
2. 선택값을 화면 표시용 문자열이 아니라 `subject_id` 기준으로 저장
3. 관심사는 `list[str]` 형태로 저장하고 `data/user_profiles/{user_id}.json`에 동기화
4. 이후 Chat 페이지는 이 세션 값을 그대로 사용

### 2. 질문-응답 플로우

1. `pages/1_Chat.py`에서 사용자 질문 입력
2. 현재 세션 상태를 `run_question_graph()` 입력 payload로 변환
3. `core/graph.py`가 질문 분석, 컬렉션 해석, RAG 검색, 관점 라우팅, 프롬프트 조립, 답변 생성 수행
4. 반환값을 `st.session_state.messages`에 user/assistant 레코드로 저장
5. `pages/2_Insight.py`는 이 `messages`를 읽어 실제 Bloom/관점 통계를 시각화

### 3. 인사이트 플로우

1. user 메시지와 assistant 메시지를 짝지음
2. assistant 메시지의 `bloom_level`, `perspective`를 기준으로 통계 집계
3. 질문 이력, 평균 Bloom, 관점 분포, 최근 답변을 렌더링

---

## API 명세

### `core.graph.run_question_graph(payload)`

| 항목 | 값 |
|---|---|
| 시그니처 | `run_question_graph(payload: dict[str, Any]) -> dict[str, Any]` |
| 역할 | Streamlit/CLI에서 호출하는 최종 실행 함수 |
| 입력 필수 | `question`, `subject_id`, `selected_perspective` |
| 입력 선택 | `interests`, `chat_history`, `session_scope_id` |
| 반환 필수 | `status`, `answer`, `debug_trace` |
| 반환 선택 | `perspective`, `bloom_level`, `bloom_label`, `improvement_tip`, `citations`, `error_code`, `error_message` |

#### payload 형식

```text
{
  question: str,                 # 필수
  subject_id: str,               # 필수
  selected_perspective: str,     # 필수, auto|concept|principle|analogy|relation|usage|caution
  interests: list[str] | str | None,   # 선택
  chat_history: list[dict] | None,     # 선택
  session_scope_id: str | None         # 선택
}
```

#### 반환 형식

```text
{
  status: "ok" | "error",
  answer: str,
  perspective: str | None,
  bloom_level: int | None,
  bloom_label: str | None,
  improvement_tip: str | None,
  citations: list[dict],
  error_code: str | None,
  error_message: str | None,
  debug_trace: list[dict]
}
```

### `core.graph.build_mock_payload(...)`

| 항목 | 값 |
|---|---|
| 시그니처 | `build_mock_payload(question, subject_id, selected_perspective="auto", interests=None, chat_history=None, session_scope_id=None) -> dict[str, Any]` |
| 역할 | 콘솔 테스트/수동 검증용 payload 생성 |
| 입력 필수 | `question`, `subject_id` |
| 입력 선택 | 나머지 전부 |
| 반환 | `run_question_graph()`와 같은 구조의 raw payload |
| 비고 | UI에서는 직접 호출하지 않음 |

### `core.graph.build_question_graph()`

| 항목 | 값 |
|---|---|
| 시그니처 | `build_question_graph()` |
| 역할 | LangGraph 워크플로우 생성 및 compile |
| 입력 | 없음 |
| 반환 | compile된 graph app |
| 비고 | UI/테스트 모두 내부적으로만 사용 |

### `core.graph` 노드 함수

| 함수 | 입력 | 반환 | 필수/선택 메모 |
|---|---|---|---|
| `init_request_node(state)` | `GraphState` | 정규화된 `GraphState` 일부 | `question`, `subject_id`, `selected_perspective`는 필수 취급 |
| `prerequisite_check_node(state)` | `GraphState` | 상태/에러 메시지 | 질문 공백, subject 공백, 관점 유효성 검증 |
| `analyze_question_node(state)` | `GraphState` | `bloom_level`, `bloom_label`, `bloom_confidence`, `improvement_tip` | `score_bloom_by_keyword()` 의존 |
| `resolve_collection_node(state)` | `GraphState` | `resolved_collection_name`, `collection_candidates` | `subject_id -> collection_name` 해석 |
| `retrieve_context_node(state)` | `GraphState` | `retrieval_context`, `citations`, `retrieval_hit` | `QUESTION_SLAYER_ENABLE_REMOTE_RAG` 조건 영향 |
| `route_perspective_node(state)` | `GraphState` | `perspective`, `routing_reason` | `selected_perspective`가 `auto`일 때만 자동 라우팅 |
| `build_prompt_input_node(state)` | `GraphState` | `prompt_input` | LLM 입력 직전 구조화 |
| `generate_answer_node(state)` | `GraphState` | `answer_draft` | `QUESTION_SLAYER_ENABLE_LLM`, `OPENAI_API_KEY` 의존 |
| `finalize_response_node(state)` | `GraphState` | `answer_final`, `answer`, 최종 메타데이터 | 외부 반환용 정리 |

### `core.rag.get_retriever(collection_name, top_k=5)`

| 항목 | 값 |
|---|---|
| 시그니처 | `get_retriever(collection_name: str, top_k: int = 5)` |
| 입력 필수 | `collection_name` |
| 입력 선택 | `top_k` |
| 반환 | Retriever 또는 `None` |
| 실패 시 | 컬렉션 생성 실패, 경로 문제, Chroma 접근 실패 |
| graph 연동 | `retrieve_context_node()`가 직접 호출 |

### `core.rag.process_pdf(pdf_path, collection_name)`

| 항목 | 값 |
|---|---|
| 시그니처 | `process_pdf(pdf_path: str, collection_name: str) -> dict` |
| 역할 | PDF 처리, 청킹, 임베딩, Chroma 저장 |
| 입력 필수 | `pdf_path`, `collection_name` |
| 반환 | `collection_name`, `total_chunks`, `status`, `message` |
| 비고 | 화면 연동 대상 아님, 데이터 준비 단계용 |

### `core.prompts.get_perspective_prompt(...)`

| 항목 | 값 |
|---|---|
| 시그니처 | `get_perspective_prompt(perspective, question, context, subject, interests=None, bloom_label=None, improvement_tip=None, chat_history=None) -> str` |
| 입력 필수 | `perspective`, `question`, `context`, `subject` |
| 입력 선택 | `interests`, `bloom_label`, `improvement_tip`, `chat_history` |
| 반환 | 프롬프트 문자열 |
| 주의 | `perspective`는 반드시 `concept|principle|analogy|relation|usage|caution` 중 하나 |
| graph 연동 | `generate_answer_node()`가 호출 |

### `core.prompts.build_fallback_answer(...)`

| 항목 | 값 |
|---|---|
| 시그니처 | `build_fallback_answer(question, perspective, subject, retrieval_context, improvement_tip=None) -> str` |
| 입력 필수 | `question`, `perspective`, `subject`, `retrieval_context` |
| 입력 선택 | `improvement_tip` |
| 반환 | fallback 답변 문자열 |
| 비고 | LLM 비활성/실패 시 사용 |

### `core.utils.score_bloom_by_keyword(question)`

| 항목 | 값 |
|---|---|
| 시그니처 | `score_bloom_by_keyword(question: str) -> dict` |
| 입력 필수 | `question` |
| 반환 키 | `level`, `name_ko`, `keywords_found`, `confidence`, `method` |
| graph 연동 | `analyze_question_node()`가 직접 사용 |

### `core.utils.save_interests(user_id, interests)`

| 항목 | 값 |
|---|---|
| 시그니처 | `save_interests(user_id: str, interests: list[str]) -> None` |
| 입력 필수 | `user_id`, `interests` |
| 반환 | 없음 |
| 저장 위치 | `data/user_profiles/{user_id}.json` |
| 화면 연동 | `pages/0_Home.py`가 사용 |

### `core.utils.load_interests(user_id)`

| 항목 | 값 |
|---|---|
| 시그니처 | `load_interests(user_id: str) -> list[str]` |
| 입력 필수 | `user_id` |
| 반환 | 관심사 목록, 없으면 `[]` |
| 화면 연동 | `pages/0_Home.py` 초기값 복원에 사용 |

### `core.utils.detect_subject(question)`

| 항목 | 값 |
|---|---|
| 시그니처 | `detect_subject(question: str) -> dict` |
| 상태 | 현재 UI 흐름에서 미사용 |
| 반환 | `subject`, `keywords_found`, `confidence` |
| 계획 | 자동 과목 추정 기능이 필요할 때만 후순위 연동 |

### `core.utils.pick_best_interest(question, interests)`

| 항목 | 값 |
|---|---|
| 시그니처 | `pick_best_interest(question: str, interests: list[str]) -> str` |
| 상태 | 현재 graph는 사용하지 않음 |
| 계획 | 비유 관점에서 관심사 1개만 고를 필요가 있을 때 후보 함수로 유지 |

---

## 모듈별 구현 명세

### `core/graph.py`

#### 상태 스키마 계약

| 키 | 타입 | 필수/선택 | 용도 |
|---|---|---|---|
| `question` | `str` | 필수 | 사용자 질문 원문 |
| `subject_id` | `str` | 필수 | Chroma 컬렉션 해석용 식별자 |
| `selected_perspective` | `str` | 필수 | UI에서 선택한 관점, 기본값 `auto` |
| `interests` | `list[str]` | 선택 | 비유 관점에서 사용 |
| `chat_history` | `list[dict[str, Any]]` | 선택 | 대화 맥락 |
| `session_scope_id` | `str | None` | 선택 | 세션 구분자 |
| `normalized_question` | `str` | 내부 | 공백 정리 질문 |
| `question_intent` | `str` | 내부 | `concept/principle/...` 의도 |
| `bloom_level` | `int | None` | 내부/반환 | Bloom 단계 |
| `bloom_label` | `str | None` | 내부/반환 | 한국어 레이블 |
| `bloom_confidence` | `float` | 내부 | 키워드 판별 신뢰도 |
| `improvement_tip` | `str | None` | 내부/반환 | 질문 개선 유도 문구 |
| `resolved_collection_name` | `str | None` | 내부 | 실제 Chroma 컬렉션명 |
| `retrieval_context` | `str` | 내부 | RAG 컨텍스트 |
| `citations` | `list[dict[str, Any]]` | 내부/반환 | 출처 메타데이터 |
| `perspective` | `str | None` | 내부/반환 | 최종 설명 관점 |
| `prompt_input` | `dict[str, Any]` | 내부 | LLM 입력 구조 |
| `answer_draft` | `str` | 내부 | 초안 답변 |
| `answer_final` | `str` | 내부/반환 | 최종 답변 |
| `answer` | `str` | 반환 | 외부 호환 응답 |
| `status` | `str` | 내부/반환 | `ok` / `error` |
| `error_code` | `str | None` | 내부/반환 | 오류 식별자 |
| `error_message` | `str | None` | 내부/반환 | 오류 설명 |
| `debug_trace` | `list[dict[str, Any]]` | 반환 | 노드별 추적 로그 |

#### 연동 포인트

- `resolve_collection_node()`는 `subject_id`를 기준으로만 동작
- `route_perspective_node()`는 `selected_perspective`가 `auto`일 때만 자동 판단
- `generate_answer_node()`는 `prompt_input`만 보고 프롬프트를 조립
- `finalize_response_node()`는 UI가 바로 쓸 수 있는 최소 필드만 외부에 노출

### `core/prompts.py`

#### 현재 연동 상태

- `get_perspective_prompt()`는 graph에서 직접 사용 중
- `build_fallback_answer()`는 graph의 실패 경로에서 직접 사용 중
- `PROMPT_CONCEPT`, `PROMPT_PRINCIPLE`, `PROMPT_ANALOGY`, `PROMPT_RELATION`, `PROMPT_USAGE`, `PROMPT_CAUTION`는 `get_perspective_prompt()`의 내부 템플릿
- `PROMPT_INTEREST_SELECTOR`와 `format_interests_for_prompt()`는 현재 phase에서 미사용

#### 주의점

- `analogy` 관점에서는 `interests`가 문자열 하나로 주입됨
- `chat_history`는 문자열 본문이 있는 항목만 프롬프트 부록으로 붙음
- `bloom_label`, `improvement_tip`은 선택 부록이므로 없어도 동작해야 함

### `core/utils.py`

#### 현재 연동 상태

- `score_bloom_by_keyword()`는 graph Bloom 분석의 1차 기준
- `save_interests()`, `load_interests()`는 Home 페이지의 설정 저장/복원에 사용
- `level_to_label()` / `label_to_level()`은 현재 graph/UI 경로에서 직접 사용하지 않음
- `detect_subject()`는 자동 subject 추정용 후보이며 현재 UI 주 흐름에는 미연동

#### 데이터 형식

- `score_bloom_by_keyword()` 반환 예:

```text
{
  "level": 2,
  "name_ko": "이해",
  "keywords_found": ["왜", "설명"],
  "confidence": 0.75,
  "method": "keyword"
}
```

- `save_interests()` 저장 파일 예:

```json
{
  "interests": ["게임", "축구", "요리"]
}
```

### `core/rag.py`

#### 현재 연동 상태

- `get_retriever()`는 graph 검색 단계의 직접 의존성
- `process_pdf()`는 데이터 적재용 CLI 흐름
- `extract_pages()`, `merge_pages()`, `split_by_sections()`, `refine_chunks()`는 `process_pdf()` 내부 파이프라인

#### `get_retriever()` 반환 계약

- 성공 시 `VectorStoreRetriever`
- 실패 시 `None`
- graph는 `None`을 받으면 검색 생략 후 fallback 경로로 이동해야 함

### `app.py`

#### 역할

- 앱 전체의 `st.set_page_config()` 설정
- 전역 세션 상태 초기화

#### 통합 계획

- 공통 세션 키를 최소 한 번에 초기화
- `subject_id`, `subject_label`, `interests`, `messages`, `selected_perspective`, `current_answer`, `session_scope_id`를 앱 공통 키로 관리
- 현재처럼 `subject` 하나로만 관리하지 않도록 정리

### `pages/0_Home.py`

#### 현재 문제

- 과목 선택 UI가 `SUBJECT_KEYWORDS` 기반임
- graph는 `subject_id -> SUBJECT_COLLECTION_MAP -> collection_name` 흐름을 요구함
- 따라서 화면 표시 목록과 그래프 입력 키가 분리되지 않으면 통합이 깨짐

#### 통합 계획

- 선택 옵션의 기준을 `SUBJECT_COLLECTION_MAP`으로 전환
- 화면 표시명(`subject_label`)과 그래프 입력값(`subject_id`)를 분리 저장
- 저장 시 `save_interests()`와 `load_interests()`를 계속 사용

#### 세션 상태 계약

| 키 | 타입 | 필수/선택 | 설명 |
|---|---|---|---|
| `subject_id` | `str | None` | 필수 수준 | 그래프 입력용 과목 식별자 |
| `subject_label` | `str | None` | 선택 | 화면 표시용 한글 과목명 |
| `interests` | `list[str]` | 선택 | 비유 설명용 관심사 |

### `pages/1_Chat.py`

#### 현재 문제

- `_dummy_bloom()`와 `get_dummy_response()`가 아직 사용 중
- `run_question_graph()` 호출 없음
- `st.session_state.messages`는 존재하지만 graph 입력용 `chat_history`로 정리되지 않음

#### 통합 계획

1. `user_input` 수신
2. 현재 세션 상태를 payload로 변환
3. `run_question_graph(payload)` 호출
4. 반환값을 assistant 메시지로 저장
5. 실패 시에도 `status`, `error_code`, `error_message`를 화면에 노출

#### payload 변환 계약

```text
{
  question: user_input,
  subject_id: st.session_state.subject_id,
  selected_perspective: st.session_state.perspective or "auto",
  interests: st.session_state.interests,
  chat_history: [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  session_scope_id: st.session_state.session_scope_id
}
```

#### 메시지 저장 계약

| 메시지 종류 | 필수 키 | 선택 키 | 설명 |
|---|---|---|---|
| user | `role`, `content` | `time`, `selected_perspective`, `subject_id` | 사용자 입력 기록 |
| assistant | `role`, `content` | `time`, `perspective`, `bloom_level`, `bloom_label`, `improvement_tip`, `citations`, `error_code`, `error_message` | graph 결과 기록 |

#### 주의점

- `chat_history`는 `messages` 전체를 넘겨도 되지만, graph는 내부에서 `role`/`content`만 정규화함
- `selected_perspective`와 `perspective`는 같은 값이 아님
  - `selected_perspective`: 사용자가 고른 값
  - `perspective`: graph가 최종 확정한 값
- `user` 메시지에는 선택값을, `assistant` 메시지에는 확정값을 저장하는 편이 Insight에 유리함

### `pages/2_Insight.py`

#### 현재 상태

- `session_state.messages`를 집계하는 구조는 이미 존재함
- 더미 데이터 대신 실제 `assistant` 메시지 메타데이터를 사용하면 됨

#### 통합 계획

- 총 질문 수: assistant 메시지 수로 계산
- 평균 Bloom: assistant 메시지의 `bloom_level` 평균
- 가장 많이 사용한 관점: assistant 메시지의 `perspective` 최빈값
- 최근 질문 이력: user 메시지와 그에 대응하는 assistant 메시지 묶음으로 표시

#### 권장 집계 기준

| 통계 | 기준 메시지 | 이유 |
|---|---|---|
| 총 질문 수 | assistant | 답변 단위가 실제 학습 완료 단위 |
| 평균 Bloom | assistant | 그래프가 판단한 최종 수준 반영 |
| 관점 분포 | assistant | 실제 설명 방식 집계 |
| 최근 질문 텍스트 | user | 질문 원문 표시 |

---

## 예외 처리 및 방어 로직

### 1. 입력 검증

- `question` 공백이면 `EMPTY_QUESTION`
- `subject_id` 공백이면 `EMPTY_SUBJECT_ID`
- `selected_perspective`가 허용 목록 밖이면 `INVALID_PERSPECTIVE`

### 2. 과목 해석 실패

- `subject_id`가 `SUBJECT_COLLECTION_MAP`에 없으면 컬렉션 해석 실패로 기록
- 이 경우 검색은 생략되더라도 그래프는 종료하지 않고 fallback 답변으로 이어질 수 있음

### 3. RAG 실패

- `QUESTION_SLAYER_ENABLE_REMOTE_RAG != "1"`이면 검색을 건너뜀
- `get_retriever()`가 `None`을 반환하면 검색 생략
- 검색 예외 발생 시 `citations=[]`, `retrieval_hit=False`로 정리

### 4. LLM 실패

- `QUESTION_SLAYER_ENABLE_LLM != "1"`이면 LLM 호출 금지
- `OPENAI_API_KEY` 없으면 LLM 호출 금지
- LLM 실패 시 `build_fallback_answer()` 사용

### 5. Streamlit 세션 불일치

- `messages`가 없으면 빈 리스트로 초기화
- `subject_id`가 없으면 Chat에서 전송 버튼 비활성화 또는 오류 배너 노출
- `interests`가 비어 있어도 비유 외 관점은 정상 동작해야 함

### 6. Insight 집계 실패

- 비정상 메시지 구조는 무시
- assistant 메시지가 없으면 0값 카드와 안내 문구 표시

---

## UI 렌더링 명세

### `app.py`

- 앱 시작 시 공통 세션 키 초기화
- 홈/채팅/인사이트 페이지가 같은 상태를 공유하도록 기준점 역할

### `pages/0_Home.py`

- 과목 선택과 관심사 저장을 분리
- 저장 완료 후 `st.session_state.subject_id`와 `st.session_state.interests`를 즉시 반영
- 선택 상태를 한눈에 확인 가능한 요약 카드 제공

### `pages/1_Chat.py`

- 좌측: 대화창
- 우측: 학습 인사이트 미리보기 또는 보조 패널
- 질문 입력 후 graph 결과를 즉시 렌더링
- assistant 메시지에 Bloom 배지와 관점 표시

### `pages/2_Insight.py`

- 상단 요약 카드
- Bloom 분포 차트
- 성장 곡선
- 최근 질문 목록
- 데이터가 없을 때는 더미가 아니라 "질문을 먼저 입력하라"는 안내 유지

---

## 체크리스트

- [ ] `subject`를 `subject_id` 기준으로 정리
- [ ] Home 페이지 과목 옵션을 `SUBJECT_COLLECTION_MAP` 기준으로 전환
- [ ] Chat 페이지에서 `_dummy_bloom()` 제거
- [ ] Chat 페이지에서 `run_question_graph()` 호출 추가
- [ ] `messages -> chat_history` 변환 함수 정의
- [ ] assistant 메시지에 `bloom_level`, `bloom_label`, `perspective`, `citations` 저장
- [ ] Insight 페이지의 통계 기준을 assistant 메시지로 고정
- [ ] `QUESTION_SLAYER_ENABLE_REMOTE_RAG`, `QUESTION_SLAYER_ENABLE_LLM`, `OPENAI_API_KEY` 환경 변수 확인
- [ ] fallback 응답과 error payload UI 처리 분리
- [ ] `debug_trace`는 개발/디버깅용으로만 노출 여부 결정

---

## 구현 기록

- 2026-04-13: 현재 코드베이스 점검 완료
- 확인 결과:
  - `core/graph.py`와 `core/rag.py` 연결은 존재함
  - `core/graph.py`와 `core/utils.py` 연결은 존재함
  - `core/graph.py`와 `core/prompts.py` 연결은 존재함
  - Streamlit 화면은 아직 graph 기준 데이터 계약으로 정리되지 않음
  - `pages/1_Chat.py`는 더미 응답을 graph로 교체해야 함
  - `pages/0_Home.py`는 `subject_id` 표준화가 필요함
  - `pages/2_Insight.py`는 실제 assistant 메타데이터를 기준으로 집계할 수 있는 구조임

### 후속 작업 메모

1. `merge_plan.md`를 기준 문서로 사용
2. 실제 구현 시에는 이 문서의 함수명/필드명 변경 없이 반영
3. `subject_id`와 `selected_perspective`는 UI와 graph 사이의 가장 중요한 계약이므로 우선 고정
