---
name: run-product-planning
description: 신제품 아이디어 발굴부터 기획서 작성까지 상품 기획 파이프라인을 실행한다. 새 제품을 기획할 때 사용.
user-invocable: true
allowed-tools: Agent, Read, Write, Bash, Glob
model: opus
effort: max
argument-hint: "[카테고리] [타겟 문제]"
---

## 사용 방법

```
/run-product-planning
/run-product-planning 카테고리=수면 타겟=초등 저학년
/run-product-planning 카테고리=면역 타겟=영유아
```

### 인자 파싱

`$ARGUMENTS`에서 아래 값을 파싱합니다:

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `카테고리` | 기획할 제품 카테고리 | (없으면 AI가 판단) |
| `타겟` | 타겟 연령·특성 | (없으면 AI가 판단) |

## 실행 순서

### Step 1: 폴더 생성
```
research_id = "product-planning_{YYYYMMDD_HHMMSS}"
teams/product-planning/outputs/{research_id}/ 폴더 생성
```

### Step 2: 시장 리서치
`product-market-researcher` 에이전트 호출:
- 어린이 영양제 시장 트렌드, 경쟁사, 소비자 수요, 기회 영역 조사
- `teams/product-planning/outputs/{research_id}/market_research.json` 저장

### Step 3: 아이디어 발굴
`product-ideator` 에이전트 호출:
- 시장 리서치 + 기존 제품군 분석 → 신제품 아이디어 3~5개 도출
- `teams/product-planning/outputs/{research_id}/product_ideas.json` 저장

### Step 4: 기획서 작성
`product-brief-writer` 에이전트 호출:
- 최우선 추천 아이디어를 구체적인 상품 기획서로 작성
- `teams/product-planning/outputs/{research_id}/product_brief.md` 저장

### Step 5: 배포
`shared-distributor` 에이전트 호출:
- Slack 전송 (기획서 요약)
- Notion 페이지 생성

### Step 6: 완료 보고
- research_id
- 추천 아이디어 제목 및 한 줄 설명
- 기획서 파일 경로
- Notion 페이지 URL
