"""콘솔 기반 LangGraph 검증 및 수동 실행 스크립트."""

from __future__ import annotations

import argparse
import json
from typing import Any

from core.graph import (
    SUBJECT_COLLECTION_MAP,
    analyze_question_node,
    build_mock_payload,
    build_prompt_input_node,
    finalize_response_node,
    generate_answer_node,
    init_request_node,
    prerequisite_check_node,
    resolve_collection_node,
    retrieve_context_node,
    route_perspective_node,
    run_question_graph,
)


def _print_case_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"[TEST] {title}")
    print("=" * 72)


def _print_key_fields(state: dict[str, Any]) -> None:
    print(f"- status: {state.get('status')}")
    print(f"- resolved_collection_name: {state.get('resolved_collection_name')}")
    print(f"- bloom_level: {state.get('bloom_level')}")
    print(f"- question_intent: {state.get('question_intent')}")
    print(f"- perspective: {state.get('perspective')}")
    print(f"- retrieval_hit: {state.get('retrieval_hit')}")
    print(f"- citations_count: {len(state.get('citations', []))}")
    answer = state.get("answer") or state.get("answer_draft") or ""
    print(f"- answer_preview: {str(answer)[:120]}")


def _print_node_snapshot(node_name: str, state: dict[str, Any]) -> None:
    print(f"\n[{node_name}]")
    for key in [
        "status",
        "normalized_question",
        "question_intent",
        "bloom_level",
        "bloom_label",
        "bloom_confidence",
        "resolved_collection_name",
        "retrieval_hit",
        "perspective",
        "routing_reason",
        "error_code",
        "error_message",
    ]:
        if key in state:
            print(f"- {key}: {state.get(key)}")

    prompt_input = state.get("prompt_input")
    if isinstance(prompt_input, dict):
        print(f"- prompt_subject: {prompt_input.get('subject_label')}")
        print(f"- prompt_context_length: {len(prompt_input.get('retrieval_context', ''))}")

    trace = state.get("debug_trace", [])
    if trace:
        print(f"- last_trace: {trace[-1]}")


def _node_pipeline(payload: dict[str, Any], verbose: bool = False) -> dict[str, Any]:
    state: dict[str, Any] = payload.copy()
    node_sequence = [
        ("init_request_node", init_request_node),
        ("prerequisite_check_node", prerequisite_check_node),
        ("analyze_question_node", analyze_question_node),
        ("resolve_collection_node", resolve_collection_node),
        ("retrieve_context_node", retrieve_context_node),
        ("route_perspective_node", route_perspective_node),
        ("build_prompt_input_node", build_prompt_input_node),
        ("generate_answer_node", generate_answer_node),
        ("finalize_response_node", finalize_response_node),
    ]

    for node_name, node_fn in node_sequence:
        update = node_fn(state)
        if "debug_trace" in update:
            state["debug_trace"] = list(state.get("debug_trace", [])) + list(
                update["debug_trace"]
            )
        state.update({key: value for key, value in update.items() if key != "debug_trace"})
        if verbose:
            _print_node_snapshot(node_name, state)

    return state


def test_1_normal_question_auto() -> None:
    _print_case_header("1) 정상 질문 + 정상 과목 + auto 관점")
    payload = build_mock_payload(
        question="운영체제의 역할은 무엇인가요?",
        subject_id="requirements_analysis",
        selected_perspective="auto",
        interests=["게임"],
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "ok"
    assert state.get("bloom_level") is not None
    assert state.get("perspective") in {
        "concept",
        "principle",
        "analogy",
        "relation",
        "usage",
        "caution",
    }


def test_2_user_selected_perspective() -> None:
    _print_case_header("2) 사용자 관점 직접 선택(override 확인)")
    payload = build_mock_payload(
        question="운영체제를 실무에서 어떻게 사용하나요?",
        subject_id="requirements_analysis",
        selected_perspective="usage",
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "ok"
    assert state.get("perspective") == "usage"


def test_3_empty_question() -> None:
    _print_case_header("3) 질문 공백")
    payload = build_mock_payload(
        question="   ",
        subject_id="requirements_analysis",
        selected_perspective="auto",
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "error"
    assert state.get("error_code") == "EMPTY_QUESTION"


def test_4_empty_subject() -> None:
    _print_case_header("4) 과목 미입력")
    payload = build_mock_payload(
        question="TCP와 UDP 차이가 뭔가요?",
        subject_id="",
        selected_perspective="auto",
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "error"
    assert state.get("error_code") == "EMPTY_SUBJECT_ID"


def test_5_collection_resolution_fail() -> None:
    _print_case_header("5) 컬렉션 해석 실패 subject")
    payload = build_mock_payload(
        question="테스트 질문",
        subject_id="unknown_subject_xxx",
        selected_perspective="auto",
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "ok"
    assert state.get("resolved_collection_name") is None
    assert state.get("retrieval_hit") is False


def test_6_retrieval_skip_fallback() -> None:
    _print_case_header("6) 검색 결과 0건/skip 경로")
    payload = build_mock_payload(
        question="의미 없는 질의 문자열 qqqqzzzz",
        subject_id="unknown_subject_xxx",
        selected_perspective="auto",
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state.get("retrieval_context") == ""
    assert state.get("citations") == []


def test_7_analogy_with_interests() -> None:
    _print_case_header("7) analogy 관점 + interests")
    payload = build_mock_payload(
        question="운영체제를 게임 비유로 쉽게 설명해줘",
        subject_id="requirements_analysis",
        selected_perspective="auto",
        interests=["게임", "축구"],
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "ok"
    assert state.get("perspective") == "analogy"
    assert state.get("prompt_input", {}).get("interests")


def test_8_low_confidence_bloom() -> None:
    _print_case_header("8) Bloom low-confidence 질문")
    payload = build_mock_payload(
        question="abcxyz 12345",
        subject_id="requirements_analysis",
        selected_perspective="auto",
    )
    state = _node_pipeline(payload)
    _print_key_fields(state)

    assert state["status"] == "ok"
    assert state.get("bloom_confidence") == 0.0


def test_9_chat_history_truncation() -> None:
    _print_case_header("9) chat_history 최근 N개 사용")
    history = [{"role": "user", "content": f"Q{i}"} for i in range(10)]
    payload = build_mock_payload(
        question="질문",
        subject_id="requirements_analysis",
        selected_perspective="auto",
        chat_history=history,
    )
    state = _node_pipeline(payload)
    used_history = state.get("prompt_input", {}).get("chat_history", [])

    print(f"- original_history_count: {len(history)}")
    print(f"- used_history_count: {len(used_history)}")
    print(f"- used_history_first: {used_history[0] if used_history else None}")

    assert len(used_history) <= 6
    assert len(used_history) == 6


def test_10_session_scope_passthrough() -> None:
    _print_case_header("10) session_scope_id 전달 확인")
    payload = build_mock_payload(
        question="질문",
        subject_id="requirements_analysis",
        selected_perspective="auto",
        session_scope_id="session-123",
    )
    state = _node_pipeline(payload)
    print(f"- session_scope_id: {state.get('session_scope_id')}")

    assert state.get("session_scope_id") == "session-123"
    assert state.get("conversation_store_policy") == "browser_session_state"


def run_node_tests() -> None:
    tests = [
        test_1_normal_question_auto,
        test_2_user_selected_perspective,
        test_3_empty_question,
        test_4_empty_subject,
        test_5_collection_resolution_fail,
        test_6_retrieval_skip_fallback,
        test_7_analogy_with_interests,
        test_8_low_confidence_bloom,
        test_9_chat_history_truncation,
        test_10_session_scope_passthrough,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            print("- result: PASS")
            passed += 1
        except AssertionError as e:
            print(f"- result: FAIL (assertion) {e}")
            failed += 1
        except Exception as e:
            print(f"- result: FAIL (exception) {e}")
            failed += 1

    print("\n" + "#" * 72)
    print(f"NODE TEST SUMMARY | passed={passed}, failed={failed}, total={len(tests)}")
    print("#" * 72)


def run_custom_case(args: argparse.Namespace) -> None:
    interests = [item.strip() for item in args.interests.split(",") if item.strip()]
    payload = build_mock_payload(
        question=args.question,
        subject_id=args.subject_id,
        selected_perspective=args.perspective,
        interests=interests,
        session_scope_id=args.session_scope_id,
    )

    _print_case_header("수동 실행: 노드별 상태 확인")
    state = _node_pipeline(payload, verbose=True)

    print("\n[FINAL STATE]")
    _print_key_fields(state)
    print("\n[FINAL ANSWER]")
    print(state.get("answer", ""))

    print("\n[DEBUG TRACE]")
    print(json.dumps(state.get("debug_trace", []), ensure_ascii=False, indent=2))

    print("\n[GRAPH INVOKE RESULT]")
    graph_result = run_question_graph(payload)
    print(json.dumps(graph_result, ensure_ascii=False, indent=2))


def print_subjects() -> None:
    _print_case_header("사용 가능한 subject_id")
    for subject_id, info in SUBJECT_COLLECTION_MAP.items():
        print(f"- {subject_id}: {info['label']} -> {info['collection_name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph 콘솔 테스트")
    parser.add_argument("--question", type=str, help="직접 실행할 질문")
    parser.add_argument(
        "--subject-id",
        type=str,
        default="requirements_analysis",
        help="subject_id 값",
    )
    parser.add_argument(
        "--perspective",
        type=str,
        default="auto",
        help="auto/concept/principle/analogy/relation/usage/caution",
    )
    parser.add_argument(
        "--interests",
        type=str,
        default="",
        help="쉼표로 구분한 관심사 목록",
    )
    parser.add_argument(
        "--session-scope-id",
        type=str,
        default=None,
        help="세션 식별자",
    )
    parser.add_argument(
        "--list-subjects",
        action="store_true",
        help="사용 가능한 subject_id 목록 출력",
    )
    args = parser.parse_args()

    if args.list_subjects:
        print_subjects()
        return

    if args.question:
        run_custom_case(args)
        return

    run_node_tests()


if __name__ == "__main__":
    main()
