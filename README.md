# Question-Slayer

NCS 자격증 학습을 위한 AI 기반 질의응답 플랫폼.
블룸의 분류학 기반 질문 수준 분석 + 6가지 관점 맞춤 답변 + 관심사 비유 학습.

## 실행 방법

### 1단계 — 저장소 클론 및 의존성 설치

```bash
# 저장소 클론
git clone https://github.com/surya2347/Question-Slayer.git
cd Question-Slayer

# 가상환경 생성 및 의존성 설치 (uv)
uv venv
uv sync
source .venv/bin/activate
```

### 2단계 — 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 값을 입력
```

### 3단계 — NCS PDF 임베딩 (최초 1회)

`data/ncs_pdfs/` 폴더에 NCS 학습모듈 PDF를 넣은 뒤 아래 CLI를 실행합니다.

```bash
uv run python scripts/chunk_and_embed.py
```

- 발견된 PDF 목록이 출력되며 개별 또는 전체 처리를 선택할 수 있습니다.
- 이미 임베딩된 파일은 자동으로 건너뜁니다 (SHA-256 해시 기반 중복 방지).
- 임베딩 결과는 `data/chroma_db/`에 저장됩니다 (Git 추적 대상).

> 📎 RAG 파이프라인 상세 설명 → [docs/plans/RAG_plan.md](docs/plans/RAG_plan.md)

### 4단계 — 앱 실행

```bash
streamlit run app.py
```

## 팀
- 2인 팀 / 개발 기간: 7일
