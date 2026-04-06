"""
메커니즘 조사용 웹문서 검색 스크립트.

네이버 웹문서 검색 API로 쿼리별 URL을 수집하고 결과를 JSON으로 저장합니다.
URL 읽기는 포함하지 않습니다 (product-url-reader 에이전트가 담당).

사용법:
  python tools/mechanism_search.py \
    --queries "teams/.../queries.json" \
    --output "teams/.../market/tmp/mechanism_urls.json" \
    --urls_per_query 3
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

HEADERS_NAVER = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}


def naver_search(query: str, display: int = 10) -> list[dict]:
    """네이버 웹문서 검색 → [{url, title}] 반환."""
    results: list[dict] = []
    seen: set[str] = set()

    api_url = (
        f"https://openapi.naver.com/v1/search/webkr"
        f"?query={quote(query)}&display={display}&sort=sim"
    )
    try:
        resp = httpx.get(api_url, headers=HEADERS_NAVER, timeout=10)
        data = resp.json()
        for item in data.get("items", []):
            link = item.get("link", "")
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            if link and link not in seen:
                seen.add(link)
                results.append({"url": link, "title": title})
    except Exception as e:
        print(f"  [WARN] 웹문서 검색 실패: {e}", file=sys.stderr)

    return results


def main():
    parser = argparse.ArgumentParser(description="메커니즘 조사 웹문서 검색")
    parser.add_argument("--queries", required=True, help="쿼리 JSON 파일 경로")
    parser.add_argument("--output", required=True, help="결과 URL 목록 저장 경로")
    parser.add_argument("--urls_per_query", type=int, default=3, help="쿼리당 선별 URL 수")
    args = parser.parse_args()

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[ERROR] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    with open(args.queries, "r", encoding="utf-8") as f:
        queries = json.load(f)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    all_results = []
    global_seen_urls: set[str] = set()

    for q in queries:
        query_text = q["query"]
        query_label = q["query_label"]
        problem_keyword = q.get("problem_keyword", "")
        print(f"[SEARCH] \"{query_text}\" ({query_label})")

        search_results = naver_search(query_text)

        # 글로벌 중복 제거 + 상위 N개 선별
        selected = []
        for item in search_results:
            if item["url"] not in global_seen_urls:
                global_seen_urls.add(item["url"])
                selected.append(item)
            if len(selected) >= args.urls_per_query:
                break

        print(f"  검색 결과: {len(search_results)}개 → 선별: {len(selected)}개")

        all_results.append({
            "query": query_text,
            "query_label": query_label,
            "problem_keyword": problem_keyword,
            "urls": selected,
        })

    # 결과 저장
    output = {
        "searched_at": datetime.now().isoformat(),
        "total_queries": len(queries),
        "total_urls": sum(len(r["urls"]) for r in all_results),
        "results": all_results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] 총 {output['total_urls']}개 URL 수집 → {args.output}")
    for r in all_results:
        for u in r["urls"]:
            print(f"  [{r['query_label']}] {u['url']}")


if __name__ == "__main__":
    main()
