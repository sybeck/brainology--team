---
name: compliance-check
description: 특정 캠페인의 카피와 이미지를 건강기능식품법과 Meta 정책 기준으로 단독 검수한다. 이미 생성된 콘텐츠를 재검수할 때 사용.
user-invocable: true
allowed-tools: Agent, Read, Write
model: opus
effort: high
---

특정 캠페인의 광고 카피와 이미지를 컴플라이언스 기준으로 검수합니다.

## 사용 방법

```
/compliance-check campaign_id=멀티비타민키즈_20260328_120000
```

$ARGUMENTS에서 campaign_id를 파싱합니다.

## 실행 순서

1. `outputs/campaigns/{campaign_id}/` 폴더 확인
2. 해당 캠페인의 모든 copy_*.json, image_*.json, video_*.json 파일 목록 수집
3. `compliance-reviewer` 에이전트 호출 — 전체 검수 실행
4. 검수 결과 출력:
   - 전체 상태 (PASS/FAIL/CONDITIONAL_PASS)
   - FAIL 항목 목록과 수정 제안
   - 필수 추가 사항

## 주의

이 스킬은 **검수만** 합니다. 수정은 별도로 진행해야 합니다.
수정까지 자동으로 원하면 `/run-product` 스킬을 사용하세요.
