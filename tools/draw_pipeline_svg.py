"""
상품 기획팀 파이프라인 SVG 생성기
출력: teams/product-planning/pipeline.svg
"""

from pathlib import Path

STEPS = [
    {
        "step": "STEP 1", "agent": "product-market-researcher",
        "label": "정성 시장 조사",
        "desc1": "문제 프로파일 · 소비자 행동 · 시즌성",
        "desc2": "소비자 언어 수집",
        "output": "market_research.json", "tool": "WebSearch",
        "color": "#4A90D9",
    },
    {
        "step": "STEP 2", "agent": "product-data-researcher",
        "label": "키워드 검색량 분석",
        "desc1": "문제 / 성분 / 해결 키워드 검색량 비교",
        "desc2": "네이버 검색광고 API · 월간 절대값",
        "output": "keyword_data.json", "tool": "Naver AD API",
        "color": "#5BB5A2",
    },
    {
        "step": "STEP 3", "agent": "product-explorer",
        "label": "경쟁 제품 탐색",
        "desc1": "상위 노출 제품 5개 선정",
        "desc2": "가격 · 제형 · 성분 · 판매량 수집",
        "output": "product_exploration.json", "tool": "WebSearch",
        "color": "#E87D5A",
    },
    {
        "step": "STEP 4", "agent": "product-review-analyst",
        "label": "소비자 리뷰 분석",
        "desc1": "네이버 쇼핑 · 블로그 · 카페",
        "desc2": "미충족 니즈 · 공통 인사이트 추출",
        "output": "consumer_reviews.json", "tool": "WebSearch",
        "color": "#C96BC9",
    },
    {
        "step": "STEP 5", "agent": "product-ideator",
        "label": "신제품 아이디어 추천",
        "desc1": "1~4단계 종합 · 아이디어 3개 도출",
        "desc2": "컨셉 · 성분 · 차별화 포인트",
        "output": "product_ideas.json", "tool": "Read / Write",
        "color": "#6C9B3A",
    },
    {
        "step": "STEP 6", "agent": "product-brief-writer",
        "label": "상품 기획서 작성",
        "desc1": "경쟁사 비교표 · 제품 스펙 · 가격 전략",
        "desc2": "출시 계획 · 리스크 · KPI",
        "output": "product_brief.md", "tool": "Read / Write",
        "color": "#E8C55A",
    },
    {
        "step": "STEP 7", "agent": "shared-distributor",
        "label": "배포",
        "desc1": "Slack 전송 · Notion 페이지 생성",
        "desc2": "",
        "output": "Slack + Notion", "tool": "Slack / Notion",
        "color": "#6C63FF",
    },
]

OUTPUT_FILES = [
    ("market_research.json",     "#4A90D9"),
    ("keyword_data.json",        "#5BB5A2"),
    ("product_exploration.json", "#E87D5A"),
    ("consumer_reviews.json",    "#C96BC9"),
    ("product_ideas.json",       "#6C9B3A"),
    ("product_brief.md",         "#E8C55A"),
]

# 레이아웃
SVG_W     = 900
CARD_X    = 50
CARD_W    = 800
CARD_H    = 104
GAP       = 18
HEADER_H  = 210

BG        = "#FFFFFF"
CARD_BG   = "#F8F9FC"
BORDER    = "#D0D5E8"
TEXT_MAIN = "#1A1A2E"
TEXT_SUB  = "#55577A"
ACCENT    = "#4B44CC"
FONT_KO   = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
FONT_MONO = "'Consolas','Courier New',monospace"


def e(s):
    """XML escape."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_card(step: dict, y: int) -> str:
    c   = step["color"]
    mid = y + CARD_H // 2

    # 연한 배경 색 (color를 흰색과 혼합)
    r = int(c[1:3], 16)
    g = int(c[3:5], 16)
    b = int(c[5:7], 16)
    dark_bg = f"#{r + (255-r)*85//100:02x}{g + (255-g)*85//100:02x}{b + (255-b)*85//100:02x}"

    desc2 = ""
    if step["desc2"]:
        desc2 = f'<text x="{CARD_X + 210}" y="{y + 80}" font-family={FONT_KO!r} font-size="12" fill="{TEXT_SUB}">{e(step["desc2"])}</text>'

    return f"""
  <g>
    <rect x="{CARD_X}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10"
          fill="{CARD_BG}" stroke="{c}" stroke-width="1.2"/>
    <rect x="{CARD_X}" y="{y}" width="8" height="{CARD_H}" rx="4" fill="{c}"/>
    <rect x="{CARD_X + 4}" y="{y}" width="4" height="{CARD_H}" fill="{c}"/>

    <!-- step 배지 -->
    <rect x="{CARD_X + 20}" y="{y + 12}" width="66" height="22" rx="5" fill="{c}"/>
    <text x="{CARD_X + 53}" y="{y + 27}" font-family={FONT_KO!r}
          font-size="11" font-weight="bold" fill="#fff" text-anchor="middle">{e(step["step"])}</text>

    <!-- 에이전트명 -->
    <text x="{CARD_X + 20}" y="{y + 55}" font-family={FONT_MONO!r}
          font-size="11" fill="{TEXT_SUB}">{e(step["agent"])}</text>

    <!-- 라벨 -->
    <text x="{CARD_X + 210}" y="{y + 38}" font-family={FONT_KO!r}
          font-size="19" font-weight="bold" fill="{TEXT_MAIN}">{e(step["label"])}</text>

    <!-- 설명 -->
    <text x="{CARD_X + 210}" y="{y + 60}" font-family={FONT_KO!r}
          font-size="12" fill="{TEXT_SUB}">{e(step["desc1"])}</text>
    {desc2}

    <!-- 툴 배지 -->
    <rect x="{CARD_X + CARD_W - 180}" y="{y + 14}" width="158" height="22" rx="5"
          fill="{dark_bg}" stroke="{c}" stroke-width="0.9"/>
    <text x="{CARD_X + CARD_W - 101}" y="{y + 29}" font-family={FONT_MONO!r}
          font-size="11" font-weight="bold" fill="{c}" text-anchor="middle">{e(step["tool"])}</text>

    <!-- 출력 파일 배지 -->
    <rect x="{CARD_X + CARD_W - 200}" y="{y + 66}" width="178" height="24" rx="5"
          fill="{dark_bg}" stroke="{c}" stroke-width="0.8"/>
    <text x="{CARD_X + CARD_W - 111}" y="{y + 82}" font-family={FONT_MONO!r}
          font-size="11" fill="{c}" text-anchor="middle">{e(step["output"])}</text>
  </g>"""


def make_arrow(y: int, color: str) -> str:
    ax = SVG_W // 2
    y1 = y
    y2 = y + GAP
    return f"""
  <line x1="{ax}" y1="{y1}" x2="{ax}" y2="{y2 - 5}"
        stroke="{color}" stroke-width="2"/>
  <polygon points="{ax-6},{y2-7} {ax+6},{y2-7} {ax},{y2+1}" fill="{color}"/>"""


# ── 높이 계산 ─────────────────────────────────────────────────────────
total_cards_h = len(STEPS) * CARD_H + (len(STEPS) - 1) * GAP
OUTPUT_BOX_H  = 88
FOOTER_H      = 40
SVG_H = HEADER_H + total_cards_h + GAP + OUTPUT_BOX_H + FOOTER_H

# ── SVG 조립 ──────────────────────────────────────────────────────────
parts = []

parts.append(f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">

  <rect width="{SVG_W}" height="{SVG_H}" fill="{BG}"/>

  <!-- 헤더 -->
  <text x="{SVG_W//2}" y="56" font-family={FONT_KO!r}
        font-size="13" fill="{TEXT_SUB}" text-anchor="middle">브레인올로지</text>
  <text x="{SVG_W//2}" y="98" font-family={FONT_KO!r}
        font-size="30" font-weight="bold" fill="{TEXT_MAIN}" text-anchor="middle">상품 기획팀 파이프라인</text>
  <line x1="230" y1="110" x2="670" y2="110" stroke="{ACCENT}" stroke-width="2"/>

  <!-- 실행 커맨드 박스 -->
  <rect x="210" y="120" width="480" height="30" rx="7"
        fill="#EEEDF8" stroke="{BORDER}" stroke-width="1"/>
  <text x="{SVG_W//2}" y="140" font-family={FONT_MONO!r}
        font-size="13" fill="{ACCENT}" text-anchor="middle">/run-product-planning  문제=면역  타겟=초등</text>

  <!-- research_id -->
  <text x="{SVG_W//2}" y="178" font-family={FONT_MONO!r}
        font-size="11" fill="{TEXT_SUB}" text-anchor="middle">research_id = product-planning_{{YYYYMMDD_HHMMSS}}</text>
""")

# 카드 + 화살표
for i, step in enumerate(STEPS):
    y = HEADER_H + i * (CARD_H + GAP)
    parts.append(make_card(step, y))
    if i < len(STEPS) - 1:
        parts.append(make_arrow(y + CARD_H, step["color"]))

# 마지막 카드 → 출력 박스 화살표
last_card_bottom = HEADER_H + len(STEPS) * (CARD_H + GAP) - GAP + CARD_H
out_y = last_card_bottom + GAP

parts.append(make_arrow(last_card_bottom, ACCENT))

# 출력 박스
parts.append(f"""
  <!-- 출력 박스 -->
  <rect x="{CARD_X}" y="{out_y}" width="{CARD_W}" height="{OUTPUT_BOX_H}" rx="10"
        fill="#EEEDF8" stroke="{ACCENT}" stroke-width="1.5"/>
  <text x="{SVG_W//2}" y="{out_y + 22}" font-family={FONT_MONO!r}
        font-size="12" fill="{ACCENT}" text-anchor="middle">teams/product-planning/outputs/{{research_id}}/</text>
  <line x1="{CARD_X + 20}" y1="{out_y + 32}" x2="{CARD_X + CARD_W - 20}" y2="{out_y + 32}"
        stroke="{BORDER}" stroke-width="0.8"/>
""")

# 출력 파일 목록
spacing = (CARD_W - 40) // len(OUTPUT_FILES)
for j, (fname, clr) in enumerate(OUTPUT_FILES):
    fx = CARD_X + 20 + j * spacing
    parts.append(f"""  <text x="{fx}" y="{out_y + 58}" font-family={FONT_MONO!r}
        font-size="10" fill="{clr}">● {e(fname)}</text>
  <text x="{fx}" y="{out_y + 76}" font-family={FONT_MONO!r}
        font-size="9" fill="{TEXT_SUB}" opacity="0.7">Step {j+1}</text>
""")

# 푸터
parts.append(f"""
  <!-- 푸터 -->
  <text x="{SVG_W//2}" y="{SVG_H - 12}" font-family={FONT_KO!r}
        font-size="11" fill="#9090AA" text-anchor="middle">브레인올로지 상품 기획팀  ·  Claude Code 기반 멀티에이전트 파이프라인</text>

</svg>""")

# 저장
out_dir = Path("teams/product-planning")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "pipeline.svg"
out_path.write_text("".join(parts), encoding="utf-8")
print(f"saved → {out_path}")
