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
    # 과목 탐지 검증
    print("=== 과목 탐지 테스트 ===")
    samples = [
        ("TCP와 UDP의 차이점은 무엇인가요?",        "네트워크관리사"),
        ("머신러닝 알고리즘을 설명해주세요",          "빅데이터분석기사"),
        ("엑셀 VLOOKUP 함수 사용법이 뭔가요?",      "컴퓨터활용능력"),
        ("암호화와 복호화의 원리가 뭔가요?",          "정보보안기사"),
        ("완전히 관계없는 질문입니다",               "일반"),
    ]
    for q, expected in samples:
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
        print(f"  🧹 테스트 파일 정리 완료")
