# Improvement Tip 최종 답변 붙이기 계획

## 개요 및 목표
최종 LLM 생성 답변 뒤에 improvement_tip을 텍스트로 붙여서 화면에 표시.
사용자가 다음 질문을 더 잘 할 수 있도록 가이드 제시.

## 모듈별 구현 명세

### 1. `finalize_response_node()` 수정 (core/graph.py)
**위치**: line 848~880 근처

**변경 내용**:
- `answer_final` 값 구성 시 `improvement_tip` 붙이기
- 포맷: `answer + "\n\n---\n💡 다음 번 팁:\n" + improvement_tip`
- 오류/빈 상태에서도 동일 적용

**코드 로직**:
```
if improvement_tip 존재:
    answer_final += "\n\n---\n💡 다음 번 팁:\n" + improvement_tip
```

## 예외 처리 및 방어 로직
- `improvement_tip` 값이 None/빈 문자열인 경우: 붙이지 않음 (if 체크)
- 정상 답변/fallback 답변 모두 동일하게 처리
- 오류 상태에서도 improvement_tip 있으면 포함

## 체크리스트
- [ ] `finalize_response_node` 수정
- [ ] 로컬 콘솔 테스트 (print 확인)
- [ ] Streamlit Chat 페이지에서 표시 확인
- [ ] 오류 상황에서 작동 확인

## 구현 기록
- 상태: 미시작
