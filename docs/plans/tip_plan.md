# Improvement Tip 최종 답변 붙이기 계획

## 개요 및 목표
최종 LLM 생성 답변 뒤에 `improvement_tip`을 구분선과 함께 텍스트로 붙여서 화면에 표시.
사용자가 다음 질문을 더 잘 할 수 있도록 가이드 제시.

기존: `improvement_tip`은 LLM 프롬프트 부록(【질문 개선 팁】)과 fallback 답변에만 사용됨.
변경: 최종 사용자에게 보이는 `answer_final`에도 구분선 + 팁을 직접 표시.

---

## 핵심 플로우 (improvement_tip 데이터 경로)

```
1. analyze_question_node
   └─ _build_improvement_tip(bloom_level, bloom_confidence, question_intent)
   └─ 출력: state.improvement_tip (str, 항상 값 있음)
                ↓
2. build_prompt_input_node
   └─ prompt_input["improvement_tip"] = state.improvement_tip
                ↓
3. generate_answer_node
   ├─ LLM 프롬프트에 【질문 개선 팁】으로 주입 (기존, 변경 없음)
   ├─ fallback: build_fallback_answer()에서 학습 팁 행 제거 ← [수정 대상]
   └─ 출력: answer_draft (현재 improvement_tip 미포함)
                ↓
4. finalize_response_node ← [수정 대상]
   ├─ answer_draft → answer_final 구성
   ├─ [NEW] improvement_tip이 있으면 answer_final 뒤에 구분선 + 팁 붙이기
   └─ 출력: answer_final, answer (동일 값)
                ↓
5. run_question_graph → result["answer"] → Chat 페이지 표시
```

---

## 모듈별 구현 명세

### 1. `finalize_response_node()` 수정 (core/graph.py)
**위치**: `finalize_response_node` 함수 내부

**변경 내용**:
- 함수 진입 시 `improvement_tip`을 `state`에서 추출
- `answer_final` 값 구성 직후, return 직전에 `improvement_tip` 붙이기
- 정상 경로와 오류 경로 **모두** 동일하게 적용

**포맷**:
```
answer_final += "\n\n---\n💡 다음 번 팁:\n" + improvement_tip
```

**코드 로직**:
```python
improvement_tip = (state.get("improvement_tip") or "").strip()

# 오류 경로
answer_final = state.get("answer_draft") or "..."
if improvement_tip:
    answer_final += f"\n\n---\n💡 다음 번 팁:\n{improvement_tip}"
return { "answer_final": answer_final, "answer": answer_final, ... }

# 정상 경로 (동일)
answer_final = state.get("answer_draft") or "..."
if improvement_tip:
    answer_final += f"\n\n---\n💡 다음 번 팁:\n{improvement_tip}"
return { ... }
```

### 2. `build_fallback_answer()` 수정 (core/prompts.py)
**위치**: `build_fallback_answer` 함수 내부

**변경 내용**:
- 기존 fallback 답변 마지막 행의 `학습 팁: {improvement_tip}` 텍스트를 **제거**
- `finalize_response_node`에서 통합 포맷으로 팁을 붙이므로 fallback에서 중복 표시 불필요
- `improvement_tip` 매개변수는 유지 (함수 시그니처 변경 최소화)

**기존 코드** (제거 대상 행):
```python
# preview 있을 때
f"학습 팁: {improvement_tip or '핵심 용어와 조건을 함께 질문하면 더 정확한 답을 받을 수 있습니다.'}"

# preview 없을 때
f"학습 팁: {improvement_tip or '예: 어떤 상황에서 쓰는지, 무엇과 비교할지까지 함께 적어보세요.'}"
```

**변경 후**: 두 return 경로 모두에서 `학습 팁:` 행 제거.
```python
# preview 있을 때
return (
    f"[{subject} | {PERSPECTIVE_TITLES.get(perspective, '학습 설명')}]\n"
    f"질문: {question}\n\n"
    "검색된 학습 자료를 바탕으로 보면 다음 내용을 우선 참고할 수 있습니다.\n"
    f"{preview}"
)

# preview 없을 때
return (
    f"[{subject} | {PERSPECTIVE_TITLES.get(perspective, '학습 설명')}]\n"
    f"질문: {question}\n\n"
    "현재 검색된 학습 컨텍스트가 없어 일반적인 설명만 제공할 수 있습니다. "
    "정확도를 높이려면 과목을 다시 확인하고, 핵심 키워드나 상황을 더 구체적으로 적어주세요."
)
```

### 3. `app.py` 수정 — `load_dotenv()` 추가
**위치**: `app.py` 최상단 (import 직후, `st.set_page_config` 이전)

**변경 내용**:
- `from dotenv import load_dotenv` 추가
- `load_dotenv()` 호출 추가
- `.env` 파일의 환경변수가 프로세스에 로드되도록 보장

**코드**:
```python
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(...)
```

**근거**: 현재 `app.py`에 `load_dotenv()`가 없어 `.env`의 `OPENAI_API_KEY`, `QUESTION_SLAYER_ENABLE_LLM`, `QUESTION_SLAYER_ENABLE_REMOTE_RAG` 등 환경변수가 로드되지 않음. `core/graph.py`의 LLM/RAG 호출이 환경변수 부재로 항상 비활성화됨.

---

## 스키마 변경 여부

**GraphState**: 변경 없음. `improvement_tip: Optional[str]` 이미 존재.

**run_question_graph 반환값**: 이미 `improvement_tip`을 포함. 변경 없음.

**1_Chat.py**: 이미 `result.get("improvement_tip")`을 메시지에 저장. 변경 없음.
단, `answer_final`에 팁이 포함되므로 `content` 필드에 팁까지 함께 표시됨.

**결론: 스키마 변경 불필요.**

---

## 사이드이펙트 점검

| 점검 항목 | 결과 | 설명 |
|-----------|------|------|
| LLM 호출 영향 | ❌ 없음 | `finalize_response_node`는 LLM 호출 없음 |
| fallback 답변 중복 | ✅ 해소 | `build_fallback_answer()`에서 `학습 팁:` 행 제거. `finalize_response_node`에서만 통합 표시 |
| 오류 경로 안전성 | ✅ 안전 | `improvement_tip`이 None/빈 → if 체크로 스킵 |
| `load_dotenv` 부재 | ✅ 해소 | `app.py`에 `load_dotenv()` 추가로 `.env` 환경변수 정상 로드 |
| Chat 메시지 저장 | ✅ 무영향 | `improvement_tip`은 별도 필드로 이미 저장됨. `content`에 팁 텍스트가 포함될 뿐 |
| Insight 페이지 | ✅ 무영향 | `improvement_tip` 필드 자체를 참조하지 않음 |
| 빈 answer_draft | ✅ 안전 | 기본값 "현재 생성된 답변이 없습니다..." 뒤에 팁이 붙음 |
| fallback 시그니처 | ✅ 무영향 | `improvement_tip` 매개변수 유지. 호출부 변경 없음 |

---

## 예외 처리 및 방어 로직
- `improvement_tip` 값이 None/빈 문자열인 경우: 붙이지 않음 (`if` 체크)
- 정상 답변/fallback 답변 모두 동일하게 처리
- 오류 상태에서도 `improvement_tip` 있으면 포함
- fallback의 `학습 팁:` 행은 제거되어 중복 발생 불가

---

## 체크리스트
- [x] `app.py`에 `load_dotenv()` 추가
- [x] `build_fallback_answer()`에서 `학습 팁:` 행 제거 (core/prompts.py)
- [x] `finalize_response_node` 수정 (정상 + 오류 경로) (core/graph.py)
- [x] `py_compile` 검증 (app.py, prompts.py, graph.py)
- [x] 로컬 Streamlit 테스트 (LLM 경로 표시 확인)
- [x] fallback 경로에서 팁 중복 없는지 확인

---

## 구현 기록

| 날짜 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-13 | `app.py` load_dotenv 추가 | ✅ Done | 이전 커밋에서 적용 완료 |
| 2026-04-13 | `build_fallback_answer` 학습 팁 행 제거 | ✅ Done | 두 return 경로 모두 제거 |
| 2026-04-13 | `finalize_response_node` 수정 | ✅ Done | 정상/오류 경로 팁 붙이기, 이전 커밋에서 적용 완료 |