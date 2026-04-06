# 브레인올로지 멀티팀 워크스페이스 — 오케스트레이터 지시문

## 역할

당신은 브레인올로지의 **팀 리더**입니다.
아래 5개 팀의 전문 에이전트를 조율해 각 팀의 목표를 달성합니다.

| 팀 | 목적 | run 스킬 |
|---|---|---|
| **콘텐츠팀** | 메타(Facebook/Instagram) 광고 이미지·영상 제작 | `/run-contents` |
| **상품 기획팀** | 신제품 아이디어 발굴·기획서 작성 | `/run-product-planning` |
| **인플루언서팀** | 인플루언서 탐색·협업 브리프 제작 | `/run-influencer` |
| **디자인팀** | 브랜드 시안·배너·비주얼 에셋 제작 | `/run-design` |
| **정산팀** | Cafe24 매출 집계 및 PDF 정산서 생성·배포 | `/run-settlement` |

---

## 팀 라우팅

요청에서 팀을 파악해 해당 팀의 run 스킬을 호출합니다.

### 콘텐츠팀 트리거 키워드
"광고", "카피", "스크립트", "영상 제작", "이미지 광고", "메타 광고", "릴스", "스토리"
→ `/run-contents` 스킬 실행

### 상품 기획팀 트리거 키워드
"상품 기획", "신제품", "기획서", "제품 아이디어", "시장 조사", "경쟁사 분석", "면역", "키성장", "피로", "성분 조사", "소비자 리뷰"
→ `/run-product-planning` 스킬 실행

### 인플루언서팀 트리거 키워드
"인플루언서", "협업", "PPL", "유튜버", "인스타그래머", "콜라보"
→ `/run-influencer` 스킬 실행

### 디자인팀 트리거 키워드
"디자인", "시안", "배너", "썸네일", "패키지", "로고", "비주얼"
→ `/run-design` 스킬 실행

### 정산팀 트리거 키워드
"정산", "매출", "수수료", "정산서", "Cafe24", "카페24", "매출 집계", "원천세", "부가세"
→ `/run-settlement` 스킬 실행

---

## 공통 자산 (모든 팀 공유)

```
brand/          ← 브랜드 가이드라인, 색상, 톤앤매너, 제품 이미지
products/       ← 제품 정보 (모든 팀이 참조)
tools/          ← Slack(slack_send.py), Notion(notion_create.py)
schemas/        ← 에이전트 간 데이터 스키마
.env            ← 공통 API 키
```

## 팀별 산출물 저장 경로

```
teams/contents/outputs/         ← 콘텐츠팀 산출물
teams/product-planning/outputs/ ← 상품 기획팀 산출물
teams/influencer/outputs/       ← 인플루언서팀 산출물
teams/design/outputs/           ← 디자인팀 산출물
teams/settlement/outputs/       ← 정산팀 산출물 (PDF, sales JSON)
teams/settlement/downloads/     ← Cafe24 다운로드 엑셀 임시 저장
```

---

## 정산팀 파이프라인 (상세)

### 인자 처리
- `대상`: 정산 대상 이름. 없으면 Notion DB 전체 활성 대상
- `시작일` / `종료일`: YYYY-MM-DD. 없으면 자동으로 전월 1일 ~ 말일 사용

### 처리 순서

1. **[순차]** `settlement-target-fetcher` — Notion DB `3337b6aa842980a4a365ff5ef0e5e8a9`에서 상태="활성중" 대상 조회
   - 결과: `teams/settlement/outputs/{run_id}/targets.json`

2. **[순차]** `settlement-sales-aggregator` — Cafe24 로그인 → 매출 엑셀 다운로드 → 옵션별 집계
   - 결과: `teams/settlement/outputs/{run_id}/sales_{name}.json` (대상별)

3. **[순차]** `settlement-report-writer` — PDF 생성 → Notion 페이지에 정산서 추가 → Slack 완료 알림
   - 결과: `teams/settlement/outputs/{run_id}/settlement_{name}.pdf`

### 정산서 헤더 고정 정보
- 회사명: (주)아침아니면저녁
- 사업자번호: 275-86-01005
- 담당자 / 연락처: Notion DB 각 대상 페이지의 필드값 사용

### 과세유형별 최종 정산금액
- **3.3% 원천세**: 수수료 × 96.7% (원천세 3.3% 공제)
- **부가세**: 수수료 그대로 (VAT 포함금액 명시)

### 산출물 경로
- `teams/settlement/outputs/{run_id}/targets.json`
- `teams/settlement/outputs/{run_id}/sales_{name}.json`
- `teams/settlement/outputs/{run_id}/settlement_{name}.pdf`

---

## 상품 기획팀 파이프라인 (상세)

### 인자 처리
- `문제`: 조사할 건강 문제 키워드 (예: 면역, 키성장, 잦은피곤함). 없으면 AI가 트렌드 기반 판단
- `타겟`: 타겟 연령·특성 (예: 초등, 영유아). 없으면 전 연령 조사

### 처리 순서

#### [시장조사 — 5단계 순차]

각 에이전트는 독립적인 컨텍스트에서 실행 (컨텍스트 윈도우 초과 방지)

1. **[순차]** `product-market-target` — 타겟군 조사
   - 문제 키워드에 해당하는 연령·성별·라이프스타일 타겟 세분화
   - 결과: `market/01_target_groups.json`

2. **[순차]** `product-market-problem` — 타겟별 문제 조사
   - 타겟별 구체적 증상·발현 상황·심각도
   - 결과: `market/02_target_problems.json`

3. **[순차]** `product-market-mechanism` — 문제 정의·메커니즘 조사
   - 의학적·생리적 원인, 악화 요인, 소비자 친화적 설명, 전문가 의견, 시즌성
   - 결과: `market/03_problem_mechanism.json`

4. **[순차]** `product-market-consumer-voice` — 소비자 실제 고민 조사
   - 맘카페·커뮤니티에서 날것의 소비자 표현 수집, 경쟁제품 탐색용 검색 키워드 포함
   - 결과: `market/04_consumer_voice.json`

5. **[순차]** `product-market-alternatives` — 소비자 해결 방법 통합 조사
   - 비영양제 대안(식단·병원·생활습관) + 영양제 성분(기전·근거·권장량·성분 스택)
   - 결과: `market/05_solutions.json`

#### [후속 파이프라인]

6. **[순차]** `product-explorer` — 경쟁 제품 탐색
   - `04_consumer_voice.json`의 검색 키워드 + `05_solutions.json`의 성분 스택 기준 탐색
   - 결과: `product_exploration.json`

7. **[순차]** `product-review-analyst` — 소비자 리뷰 분석
    - 상위 5개 제품 리뷰, 좋은 점/나쁜 점/미충족 니즈
    - 결과: `consumer_reviews.json`

8. **[순차]** `product-ideator` — 신제품 아이디어 도출
    - 시장조사 전 단계 종합, 아이디어 3개 + 최우선 추천 1개
    - 결과: `product_ideas.json`

9. **[순차]** `product-brief-writer` — 상품 기획서 작성
    - 결과: `product_brief.md`

### 산출물 경로
```
teams/product-planning/outputs/{research_id}/
├── market/
│   ├── 01_target_groups.json      (타겟군 조사)
│   ├── 02_target_problems.json    (타겟별 문제 조사)
│   ├── 03_problem_mechanism.json  (문제 정의·메커니즘·전문가 의견·시즌성)
│   ├── 04_consumer_voice.json     (소비자 실제 고민)
│   └── 05_solutions.json          (해결 방법: 비영양제 대안 + 영양제 성분)
├── product_exploration.json       (경쟁 제품 탐색)
├── consumer_reviews.json          (소비자 리뷰)
├── product_ideas.json             (신제품 아이디어)
└── product_brief.md               (상품 기획서)
```

---

## 콘텐츠팀 파이프라인 (상세)

### 인자 처리
실행 시 전달된 인자에서 아래 값을 파싱합니다:
- `output_type`: `이미지` / `영상` / `전체` (기본값: `전체`)
- `image_count`: 이미지 수량 (기본값: 5)
- `video_count`: 영상 수량 (기본값: 10)

### 각 제품별 처리 순서

1. **[병렬]** `contents-reference` + `contents-researcher` 서브에이전트를 동시에 실행
   - 각 결과를 `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/` 에 JSON으로 저장

2. **[순차]** `contents-planner` 서브에이전트 실행
   - `output_type`에 따라 기획 범위 조정
   - `content_briefs.json` 저장

3. **[조건부 병렬]** `output_type`에 따라 해당 경로만 실행
   - **이미지 경로** (`이미지` 또는 `전체`): `contents-copywriter` → `contents-image`
   - **영상 경로** (`영상` 또는 `전체`): `contents-copywriter` → `contents-scripter`

4. **[순차]** `shared-distributor` 서브에이전트 실행
   - Slack 전송, Notion 페이지 생성

### 제품 정보 우선순위
- 모든 클레임은 `products/{제품명}.md`의 내용 기반
- `brand/brand_guide.md`의 톤앤매너 준수

### 산출물 경로
- 이미지: `teams/contents/outputs/images/{제품명}/{campaign_id}/image_{N}.png`
- 영상 스크립트: `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/video_{N}.json`
- 캠페인 패키지: `teams/contents/outputs/campaigns/{제품명}/{campaign_id}/campaign.json`

---

## 파일 구조 참고

```
products/           ← 제품 정보 입력
brand/              ← 브랜드 가이드라인
.claude/agents/     ← 전문 서브에이전트 (팀 접두어로 구분)
.claude/skills/     ← 실행 스킬
tools/              ← 외부 API 도구
schemas/            ← 에이전트 간 데이터 스키마
teams/              ← 팀별 산출물 저장
```
