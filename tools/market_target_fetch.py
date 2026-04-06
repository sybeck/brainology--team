"""
product-market-target 1단계: 웹 서치 + URL 읽기 자동화 스크립트

에이전트의 WebSearch × 7쿼리 + product-url-reader 위임 로직을 코드로 대체.
7개 쿼리 × 상위 4개 URL = 최대 28개 파일을 아래 경로에 저장:
  teams/product-planning/outputs/{research_id}/market/tmp/target_{N}.json

사용법:
  python tools/market_target_fetch.py \\
    --problem-keyword 산만함 \\
    --research-id test9_product-planning_20260403
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 7개 쿼리 (query_label, 검색어 템플릿)
QUERIES = [
    ("q1_general",  "{keyword} 문제 고민"),
    ("q2_영유아",   "영유아 {keyword}"),
    ("q3_어린이",   "어린이 {keyword}"),
    ("q4_청소년",   "청소년 {keyword}"),
    ("q5_20대",     "20대 {keyword}"),
    ("q6_3040대",   "30대 40대 {keyword}"),
    ("q7_시니어",   "시니어 {keyword}"),
]

URLS_PER_QUERY = 4
MAX_CONTENT_CHARS = 5000  # Claude에 전달할 최대 텍스트 길이


# ── Tavily 웹 서치 ────────────────────────────────────────────────────────────

def search_tavily(query: str) -> list[dict]:
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY 환경변수가 없습니다.")

    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": URLS_PER_QUERY,
            "search_depth": "basic",
            "include_raw_content": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])[:URLS_PER_QUERY]


# ── URL 가져오기 + HTML → 텍스트 ─────────────────────────────────────────────

def fetch_text(url: str) -> str:
    resp = httpx.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=15,
        follow_redirects=True,
    )
    resp.raise_for_status()

    text = resp.text[:120_000]
    # script / style 제거
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # 나머지 태그 제거
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CONTENT_CHARS]


# ── Claude Haiku로 항목 추출 ─────────────────────────────────────────────────

_claude = None


def get_claude() -> Anthropic:
    global _claude
    if _claude is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 없습니다.")
        _claude = Anthropic(api_key=api_key)
    return _claude


def extract_with_claude(content: str, query_label: str, problem_keyword: str) -> dict:
    prompt = f"""아래 웹 페이지 텍스트에서 지정 항목을 추출하세요.
문제 키워드: {problem_keyword}
query_label: {query_label}

추출 항목 (각 최대 200자):
- 타겟의 특징: 연령·성별·직업 등 타겟을 구분하는 특징
- 타겟의 라이프스타일: 타겟의 일상 패턴·환경·행동 양식
- 문제 양상 1: 타겟이 '{problem_keyword}' 문제를 겪는 구체적 양상 또는 맥락
- 문제 양상 2: 타겟이 '{problem_keyword}' 문제를 겪는 또 다른 구체적 양상 또는 맥락

관련성 평가:
- 높음: '{problem_keyword}' 관련 정보가 풍부하고 타겟 정보도 명확
- 중간: 일부 관련 정보 있음
- 낮음: '{problem_keyword}'와 거의 무관

웹 페이지 텍스트:
{content}

JSON만 반환 (다른 텍스트 없이):
{{
  "타겟의 특징": "...",
  "타겟의 라이프스타일": "...",
  "문제 양상 1": "...",
  "문제 양상 2": "...",
  "relevance": "높음 또는 중간 또는 낮음"
}}"""

    message = get_claude().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"JSON 파싱 실패: {raw[:200]}")
    return json.loads(match.group())


# ── URL 1개 처리 ──────────────────────────────────────────────────────────────

def process_url(
    url: str,
    n: int,
    query_label: str,
    problem_keyword: str,
    tmp_dir: Path,
    source_label: str,
) -> None:
    save_path = tmp_dir / f"target_{n}.json"

    try:
        content = fetch_text(url)
        extracted = extract_with_claude(content, query_label, problem_keyword)

        result = {
            "query_label": query_label,
            "source_label": source_label,
            "url": url,
            "status": "success",
            "extracted": {
                "타겟의 특징":        extracted.get("타겟의 특징", ""),
                "타겟의 라이프스타일": extracted.get("타겟의 라이프스타일", ""),
                "문제 양상 1":        extracted.get("문제 양상 1", ""),
                "문제 양상 2":        extracted.get("문제 양상 2", ""),
            },
            "relevance": extracted.get("relevance", "중간"),
        }
        tag = "OK"
    except Exception as e:
        result = {
            "query_label": query_label,
            "source_label": source_label,
            "url": url,
            "status": "failed",
            "error": str(e),
        }
        tag = "FAIL"

    save_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    [{tag}] target_{n}.json ← {url[:70]}")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="product-market-target: 웹 서치 + URL 읽기 자동화"
    )
    parser.add_argument("--problem-keyword", required=True, help="조사할 문제 키워드 (예: 산만함)")
    parser.add_argument("--research-id",     required=True, help="저장 경로 ID")
    args = parser.parse_args()

    keyword     = args.problem_keyword
    research_id = args.research_id

    tmp_dir = BASE_DIR / "teams/product-planning/outputs" / research_id / "market/tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    file_counter = 1
    query_counts: dict[str, int] = {}  # 검증용

    for query_label, query_template in QUERIES:
        query = query_template.replace("{keyword}", keyword)
        print(f"\n[{query_label}] 검색: {query}")

        try:
            results = search_tavily(query)
        except Exception as e:
            print(f"  [ERROR] Tavily 검색 실패: {e}")
            query_counts[query_label] = 0
            continue

        print(f"  → {len(results)}개 URL")
        query_counts[query_label] = len(results)

        for item in results:
            url = item.get("url", "")
            if not url:
                continue
            source_label = (item.get("title") or url)[:40]
            process_url(url, file_counter, query_label, keyword, tmp_dir, source_label)
            file_counter += 1
            time.sleep(0.3)  # rate limit 방지

    # ── 자기 검증 ──────────────────────────────────────────────────────────────
    print("\n── 자기 검증 ──")
    all_ok = True
    for query_label, _ in QUERIES:
        saved = [
            f for f in tmp_dir.glob("target_*.json")
            if json.loads(f.read_text(encoding="utf-8")).get("query_label") == query_label
        ]
        count = len(saved)
        expected = URLS_PER_QUERY
        status = "OK" if count >= expected else "FAIL"
        if count < expected:
            all_ok = False
        print(f"  {query_label}: {count}/{expected}  [{status}]")

    total = file_counter - 1
    print(f"\n[완료] 총 {total}개 파일 저장 → {tmp_dir}")
    if not all_ok:
        print("[경고] 일부 query_label의 파일 수가 부족합니다. 에이전트가 재처리합니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
