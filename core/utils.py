# core/utils.py
# 역할: 공통 유틸리티 함수 모음
# - 관심사 JSON 불러오기 / 저장 (data/user_profiles/)
# - Bloom 인지 단계 레이블 매핑 (1~6 → 지식/이해/응용/분석/종합/평가)
# - 질문 이력 JSON 저장 (Insight 시각화용 데이터 축적)
# - 공통 예외 처리 헬퍼 및 Fallback 메시지 반환

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# 사용자 프로필 저장 경로
_PROFILES_DIR = Path(__file__).parent.parent / "data" / "user_profiles"


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
        {level, name_ko, keywords_found, confidence, method} dict
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
# 과목 탐지 (Subject Router)
# ============================================================================

# 과목별 트리거 키워드
# 아직 제대로 NCS 과목에 제대로 적용되지 않음
# 임시 정도로 정보처리기사, 빅데이터분석기사, 정보보안기사, 네트워크관리사로 넣어놓음.
SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "정보처리기사": ["정보처리", "자료구조", "운영체제", "데이터베이스", "소프트웨어공학", "네트워크", "보안", "정렬 알고리즘", "탐색 알고리즘"],
    "빅데이터분석기사": ["빅데이터", "머신러닝", "딥러닝", "데이터분석", "통계", "R언어", "파이썬 분석", "시각화"],
    "정보보안기사": ["정보보안", "암호화", "침해사고", "취약점", "방화벽", "해킹", "보안관제"],
    "네트워크관리사": ["네트워크", "TCP", "UDP", "IP", "라우터", "스위치", "OSI", "VLAN"],
    "컴퓨터활용능력": ["엑셀", "스프레드시트", "피벗", "VLOOKUP", "함수", "차트", "데이터베이스 함수"],
}


def detect_subject(question: str) -> dict:
    """질문에서 NCS 과목을 키워드 기반으로 탐지합니다.

    복수 과목에 키워드가 매칭될 경우 매칭 수가 가장 많은 과목을 선택합니다.
    매칭이 없으면 subject="일반", confidence=0.0 을 반환합니다.

    Args:
        question: 사용자 질문 문자열

    Returns:
        {subject, keywords_found, confidence} dict
    """
    matches: dict[str, list[str]] = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        found = [kw for kw in keywords if kw in question]
        if found:
            matches[subject] = found

    if not matches:
        return {"subject": "일반", "keywords_found": [], "confidence": 0.0}

    # 매칭 수가 같을 경우 키워드 총 길이(구체성)가 긴 쪽 선택
    best = max(matches, key=lambda s: (len(matches[s]), sum(len(k) for k in matches[s])))
    count = len(matches[best])
    confidence = {1: 0.6, 2: 0.8}.get(count, 0.95)

    return {
        "subject": best,
        "keywords_found": matches[best],
        "confidence": confidence,
    }


# ============================================================================
# 관심사 저장 구조 (user_profiles JSON)
# ============================================================================

def save_interests(user_id: str, interests: list[str]) -> None:
    """사용자 관심사를 JSON 파일로 저장합니다.

    저장 경로: data/user_profiles/{user_id}.json

    Args:
        user_id: 사용자 식별자 (예: "user_001")
        interests: 관심사 목록 (예: ["게임", "음악"])
    """
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = _PROFILES_DIR / f"{user_id}.json"

    # 기존 프로필 로드 (없으면 빈 dict)
    profile: dict = {}
    if profile_path.exists():
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)

    profile["interests"] = interests

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def load_interests(user_id: str) -> list[str]:
    """저장된 사용자 관심사를 불러옵니다.

    파일이 없거나 interests 키가 없으면 빈 리스트를 반환합니다.

    Args:
        user_id: 사용자 식별자

    Returns:
        관심사 목록 (없으면 [])
    """
    profile_path = _PROFILES_DIR / f"{user_id}.json"

    if not profile_path.exists():
        return []

    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    return profile.get("interests", [])


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

    # 과목 탐지 검증
    print("\n=== 과목 탐지 테스트 ===")
    subject_samples = [
        ("TCP와 UDP의 차이점은 무엇인가요?",        "네트워크관리사"),
        ("머신러닝 알고리즘을 설명해주세요",          "빅데이터분석기사"),
        ("엑셀 VLOOKUP 함수 사용법이 뭔가요?",      "컴퓨터활용능력"),
        ("암호화와 복호화의 원리가 뭔가요?",          "정보보안기사"),
        ("완전히 관계없는 질문입니다",               "일반"),
    ]
    for q, expected in subject_samples:
        result = detect_subject(q)
        mark = "✅" if result["subject"] == expected else "❌"
        print(f"  {mark} [{result['subject']}] conf={result['confidence']} | {q}")
        if result["keywords_found"]:
            print(f"       → 매칭 키워드: {result['keywords_found']}")

    # 관심사 저장/불러오기 검증
    print("\n=== 관심사 저장/불러오기 테스트 ===")
    _test_id = "_test_user"
    _test_interests = ["게임", "음악", "영화"]

    save_interests(_test_id, _test_interests)
    loaded = load_interests(_test_id)
    mark = "✅" if loaded == _test_interests else "❌"
    print(f"  {mark} 저장: {_test_interests}")
    print(f"  {mark} 불러오기: {loaded}")

    # 없는 유저 테스트
    empty = load_interests("_nonexistent_user")
    mark = "✅" if empty == [] else "❌"
    print(f"  {mark} 없는 유저 → {empty}")

    # 테스트 파일 정리
    test_path = _PROFILES_DIR / f"{_test_id}.json"
    if test_path.exists():
        os.remove(test_path)
        print("  🧹 테스트 파일 정리 완료")
