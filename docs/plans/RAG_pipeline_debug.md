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
- 현재 저장된 모든 NCS PDF에 공통 적용
- 다만 MVP 일정 대응 목적의 임시 규칙으로 간주

**방어 조건:** `if len(pages) > 12: pages = pages[12:]`

**사이드 이펙트:** PDF 형식이 달라질 경우 앞 12페이지 내 유효 본문까지 함께 제거될 가능성 존재. MVP 범위에서 허용.

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

**채택안:** 비교안 B
- 연속 `"학습 N"` 라인 구간 자체를 즉시 대단원으로 확정하지 않음
- 해당 구간은 `major_candidates` 버퍼에 누적 저장
- 이후 `N-M.` 형태의 소단원 번호가 등장하는 순간, 그 번호의 앞자리 `N`에 대응하는 학습 라인만 `current_major`로 확정
- 즉, 목차성 학습 목록은 버퍼링 대상이고 실제 본문 진입 신호는 소단원 번호로 판단

**채택 사유:**
- 대단원 제목 텍스트 보존 가능
- 현재 문제 PDF 구조에서 목차 구간과 본문 구간을 가장 안정적으로 분리 가능
- 소단원도 다음 소단원 전까지 유지되는 상태값이 필요하므로 동일한 버퍼링 접근과 잘 맞음

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
chunks            : list[dict]     # 최종 분할 결과
```

#### 3-3. 상태머신 처리 순서 (라인 단위)

각 라인을 아래 순서로 평가합니다. 앞 조건에서 처리되면 다음 조건은 평가하지 않습니다.

**전제:**
- 입력은 `clean_ncs_junk()` 이후 문자열
- `text.splitlines()` 기준으로 라인 순회
- 각 라인에 대해 `raw_line`과 `stripped = line.strip()`를 함께 사용
- `pending_sub_num` 상태는 "직전 줄이 `1-1.` 같은 번호만 있는 줄이었고, 지금 줄이 소단원 제목 후보인지 확인 중"을 의미
- `current_sub`는 한 번 확정되면 다음 소단원 번호를 만날 때까지 유지

**중요 규칙:**
- `1-1. 어쩌구` 같이 번호와 텍스트가 같은 줄에 있는 경우는 소단원으로 인정하지 않음
- 반드시 `1-1.` 같은 번호-only 줄이 먼저 나와야 함
- 그 다음 줄이 즉시 일반 문자열이어야만 소단원으로 확정
- 번호 줄 다음에 빈 줄이 나오면 소단원 아님
- 번호 줄 다음에 `학습 N`, `필요 지식`, `수행 내용`, `평가`, `교수·학습 방법`, `개발 이력`, 또 다른 `N-M.` 같은 구조 라인이 나오면 소단원 아님
- 위 경우에는 `pending_sub_num` 해제 후 해당 라인을 원래 규칙대로 다시 평가해야 함

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
- 직전 줄이 `1-1.` 같은 번호-only 줄이었다는 의미
- 아래 순서로 평가:

  1. 현재 라인이 **비어있으면**
     - `pending_sub_num = None`
     - 소단원 확정 실패
     - 빈 줄은 버림
     - `continue`

  2. 현재 라인이 `RE_MAJOR` / `RE_SECTION` / `RE_SUB_NUM` / `RE_SKIP_START` 중 하나에 매치되면
     - `pending_sub_num = None`
     - 소단원 확정 실패
     - 현재 라인은 구조 라인이므로 버리지 말고 **현재 루프에서 다시 평가해야 함**
     - 구현 시 `continue` 하면 안 됨
     - 구현 방법:
       - `pending_sub_num`만 해제한 뒤, 아래의 일반 상태머신 분기 로직으로 fall-through
       - 또는 `reprocess_current_line = True` 방식 사용 가능

  3. 현재 라인이 **비어있지 않고 구조 라인도 아니면**
     - `current_sub = "N-M. {stripped}"` 확정
     - `pending_sub_num = None`
     - 이 줄은 소단원 제목 줄이므로 `content_buf`에 넣지 않음
     - `continue`

**⑤-보충. 소단원 확정 예시**

소단원으로 인정:
```text
1-1.
운영체제 개요
```

소단원으로 불인정:
```text
1-1. 운영체제 개요
```

소단원으로 불인정:
```text
1-1.

운영체제 개요
```

소단원으로 불인정:
```text
1-1.
필요 지식
```

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
  "learning_unit": current_major,
  "section_type":  current_section,
  "subtitle":      current_sub,
  "content":       content_buf joined + strip,
  "pages":         현재 content_buf 내부 PAGE 마커 기준 추출값,
}
```

이후 `content_buf.clear()`.

**사이드 이펙트:**
- `pending_sub_num` 상태에서 빈 줄 감지 시 즉시 해제 → 해당 번호 줄은 소단원으로 채택되지 않음.
- `major_candidates`에서 N번이 없는 경우(목차 스킵 후 첫 소단원이 갑자기 등장) → `current_major`를 `"학습 N (제목 미확인)"` 폴백으로 처리.
- `current_sub`는 다음 소단원 번호가 나오기 전까지 유지되므로, 소단원 간 간격이 멀어도 중간 본문은 모두 직전 소단원에 귀속.
- `flush()`는 "현재까지 누적된 본문을 직전 확정된 `current_major` / `current_section` / `current_sub` 조합으로 저장"하는 동작임. 즉 새 소단원 번호를 만나기 전까지는 이전 소단원 기준 누적 유지.

---

### Step 4. `process_pdf` — 호출 순서 명세

```
extract_pages → (pages join) → clean_ncs_junk → split_by_sections → list[dict] 반환
```

`merge_pages` 같은 중간 함수가 현재 존재한다면 `clean_ncs_junk` 호출은 그 직후에 위치.

### Step 5. 메타데이터 유지 방침

**원칙:**
- 이번 디버깅 범위에서는 메타데이터 필드명 변경 금지
- 기존 `learning_unit`, `section_type`, `subtitle`, `pages` 유지
- 특히 `pages` 필드는 제거하지 않음

**사유:**
- 디버깅 시 원문 PDF 추적 근거로 사용
- 기존 테스트 스크립트 및 후속 검증 흐름과의 호환성 유지 목적

---

## 체크리스트

- [ ] `extract_pages` 물리적 12페이지 슬라이싱 + 길이 방어 조건
- [ ] `clean_ncs_junk` 삽입 및 `process_pdf` 내 join 직후 호출 위치 확인
- [ ] `RE_SUB_NUM`이 `줄 끝까지 번호만` 조건(`\s*$`)으로 작성되었는지 확인
- [ ] `1-1. 제목` 같은 same-line 패턴이 소단원으로 매칭되지 않는지 확인
- [ ] `1-1.` 다음 줄이 일반 문자열일 때만 소단원 확정되는지 확인
- [ ] `1-1.` 다음 줄이 빈 줄이면 소단원 미확정 처리되는지 확인
- [ ] `1-1.` 다음 줄이 `필요 지식` 등 구조 라인이면 소단원 미확정 + 해당 라인 재평가되는지 확인
- [ ] `major_candidates` 딕셔너리에서 N번 없을 때 폴백 처리 확인
- [ ] `skip_mode` 해제 조건(세 패턴 중 하나 매치) 동작 확인
- [ ] `flush()` 후 `content_buf.clear()` 누락 여부 확인
- [ ] 루프 종료 후 마지막 `flush()` 호출 누락 여부 확인
- [ ] 메타데이터 필드 `learning_unit`, `section_type`, `subtitle`, `pages` 유지 확인

---

## 예외 처리 및 방어 로직

- `len(pages) <= 12` 인 경우: 빈 리스트 반환 방지. 원본 페이지 유지
- `major_candidates`에서 해당 번호를 찾지 못한 경우: `"학습 N (제목 미확인)"` 폴백 적용
- `pending_sub_num` 직후 빈 줄 등장 시: 상태 해제. 소단원 미확정 처리. 빈 줄 버림
- `pending_sub_num` 직후 구조 라인 등장 시: 상태 해제 후 해당 라인 재평가
- `1-1. 제목` same-line 패턴 등장 시: 소단원 번호로 간주하지 않음. 일반 본문 라인으로 처리
- `split_by_sections` 결과가 비정상적으로 적거나 비어 있는 경우: 샘플 PDF 기준 수동 검증 필요
- 메타데이터 필드 변경 유혹 발생 시: 이번 디버깅 범위에서는 보류. 구조 안정화 우선

## 검증 기준

- 샘플 PDF에서 연속 `학습 1`, `학습 2`, `학습 3` 목록이 나온 뒤 `2-1.` 이 등장하면 `current_major`는 `학습 2 ...` 로 확정되어야 함
- `1-1.` 뒤에 바로 제목 줄이 나오면 `subtitle = "1-1. {제목}"` 형태로 확정되어야 함
- `1-1. 제목` 한 줄 패턴은 subtitle 확정이 아니라 본문으로 남아야 함
- 소단원 확정 후 다음 `N-M.` 전까지의 긴 본문은 모두 직전 subtitle에 귀속되어야 함
- 결과 청크 메타데이터에 `learning_unit`, `section_type`, `subtitle`, `pages`가 모두 남아 있어야 함

---

## 구현 기록
- **작업 내용 (2026-04-10)**: 
- **검증 결과**: 미진행
- **계획 대비 편차**:
