# RAG 청킹·임베딩·적재·검색 파이프라인 구현 계획

### 날짜
2026-04-09

---

## 개요 및 목표

- **목적**: NCS 학습모듈 PDF를 청킹·임베딩하여 ChromaDB에 적재하고, 과목별 유사 청크 검색 기능 제공
- **스코프**: PDF 텍스트 추출 → 노이즈 필터링 → 하이브리드 청킹 → 임베딩 → ChromaDB 적재 → Retriever 함수
- **대상 문서**: `data/ncs_pdfs/` 내 NCS 학습모듈 PDF
- **임베딩 모델**: OpenAI `text-embedding-3-small` — Streamlit Cloud 배포 호환, 7일 스프린트 적합
- **벡터 DB**: ChromaDB `PersistentClient` — **과목별 컬렉션 1개씩** 생성
- **청킹 전략**: 하이브리드 (1차: NCS 소제목 기준 분할 → 2차: 500 tokens 초과 시 RecursiveCharacterTextSplitter 재분할, 50 tokens 오버랩)
- **표 처리**: `pdfplumber.extract_tables()` + `pandas.to_markdown()` 으로 텍스트 기반 표만 Markdown 변환. **도표·그림·사진·삽화 일체 제외**
- **노이즈 필터링**: 키워드 기반. "교수·학습 방법", "평가", "개발 이력" 섹션 제거
- **저작권 고지**: NCS 학습모듈은 교육 목적 + 출처 명시 조건으로 활용 가능. 도표/사진/삽화/도면은 원작자 동의 필요 → 이미지 기반 콘텐츠 제외 사유. 챗봇 답변 시 "출처: NCS 학습모듈({과목명})" 자동 첨부 로직 필요

---

## 디렉토리 구조

```
Question-Slayer/
├── core/
│   └── rag.py                  # [수정] RAG 파이프라인 전체 — 추출, 청킹, 임베딩, 적재, 검색
├── scripts/                     # core/는 import용 라이브러리, scripts/는 직접 실행 CLI → 분리 적절
│   └── chunk_and_embed.py      # [신규] 인터랙티브 CLI — PDF 선택 및 파이프라인 실행
├── data/
│   ├── ncs_pdfs/               # [기존] NCS 원본 PDF 보관
│   └── chroma_db/              # [자동생성] ChromaDB 로컬 저장소 (Git 포함 — 배포 서버 휘발성 대응)
└── pyproject.toml              # [수정] pandas, tabulate 의존성 추가
```

---

## 핵심 플로우

```
1. [PDF 로드]       pdfplumber로 페이지별 텍스트 + 표 추출
       ↓
2. [표 변환]        텍스트 기반 표 → Markdown 테이블 변환 (pandas.to_markdown)
       ↓
3. [텍스트 병합]    페이지별 텍스트를 하나로 병합 (페이지 경계 마커 삽입)
       ↓
4. [노이즈 필터링]  키워드 기반 불필요 섹션 제거
       ↓
5. [1차 분할]       NCS 소제목 패턴으로 섹션 분할
       ↓
6. [2차 분할]       500 tokens 초과 섹션 → RecursiveCharacterTextSplitter 재분할
       ↓
7. [임베딩 + 적재]  OpenAI text-embedding-3-small → ChromaDB 과목별 컬렉션 저장
       ↓
8. [검색]           사용자 질문 → 과목 컬렉션에서 유사 청크 Top-K 검색
```

---

## 모듈별 구현 명세

### `core/rag.py`

#### 상수 및 설정

```python
CHROMA_DB_PATH: str = "data/chroma_db"
NCS_PDF_DIR: str = "data/ncs_pdfs"
EMBEDDING_MODEL: str = "text-embedding-3-small"
MAX_CHUNK_TOKENS: int = 500
CHUNK_OVERLAP_TOKENS: int = 50
MIN_CHUNK_TOKENS: int = 50          # 이 값 미만인 섹션은 이전 섹션에 병합

# 노이즈 필터링 키워드 (섹션 헤더에 포함 시 해당 섹션 ~ 다음 구조 헤더까지 제거)
NOISE_SECTION_KEYWORDS: list[str] = [
    "교수·학습 방법", "교수 학습 방법", "교수학습 방법",
    "평가 준거", "평가준거",
    "개발 이력", "개발이력",
]

# 도표·그림 제거 후 빈 섹션에 삽입할 플레이스홀더
EMPTY_SECTION_PLACEHOLDER: str = (
    "[해당 섹션은 도표·그림 위주 콘텐츠로 구성되어 텍스트 정보가 제외되었습니다.]"
)

# NCS 문서 구조 감지용 정규식
# ⚠️ LEARNING_UNIT_PATTERN 은 실제 PDF 확인 후 수정됨 — 계획 대비 편차 발생.
#    변경 내용 및 사유: ## 구현 기록 > 계획 대비 편차 섹션 참조.
LEARNING_UNIT_PATTERN: str = r"학습\s*(\d+)\s*[:.·]\s*(.+)"  # 원본 (계획서 기준)
SECTION_TYPE_PATTERN: str = r"(필요\s*지식|수행\s*내용|수행내용|필요지식)"
# 다양한 대시 대응: 하이픈(-), 엔 대시(–), 엠 대시(—) + 공백 유연성
SUBTITLE_PATTERN: str = r"(\d+\s*[-–—]\s*\d+\.?\s+.+)|([가-힣]\.\s+.+)"

# 페이지 경계 마커 (내부 처리용, 최종 텍스트에서 제거)
PAGE_MARKER_TEMPLATE: str = "\n<!--PAGE:{page_num}-->\n"
PAGE_MARKER_REGEX: str = r"<!--PAGE:(\d+)-->"
```

#### 임포트

```python
import re
import hashlib
from pathlib import Path

import pdfplumber
import pandas as pd
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
```

---

#### 함수 명세

##### 1. `extract_pages(pdf_path: str) -> list[dict]`

- **역할**: PDF에서 페이지별 텍스트와 표 추출
- **반환**: `[{"page": int, "text": str}, ...]`
- **로직**:
  1. `pdfplumber.open(pdf_path)`
  2. 각 page에서 `extract_text()` → 텍스트 추출 (None이면 `""`)
  3. `extract_tables()` → 각 표를 `pd.DataFrame(table[1:], columns=table[0]).to_markdown(index=False)` 변환
  4. 표 Markdown을 텍스트 끝에 `\n\n{md_table}\n\n` 으로 추가
  5. `{"page": 1-indexed, "text": 결합된_텍스트}` 리스트 반환
- **예외**: `FileNotFoundError` raise (파일 미존재). pdfplumber 파싱 오류 → 해당 페이지 건너뛰기 + 경고 로그
- **취소**: 해당 없음

---

##### 2. `merge_pages(pages: list[dict]) -> str`

- **역할**: 페이지별 텍스트를 하나로 병합. 페이지 경계에 `<!--PAGE:N-->` 마커 삽입
- **반환**: `str` — 마커 포함 전체 텍스트
- **로직**: 각 페이지 앞에 `PAGE_MARKER_TEMPLATE.format(page_num=page["page"])` 삽입 후 결합

---

##### 3. `filter_noise(text: str) -> str`

- **역할**: 키워드 기반 불필요 섹션 제거
- **반환**: `str` — 정리된 텍스트
- **로직**:
  1. `NOISE_SECTION_KEYWORDS` 각 키워드의 위치 탐색
  2. 키워드 라인 ~ 다음 `LEARNING_UNIT_PATTERN` 또는 `SECTION_TYPE_PATTERN` 직전까지 삭제
  3. 다음 패턴 없으면 문서 끝까지 삭제
- **정상 흐름**: 필터링된 텍스트 반환
- **예외 흐름**: 키워드 미발견 시 원본 그대로 반환

---

##### 4. `split_by_sections(text: str) -> list[dict]`

- **역할**: NCS 문서 구조에 따라 소제목 단위로 1차 분할 + **짧은 섹션 병합** + **빈 섹션 플레이스홀더 주입**
- **반환**: `[{"learning_unit": str, "section_type": str, "subtitle": str, "content": str, "pages": list[int]}, ...]`
- **로직**:
  1. `LEARNING_UNIT_PATTERN` → 대단위 분할 (예: "학습 1: 현행 시스템 분석하기")
  2. 각 대단위에서 `SECTION_TYPE_PATTERN` → 중단위 분할 (필요 지식 / 수행 내용)
  3. 각 중단위에서 `SUBTITLE_PATTERN` → 소단위 분할 (예: "1-1. 운영체제 개요")
  4. 소단위 패턴 미매칭 텍스트 → 중단위 이름을 subtitle로 사용
  5. 각 섹션의 content에서 `PAGE_MARKER_REGEX` 탐색 → 페이지 번호 목록 추출
  6. 페이지 마커를 content에서 제거
  7. **빈 껍데기 처리**: content가 공백만 있거나 비어있는 섹션(도표·그림 제거로 인한 빈 섹션) → `EMPTY_SECTION_PLACEHOLDER` 주입. 단, 이 플레이스홀더 청크도 임베딩 대상에 포함하여 LLM이 "원문에 도표가 있으나 텍스트로는 확인 불가" 안내 가능
  8. **짧은 섹션 병합**: 토큰 수 < `MIN_CHUNK_TOKENS`(50) 인 섹션 → 이전 섹션의 content 뒤에 `\n\n--- {subtitle} ---\n\n{content}` 형태로 병합. 첫 번째 섹션이 짧으면 다음 섹션에 병합

---

##### 5. `refine_chunks(sections: list[dict], max_tokens: int = 500, overlap_tokens: int = 50) -> list[Document]`

- **역할**: 500 tokens 초과 섹션을 RecursiveCharacterTextSplitter로 2차 분할
- **반환**: `list[Document]` — LangChain Document 리스트
- **로직**:
  1. `RecursiveCharacterTextSplitter.from_tiktoken_encoder(model_name="gpt-4", chunk_size=max_tokens, chunk_overlap=overlap_tokens, separators=["\n\n", "\n", "|\n", ". ", " "])` 생성
     - `"|\n"` 세퍼레이터 추가: Markdown 테이블의 행 경계에서 우선 분할하여 **표의 행이 중간에 잘리는 문제 방지**
  2. 각 섹션:
     - 토큰 수 ≤ `max_tokens` → `Document` 1개 (chunk_index=0)
     - 토큰 수 > `max_tokens` → `splitter.split_text()` → 각 분할에 chunk_index 부여
  3. metadata 설정 — 아래 스키마 참조. `source`와 `doc_hash`는 호출부(`process_pdf`)에서 주입

#### 메타데이터 스키마 (ChromaDB JSON)

> ChromaDB는 각 Document에 JSON key-value 메타데이터를 저장함. 검색 시 필터 조건으로 활용 가능.

| 필드 | 타입 | 필수 | 설명 | 예시 |
|---|---|---|---|---|
| `source` | `str` | ✅ | PDF 파일명 또는 과목명. 출처 자동 첨부 기능에 사용 | `"요구사항확인"` |
| `doc_hash` | `str` | ✅ | PDF 파일의 SHA-256 해시값 (앞 16자). 중복 적재 방지용 | `"a1b2c3d4e5f6g7h8"` |
| `learning_unit` | `str` | ✅ | 대단위 학습명 | `"학습 1: 현행 시스템 분석하기"` |
| `section_type` | `str` | ✅ | 중단위 구분 | `"필요 지식"` 또는 `"수행 내용"` |
| `subtitle` | `str` | ✅ | 소단위 소제목 | `"1-1. 운영체제 개요"` |
| `pages` | `str` | ⬚ | 원본 PDF 페이지 범위 (JSON 문자열) | `"[15, 16, 17]"` |
| `chunk_index` | `int` | ✅ | 동일 소제목 내 청크 순번 (0-indexed) | `0` |

> **`doc_hash` 동작 원리**: `process_pdf()` 실행 시 PDF 파일의 SHA-256 해시를 계산. 컬렉션에 동일 `doc_hash`가 이미 존재하면 임베딩을 건너뜀(Skip) → OpenAI API 비용 절약.

---

##### 6. `get_embeddings() -> OpenAIEmbeddings`

- **역할**: OpenAI 임베딩 모델 인스턴스 반환
- **로직**: `load_dotenv()` 호출 후 `OpenAIEmbeddings(model=EMBEDDING_MODEL)` 반환
- **예외**: `OPENAI_API_KEY` 미설정 시 명시적 오류 메시지와 함께 `ValueError` raise

---

##### 7. `store_chunks(documents: list[Document], collection_name: str) -> Chroma`

- **역할**: Document 리스트를 ChromaDB 컬렉션에 임베딩 + 저장
- **로직**:
  1. `get_embeddings()` 호출
  2. `Chroma.from_documents(documents=documents, embedding=embeddings, persist_directory=CHROMA_DB_PATH, collection_name=collection_name)` 호출
- **정상 흐름**: Chroma 인스턴스 반환
- **예외 흐름**: API 키 오류 → `ValueError`. 네트워크 오류 → 오류 전파

---

##### 8. `get_retriever(collection_name: str, top_k: int = 5) -> VectorStoreRetriever`

- **역할**: 과목별 컬렉션에서 유사 청크 검색 Retriever 반환
- **로직**:
  1. `Chroma(persist_directory=CHROMA_DB_PATH, collection_name=collection_name, embedding_function=get_embeddings())`
  2. `.as_retriever(search_type="similarity", search_kwargs={"k": top_k})` 반환
- **사용 예**: `retriever.invoke("운영체제의 종류는?")` → `list[Document]`
- **예외 흐름**: 컬렉션 미존재 시 빈 결과 반환 + 경고 로그

> **스코프 경계**: 검색 결과의 중복 제거(Context Merging)와 출처 포맷팅(`[출처: 요구사항 확인(15p)]` 형태 변환)은 이 모듈의 책임이 아님. `core/graph.py`(LangGraph 워크플로우) 또는 `core/utils.py`에서 처리. 이 계획서에서는 **메타데이터에 `source` 필드를 확실히 넣는 것**까지만 보장.

---

##### 9. `compute_file_hash(pdf_path: str) -> str`

- **역할**: PDF 파일의 SHA-256 해시값 앞 16자 반환
- **로직**: `hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()[:16]`
- **용도**: 중복 적재 방지. 동일 파일 재실행 시 Skip 판단 기준

---

##### 10. `process_pdf(pdf_path: str, collection_name: str) -> dict`

- **역할**: 단일 PDF에 대한 전체 RAG 파이프라인 통합 실행
- **반환**: `{"collection_name": str, "total_chunks": int, "status": "success" | "skipped" | "error", "message": str}`
- **로직**:
  1. `compute_file_hash(pdf_path)` → `doc_hash` 계산
  2. **중복 체크**: 해당 컬렉션에 동일 `doc_hash`가 이미 존재하면 → `status="skipped"` 반환 (임베딩 API 호출 안 함)
  3. `extract_pages(pdf_path)`
  4. `merge_pages(pages)`
  5. `filter_noise(text)`
  6. `split_by_sections(text)`
  7. `refine_chunks(sections)` — metadata에 `source`(파일명 stem)와 `doc_hash` 주입
  8. `store_chunks(documents, collection_name)`
  9. 결과 딕셔너리 반환
- **정상 흐름**: status="success", total_chunks=저장된 청크 수
- **스킵 흐름**: status="skipped", message="동일 파일이 이미 적재됨 (hash: {doc_hash})"
- **예외 흐름**: 어느 단계든 실패 시 status="error", message=오류 내용

---

### `scripts/chunk_and_embed.py`

#### 역할
인터랙티브 CLI. `data/ncs_pdfs/` 폴더의 PDF를 스캔하고, 사용자 선택에 따라 개별/전체 처리 실행.

#### 함수 명세

##### 1. `scan_pdfs(pdf_dir: str = NCS_PDF_DIR) -> list[Path]`

- **역할**: 폴더 내 `.pdf` 파일 목록 반환 (알파벳순 정렬)
- **예외**: 폴더 미존재 시 오류 메시지 출력 후 빈 리스트 반환

##### 2. `derive_collection_name(pdf_path: Path) -> str`

- **역할**: PDF 파일명에서 컬렉션 이름 자동 생성
- **로직**:
  1. 확장자 제거 → 파일명 stem
  2. 공백·특수문자 → 언더스코어 치환
  3. `"ncs_"` 접두사 추가
  4. ChromaDB 제약 (3~63자, 영숫자 시작/끝) 검증
  5. **한글 파일명으로 인해 제약 위반 시**: `"ncs_{순번:03d}"` (예: `"ncs_001"`) 사용 + 사용자에게 매핑 정보 출력

##### 3. `display_menu(pdf_files: list[Path]) -> None`

> ⚠️ **주의**: PDF 목록·갯수·선택 범위를 절대 하드코딩하지 말 것. `pdf_files` 리스트를 순회하여 동적 렌더링.

- **역할**: PDF 목록 + 선택 옵션 출력
- **출력 형식**:
  ```
  ============================================
    NCS PDF 청킹·임베딩 도구
  ============================================
  발견된 PDF 파일:
    [1] 요구사항확인.pdf
    [2] 데이터베이스구현.pdf
    [3] 화면설계.pdf
  --------------------------------------------
  선택:
    0  → 전체 PDF 처리
    1~3 → 개별 PDF 처리
    q  → 종료
  --------------------------------------------
  입력:
  ```

##### 4. `run_single(pdf_path: Path, collection_name: str) -> None`

- **역할**: 단일 PDF 처리. `core.rag.process_pdf()` 호출 + 진행 상황 출력
- **출력**: 처리 시작/완료 메시지, 총 청크 수, 소요 시간

##### 5. `main() -> None`

- **역할**: 메인 루프
- **로직**:
  1. `scan_pdfs()` 호출
  2. PDF 없으면 `"data/ncs_pdfs/에 PDF 파일을 넣어주세요."` 출력 후 종료
  3. `display_menu()` 출력
  4. `input()` 대기:
     - `"q"` 또는 `"Q"` → `"취소되었습니다."` 출력 후 종료
     - `"0"` → 전체 PDF 순회, 각각 `run_single()` 호출
     - `"1"~"N"` → 해당 번호 PDF에 `run_single()` 호출
     - 범위 외 입력 → `"잘못된 입력입니다."` 출력 후 메뉴 재표시
  5. 처리 완료 후 메뉴 재표시 (반복)

#### 실행 방법

```bash
python scripts/chunk_and_embed.py
```

---

## 예외 처리 및 방어 로직

| 단계 | 예외 상황 | 처리 방법 |
|---|---|---|
| PDF 로드 | 파일 미존재 | `FileNotFoundError` raise |
| PDF 로드 | 손상된 PDF / 암호화 PDF | 해당 파일 건너뛰기 + 경고 로그 |
| 표 추출 | `extract_tables()` 빈 결과 | 정상 처리 (표 없는 페이지) |
| 표 변환 | 헤더 None 또는 빈 표 | 해당 표 건너뛰기 + 경고 로그 |
| 노이즈 필터링 | 키워드 미발견 | 원본 텍스트 그대로 반환 |
| 1차 분할 | NCS 구조 패턴 미매칭 | 전체 텍스트를 단일 섹션으로 처리 (fallback) |
| 2차 분할 | tiktoken 인코딩 오류 | 문자 수 기반 분할로 fallback (chunk_size * 2 글자) |
| 임베딩 | `OPENAI_API_KEY` 미설정 | 명시적 `ValueError` + 안내 메시지 |
| 임베딩 | API rate limit / 네트워크 오류 | 오류 메시지 출력 후 중단 (재시도 없음) |
| ChromaDB | 컬렉션 이름 제약 위반 | `derive_collection_name()` 에서 자동 보정 |
| Retriever | 컬렉션 미존재 | 빈 결과 반환 + 경고 로그 |
| CLI | `data/ncs_pdfs/` 폴더 비어있음 | 안내 메시지 출력 후 종료 |
| CLI | 잘못된 입력 (범위 외 번호, 문자열 등) | `"잘못된 입력입니다."` 출력 후 메뉴 재표시 |
| 중복 적재 | 동일 `doc_hash` 컬렉션에 존재 | `status="skipped"` 반환, 임베딩 API 호출 안 함 |

---

## 의존성 및 환경 설정

### 환경 구축 커맨드 (터미널)

> 프로젝트 루트에서 실행. 이미 `pyproject.toml`에 등록된 패키지(`chromadb`, `langchain-openai` 등)는 재추가 불필요.

```bash
# 신규 의존성 추가 (pyproject.toml 자동 갱신 + uv.lock 갱신)
uv add pandas tabulate

# 전체 의존성 동기화 (팀원 온보딩 시)
uv sync
```

### pyproject.toml 변경사항

기존 의존성에 아래 추가:

```toml
dependencies = [
    # ... 기존 유지 ...
    "pandas>=2.0.0",
    "tabulate>=0.9.0",    # pandas.to_markdown() 내부 의존
]
```

### 환경 변수 (.env)

```
OPENAI_API_KEY=sk-...   # 임베딩 API 호출용 (필수)
```

---

## 참고 자료

- **LangChain Text Splitters**: https://python.langchain.com/docs/how_to/recursive_text_splitter/
- **LangChain OpenAI Embeddings**: https://python.langchain.com/docs/integrations/text_embedding/openai/
- **LangChain Chroma**: https://python.langchain.com/docs/integrations/vectorstores/chroma/
- **ChromaDB Python Guide**: https://docs.trychroma.com/guides
- **pdfplumber**: https://github.com/jsvine/pdfplumber
- **NCS 저작권**: NCS 학습모듈은 교육훈련기관에서 출처 명시 + 교육적 목적으로 활용 가능. 도표/사진/삽화/도면은 국가 저작재산권 미보유 → 원작자 동의 필요

---

## NCS 문서 구조 참고 (청킹 로직 설계 근거)

```
[학습 1: 현행 시스템 분석하기]           ← LEARNING_UNIT_PATTERN (대단위)
  ├── [필요 지식]                      ← SECTION_TYPE_PATTERN (중단위) → 포함
  │     ├── 1-1. 운영체제 개요         ← SUBTITLE_PATTERN (소단위) → 청크 경계
  │     ├── 1-2. DBMS 종류            ← SUBTITLE_PATTERN
  │     └── ...
  ├── [수행 내용]                      ← SECTION_TYPE_PATTERN → 포함
  │     ├── Step 1. ...
  │     └── ...
  ├── [교수·학습 방법]                 ← NOISE → 제거
  └── [평가]                          ← NOISE → 제거

[학습 2: 요구사항 확인하기]
  └── ... (동일 패턴 반복)
```

---

## 체크리스트

- [x] `pyproject.toml`에 `pandas`, `tabulate`, `tiktoken` 의존성 추가 + `uv sync`
- [x] `scripts/` 디렉토리 생성
- [x] `core/rag.py` — 상수/설정 정의 (`MIN_CHUNK_TOKENS`, `EMPTY_SECTION_PLACEHOLDER` 포함)
- [x] `core/rag.py` — `extract_pages()` 구현 (pdfplumber + 표 Markdown 변환)
- [x] `core/rag.py` — `merge_pages()` 구현
- [x] `core/rag.py` — `filter_noise()` 구현 (키워드 기반)
- [x] `core/rag.py` — `split_by_sections()` 구현 (NCS 소제목 패턴 + **짧은 섹션 병합** + **빈 섹션 플레이스홀더**)
- [x] `core/rag.py` — `refine_chunks()` 구현 (RecursiveCharacterTextSplitter + **표 행 분리 방지 세퍼레이터**)
- [x] `core/rag.py` — `get_embeddings()` 구현
- [x] `core/rag.py` — `store_chunks()` 구현 (Chroma.from_documents)
- [x] `core/rag.py` — `get_retriever()` 구현
- [x] `core/rag.py` — `compute_file_hash()` 구현 (SHA-256)
- [x] `core/rag.py` — `process_pdf()` 통합 파이프라인 구현 (**중복 적재 방지** 포함)
- [x] `scripts/chunk_and_embed.py` — 인터랙티브 CLI 구현
- [x] 테스트 PDF 1개로 전체 파이프라인 End-to-End 검증
- [x] 동일 PDF 재실행 시 `skipped` 상태 확인 (중복 방지 검증)
- [x] Retriever로 검색 쿼리 테스트 (콘솔 출력 확인)
- [x] 연관 문서 변경 (아래 섹션 참조)

---

## 연관 문서 변경 사항

본 계획서 구현 완료 후, 아래 문서들의 해당 부분을 갱신해야 함.

### 1. `AGENTS.md`

| 섹션 | 변경 내용 |
|---|---|
| `## 기술 스택` | `pandas / tabulate` 추가 → `Python 3.11 / Streamlit / LangGraph / ChromaDB / OpenAI / Plotly / pandas / uv` |
| `## 디렉토리 규칙` | `scripts/` 항목 추가: `- scripts/ : chunk_and_embed.py(PDF 청킹·임베딩 CLI)` |

### 2. `docs/plans/start_plan.md`

| 섹션 | 변경 내용 |
|---|---|
| `## 프로젝트 디렉토리 구조` (L58) | `scripts/` 폴더 추가 + 하단에 참고 링크 추가: `> 📎 scripts/ 상세 → [RAG 구현 계획](docs/plans/RAG_plan.md)` |
| `## 일별 작업 계획 > Day 1` (L115) | `pyproject.toml`에 `pandas`, `tabulate` 추가된 사항 반영 필요 |

### 3. `pyproject.toml`

```toml
# 아래 2개 의존성 추가
"pandas>=2.0.0",
"tabulate>=0.9.0",
```

### 4. `.gitignore`

- `data/chroma_db/` 항목 **삭제** (Git 추적 대상으로 전환)
- **사유**: Streamlit Cloud 서버는 휘발성(리셋 시 데이터 소멸). 로컬에서 임베딩 완료된 DB를 Git에 포함하면 배포 시 OpenAI API 재호출 비용 0원. NCS PDF 3~4개 기준 DB 크기 10~30MB로 Git 허용 범위 내.

### 5. `start_plan.md`

- `## 주의사항` (L90) 내 `chroma_db/`를 `.gitignore` 처리한다는 언급 → 삭제 또는 수정 필요
- `## 프로젝트 디렉토리 구조` (L73) 내 `chroma_db/` 주석 → `(Git 포함 — 배포 서버 휘발성 대응)` 으로 변경

---

## 구현 기록

- **작업 내용 (2026-04-09)**: `core/rag.py` 및 `scripts/chunk_and_embed.py` 구현 완료.
  - `pyproject.toml`에 `pandas>=2.0.0`, `tabulate>=0.9.0`, `tiktoken>=0.7.0` 추가 후 `uv sync`
  - `core/rag.py`: 10개 함수 전체 구현 (추출/병합/노이즈필터링/1차분할/2차분할/임베딩/적재/검색/해시/파이프라인)
  - `scripts/chunk_and_embed.py`: 인터랙티브 CLI 구현 (동적 목록, 0=전체/N=개별/q=종료)
- **검증 결과** — `test_rag_pipeline.py` 기준 / 대상 PDF: `LM2001020201_23v5_요구사항+확인_20251108.pdf` (77p, 2.2MB):

  | 단계 | 테스트 항목 | 결과 | 비고 |
  |---|---|---|---|
  | [1] SHA-256 해시 | `compute_file_hash()` | `8151540c8bbdf584` | 16자, 정상 ✅ |
  | [2] PDF 추출 | `extract_pages()` | 77페이지, **한글 36,377자** | 한글 깨짐 없음 ✅ |
  | [3] 페이지 병합 | `merge_pages()` | 전체 76,320자, 페이지 마커 삽입 | ✅ |
  | [4] 노이즈 필터링 | `filter_noise()` | 76,320자 → 53,583자 (**29.8% 제거**) | 불필요 섹션 제거 ✅ |
  | [5] 1차 분할 | `split_by_sections()` | **73개 섹션** (빈 섹션 13개 플레이스홀더 포함) | ✅ |
  | [6] 2차 분할 | `refine_chunks()` | **98개 청크** / 최소 105자·최대 977자·평균 425자 | 7개 메타데이터 필드 완전 ✅ |
  | [7] E2E 적재 | `process_pdf()` | **status=success**, 98개 청크 ChromaDB 적재 | `ncs_test_e2e` 컬렉션 ✅ |
  | [8] 중복 방지 | `process_pdf()` 재실행 | **status=skipped** (hash: `8151540c8bbdf584`) | API 재호출 없이 차단 ✅ |
  | [9] Retriever 검색 | `get_retriever().invoke()` | 쿼리 "요구사항 분석의 절차와 방법은?" → **3개 청크 반환** | source·subtitle·pages 메타데이터 포함 ✅ |

- **계획 대비 편차**:
  - `_check_already_embedded()` 내부 헬퍼 함수 추가 — 중복 체크 로직 분리 (가독성 목적, 계획서 스코프 내)
  - `tiktoken` 초기화 실패 시 글자 수 기반 fallback splitter 추가 (방어 로직 강화)
  - **`LEARNING_UNIT_PATTERN` 수정** — 실제 NCS PDF 확인 결과 본문 헤더가 `학습 1 현행 시스템 분석하기` (구분자 없음) 형태임을 확인. 계획서의 `[:.·]` 구분자 필수 패턴 → `[:.·]?` 선택적으로 변경. 오매칭 방지를 위해 제목 시작 `[가-힣]` 필수 조건 추가. (**영향 범위**: `## 상수 및 설정` 코드 블록 내 `LEARNING_UNIT_PATTERN` 값 상이)
  - **`.env` 파일명 오류 수정** — 파일명에 공백이 포함된 `.env ` 상태였음 (`mv` 명령으로 `.env`로 수정). `load_dotenv()`가 `.env`만 탐색하므로 API 키 로드 실패 원인.
