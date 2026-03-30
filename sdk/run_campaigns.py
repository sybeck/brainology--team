"""
Claude Agent SDK 자동화 진입점.
Claude Code CLI 없이 프로그래매틱으로 광고 콘텐츠 파이프라인을 실행.
CI/CD, 스케줄 실행, 배치 처리에 활용.

사용법:
  # 모든 제품 처리
  python sdk/run_campaigns.py

  # 특정 제품만
  python sdk/run_campaigns.py --product 멀티비타민키즈

  # 드라이런 (실제 생성 없이 파이프라인 확인)
  python sdk/run_campaigns.py --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Claude Agent SDK
try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    print("[ERROR] anthropic 패키지가 없습니다. pip install anthropic 실행 후 재시도하세요.")
    sys.exit(1)


PIPELINE_PROMPT = """
당신은 어린이 영양제 메타 광고 콘텐츠 제작 팀의 오케스트레이터입니다.
CLAUDE.md의 지시문에 따라 다음 제품에 대해 광고 콘텐츠 파이프라인을 실행하세요.

제품명: {product_name}
제품 파일: {product_path}
캠페인 ID: {campaign_id}

실행 순서:
1. reference-collector와 consumer-researcher 에이전트를 병렬로 실행
2. content-planner로 이미지 5개 + 영상 10개 컨셉 기획
3. copywriter로 각 컨셉별 카피 작성
4. image-creator로 이미지 5장 생성 (python tools/image_generation.py 호출)
5. video-scripter로 영상 스크립트 10개 작성
6. compliance-reviewer로 전체 검수 (FAIL 시 최대 3회 수정)
7. distributor로 Slack 전송 + Notion 기록

CLAUDE.md와 brand/brand_guide.md를 반드시 먼저 읽으세요.
""".strip()


async def run_product_pipeline(product_name: str, product_path: str, campaign_id: str, dry_run: bool = False) -> dict:
    """단일 제품에 대해 광고 콘텐츠 파이프라인 실행."""
    print(f"\n{'='*60}")
    print(f"[시작] 제품: {product_name} | 캠페인 ID: {campaign_id}")
    print(f"{'='*60}")

    if dry_run:
        print(f"[DRY RUN] 실제 실행 없이 파이프라인 확인만 합니다.")
        return {"product_name": product_name, "campaign_id": campaign_id, "status": "dry_run"}

    # outputs 폴더 생성
    output_dir = Path(f"outputs/campaigns/{product_name}/{campaign_id}")
    image_dir = Path(f"outputs/images/{product_name}/{campaign_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = PIPELINE_PROMPT.format(
        product_name=product_name,
        product_path=product_path,
        campaign_id=campaign_id,
    )

    result = {"product_name": product_name, "campaign_id": campaign_id, "status": "unknown"}

    try:
        # Claude Agent SDK로 파이프라인 실행
        # setting_sources: ["project"]로 CLAUDE.md, .claude/agents/, .claude/skills/ 자동 로드
        async with client.beta.messages.stream(
            model="claude-opus-4-6",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                print(text, end="", flush=True)

        print(f"\n[완료] {product_name}")

        # campaign.json에서 결과 읽기
        campaign_json = output_dir / "campaign.json"
        if campaign_json.exists():
            with open(campaign_json, encoding="utf-8") as f:
                campaign_data = json.load(f)
            result.update({
                "status": campaign_data.get("overall_compliance_status", "UNKNOWN"),
                "notion_url": campaign_data.get("notion_page_url"),
                "image_count": campaign_data.get("image_count", 0),
                "video_count": campaign_data.get("video_script_count", 0),
            })
        else:
            result["status"] = "COMPLETED_NO_JSON"

    except Exception as e:
        print(f"\n[ERROR] {product_name} 파이프라인 실패: {e}", file=sys.stderr)
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


async def run_all_campaigns(target_product: str | None = None, dry_run: bool = False):
    """모든 제품(또는 특정 제품)에 대해 파이프라인 실행."""
    from datetime import datetime

    products_dir = Path("products")
    if not products_dir.exists():
        print("[ERROR] products/ 폴더가 없습니다.")
        sys.exit(1)

    product_files = list(products_dir.glob("*.md"))
    if not product_files:
        print("[ERROR] products/ 폴더에 제품 파일(.md)이 없습니다.")
        sys.exit(1)

    # 특정 제품만 실행
    if target_product:
        product_files = [p for p in product_files if p.stem == target_product]
        if not product_files:
            print(f"[ERROR] '{target_product}' 제품 파일을 찾을 수 없습니다.")
            print(f"현재 제품 목록: {[p.stem for p in Path('products').glob('*.md')]}")
            sys.exit(1)

    print(f"[시작] 총 {len(product_files)}개 제품 처리")
    print(f"제품 목록: {[p.stem for p in product_files]}")

    results = []
    for product_file in product_files:
        product_name = product_file.stem
        campaign_id = f"{product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        result = await run_product_pipeline(
            product_name=product_name,
            product_path=str(product_file),
            campaign_id=campaign_id,
            dry_run=dry_run,
        )
        results.append(result)

    # 최종 결과 요약
    print(f"\n{'='*60}")
    print("최종 결과 요약")
    print(f"{'='*60}")

    pass_count = sum(1 for r in results if r.get("status") == "PASS")
    fail_count = sum(1 for r in results if r.get("status") in ("FAIL", "PENDING_REVIEW"))
    error_count = sum(1 for r in results if r.get("status") == "ERROR")

    for r in results:
        status = r.get("status", "UNKNOWN")
        notion_url = r.get("notion_url", "N/A")
        img = r.get("image_count", 0)
        vid = r.get("video_count", 0)
        print(f"  {r['product_name']}: {status} | 이미지 {img}개 | 스크립트 {vid}개 | {notion_url}")

    print(f"\n총계: PASS {pass_count} | 검토 필요 {fail_count} | 오류 {error_count}")

    return results


def main():
    parser = argparse.ArgumentParser(description="광고 콘텐츠 자동 생성 파이프라인 (Agent SDK)")
    parser.add_argument("--product", help="특정 제품명만 처리 (없으면 전체 products/ 처리)")
    parser.add_argument("--dry-run", action="store_true", help="실제 생성 없이 파이프라인 흐름만 확인")

    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[ERROR] ANTHROPIC_API_KEY 환경변수가 없습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    asyncio.run(run_all_campaigns(target_product=args.product, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
