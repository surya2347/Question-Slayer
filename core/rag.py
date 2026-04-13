"""
core/rag.py
역할: RAG(Retrieval-Augmented Generation) 파이프라인 전체
  - pdfplumber로 NCS PDF 텍스트 + 텍스트 기반 표 추출
  - 키워드 기반 노이즈 필터링 (교수학습방법, 평가, 개발이력 섹션 제거)
  - 하이브리드 청킹: 1차 NCS 소제목 단위 분할 → 2차 500 tokens 초과 시 RecursiveCharacterTextSplitter
  - OpenAI text-embedding-3-small로 임베딩 후 ChromaDB 과목별 컬렉션 저장
  - SHA-256 해시 기반 중복 적재 방지
  - 과목별 컬렉션에서 유사 청크 검색 Retriever 제공
"""

import hashlib
import json
import logging
import re
import warnings
from pathlib import Path

import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# 로거 설정
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 상수 및 설정
# ---------------------------------------------------------------------------
CHROMA_DB_PATH: str = "data/chroma_db"
NCS_PDF_DIR: str = "data/ncs_pdfs"
EMBEDDING_MODEL: str = "text-embedding-3-small"
MAX_CHUNK_TOKENS: int = 500
CHUNK_OVERLAP_TOKENS: int = 50
MIN_CHUNK_TOKENS: int = 50  # 이 값 미만인 섹션은 이전(또는 다음) 섹션에 병합

# 도표·그림 제거 후 빈 섹션에 삽입할 플레이스홀더
EMPTY_SECTION_PLACEHOLDER: str = (
    "[해당 섹션은 도표·그림 위주 콘텐츠로 구성되어 텍스트 정보가 제외되었습니다.]"
)

# NCS 문서 구조 감지용 정규식
RE_MAJOR_PATTERN: str = r"^[ \t]*학\s*습\s*(\d+)\.?\s*([가-힣a-zA-Z\s]+)"
RE_SUB_NUM_PATTERN: str = r"^[ \t]*(\d+)-(\d+)\.\s*$"
RE_SECTION_PATTERN: str = r"^[ \t]*(필\s*요\s*지\s*식|수\s*행\s*내\s*용|평\s*가)\s*/?\s*"
RE_SKIP_START_PATTERN: str = r"^[ \t]*(교수\s*[·・]?\s*학습\s*방법|개발\s*이력)"

# 페이지 경계 마커 (내부 처리용, 최종 청크에서 제거)
PAGE_MARKER_TEMPLATE: str = "\n<!--PAGE:{page_num}-->\n"
PAGE_MARKER_REGEX: str = r"<!--PAGE:(\d+)-->"


# ---------------------------------------------------------------------------
# 1. PDF 페이지별 텍스트 + 표 추출
# ---------------------------------------------------------------------------
def extract_pages(pdf_path: str) -> list[dict]:
    """
    PDF에서 페이지별 텍스트와 텍스트 기반 표를 추출한다.

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        [{"page": int(1-indexed), "text": str}, ...]

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 경우
    """
    # 파일 존재 확인
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    pages: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1  # 1-indexed
            try:
                # 텍스트 추출 (None이면 빈 문자열로 처리)
                raw_text: str = page.extract_text() or ""

                # 표 추출 및 Markdown 변환
                md_tables: list[str] = []
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        # 헤더만 있거나 빈 표 → 건너뜀
                        continue
                    try:
                        header = table[0]
                        rows = table[1:]
                        # None 값 처리: 빈 문자열로 교체
                        header = [str(h) if h is not None else "" for h in header]
                        cleaned_rows = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in rows
                        ]
                        df = pd.DataFrame(cleaned_rows, columns=header)
                        md_table = df.to_markdown(index=False)
                        md_tables.append(md_table)
                    except Exception as e:
                        # 표 변환 실패 시 해당 표만 건너뜀
                        logger.warning(f"[페이지 {page_num}] 표 변환 실패 (건너뜀): {e}")

                # 텍스트 + 표 Markdown 결합
                combined = raw_text
                if md_tables:
                    combined += "\n\n" + "\n\n".join(md_tables) + "\n\n"

                pages.append({"page": page_num, "text": combined})

            except Exception as e:
                # 페이지 파싱 오류 시 해당 페이지 건너뜀
                logger.warning(f"[페이지 {page_num}] 파싱 오류 (건너뜀): {e}")

    # MVP 범위에서 모든 NCS PDF에 동일 적용하는 임시 규칙: 앞 12페이지 하드 스킵
    if len(pages) > 12:
        pages = pages[12:]

    return pages


# ---------------------------------------------------------------------------
# 2. NCS PDF 공통 잡음 제거
# ---------------------------------------------------------------------------
def clean_ncs_junk(text: str) -> str:
    """
    NCS PDF에서 반복적으로 등장하는 공통 잡음을 제거한다.

    Args:
        text: merge_pages() 이후 전체 텍스트

    Returns:
        잡음 제거 후 텍스트
    """
    cleaned = text

    patterns = [
        (r"\(cid:\d+\)", ""),
        (r"출처\s*:.*?\(\d{4}\).*?p\.\s*\d+", ""),
        (r"\[그림\s*\d+-\d+\]", ""),
        (r"www\.ncs\.go\.kr", ""),
        (r"^\s*\d+\s*$", "", re.MULTILINE),
        (r"\n{3,}", "\n\n"),
    ]

    for pattern_info in patterns:
        pattern, replacement, *flags = pattern_info
        regex_flags = flags[0] if flags else 0
        cleaned = re.sub(pattern, replacement, cleaned, flags=regex_flags)

    return cleaned


def filter_noise(text: str) -> str:
    """기존 호출부 호환을 위해 clean_ncs_junk()를 위임 호출한다."""
    return clean_ncs_junk(text)


# ---------------------------------------------------------------------------
# 3. 페이지별 텍스트 → 하나의 문자열로 병합 (페이지 마커 삽입)
# ---------------------------------------------------------------------------
def merge_pages(pages: list[dict]) -> str:
    """
    페이지별 텍스트를 하나로 병합한다.
    페이지 경계에 <!--PAGE:N--> 마커를 삽입하여 이후 페이지 번호 추적에 사용.

    Args:
        pages: extract_pages()의 반환값

    Returns:
        마커 포함 전체 텍스트 문자열
    """
    parts: list[str] = []
    for page in pages:
        marker = PAGE_MARKER_TEMPLATE.format(page_num=page["page"])
        parts.append(marker + page["text"])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 4. NCS 소제목 단위 1차 분할 + 짧은 섹션 병합 + 빈 섹션 플레이스홀더
# ---------------------------------------------------------------------------
def split_by_sections(text: str) -> list[dict]:
    """
    NCS 문서 구조에 따라 상태머신 기반으로 1차 분할한다.
    - 연속 학습 목록은 major_candidates에 버퍼링
    - N-M. 번호-only 줄이 등장하면 해당 N의 학습 라인을 current_major로 확정
    - N-M. 다음 줄이 즉시 일반 문자열일 때만 소단원으로 확정

    빈 섹션은 EMPTY_SECTION_PLACEHOLDER로 대체.
    MIN_CHUNK_TOKENS 미만 섹션은 이전 섹션에 병합.

    Args:
        text: clean_ncs_junk()의 반환값

    Returns:
        [{"learning_unit": str, "section_type": str,
          "subtitle": str, "content": str, "pages": list[int]}, ...]
    """
    sections: list[dict] = []

    re_major = re.compile(RE_MAJOR_PATTERN)
    re_sub_num = re.compile(RE_SUB_NUM_PATTERN)
    re_section = re.compile(RE_SECTION_PATTERN)
    re_skip_start = re.compile(RE_SKIP_START_PATTERN)
    re_page = re.compile(PAGE_MARKER_REGEX)

    current_major = "전체"
    current_section = "필요 지식"
    current_sub = "전체"
    pending_sub_num: str | None = None
    major_candidates: dict[int, str] = {}
    content_buf: list[str] = []
    skip_mode = False

    def flush() -> None:
        if not content_buf:
            return

        joined = "\n".join(content_buf)
        raw_pages = _extract_pages_from_text(joined, re_page)
        clean = re_page.sub("", joined).strip()
        if not clean:
            # 페이지 마커만 있는 버퍼는 실제 청크로 저장하지 않는다.
            content_buf.clear()
            return

        sections.append(
            {
                "learning_unit": current_major,
                "section_type": current_section,
                "subtitle": current_sub,
                "content": clean,
                "pages": raw_pages,
            }
        )
        content_buf.clear()

    lines = text.splitlines()

    for raw_line in lines:
        line = raw_line
        stripped = line.strip()

        while True:
            major_match = re_major.match(line)
            section_match = re_section.match(line)
            sub_num_match = re_sub_num.match(line)
            skip_start_match = re_skip_start.match(line)

            if skip_start_match:
                flush()
                skip_mode = True
                pending_sub_num = None
                break

            if skip_mode:
                if major_match or section_match or sub_num_match:
                    skip_mode = False
                    continue
                break

            if pending_sub_num is not None:
                if not stripped:
                    pending_sub_num = None
                    break

                if major_match or section_match or sub_num_match or skip_start_match:
                    pending_sub_num = None
                    continue

                current_sub = f"{pending_sub_num}. {stripped}"
                pending_sub_num = None
                break

            if major_match:
                flush()
                major_num = int(major_match.group(1))
                major_title = major_match.group(2).strip()
                major_candidates[major_num] = f"학습 {major_num}. {major_title}"
                break

            if sub_num_match:
                flush()
                major_num = int(sub_num_match.group(1))
                pending_sub_num = f"{major_num}-{sub_num_match.group(2)}"
                if major_num in major_candidates:
                    current_major = major_candidates[major_num]
                elif current_major.startswith(f"학습 {major_num}"):
                    current_major = current_major
                else:
                    current_major = f"학습 {major_num} (제목 미확인)"
                major_candidates.clear()
                break

            if section_match:
                flush()
                current_section = _normalize_section_name(section_match.group(1))
                pending_sub_num = None
                break

            content_buf.append(line)
            break

    if pending_sub_num is not None:
        pending_sub_num = None

    flush()

    if not sections:
        logger.warning("NCS 구조 패턴 미매칭 → 전체 텍스트를 단일 섹션으로 처리")
        raw_pages = _extract_pages_from_text(text, re_page)
        clean = re_page.sub("", text).strip()
        clean = clean if clean else EMPTY_SECTION_PLACEHOLDER
        sections = [
            {
                "learning_unit": "전체",
                "section_type": "필요 지식",
                "subtitle": "전체",
                "content": clean,
                "pages": raw_pages,
            }
        ]

    # 짧은 섹션 병합: MIN_CHUNK_TOKENS 미만인 섹션을 이전 섹션에 병합
    sections = _merge_short_sections(sections)

    return sections


def _extract_pages_from_text(text: str, re_page: re.Pattern) -> list[int]:
    """텍스트에서 <!--PAGE:N--> 마커를 찾아 페이지 번호 목록 반환"""
    return [int(m.group(1)) for m in re_page.finditer(text)]


def _normalize_section_name(section: str) -> str:
    """중단원 표기를 기존 메타데이터 형식으로 정규화한다."""
    compact = re.sub(r"\s+", "", section)
    if compact == "필요지식":
        return "필요 지식"
    if compact == "수행내용":
        return "수행 내용"
    return compact


def _count_tokens_approx(text: str) -> int:
    """
    토큰 수 근사 계산 (한국어 포함 텍스트: 글자 수 / 1.5 근사).
    tiktoken 없이도 동작하기 위한 보조 함수.
    """
    # 한국어는 1글자 ≈ 0.5~1토큰, 영어는 1단어 ≈ 1토큰
    # 보수적으로 글자 수 / 1.5 사용
    return max(1, len(text) // 2)


def _merge_short_sections(sections: list[dict]) -> list[dict]:
    """
    MIN_CHUNK_TOKENS 미만인 섹션을 이전 섹션에 병합한다.
    첫 번째 섹션이 짧으면 다음 섹션에 병합.
    """
    if not sections:
        return sections

    merged: list[dict] = []
    pending: dict | None = None  # 앞 섹션이 짧아서 다음에 붙일 대기 섹션

    for sec in sections:
        token_count = _count_tokens_approx(sec["content"])

        if pending is not None:
            # 첫 번째 섹션이 짧았던 경우: 다음 섹션 앞에 붙임
            sec = sec.copy()
            sec["content"] = (
                sec["content"]
                + f"\n\n--- {pending['subtitle']} ---\n\n"
                + pending["content"]
            )
            sec["pages"] = sorted(set(sec["pages"] + pending["pages"]))
            pending = None

        if token_count < MIN_CHUNK_TOKENS and merged:
            # 이전 섹션에 병합
            prev = merged[-1]
            prev["content"] += (
                f"\n\n--- {sec['subtitle']} ---\n\n" + sec["content"]
            )
            prev["pages"] = sorted(set(prev["pages"] + sec["pages"]))
        elif token_count < MIN_CHUNK_TOKENS and not merged:
            # 이전 섹션 없음 → 다음 섹션에 붙이기 위해 보류
            pending = sec
        else:
            merged.append(dict(sec))

    # 마지막까지 pending이 남은 경우 (전체가 1개 섹션이고 짧은 경우)
    if pending is not None:
        if merged:
            merged[-1]["content"] += (
                f"\n\n--- {pending['subtitle']} ---\n\n" + pending["content"]
            )
            merged[-1]["pages"] = sorted(set(merged[-1]["pages"] + pending["pages"]))
        else:
            merged.append(pending)

    return merged


# ---------------------------------------------------------------------------
# 5. 500 tokens 초과 섹션 RecursiveCharacterTextSplitter로 2차 분할
# ---------------------------------------------------------------------------
def refine_chunks(
    sections: list[dict],
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    source: str = "",
    doc_hash: str = "",
) -> list[Document]:
    """
    섹션 리스트를 LangChain Document 리스트로 변환한다.
    500 tokens 초과 섹션은 RecursiveCharacterTextSplitter로 2차 분할.
    표 행이 분할 경계에서 잘리지 않도록 '|\\n' 세퍼레이터 우선 적용.

    Args:
        sections: split_by_sections()의 반환값
        max_tokens: 최대 청크 토큰 수 (기본 500)
        overlap_tokens: 오버랩 토큰 수 (기본 50)
        source: PDF 파일명 (과목명). process_pdf()에서 주입
        doc_hash: SHA-256 해시 앞 16자. process_pdf()에서 주입

    Returns:
        list[Document] — ChromaDB 적재용 LangChain Document 리스트
    """
    # tiktoken 기반 splitter 생성 (실패 시 글자 수 기반 fallback)
    try:
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4",
            chunk_size=max_tokens,
            chunk_overlap=overlap_tokens,
            # '|\n' 우선: Markdown 테이블 행 경계에서 분할하여 표 행 중간 절단 방지
            separators=["\n\n", "\n", "|\n", ". ", " "],
        )
    except Exception as e:
        logger.warning(f"tiktoken 초기화 실패, 글자 수 기반 splitter로 fallback: {e}")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens * 2,  # 글자 수 기준은 토큰보다 여유 있게
            chunk_overlap=overlap_tokens * 2,
            separators=["\n\n", "\n", "|\n", ". ", " "],
        )

    documents: list[Document] = []

    for section in sections:
        content = section["content"]
        pages_str = json.dumps(section["pages"], ensure_ascii=False)

        # 공통 메타데이터 (source, doc_hash는 호출부에서 주입)
        base_metadata = {
            "source": source,
            "doc_hash": doc_hash,
            "learning_unit": section["learning_unit"],
            "section_type": section["section_type"],
            "subtitle": section["subtitle"],
            "pages": pages_str,
        }

        # 토큰 수 근사 계산
        approx_tokens = _count_tokens_approx(content)

        if approx_tokens <= max_tokens:
            # 청크 분할 불필요
            metadata = {**base_metadata, "chunk_index": 0}
            documents.append(Document(page_content=content, metadata=metadata))
        else:
            # 2차 분할
            try:
                chunks = splitter.split_text(content)
            except Exception as e:
                logger.warning(f"분할 실패, 단일 청크로 처리: {e}")
                chunks = [content]

            for idx, chunk in enumerate(chunks):
                metadata = {**base_metadata, "chunk_index": idx}
                documents.append(Document(page_content=chunk, metadata=metadata))

    return documents


# ---------------------------------------------------------------------------
# 6. OpenAI 임베딩 인스턴스 반환
# ---------------------------------------------------------------------------
def get_embeddings() -> OpenAIEmbeddings:
    """
    OpenAI 임베딩 모델 인스턴스를 반환한다.

    Returns:
        OpenAIEmbeddings 인스턴스

    Raises:
        ValueError: OPENAI_API_KEY 미설정 시
    """
    import os

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 OPENAI_API_KEY=sk-... 를 추가하세요."
        )
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


# ---------------------------------------------------------------------------
# 7. ChromaDB 컬렉션에 Document 저장
# ---------------------------------------------------------------------------
def store_chunks(documents: list[Document], collection_name: str) -> Chroma:
    """
    Document 리스트를 ChromaDB 과목별 컬렉션에 임베딩 + 저장한다.

    Args:
        documents: refine_chunks()의 반환값
        collection_name: ChromaDB 컬렉션 이름 (과목별 1개)

    Returns:
        Chroma 인스턴스

    Raises:
        ValueError: API 키 오류
    """
    embeddings = get_embeddings()

    # ChromaDB 저장 경로를 절대 경로로 변환
    db_path = str(Path(CHROMA_DB_PATH).resolve())

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name=collection_name,
    )
    return vectorstore


# ---------------------------------------------------------------------------
# 8. 과목별 Retriever 반환
# ---------------------------------------------------------------------------
def get_retriever(collection_name: str, top_k: int = 5):
    """
    과목별 ChromaDB 컬렉션에서 유사 청크를 검색하는 Retriever를 반환한다.

    스코프 경계: 중복 제거(Context Merging), 출처 포맷팅은 core/graph.py 또는
    core/utils.py의 책임. 이 함수는 메타데이터에 source 필드를 보장하는 것까지만 담당.

    Args:
        collection_name: 검색 대상 컬렉션 이름
        top_k: 반환할 유사 청크 수 (기본 5)

    Returns:
        VectorStoreRetriever 인스턴스

    사용 예:
        retriever = get_retriever("ncs_요구사항확인")
        docs = retriever.invoke("운영체제의 종류는?")
    """
    db_path = str(Path(CHROMA_DB_PATH).resolve())

    try:
        vectorstore = Chroma(
            persist_directory=db_path,
            collection_name=collection_name,
            embedding_function=get_embeddings(),
        )
        return vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k},
        )
    except Exception as e:
        logger.warning(f"컬렉션 '{collection_name}' Retriever 생성 실패: {e}")
        # 빈 결과를 반환하는 더미 Retriever 대신 None 반환 후 호출부에서 처리
        return None


# ---------------------------------------------------------------------------
# 9. PDF 파일 SHA-256 해시 계산
# ---------------------------------------------------------------------------
def compute_file_hash(pdf_path: str) -> str:
    """
    PDF 파일의 SHA-256 해시값 앞 16자를 반환한다.
    중복 적재 방지에 사용: 동일 파일 재실행 시 Skip 판단 기준.

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        SHA-256 해시값 앞 16자 문자열
    """
    return hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 10. 전체 RAG 파이프라인 통합 실행
# ---------------------------------------------------------------------------
def process_pdf(pdf_path: str, collection_name: str) -> dict:
    """
    단일 PDF에 대한 전체 RAG 파이프라인을 실행한다.

    흐름:
        해시 계산 → 중복 체크 → 텍스트 추출 → 페이지 병합 → 공통 잡음 제거
        → 1차 분할 → 2차 분할 → 임베딩 + ChromaDB 적재

    Args:
        pdf_path: 처리할 PDF 파일 경로
        collection_name: ChromaDB 컬렉션 이름

    Returns:
        {
            "collection_name": str,
            "total_chunks": int,
            "status": "success" | "skipped" | "error",
            "message": str,
        }
    """
    result = {
        "collection_name": collection_name,
        "total_chunks": 0,
        "status": "error",
        "message": "",
    }

    try:
        # 1. 해시 계산
        doc_hash = compute_file_hash(pdf_path)
        source = Path(pdf_path).stem  # 파일명 (확장자 제외)

        # 2. 중복 체크: 동일 doc_hash가 이미 컬렉션에 존재하면 Skip
        if _check_already_embedded(collection_name, doc_hash):
            result["status"] = "skipped"
            result["message"] = f"동일 파일이 이미 적재됨 (hash: {doc_hash})"
            return result

        # 3. PDF 텍스트 + 표 추출
        pages = extract_pages(pdf_path)
        if not pages:
            result["message"] = "PDF에서 텍스트를 추출하지 못했습니다."
            return result

        # 4. 페이지 병합
        merged_text = merge_pages(pages)

        # 5. 공통 잡음 제거
        filtered_text = clean_ncs_junk(merged_text)

        # 6. 1차 분할 (NCS 소제목 단위)
        sections = split_by_sections(filtered_text)
        if not sections:
            result["message"] = "청킹 결과가 비어있습니다."
            return result

        # 7. 2차 분할 + Document 생성 (source, doc_hash 주입)
        documents = refine_chunks(
            sections,
            source=source,
            doc_hash=doc_hash,
        )
        if not documents:
            result["message"] = "Document 생성 결과가 비어있습니다."
            return result

        # 8. ChromaDB 임베딩 + 저장
        store_chunks(documents, collection_name)

        result["status"] = "success"
        result["total_chunks"] = len(documents)
        result["message"] = f"{len(documents)}개 청크 적재 완료"

    except FileNotFoundError as e:
        result["message"] = str(e)
    except ValueError as e:
        # API 키 오류 등
        result["message"] = str(e)
    except Exception as e:
        result["message"] = f"파이프라인 실행 오류: {e}"
        logger.exception(f"process_pdf 예외 발생: {pdf_path}")

    return result


def _check_already_embedded(collection_name: str, doc_hash: str) -> bool:
    """
    ChromaDB 컬렉션에 동일 doc_hash를 가진 문서가 존재하는지 확인한다.

    Args:
        collection_name: 확인할 컬렉션 이름
        doc_hash: 비교할 해시값

    Returns:
        True면 이미 적재됨 (Skip 대상), False면 신규 적재 필요
    """
    db_path = str(Path(CHROMA_DB_PATH).resolve())
    try:
        # 컬렉션이 없으면 Chroma 생성 시 예외 발생 → False 반환
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            vectorstore = Chroma(
                persist_directory=db_path,
                collection_name=collection_name,
                # 중복 체크만 하므로 임베딩 함수는 None (get이나 peek만 사용)
                embedding_function=None,
            )
        # doc_hash로 필터링하여 1개라도 있으면 이미 적재된 것
        existing = vectorstore.get(
            where={"doc_hash": doc_hash},
            limit=1,
        )
        return len(existing.get("ids", [])) > 0
    except Exception:
        # 컬렉션 미존재 등 모든 예외 → 신규 적재로 처리
        return False
