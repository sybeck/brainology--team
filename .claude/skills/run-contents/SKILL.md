---
name: run-contents
description: 메타 광고 콘텐츠(이미지/영상/전체)를 생성한다. 특정 제품 또는 전체 제품에 대해 실행 가능하며 산출물 유형과 수량을 선택할 수 있다.
user-invocable: true
allowed-tools: Agent, Read, Write, Bash, Glob
model: opus
effort: max
argument-hint: "[제품명=XXX] [타입=이미지|영상|전체] [이미지=N] [영상=N]"
---

## 사용 방법

```
/run-contents                                    ← 전체 제품, 전체 타입
/run-contents 제품명=뉴턴젤리                     ← 특정 제품, 전체 타입
/run-contents 제품명=뉴턴젤리 타입=영상 수량=5    ← 특정 제품, 영상만 5개
/run-contents 제품명=뉴턴젤리 타입=이미지 수량=3  ← 특정 제품, 이미지만 3개
/run-contents 제품명=뉴턴젤리 타입=전체 이미지=3 영상=5
```

### 인자 파싱

`$ARGUMENTS`에서 아래 값을 파싱합니다:

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `제품명` | 생성할 제품 이름. 없으면 `products/` 전체 | (없으면 전체) |
| `타입` | `이미지` / `영상` / `전체` | `전체` |
| `수량` | 이미지·영상 공통 수량 (`타입=이미지` 또는 `타입=영상`일 때) | 이미지 5 / 영상 10 |
| `이미지` | 이미지 수량 (`타입=전체`일 때) | 5 |
| `영상` | 영상 수량 (`타입=전체`일 때) | 10 |

---

## 실행 순서

### Step 1: 제품 목록 확인
- `제품명` 인자가 있으면: `products/{제품명}.md` 존재 확인
  - 없으면 "해당 제품 파일이 없습니다." 출력 후 중단
- `제품명` 인자가 없으면: `products/` 폴더의 모든 `.md` 파일 목록 수집

### Step 2: 캠페인 ID 및 폴더 생성

```
campaign_id = "{제품명}_{YYYYMMDD_HHMMSS}"
teams/contents/outputs/campaigns/{제품명}/{campaign_id}/
teams/contents/outputs/images/{제품명}/{campaign_id}/  ← 이미지 생성 시
```

### Step 3: 파이프라인 실행 (제품별)

**Phase 1 — 리서치 [병렬]**

두 에이전트를 동시에 호출:
- `contents-reference` 에이전트: 경쟁사 광고·트렌드 수집
- `contents-researcher` 에이전트: 부모 커뮤니티 페인포인트·소비자 언어 수집

각 에이전트에 `campaign_id`, `제품명`을 전달.
결과를 `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/`에 저장.

**Phase 2 — 콘텐츠 기획 [순차]**

`contents-planner` 에이전트 호출. `타입`에 따라 기획 범위 지정:
- `이미지`: 이미지 컨셉 `수량`개만 기획
- `영상`: 영상 컨셉 `수량`개만 기획
- `전체`: 이미지 `이미지`개 + 영상 `영상`개 기획

입력 파일:
- `brand/brand_guide.md`
- `products/{제품명}.md`
- `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/references.json`
- `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/consumer_insights.json`
- `.claude/skills/plan-content/SKILL.md` — 기획 방법론

**Phase 3 — 제작 [타입별 분기]**

`타입=이미지` 또는 `타입=전체`:
1. `contents-copywriter` 에이전트 — 이미지 카피 작성 (`.claude/skills/copywriting/SKILL.md` 참조)
2. `contents-image` 에이전트 — 이미지 생성

`타입=영상` 또는 `타입=전체`:
1. `contents-copywriter` 에이전트 — 영상 카피 작성 (`.claude/skills/copywriting/SKILL.md` 참조)
2. `contents-scripter` 에이전트 — 스크립트 작성

**Phase 4 — 배포 [순차]**

`shared-distributor` 에이전트 호출:
- Slack 전송
- Notion 페이지 생성 (`tools/notion_create.py` 사용)

### Step 4: 완료 보고

- 처리된 제품 목록
- 생성된 이미지 경로 목록 (해당 시)
- 생성된 스크립트 경로 목록 (해당 시)
- Notion 페이지 URL
