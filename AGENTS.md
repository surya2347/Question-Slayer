# AGENTS.md — AI 코딩 어시스턴트 가이드

## 프로젝트 목적
NCS 자격증 학습용 AI 질의응답 플랫폼. Bloom 분류학(1956) 기반 질문 수준 분석 + 6관점 맞춤 답변.

## 기술 스택
Python 3.11 / Streamlit / LangGraph / ChromaDB / OpenAI / Plotly / uv

## 디렉토리 규칙
- `app.py` : Streamlit 엔트리, 세션 초기화
- `pages/` : 1_Chat.py (채팅), 2_Insight.py (시각화)
- `core/` : graph.py(워크플로우), rag.py(검색), prompts.py(템플릿), utils.py(헬퍼)
- `data/` : ncs_pdfs/(PDF), chroma_db/(벡터DB), user_profiles/(JSON)
- `docs/plans/` : 기능별 상세 계획 문서
- `.rules/` : 하위 AI 에이전트 규칙 문서

## 코딩 컨벤션
- 파일명/폴더명: 영문 소문자 + 언더스코어, 한글·이모티콘 금지
- 주석 언어: 한국어 허용
- 환경 변수: python-dotenv + .env (커밋 금지)

## 절대 하지 말 것
- 내부 코드 구조 임의 변경 (plan.md 확인 후 구현)
- .env 커밋 / 한글 파일명 사용 / requirements.txt 사용 (대신 uv 사용)

## 브랜치 전략
main(배포) / dev(통합) / feature/*(기능단위) — PR: feature/* → dev
