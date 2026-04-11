# core/utils.py
# 역할: 공통 유틸리티 함수 모음
# - 관심사 JSON 불러오기 / 저장 (data/user_profiles/)
# - Bloom 인지 단계 레이블 매핑 (1~6 → 지식/이해/응용/분석/종합/평가)
# - 질문 이력 JSON 저장 (Insight 시각화용 데이터 축적)
# - 공통 예외 처리 헬퍼 및 Fallback 메시지 반환

from __future__ import annotations


# ============================================================================
# Bloom 분류학 상수 (1956년 원년 6단계)
# ============================================================================

BLOOM_LEVELS: dict[int, dict] = {
    1: {
        "name_ko": "지식",
        "definition": "사실, 용어, 기본 개념을 기억하는 능력",
    },
    2: {
        "name_ko": "이해",
        "definition": "사실과 개념을 이해하고 요약·정리하는 능력",
    },
    3: {
        "name_ko": "응용",
        "definition": "습득한 지식으로 새로운 상황에서 문제를 해결하는 능력",
    },
    4: {
        "name_ko": "분석",
        "definition": "정보를 나눠 관계·동기·원인을 파악하는 능력",
    },
    5: {
        "name_ko": "종합",
        "definition": "여러 요소를 결합해 새로운 전체를 창출하는 능력",
    },
    6: {
        "name_ko": "평가",
        "definition": "기준·표준에 따라 정보에 대해 판단을 내리는 능력",
    },
}

# 단계별 트리거 키워드 (1차 판별용)
BLOOM_KEYWORDS: dict[int, list[str]] = {
    1: ["무엇", "뭐", "누가", "언제", "어디서", "란?", "이란?", "정의", "뜻", "나열", "몇 개", "몇 년"],
    2: ["어떻게 작동", "왜", "설명", "의미", "해석", "어떤", "어떻게 되나", "이해"],
    3: ["활용", "적용", "어떻게 사용", "사용하면", "실무에서", "써보면", "만들면", "구현하면"],
    4: ["차이점", "비교", "왜 이렇게", "구조", "분류", "나누면", "관계", "원인"],
    5: ["결합", "설계", "새로운", "통합", "만들어보면", "조합", "창안", "개발한다면"],
    6: ["평가", "더 나은", "장단점", "판단", "최선", "추천", "어느 것", "옳은가"],
}


# ============================================================================
# Bloom 레이블 매핑
# ============================================================================

def level_to_label(level: int) -> str:
    """Bloom 단계 숫자를 한국어 레이블로 변환합니다.

    Args:
        level: Bloom 단계 (1~6)

    Returns:
        한국어 레이블 ("지식", "이해", ...)

    Raises:
        ValueError: 1~6 범위를 벗어난 경우
    """
    if level not in BLOOM_LEVELS:
        raise ValueError(f"유효하지 않은 Bloom 단계: {level} (1~6 사이여야 합니다)")
    return BLOOM_LEVELS[level]["name_ko"]


def label_to_level(label: str) -> int:
    """한국어 레이블을 Bloom 단계 숫자로 변환합니다.

    Args:
        label: 한국어 레이블 ("지식", "이해", ...)

    Returns:
        Bloom 단계 숫자 (1~6)

    Raises:
        ValueError: 유효하지 않은 레이블인 경우
    """
    for level, info in BLOOM_LEVELS.items():
        if info["name_ko"] == label:
            return level
    valid = [v["name_ko"] for v in BLOOM_LEVELS.values()]
    raise ValueError(f"유효하지 않은 레이블: '{label}'. 사용 가능: {valid}")


# ============================================================================
# Bloom 1차 키워드 판별
# ============================================================================

def score_bloom_by_keyword(question: str) -> dict:
    """키워드 매칭으로 질문의 Bloom 단계를 1차 판별합니다.

    신뢰도(confidence) 계산:
        매칭 키워드 1개 → 0.6
        매칭 키워드 2개 → 0.75
        매칭 키워드 3개 이상 → 0.9

    복수 단계에 키워드가 매칭될 경우 가장 높은 단계를 선택합니다.
    매칭이 없을 경우 confidence=0.0 을 반환하며,
    호출 측(graph.py)에서 LLM 2차 정교화로 fallback해야 합니다.

    Args:
        question: 사용자 질문 문자열

    Returns:
        {level, name_ko, name_en, keywords_found, confidence, method} dict
    """
    _CONFIDENCE_MAP = {1: 0.6, 2: 0.75}  # 3개 이상은 아래에서 0.9 처리

    # 단계별 매칭 키워드 수집
    matches: dict[int, list[str]] = {}
    for level, keywords in BLOOM_KEYWORDS.items():
        found = [kw for kw in keywords if kw in question]
        if found:
            matches[level] = found

    # 매칭 없음 → LLM fallback 신호
    if not matches:
        return {
            "level": 1,
            "name_ko": BLOOM_LEVELS[1]["name_ko"],
            "keywords_found": [],
            "confidence": 0.0,
            "method": "keyword",
        }

    # 복수 단계 매칭 시 가장 높은 단계 선택
    best_level = max(matches.keys())
    found_kws = matches[best_level]
    count = len(found_kws)
    confidence = _CONFIDENCE_MAP.get(count, 0.9)

    return {
        "level": best_level,
        "name_ko": BLOOM_LEVELS[best_level]["name_ko"],
        "keywords_found": found_kws,
        "confidence": confidence,
        "method": "keyword",
    }


# ============================================================================
# 비유 관심사 선택
# ============================================================================

def pick_best_interest(question: str, interests: list[str]) -> str:
    """질문과 가장 관련 있는 관심사 하나를 반환합니다.

    질문 문자열에 직접 포함된 관심사를 우선 선택하고,
    없으면 첫 번째 관심사를 반환합니다.
    관심사 목록이 비어있으면 "일상생활"을 반환합니다.

    Args:
        question: 사용자 질문 문자열
        interests: 사용자 관심사 목록

    Returns:
        선택된 관심사 문자열 (단일 항목)
    """
    if not interests:
        return "일상생활"

    # 질문에 직접 언급된 관심사 우선 선택
    for interest in interests:
        if interest in question:
            return interest

    # 없으면 목록의 첫 번째 항목 반환
    return interests[0]


# ============================================================================
# 직접 실행 시 검증
# ============================================================================

if __name__ == "__main__":
    # 레이블 매핑 검증
    print("=== 레이블 매핑 검증 ===")
    for i in range(1, 7):
        label = level_to_label(i)
        back = label_to_level(label)
        mark = "✅" if back == i else "❌"
        print(f"  {mark} level_to_label({i}) = '{label}' → label_to_level('{label}') = {back}")

    # 키워드 판별 검증
    print("\n=== Bloom 키워드 판별 테스트 ===")
    samples = [
        ("Python 변수란 무엇인가요?",               1),
        ("왜 포인터를 사용하나요?",                  2),
        ("이 개념을 실무에 어떻게 활용하나요?",       3),
        ("TCP와 UDP의 차이점은?",                   4),
        ("REST API와 GraphQL을 결합해 설계한다면?",  5),
        ("Python과 Java 중 어느 것이 더 나은가요?",  6),
        ("완전히 뜬금없는 질문입니다",               None),
    ]

    for q, expected in samples:
        result = score_bloom_by_keyword(q)
        if expected is None:
            mark = "✅" if result["confidence"] == 0.0 else "❌"
        else:
            mark = "✅" if result["level"] == expected else "❌"
        print(f"  {mark} [{result['name_ko']} Lv{result['level']}] conf={result['confidence']} | {q}")
        if result["keywords_found"]:
            print(f"       → 매칭 키워드: {result['keywords_found']}")
