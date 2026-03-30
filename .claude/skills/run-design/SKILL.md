---
name: run-design
description: 디자인 브리프 작성부터 AI 시안 생성·검수까지 디자인 파이프라인을 실행한다. 광고 배너, SNS 이미지, 패키지 시안이 필요할 때 사용.
user-invocable: true
allowed-tools: Agent, Read, Write, Bash, Glob
model: opus
effort: max
argument-hint: "[제품명] [용도] [수량]"
---

## 사용 방법

```
/run-design
/run-design 제품명=뉴턴젤리
/run-design 제품명=뉴턴젤리 용도=메타광고피드 수량=3
/run-design 제품명=오메가3 용도=스토리 수량=5
```

### 인자 파싱

`$ARGUMENTS`에서 아래 값을 파싱합니다:

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `제품명` | 디자인할 제품 | (필수 또는 AI 선택) |
| `용도` | `메타광고피드` / `스토리` / `배너` / `썸네일` / `패키지목업` | `메타광고피드` |
| `수량` | 생성할 시안 수 | 3 |

## 실행 순서

### Step 1: 제품 파일 확인 및 폴더 생성
```
project_id = "design_{제품명}_{YYYYMMDD_HHMMSS}"
teams/design/outputs/{project_id}/ 폴더 생성
```

### Step 2: 디자인 브리프 작성
`design-briefer` 에이전트 호출:
- 용도·규격·핵심 메시지·컬러 방향·금지 사항 정의
- `teams/design/outputs/{project_id}/design_brief.md` 저장

### Step 3: 시안 생성
`design-image-creator` 에이전트 호출:
- 브리프 기반으로 `수량`개 이미지 생성
- `teams/design/outputs/{project_id}/image_{N}.png` 저장
- `teams/design/outputs/{project_id}/design_assets.json` 저장

### Step 4: 브랜드 검수
`design-reviewer` 에이전트 호출:
- 브랜드 가이드라인 적합성 검수
- `teams/design/outputs/{project_id}/design_review.json` 저장
- REVISION_NEEDED 항목은 `design-image-creator`에 재요청 (최대 2회)

### Step 5: 배포
`shared-distributor` 에이전트 호출:
- Slack 전송 (시안 이미지 첨부)
- Notion 페이지 생성

### Step 6: 완료 보고
- project_id
- 생성된 시안 파일 경로 목록
- 검수 결과 (PASS/REVISION 수)
- Notion 페이지 URL
