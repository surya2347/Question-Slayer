# core/graph.py
# 역할: LangGraph 워크플로우 정의
# - 상태(State) 스키마 정의 (질문, 관점, Bloom 수준, 답변 등)
# - 노드 정의: 과목 탐지 → 관점 라우터 → RAG 검색 → 프롬프트 생성 → LLM 호출
# - 엣지(분기) 정의: 관점별 RunnableBranch 라우팅
# - 그래프 컴파일 및 외부에 실행 인터페이스 제공
