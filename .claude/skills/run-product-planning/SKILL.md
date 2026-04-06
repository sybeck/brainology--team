---
name: run-product-planning
description: 문제 키워드 기반 시장 조사부터 신제품 기획서 작성까지 상품 기획 파이프라인을 실행한다.
user-invocable: true
allowed-tools: Agent, Read, Write, Bash, Glob
model: opus
effort: max
argument-hint: "[문제] [타겟]"
---

## 사용 방법

```
/run-product-planning
/run-product-planning 문제=면역
/run-product-planning 문제=키성장 타겟=초등
/run-product-planning 문제=잦은피곤함 타겟=영유아
```

## 인자 파싱

`$ARGUMENTS`에서 아래 값을 파싱합니다:

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `문제` | 조사할 건강 문제 키워드 | (없으면 AI가 트렌드 기반 판단) |
| `타겟` | 타겟 연령·특성 | (없으면 전 연령 조사) |

---

## 실행 순서

### Step 0: 초기화

```
research_id = "product-planning_{YYYYMMDD_HHMMSS}"
출력 디렉터리: teams/product-planning/outputs/{research_id}/
시장조사 디렉터리: teams/product-planning/outputs/{research_id}/market/
```

---

### [시장조사 — 8단계 순차 실행]

각 에이전트는 독립적인 컨텍스트에서 실행되며, 직전 단계의 JSON 파일만 읽고 결과를 저장합니다.

### Step 1: 타겟군 조사

`product-market-target` 에이전트 호출 — `problem_keyword`, `target_age`, `research_id` 전달:
- 문제 키워드에 해당하는 타겟 그룹(연령·성별·라이프스타일) 세분화
- 결과: `market/01_target_groups.json`

### Step 2: 타겟별 문제 조사

`product-market-problem` 에이전트 호출 — `research_id` 전달:
- `01_target_groups.json` 기반으로 타겟별 구체적 증상·발현 상황 조사
- 결과: `market/02_target_problems.json`

### Step 3: 문제 정의·메커니즘 조사

`product-market-mechanism` 에이전트 호출 — `research_id` 전달:
- `02_target_problems.json` 기반으로 문제의 의학적·생리적 메커니즘 조사
- 결과: `market/03_problem_mechanism.json`

### Step 4: 소비자 실제 고민 조사

`product-market-consumer-voice` 에이전트 호출 — `research_id` 전달:
- `02_target_problems.json` 기반으로 맘카페·커뮤니티에서 소비자 날것의 언어 수집
- 경쟁제품 탐색 단계에서 사용할 `search_language` 포함
- 결과: `market/04_consumer_voice.json`

### Step 5: 전문가 의견 조사

`product-market-expert` 에이전트 호출 — `research_id` 전달:
- `03_problem_mechanism.json` 기반으로 소아과·식약처·학회 권고안 조사
- 조사할 성분 후보(`key_nutrients_mentioned`) 포함
- 결과: `market/05_expert_opinion.json`

### Step 6: 시즌성 조사

`product-market-seasonality` 에이전트 호출 — `research_id` 전달:
- `02_target_problems.json` 기반으로 문제의 계절·학사일정 패턴 조사
- 출시 최적 시기 제안 포함
- 결과: `market/06_seasonality.json`

### Step 7: 영양제 외 해결책 조사

`product-market-alternatives` 에이전트 호출 — `research_id` 전달:
- `04_consumer_voice.json` 기반으로 식단·병원·생활습관 등 비영양제 해결책 조사
- 결과: `market/07_other_solutions.json`

### Step 8: 영양제 성분 조사

`product-market-ingredients` 에이전트 호출 — `research_id` 전달:
- `05_expert_opinion.json` + `03_problem_mechanism.json` 기반으로 효과 성분 조사
- 추천 성분 스택과 시장 공백 포함
- 결과: `market/08_ingredient_research.json`

---

### [후속 파이프라인 — 순차 실행]

### Step 9: 경쟁 제품 탐색

`product-explorer` 에이전트 호출 — `research_id` 전달:
- `04_consumer_voice.json`의 `search_language` + `08_ingredient_research.json`의 `recommended_stack` 기반 제품 탐색
- 상위 5개 제품 선정 (가격·제형·성분·판매량)
- 결과: `product_exploration.json`

### Step 10: 소비자 리뷰 분석

`product-review-analyst` 에이전트 호출 — `research_id` 전달:
- `product_exploration.json`의 상위 5개 제품 리뷰 수집
- 좋은 점 / 나쁜 점 / 미충족 니즈 / 소비자 언어 뱅크
- 결과: `consumer_reviews.json`

### Step 11: 신제품 아이디어 도출

`product-ideator` 에이전트 호출 — `research_id` 전달:
- 시장조사 8단계 결과 + 경쟁제품 + 리뷰 종합
- 아이디어 3개 도출, 최우선 추천 1개 선정
- 결과: `product_ideas.json`

### Step 12: 상품 기획서 작성

`product-brief-writer` 에이전트 호출 — `research_id` 전달:
- 추천 아이디어를 실행 가능한 기획서로 구체화
- 경쟁사 비교표, 소비자 인사이트, 제품 스펙, 가격 전략, 출시 타임라인 포함
- 결과: `product_brief.md`

### Step 13: 배포

`shared-distributor` 에이전트 호출:
- Slack 전송 (기획서 요약 + 추천 아이디어 핵심)
- Notion 페이지 생성

### Step 14: 완료 보고

```
✔ 상품 기획 완료
────────────────────────────────────────
문제 키워드: {문제}
추천 아이디어: {working_title} — {concept}
────────────────────────────────────────
산출물: teams/product-planning/outputs/{research_id}/
  ├── market/
  │   ├── 01_target_groups.json      (타겟군 조사)
  │   ├── 02_target_problems.json    (타겟별 문제 조사)
  │   ├── 03_problem_mechanism.json  (문제 정의·메커니즘)
  │   ├── 04_consumer_voice.json     (소비자 실제 고민)
  │   ├── 05_expert_opinion.json     (전문가 의견)
  │   ├── 06_seasonality.json        (시즌성)
  │   ├── 07_other_solutions.json    (영양제 외 해결책)
  │   └── 08_ingredient_research.json (영양제 성분 조사)
  ├── product_exploration.json       (경쟁 제품 탐색)
  ├── consumer_reviews.json          (소비자 리뷰)
  ├── product_ideas.json             (신제품 아이디어)
  └── product_brief.md               (상품 기획서)
```
