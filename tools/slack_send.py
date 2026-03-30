"""
Slack 전송 도구.
캠페인 결과물을 Slack 채널에 Block Kit 형식으로 전송.

사용법:
  python tools/slack_send.py \
    --campaign_id "멀티비타민키즈_20260328_120000" \
    --product_name "멀티비타민키즈" \
    --compliance_status "PASS" \
    --image_count 5 \
    --video_count 10 \
    --campaign_json "outputs/campaigns/멀티비타민키즈/campaign_id/campaign.json"
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def build_blocks(
    product_name: str,
    campaign_id: str,
    compliance_status: str,
    image_count: int,
    video_count: int,
    notion_url: str | None,
    image_paths: list[str],
) -> list[dict]:
    """Slack Block Kit 메시지 블록 생성."""

    status_emoji = {
        "PASS": ":white_check_mark:",
        "CONDITIONAL_PASS": ":large_yellow_circle:",
        "FAIL": ":x:",
        "PENDING_REVIEW": ":warning:",
    }.get(compliance_status, ":grey_question:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"광고 콘텐츠 제작 완료 — {product_name}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*제품명*\n{product_name}"},
                {"type": "mrkdwn", "text": f"*캠페인 ID*\n{campaign_id}"},
                {
                    "type": "mrkdwn",
                    "text": f"*컴플라이언스*\n{status_emoji} {compliance_status}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*생성 결과*\n이미지 {image_count}개 | 영상 스크립트 {video_count}개",
                },
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": ":robot_face: AI로 제작된 콘텐츠",
                }
            ],
        },
    ]

    if notion_url:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Notion에서 전체 결과 보기"},
                        "url": notion_url,
                        "style": "primary",
                    }
                ],
            }
        )

    if compliance_status in ("FAIL", "PENDING_REVIEW"):
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":warning: *컴플라이언스 검토 필요*\n일부 콘텐츠가 자동 검수를 통과하지 못했습니다. Notion 페이지에서 상세 내용을 확인하고 수동 검토해주세요.",
                },
            }
        )

    return blocks


def send_to_slack(
    webhook_url: str,
    product_name: str,
    campaign_id: str,
    compliance_status: str,
    image_count: int,
    video_count: int,
    notion_url: str | None,
    image_paths: list[str],
) -> bool:
    """Slack Incoming Webhook으로 메시지 전송."""
    try:
        import urllib.request

        blocks = build_blocks(
            product_name=product_name,
            campaign_id=campaign_id,
            compliance_status=compliance_status,
            image_count=image_count,
            video_count=video_count,
            notion_url=notion_url,
            image_paths=image_paths,
        )

        payload = {
            "text": f"[{product_name}] 광고 콘텐츠 제작 완료 — 컴플라이언스: {compliance_status}",
            "blocks": blocks,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"[OK] Slack 전송 완료: {product_name}")
                return True
            else:
                print(f"[ERROR] Slack 응답 오류: {response.status}", file=sys.stderr)
                return False

    except Exception as e:
        print(f"[ERROR] Slack 전송 실패: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Slack 전송 도구")
    parser.add_argument("--campaign_id", required=True)
    parser.add_argument("--product_name", required=True)
    parser.add_argument("--compliance_status", required=True)
    parser.add_argument("--image_count", type=int, default=5)
    parser.add_argument("--video_count", type=int, default=10)
    parser.add_argument("--campaign_json", required=True)

    args = parser.parse_args()

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[ERROR] SLACK_WEBHOOK_URL 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # campaign.json에서 Notion URL 읽기
    notion_url = None
    image_paths = []
    campaign_path = Path(args.campaign_json)
    if campaign_path.exists():
        with open(campaign_path, encoding="utf-8") as f:
            campaign_data = json.load(f)
        notion_url = campaign_data.get("notion_page_url")
        image_paths = campaign_data.get("image_assets", [])

    success = send_to_slack(
        webhook_url=webhook_url,
        product_name=args.product_name,
        campaign_id=args.campaign_id,
        compliance_status=args.compliance_status,
        image_count=args.image_count,
        video_count=args.video_count,
        notion_url=notion_url,
        image_paths=image_paths,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
