"""
scripts/chunk_and_embed.py
역할: NCS PDF 청킹·임베딩 인터랙티브 CLI
  - data/ncs_pdfs/ 폴더의 PDF 파일을 동적으로 스캔
  - 0 입력 시 전체 처리, 번호 입력 시 개별 처리, q 입력 시 종료
  - core.rag.process_pdf()를 호출하여 파이프라인 실행

실행 방법:
    python scripts/chunk_and_embed.py
"""

import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (스크립트 직접 실행 시 core 임포트 가능하게)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.rag import NCS_PDF_DIR, process_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# 1. PDF 파일 목록 스캔
# ---------------------------------------------------------------------------
def scan_pdfs(pdf_dir: str = NCS_PDF_DIR) -> list[Path]:
    """
    지정 폴더 내 .pdf 파일 목록을 알파벳순으로 반환한다.

    Args:
        pdf_dir: 스캔할 폴더 경로 (기본: data/ncs_pdfs)

    Returns:
        Path 객체 리스트 (정렬됨)
    """
    target = Path(pdf_dir)

    if not target.exists():
        print(f"[오류] 폴더가 존재하지 않습니다: {target}")
        return []

    pdf_files = sorted(target.glob("*.pdf"))
    return pdf_files


# ---------------------------------------------------------------------------
# 2. PDF 파일명 → ChromaDB 컬렉션 이름 자동 생성
# ---------------------------------------------------------------------------
def derive_collection_name(pdf_path: Path, index: int) -> str:
    """
    PDF 파일명에서 ChromaDB 컬렉션 이름을 자동 생성한다.

    ChromaDB 제약: 3~63자, 영숫자·점·대시·언더스코어만 허용, 영숫자로 시작/끝.
    한글 파일명 등 제약 위반 시 ncs_{순번:03d} 형태로 자동 보정.

    Args:
        pdf_path: PDF 파일 Path 객체
        index: 파일 목록 순번 (1-indexed, 보정 이름 생성에 사용)

    Returns:
        유효한 ChromaDB 컬렉션 이름 문자열
    """
    import re

    stem = pdf_path.stem  # 확장자 제외 파일명

    # 공백·특수문자 → 언더스코어 치환
    sanitized = re.sub(r"[^\w]", "_", stem, flags=re.ASCII)
    candidate = f"ncs_{sanitized}"

    # ChromaDB 이름 제약 검증
    valid_pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,61}[a-zA-Z0-9]$")
    if valid_pattern.match(candidate) and len(candidate) <= 63:
        return candidate

    # 제약 위반(한글 등) → 순번 기반 이름으로 보정
    fallback = f"ncs_{index:03d}"
    print(f"  [알림] 파일명 '{stem}' → 컬렉션명 자동 보정: '{fallback}'")
    return fallback


# ---------------------------------------------------------------------------
# 3. 메뉴 출력
# ---------------------------------------------------------------------------
def display_menu(pdf_files: list[Path]) -> None:
    """
    PDF 목록과 선택 옵션을 동적으로 출력한다.
    목록·갯수·선택 범위는 pdf_files 리스트를 순회하여 결정 (하드코딩 없음).

    Args:
        pdf_files: scan_pdfs()의 반환값
    """
    print()
    print("=" * 44)
    print("  NCS PDF 청킹·임베딩 도구")
    print("=" * 44)
    print("발견된 PDF 파일:")
    for i, path in enumerate(pdf_files, start=1):
        print(f"  [{i}] {path.name}")
    print("-" * 44)
    print("선택:")
    print("  0  → 전체 PDF 처리")
    print(f"  1~{len(pdf_files)} → 개별 PDF 처리")
    print("  q  → 종료")
    print("-" * 44)
    print("입력: ", end="", flush=True)


# ---------------------------------------------------------------------------
# 4. 단일 PDF 처리 실행 + 결과 출력
# ---------------------------------------------------------------------------
def run_single(pdf_path: Path, collection_name: str) -> None:
    """
    단일 PDF에 대해 process_pdf()를 호출하고 결과를 출력한다.

    Args:
        pdf_path: 처리할 PDF Path 객체
        collection_name: 저장할 ChromaDB 컬렉션 이름
    """
    print(f"\n  ▶ 처리 시작: {pdf_path.name}")
    print(f"    컬렉션명   : {collection_name}")

    start = time.time()
    result = process_pdf(str(pdf_path), collection_name)
    elapsed = time.time() - start

    status = result.get("status", "error")
    msg = result.get("message", "")
    chunks = result.get("total_chunks", 0)

    if status == "success":
        print(f"  ✅ 완료: {chunks}개 청크 적재 | 소요: {elapsed:.1f}초")
    elif status == "skipped":
        print(f"  ⏭  스킵: {msg}")
    else:
        print(f"  ❌ 오류: {msg}")


# ---------------------------------------------------------------------------
# 5. 메인 루프
# ---------------------------------------------------------------------------
def main() -> None:
    """
    인터랙티브 CLI 메인 루프.
    PDF 스캔 → 메뉴 표시 → 입력 대기 → 처리 → 반복
    q 입력 시 종료.
    """
    # PDF 파일 스캔
    pdf_files = scan_pdfs()

    if not pdf_files:
        print(f"\n[안내] {NCS_PDF_DIR}/ 폴더에 PDF 파일이 없습니다.")
        print("      NCS 학습모듈 PDF를 해당 폴더에 넣은 후 다시 실행해 주세요.")
        return

    # 컬렉션 이름 미리 계산 (파일명 → 컬렉션명 매핑)
    collection_map: dict[int, tuple[Path, str]] = {}
    for i, pdf_path in enumerate(pdf_files, start=1):
        col_name = derive_collection_name(pdf_path, i)
        collection_map[i] = (pdf_path, col_name)

    # 메인 루프
    while True:
        display_menu(pdf_files)

        try:
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n취소되었습니다.")
            break

        if user_input.lower() == "q":
            print("\n취소되었습니다.")
            break

        if user_input == "0":
            # 전체 처리
            print(f"\n  전체 {len(pdf_files)}개 PDF 처리를 시작합니다.")
            for i in range(1, len(pdf_files) + 1):
                pdf_path, col_name = collection_map[i]
                run_single(pdf_path, col_name)
            print("\n  전체 처리 완료.")

        elif user_input.isdigit():
            idx = int(user_input)
            if 1 <= idx <= len(pdf_files):
                pdf_path, col_name = collection_map[idx]
                run_single(pdf_path, col_name)
            else:
                print(f"\n  잘못된 입력입니다. (1~{len(pdf_files)} 또는 0, q 를 입력)")

        else:
            print(f"\n  잘못된 입력입니다. (1~{len(pdf_files)} 또는 0, q 를 입력)")


# ---------------------------------------------------------------------------
# 스크립트 진입점
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
