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
uv run streamlit app.py
```

### 5단계 — LangGraph 콘솔 테스트

그래프만 먼저 확인하고 싶다면 아래처럼 실행하면 됩니다.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python test_graph.py
```

- 기본 실행 시 계획서 기준 노드 테스트 10개를 순서대로 돌립니다.
- 각 테스트마다 `status`, `bloom_level`, `perspective`, `retrieval_hit` 등을 확인할 수 있습니다.
- 기본값은 원격 OpenAI 호출 없이 fallback 답변과 중간 로그를 확인하는 모드입니다.

질문과 과목을 직접 넣어서 중간 단계 로그까지 보고 싶다면:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python test_graph.py \
  --question "요구사항 분석에서 기능 요구사항과 비기능 요구사항 차이를 설명해줘" \
  --subject-id requirements_analysis \
  --perspective auto \
  --interests "게임,축구"
```

- 노드별 상태가 순서대로 출력됩니다.
- 마지막에는 최종 답변과 `debug_trace` JSON 로그가 함께 출력됩니다.
- 사용 가능한 `subject_id` 목록은 아래 명령으로 확인할 수 있습니다.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python test_graph.py --list-subjects
```

실제 OpenAI 호출까지 켜고 싶다면 환경 변수를 함께 주면 됩니다.

```bash
QUESTION_SLAYER_ENABLE_REMOTE_RAG=1 \
QUESTION_SLAYER_ENABLE_LLM=1 \
UV_CACHE_DIR=/tmp/uv-cache uv run python test_graph.py \
  --question "요구사항 확인 단계의 핵심 산출물을 설명해줘" \
  --subject-id requirements_analysis
```

#### 추가적인 test 방법

* 문서별 RAG 청킹 결과 보기 (자연어 단위, 임베딩X)

```bash
uv run python scripts/test_chunking.py
```

* PDF 원본 텍스트 + 표 추출 테스트 (원하는 페이지 단위로)
  - `scripts/read_pdf_pages.py`에서 `PAGES_TO_SCAN` 리스트를 수정하여 원하는 페이지(물리적인 페이지)를 지정할 수 있습니다.

```bash
uv run python scripts/read_pdf_pages.py
```

## 과목 수정하는 법

새 과목을 추가하거나 연결을 바꾸려면 아래 순서로 작업하면 됩니다.

1. 새 PDF를 `data/ncs_pdfs/`에 넣습니다.
2. `uv run python scripts/chunk_and_embed.py`로 임베딩합니다.
3. 생성된 Chroma 컬렉션명을 확인합니다.
4. [core/graph.py](/home/user/Question-Slayer/core/graph.py) 의 `SUBJECT_COLLECTION_MAP`에 `subject_id`, `label`, `collection_name`, `source`를 추가하거나 수정합니다.
5. 별칭으로도 인식시키고 싶다면 같은 파일의 `SUBJECT_ALIASES`를 함께 수정합니다.
6. `UV_CACHE_DIR=/tmp/uv-cache uv run python test_graph.py --list-subjects` 와 수동 질문 실행으로 실제 연결을 확인합니다.

현재 기본 매핑은 다음 3개입니다.

- `requirements_analysis` → 요구사항 확인
- `data_io_implementation` → 데이터 입출력 구현
- `server_program_implementation` → 서버 프로그램 구현




## 팀
- 2인 팀 / 개발 기간: 7일
