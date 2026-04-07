---
name: run-contents
description: 메타 광고 콘텐츠(이미지/영상/전체)를 생성한다. 특정 제품 또는 전체 제품에 대해 실행 가능하며 산출물 유형과 수량을 선택할 수 있다.
user-invocable: true
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

**Phase 0 — 레퍼런스 학습 [순차, 최우선]**

스크립트/카피 작성 전 반드시 레퍼런스 학습을 먼저 실행:

```bash
python tools/reference_learner.py --db_url "https://www.notion.so/3367b6aa842980ee897ed424f2f3076c"
```

- 결과: `brand/reference_learnings.md` 생성/갱신
- 이후 모든 copywriter·scripter 에이전트가 이 파일을 참조
- 파일이 이미 오늘 날짜로 있으면 스킵 가능

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

**Phase 2.5 — 기존 Notion 스크립트 중복 사전 검사 [순차, 영상 제작 시 필수]**

`타입=영상` 또는 `타입=전체`인 경우, 스크립트 작성 전 반드시 실행:

Notion DB(`NOTION_DATABASE_ID`)에서 해당 제품의 기존 페이지를 모두 조회하여 훅 유형·전개 구조·오프닝 소재를 정리한다.
`contents-scripter` 에이전트에 결과를 전달하여 **70% 이상 유사한 패턴 재사용 금지** 원칙을 적용한다.

- DB 페이지: https://www.notion.so/_-3327b6aa84298031b774c3ef314849b5
- 판단 기준: 훅 유형(A-1) / 전개 구조(A-2) / 오프닝 소재 중 2가지 이상 겹치면 중복으로 판정
- 중복 발견 시: 해당 브리프 방향을 기존에 가장 적게 쓰인 패턴으로 교체 후 제작 진행

**Phase 3 — 제작 [타입별 분기]**

`타입=이미지` 또는 `타입=전체`:
1. `contents-copywriter` 에이전트 — 이미지 카피 작성 (`.claude/skills/copywriting/SKILL.md` 참조)
2. `contents-image` 에이전트 — 이미지 생성

`타입=영상` 또는 `타입=전체`:
1. `contents-copywriter` 에이전트 — 영상 카피 작성 (`.claude/skills/copywriting/SKILL.md` 참조)
2. `contents-scripter` 에이전트 — 스크립트 작성

**Phase 4 — 배포 [순차, 오케스트레이터 직접 실행]**

> ⚠️ 서브에이전트는 Bash 실행 권한이 없으므로, **오케스트레이터(메인 Claude)가 직접** 아래 커맨드를 실행한다.
> `shared-distributor` 에이전트는 호출하지 않는다.

**Step 4-1. campaign.json 생성** (없는 경우 Write 도구로 직접 생성):
```json
{
  "campaign_id": "{campaign_id}",
  "product_name": "{제품명}",
  "created_at": "{YYYY-MM-DD}"
}
```
저장 경로: `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/campaign.json`

**Step 4-2. Notion 배포** (Bash로 직접 실행):
```bash
python tools/notion_create.py \
  --campaign_id "{campaign_id}" \
  --product_name "{제품명}" \
  --campaign_json "teams/contents/outputs/campaigns/{제품명}/{campaign_id}/campaign.json"
```
- `campaign.json` 없어도 자동 생성됨
- 결과 Notion URL은 `campaign.json`에 자동 저장됨

**Step 4-3. Slack 알림** (Bash로 직접 실행):
```bash
python tools/slack_send.py \
  --campaign_id "{campaign_id}" \
  --product_name "{제품명}" \
  --campaign_json "teams/contents/outputs/campaigns/{제품명}/{campaign_id}/campaign.json"
```

### Step 4: 완료 보고

- 처리된 제품 목록
- 생성된 이미지 경로 목록 (해당 시)
- 생성된 스크립트 경로 목록 (해당 시)
- Notion 페이지 URL
