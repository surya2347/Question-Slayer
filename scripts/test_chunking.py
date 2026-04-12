"""
scripts/test_chunking.py
역할: 임베딩 직전의 청킹 상태를 눈으로 직접 확인하기 위한 테스트 스크립트

실행 방법:
    uv run python scripts/test_chunking.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.rag import compute_file_hash, extract_pages, filter_noise, merge_pages, refine_chunks, split_by_sections

def test_chunking_for_file(pdf_path: str, output_file: str = "test_chunk_output.txt"):
    # 파이프라인 시뮬레이션
    print(f"[{Path(pdf_path).name}] 처리 및 파일 기록 중... (저장 파일: {output_file})")
    
    # 임베딩에 사용하는 값 도출
    doc_hash = compute_file_hash(pdf_path)
    source = Path(pdf_path).stem
    
    pages = extract_pages(pdf_path)
    merged_text = merge_pages(pages)
    filtered_text = filter_noise(merged_text)
    sections = split_by_sections(filtered_text)
    documents = refine_chunks(sections, source=source, doc_hash=doc_hash)
    
    total_chunks = len(documents)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"📄 대상 파일: {Path(pdf_path).name}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"✅ 완료: 총 {total_chunks}개의 청크가 생성되었습니다.\n\n")
        f.write("👇 [생성된 청크 내용] 👇\n")
        f.write("-" * 60 + "\n")
        
        for i, doc in enumerate(documents, start=1):
            meta = doc.metadata
            f.write(f"\n📦 [청크 {i}/{total_chunks}]\n")
            f.write(f"🏷️ 학습단위: {meta.get('learning_unit', 'N/A')}\n")
            f.write(f"🏷️ 섹션타입: {meta.get('section_type', 'N/A')}\n")
            f.write(f"🏷️ 소제목  : {meta.get('subtitle', 'N/A')}\n")
            f.write(f"📄 출처페이지: {meta.get('pages', 'N/A')}\n")
            f.write(f"--- [본문 내용] ---\n")
            
            # 파일 출력이므로 내용 전체를 기록합니다
            f.write(doc.page_content.strip() + "\n")
            f.write("-" * 60 + "\n")
            
    print("✅ 파일 저장이 완료되었습니다!")
    print("\n테스트 종료.")

if __name__ == "__main__":
    test_pdf_path = "data/ncs_pdfs/LM2001020201_23v5_요구사항+확인_20251108.pdf"
    
    if not Path(test_pdf_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {test_pdf_path}")
    else:
        test_chunking_for_file(test_pdf_path)
