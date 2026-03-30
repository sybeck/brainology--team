---
name: create-skill
description: 새로운 스킬 파일(SKILL.md) 또는 에이전트 파일(.md)을 Claude Code 공식 형식에 맞게 생성한다. 새 스킬이나 에이전트를 추가할 때 사용.
user-invocable: true
allowed-tools: Read, Write, Glob
model: inherit
argument-hint: "[skill-name 또는 agent-name] [한 줄 설명]"
---

## 작업

`$ARGUMENTS`를 파싱해 새 스킬 또는 에이전트 파일을 생성합니다.

- 첫 번째 인자: 이름 (예: `run-design`, `design-briefer`)
- 두 번째 인자 이후: 설명

인자가 없으면 사용자에게 이름과 목적을 물어보세요.

---

## 판단 기준: 스킬 vs 에이전트

| 구분 | 스킬 (SKILL.md) | 에이전트 (.md) |
|------|----------------|---------------|
| **컨텍스트** | 주 대화 내에서 실행 | 독립된 컨텍스트로 실행 |
| **호출 방식** | `/skill-name` 또는 자동 로드 | Claude가 자동 위임 또는 명시 호출 |
| **용도** | 재사용 가능한 지침·워크플로우 | 독립적으로 처리 가능한 자체완결 작업 |
| **결과 반환** | 주 대화에서 계속 진행 | 요약된 결과를 오케스트레이터에 반환 |

**스킬로 만들어야 하는 경우**
- `/run-XXX` 같은 사용자 실행 진입점
- 작성 규칙, 방법론, 참조 가이드
- 여러 에이전트를 순서대로 조율하는 파이프라인 설명

**에이전트로 만들어야 하는 경우**
- 웹 검색, 파일 읽기, API 호출 등 실제 작업을 수행하는 전문 역할
- 긴 리서치·분석·생성 작업 (주 컨텍스트를 보호해야 할 때)
- 특정 도구 세트만 사용해야 하는 역할

---

## 스킬 파일 형식

저장 위치: `.claude/skills/{name}/SKILL.md`

```markdown
---
name: {스킬명}
description: {Claude가 자동 사용 시 판단 기준이 될 설명. 언제 이 스킬을 써야 하는지 명확하게.}
user-invocable: true|false   # false = /메뉴에서 숨김 (내부 전용)
allowed-tools: Read, Write, Glob, Bash, Agent  # 이 스킬 실행 시 허용 도구
model: inherit|sonnet|opus|haiku
effort: low|medium|high|max   # opus 모델일 때만 의미 있음
argument-hint: "[인자 예시]"  # 자동완성 힌트 (user-invocable: true일 때)
context: fork                 # 선택: forked subagent에서 실행 시
agent: general-purpose        # context: fork일 때 사용할 에이전트 유형
---

스킬 본문...

## 사용 방법
/{name} [인자]

## 실행 순서
1. ...
2. ...
```

---

## 에이전트 파일 형식

저장 위치: `.claude/agents/{name}.md`

```markdown
---
name: {에이전트명}           # 소문자-하이픈 형식
description: {이 에이전트가 어떤 작업을 하는지 + 언제 자동 위임될지. 구체적일수록 좋음.}
tools: Read, Write, WebSearch, Bash  # 허용 도구 목록
model: sonnet|opus|haiku
effort: low|medium|high|max
permissionMode: default|acceptEdits|bypassPermissions  # 선택
maxTurns: 10               # 선택: 최대 턴 수 제한
memory: user|project|local  # 선택: 지속 메모리
---

에이전트 역할 설명...

## 입력 파일 읽기
...

## 처리 로직
...

## 출력
...저장 경로와 JSON 스키마
```

---

## 이 프로젝트 네이밍 컨벤션

| 팀 | 에이전트 접두어 | run 스킬 |
|---|---|---|
| 콘텐츠팀 | `contents-` | `run-contents` |
| 상품 기획팀 | `product-` | `run-product-planning` |
| 인플루언서팀 | `influencer-` | `run-influencer` |
| 디자인팀 | `design-` | `run-design` |
| 공통 | `shared-` | — |

---

## 기존 파일 참고 경로

스킬 예시:
- `.claude/skills/copywriting/SKILL.md` — user-invocable: false, 내부 규칙 스킬
- `.claude/skills/plan-content/SKILL.md` — 방법론 참조 스킬
- `.claude/skills/run-contents/SKILL.md` — user-invocable: true, 파이프라인 진입점

에이전트 예시:
- `.claude/agents/contents-planner.md` — opus, high effort
- `.claude/agents/contents-researcher.md` — sonnet, medium effort, WebSearch 포함
- `.claude/agents/shared-distributor.md` — haiku, medium effort, Bash 포함

---

## 생성 절차

1. 기존 유사 파일 1개를 Glob·Read로 참조
2. 위 형식에 맞게 frontmatter 작성
3. 본문: 역할 설명 → 입력 파일 → 처리 로직 → 출력(경로·스키마)
4. 파일 저장
5. 스킬인 경우 `MEMORY.md`에 항목 추가 불필요 (자동 인식)

생성 후 파일 경로를 사용자에게 알려주세요.
