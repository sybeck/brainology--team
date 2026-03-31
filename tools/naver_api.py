"""
네이버 검색광고 키워드 도구 API — 월간 검색수 조회.

절대값(월간검색수 PC + 모바일)을 반환합니다.
DataLab(상대값)과 달리 실제 검색량을 확인할 수 있습니다.

환경변수:
  NAVER_AD_API_KEY      — 검색광고 API 액세스 라이선스 (API Key)
  NAVER_AD_SECRET_KEY   — 검색광고 API 시크릿 키
  NAVER_AD_CUSTOMER_ID  — 검색광고 고객 ID (숫자)

사용법:
  python tools/naver_api.py \\
    --keywords "어린이 면역,아이 감기,키즈 비타민" \\
    --output "teams/product-planning/outputs/{research_id}/naver_keyword.json"

API 키 발급:
  1. https://searchad.naver.com 로그인
  2. 우측 상단 계정명 클릭 → [설정] → [API 관리]
  3. API 라이선스 신청 → API Key / Secret Key / Customer ID 확인
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

KEYWORD_TOOL_URL = "https://api.searchad.naver.com/keywordstool"


def _signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    """네이버 검색광고 API HMAC-SHA256 서명 생성."""
    message = f"{timestamp}.{method}.{uri}"
    raw = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(raw).decode("utf-8")


def _headers(method: str = "GET", uri: str = "/keywordstool") -> dict:
    api_key = os.getenv("NAVER_AD_API_KEY", "")
    secret_key = os.getenv("NAVER_AD_SECRET_KEY", "")
    customer_id = os.getenv("NAVER_AD_CUSTOMER_ID", "")

    if not api_key or not secret_key or not customer_id:
        raise RuntimeError(
            "NAVER_AD_API_KEY / NAVER_AD_SECRET_KEY / NAVER_AD_CUSTOMER_ID "
            "환경변수가 없습니다.\n"
            "발급 방법:\n"
            "  1. https://searchad.naver.com 로그인\n"
            "  2. 우측 상단 계정명 → [설정] → [API 관리]\n"
            "  3. API 라이선스 신청 후 Key / Secret / Customer ID 복사\n"
            "  4. .env 파일에 추가"
        )

    timestamp = str(int(time.time() * 1000))
    sig = _signature(timestamp, method, uri, secret_key)

    return {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": sig,
        "Content-Type": "application/json; charset=UTF-8",
    }


def fetch_keyword_volume(keywords: list[str]) -> list[dict]:
    """키워드별 월간 검색수(PC + 모바일)를 조회합니다.

    네이버 검색광고 API의 hintKeywords는 단일 단어만 지원합니다.
    다중 단어 키워드(예: '어린이 면역')는 개별 단어로 분리해서 hint로 전송하고,
    API가 반환하는 연관 키워드 목록에서 원하는 키워드와 유사한 항목을 포함합니다.

    Args:
        keywords: 검색할 키워드 목록 (다중 단어 포함 가능)

    Returns:
        연관 키워드별 검색량 데이터 리스트
    """
    # 다중 단어 키워드를 개별 단어로 분리, 중복 제거
    hint_words: list[str] = []
    seen: set[str] = set()
    for kw in keywords:
        for word in kw.split():
            w = word.strip()
            if w and w not in seen:
                seen.add(w)
                hint_words.append(w)

    results = []
    # API는 1회 최대 5개 힌트 → 5개씩 청크
    for i in range(0, len(hint_words), 5):
        chunk = hint_words[i:i + 5]
        # 키워드는 개별 인코딩, 쉼표는 미인코딩 (단일 파라미터로 전송)
        kw_str = ",".join(urllib.parse.quote(w) for w in chunk)
        url = f"{KEYWORD_TOOL_URL}?showDetail=1&hintKeywords={kw_str}"

        resp = httpx.get(url, headers=_headers(), timeout=30)
        if not resp.is_success:
            print(f"[ERROR] status={resp.status_code}, body={resp.text}", file=sys.stderr)
            resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("keywordList", []))

    # relKeyword 기준으로 중복 제거
    seen_kw: set[str] = set()
    unique: list[dict] = []
    for item in results:
        rk = item.get("relKeyword", "")
        if rk not in seen_kw:
            seen_kw.add(rk)
            unique.append(item)

    return unique


def summarize(raw_list: list[dict]) -> list[dict]:
    """API 응답을 정리된 형태로 변환합니다."""
    out = []
    for item in raw_list:
        kw = item.get("relKeyword", "")
        pc = item.get("monthlyPcQcCnt", 0)
        mobile = item.get("monthlyMobileQcCnt", 0)

        # API가 "< 10" 같은 문자열로 반환하는 경우 처리
        def parse_count(v) -> int:
            if isinstance(v, int):
                return v
            s = str(v).replace(",", "").strip()
            if s.startswith("<"):
                return 5  # "< 10" → 5로 대체
            try:
                return int(float(s))
            except Exception:
                return 0

        pc_cnt = parse_count(pc)
        mobile_cnt = parse_count(mobile)
        total = pc_cnt + mobile_cnt

        # 검색량 수준 분류
        if total >= 100_000:
            level = "매우 높음"
        elif total >= 30_000:
            level = "높음"
        elif total >= 10_000:
            level = "중간"
        elif total >= 1_000:
            level = "낮음"
        else:
            level = "매우 낮음"

        out.append({
            "keyword": kw,
            "monthly_pc": pc_cnt,
            "monthly_mobile": mobile_cnt,
            "monthly_total": total,
            "search_level": level,
            "competition": item.get("compIdx", ""),        # 경쟁 강도 (낮음/중간/높음)
            "avg_cpc_pc": item.get("plAvgDepth", ""),      # PC 평균 클릭당 비용
            "avg_cpc_mobile": item.get("monthlyAveMobileClkCnt", ""),
        })

    # 월간 검색수 내림차순 정렬
    out.sort(key=lambda x: x["monthly_total"], reverse=True)
    return out


def main():
    parser = argparse.ArgumentParser(description="네이버 검색광고 키워드 월간 검색수 조회")
    parser.add_argument("--keywords", required=True,
                        help="쉼표 구분 키워드 목록. 예: '어린이 면역,아이 감기,키즈 비타민'")
    parser.add_argument("--output", required=True,
                        help="결과 저장 경로 (JSON)")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        print("[ERROR] 키워드를 입력해주세요.", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"[INFO] 네이버 검색광고 키워드 조회: {keywords}")
        raw = fetch_keyword_volume(keywords)
        summary = summarize(raw)

        output = {
            "queried_at": __import__("datetime").datetime.now().isoformat(),
            "keywords_queried": keywords,
            "results": summary,
        }

        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[OK] 키워드 검색량 데이터 저장 → {args.output}")
        print(f"{'키워드':<20} {'PC':>8} {'모바일':>10} {'합계':>10} {'수준'}")
        print("-" * 60)
        for item in summary:
            print(f"{item['keyword']:<20} {item['monthly_pc']:>8,} "
                  f"{item['monthly_mobile']:>10,} {item['monthly_total']:>10,} "
                  f"  {item['search_level']}")

    except RuntimeError as e:
        print(f"[SKIP] {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
