# core/graph.py
# 역할: LangGraph 워크플로우 정의
# - 상태(State) 스키마 정의 (질문, 관점, Bloom 수준, 답변 등)
# - 노드 정의: 질문 정규화 → Bloom 분석 → 컬렉션 해석 → RAG 검색 → 관점 라우팅
# - 프롬프트 입력 조합 → LLM 호출(또는 fallback) → 최종 응답 포맷팅
# - 콘솔 테스트와 Streamlit 연동을 위한 실행 인터페이스 제공

from __future__ import annotations

import json
import os
import uuid
from operator import add
from pathlib import Path
from typing import Annotated, Any, Optional, TypedDict

from chromadb import PersistentClient
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from core.config import (
    BLOOM_CONFIDENCE_THRESHOLD,
    GRAPH_CHAT_HISTORY_WINDOW,
    GRAPH_CONTEXT_CHAR_LIMIT,
    GRAPH_RETRIEVAL_TOP_K,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
)
from core.prompts import build_fallback_answer, get_perspective_prompt
from core.rag import get_retriever
from core.utils import score_bloom_by_keyword


ALLOWED_PERSPECTIVES = (
    "auto",
    "concept",
    "principle",
    "analogy",
    "relation",
    "usage",
    "caution",
)

QUESTION_INTENT_TO_PERSPECTIVE: dict[str, str] = {
    "concept": "concept",
    "principle": "principle",
    "relation": "relation",
    "usage": "usage",
    "caution": "caution",
    "analogy": "analogy",
}

SUBJECT_COLLECTION_MAP: dict[str, dict[str, str]] = {
    "requirements_analysis": {
        "label": "요구사항 확인",
        "collection_name": "ncs_LM2001020201_23v5_________20251108",
        "source": "LM2001020201_23v5_요구사항+확인_20251108",
    },
    "data_io_implementation": {
        "label": "데이터 입출력 구현",
        "collection_name": "ncs_LM2001020205_23v6____________20251108",
        "source": "LM2001020205_23v6_데이터+입출력+구현_20251108",
    },
    "server_program_implementation": {
        "label": "서버 프로그램 구현",
        "collection_name": "ncs_LM2001020211_23v6____________20251108",
        "source": "LM2001020211_23v6_서버+프로그램+구현_20251108",
    },
}

SUBJECT_ALIASES: dict[str, set[str]] = {
    "requirements_analysis": {
        "requirements_analysis",
        "요구사항 확인",
        "요구사항확인",
        "requirements",
    },
    "data_io_implementation": {
        "data_io_implementation",
        "데이터 입출력 구현",
        "데이터입출력구현",
        "data io",
    },
    "server_program_implementation": {
        "server_program_implementation",
        "서버 프로그램 구현",
        "서버프로그램구현",
        "server program",
    },
}


class GraphState(TypedDict, total=False):
    # 요청 입력 상태
    question: str
    subject_id: str
    selected_perspective: str
    interests: list[str]
    chat_history: list[dict[str, Any]]
    session_scope_id: Optional[str]

    # 분석 상태
    normalized_question: str
    question_intent: str
    bloom_level: Optional[int]
    bloom_label: Optional[str]
    bloom_confidence: float
    bloom_reason: str
    improvement_tip: Optional[str]

    # 검색 라우팅 상태
    collection_candidates: list[str]
    resolved_collection_name: Optional[str]
    collection_resolution_reason: str
    retrieval_query: str

    # 검색 상태
    retrieved_docs: list[Any]
    retrieval_context: str
    citations: list[dict[str, Any]]
    retrieval_hit: bool

    # 관점 라우팅 상태
    perspective: Optional[str]
    routing_reason: str

    # 생성 상태
    prompt_input: dict[str, Any]
    answer_draft: str
    answer_final: str

    # 제어 상태
    status: str
    retry_count: int
    error_code: Optional[str]
    error_message: Optional[str]
    validation_result: str
    conversation_store_policy: Optional[str]
    debug_trace: Annotated[list[dict[str, Any]], add]

    # 최종 반환용 키
    answer: str


def _append_trace(
    state: GraphState,
    node_name: str,
    message: str,
    **extra: Any,
) -> list[dict[str, Any]]:
    """노드별 디버그 추적 정보를 누적합니다."""
    item = {"node": node_name, "message": message}
    if extra:
        item["extra"] = extra
    return [item]


def _normalize_question(question: str) -> str:
    return " ".join((question or "").strip().split())


def _normalize_interests(interests: list[str] | str | None) -> list[str]:
    if interests is None:
        return []
    if isinstance(interests, str):
        cleaned = interests.strip()
        return [cleaned] if cleaned else []
    return [str(item).strip() for item in interests if str(item).strip()]


def _normalize_chat_history(chat_history: Any) -> list[dict[str, Any]]:
    if not isinstance(chat_history, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in chat_history:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "role": str(item.get("role", "user")),
                "content": str(item.get("content", "")).strip(),
            }
        )
    return normalized


def _infer_question_intent(question: str, interests: list[str]) -> str:
    if any(keyword in question for keyword in ("비유", "쉽게")) and interests:
        return "analogy"
    if any(keyword in question for keyword in ("주의", "실수", "문제")):
        return "caution"
    if any(keyword in question for keyword in ("차이", "비교", "관계")):
        return "relation"
    if any(keyword in question for keyword in ("왜", "원리", "작동")):
        return "principle"
    if any(keyword in question for keyword in ("활용", "어떻게 사용", "실무")):
        return "usage"
    if any(keyword in question for keyword in ("무엇", "정의", "뜻")):
        return "concept"
    return "concept"


def _build_improvement_tip(
    bloom_level: Optional[int],
    bloom_confidence: float,
    question_intent: str,
) -> str:
    if bloom_confidence < BLOOM_CONFIDENCE_THRESHOLD:
        return "질문에 핵심 개념이나 비교 대상, 사용 상황을 더 구체적으로 넣어보세요."
    if bloom_level in (1, 2):
        return f"'{question_intent}' 관점에서 예시나 비교 기준을 함께 물으면 더 깊은 답변을 받을 수 있습니다."
    if bloom_level == 3:
        return "실무 상황이나 입력/출력 조건을 덧붙이면 활용 중심 답변이 더 좋아집니다."
    return "판단 기준이나 비교 대상을 함께 적으면 더 정교한 답변을 받을 수 있습니다."


def _list_available_collections() -> list[str]:
    """ChromaDB에서 현재 사용 가능한 컬렉션 목록을 가져옵니다."""
    db_path = str((Path(__file__).resolve().parent.parent / "data" / "chroma_db").resolve())
    try:
        client = PersistentClient(path=db_path)
        return sorted(collection.name for collection in client.list_collections())
    except Exception:
        return sorted(
            {
                info["collection_name"]
                for info in SUBJECT_COLLECTION_MAP.values()
                if info.get("collection_name")
            }
        )


def _resolve_collection_name(subject_id: str) -> tuple[Optional[str], str, list[str]]:
    """subject_id를 실제 컬렉션명으로 해석합니다."""
    available_collections = _list_available_collections()
    subject_key = (subject_id or "").strip()
    if not subject_key:
        return None, "empty_subject_id", available_collections

    if subject_key in SUBJECT_COLLECTION_MAP:
        collection_name = SUBJECT_COLLECTION_MAP[subject_key]["collection_name"]
        if collection_name in available_collections:
            return collection_name, "mapped_subject_id", available_collections
        return collection_name, "mapped_subject_id_missing_in_db", available_collections

    normalized = subject_key.lower().replace(" ", "").replace("_", "")
    for mapped_subject_id, aliases in SUBJECT_ALIASES.items():
        normalized_aliases = {
            alias.lower().replace(" ", "").replace("_", "") for alias in aliases
        }
        if normalized in normalized_aliases:
            collection_name = SUBJECT_COLLECTION_MAP[mapped_subject_id]["collection_name"]
            if collection_name in available_collections:
                return collection_name, "alias_match", available_collections
            return collection_name, "alias_match_missing_in_db", available_collections

    for collection_name in available_collections:
        normalized_collection = collection_name.lower().replace("_", "")
        if normalized and normalized in normalized_collection:
            return collection_name, "collection_partial_match", available_collections

    return None, "collection_not_found", available_collections


def _safe_pages(pages_raw: Any) -> list[int]:
    if isinstance(pages_raw, list):
        return [int(page) for page in pages_raw if str(page).isdigit()]
    if isinstance(pages_raw, str):
        try:
            parsed = json.loads(pages_raw)
            if isinstance(parsed, list):
                return [int(page) for page in parsed if str(page).isdigit()]
        except Exception:
            return []
    return []


def _build_context_and_citations(docs: list[Any]) -> tuple[str, list[dict[str, Any]]]:
    context_parts: list[str] = []
    citations: list[dict[str, Any]] = []

    for index, doc in enumerate(docs, start=1):
        metadata = getattr(doc, "metadata", {}) or {}
        page_content = str(getattr(doc, "page_content", "")).strip()
        pages = _safe_pages(metadata.get("pages"))
        subtitle = metadata.get("subtitle") or "소제목 미확인"
        source = metadata.get("source") or "출처 미확인"

        if page_content:
            context_parts.append(f"[문서 {index}] {subtitle}\n{page_content}")

        citations.append(
            {
                "source": source,
                "pages": pages,
                "subtitle": subtitle,
                "chunk_index": metadata.get("chunk_index"),
            }
        )

    context = "\n\n".join(context_parts)
    if len(context) > GRAPH_CONTEXT_CHAR_LIMIT:
        context = context[:GRAPH_CONTEXT_CHAR_LIMIT].rstrip() + "..."
    return context, citations


def _recent_chat_history(chat_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not chat_history:
        return []
    return chat_history[-GRAPH_CHAT_HISTORY_WINDOW:]


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )


def init_request_node(state: GraphState) -> GraphState:
    """raw payload를 그래프 표준 상태로 정규화합니다."""
    question = str(state.get("question", ""))
    subject_id = str(state.get("subject_id", ""))
    selected_perspective = str(state.get("selected_perspective") or "auto")
    normalized_state: GraphState = {
        "question": question,
        "subject_id": subject_id,
        "selected_perspective": selected_perspective,
        "interests": _normalize_interests(state.get("interests")),
        "chat_history": _normalize_chat_history(state.get("chat_history")),
        "session_scope_id": state.get("session_scope_id"),
        "retry_count": 0,
        "status": "ok",
        "error_code": None,
        "error_message": None,
        "validation_result": "skipped",
        "conversation_store_policy": "browser_session_state",
        "debug_trace": _append_trace(
            state,
            "init_request_node",
            "요청을 표준 상태로 정규화했습니다.",
            subject_id=subject_id,
            selected_perspective=selected_perspective,
        ),
    }
    return normalized_state


def prerequisite_check_node(state: GraphState) -> GraphState:
    """그래프 진입 전 필수 입력값을 검증합니다."""
    question = _normalize_question(state.get("question", ""))
    subject_id = str(state.get("subject_id", "")).strip()
    selected_perspective = str(state.get("selected_perspective", "auto")).strip()

    if not question:
        return {
            "status": "error",
            "error_code": "EMPTY_QUESTION",
            "error_message": "질문을 입력해주세요.",
            "debug_trace": _append_trace(
                state,
                "prerequisite_check_node",
                "질문 공백으로 검증에 실패했습니다.",
                error_code="EMPTY_QUESTION",
            ),
        }

    if not subject_id:
        return {
            "status": "error",
            "error_code": "EMPTY_SUBJECT_ID",
            "error_message": "subject_id를 입력해주세요.",
            "debug_trace": _append_trace(
                state,
                "prerequisite_check_node",
                "과목 미입력으로 검증에 실패했습니다.",
                error_code="EMPTY_SUBJECT_ID",
            ),
        }

    if selected_perspective not in ALLOWED_PERSPECTIVES:
        return {
            "status": "error",
            "error_code": "INVALID_PERSPECTIVE",
            "error_message": (
                "selected_perspective 값이 올바르지 않습니다. "
                f"허용값: {', '.join(ALLOWED_PERSPECTIVES)}"
            ),
            "debug_trace": _append_trace(
                state,
                "prerequisite_check_node",
                "허용되지 않은 관점 값이 들어왔습니다.",
                selected_perspective=selected_perspective,
            ),
        }

    return {
        "status": "ok",
        "error_code": None,
        "error_message": None,
        "debug_trace": _append_trace(
            state,
            "prerequisite_check_node",
            "그래프 실행 전 필수 검증을 통과했습니다.",
        ),
    }


def analyze_question_node(state: GraphState) -> GraphState:
    """질문 정규화와 Bloom 분석, 질문 의도 분류를 수행합니다."""
    if state.get("status") == "error":
        return {
            "debug_trace": _append_trace(
                state,
                "analyze_question_node",
                "이전 오류 상태로 인해 질문 분석을 건너뛰었습니다.",
            )
        }

    normalized_question = _normalize_question(state.get("question", ""))
    bloom_result = score_bloom_by_keyword(normalized_question)
    question_intent = _infer_question_intent(
        normalized_question,
        state.get("interests", []),
    )
    bloom_level = int(bloom_result["level"])
    bloom_label = str(bloom_result["name_ko"])
    bloom_confidence = float(bloom_result["confidence"])
    keywords_found = bloom_result.get("keywords_found", [])
    bloom_reason = (
        f"keyword:{','.join(keywords_found)}"
        if keywords_found
        else "keyword_match_not_found"
    )
    improvement_tip = _build_improvement_tip(
        bloom_level=bloom_level,
        bloom_confidence=bloom_confidence,
        question_intent=question_intent,
    )

    return {
        "normalized_question": normalized_question,
        "question_intent": question_intent,
        "bloom_level": bloom_level,
        "bloom_label": bloom_label,
        "bloom_confidence": bloom_confidence,
        "bloom_reason": bloom_reason,
        "improvement_tip": improvement_tip,
        "debug_trace": _append_trace(
            state,
            "analyze_question_node",
            "질문 의도와 Bloom 수준을 분석했습니다.",
            bloom_level=bloom_level,
            question_intent=question_intent,
            bloom_confidence=bloom_confidence,
        ),
    }


def resolve_collection_node(state: GraphState) -> GraphState:
    """subject_id를 Chroma 컬렉션명으로 해석합니다."""
    if state.get("status") == "error":
        return {
            "collection_candidates": [],
            "resolved_collection_name": None,
            "collection_resolution_reason": "skipped_due_to_error",
            "debug_trace": _append_trace(
                state,
                "resolve_collection_node",
                "이전 오류 상태로 인해 컬렉션 해석을 건너뛰었습니다.",
            ),
        }

    resolved_collection_name, reason, candidates = _resolve_collection_name(
        state.get("subject_id", "")
    )
    return {
        "collection_candidates": candidates,
        "resolved_collection_name": resolved_collection_name,
        "collection_resolution_reason": reason,
        "debug_trace": _append_trace(
            state,
            "resolve_collection_node",
            "subject_id에 대응하는 컬렉션을 해석했습니다.",
            resolved_collection_name=resolved_collection_name,
            reason=reason,
        ),
    }


def retrieve_context_node(state: GraphState) -> GraphState:
    """resolved collection에서 RAG 검색을 수행합니다."""
    if state.get("status") == "error":
        return {
            "retrieval_query": "",
            "retrieved_docs": [],
            "retrieval_context": "",
            "citations": [],
            "retrieval_hit": False,
            "debug_trace": _append_trace(
                state,
                "retrieve_context_node",
                "이전 오류 상태로 인해 검색을 건너뛰었습니다.",
            ),
        }

    resolved_collection_name = state.get("resolved_collection_name")
    retrieval_query = state.get("normalized_question") or state.get("question", "")
    if os.getenv("QUESTION_SLAYER_ENABLE_REMOTE_RAG") != "1":
        return {
            "retrieval_query": retrieval_query,
            "retrieved_docs": [],
            "retrieval_context": "",
            "citations": [],
            "retrieval_hit": False,
            "debug_trace": _append_trace(
                state,
                "retrieve_context_node",
                "원격 RAG 호출이 비활성화되어 retrieval skip 처리했습니다.",
            ),
        }

    if not resolved_collection_name:
        return {
            "retrieval_query": retrieval_query,
            "retrieved_docs": [],
            "retrieval_context": "",
            "citations": [],
            "retrieval_hit": False,
            "debug_trace": _append_trace(
                state,
                "retrieve_context_node",
                "해석된 컬렉션이 없어 retrieval skip 처리했습니다.",
            ),
        }

    retriever = get_retriever(
        collection_name=resolved_collection_name,
        top_k=GRAPH_RETRIEVAL_TOP_K,
    )
    if retriever is None:
        return {
            "retrieval_query": retrieval_query,
            "retrieved_docs": [],
            "retrieval_context": "",
            "citations": [],
            "retrieval_hit": False,
            "debug_trace": _append_trace(
                state,
                "retrieve_context_node",
                "Retriever 생성 실패로 retrieval skip 처리했습니다.",
                collection_name=resolved_collection_name,
            ),
        }

    try:
        docs = retriever.invoke(retrieval_query)
        retrieval_context, citations = _build_context_and_citations(docs)
        return {
            "retrieval_query": retrieval_query,
            "retrieved_docs": docs,
            "retrieval_context": retrieval_context,
            "citations": citations,
            "retrieval_hit": bool(docs),
            "debug_trace": _append_trace(
                state,
                "retrieve_context_node",
                "RAG 검색을 수행했습니다.",
                retrieval_hit=bool(docs),
                citations_count=len(citations),
            ),
        }
    except Exception as exc:
        return {
            "retrieval_query": retrieval_query,
            "retrieved_docs": [],
            "retrieval_context": "",
            "citations": [],
            "retrieval_hit": False,
            "debug_trace": _append_trace(
                state,
                "retrieve_context_node",
                "검색 중 예외가 발생해 retrieval skip 처리했습니다.",
                error=str(exc),
            ),
        }


def route_perspective_node(state: GraphState) -> GraphState:
    """우선순위 기반으로 최종 관점을 1개 선택합니다."""
    if state.get("status") == "error":
        return {
            "perspective": None,
            "routing_reason": "skipped_due_to_error",
            "debug_trace": _append_trace(
                state,
                "route_perspective_node",
                "이전 오류 상태로 인해 관점 라우팅을 건너뛰었습니다.",
            ),
        }

    selected_perspective = state.get("selected_perspective", "auto")
    question_intent = state.get("question_intent", "concept")
    bloom_level = int(state.get("bloom_level") or 1)
    interests = state.get("interests", [])

    if selected_perspective != "auto":
        perspective = selected_perspective
        routing_reason = "user_selected"
    elif question_intent in QUESTION_INTENT_TO_PERSPECTIVE:
        perspective = QUESTION_INTENT_TO_PERSPECTIVE[question_intent]
        routing_reason = f"intent_{question_intent}"
    elif bloom_level in (1, 2):
        perspective = "concept"
        routing_reason = "bloom_concept_default"
    elif bloom_level == 3:
        perspective = "usage"
        routing_reason = "bloom_usage_default"
    elif bloom_level == 4:
        perspective = "relation"
        routing_reason = "bloom_relation_default"
    else:
        perspective = "caution"
        routing_reason = "bloom_caution_default"

    if (
        selected_perspective == "auto"
        and perspective in {"concept", "principle"}
        and interests
        and question_intent == "analogy"
    ):
        perspective = "analogy"
        routing_reason = "intent_analogy"

    return {
        "perspective": perspective,
        "routing_reason": routing_reason,
        "debug_trace": _append_trace(
            state,
            "route_perspective_node",
            "최종 설명 관점을 결정했습니다.",
            perspective=perspective,
            routing_reason=routing_reason,
        ),
    }


def build_prompt_input_node(state: GraphState) -> GraphState:
    """생성 노드에 전달할 구조화된 입력을 조립합니다."""
    if state.get("status") == "error":
        return {
            "prompt_input": {},
            "debug_trace": _append_trace(
                state,
                "build_prompt_input_node",
                "이전 오류 상태로 인해 프롬프트 입력 조합을 건너뛰었습니다.",
            ),
        }

    subject_info = SUBJECT_COLLECTION_MAP.get(state.get("subject_id", ""), {})
    prompt_input = {
        "question": state.get("question", ""),
        "normalized_question": state.get("normalized_question", ""),
        "subject_id": state.get("subject_id", ""),
        "subject_label": subject_info.get("label", state.get("subject_id", "")),
        "perspective": state.get("perspective", "concept"),
        "retrieval_context": state.get("retrieval_context", ""),
        "retrieval_hit": state.get("retrieval_hit", False),
        "citations": state.get("citations", []),
        "interests": (
            state.get("interests", [])
            if state.get("perspective") == "analogy"
            else []
        ),
        "improvement_tip": state.get("improvement_tip"),
        "bloom_label": state.get("bloom_label"),
        "chat_history": _recent_chat_history(state.get("chat_history", [])),
    }

    return {
        "prompt_input": prompt_input,
        "debug_trace": _append_trace(
            state,
            "build_prompt_input_node",
            "LLM 호출용 프롬프트 입력을 조립했습니다.",
            chat_history_count=len(prompt_input["chat_history"]),
            retrieval_hit=prompt_input["retrieval_hit"],
        ),
    }


def generate_answer_node(state: GraphState) -> GraphState:
    """프롬프트를 구성하고 답변 초안을 생성합니다."""
    if state.get("status") == "error":
        return {
            "answer_draft": "",
            "debug_trace": _append_trace(
                state,
                "generate_answer_node",
                "이전 오류 상태로 인해 답변 생성을 건너뛰었습니다.",
            ),
        }

    prompt_input = state.get("prompt_input", {})
    subject_label = prompt_input.get("subject_label") or state.get("subject_id", "")
    prompt_text = get_perspective_prompt(
        perspective=prompt_input.get("perspective", "concept"),
        question=prompt_input.get("question", ""),
        context=prompt_input.get("retrieval_context", ""),
        subject=subject_label,
        interests=", ".join(prompt_input.get("interests", [])) or None,
        bloom_label=prompt_input.get("bloom_label"),
        improvement_tip=prompt_input.get("improvement_tip"),
        chat_history=prompt_input.get("chat_history", []),
    )

    try:
        if os.getenv("QUESTION_SLAYER_ENABLE_LLM") != "1":
            raise ValueError("QUESTION_SLAYER_ENABLE_LLM이 활성화되지 않았습니다.")
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        llm = _create_llm()
        response = llm.invoke(prompt_text)
        answer_text = getattr(response, "content", "") or str(response)
        if not str(answer_text).strip():
            raise ValueError("LLM 응답이 비어 있습니다.")
        return {
            "answer_draft": str(answer_text).strip(),
            "debug_trace": _append_trace(
                state,
                "generate_answer_node",
                "LLM 호출로 답변 초안을 생성했습니다.",
                llm_model=LLM_MODEL,
            ),
        }
    except Exception as exc:
        fallback_answer = build_fallback_answer(
            question=prompt_input.get("question", ""),
            perspective=prompt_input.get("perspective", "concept"),
            subject=subject_label,
            retrieval_context=prompt_input.get("retrieval_context", ""),
            improvement_tip=prompt_input.get("improvement_tip"),
        )
        return {
            "answer_draft": fallback_answer,
            "debug_trace": _append_trace(
                state,
                "generate_answer_node",
                "LLM 호출 실패로 fallback 답변을 생성했습니다.",
                error=str(exc),
            ),
        }


def finalize_response_node(state: GraphState) -> GraphState:
    """외부에 반환할 최종 payload를 구성합니다."""
    if state.get("status") == "error":
        answer_final = state.get("answer_draft") or (
            "요청을 처리하지 못했습니다. 입력값을 확인한 뒤 다시 시도해주세요."
        )
        return {
            "answer_final": answer_final,
            "answer": answer_final,
            "citations": state.get("citations", []),
            "debug_trace": _append_trace(
                state,
                "finalize_response_node",
                "오류 상태 최종 응답을 구성했습니다.",
                error_code=state.get("error_code"),
            ),
        }

    answer_final = state.get("answer_draft") or (
        "현재 생성된 답변이 없습니다. 질문을 조금 더 구체적으로 입력해주세요."
    )
    return {
        "status": state.get("status", "ok"),
        "answer_final": answer_final,
        "answer": answer_final,
        "perspective": state.get("perspective"),
        "bloom_level": state.get("bloom_level"),
        "bloom_label": state.get("bloom_label"),
        "improvement_tip": state.get("improvement_tip"),
        "citations": state.get("citations", []),
        "error_code": state.get("error_code"),
        "error_message": state.get("error_message"),
        "debug_trace": _append_trace(
            state,
            "finalize_response_node",
            "최종 응답 payload를 구성했습니다.",
            citations_count=len(state.get("citations", [])),
        ),
    }


def validate_answer_node(state: GraphState) -> GraphState:
    """Phase 2 확장용 자리입니다."""
    return {
        "validation_result": "skipped",
        "debug_trace": _append_trace(
            state,
            "validate_answer_node",
            "Phase 2 이전이라 검증 노드를 생략했습니다.",
        ),
    }


def build_question_graph():
    """LangGraph 워크플로우를 생성하고 compile 합니다."""
    builder = StateGraph(GraphState)
    builder.add_node("init_request_node", init_request_node)
    builder.add_node("prerequisite_check_node", prerequisite_check_node)
    builder.add_node("analyze_question_node", analyze_question_node)
    builder.add_node("resolve_collection_node", resolve_collection_node)
    builder.add_node("retrieve_context_node", retrieve_context_node)
    builder.add_node("route_perspective_node", route_perspective_node)
    builder.add_node("build_prompt_input_node", build_prompt_input_node)
    builder.add_node("generate_answer_node", generate_answer_node)
    builder.add_node("finalize_response_node", finalize_response_node)

    builder.set_entry_point("init_request_node")
    builder.add_edge("init_request_node", "prerequisite_check_node")
    builder.add_edge("prerequisite_check_node", "analyze_question_node")
    builder.add_edge("prerequisite_check_node", "resolve_collection_node")
    builder.add_edge("resolve_collection_node", "retrieve_context_node")
    builder.add_edge(
        ["analyze_question_node", "retrieve_context_node"],
        "route_perspective_node",
    )
    builder.add_edge("route_perspective_node", "build_prompt_input_node")
    builder.add_edge("build_prompt_input_node", "generate_answer_node")
    builder.add_edge("generate_answer_node", "finalize_response_node")
    builder.add_edge("finalize_response_node", END)

    return builder.compile()


def build_mock_payload(
    question: str,
    subject_id: str,
    selected_perspective: str = "auto",
    interests: list[str] | str | None = None,
    chat_history: Optional[list[dict[str, Any]]] = None,
    session_scope_id: Optional[str] = None,
) -> dict[str, Any]:
    """콘솔 테스트용 payload를 생성합니다."""
    return {
        "question": question,
        "subject_id": subject_id,
        "selected_perspective": selected_perspective,
        "interests": interests,
        "chat_history": chat_history,
        "session_scope_id": session_scope_id or f"mock-session-{uuid.uuid4().hex[:8]}",
    }


def run_question_graph(payload: dict[str, Any]) -> dict[str, Any]:
    """mock payload로 그래프를 실행하고 최종 응답을 반환합니다."""
    try:
        graph_app = build_question_graph()
        result = graph_app.invoke(payload)
        return {
            "status": result.get("status", "ok"),
            "answer": result.get("answer", ""),
            "perspective": result.get("perspective"),
            "bloom_level": result.get("bloom_level"),
            "bloom_label": result.get("bloom_label"),
            "improvement_tip": result.get("improvement_tip"),
            "citations": result.get("citations", []),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "debug_trace": result.get("debug_trace", []),
        }
    except Exception as exc:
        return {
            "status": "error",
            "answer": "그래프 실행 중 오류가 발생했습니다.",
            "perspective": None,
            "bloom_level": None,
            "bloom_label": None,
            "improvement_tip": None,
            "citations": [],
            "error_code": "GRAPH_RUN_FAILED",
            "error_message": str(exc),
            "debug_trace": [
                {
                    "node": "run_question_graph",
                    "message": "그래프 실행 중 예외가 발생했습니다.",
                    "extra": {"error": str(exc)},
                }
            ],
        }
