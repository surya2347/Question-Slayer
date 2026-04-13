# 🎯 Question-Slayer

> 질문을 못 만드는 학습자를 위한 AI 기반 학습 도우미

**배포 URL**:[ https://question-slayer-cfxpquyozl2kxbc3rxtypj.streamlit.app](https://question-slayer-de7pihwiprkfax68hn8wad.streamlit.app)

---

## 📌 프로젝트 소개

### 배경
모르는 개념이 생겨도 어떻게 질문해야 할지 몰라 그냥 넘겨본 경험, 있으신가요?  
기존 검색이나 단순 챗봇은 표면적인 정의만 던져줄 뿐, 개념의 원리나 인접 개념과의 관계까지는 연결해주지 못합니다.  
Question-Slayer는 학습자의 막힌 지점을 AI가 먼저 질문으로 정리하고, 6가지 관점으로 구조화된 답변을 제공합니다.

### 핵심 기능
- **질문 정규화** - 학습자의 표현을 NCS 학습모듈 **용어로 재정렬**해 답변 상단에 제시
- **6관점 맞춤 답변** - 개념 · 원리 · 비유 · 관계 · 활용 · 주의사항으로 구조화된 설명
- **Bloom 수준 분석** - 질문을 **인지적 난이도 6단계로 자동 분류**해 현재 이해 수준 시각화
- **RAG 파이프라인** - NCS 교재 PDF 기반으로 맥락에 맞는 정확한 답변 제공

---

## 🛠️ 기술 스택

| 카테고리 | 기술 |
|---------|------|
| Language / Runtime | Python 3.11 |
| UI | Streamlit |
| LLM · 오케스트레이션 | LangGraph, LangChain, OpenAI API |
| 벡터 DB · RAG | ChromaDB, OpenAI Embeddings |
| 시각화 | Plotly |
| 패키지 관리 | uv |

---

## 👥 팀원

| GitHub | 역할 |
|--------|------|
| [surya2347](https://github.com/surya2347) | LangGraph 워크플로우, LLM 통합 로직 |
| [morunero211](https://github.com/morunero211) | Bloom 기반 인지 분류 로직, Streamlit UI/UX  |

개발 기간: 7일 · 팀 규모: 2인

---

## 🚀 실행 방법 (로컬)

```bash
# 1. 저장소 클론
git clone https://github.com/surya2347/Question-Slayer.git
cd Question-Slayer

# 2. 의존성 설치
uv venv
uv sync
source .venv/bin/activate

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 4. 앱 실행
uv run streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

> 💡 임베딩 데이터는 `data/chroma_db/`에 포함되어 있어 별도 처리가 불필요합니다.

---

## 🏗️ 아키텍처

```
입력 (질문 + 과목 + 관심사)
  ↓
[1] 질문 정규화        자연어 → NCS 표준 용어로 변환
  ↓
[2] Bloom 수준 분류    인지적 난이도 1~6단계 추출
  ↓
[3] RAG 검색          벡터 임베딩으로 관련 교재 내용 추출
  ↓
[4] 관점 라우팅        Bloom 수준 기반 최적 관점 선택
  ↓
[5] 답변 생성          최종 답변 + Bloom 수준 메타데이터 출력
```
