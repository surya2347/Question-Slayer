# core/prompts.py
# 역할: 프롬프트 템플릿 모음 (수정 편의를 위해 한 파일에 집중 관리)
# - 6관점 템플릿: 개념 / 원리 / 비유(관심사 주입) / 관계 / 활용 / 주의사항
# - Bloom 스코어링 프롬프트: 질문을 분석해 JSON 형태로 인지 단계 반환
# - 질문 교정 가이드 프롬프트: 현재 Bloom 수준 → 상위 수준 질문 유도 피드백
# - 용어 설명 프롬프트: 특정 용어에 대한 간결한 정의 반환

from __future__ import annotations

from typing import Any, Optional


# ============================================================================
# 관점 제목 매핑 (graph.py / fallback 에서 사용)
# ============================================================================

PERSPECTIVE_TITLES: dict[str, str] = {
    "concept":   "개념 중심 설명",
    "principle": "원리 중심 설명",
    "analogy":   "비유 중심 설명",
    "relation":  "관계 중심 설명",
    "usage":     "활용 중심 설명",
    "caution":   "주의사항 중심 설명",
}



# ============================================================================
# 1. 개념 (Concept)
# ============================================================================

PROMPT_CONCEPT = """\
당신은 {subject} 과목의 전문 튜터입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 위 개념/용어의 정확한 정의를 제시하세요 (한 문장).
2. 이 개념이 왜 필요한지, 어떤 배경에서 생겨났는지 설명하세요.
3. 개념을 이해하기 위한 핵심 용어 3~4가지를 나열하고 간단히 설명하세요.
4. 이해를 돕기 위한 간단한 예시 1~2개를 드세요.

【답변 형식】
**정의**: [한 문장 정의]

**배경 및 필요성**: [2~3문장]

**핵심 용어**:
- 용어1: [설명]
- 용어2: [설명]
- 용어3: [설명]
- 용어4: [설명]

**예시**: [간단한 예시 1~2개]
"""

# ============================================================================
# 2. 원리 (Principle)
# ============================================================================

PROMPT_PRINCIPLE = """\
당신은 {subject} 과목의 기술 전문가입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념이 어떤 원리로 작동하는지 3~4단계의 프로세스로 설명하세요.
2. 각 단계 간의 인과관계를 명확히 하세요.
3. 텍스트 흐름도로 표현하세요.
4. 이 원리가 왜 이렇게 설계되었는지 이유를 설명하세요 (1~2문장).

【답변 형식】
**작동 원리 개요**: [한 문장 요약]

**단계별 프로세스**:
1. 단계1: [설명 및 결과]
2. 단계2: [설명 및 결과]
3. 단계3: [설명 및 결과]
4. 단계4: [설명 및 결과]

**흐름도**:
[입력] → [처리1] → [처리2] → [처리3] → [출력]

**설계 의도**: [왜 이렇게 설계되었나?]
"""

# ============================================================================
# 3. 비유 (Analogy) — 사용자 관심사 주입
# ============================================================================

PROMPT_ANALOGY = """\
당신은 {subject} 과목의 친절한 튜터입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【사용자 배경】
관심사: {interests}

【지시사항】
1. 사용자의 관심사인 "{interests}"와 이 개념의 유사한 측면을 찾으세요.
2. 이 개념을 "{interests}"의 예시로 비유해서 설명하세요 (2~3문장).
3. 비유에서의 유사점 2~3가지를 명시하세요.
4. 비유의 한계(다른 점)가 있다면 언급하세요.
5. 개념의 정확한 정의로 마무리하세요.

【답변 형식】
**"{interests}"와의 비유**:
[비유 설명 2~3문장]

**유사점**:
1. 유사점1: [설명]
2. 유사점2: [설명]
3. 유사점3: [설명]

**비유의 한계**: [다른 점 언급]

**정확한 정의**: [개념의 정확한 정의]
"""

# ============================================================================
# 4. 관계 (Relation)
# ============================================================================

PROMPT_RELATION = """\
당신은 {subject} 과목의 체계적인 전문가입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념을 이해하기 위해 꼭 알아야 하는 선행 개념 2~3개를 나열하세요.
2. 이 개념과 자주 혼동되는 유사 개념 1~2개를 들어 차이를 표로 정리하세요.
3. 이 개념 다음에 학습해야 할 후속 개념 2~3개를 나열하세요.
4. 전체 개념 간 관계를 간단한 흐름도로 표현하세요.

【답변 형식】
**선행 개념** (꼭 알아야 함):
1. 선행1: [간단 설명]
2. 선행2: [간단 설명]
3. 선행3: [간단 설명]

**유사 개념과의 차이**:
| 특성 | 현재 개념 | 유사 개념1 | 유사 개념2 |
|-----|---------|---------|---------|
| [특성1] | ... | ... | ... |
| [특성2] | ... | ... | ... |
| [특성3] | ... | ... | ... |

**후속 개념** (다음에 배울 것):
1. 후속1: [간단 설명]
2. 후속2: [간단 설명]
3. 후속3: [간단 설명]

**개념 흐름도**:
[선행1] → [선행2] → 【현재 개념】 → [후속1] → [후속2]
"""

# ============================================================================
# 5. 활용 (Usage)
# ============================================================================

PROMPT_USAGE = """\
당신은 {subject} 과목의 실무 전문가입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념을 실무/실제 상황에서 어디에 활용하는지 설명하세요.
2. 구체적인 사용 사례 3~4가지를 시나리오 형식으로 제시하세요.
3. 각 사례에 대해 어떻게 적용하는지 단계별(Step 1, 2, 3...)로 설명하세요.
4. 각 사례의 기대 결과/효과를 명시하세요.
5. 사용할 때 주의할 점 2~3가지를 덧붙이세요.

【답변 형식】
**활용 분야**: [어디에 사용되나?]

**사용 사례1: [상황]**
- 시나리오: [설명]
- Step 1: ...
- Step 2: ...
- Step 3: ...
- 기대 효과: [결과]

**사용 사례2: [상황]**
[동일 형식]

**사용 사례3: [상황]**
[동일 형식]

**주의사항**:
1. [주의1]
2. [주의2]
3. [주의3]
"""

# ============================================================================
# 6. 주의사항 (Caution)
# ============================================================================

PROMPT_CAUTION = """\
당신은 {subject} 과목의 철저한 품질 관리자입니다.

【사용자 질문】
{question}

【검색 결과(RAG)】
{context}

【지시사항】
1. 이 개념을 사용할 때 초보자들이 자주 하는 실수 3~5가지를 나열하세요.
2. 각 실수에 대해 왜 그런 실수가 나타나는지 원인을 설명하세요.
3. 각 실수를 예방하거나 바로잡는 방법을 제시하세요.
4. 잘못된 예(❌)와 올바른 예(✅)로 대조해서 보여주세요.
5. 이 개념의 한계나 예외 상황이 있다면 언급하세요.

【답변 형식】
**주의사항1: [실수 제목]**
- 증상: [어떤 문제가 나타나나?]
- 원인: [왜 이런 실수가 나타나나?]
- 예방법: [어떻게 예방하나?]
- ❌ 잘못된 예: [코드/설명]
- ✅ 올바른 예: [코드/설명]

**주의사항2: [실수 제목]**
[동일 형식]

**주의사항3: [실수 제목]**
[동일 형식]

**한계 및 예외**: [한계 설명]
"""

# ============================================================================
# 7. 관심사 선택 (Interest Selector) — 비유 관점 전처리용
# ============================================================================

PROMPT_INTEREST_SELECTOR = """\
사용자의 관심사 목록 중 현재 질문과 의미적으로 가장 잘 어울리는 관심사 1개를 선택하세요.

【사용자 질문】
{question}

【관심사 목록】
{interests_list}

【선택 기준】
- 질문의 핵심 개념과 비유로 연결 가능한 관심사를 선택하세요.
- 관심사와 질문 개념 사이의 공통점(구조, 역할, 흐름 등)이 있어야 합니다.
- 목록에 없는 관심사는 절대 선택하지 마세요.

【지시사항】
반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 포함 금지).

【필수 JSON 형식】
{{
    "selected": "[목록에서 선택한 관심사를 그대로 입력]",
    "reason": "[이 관심사를 선택한 이유 1문장]"
}}
"""


# ============================================================================
# 8. Bloom 스코어링 (Bloom Scoring) — LLM 2차 정교화용
# ============================================================================

PROMPT_BLOOM_SCORING = """\
당신은 Bloom의 교육목표 분류학(1956) 전문가입니다.
사용자의 질문이 Bloom 6단계 중 어디에 해당하는지 분석하세요.

【분석할 질문】
{question}

【Bloom 분류학 6단계 기준】
1. 지식(Knowledge)   : 사실·용어·개념을 기억/인식하는 능력
   - 키워드: 무엇, 정의, 나열, 뜻, 언제, 누가
2. 이해(Comprehension): 정보를 이해하고 요약하는 능력
   - 키워드: 설명, 왜, 어떻게 작동, 의미, 해석
3. 응용(Application) : 지식을 새 상황에 적용하는 능력
   - 키워드: 활용, 적용, 사용하면, 실무에서, 만들면
4. 분석(Analysis)    : 정보를 분해해 관계·원인을 파악하는 능력
   - 키워드: 차이점, 비교, 구조, 분류, 원인
5. 종합(Synthesis)   : 요소들을 결합해 새것을 창출하는 능력
   - 키워드: 결합, 설계, 새로운, 통합, 조합
6. 평가(Evaluation)  : 기준에 따라 판단하는 능력
   - 키워드: 평가, 더 나은, 장단점, 판단, 추천

【지시사항】
- 위 질문이 Bloom 6단계 중 어디에 해당하는지 분석하세요.
- 반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 포함 금지).

【필수 JSON 형식】
{{
    "level": [1~6 정수],
    "name_ko": "[지식|이해|응용|분석|종합|평가]",
    "evidence": "[이 질문이 해당 단계인 이유 1~2문장]",
    "keywords_found": ["[질문에서 발견된 키워드]"],
    "confidence": [0.0~1.0 소수]
}}
"""


# ============================================================================
# 헬퍼 함수
# ============================================================================

def format_interests_for_prompt(interests: list) -> str:
    """관심사 목록을 프롬프트 주입용 번호 목록 문자열로 변환합니다.

    Args:
        interests: 관심사 문자열 목록 (최소 3개 권장)

    Returns:
        번호 매긴 줄바꿈 문자열 (예: "1. 축구\n2. 요리\n3. 게임")
    """
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(interests))


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
    """선택된 관점에 맞는 프롬프트 템플릿에 변수를 주입해 반환합니다.

    Args:
        perspective: 관점 키 (concept | principle | analogy | relation | usage | caution)
        question: 사용자 질문
        context: RAG 검색 결과
        subject: 학습 과목
        interests: 사용자 관심사 (analogy 관점에서만 사용)
        bloom_label: Bloom 단계 레이블 (graph.py에서 주입, 선택적)
        improvement_tip: 질문 개선 팁 (graph.py에서 주입, 선택적)
        chat_history: 대화 기록 (graph.py에서 주입, 선택적)

    Returns:
        변수가 주입된 프롬프트 문자열

    Raises:
        ValueError: 유효하지 않은 perspective
    """
    templates = {
        "concept": PROMPT_CONCEPT,
        "principle": PROMPT_PRINCIPLE,
        "analogy": PROMPT_ANALOGY,
        "relation": PROMPT_RELATION,
        "usage": PROMPT_USAGE,
        "caution": PROMPT_CAUTION,
    }

    key = perspective.lower()
    if key not in templates:
        raise ValueError(
            f"유효하지 않은 관점: '{perspective}'. "
            f"사용 가능한 관점: {', '.join(templates)}"
        )

    if key == "analogy":
        core_prompt = templates[key].format(
            question=question,
            context=context,
            subject=subject,
            interests=interests or "일상생활",
        )
    else:
        core_prompt = templates[key].format(
            question=question,
            context=context,
            subject=subject,
        )

    # graph.py에서 추가 컨텍스트가 주입된 경우 부록 형태로 추가
    extras: list[str] = []
    if bloom_label:
        extras.append(f"【Bloom 수준】\n{bloom_label}")
    if improvement_tip:
        extras.append(f"【질문 개선 팁】\n{improvement_tip}")
    if chat_history:
        lines = [
            f"- {m.get('role', '')}: {str(m.get('content', '')).strip()}"
            for m in chat_history
            if str(m.get("content", "")).strip()
        ]
        if lines:
            extras.append("【대화 기록】\n" + "\n".join(lines))

    if extras:
        return core_prompt + "\n\n" + "\n\n".join(extras)
    return core_prompt


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
            f"{preview}"
        )

    return (
        f"[{subject} | {PERSPECTIVE_TITLES.get(perspective, '학습 설명')}]\n"
        f"질문: {question}\n\n"
        "현재 검색된 학습 컨텍스트가 없어 일반적인 설명만 제공할 수 있습니다. "
        "정확도를 높이려면 과목을 다시 확인하고, 핵심 키워드나 상황을 더 구체적으로 적어주세요."
    )


def validate_templates() -> dict:
    """모든 프롬프트 템플릿의 변수 주입 가능 여부를 검증합니다."""
    sample = {
        "question": "테스트 질문",
        "context": "테스트 컨텍스트",
        "subject": "테스트 과목",
        "interests": "테스트 관심사",
    }
    results = {}
    for key in ("concept", "principle", "analogy", "relation", "usage", "caution"):
        try:
            get_perspective_prompt(key, **{k: v for k, v in sample.items() if k != "interests"},
                                   interests=sample["interests"])
            results[key] = "OK"
        except Exception as e:
            results[key] = f"FAIL — {e}"
    return results


# ============================================================================
# 질문 재구성 프롬프트
# ============================================================================

PROMPT_RESTRUCTURE_QUESTION = """\
당신은 사용자의 질문을 정확한 기술 용어와 개념으로 재해석하는 전문가입니다.

【사용자 질문】
{normalized_question}

【이전 대화 기록】
{chat_history}

【지시사항】
1. 사용자 질문의 핵심 의도를 파악하세요.
2. 질문에 담긴 개념/기술 용어를 명확히 하세요.
3. 이전 대화 기록이 있다면 맥락을 참고해 질문을 재정의하세요.
4. 한 문장으로 재해석하세요: "~~~가 궁금하신 거죠?"
5. 형식: "~~~가 궁금하신 거죠?" (자연스러운 한국어 표현)
6. 원본 질문이 이미 명확하면 원본 그대로 사용.

【응답 형식】
한 줄만 반환. 추가 설명 금지. 100자 내로 작성.
예) "데이터베이스의 정규화 개념 중 BCNF가 궁금하신 거죠?"
"""


# ============================================================================
# 직접 실행 시 검증
# ============================================================================

if __name__ == "__main__":
    # 6관점 템플릿 검증
    results = validate_templates()
    print("=== 6관점 프롬프트 템플릿 검증 결과 ===")
    for perspective, status in results.items():
        mark = "✅" if status == "OK" else "❌"
        print(f"  {mark} {perspective}: {status}")

    # Bloom 스코어링 템플릿 검증
    print("\n=== Bloom 스코어링 프롬프트 검증 ===")
    try:
        rendered = PROMPT_BLOOM_SCORING.format(question="Python 변수란 무엇인가요?")
        # {question} 변수가 치환되었는지만 확인 (JSON 예시의 { } 는 정상)
        assert "{question}" not in rendered, "변수 주입 실패"
        print("  ✅ PROMPT_BLOOM_SCORING: OK")
    except Exception as e:
        print(f"  ❌ PROMPT_BLOOM_SCORING: FAIL — {e}")
