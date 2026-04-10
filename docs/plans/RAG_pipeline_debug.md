# RAG Pipeline Debug & Refactoring Plan (수정본 v3)

## 개요 및 목표

MVP 일정 내 "확실하게 기능하는" 파이프라인을 만드는 것이 목표입니다. 유연성·강건성보다 **정확한 결과물 우선**으로 하드코딩 허용합니다.

---

## 디렉토리 구조

수정 대상은 `core/rag.py` 단일 파일입니다.

---

## 모듈별 구현 명세

### Step 1. `extract_pages` — 물리적 12페이지 하드스킵

**수정 위치:** `extract_pages(pdf_path)` 반환 직전

**로직:**
- 물리적 페이지 번호 기준으로 앞 12장 슬라이싱
- 전체 페이지가 12장 이하면 빈 리스트 반환 방지

**방어 조건:** `if len(pages) > 12: pages = pages[12:]`

**사이드 이펙트:** 없음

---

### Step 2. `clean_ncs_junk` — 신규 함수 추가

**수정 위치:** `extract_pages` 아래 신규 함수 삽입. `process_pdf` 내 페이지 join 직후 호출.

**제거 대상:**

| 대상 | 패턴 |
|---|---|
| CID 기호 | `\(cid:\d+\)` |
| 도표 출처 | `출처\s*:.*?\(\d{4}\).*?p\.\s*\d+` |
| 그림 라벨 | `\[그림\s*\d+-\d+\]` |
| NCS URL | `www\.ncs\.go\.kr` |
| 단독 줄 숫자(페이지 번호) | `^\s*\d+\s*$` (MULTILINE) |
| 연속 빈 줄 3줄 이상 | `\n{3,}` → `\n\n` |

**사이드 이펙트:** `출처:` 패턴이 본문 문장에 포함된 경우 오제거 가능. MVP 범위에서 무시.

---

### Step 3. `split_by_sections` — 전면 재작성

#### 3-1. 정규식 정의

```
RE_MAJOR     : ^[ \t]*학\s*습\s*(\d+)\.?\s*([가-힣a-zA-Z\s]+)
               → 학습 번호(group 1) + 제목(group 2)

RE_SUB_NUM   : ^[ \t]*(\d+)-(\d+)\.\s*$
               → 줄 끝까지 번호만 존재해야 매칭 (같은 줄에 텍스트 있으면 불매칭)

RE_SECTION   : ^[ \t]*(필\s*요\s*지\s*식|수\s*행\s*내\s*용|평\s*가)\s*/?\s*

RE_SKIP_START: ^[ \t]*(교수\s*[·・]\s*학습\s*방법|개발\s*이력)
```

#### 3-2. 상태 변수

```
current_major     : str            # 확정된 대단원 전체 문자열
current_section   : str            # 현재 중단원 (필요 지식 등)
current_sub       : str            # 확정된 소단원 — 다음 소단원까지 유지
pending_sub_num   : str | None     # "1-1" — 번호만 감지, 제목 한 줄 대기 중
major_candidates  : dict[int,str]  # {1: "현행 시스템 분석하기", 2: ...}
                                   # 연속 학습 목록을 소단원 확정 전까지 보관
content_buf       : list[str]      # 현재 소단원에 누적 중인 본문
skip_mode         : bool
```

#### 3-3. 상태머신 처리 순서 (라인 단위)

각 라인을 아래 순서로 평가합니다. 앞 조건에서 처리되면 다음 조건은 평가하지 않습니다.

**① RE_SKIP_START 매치**
- `flush()` 호출 후 `skip_mode = True`
- `pending_sub_num = None` 초기화

**② skip_mode == True**
- `RE_MAJOR` / `RE_SECTION` / `RE_SUB_NUM` 중 하나라도 매치되면 `skip_mode = False` 후 아래 로직으로 fall-through
- 아니면 `continue` (라인 버림)

**③ RE_MAJOR 매치**
- `flush()` 호출
- `major_candidates[N] = 제목` 으로 저장 (확정하지 않음)
- `pending_sub_num = None`

**④ RE_SUB_NUM 매치** — `N-M.` 형태, 줄 끝까지 번호만
- `flush()` 호출
- `major_candidates`에서 N번 항목을 꺼내 `current_major` 확정
- `pending_sub_num = "N-M"` 으로 저장 (제목은 다음 줄 대기)
- `major_candidates` 비움

**⑤ pending_sub_num 상태**
- 현재 라인이 **비어있으면**: `pending_sub_num = None`, 해당 라인 본문으로 처리 (`content_buf.append`)
- 현재 라인이 **비어있지 않으면**: `current_sub = "N-M. {stripped}"` 확정, `pending_sub_num = None`
- 두 경우 모두 `continue`

**⑥ RE_SECTION 매치**
- `flush()` 호출
- `current_section` 갱신
- `pending_sub_num = None`

**⑦ 그 외 본문 라인**
- `content_buf.append(line)`

**루프 종료 후**: `flush()` 한 번 더 호출하여 마지막 버퍼 처리.

#### 3-4. flush() 동작

`content_buf`에 내용이 있을 때만 아래 딕셔너리를 `chunks`에 append:

```
{
  "major":     current_major,
  "section":   current_section,
  "sub_title": current_sub,
  "content":   content_buf joined + strip,
}
```

이후 `content_buf.clear()`.

**사이드 이펙트:**
- `pending_sub_num` 상태에서 빈 줄 감지 시 즉시 해제 → 이후 라인은 본문으로 누적. 빈 줄 자체는 `content_buf`에 들어가지만 `strip()` 시 영향 없음.
- `major_candidates`에서 N번이 없는 경우(목차 스킵 후 첫 소단원이 갑자기 등장) → `current_major`를 `"학습 N (제목 미확인)"` 폴백으로 처리.

---

### Step 4. `process_pdf` — 호출 순서 명세

```
extract_pages → (pages join) → clean_ncs_junk → split_by_sections → list[dict] 반환
```

`merge_pages` 같은 중간 함수가 현재 존재한다면 `clean_ncs_junk` 호출은 그 직후에 위치.

---

## 체크리스트

- [ ] `extract_pages` 물리적 12페이지 슬라이싱 + 길이 방어 조건
- [ ] `clean_ncs_junk` 삽입 및 `process_pdf` 내 join 직후 호출 위치 확인
- [ ] `RE_SUB_NUM`이 `줄 끝까지 번호만` 조건(`\s*$`)으로 작성되었는지 확인
- [ ] `pending_sub_num` 상태에서 빈 줄 → 즉시 해제 + 본문 처리 동작 확인
- [ ] `major_candidates` 딕셔너리에서 N번 없을 때 폴백 처리 확인
- [ ] `skip_mode` 해제 조건(세 패턴 중 하나 매치) 동작 확인
- [ ] `flush()` 후 `content_buf.clear()` 누락 여부 확인
- [ ] 루프 종료 후 마지막 `flush()` 호출 누락 여부 확인

---

## 구현 기록
- **작업 내용**: v3 계획서 작성 (2025-04-10) — 비교안 B 확정, 소단원 2줄 버퍼 조건 강화
- **검증 결과**: 미진행
- **계획 대비 편차**: 대단원 `major_candidates` 버퍼 추가, 소단원 확정 조건 `\s*$` 강화