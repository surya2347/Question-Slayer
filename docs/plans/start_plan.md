# Question-Slayer 프로젝트 전체 환경 설정 계획

### 날짜
2026-04-08

---

## 프로젝트 개요

NCS(국가직무능력표준) 자격증 학습을 위한 AI 기반 질의응답 플랫폼.
사용자의 질문 수준을 블룸의 분류학 기반으로 분석하고,
6가지 관점(개념, 원리, 비유, 관계, 활용, 주의사항)으로 맞춤형 답변을 제공한다.

- **팀 인원**: 2명
- **목표 기간**: 7일 (Day 1 ~ Day 7, 여유분 포함)
- **최종 목표**: Streamlit Cloud 배포 완료 + 시연 가능 상태

---

## 기술 스택

| 분류 | 선택 | 비고 |
|---|---|---|
| Frontend | Streamlit (멀티페이지) | 빠른 UI 구축 |
| Backend | Python 3.11+ | 단일 언어 통일 |
| LLM 오케스트레이션 | LangGraph (LangChain 기반) | 워크플로우 + 상태 관리 |
| Vector DB | ChromaDB | 로컬 임베딩 저장소 |
| Embedding | OpenAI text-embedding-3-small (또는 HuggingFace) | 비용 vs 성능 트레이드오프 |
| 시각화 | Plotly | 블룸 분포 차트, 성장 곡선 |
| 패키지/가상환경 관리 | uv | pip 대비 빠른 설치, pyproject.toml + uv.lock 기반 |
| 환경 변수 관리 | python-dotenv + .env | API Key 관리 |
| PDF 처리 | pdfplumber (1순위), pypdf (2순위) | 한글 깨짐 최소화 |
| 개발 환경 | Ubuntu 24, VSCode, Antigravity | |

---

## MVP 정의 (핵심 기능)

### 반드시 구현 (Core)
1. **6관점 라우터 + 관점별 프롬프트** — 개념 / 원리 / 비유 / 관계 / 활용 / 주의사항
2. **과목별 RAG** — NCS PDF → ChromaDB 적재 → 검색 기반 답변
3. **블룸의 분류학 스코어링** — 질문 인지 수준 판단 (지식 → 평가 6단계) + 교정 가이드
4. **관심사 기반 비유 파이프라인** — 사용자 관심사를 비유 관점에 주입
5. **관심사 저장** — session_state + JSON 파일 (URL/로그인 없이 단순 저장)

### 시간 여유 시 구현 (Buffer)
- 환각 억제 Self-Correction 로직 (RAG 근거 검증)
- Insight 페이지 Plotly 차트 (블룸 분포 막대, 성장 곡선)
- UI 디테일 (Spinner, Badge, Tag)

### 제외 (스코프 아웃)
- 사용자 모르는 범위 추적
- 로그인 / 계정 관리
- 실시간 DB 동기화

---

## 프로젝트 디렉토리 구조

```
Question-Slayer/
├── app.py                        # Streamlit 메인 엔트리 — Home 페이지, 세션 초기화, 과목·관심사 선택 UI
├── pages/
│   ├── 1_Chat.py                 # 채팅 페이지 — 질의응답, 관점 선택, Bloom 단계 뱃지 표시
│   └── 2_Insight.py             # Insight 페이지 — 학습 이력 시각화 대시보드 (Plotly)
├── core/
│   ├── graph.py                  # LangGraph 워크플로우 — 노드 정의, 엣지 라우팅, 상태 스키마
│   ├── rag.py                    # RAG 파이프라인 — ChromaDB 연결, PDF 처리, 청킹, 임베딩, 검색
│   ├── prompts.py                # 프롬프트 모음 — 6관점 템플릿, Bloom 스코어링, 교정 가이드, 비유 주입
│   └── utils.py                  # 유틸리티 — 관심사 JSON 입출력, Bloom 수준 계산, 공통 헬퍼
├── data/
│   ├── ncs_pdfs/                 # NCS 원본 PDF 파일 보관
│   ├── chroma_db/                # ChromaDB 로컬 저장소 (자동 생성, .gitignore 처리)
│   └── user_profiles/           # 사용자 관심사 JSON 저장소
├── docs/
│   └── plans/                   # 기능별 상세 계획 문서 보관소
│       └── plan.md              # 현재 파일
├── .env                          # OpenAI API Key 등 비밀 키 (절대 커밋 금지)
├── .env.example                  # .env 템플릿 (커밋용, 실제 값 없음)
├── .gitignore                    # chroma_db/, .env, .venv/, __pycache__ 등 제외
├── .python-version               # uv가 사용할 Python 버전 고정 (예: 3.11)
├── pyproject.toml                # uv 프로젝트 메타데이터 + 의존성 선언
├── uv.lock                       # uv 락파일 — 재현 가능한 의존성 버전 고정 (커밋 대상)
├── AGENTS.md                     # AI 코딩 어시스턴트(Antigravity 등)에게 전달할 프로젝트 컨텍스트 및 규칙
└── README.md                     # 프로젝트 소개, 실행 방법, 팀 정보
```

---

## 주의사항

- 절대 내부 코드 구조(함수, 클래스 등)를 작성하지 말 것.
- 폴더명·파일명은 영문 소문자 + 언더스코어 기준, 한글·이모티콘 사용 금지.
- 환경 설정 단계에서는 각 파일을 생성하고 **주석으로 역할만 기술**, 실제 코드 작성 금지.
- `.env`는 절대 Git에 커밋하지 말 것 — `.gitignore`에 반드시 포함.
- `chroma_db/` 폴더도 `.gitignore` 처리 (용량 이슈 및 재현 가능성 확보).

---

## 브랜치 전략

```
main          ← 배포용 (Streamlit Cloud 연결)
dev           ← 통합 개발 브랜치
feature/...   ← 기능 단위 브랜치 (예: feature/rag-pipeline, feature/bloom-scorer)
```

- PR은 `feature/* → dev` 로만 올림.
- `dev → main` 머지는 Day 4 배포 직전 1회.

---

## 일별 작업 계획

### Day 1 — 환경 설정 + RAG 적재
| 작업 | 담당 | 완료 기준 |
|---|---|---|
| GitHub Repo 생성 + 브랜치 전략 적용 | 공통 | main/dev/feature 구조 확인 |
| 디렉토리 골격 생성 + 파일별 주석 작성 | 공통 | 전체 폴더·파일 존재 확인 |
| uv 설치 확인 (`uv --version`) | A | uv 명령어 동작 확인 |
| `uv init` + `.python-version` 설정 | A | `pyproject.toml` 생성 확인 |
| `uv venv` + `uv sync` 로 가상환경 구성 | A | `.venv/` 생성 + 패키지 설치 완료 |
| .env / .env.example / .gitignore 설정 | A | API Key 로드 확인 |
| NCS PDF 수집 (3~4개 과목) | B | ncs.go.kr에서 다운로드 완료 |
| PDF 텍스트 추출 + 한글 깨짐 테스트 | B | 정상 출력 확인 |
| 청킹 전략 합의 (800 tokens, 과목 태깅) | 공통 | 메타데이터 스키마 확정 |
| ChromaDB 컬렉션 생성 + 임베딩 적재 | A | 검색 결과 출력 확인 |
| **체크포인트**: RAG 쿼리 검색 성공 | 공통 | 콘솔에서 검색 결과 출력 |

### Day 2 — 라우터 + 비유 파이프라인
| 작업 | 담당 | 완료 기준 |
|---|---|---|
| 과목 탐지(Subject Router) 로직 | A | 키워드/유사도 기반 과목 분류 |
| 6관점별 프롬프트 템플릿 작성 | B | 6개 관점 모두 초안 완성 |
| 관점 라우터 구현 (LangGraph RunnableBranch) | A | 관점별 분기 동작 확인 |
| 관심사 저장 구조 (session_state + JSON) | B | 저장·불러오기 확인 |
| 비유 엔진: 관심사 주입 파이프라인 | B | 맞춤형 비유 답변 생성 확인 |
| **체크포인트**: 질문 → 비유 답변 End-to-End | 공통 | 전체 흐름 동작 확인 |

### Day 3 — Bloom 스코어링 + Streamlit UI
| 작업 | 담당 | 완료 기준 |
|---|---|---|
| Bloom 스코어링 프롬프트 (JSON 반환) | A | 6단계 수준 정량화 |
| 질문 교정 가이드 프롬프트 | A | 수준 향상 피드백 생성 확인 |
| 분석 이력 저장 로직 | A | 시각화용 JSON 축적 |
| Streamlit 멀티페이지 구조 생성 | B | app.py + pages/ 라우팅 |
| Home: 관심사·과목 선택 UI | B | 세션 저장 확인 |
| Chat: 채팅창 + Bloom 뱃지 표시 | B | 답변 + 단계 뱃지 렌더링 |
| 용어 설명 기능 | A | 용어 클릭 시 설명 표시 |
| Insight: 차트 레이아웃 뼈대 | B | 대시보드 페이지 렌더링 |

### Day 4 — 연동 + 배포
| 작업 | 담당 | 완료 기준 |
|---|---|---|
| 전체 페이지 데이터 연동 테스트 | 공통 | 세션 공유 및 흐름 검증 |
| Plotly Bloom 단계 분포 차트 | B | 막대 그래프 렌더링 |
| Plotly 질문 수준 성장 곡선 | B | 라인 그래프 렌더링 |
| 예외 처리 + Fallback 메시지 처리 | 공통 | 오류 상황 안내 메시지 |
| Streamlit Cloud 배포 + secrets.toml 설정 | A | 퍼블릭 URL 접속 확인 |
| **최종**: 시나리오 시연 테스트 | 공통 | 발표 준비 완료 |

### Buffer (Day 5~7 여유분)
| 작업 | 담당 |
|---|---|
| 환각 억제 Self-Correction 로직 (RAG 근거 검증) | 공통 |
| UI 디테일 강화 (Spinner, Tag, Badge 등) | B |
| 최종 발표 자료 정리 | 공통 |

---

## 패키지 관리 (uv)

### uv 기본 사용법

```bash
# uv 설치 (최초 1회)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 초기화
uv init

# Python 버전 고정
uv python pin 3.11

# 가상환경 생성
uv venv

# 패키지 추가 (pyproject.toml 자동 업데이트 + uv.lock 갱신)
uv add streamlit langchain langgraph langchain-openai langchain-community \
       chromadb pdfplumber python-dotenv plotly openai

# 의존성 전체 설치 (팀원 온보딩 시)
uv sync

# 가상환경 활성화
source .venv/bin/activate
```

### pyproject.toml 의존성 초안

```toml
[project]
name = "question-slayer"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.33.0",
    "langchain>=0.2.0",
    "langgraph>=0.1.0",
    "langchain-openai>=0.1.0",
    "langchain-community>=0.2.0",
    "chromadb>=0.5.0",
    "pdfplumber>=0.10.0",
    "python-dotenv>=1.0.0",
    "plotly>=5.20.0",
    "openai>=1.30.0",
]
```

> `uv.lock`은 Git에 커밋한다 — 팀원 간 동일한 의존성 버전 보장.

---

## AGENTS.md 작성 지침 (Day 1에 생성)
30 줄을 넘지 않도록 작성

Antigravity 등 AI 코딩 어시스턴트가 프로젝트를 이해할 수 있도록 다음 내용을 포함한다:
- 프로젝트 목적 및 MVP 범위
- 디렉토리 구조 설명
- 코딩 컨벤션 (파일명, 변수명, 주석 언어 등)
- 절대 하지 말아야 할 것 (코드 구조 임의 변경, 한글 파일명 등)
- 브랜치 전략 ( main, dev, feature/* )