# LangGraph 아키텍처 및 노드 설계 계획

### 날짜
2026-04-11

---

## 개요 및 목표

- **유형**: Streamlit 기반 학습용 웹 서비스의 LangGraph 설계 문서
- **현재 목표**: `core/graph.py`에 들어갈 그래프 구조, 상태 스키마, 노드 책임, 노드 내부 로직, 입출력 계약 정리
- **설계 기준**: LangGraph `0.2.x`
- **이번 문서의 초점**:
  - UI 연동보다 그래프 내부 아키텍처 우선
  - 구현 코드보다 노드/상태/흐름 정의 우선
  - 이미 다른 팀원이 작업 중인 `prompts.py`와 이미 들어온 `utils.py` 로직은 재구현하지 않고 연동 계약만 정의
  - 현재 단계의 입력은 Streamlit이 아니라 **mock payload**
- **MVP 범위**:
  - 질문 입력 정규화
  - Bloom 분석
  - 과목별 컬렉션 해석
  - RAG 검색
  - 관점 선택
  - 프롬프트 입력 조합
  - 답변 생성
  - 최종 응답 포맷팅

---

## 제외 범위

- `pages/1_Chat.py` 연동
- `app.py` 연동
- Streamlit 렌더링 정책
- `core/prompts.py` 실제 구현
- Bloom 1차 규칙 함수 재구현
- 관점 매핑 유틸 재구현
- Guardrail/검증 노드 실구현
- 재생성 루프 실구현
- 테스트 페이지 `pages/test_graph_page.py` 작성

> 현재 단계는 **그래프 설계 문서** 단계이므로, 콘솔 기반 테스트 계획까지만 포함하고 UI 페이지 계획은 제외함.

---

## 디렉토리 구조

```
Question-Slayer/
├── core/
│   ├── graph.py                 # [설계 대상] LangGraph 상태, 노드, 엣지, 실행 인터페이스
│   ├── rag.py                   # [기존 구현 활용] Retriever 및 Chroma 검색
│   ├── prompts.py               # [추후 연동] 관점별 프롬프트 함수 모음
│   └── utils.py                 # [기존 구현 활용] Bloom 규칙 분류, 과목 탐지, 공통 헬퍼
├── data/
│   └── chroma_db/               # [확인 완료] 과목별 컬렉션 저장소
├── docs/plans/
│   ├── start_plan.md
│   ├── RAG_plan.md
│   └── Langgraph_plan.md
├── pyproject.toml               # [추후 수정 대상] LangGraph 0.2 계열 고정 필요
├── uv.lock                      # [검증 대상] 실제 해석 버전 확인
└── test_graph.py                # [추후 작성 계획만 정의] 콘솔 기반 그래프 테스트 스크립트
```

### 현재 상태 반영 메모

- `core/prompts.py`는 다른 팀원이 구현 중이며, 추후 가져와 연동 예정
- `core/utils.py`에는 Bloom 1차 규칙 로직이 이미 일부 구현되어 있음
- `pages/1_Chat.py`는 지금 단계 작업 대상 아님
- 현재 워크스페이스에서 `data/ncs_pdfs/` 원본 PDF 파일 목록은 확인되지 않음
- `data/chroma_db` 컬렉션명은 현재 다음과 같이 확인됨
  - `ncs_LM2001020211_23v6____________20251108`
  - `ncs_LM2001020205_23v6____________20251108`
  - `ncs_LM2001020201_23v5_________20251108`
- 컬렉션 메타데이터의 `source` 값은 다음과 같이 확인됨
  - `LM2001020211_23v6_서버+프로그램+구현_20251108`
  - `LM2001020205_23v6_데이터+입출력+구현_20251108`
  - `LM2001020201_23v5_요구사항+확인_20251108`
- 따라서 `subject_id`를 바로 컬렉션명으로 쓰지 않고, **subject_id -> collection_name 해석 단계**가 필요함

---

## subject_id 매핑표 초안

### 목적

- UI/입력 계층에서 사용하는 `subject_id`
- 사용자가 보는 과목명 `subject_label`
- 실제 Chroma 컬렉션명 `collection_name`
- 원본 PDF 또는 Chroma 메타데이터의 `source`

를 분리 관리하기 위한 초안 표 정의.

### 권장 관리 원칙

- `subject_id`는 사람이 읽기 쉬운 영문 소문자 + 언더스코어 형식 사용
- 실제 Chroma `collection_name`은 임베딩 결과를 그대로 사용
- 사용자가 보는 한글 과목명은 `subject_label` 필드로 별도 관리
- 과목 수정 시 UI 표시명만 바꾸는 경우와, 실제 컬렉션 연결을 바꾸는 경우를 구분

### 초안 매핑표

| subject_id | subject_label | collection_name | source 예시 | 비고 |
|---|---|---|---|---|
| `requirements_analysis` | 요구사항 확인 | `ncs_LM2001020201_23v5_________20251108` | `LM2001020201_23v5_요구사항+확인_20251108` | Chroma 메타데이터로 확인 |
| `data_io_implementation` | 데이터 입출력 구현 | `ncs_LM2001020205_23v6____________20251108` | `LM2001020205_23v6_데이터+입출력+구현_20251108` | Chroma 메타데이터로 확인 |
| `server_program_implementation` | 서버 프로그램 구현 | `ncs_LM2001020211_23v6____________20251108` | `LM2001020211_23v6_서버+프로그램+구현_20251108` | Chroma 메타데이터로 확인 |

### 권장 데이터 구조

```python
SUBJECT_COLLECTION_MAP = {
    "requirements_analysis": {
        "label": "요구사항 확인",
        "collection_name": "ncs_LM2001020201_23v5_________20251108",
        "source": "LM2001020201_23v5_요구사항+확인_20251108",
    },
    "data_io_implementation": {
        "label": "데이터 입출력 구현",
        "collection_name": "ncs_LM2001020205_23v6____________20251108",
        "source": "LM2001020205_23v6_데이터+입출력+구현_20251108",
    },
    "server_program_implementation": {
        "label": "서버 프로그램 구현",
        "collection_name": "ncs_LM2001020211_23v6____________20251108",
        "source": "LM2001020211_23v6_서버+프로그램+구현_20251108",
    },
}
```

### 유지보수 정책

1. 새 과목 PDF를 임베딩하면 먼저 생성된 컬렉션명과 `source`를 확인
2. `subject_id`는 되도록 안정적으로 유지
3. 과목명이 바뀌면 우선 `label`만 변경 가능한지 검토
4. 실제 컬렉션이 바뀌었으면 `collection_name`도 함께 갱신
5. 과목 삭제 시 UI 선택지와 매핑표를 함께 정리

### README 반영 예정 항목

- `README.md`에 추후 `과목 수정하는 법` 섹션 추가
- 포함할 내용:
  - 새 PDF 임베딩 후 컬렉션명 확인 방법
  - `subject_id` / `label` / `collection_name` 수정 위치
  - UI 표시 과목명 변경 위치
  - 컬렉션명과 과목명을 일치시키는 확인 절차

### README 섹션 초안 항목

1. 새 PDF를 `data/ncs_pdfs/`에 추가
2. 임베딩 CLI 실행
3. 생성된 Chroma 컬렉션명 확인
4. subject 매핑표 업데이트
5. 앱에서 표시할 과목명 업데이트
6. 콘솔 테스트로 실제 검색 동작 확인

---

## 의존성 및 환경 설정

### 버전 기준

- **설계 기준 버전**: LangGraph `0.2.x`
- **현재 워크스페이스 실제 해석 버전**:
  - `langgraph 1.1.6`
  - `langchain 1.2.15`
  - `langchain-openai 1.1.12`

### 결론

- 지금 상태로 구현을 시작하면 0.2 설계가 아니라 1.x API로 미끄러질 가능성이 높음
- 구현 시작 전 반드시 0.2 계열로 고정 필요

### 구현 전 선행 작업

1. `pyproject.toml`에서 `langgraph` 범위를 `>=0.2,<0.3` 또는 팀 합의한 0.2 패치 버전으로 고정
2. `uv.lock` 재생성
3. 실제 설치 버전 재확인
4. 그 후 `core/graph.py` 구현 시작

### 0.2 계열 주의사항

- `StateGraph` 중심 구조 사용
- `set_entry_point(...)` 기준으로 설계
- 1.x 문서 예제를 혼용하지 않음

---

## 핵심 플로우

### 입력 기준

현재 단계에서는 Streamlit 대신 mock payload 기준으로 설계함.

```python
{
    "question": str,
    "subject_id": str,
    "selected_perspective": str,   # auto | concept | principle | analogy | relation | usage | caution
    "interests": list[str] | str | None,
    "chat_history": list[dict] | None,
}
```

### 메인 플로우

```
mock payload
   ↓
init_request_node
   ↓
prerequisite_check_node
   ↓
┌──────────────────────────── 병렬 분기 ────────────────────────────┐
│ analyze_question_node         resolve_collection_node             │
└───────────────────────────────┬───────────────────────────────────┘
                                ↓
                       retrieve_context_node
                                ↓
                       route_perspective_node
                                ↓
                     build_prompt_input_node
                                ↓
                       generate_answer_node
                                ↓
                     finalize_response_node
                                ↓
                           final payload
```

### 확장 플로우 `Phase 2`

```
generate_answer_node
   ↓
validate_answer_node
   ├─ pass → finalize_response_node
   └─ fail → retry_or_finalize_node
```

### 구조 선택 이유

1. `resolve_collection_node`를 분리
   - 현재 Chroma 컬렉션명이 과목명과 직접 1:1로 대응하지 않기 때문
   - 검색 전에 컬렉션 해석 로직이 반드시 필요함

2. `route_perspective_node`를 생성 노드와 분리
   - 관점 선택 기준을 디버깅 가능하게 유지하기 위함

3. 프롬프트 조합 노드를 별도 분리
   - 추후 `prompts.py` 구현본 merge 시 결합 지점을 명확히 하기 위함

---

## 모듈별 구현 명세

### `core/graph.py`

#### 책임

- LangGraph state schema 정의
- 노드 함수 정의
- 노드 간 데이터 계약 정의
- 조건부/직선 엣지 정의
- compile 된 그래프 반환 함수 정의
- mock payload 기반 실행 함수 정의

#### 제안 함수 목록

1. `build_question_graph()`
   - 역할: 그래프 정의 및 compile
   - 입력: 없음
   - 반환: compiled LangGraph app

2. `run_question_graph(payload: dict) -> dict`
   - 역할: mock payload로 그래프 실행
   - 입력: 테스트용 payload
   - 반환: 최종 응답 payload

3. `build_mock_payload(...) -> dict` `선택`
   - 역할: 테스트용 입력 생성 헬퍼
   - 비고: 필수는 아니지만 `test_graph.py`에서 사용 가능

---

### 상태 스키마

#### 1. Request State

- `question: str`
- `subject_id: str`
- `selected_perspective: str`
- `interests: list[str] | str | None`
- `chat_history: list[dict]`
- `session_scope_id: str | None`

#### 2. Analysis State

- `normalized_question: str`
- `question_intent: str`
- `bloom_level: int | None`
- `bloom_label: str | None`
- `bloom_confidence: float`
- `bloom_reason: str`
- `improvement_tip: str | None`

#### 3. Retrieval Routing State

- `collection_candidates: list[str]`
- `resolved_collection_name: str | None`
- `collection_resolution_reason: str`
- `retrieval_query: str`

#### 4. Retrieval State

- `retrieved_docs: list`
- `retrieval_context: str`
- `citations: list[dict]`
- `retrieval_hit: bool`

#### 5. Routing State

- `perspective: str | None`
- `routing_reason: str`

#### 6. Generation State

- `prompt_input: dict`
- `answer_draft: str`
- `answer_final: str`

#### 7. Control State

- `status: str`
- `retry_count: int`
- `error_code: str | None`
- `error_message: str | None`
- `validation_result: str`
- `conversation_store_policy: str | None`

---

### 노드 설계

#### 1. `init_request_node(state) -> state_update`

- **목적**: raw payload를 그래프에서 사용할 표준 형식으로 정규화
- **입력 파라미터**:
  - `question`
  - `subject_id`
  - `selected_perspective`
  - `interests`
  - `chat_history`
  - `session_scope_id`
- **출력 필드**:
  - `question`
  - `subject_id`
  - `selected_perspective`
  - `interests`
  - `chat_history`
  - `session_scope_id`
  - `retry_count=0`
  - `status="ok"`
  - `validation_result="skipped"`
  - `conversation_store_policy="browser_session_state"`
- **내부 로직**:
  1. payload에서 필수 키 존재 여부 확인
  2. `chat_history`가 `None`이면 빈 리스트로 정규화
  3. `interests`가 문자열이면 단일 리스트 또는 그대로 유지할 내부 정책 통일
  4. `selected_perspective`가 비어 있으면 `auto`로 보정
  5. `session_scope_id`가 없으면 호출부에서 만든 세션 식별자를 그대로 사용하거나 `None` 유지
  6. 상태 기본값 초기화
- **비고**:
  - 여기서는 판단 로직을 최소화
  - 검증 실패 처리는 다음 노드에서 담당

#### 2. `prerequisite_check_node(state) -> state_update`

- **목적**: 그래프 진입 가능 여부 판단
- **입력 필드**:
  - `question`
  - `subject_id`
  - `selected_perspective`
- **출력 필드**:
  - 정상 시 `status="ok"`
  - 실패 시 `status="error"`, `error_code`, `error_message`
- **검사 규칙**:
  1. `question.strip()` 결과가 비어 있으면 실패
  2. `subject_id`가 비어 있으면 실패
  3. `selected_perspective`가 허용값 집합에 없으면 실패
- **허용 관점 값**:
  - `auto`
  - `concept`
  - `principle`
  - `analogy`
  - `relation`
  - `usage`
  - `caution`
- **내부 로직**:
  1. 질문 공백 여부 검사
  2. 과목 미선택 여부 검사
  3. 관점 값 유효성 검사
  4. 최초 실패 사유를 `error_code`에 기록
- **설계 이유**:
  - 이후 노드가 전제 조건을 믿고 동작할 수 있게 함

#### 3. `analyze_question_node(state) -> state_update`

- **목적**: 질문 분석 결과 확정
- **입력 필드**:
  - `question`
  - `chat_history`
- **출력 필드**:
  - `normalized_question`
  - `question_intent`
  - `bloom_level`
  - `bloom_label`
  - `bloom_confidence`
  - `bloom_reason`
  - `improvement_tip`
- **연동 대상**:
  - `core/utils.py`의 Bloom 1차 규칙 함수
- **내부 로직**:
  1. 질문 문자열 공백/개행 정리
  2. 기존 Bloom 규칙 함수 호출
  3. 반환값에서 `level`, `confidence`, `keywords_found`, `method` 추출
  4. `level`을 `bloom_label`로 변환
  5. 질문 패턴 기반으로 `question_intent` 산출
     - 정의 요청
     - 원리 설명 요청
     - 비교 요청
     - 활용 요청
     - 주의사항 요청
     - 비유 요청
  6. `confidence`가 임계치보다 낮으면 추후 LLM 보정 훅 사용 가능하도록 여지 남김
  7. 간단한 `improvement_tip` 생성
- **질문 의도 분류 규칙 초안**:
  - `"무엇"`, `"정의"`, `"뜻"` 포함 → `concept`
  - `"왜"`, `"원리"`, `"작동"` 포함 → `principle`
  - `"차이"`, `"비교"`, `"관계"` 포함 → `relation`
  - `"어떻게 사용"`, `"활용"`, `"실무"` 포함 → `usage`
  - `"주의"`, `"실수"`, `"문제"` 포함 → `caution`
  - `"비유"`, `"쉽게"` 포함 + interests 존재 가능 → `analogy`
- **비고**:
  - 여기서 관점을 최종 확정하지는 않음
  - 의도 힌트만 생산

#### 4. `resolve_collection_node(state) -> state_update`

- **목적**: `subject_id`를 실제 Chroma 컬렉션명으로 해석
- **입력 필드**:
  - `subject_id`
- **출력 필드**:
  - `collection_candidates`
  - `resolved_collection_name`
  - `collection_resolution_reason`
- **배경**:
  - 현재 확인된 컬렉션명은 과목명 한글 문자열이 아니라 `ncs_LM...` 형식
  - 따라서 `subject_id`를 바로 `collection_name`으로 넘길 수 없음
- **내부 로직**:
  1. `data/chroma_db`에서 사용 가능한 컬렉션 목록 조회
  2. 프로젝트 내부에서 관리할 `subject_id -> collection_name` 매핑 테이블 우선 탐색
  3. 매핑이 없으면 alias 후보 탐색
  4. 그래도 없으면 부분 문자열/정규화 문자열 비교
  5. 최종 1개 확정 시 `resolved_collection_name` 저장
  6. 0개면 오류 상태 또는 retrieval skip 상태로 처리
- **권장 설계**:
  - 매핑 테이블은 하드코딩 또는 설정 상수로 분리
  - collection 자동 추측은 fallback으로만 사용
- **현재 확인된 컬렉션 목록**
  - `ncs_LM2001020211_23v6____________20251108`
  - `ncs_LM2001020205_23v6____________20251108`
  - `ncs_LM2001020201_23v5_________20251108`
- **계획 메모**:
  - 실제 과목명과 컬렉션명 대응표를 먼저 정리한 뒤 구현하는 편이 안전

#### 5. `retrieve_context_node(state) -> state_update`

- **목적**: resolved collection에서 RAG 검색 수행
- **입력 필드**:
  - `resolved_collection_name`
  - `normalized_question`
  - `question`
- **출력 필드**:
  - `retrieval_query`
  - `retrieved_docs`
  - `retrieval_context`
  - `citations`
  - `retrieval_hit`
- **연동 대상**:
  - `core.rag.get_retriever(collection_name: str, top_k: int = 5)`
- **내부 로직**:
  1. `normalized_question`이 있으면 그것을 우선 검색 질의로 사용
  2. resolved collection 기준 retriever 생성
  3. top-k 검색 수행
  4. 검색 결과 문서를 생성용 context 문자열로 합성
  5. 메타데이터에서 `source`, `pages`, `subtitle` 추출해 citation 구성
  6. 결과가 없으면 `retrieval_hit=False`, `retrieval_context=""`
- **검색 결과 포맷 정책**:
  - context는 길이 제한을 둠
  - 문서 간 구분자를 넣음
  - citation은 UI 포맷이 아니라 구조화 리스트로 유지
- **비고**:
  - rerank는 현재 MVP 제외
  - 검색 실패 자체를 치명적 오류로 보지 않음

#### 6. `route_perspective_node(state) -> state_update`

- **목적**: 6관점 중 최종 관점 1개 선택
- **입력 필드**:
  - `selected_perspective`
  - `question_intent`
  - `bloom_level`
  - `interests`
  - `retrieval_hit`
- **출력 필드**:
  - `perspective`
  - `routing_reason`
- **핵심 설계 결정**:
  - **점수제 미사용**
  - **우선순위 기반 단일 결정 로직 사용**
- **이유**:
  - 시간이 적고 디버깅 가능성이 중요
  - 점수제는 기준이 많아져 계획서와 구현 모두 복잡해짐
- **우선순위 로직**:
  1. `selected_perspective != "auto"` 이면 사용자가 선택한 관점으로 고정
  2. `question_intent`가 명확하면 그 관점 채택
  3. `question_intent`가 불명확하면 `bloom_level` 기반 기본 관점 선택
  4. `interests`가 존재하고 설명 난이도가 높은 질문이면 `analogy`로 보정 가능
  5. 위 규칙으로도 확정이 안 되면 `concept` fallback
- **Bloom 기반 기본 매핑**
  - 1~2단계 → `concept` 또는 `principle`
  - 3단계 → `usage`
  - 4단계 → `relation`
  - 5~6단계 → `caution` 또는 `relation`
- **명확한 고정 규칙**
  - 사용자가 직접 선택한 값은 override 하지 않음
- **보정 규칙**
  - `selected_perspective="auto"`일 때만 자동 결정
  - interests 존재만으로 무조건 `analogy`를 고르지 않음
- **routing_reason 예시**
  - `user_selected`
  - `intent_relation`
  - `bloom_usage_default`
  - `fallback_concept`

#### 7. `build_prompt_input_node(state) -> state_update`

- **목적**: 생성 노드에 전달할 입력 구조 조립
- **입력 필드**:
  - `perspective`
  - `question`
  - `retrieval_context`
  - `subject_id`
  - `interests`
  - `improvement_tip`
  - `chat_history`
- **출력 필드**:
  - `prompt_input`
- **내부 로직**:
  1. 기본 입력 구조 생성
  2. `retrieval_context` 포함
  3. `subject_id` 포함
  4. `perspective` 포함
  5. `chat_history`는 최근 N개만 사용하도록 축약
  6. `perspective == "analogy"`일 때만 interests 실질 주입
- **추후 연동 계약**:
  - `core.prompts.py`의 다음 함수 사용 전제

```python
def get_perspective_prompt(
    perspective: str,
    question: str,
    context: str,
    subject: str,
    interests: Optional[str] = None,
) -> str:
    ...
```

- **설계 메모**:
  - `prompt_input`은 문자열 1개보다 구조화 dict가 더 적합
  - 실제 prompt 문자열 생성 책임은 `prompts.py`에 둠

#### 8. `generate_answer_node(state) -> state_update`

- **목적**: 메인 답변 초안 생성
- **입력 필드**:
  - `prompt_input`
- **출력 필드**:
  - `answer_draft`
- **내부 로직**:
  1. `prompts.py`의 관점별 프롬프트 함수 호출
  2. 해당 프롬프트를 LLM에 전달
  3. 문자열 응답 수신
  4. `answer_draft`에 저장
- **생성 원칙**:
  - RAG 컨텍스트가 있으면 그 범위 우선
  - 검색 근거가 부족하면 단정적 서술 축소
  - 관점별 말하기 방식은 프롬프트에 위임
- **비고**:
  - 현재 단계는 설계만 수행
  - 실제 LLM/모델 선택은 별도 구현 단계에서 결정

#### 9. `finalize_response_node(state) -> state_update`

- **목적**: 그래프 외부에 반환할 최종 payload 구성
- **입력 필드**:
  - `answer_draft`
  - `citations`
  - `bloom_level`
  - `bloom_label`
  - `improvement_tip`
  - `perspective`
  - `status`
- **출력 필드**:
  - `answer_final`
  - 반환용 최종 상태
- **내부 로직**:
  1. `answer_draft`가 비어 있으면 fallback 메시지 대체
  2. citation 구조 정리
  3. 최종 응답에 필요한 필드만 유지
  4. 외부 반환 형식으로 정렬
- **최종 반환 payload**
  - `status`
  - `answer`
  - `perspective`
  - `bloom_level`
  - `bloom_label`
  - `improvement_tip`
  - `citations`
  - `error_code`
  - `error_message`

#### 10. `validate_answer_node(state) -> state_update` `Phase 2`

- **목적**: 생성 답변 검증
- **검증 항목**:
  - 질문 의도 부합 여부
  - 검색 근거 이탈 여부
  - 명백한 오류 여부
- **출력 필드**:
  - `validation_result`
  - `error_message`
- **비고**:
  - 현재 단계 MVP 제외
  - 위치만 설계에 남김

---

### 엣지 설계

#### 시작 노드

- `set_entry_point("init_request_node")`

#### 기본 엣지

- `init_request_node` → `prerequisite_check_node`
- `prerequisite_check_node` → `analyze_question_node`
- `prerequisite_check_node` → `resolve_collection_node`
- `resolve_collection_node` → `retrieve_context_node`
- `analyze_question_node` → `route_perspective_node`
- `retrieve_context_node` → `route_perspective_node`
- `route_perspective_node` → `build_prompt_input_node`
- `build_prompt_input_node` → `generate_answer_node`
- `generate_answer_node` → `finalize_response_node`

#### 조건부 엣지

- `prerequisite_check_node`
  - `status="error"`이면 종료 경로
  - `status="ok"`이면 계속 진행

- `resolve_collection_node`
  - 컬렉션 해석 실패 시
    - 설계안 A: 오류 종료
    - 설계안 B: retrieval skip 후 생성은 계속
  - **채택안**: B
  - 사유: 검색 실패와 그래프 실패를 분리하는 편이 MVP에서 안전

- `generate_answer_node` `Phase 2`
  - 검증 노드 활성화 시 `validate_answer_node`로 이동

#### 병렬 분기 규칙

- `analyze_question_node`와 `resolve_collection_node`는 병렬 가능
- `retrieve_context_node`는 `resolved_collection_name` 필요하므로 `resolve_collection_node` 뒤에 위치
- state 충돌 방지 원칙:
  - 분석 노드는 analysis state만 갱신
  - 컬렉션 해석 노드는 retrieval routing state만 갱신
  - 검색 노드는 retrieval state만 갱신

---

### 그래프 외부 계약

#### 입력 계약

```python
{
    "question": str,
    "subject_id": str,
    "selected_perspective": str,
    "interests": list[str] | str | None,
    "chat_history": list[dict] | None,
    "session_scope_id": str | None,
}
```

#### 출력 계약

```python
{
    "status": "ok" | "error",
    "answer": str,
    "perspective": str | None,
    "bloom_level": int | None,
    "bloom_label": str | None,
    "improvement_tip": str | None,
    "citations": list[dict],
    "error_code": str | None,
    "error_message": str | None,
}
```

---

### 외부 모듈 연동 기준

#### `core/utils.py`

- 재구현하지 않음
- 그래프가 기대하는 것:
  - Bloom 1차 분석 함수 호출 가능
  - 레이블 변환 가능
  - 필요 시 과목 감지 fallback 사용 가능

#### `core/prompts.py`

- 현재 단계 구현 대상 아님
- 그래프가 기대하는 것:
  - `get_perspective_prompt(...)` 제공
  - 관점별 prompt 생성 함수 내부 구현 완료 상태
- `analogy` 관점에서는 `interests`가 실질 입력으로 사용됨

#### `core/rag.py`

- 그래프는 아래 계약만 사용
  - `get_retriever(collection_name: str, top_k: int = 5)`
- 그래프 내부에서 할 일
  - resolved collection name 전달
  - 검색 결과를 context로 합성
  - citation 구조화
  - 검색 실패 시 fallback 처리

---

## 대화 기록 저장 정책

### 목표

- 회원 기능 없이 브라우저 접속 단위로 대화 기록 유지
- 브라우저 창/탭을 닫으면 대화 기록 소멸
- 새로고침 중에는 가능하면 대화 기록 유지
- 서버 재시작, 세션 만료, 브라우저 세션 종료 시 기록 소멸 허용

### 권장 정책

- **저장 단위**: 브라우저 세션 단위
- **저장 위치**: Streamlit `st.session_state`
- **그래프 입력 단위**: `chat_history`
- **세션 식별 개념**: Streamlit이 관리하는 사용자 연결 세션 또는 해당 세션에서 유지되는 `session_state`

### 이 방식으로 가능한지

- **가능한 방향**: 예
- 다만 “브라우저 창을 닫는 순간 즉시 삭제 이벤트를 정확히 감지”하는 방식보다는,
  세션이 끊기면 서버 측 `session_state`가 더 이상 유지되지 않는 구조를 활용하는 방식이 현실적임

### 동작 기준 정리

1. **같은 브라우저 탭에서 대화 진행**
   - `st.session_state["chat_history"]`에 기록 유지 가능

2. **새로고침**
   - 일반적으로 같은 세션 흐름이면 기록이 유지될 수 있음
   - 다만 Streamlit 내부 세션 재연결 상황에 따라 항상 100% 보장으로 가정하지는 않음
   - 계획상 기대 동작은 “새로고침 시 유지”로 두되, 구현 시 실제 동작 확인 필요

3. **브라우저 탭/창 닫기**
   - 해당 세션 연결이 끊기면 서버 메모리상의 `session_state`도 유지되지 않는 방향으로 설계 가능
   - 별도 파일/DB 저장을 하지 않으면 재접속 시 기록이 사실상 사라짐

4. **새 탭으로 다시 접속**
   - 새 세션으로 간주될 수 있으므로 기록이 없는 상태로 시작 가능

5. **서버 재시작**
   - 메모리 기반 상태이므로 기록 소멸

### 계획상 채택안

- **1차 구현 채택안**:
  - 대화 기록은 `st.session_state["chat_history"]`에만 저장
  - `data/user_profiles/`, JSON 파일, DB, Chroma 등에 채팅 기록 저장하지 않음
  - `core/graph.py`는 항상 호출 시점의 `chat_history`만 입력으로 받음
- **이유**:
  - 회원 기능이 없는 현재 MVP와 가장 잘 맞음
  - 구현 단순성 높음
  - 개인정보/상태 동기화 부담 낮음

### 그래프와 UI의 책임 분리

- UI/호출부 책임:
  - `st.session_state["chat_history"]` 유지
  - 각 질문 전 그래프에 `chat_history` 전달
  - 응답 수신 후 `chat_history` append

- 그래프 책임:
  - 전달받은 `chat_history`를 읽기 전용 입력으로 사용
  - 필요 시 최근 N개만 잘라 prompt input에 반영
  - 대화 기록의 영속 저장은 하지 않음

### 설계 메모

- 현재 계획 문서 기준으로는 UI 연동 제외지만, 추후 연동 시 대화 기록 저장 정책은 위 방식으로 고정하는 것이 적절
- “브라우저 창을 닫으면 기록 소멸” 요구에는 메모리 기반 세션 저장이 가장 가까움
- “새로고침 시 유지 여부”는 Streamlit 실제 세션 동작 검증이 필요하므로 테스트 체크리스트에 포함

---

## 예외 처리 및 방어 로직

### 정상 흐름

1. mock payload 수신
2. 요청 정규화
3. 필수값 검증
4. 질문 분석 + 컬렉션 해석
5. 컬렉션 기반 검색
6. 관점 선택
7. 프롬프트 입력 조합
8. 답변 생성
9. 최종 payload 반환

### 예외 흐름

1. **질문 공백**
   - `prerequisite_check_node`에서 차단

2. **과목 미선택**
   - `prerequisite_check_node`에서 차단

3. **잘못된 관점 값**
   - `prerequisite_check_node`에서 차단

4. **Bloom 규칙 분석이 애매함**
   - 기존 규칙 함수 결과를 사용하되 confidence 낮음으로 기록
   - 그래프는 계속 진행

5. **컬렉션 해석 실패**
   - retrieval skip
   - `resolved_collection_name=None`
   - `retrieval_hit=False`
   - 생성은 계속 진행

6. **검색 결과 0건**
   - 치명적 오류로 보지 않음
   - retrieval context 없이 생성 진행

7. **프롬프트 함수 미연동**
   - 구현 단계에서 막히는 포인트
   - 현재 계획서에서는 연동 계약만 정의

8. **LLM 호출 실패**
   - `status="error"`
   - 일반 fallback 메시지 반환

9. **병렬 분기 state 충돌**
   - 노드별 갱신 범위 고정
   - reducer 없는 중복 키 갱신 금지

10. **버전 불일치**
   - 1.x 환경에서 0.2 기준 구현 금지

11. **브라우저 세션 종료**
   - `st.session_state` 기반 대화 기록 소멸 허용

12. **새로고침 후 세션 재연결 편차**
   - 실제 구현 후 유지 여부 수동 검증 필요

---

## 테스트 계획

### 목적

- UI 없이 콘솔에서 그래프 설계 검증
- 노드 간 state 흐름 확인
- mock payload별 분기 결과 확인

### 대상 파일

- `test_graph.py` `추후 작성`

### 테스트 방식

- Streamlit 페이지 대신 콘솔 실행
- mock payload 여러 개 준비
- 각 payload에 대한 최종 반환값과 핵심 state 출력

### 테스트 항목

1. **정상 질문 + 정상 과목 + auto 관점**
   - Bloom 분석 결과 확인
   - 컬렉션 해석 확인
   - 검색 성공 여부 확인
   - 최종 관점 선택 확인

2. **사용자 관점 직접 선택**
   - `selected_perspective="usage"` 등으로 고정
   - 자동 라우팅이 override 하지 않는지 확인

3. **질문 공백**
   - 초반 차단 여부 확인

4. **과목 미입력**
   - 오류 처리 확인

5. **컬렉션 해석 실패 subject**
   - retrieval skip 후 그래프가 계속 도는지 확인

6. **검색 0건 질문**
   - fallback 응답 경로 확인

7. **analogy 관점 + interests 존재**
   - interests가 prompt input에 들어가는지 확인

8. **Bloom low-confidence 질문**
   - confidence 낮은 상태로 계속 진행되는지 확인

9. **새로고침 시 대화 기록 유지 여부**
   - 같은 브라우저 세션에서 `chat_history`가 유지되는지 확인

10. **브라우저 창 닫기 후 재접속**
   - 새 세션으로 시작되어 기록이 초기화되는지 확인

### 콘솔 출력 권장 항목

- `status`
- `resolved_collection_name`
- `bloom_level`
- `question_intent`
- `perspective`
- `retrieval_hit`
- `citations`
- `answer`

---

## Phase 계획

### Phase 1. 버전 고정

- LangGraph 0.2 계열 고정
- lock 재생성
- 실제 설치 버전 재확인

### Phase 2. 그래프 골격 구현

- 상태 스키마 정의
- 진입/검증 노드 정의
- 질문 분석 노드 정의
- 컬렉션 해석 노드 정의
- 검색 노드 정의
- 관점 라우팅 노드 정의
- 프롬프트 입력 조합 노드 정의
- 최종 응답 노드 정의

### Phase 3. 외부 모듈 연동

- 기존 Bloom 규칙 로직 연결
- 컬렉션명 매핑표 연결
- `prompts.py` 구현본 연결
- subject 관리 정책 정리
- README 운영 가이드 초안 준비

### Phase 4. 확장

- 검증 노드 추가
- 재시도 정책 추가
- 이후 필요 시 Streamlit UI 연동
- 브라우저 세션 기반 chat history 정책 실제 검증

---

## 체크리스트

- [ ] LangGraph 0.2 계열로 의존성 고정
- [ ] 실제 설치 버전 재확인
- [ ] mock payload 입력 계약 확정
- [ ] state schema 확정
- [ ] `init_request_node` 내부 로직 확정
- [ ] `prerequisite_check_node` 검증 규칙 확정
- [ ] `analyze_question_node` 입출력 및 내부 로직 확정
- [ ] `resolve_collection_node` 해석 로직 확정
- [ ] subject_id 와 collection_name 대응표 정리
- [ ] subject_id / label / collection_name 관리 위치 확정
- [ ] README에 `과목 수정하는 법` 섹션 추가 항목 정의
- [ ] `retrieve_context_node` 검색 결과 포맷 정책 확정
- [ ] `route_perspective_node` 우선순위 로직 확정
- [ ] `build_prompt_input_node` 입력 구조 확정
- [ ] `generate_answer_node` 연동 계약 확정
- [ ] `finalize_response_node` 반환 포맷 확정
- [ ] 콘솔 테스트 파일 `test_graph.py` 계획 확정
- [ ] 브라우저 세션 기반 chat history 저장 정책 반영
- [ ] 새로고침/창 닫기 시 chat history 동작 검증 항목 추가
- [ ] Guardrail/검증 노드는 Phase 2로 분리 유지

---

## 구현 기록

- 추후 코드 구현 단계에서 작성

---

## 참고 자료

- AGENTS 규칙 문서: `AGENTS.md`
- 상위 범위 문서: `docs/plans/start_plan.md`
- RAG 세부 계획: `docs/plans/RAG_plan.md`
- LangGraph 0.2.0 PyPI: https://pypi.org/project/langgraph/0.2.0/
- LangGraph 0.2.73 PyPI: https://pypi.org/project/langgraph/0.2.73/
- LangGraph 0.2.0 PyPI JSON: https://pypi.org/pypi/langgraph/0.2.0/json
- LangGraph 0.2.73 PyPI JSON: https://pypi.org/pypi/langgraph/0.2.73/json
