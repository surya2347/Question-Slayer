# core/rag.py
# 역할: RAG(Retrieval-Augmented Generation) 파이프라인
# - pdfplumber 로 NCS PDF 텍스트 추출
# - 800 tokens 기준 청킹 + 과목명 메타데이터 태깅
# - OpenAI 임베딩으로 벡터화 후 ChromaDB 컬렉션에 적재
# - 사용자 질문을 임베딩하여 유사 청크 검색 (과목 필터 적용)
