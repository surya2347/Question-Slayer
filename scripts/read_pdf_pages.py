"""
scripts/read_pdf_pages.py
역할: PDF에서 특정 페이지들의 추출 내용(텍스트 + 표)을 파일로 출력하여 원본 분석
"""

import sys
from pathlib import Path
import pandas as pd
import pdfplumber

# 프로젝트 루트를 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def read_pdf_pages_to_txt(pdf_path: str, target_pages: list[int], output_file: str = "output_raw_pages.txt"):
    """
    PDF의 특정 페이지를 읽어 텍스트와 표(Markdown)를 추출하고 파일에 저장합니다.
    """
    if not Path(pdf_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
        return

    print(f"🔍 [{Path(pdf_path).name}] 페이지 {target_pages} 읽기 시작...")
    
    results = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_p = len(pdf.pages)
        
        for p_num in sorted(target_pages):
            if p_num < 1 or p_num > total_p:
                print(f"⚠️ 페이지 {p_num}은 범위를 벗어남 (전체 {total_p}p). 건너뜁니다.")
                continue
            
            page = pdf.pages[p_num - 1]
            
            # core/rag.py의 추출 로직 복사
            raw_text = page.extract_text() or ""
            
            # 표 추출 및 Markdown 변환
            md_tables = []
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                try:
                    header = [str(h) if h is not None else "" for h in table[0]]
                    rows = [[str(cell) if cell is not None else "" for cell in row] for row in table[1:]]
                    df = pd.DataFrame(rows, columns=header)
                    md_table = df.to_markdown(index=False)
                    md_tables.append(md_table)
                except Exception as e:
                    print(f"⚠️ [페이지 {p_num}] 표 변환 실패: {e}")

            combined = raw_text
            if md_tables:
                combined += "\n\n[발견된 표]\n" + "\n\n".join(md_tables) + "\n"
            
            results.append((p_num, combined))

    # 파일 기록
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"PDF Raw Extraction Test Output\n")
        f.write(f"Target File: {pdf_path}\n")
        f.write("=" * 60 + "\n\n")
        
        for p_num, content in results:
            f.write(f"--- [PAGE {p_num}] ---\n")
            f.write(content)
            f.write("\n\n" + "="*40 + "\n\n")

    print(f"✅ 추출 완료: {output_file} 파일을 확인하세요.")

if __name__ == "__main__":
    TEST_PDF = "data/ncs_pdfs/LM2001020201_23v5_요구사항+확인_20251108.pdf"
    
    # 실제로 까볼 페이지
    PAGES_TO_SCAN = [16, 17,28, 39, 42, 43, 44] 
    
    read_pdf_pages_to_txt(TEST_PDF, PAGES_TO_SCAN)
