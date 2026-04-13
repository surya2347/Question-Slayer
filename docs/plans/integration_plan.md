# pages ↔ core 연동 기준 및 작업 계획

### 날짜
2026-04-13

---

## 이미 연결된 것들

아래 4개는 `core/graph.py` 내부에서 이미 완전 연동되어 있습니다. 건드릴 필요 없습니다.

| 연결 | 위치 | 상태 |
|---|---|---|
| `graph.py` → `score_bloom_by_keyword()` | `analyze_question_node()` 내부 | 완전 연동 |
| `graph.py` → `get_retriever()` | `retrieve_context_node()` 내부 | 완전 연동 |
| `graph.py` → `get_perspective_prompt()` | `generate_answer_node()` 내부 | 완전 연동 |
| `graph.py` → `build_fallback_answer()` | `generate_answer_node()` 실패 경로 | 완전 연동 |

---

## 연동이 필요한 사안들

### 1. `pages/0_Home.py` ↔ `core/graph.py` — 과목 선택 기준 불일치

**현재 상태:**

- `Home.py`는 `core/utils.py`의 `SUBJECT_KEYWORDS.keys()`를 selectbox 옵션으로 사용
  - 옵션값: "정보처리기사", "빅데이터분석기사", "정보보안기사" 등 (임시 자격증명, 벡터 DB와 무관)
  - 세션 키: `st.session_state.subject` (한글 전체명)
- `graph.py`는 `SUBJECT_COLLECTION_MAP`의 영문 키를 `subject_id`로 해석
  - 허용 키: `requirements_analysis`, `data_io_implementation`, `server_program_implementation`
  - 실제 Chroma 컬렉션과 1:1 매핑된 유일한 과목 목록

**기준: `graph.py`의 `SUBJECT_COLLECTION_MAP`**
벡터 DB와 직접 연결된 실데이터이므로 이쪽이 정답.

**연동 방향:**

- `Home.py`가 `core.graph.SUBJECT_COLLECTION_MAP`을 import해서 selectbox 옵션으로 사용
- 세션 키를 분리:
  - `st.session_state.subject_id` → 영문 키 (`requirements_analysis` 등)
  - `st.session_state.subject_label` → 한글 표시명 (`SUBJECT_COLLECTION_MAP[key]["label"]`)
- 기존 `st.session_state.subject` 참조 코드 전체 교체 대상

---

### 2. `pages/1_Chat.py` ↔ `core/graph.py` — 더미 → 실호출 교체

**현재 상태:**

| 항목 | Chat.py 현재 | graph.py 기대 |
|---|---|---|
| 답변 생성 | `get_dummy_response()` | `run_question_graph(payload)` |
| Bloom 판별 | `_dummy_bloom()` | graph 반환값 `bloom_level`, `bloom_label` |
| 과목 키 | `st.session_state.subject` (한글) | `payload["subject_id"]` (영문 키) |
| 관점 확정값 | assistant 메시지에 없음 | graph 반환값 `perspective` |

**기준: `graph.py`의 `run_question_graph()` 반환값**
더미 함수 2개(`get_dummy_response`, `_dummy_bloom`) 제거 대상.

**연동 방향:**

send 버튼 핸들러를 아래 흐름으로 교체:

```python
from core.graph import run_question_graph

payload = {
    "question": user_input,
    "subject_id": st.session_state.subject_id,
    "selected_perspective": st.session_state.perspective or "auto",
    # ✅ 검증 완료: Chat.py의 PERSPECTIVES dict가 {영문키: "한글라벨"} 구조.
    # 라디오 버튼 선택 시 p_keys[p_labels.index(selected_label)]로 역변환하여
    # st.session_state.perspective에는 "concept", "principle" 등 영문 키가 저장됨.
    # graph에는 영문 키가 그대로 전달되므로 문제 없음.
    "interests": st.session_state.get("interests", []),
    "chat_history": [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ],
    "session_scope_id": st.session_state.get("session_scope_id"),
}

result = run_question_graph(payload)
```

assistant 메시지 저장 계약:

```python
st.session_state.messages.append({
    "role": "assistant",
    "content": result["answer"],
    "time": time_str,
    "perspective": result.get("perspective"),
    "bloom_level": result.get("bloom_level"),
    "bloom_label": result.get("bloom_label"),
    # ✅ 검증 완료: score_bloom_by_keyword()가 BLOOM_LEVELS[level]["name_ko"]를 반환.
    # bloom_label은 "지식", "이해", "응용" 등 한글로 저장됨.
    # Chat.py의 BLOOM_BADGE도 한글 기준이므로 일치. 별도 변환 불필요.
    "improvement_tip": result.get("improvement_tip"),
    "citations": result.get("citations", []),
    "error_code": result.get("error_code"),
    "error_message": result.get("error_message"),
})
```

---

### 3. `pages/2_Insight.py` ↔ `pages/1_Chat.py` — 관점 집계 기준 불일치

**현재 상태:**

`Insight.py`의 `_collect_stats()`에서 `perspectives`를 user 메시지에서 읽음:

```python
perspectives = [m.get("perspective") for m in messages if m.get("role") == "user"]
```

- user 메시지의 `perspective` = 사용자가 **선택한** 값 (`selected_perspective`)
- assistant 메시지의 `perspective` = graph가 **확정한** 실제 관점

**기준: assistant 메시지**
graph가 최종 결정한 관점이 실제 설명 방식이므로 통계 기준은 assistant.

**연동 방향:**

`_collect_stats()` 내 perspectives 집계 기준 변경:

```python
# 변경 전
perspectives = [m.get("perspective") for m in messages if m.get("role") == "user"]

# 변경 후
perspectives = [m.get("perspective") for m in messages if m.get("role") == "assistant"]
```

단, `#2` 작업(`Chat.py` 실연동)이 완료되어 assistant 메시지에 `perspective`가 실제로 기록된 이후에 의미가 있음.

---

### 4. `app.py` — 세션 키 표준화 미흡

**현재 상태:**

- `app.py`: `subject`, `interests`만 초기화
- `Home.py`, `Chat.py`, `Insight.py`: 각자 부분적으로 세션 키 초기화 (분산, 중복)

**기준: `merge_plan.md`에 정의된 공통 세션 키 목록**

**연동 방향:**

`app.py`에서 아래 키를 전부 한 번에 초기화:

```python
defaults = {
    "subject_id": None,
    "subject_label": None,
    "interests": [],
    "messages": [],
    "perspective": None,
    "session_scope_id": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
```

각 페이지의 중복 초기화 코드는 제거 대상.

---

## 작업 순서

| 순서 | 작업 | 파일 | 선행 조건 |
|---|---|---|---|
| 1 | 세션 키 표준화 | `app.py` | 없음 |
| 2 | 과목 선택 교체 | `pages/0_Home.py` | #1 완료 |
| 3 | 더미 교체 + graph 실연동 | `pages/1_Chat.py` | #1, #2 완료 |
| 4 | 관점 집계 기준 수정 | `pages/2_Insight.py` | #3 완료 |

---

## 구현 시 주의사항 체크리스트

### app.py
- [ ] 기존 `subject` 키 초기화 코드를 `subject_id`, `subject_label`로 교체 (하위 호환 주의)
- [ ] `session_scope_id` 초기화 시 `uuid` 기반 고정값으로 생성할 것 (매 rerun마다 새로 생성하면 안 됨)

### pages/0_Home.py
- [ ] `SUBJECT_KEYWORDS` import 제거, `SUBJECT_COLLECTION_MAP` import로 교체
- [ ] selectbox 옵션값이 한글 표시명(`label`)이고, 저장값이 영문 키(`subject_id`)임을 혼동하지 않을 것
- [ ] 저장 시 `st.session_state.subject_id`와 `st.session_state.subject_label` 양쪽 모두 저장
- [ ] 기존 `st.session_state.subject` 참조 전부 제거 (사이드바 표시 포함)

### pages/1_Chat.py
- [ ] `_dummy_bloom()` 함수 제거
- [ ] `get_dummy_response()` 함수 제거
- [ ] `run_question_graph()` import 추가 (`from core.graph import run_question_graph`)
- [ ] payload의 `subject_id`는 `st.session_state.subject_id` 사용 (None 가능성 방어 필요)
- [ ] `subject_id`가 None이면 전송 버튼 비활성화 또는 경고 배너 표시
- [ ] `selected_perspective`는 이미 영문 키로 저장되어 있으므로 변환 불필요
- [ ] assistant 메시지에 `perspective`, `bloom_level`, `bloom_label`, `improvement_tip`, `citations` 저장
- [ ] `result["status"] == "error"` 일 때 error_message를 화면에 표시하는 분기 추가
- [ ] `chat_history` 구성 시 `role`/`content` 키만 전달 (메타데이터 제외)
- [ ] 기존 `st.session_state.subject` 사이드바 표시를 `subject_label`로 교체

### pages/2_Insight.py
- [ ] `_collect_stats()` 내 `perspectives` 집계 기준을 user → assistant 메시지로 변경
- [ ] assistant 메시지에 `perspective`가 없는 경우(`None`) 집계에서 제외 처리
- [ ] `bloom_label`이 한글(`"지식"` 등)로 저장됨을 전제로 차트 레이블 구성
- [ ] 기존 `st.session_state.subject` 사이드바 표시를 `subject_label`로 교체
- [ ] 데이터 없을 때(`has_data == False`) 더미 데이터가 아닌 안내 문구만 표시되는지 확인
