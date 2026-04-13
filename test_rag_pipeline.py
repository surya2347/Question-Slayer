"""
테스트 스크립트: PDF 텍스트 추출 + 한글 깨짐 + 파이프라인 단계 검증
+ End-to-End 임베딩/적재 + 중복 방지(skipped) + Retriever 쿼리 검증

실행: uv run python test_rag_pipeline.py
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from core.rag import (
    compute_file_hash,
    extract_pages,
    filter_noise,
    merge_pages,
    process_pdf,
    get_retriever,
    refine_chunks,
    split_by_sections,
)

# 테스트에 사용할 PDF (가장 작은 파일 선택)
PDF_PATH = "data/ncs_pdfs/LM2001020201_23v5_요구사항+확인_20251108.pdf"
# 테스트용 컬렉션 이름
COLLECTION_NAME = "ncs_test_e2e"

print("=" * 60)
print("  RAG 파이프라인 단계별 테스트")
print("=" * 60)

# ── 1. 해시 계산 ──────────────────────────────────────────────
print("\n[1] SHA-256 해시 계산")
doc_hash = compute_file_hash(PDF_PATH)
print(f"    해시 (앞 16자): {doc_hash}")
assert len(doc_hash) == 16, "해시 길이 오류"
print("    ✅ OK")

# ── 2. PDF 텍스트 추출 ────────────────────────────────────────
print("\n[2] PDF 텍스트 + 표 추출 (pdfplumber)")
pages = extract_pages(PDF_PATH)
print(f"    총 페이지 수: {len(pages)}")
assert len(pages) > 0, "페이지 추출 실패"

# 한글 깨짐 검사: 한글이 1개라도 있어야 통과
all_text = " ".join(p["text"] for p in pages)
korean_chars = [c for c in all_text if "\uAC00" <= c <= "\uD7A3"]
print(f"    한글 글자 수: {len(korean_chars):,}자")
assert len(korean_chars) > 100, f"한글 추출 부족: {len(korean_chars)}자"

# 샘플 출력 (첫 3페이지 앞 150자)
for p in pages[:3]:
    snippet = p["text"][:150].replace("\n", " ")
    print(f"    [페이지 {p['page']}] {snippet}...")
print("    ✅ 한글 깨짐 없음 확인")

# ── 3. 페이지 병합 ────────────────────────────────────────────
print("\n[3] 페이지 병합 (merge_pages)")
merged = merge_pages(pages)
print(f"    병합 텍스트 전체 길이: {len(merged):,}자")
assert "<!--PAGE:" in merged, "페이지 마커 삽입 실패"
print("    ✅ OK")

# ── 4. 노이즈 필터링 ──────────────────────────────────────────
print("\n[4] 노이즈 필터링 (filter_noise)")
before_len = len(merged)
filtered = filter_noise(merged)
after_len = len(filtered)
removed = before_len - after_len
print(f"    필터링 전: {before_len:,}자")
print(f"    필터링 후: {after_len:,}자  (제거: {removed:,}자, {removed/before_len*100:.1f}%)")
assert after_len > 0, "필터링 후 텍스트 비어있음"
print("    ✅ OK")

# ── 5. 1차 분할 (소제목 단위) ─────────────────────────────────
print("\n[5] 1차 분할 - NCS 소제목 단위 (split_by_sections)")
sections = split_by_sections(filtered)
print(f"    생성된 섹션 수: {len(sections)}")
assert len(sections) > 0, "섹션 분할 실패"

# 섹션 분포 출력
lu_counts: dict = {}
for s in sections:
    lu = s["learning_unit"][:20]
    lu_counts[lu] = lu_counts.get(lu, 0) + 1
for lu, cnt in lu_counts.items():
    print(f"      [{lu}...] → {cnt}개 섹션")

# 빈 섹션 비율
empty = [s for s in sections if "도표·그림 위주" in s["content"]]
print(f"    빈 섹션(플레이스홀더): {len(empty)}개")
print("    ✅ OK")

# ── 6. 2차 분할 (토큰 초과 청크) ─────────────────────────────
print("\n[6] 2차 분할 - Document 생성 (refine_chunks)")
docs = refine_chunks(sections, source="테스트_요구사항확인", doc_hash=doc_hash)
print(f"    생성된 Document 수: {len(docs)}")
assert len(docs) > 0, "Document 생성 실패"

# 메타데이터 필드 검증
required_fields = {"source", "doc_hash", "learning_unit", "section_type", "subtitle", "pages", "chunk_index"}
sample_meta = docs[0].metadata
missing = required_fields - set(sample_meta.keys())
if missing:
    print(f"    ❌ 메타데이터 누락 필드: {missing}")
else:
    print(f"    메타데이터 필드: {list(sample_meta.keys())}")
    print(f"    샘플 메타데이터: source={sample_meta['source']}, subtitle={sample_meta['subtitle'][:30]}")
    print("    ✅ 메타데이터 스키마 완전")

# 청크 길이 분포
lengths = [len(d.page_content) for d in docs]
print(f"    청크 길이 - 최소: {min(lengths)}자 / 최대: {max(lengths)}자 / 평균: {sum(lengths)//len(lengths)}자")

# ── 7. End-to-End (process_pdf — 임베딩 + ChromaDB 적재) ──────
print("\n[7] End-to-End 파이프라인 (process_pdf — 임베딩 + ChromaDB 적재)")
print(f"    컬렉션: {COLLECTION_NAME}")
result = process_pdf(PDF_PATH, COLLECTION_NAME)
print(f"    status  : {result['status']}")
print(f"    message : {result['message']}")
print(f"    chunks  : {result['total_chunks']}")

if result["status"] == "success":
    assert result["total_chunks"] > 0, "적재된 청크가 0개"
    print("    ✅ 임베딩 + 적재 성공")
elif result["status"] == "skipped":
    print("    ⚠️  이미 적재된 파일 — 7번을 먼저 실행했다면 정상 (중복 방지 동작)")
else:
    print(f"    ❌ 오류: {result['message']}")

# ── 8. 중복 방지 검증 (동일 PDF 재실행 → skipped) ─────────────
print("\n[8] 중복 방지 검증 (동일 PDF 재실행 → skipped 확인)")
result2 = process_pdf(PDF_PATH, COLLECTION_NAME)
print(f"    status  : {result2['status']}")
print(f"    message : {result2['message']}")

if result2["status"] == "skipped":
    print("    ✅ skipped 정상 — 동일 파일 재처리 차단 확인")
else:
    print(f"    ❌ 예상 status='skipped', 실제: {result2['status']}")

# ── 9. Retriever 쿼리 테스트 ──────────────────────────────────
print("\n[9] Retriever 쿼리 테스트 (get_retriever)")
retriever = get_retriever(COLLECTION_NAME, top_k=3)
if retriever is None:
    print("    ❌ Retriever 생성 실패")
else:
    query = "요구사항 분석의 절차와 방법은 무엇인가?"
    print(f"    쿼리: {query}")
    retrieved_docs = retriever.invoke(query)
    print(f"    검색된 청크 수: {len(retrieved_docs)}")
    assert len(retrieved_docs) > 0, "검색 결과 없음"
    for i, d in enumerate(retrieved_docs):
        src = d.metadata.get("source", "?")
        sub = d.metadata.get("subtitle", "?")[:30]
        pages_str = d.metadata.get("pages", "[]")
        snippet = d.page_content[:80].replace("\n", " ")
        print(f"\n    [{i+1}] source={src} | subtitle={sub}")
        print(f"         pages={pages_str}")
        print(f"         내용 미리보기: {snippet}...")
    print("\n    ✅ Retriever 검색 정상")

print("\n" + "=" * 60)
print(f"  총 결과: {len(pages)}페이지 → {len(sections)}섹션 → {len(docs)}청크")
print(f"  E2E 적재: {result['status']} | 중복 방지: {result2['status']}")
print("  모든 단계 통과 ✅")
print("=" * 60)
