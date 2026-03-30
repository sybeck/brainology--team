---
name: run-settlement
description: 정산 대상을 조회하고 Cafe24 매출을 집계해 PDF 정산서를 생성한다. Notion 업로드 및 Slack 완료 알림까지 자동 처리.
user-invocable: true
allowed-tools: Agent, Read, Write, Bash, Glob
model: opus
effort: high
argument-hint: "[대상=이름] [시작일=YYYY-MM-DD] [종료일=YYYY-MM-DD]"
---

## 사용 방법

```
/run-settlement                                        ← 전체 대상, 전월 기간
/run-settlement 대상=홍길동                            ← 특정 대상, 전월 기간
/run-settlement 시작일=2026-02-01 종료일=2026-02-28    ← 전체 대상, 지정 기간
/run-settlement 대상=홍길동 시작일=2026-02-01 종료일=2026-02-28
```

## 인자 파싱

`$ARGUMENTS`에서 아래 값을 파싱합니다:

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `대상` | 정산 대상 이름. 없으면 Notion DB 활성 대상 전체 | (전체) |
| `시작일` | 정산 기간 시작일 (YYYY-MM-DD). 없으면 전월 1일 | 전월 1일 |
| `종료일` | 정산 기간 종료일 (YYYY-MM-DD). 없으면 전월 말일 | 전월 말일 |

**전월 기간 계산 예시 (오늘이 2026-03-30이면):**
- 시작일: `2026-02-01`
- 종료일: `2026-02-28`

---

## 실행 순서

### Step 0: run_id 및 기간 결정

```
run_id = "{YYYYMMDD_HHMMSS}"  ← 현재 시각
start_date = 인자에서 파싱 또는 전월 1일
end_date   = 인자에서 파싱 또는 전월 말일
```

출력 디렉터리: `teams/settlement/outputs/{run_id}/`

---

### Step 1: 정산 대상 조회

`settlement-target-fetcher` 에이전트 호출:
- `run_id`, `output_dir` 전달
- 결과: `teams/settlement/outputs/{run_id}/targets.json`

`대상` 인자가 있는 경우 targets.json 로드 후 해당 이름만 필터링합니다.

---

### Step 2: 매출 집계

`settlement-sales-aggregator` 에이전트 호출:
- `run_id`, `targets_json` 경로, `start_date`, `end_date` 전달
- 대상이 여럿이면 순차 처리 (Cafe24 브라우저 자동화)
- 결과: `teams/settlement/outputs/{run_id}/sales_{name}.json` (대상별)

---

### Step 3: 정산서 작성 및 배포

`settlement-report-writer` 에이전트 호출:
- `run_id`, `sales_json_list` 전달
- PDF 생성 → `teams/settlement/outputs/{run_id}/settlement_{name}.pdf`
- Notion 각 대상 페이지 본문에 정산 내용 추가
- Slack 완료 알림 전송

---

### Step 4: 완료 보고

처리된 대상 목록과 각 정산서 요약을 출력합니다:

```
✔ 정산 완료 (2026-02-01 ~ 2026-02-28)
─────────────────────────────────────
홍길동  |  총 1,234,000원  →  수수료 185,100원  →  최종 정산 179,003원
이영희  |  총 890,000원   →  수수료 133,500원  →  최종 정산 133,500원 (VAT 포함)
─────────────────────────────────────
PDF:    teams/settlement/outputs/{run_id}/settlement_*.pdf
Notion: 각 대상 페이지 업로드 완료
Slack:  전송 완료
```
