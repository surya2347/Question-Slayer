# core/config.py
# 역할: 프로젝트 전역 상수 및 LLM 설정 관리

from __future__ import annotations

# ---------------------------------------------------------------------------
# LLM 설정
# ---------------------------------------------------------------------------
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.6
LLM_MAX_TOKENS = 1000

# ---------------------------------------------------------------------------
# 그래프 실행 설정
# ---------------------------------------------------------------------------
GRAPH_CHAT_HISTORY_WINDOW = 6
GRAPH_RETRIEVAL_TOP_K = 5
GRAPH_CONTEXT_CHAR_LIMIT = 2200
BLOOM_CONFIDENCE_THRESHOLD = 0.6
