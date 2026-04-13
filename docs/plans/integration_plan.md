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
    [//] 해당 perspective을 가져오는게 하는게. streamlit chat 화면에 있는 질문 입력 칸 바로 위에 있는 개념, 원리, 비유, 관계, 활용, 주의사항 라디오 버튼들 중 하나를 클릭했을 때, 해당 관점으로 세팅되는게 맞는지 확인해줘. 그리고 이게 streamlit에는 개념,원리 이런 식으로 한글로 되어있는데, 영어나 관점 label? 로 전달 되어야 하지 않나? core에는 관점에 한글명이 없을텐데. 확인해줘.
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
    [//] 이것도 내가 알기로,, core에서는 영어명으로 bloom단계 세팅이 되어 있을텐데, 아닌가? 이거 문제없나? 이거 한글로 저장되는지 영어로 저장되는지 한번 확인해줘.
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
