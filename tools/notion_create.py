"""
Notion 페이지 생성 도구.
스크립트/이미지 1개 = Notion 페이지 1개.

사용법:
  python tools/notion_create.py \
    --campaign_id "뉴턴젤리_20260329_203641" \
    --product_name "뉴턴젤리" \
    --campaign_json "outputs/campaigns/뉴턴젤리/뉴턴젤리_20260329_203641/campaign.json"

Notion DB 필요 컬럼:
  - 제목     : Title (기본 제목 컬럼)
  - 제품명   : Text
  - 생성일   : Date
  - 유형     : Select
  - 영상길이(초) : Number
  - 캠페인ID : Text
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ── 블록 헬퍼 ────────────────────────────────────────────

def _para(text: str) -> dict:
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text[:2000]}}]},
    }

def _h2(text: str) -> dict:
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": text}}]},
    }

def _h3(text: str) -> dict:
    return {
        "object": "block", "type": "heading_3",
        "heading_3": {"rich_text": [{"text": {"content": text}}]},
    }

def _quote(text: str) -> dict:
    return {
        "object": "block", "type": "quote",
        "quote": {"rich_text": [{"text": {"content": text[:2000]}}]},
    }

def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}

def _callout(text: str, emoji: str = "📝") -> dict:
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"text": {"content": text[:2000]}}],
            "icon": {"emoji": emoji},
        },
    }


# ── 영상 스크립트 본문 블록 ───────────────────────────────

def build_video_blocks(vid: dict) -> list[dict]:
    blocks = []

    # 기본 정보
    blocks.append(_h2("기본 정보"))
    info = "\n".join(filter(None, [
        f"outline_type: {vid.get('outline_type', '')}",
        f"appearance_type: {vid.get('appearance_type', '')}",
        f"narration: {vid.get('narration', '')}",
        f"format: {vid.get('format', '')}",
    ]))
    blocks.append(_para(info))
    blocks.append(_divider())

    # 후킹 문구
    hook = vid.get("hook", "")
    if hook:
        blocks.append(_h2("후킹 문구"))
        blocks.append(_callout(hook, "🎣"))
        blocks.append(_divider())

    # VO 전문
    vo = vid.get("vo_full_transcript", "")
    if vo:
        blocks.append(_h2("VO 전문"))
        blocks.append(_quote(vo))
        blocks.append(_divider())

    # 씬별 스크립트
    scenes = vid.get("scenes", [])
    if scenes:
        blocks.append(_h2("씬별 스크립트"))
        for scene in scenes:
            label = scene.get("label", "")
            time_range = scene.get("time_range", "")
            blocks.append(_h3(f"씬 {scene.get('scene_no', '')}  [{label}]  {time_range}"))
            if scene.get("visual"):
                blocks.append(_para(f"📷 비주얼\n{scene['visual']}"))
            if scene.get("vo_or_caption"):
                blocks.append(_para(f"🎙 VO / 자막\n{scene['vo_or_caption']}"))
            if scene.get("direction"):
                blocks.append(_para(f"🎬 연출\n{scene['direction']}"))
            if scene.get("bgm_direction"):
                blocks.append(_para(f"🎵 BGM\n{scene['bgm_direction']}"))
        blocks.append(_divider())

    # 전체 톤
    if vid.get("overall_tone"):
        blocks.append(_h2("전체 톤"))
        blocks.append(_para(vid["overall_tone"]))

    # 프로덕션 노트
    if vid.get("production_notes"):
        blocks.append(_h2("프로덕션 노트"))
        blocks.append(_para(vid["production_notes"]))

    return blocks


# ── 이미지 광고 본문 블록 ─────────────────────────────────

def build_image_blocks(img: dict) -> list[dict]:
    blocks = []

    blocks.append(_h2("기본 정보"))
    info = "\n".join(filter(None, [
        f"angle: {img.get('angle', '')}",
        f"reframe_type: {img.get('reframe_type', '')}",
        f"target_emotion: {img.get('target_emotion', '')}",
    ]))
    blocks.append(_para(info))
    blocks.append(_divider())

    if img.get("core_message"):
        blocks.append(_h2("핵심 메시지"))
        blocks.append(_callout(img["core_message"], "💡"))
        blocks.append(_divider())

    if img.get("visual_direction"):
        blocks.append(_h2("비주얼 방향"))
        blocks.append(_para(img["visual_direction"]))

    if img.get("key_copy_direction"):
        blocks.append(_h2("카피 방향"))
        blocks.append(_para(img["key_copy_direction"]))

    return blocks


# ── 페이지 1개 생성 ───────────────────────────────────────

def create_page(notion, database_id: str, campaign_id: str, product_name: str,
                created_at: str, content_type: str, item: dict) -> str | None:
    concept_title = item.get("concept_title") or item.get("brief_id", "")
    duration_sec = item.get("duration_sec")

    properties = {
        "제목": {"title": [{"text": {"content": concept_title}}]},
        "제품명": {"rich_text": [{"text": {"content": product_name}}]},
        "생성일": {"date": {"start": created_at[:10]}},
        "유형": {"select": {"name": content_type}},
        "캠페인ID": {"rich_text": [{"text": {"content": campaign_id}}]},
    }
    if duration_sec is not None:
        properties["영상길이(초)"] = {"number": int(duration_sec)}

    blocks = build_video_blocks(item) if content_type == "영상" else build_image_blocks(item)

    response = notion.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=blocks[:100],
    )
    return response.get("url", "")


# ── main ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign_id", required=True)
    parser.add_argument("--product_name", required=True)
    parser.add_argument("--campaign_json", required=True)
    args = parser.parse_args()

    from notion_client import Client
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        print("[ERROR] NOTION_DATABASE_ID 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    campaign_data = load_json(args.campaign_json)
    campaign_dir = Path(args.campaign_json).parent
    created_at = campaign_data.get("created_at", "")

    # 영상 파일 수집
    video_files = []
    for i in range(1, 20):
        data = load_json(str(campaign_dir / f"video_{i}.json"))
        if not data:
            data = load_json(str(campaign_dir / f"video_vid_{i}.json"))
        if data:
            video_files.append(data)

    # 이미지 파일 수집
    image_files = []
    for i in range(1, 10):
        data = load_json(str(campaign_dir / f"image_{i}.json"))
        if not data:
            data = load_json(str(campaign_dir / f"image_img_{i}.json"))
        if data:
            image_files.append(data)

    page_urls = []

    for item in video_files:
        try:
            url = create_page(notion, database_id, args.campaign_id, args.product_name,
                              created_at, "영상", item)
            if url:
                page_urls.append(url)
                print(f"[OK] 영상: {item.get('concept_title', item.get('brief_id', ''))}  →  {url}")
        except Exception as e:
            print(f"[ERROR] 영상 페이지 실패 ({item.get('brief_id', '')}): {e}", file=sys.stderr)

    for item in image_files:
        try:
            url = create_page(notion, database_id, args.campaign_id, args.product_name,
                              created_at, "이미지", item)
            if url:
                page_urls.append(url)
                print(f"[OK] 이미지: {item.get('concept_title', item.get('brief_id', ''))}  →  {url}")
        except Exception as e:
            print(f"[ERROR] 이미지 페이지 실패 ({item.get('brief_id', '')}): {e}", file=sys.stderr)

    if page_urls:
        campaign_data["notion_page_urls"] = page_urls
        with open(args.campaign_json, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f, ensure_ascii=False, indent=2)
        print(f"\n총 {len(page_urls)}개 페이지 생성 완료.")
        sys.exit(0)
    else:
        print("[ERROR] 생성된 페이지 없음", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
