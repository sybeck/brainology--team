"""
reference_learner.py
노션 레퍼런스 DB에서 분석완료된 영상의 자막/나레이션을 읽고
타사/자사 기준으로 학습 인사이트를 추출해 brand/reference_learnings.md에 저장.

사용법:
    python tools/reference_learner.py --db_url <노션DB URL>
    python tools/reference_learner.py --db_id <DB ID>
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NOTION_API = "https://api.notion.com/v1"


# ── 노션 유틸 ─────────────────────────────────────────────

def notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

def notion_request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{NOTION_API}{path}", data=data,
        headers=notion_headers(), method=method
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def extract_page_id(url_or_id: str) -> str:
    match = re.search(r"([a-f0-9]{32})", url_or_id.replace("-", ""))
    if match:
        raw = match.group(1)
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
    return url_or_id


# ── DB 쿼리: 분석완료 페이지 조회 ─────────────────────────

def fetch_analyzed_pages(db_id: str) -> list[dict]:
    """분석완료=true인 페이지 전체 조회. 레퍼런스 속성 포함."""
    body = {"filter": {"property": "분석완료", "checkbox": {"equals": True}}}
    data = notion_request("POST", f"/databases/{db_id}/query", body)
    pages = data.get("results", [])
    print(f"  분석완료 페이지: {len(pages)}개")
    return pages


def get_reference_type(page: dict) -> str:
    """페이지의 레퍼런스 속성값 반환 (타사/자사/기타)"""
    props = page.get("properties", {})
    ref_prop = props.get("레퍼런스", {})
    ptype = ref_prop.get("type")
    if ptype == "select":
        sel = ref_prop.get("select")
        return sel.get("name", "기타") if sel else "기타"
    if ptype == "multi_select":
        items = ref_prop.get("multi_select", [])
        return items[0].get("name", "기타") if items else "기타"
    return "기타"


def get_page_title(page: dict) -> str:
    props = page.get("properties", {})
    for key in ["제목", "이름", "Name", "title"]:
        prop = props.get(key, {})
        title_list = prop.get("title", [])
        if title_list:
            return "".join(t.get("plain_text", "") for t in title_list)
    return page.get("id", "제목없음")


# ── 페이지 블록에서 분석 결과 추출 ────────────────────────

def extract_analysis_from_page(page_id: str) -> dict:
    """페이지 블록에서 나레이션/고정자막/흘러가는자막 추출"""
    data = notion_request("GET", f"/blocks/{page_id}/children?page_size=100")
    blocks = data.get("results", [])

    result = {"narration": [], "fixed": [], "flowing": []}
    current_section = None

    for block in blocks:
        btype = block.get("type", "")

        # 섹션 헤더 감지
        if btype in ("heading_2", "heading_3"):
            rich = block.get(btype, {}).get("rich_text", [])
            heading = "".join(r.get("plain_text", "") for r in rich)
            if "나레이션" in heading:
                current_section = "narration"
            elif "고정" in heading:
                current_section = "fixed"
            elif "흘러" in heading or "자막" in heading:
                current_section = "flowing"
            else:
                current_section = None
            continue

        # 불릿 아이템 텍스트 수집
        if btype == "bulleted_list_item" and current_section:
            rich = block.get("bulleted_list_item", {}).get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in rich).strip()
            if text:
                # 나레이션 타임라인은 [00:00-00:05] 형식 → 텍스트만 추출
                if current_section == "narration":
                    text = re.sub(r"^\[[\d:]+[-–][\d:]+\]\s*", "", text)
                result[current_section].append(text)

    return result


# ── Claude로 학습 인사이트 생성 ───────────────────────────

def synthesize_learnings(
    brand_entries: list[dict],   # 자사: {title, narration, fixed, flowing}
    competitor_entries: list[dict]  # 타사: 동일 구조
) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    brand_text = _format_entries(brand_entries, "자사")
    comp_text = _format_entries(competitor_entries, "타사")

    prompt = f"""너는 광고 카피라이팅 전략가야.
아래는 레퍼런스 영상들에서 추출한 자막과 나레이션 데이터야.

=== 자사 영상 ({len(brand_entries)}개) ===
{brand_text}

=== 타사 영상 ({len(competitor_entries)}개) ===
{comp_text}

위 데이터를 분석해서 아래 항목별로 학습 인사이트를 작성해줘.
마크다운 형식으로, 각 항목은 헤딩으로 구분해줘.

**[자사 학습 — 카피/스크립트 작성 시 반드시 반영]**
1. 자사 고유 키워드 & 표현법: 자주 사용되는 단어, 성분명 표현 방식, 효과 설명 방식
2. 문제 제기 방식: 어떤 상황/고통을 어떤 표현으로 제시하는지
3. 훅(Hook) 패턴: 첫 문장 구조와 톤
4. 나레이션 흐름 구조: 기승전결 패턴 (예: 고백→원인→성분→반전)
5. 고정자막 패턴: 어떤 정보를 고정 텍스트로 쓰는지 (브랜드, 보증, CTA 등)
6. 자막 문체: 어미, 감탄사, 말투 특징

**[타사 학습 — 구조와 기법만 참고, 내용은 절대 사용 금지]**
1. 훅 구조 기법: 어떤 방식으로 첫 주목을 끄는지 (질문형/숫자형/역발상 등)
2. 나레이션 전개 구조: 흐름 패턴 (감정선 구성 방식)
3. 자막 활용 기법: 강조 방식, 자막과 VO의 역할 분리 방식
4. 고정자막 활용법: 어떤 요소를 고정 텍스트로 쓰는지

**[종합 적용 가이드 — 스크립트 작성 시 체크리스트]**
- 자사 키워드/표현 중 반드시 포함할 것
- 자사 나레이션 구조 중 가장 효과적인 패턴
- 타사에서 배울 수 있는 구조적 기법 (내용 제외)
- 피해야 할 패턴 (반복되어 식상해진 표현 등)
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def _format_entries(entries: list[dict], label: str) -> str:
    if not entries:
        return f"({label} 데이터 없음)"
    parts = []
    for e in entries:
        narration = " / ".join(e["narration"][:10])  # 최대 10줄
        fixed = " | ".join(e["fixed"][:5])
        flowing = " / ".join(e["flowing"][:15])
        parts.append(
            f"[{e['title']}]\n"
            f"  나레이션: {narration}\n"
            f"  고정자막: {fixed or '없음'}\n"
            f"  흘러가는자막: {flowing}"
        )
    return "\n\n".join(parts)


# ── 메인 실행 ─────────────────────────────────────────────

def run(db_url: str) -> None:
    db_id = extract_page_id(db_url)
    print(f"\n레퍼런스 학습 시작  |  DB ID: {db_id}")
    print("=" * 50)

    pages = fetch_analyzed_pages(db_id)
    if not pages:
        print("분석완료된 페이지가 없습니다.")
        sys.exit(0)

    brand_entries = []
    competitor_entries = []

    for page in pages:
        ref_type = get_reference_type(page)
        title = get_page_title(page)
        print(f"  [{ref_type}] {title} 읽는 중...")

        analysis = extract_analysis_from_page(page["id"])
        entry = {"title": title, **analysis}

        if ref_type == "자사":
            brand_entries.append(entry)
        elif ref_type == "타사":
            competitor_entries.append(entry)

    print(f"\n자사 {len(brand_entries)}개 / 타사 {len(competitor_entries)}개 분석 중...")
    learnings = synthesize_learnings(brand_entries, competitor_entries)

    # 저장
    output_path = Path("brand/reference_learnings.md")
    output_path.parent.mkdir(exist_ok=True)

    header = f"""# 레퍼런스 학습 인사이트

> 자동 생성 | 자사 {len(brand_entries)}개 · 타사 {len(competitor_entries)}개 레퍼런스 분석
> 스크립트/카피 작성 전 반드시 이 파일을 읽고 반영할 것

---

"""
    output_path.write_text(header + learnings, encoding="utf-8")
    print(f"\n저장 완료: {output_path}")
    print(learnings[:300] + "...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_url", help="노션 DB URL")
    parser.add_argument("--db_id", help="노션 DB ID")
    args = parser.parse_args()
    url = args.db_url or args.db_id
    if not url:
        print("오류: --db_url 또는 --db_id 를 입력해주세요.")
        sys.exit(1)
    run(url)
