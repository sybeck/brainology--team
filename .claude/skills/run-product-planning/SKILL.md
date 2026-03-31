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
```

### Step 1: 정성 시장 조사

`product-market-researcher` 에이전트 호출 — `문제`, `타겟`, `research_id` 전달:
- 문제 프로파일 (연령/성별, 증상, 시즌성)
- 소비자 해결 행동 (방식, 구매 기준, 채널)
- 소비자 언어 수집
- 결과: `market_research.json`

### Step 2: 키워드 데이터 조사

`product-data-researcher` 에이전트 호출 — `research_id` 전달:
- `market_research.json`의 소비자 언어에서 키워드 추출
- 문제 키워드 / 성분 키워드 / 해결 키워드 검색량 분석
- 네이버 DataLab API (키 있으면) 또는 WebSearch 폴백
- 키워드 성격 확인 (정보성 vs 구매의향)
- 결과: `keyword_data.json`

### Step 3: 경쟁 제품 탐색

`product-explorer` 에이전트 호출 — `research_id` 전달:
- `keyword_data.json`의 `top_keywords` 기준 상위 제품 탐색
- 제품별 가격·제형·용량·성분·판매량·특장점 수집
- 상위 5개 제품 선정
- 결과: `product_exploration.json`

### Step 4: 소비자 리뷰 분석

`product-review-analyst` 에이전트 호출 — `research_id` 전달:
- `product_exploration.json`의 상위 5개 제품 리뷰 수집
- 제품별 좋은 점 / 나쁜 점 / 미충족 니즈
- 공통 인사이트 추출
- 결과: `consumer_reviews.json`

### Step 5: 신제품 아이디어 추천

`product-ideator` 에이전트 호출 — `research_id` 전달:
- 1~4단계 전체 결과 종합
- 컨셉, 가칭, 가격대, 제형, 용량, 주요 성분, 차별화 포인트 포함한 아이디어 3개 도출
- 최우선 추천 1개 선정
- 결과: `product_ideas.json`

### Step 6: 상품 기획서 작성

`product-brief-writer` 에이전트 호출 — `research_id` 전달:
- 추천 아이디어를 실행 가능한 기획서로 구체화
- 경쟁사 비교표, 소비자 인사이트, 제품 스펙, 가격 전략 포함
- 결과: `product_brief.md`

### Step 7: 배포

`shared-distributor` 에이전트 호출:
- Slack 전송 (기획서 요약 + 추천 아이디어 핵심)
- Notion 페이지 생성

### Step 8: 완료 보고

```
✔ 상품 기획 완료
────────────────────────────────────────
문제 키워드: {문제}
추천 아이디어: {working_title} — {concept}
────────────────────────────────────────
산출물: teams/product-planning/outputs/{research_id}/
  ├── market_research.json      (정성 시장 조사)
  ├── keyword_data.json         (키워드 검색량)
  ├── product_exploration.json  (경쟁 제품 탐색)
  ├── consumer_reviews.json     (소비자 리뷰)
  ├── product_ideas.json        (신제품 아이디어)
  └── product_brief.md          (상품 기획서)
```
