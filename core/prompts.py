# core/prompts.py
# 역할: 프롬프트 템플릿 모음 (수정 편의를 위해 한 파일에 집중 관리)
# - 6관점 템플릿: 개념 / 원리 / 비유(관심사 주입) / 관계 / 활용 / 주의사항
# - 그래프용 프롬프트 조합 함수 제공
# - LLM 미호출 환경에서도 확인 가능한 fallback 답변 텍스트 생성

from __future__ import annotations

from typing import Any, Optional


PERSPECTIVE_TITLES: dict[str, str] = {
    "concept": "개념 중심 설명",
    "principle": "원리 중심 설명",
    "analogy": "비유 중심 설명",
    "relation": "관계 중심 설명",
    "usage": "활용 중심 설명",
    "caution": "주의사항 중심 설명",
}


def get_perspective_prompt(
    perspective: str,
    question: str,
    context: str,
    subject: str,
    interests: Optional[str] = None,
    bloom_label: Optional[str] = None,
    improvement_tip: Optional[str] = None,
    chat_history: Optional[list[dict[str, Any]]] = None,
) -> str:
    """관점별 프롬프트 문자열을 생성합니다."""
    perspective_title = PERSPECTIVE_TITLES.get(perspective, "학습 설명")
    chat_history_lines: list[str] = []
    for item in chat_history or []:
        role = item.get("role", "unknown")
        content = str(item.get("content", "")).strip()
        if content:
            chat_history_lines.append(f"- {role}: {content}")

    interest_line = (
        f"사용자 관심사: {interests}"
        if perspective == "analogy" and interests
        else "사용자 관심사: 없음"
    )

    prompt = f"""
당신은 NCS 자격증 학습을 돕는 한국어 튜터입니다.
답변 관점: {perspective_title}
과목: {subject}
Bloom 수준: {bloom_label or "미확인"}
질문: {question}
{interest_line}

대화 기록:
{chr(10).join(chat_history_lines) if chat_history_lines else "- 없음"}

검색 컨텍스트:
{context or "- 검색 컨텍스트 없음"}

답변 작성 규칙:
1. 한국어로 답변합니다.
2. 검색 컨텍스트가 있으면 그 범위를 우선 사용합니다.
3. 검색 근거가 부족하면 추정이라고 밝히고 단정하지 않습니다.
4. 관점에 맞게 설명 스타일을 조절합니다.
5. 마지막에는 학습 포인트를 한 줄로 정리합니다.
6. improvement_tip이 있으면 자연스럽게 반영합니다.

질문 개선 팁:
{improvement_tip or "- 없음"}
""".strip()
    return prompt


def build_fallback_answer(
    question: str,
    perspective: str,
    subject: str,
    retrieval_context: str,
    improvement_tip: Optional[str] = None,
) -> str:
    """LLM 호출이 어려울 때 사용할 보수적 fallback 답변을 생성합니다."""
    preview = retrieval_context.strip().replace("\n", " ")
    preview = preview[:500] + ("..." if len(preview) > 500 else "")

    if preview:
        return (
            f"[{subject} | {PERSPECTIVE_TITLES.get(perspective, '학습 설명')}]\n"
            f"질문: {question}\n\n"
            "검색된 학습 자료를 바탕으로 보면 다음 내용을 우선 참고할 수 있습니다.\n"
            f"{preview}\n\n"
            f"학습 팁: {improvement_tip or '핵심 용어와 조건을 함께 질문하면 더 정확한 답을 받을 수 있습니다.'}"
        )

    return (
        f"[{subject} | {PERSPECTIVE_TITLES.get(perspective, '학습 설명')}]\n"
        f"질문: {question}\n\n"
        "현재 검색된 학습 컨텍스트가 없어 일반적인 설명만 제공할 수 있습니다. "
        "정확도를 높이려면 과목을 다시 확인하고, 핵심 키워드나 상황을 더 구체적으로 적어주세요.\n\n"
        f"학습 팁: {improvement_tip or '예: 어떤 상황에서 쓰는지, 무엇과 비교할지까지 함께 적어보세요.'}"
    )
