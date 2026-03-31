"""
브레인올로지 전 팀 파이프라인 SVG 생성기
출력: teams/{팀}/pipeline.svg
"""

from pathlib import Path

# ── 공통 스타일 ───────────────────────────────────────────────────────
BG        = "#FFFFFF"
CARD_BG   = "#F8F9FC"
BORDER    = "#D0D5E8"
TEXT_MAIN = "#1A1A2E"
TEXT_SUB  = "#55577A"
FONT_KO   = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
FONT_MONO = "'Consolas','Courier New',monospace"

SVG_W    = 900
CARD_X   = 50
CARD_W   = 800
CARD_H   = 104
GAP      = 18
HEADER_H = 210


def e(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def light_bg(hex_color):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    lr = r + (255 - r) * 85 // 100
    lg = g + (255 - g) * 85 // 100
    lb = b + (255 - b) * 85 // 100
    return f"#{lr:02x}{lg:02x}{lb:02x}"


def make_card(step: dict, y: int) -> str:
    c  = step["color"]
    lb = light_bg(c)

    note = ""
    if step.get("note"):
        note = f'<rect x="{CARD_X + 20}" y="{y + 38}" width="44" height="14" rx="3" fill="{c}" opacity="0.2"/>' \
               f'<text x="{CARD_X + 42}" y="{y + 48}" font-family={FONT_KO!r} font-size="8" fill="{c}" text-anchor="middle" font-weight="bold">{e(step["note"])}</text>'

    desc2 = ""
    if step.get("desc2"):
        desc2 = f'<text x="{CARD_X + 210}" y="{y + 80}" font-family={FONT_KO!r} font-size="12" fill="{TEXT_SUB}">{e(step["desc2"])}</text>'

    return f"""
  <g>
    <rect x="{CARD_X}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10"
          fill="{CARD_BG}" stroke="{c}" stroke-width="1.2"/>
    <rect x="{CARD_X}" y="{y}" width="8" height="{CARD_H}" rx="4" fill="{c}"/>
    <rect x="{CARD_X+4}" y="{y}" width="4" height="{CARD_H}" fill="{c}"/>

    <rect x="{CARD_X+20}" y="{y+12}" width="66" height="22" rx="5" fill="{c}"/>
    <text x="{CARD_X+53}" y="{y+27}" font-family={FONT_KO!r}
          font-size="11" font-weight="bold" fill="#fff" text-anchor="middle">{e(step["step"])}</text>
    {note}

    <text x="{CARD_X+20}" y="{y+55}" font-family={FONT_MONO!r}
          font-size="11" fill="{TEXT_SUB}">{e(step["agent"])}</text>

    <text x="{CARD_X+210}" y="{y+38}" font-family={FONT_KO!r}
          font-size="19" font-weight="bold" fill="{TEXT_MAIN}">{e(step["label"])}</text>
    <text x="{CARD_X+210}" y="{y+60}" font-family={FONT_KO!r}
          font-size="12" fill="{TEXT_SUB}">{e(step["desc1"])}</text>
    {desc2}

    <rect x="{CARD_X+CARD_W-180}" y="{y+14}" width="158" height="22" rx="5"
          fill="{lb}" stroke="{c}" stroke-width="0.9"/>
    <text x="{CARD_X+CARD_W-101}" y="{y+29}" font-family={FONT_MONO!r}
          font-size="11" font-weight="bold" fill="{c}" text-anchor="middle">{e(step["tool"])}</text>

    <rect x="{CARD_X+CARD_W-200}" y="{y+66}" width="178" height="24" rx="5"
          fill="{lb}" stroke="{c}" stroke-width="0.8"/>
    <text x="{CARD_X+CARD_W-111}" y="{y+82}" font-family={FONT_MONO!r}
          font-size="11" fill="{c}" text-anchor="middle">{e(step["output"])}</text>
  </g>"""


def make_arrow(y: int, color: str) -> str:
    ax = SVG_W // 2
    return f"""
  <line x1="{ax}" y1="{y}" x2="{ax}" y2="{y+GAP-5}" stroke="{color}" stroke-width="2"/>
  <polygon points="{ax-6},{y+GAP-7} {ax+6},{y+GAP-7} {ax},{y+GAP+1}" fill="{color}"/>"""


def generate_svg(
    team_name: str,
    title: str,
    cmd: str,
    run_id: str,
    steps: list,
    output_files: list,
    accent: str,
    out_path: str,
):
    total_h = HEADER_H + len(steps) * (CARD_H + GAP) + 88 + 40
    parts = []

    parts.append(f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{SVG_W}" height="{total_h}" viewBox="0 0 {SVG_W} {total_h}">

  <rect width="{SVG_W}" height="{total_h}" fill="{BG}"/>

  <text x="{SVG_W//2}" y="56" font-family={FONT_KO!r}
        font-size="13" fill="{TEXT_SUB}" text-anchor="middle">브레인올로지</text>
  <text x="{SVG_W//2}" y="98" font-family={FONT_KO!r}
        font-size="30" font-weight="bold" fill="{TEXT_MAIN}" text-anchor="middle">{e(title)}</text>
  <line x1="200" y1="110" x2="700" y2="110" stroke="{accent}" stroke-width="2"/>

  <rect x="180" y="120" width="540" height="30" rx="7"
        fill="{light_bg(accent)}" stroke="{BORDER}" stroke-width="1"/>
  <text x="{SVG_W//2}" y="140" font-family={FONT_MONO!r}
        font-size="13" fill="{accent}" text-anchor="middle">{e(cmd)}</text>

  <text x="{SVG_W//2}" y="178" font-family={FONT_MONO!r}
        font-size="11" fill="{TEXT_SUB}" text-anchor="middle">{e(run_id)}</text>
""")

    for i, step in enumerate(steps):
        y = HEADER_H + i * (CARD_H + GAP)
        parts.append(make_card(step, y))
        if i < len(steps) - 1:
            parts.append(make_arrow(y + CARD_H, step["color"]))

    last_bottom = HEADER_H + len(steps) * (CARD_H + GAP) - GAP + CARD_H
    out_y = last_bottom + GAP
    parts.append(make_arrow(last_bottom, accent))

    # 출력 박스
    out_lb = light_bg(accent)
    parts.append(f"""
  <rect x="{CARD_X}" y="{out_y}" width="{CARD_W}" height="88" rx="10"
        fill="{out_lb}" stroke="{accent}" stroke-width="1.5"/>
  <text x="{SVG_W//2}" y="{out_y+22}" font-family={FONT_MONO!r}
        font-size="12" fill="{accent}" text-anchor="middle">{e(output_files[0][0])}</text>
  <line x1="{CARD_X+20}" y1="{out_y+32}" x2="{CARD_X+CARD_W-20}" y2="{out_y+32}"
        stroke="{BORDER}" stroke-width="0.8"/>
""")

    sp = (CARD_W - 40) // max(len(output_files) - 1, 1)
    for j, (fname, clr) in enumerate(output_files[1:], 0):
        fx = CARD_X + 20 + j * sp
        parts.append(f"""  <text x="{fx}" y="{out_y+58}" font-family={FONT_MONO!r}
        font-size="10" fill="{clr}">● {e(fname)}</text>
  <text x="{fx}" y="{out_y+76}" font-family={FONT_MONO!r}
        font-size="9" fill="{TEXT_SUB}" opacity="0.7">Step {j+1}</text>
""")

    parts.append(f"""
  <text x="{SVG_W//2}" y="{total_h-12}" font-family={FONT_KO!r}
        font-size="11" fill="#9090AA" text-anchor="middle">브레인올로지 {e(team_name)}  ·  Claude Code 기반 멀티에이전트 파이프라인</text>
</svg>""")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("".join(parts), encoding="utf-8")
    print(f"saved → {out_path}")


# ════════════════════════════════════════════════════════════════════════
# 각 팀 파이프라인 정의
# ════════════════════════════════════════════════════════════════════════

# ── 1. 콘텐츠팀 ──────────────────────────────────────────────────────────
generate_svg(
    team_name="콘텐츠팀",
    title="콘텐츠팀 파이프라인",
    cmd="/run-contents  제품명=뉴턴젤리  타입=전체  이미지=5  영상=10",
    run_id="campaign_id = {제품명}_{YYYYMMDD_HHMMSS}",
    accent="#D9601A",
    steps=[
        {
            "step": "STEP 1", "note": "병렬",
            "agent": "contents-reference  +  contents-researcher",
            "label": "레퍼런스 · 소비자 리서치",
            "desc1": "경쟁사 광고 트렌드 · 부모 커뮤니티 페인포인트",
            "desc2": "소비자 언어 수집",
            "output": "references.json + consumer_insights.json",
            "tool": "WebSearch",
            "color": "#D9601A",
        },
        {
            "step": "STEP 2", "note": "",
            "agent": "contents-planner",
            "label": "콘텐츠 기획",
            "desc1": "이미지 컨셉 5개 + 영상 컨셉 10개",
            "desc2": "브랜드 가이드 · 제품 파일 · 리서치 결과 종합",
            "output": "content_briefs.json",
            "tool": "Read / Write",
            "color": "#E88A3A",
        },
        {
            "step": "STEP 3", "note": "",
            "agent": "contents-copywriter",
            "label": "카피라이팅",
            "desc1": "헤드라인 · 바디카피 · CTA 작성",
            "desc2": "이미지용 + 영상용 분리 작성",
            "output": "copy.json",
            "tool": "Read / Write",
            "color": "#E8A43A",
        },
        {
            "step": "STEP 4", "note": "분기",
            "agent": "contents-image  +  contents-scripter",
            "label": "에셋 제작",
            "desc1": "이미지: AI 생성 → 이미지 파일 저장",
            "desc2": "영상: Reel/스토리 스크립트 작성",
            "output": "image_{N}.png + video_{N}.json",
            "tool": "DALL·E / Write",
            "color": "#C95A0A",
        },
        {
            "step": "STEP 5", "note": "",
            "agent": "shared-distributor",
            "label": "배포",
            "desc1": "Slack 전송 · Notion 페이지 생성",
            "desc2": "",
            "output": "Slack + Notion",
            "tool": "Slack / Notion API",
            "color": "#8B3A0A",
        },
    ],
    output_files=[
        ("teams/contents/outputs/campaigns/{제품명}/{campaign_id}/", "#D9601A"),
        ("references.json",       "#D9601A"),
        ("consumer_insights.json","#E88A3A"),
        ("content_briefs.json",   "#E8A43A"),
        ("copy.json",             "#C95A0A"),
        ("image_{N}.png",         "#8B3A0A"),
    ],
    out_path="teams/contents/pipeline.svg",
)

# ── 2. 상품 기획팀 ────────────────────────────────────────────────────────
generate_svg(
    team_name="상품 기획팀",
    title="상품 기획팀 파이프라인",
    cmd="/run-product-planning  문제=면역  타겟=초등",
    run_id="research_id = product-planning_{YYYYMMDD_HHMMSS}",
    accent="#4B44CC",
    steps=[
        {
            "step": "STEP 1", "note": "",
            "agent": "product-market-researcher",
            "label": "정성 시장 조사",
            "desc1": "문제 프로파일 · 소비자 행동 · 시즌성",
            "desc2": "소비자 언어 수집",
            "output": "market_research.json",
            "tool": "WebSearch",
            "color": "#4A90D9",
        },
        {
            "step": "STEP 2", "note": "",
            "agent": "product-data-researcher",
            "label": "키워드 검색량 분석",
            "desc1": "문제 / 성분 / 해결 키워드 검색량 비교",
            "desc2": "네이버 검색광고 API · 월간 절대값",
            "output": "keyword_data.json",
            "tool": "Naver AD API",
            "color": "#5BB5A2",
        },
        {
            "step": "STEP 3", "note": "",
            "agent": "product-explorer",
            "label": "경쟁 제품 탐색",
            "desc1": "상위 노출 제품 5개 선정",
            "desc2": "가격 · 제형 · 성분 · 판매량 수집",
            "output": "product_exploration.json",
            "tool": "WebSearch",
            "color": "#E87D5A",
        },
        {
            "step": "STEP 4", "note": "",
            "agent": "product-review-analyst",
            "label": "소비자 리뷰 분석",
            "desc1": "네이버 쇼핑 · 블로그 · 카페",
            "desc2": "미충족 니즈 · 공통 인사이트 추출",
            "output": "consumer_reviews.json",
            "tool": "WebSearch",
            "color": "#C96BC9",
        },
        {
            "step": "STEP 5", "note": "",
            "agent": "product-ideator",
            "label": "신제품 아이디어 추천",
            "desc1": "1~4단계 종합 · 아이디어 3개 도출",
            "desc2": "컨셉 · 성분 · 차별화 포인트",
            "output": "product_ideas.json",
            "tool": "Read / Write",
            "color": "#6C9B3A",
        },
        {
            "step": "STEP 6", "note": "",
            "agent": "product-brief-writer",
            "label": "상품 기획서 작성",
            "desc1": "경쟁사 비교표 · 제품 스펙 · 가격 전략",
            "desc2": "출시 계획 · 리스크 · KPI",
            "output": "product_brief.md",
            "tool": "Read / Write",
            "color": "#E8C55A",
        },
        {
            "step": "STEP 7", "note": "",
            "agent": "shared-distributor",
            "label": "배포",
            "desc1": "Slack 전송 · Notion 페이지 생성",
            "desc2": "",
            "output": "Slack + Notion",
            "tool": "Slack / Notion API",
            "color": "#6C63FF",
        },
    ],
    output_files=[
        ("teams/product-planning/outputs/{research_id}/", "#4B44CC"),
        ("market_research.json",     "#4A90D9"),
        ("keyword_data.json",        "#5BB5A2"),
        ("product_exploration.json", "#E87D5A"),
        ("consumer_reviews.json",    "#C96BC9"),
        ("product_ideas.json",       "#6C9B3A"),
        ("product_brief.md",         "#E8C55A"),
    ],
    out_path="teams/product-planning/pipeline.svg",
)

# ── 3. 인플루언서팀 ───────────────────────────────────────────────────────
generate_svg(
    team_name="인플루언서팀",
    title="인플루언서팀 파이프라인",
    cmd="/run-influencer  제품명=뉴턴젤리  플랫폼=인스타그램  예산등급=B",
    run_id="campaign_id = influencer_{제품명}_{YYYYMMDD_HHMMSS}",
    accent="#B83A8A",
    steps=[
        {
            "step": "STEP 1", "note": "",
            "agent": "influencer-scout",
            "label": "인플루언서 탐색",
            "desc1": "플랫폼 · 팔로워 규모 · 육아 카테고리 필터링",
            "desc2": "예산등급별 후보군 수집 · 적합성 평가",
            "output": "influencer_list.json",
            "tool": "WebSearch",
            "color": "#E84A9A",
        },
        {
            "step": "STEP 2", "note": "",
            "agent": "influencer-brief-writer",
            "label": "협업 브리프 작성",
            "desc1": "Top 3 인플루언서 맞춤 브리프",
            "desc2": "제품 컨셉 · 콘텐츠 방향 · 조건 포함",
            "output": "collaboration_brief.md",
            "tool": "Read / Write",
            "color": "#C93A7A",
        },
        {
            "step": "STEP 3", "note": "",
            "agent": "influencer-tracker",
            "label": "성과 추적",
            "desc1": "캠페인 진행 중 노출 · 도달 · 전환 모니터링",
            "desc2": "성과 보고서 작성",
            "output": "performance_report.json",
            "tool": "WebSearch",
            "color": "#A02A5A",
        },
        {
            "step": "STEP 4", "note": "",
            "agent": "shared-distributor",
            "label": "배포",
            "desc1": "Slack 전송 (후보 목록 + 브리프 요약)",
            "desc2": "Notion 페이지 생성",
            "output": "Slack + Notion",
            "tool": "Slack / Notion API",
            "color": "#7A1A3A",
        },
    ],
    output_files=[
        ("teams/influencer/outputs/{campaign_id}/", "#B83A8A"),
        ("influencer_list.json",    "#E84A9A"),
        ("collaboration_brief.md",  "#C93A7A"),
        ("performance_report.json", "#A02A5A"),
        ("Slack + Notion",          "#7A1A3A"),
    ],
    out_path="teams/influencer/pipeline.svg",
)

# ── 4. 디자인팀 ───────────────────────────────────────────────────────────
generate_svg(
    team_name="디자인팀",
    title="디자인팀 파이프라인",
    cmd="/run-design  제품명=뉴턴젤리  용도=메타광고피드  수량=3",
    run_id="project_id = design_{제품명}_{YYYYMMDD_HHMMSS}",
    accent="#1A6ACC",
    steps=[
        {
            "step": "STEP 1", "note": "",
            "agent": "design-briefer",
            "label": "디자인 브리프 작성",
            "desc1": "용도 · 규격 · 핵심 메시지 · 컬러 방향 정의",
            "desc2": "금지 사항 · 참고 레퍼런스 포함",
            "output": "design_brief.md",
            "tool": "Read / Write",
            "color": "#4A90D9",
        },
        {
            "step": "STEP 2", "note": "",
            "agent": "design-image-creator",
            "label": "시안 생성",
            "desc1": "브리프 기반 AI 이미지 생성",
            "desc2": "수량만큼 시안 저장",
            "output": "image_{N}.png + design_assets.json",
            "tool": "DALL·E / Bash",
            "color": "#3A7AC9",
        },
        {
            "step": "STEP 3", "note": "",
            "agent": "design-reviewer",
            "label": "브랜드 검수",
            "desc1": "브랜드 가이드라인 적합성 검토",
            "desc2": "REVISION_NEEDED 항목 → 재생성 (최대 2회)",
            "output": "design_review.json",
            "tool": "Read / Write",
            "color": "#2A5A99",
        },
        {
            "step": "STEP 4", "note": "",
            "agent": "shared-distributor",
            "label": "배포",
            "desc1": "Slack 전송 (시안 이미지 첨부)",
            "desc2": "Notion 페이지 생성",
            "output": "Slack + Notion",
            "tool": "Slack / Notion API",
            "color": "#1A3A69",
        },
    ],
    output_files=[
        ("teams/design/outputs/{project_id}/", "#1A6ACC"),
        ("design_brief.md",    "#4A90D9"),
        ("image_{N}.png",      "#3A7AC9"),
        ("design_assets.json", "#2A5A99"),
        ("design_review.json", "#1A3A69"),
    ],
    out_path="teams/design/pipeline.svg",
)

# ── 5. 정산팀 ─────────────────────────────────────────────────────────────
generate_svg(
    team_name="정산팀",
    title="정산팀 파이프라인",
    cmd="/run-settlement  대상=홍길동  시작일=2026-02-01  종료일=2026-02-28",
    run_id="run_id = {YYYYMMDD_HHMMSS}  (기본: 전월 1일 ~ 말일)",
    accent="#1A8A6A",
    steps=[
        {
            "step": "STEP 1", "note": "",
            "agent": "settlement-target-fetcher",
            "label": "정산 대상 조회",
            "desc1": "Notion DB → 상태='활성중' 대상 전체 조회",
            "desc2": "`대상` 인자 있으면 해당 이름만 필터링",
            "output": "targets.json",
            "tool": "Notion API",
            "color": "#3AAA8A",
        },
        {
            "step": "STEP 2", "note": "",
            "agent": "settlement-sales-aggregator",
            "label": "매출 집계",
            "desc1": "Cafe24 로그인 → 기간별 매출 엑셀 다운로드",
            "desc2": "옵션별 집계 · 대상별 순차 처리",
            "output": "sales_{name}.json",
            "tool": "Playwright / Bash",
            "color": "#2A9A7A",
        },
        {
            "step": "STEP 3", "note": "",
            "agent": "settlement-report-writer",
            "label": "정산서 작성 · 배포",
            "desc1": "PDF 생성 (원천세 3.3% / 부가세 자동 계산)",
            "desc2": "Notion 업로드 · Slack 완료 알림",
            "output": "settlement_{name}.pdf",
            "tool": "fpdf2 / Notion / Slack",
            "color": "#1A7A5A",
        },
    ],
    output_files=[
        ("teams/settlement/outputs/{run_id}/", "#1A8A6A"),
        ("targets.json",          "#3AAA8A"),
        ("sales_{name}.json",     "#2A9A7A"),
        ("settlement_{name}.pdf", "#1A7A5A"),
        ("Notion + Slack",        "#0A5A3A"),
    ],
    out_path="teams/settlement/pipeline.svg",
)

print("\n✔ 전 팀 파이프라인 SVG 생성 완료")
