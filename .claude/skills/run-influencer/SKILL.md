---
name: run-influencer
description: 인플루언서 탐색부터 협업 브리프 작성까지 인플루언서 마케팅 파이프라인을 실행한다. 인플루언서 캠페인을 시작할 때 사용.
user-invocable: true
allowed-tools: Agent, Read, Write, Bash, Glob
model: opus
effort: max
argument-hint: "[제품명] [플랫폼] [예산등급]"
---

## 사용 방법

```
/run-influencer
/run-influencer 제품명=뉴턴젤리
/run-influencer 제품명=뉴턴젤리 플랫폼=인스타그램 예산등급=B
```

### 인자 파싱

`$ARGUMENTS`에서 아래 값을 파싱합니다:

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `제품명` | 협업할 제품 | (필수 또는 AI 선택) |
| `플랫폼` | `인스타그램` / `유튜브` / `틱톡` / `전체` | `전체` |
| `예산등급` | `A` (10만+) / `B` (1만~10만) / `C` (마이크로) | `B` |

## 실행 순서

### Step 1: 제품 파일 확인 및 폴더 생성
```
campaign_id = "influencer_{제품명}_{YYYYMMDD_HHMMSS}"
teams/influencer/outputs/{campaign_id}/ 폴더 생성
```

### Step 2: 인플루언서 탐색
`influencer-scout` 에이전트 호출:
- 플랫폼·예산등급 기준으로 적합한 인플루언서 후보 수집
- `teams/influencer/outputs/{campaign_id}/influencer_list.json` 저장

### Step 3: 협업 브리프 작성
`influencer-brief-writer` 에이전트 호출:
- Top 3 인플루언서 대상 맞춤 브리프 작성
- `teams/influencer/outputs/{campaign_id}/collaboration_brief.md` 저장

### Step 4: 배포
`shared-distributor` 에이전트 호출:
- Slack 전송 (인플루언서 후보 목록 + 브리프 요약)
- Notion 페이지 생성

### Step 5: 완료 보고
- campaign_id
- Top 3 인플루언서 후보 (핸들, 등급, 예상 단가)
- 브리프 파일 경로
- Notion 페이지 URL
