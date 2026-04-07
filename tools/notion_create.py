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

def _bullet(text: str) -> dict:
    return {
        "object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"text": {"content": text[:2000]}}]},
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

def _extract_subtitle_text(scene: dict) -> str:
    """씬에서 자막 텍스트를 추출. subtitle.text 또는 vo_or_caption 필드 모두 지원."""
    subtitle = scene.get("subtitle")
    if isinstance(subtitle, dict):
        return subtitle.get("text", "")
    if isinstance(subtitle, str):
        return subtitle
    return scene.get("vo_or_caption", "") or scene.get("caption", "")


def _calc_timecodes(scenes: list) -> list[str]:
    """각 씬의 duration_sec으로 누적 타임코드 [MM:SS-MM:SS] 계산."""
    result = []
    cursor = 0
    for scene in scenes:
        dur = scene.get("duration_sec") or 0
        start = cursor
        end = cursor + dur
        def fmt(s):
            return f"{s//60:02d}:{s%60:02d}"
        result.append(f"[{fmt(start)}-{fmt(end)}]")
        cursor = end
    return result


def build_video_blocks(vid: dict) -> list[dict]:
    blocks = []
    scenes = vid.get("scenes", [])

    # ── 1. 프로덕션 노트 (최상단) ─────────────────────────
    if vid.get("production_notes"):
        blocks.append(_h2("프로덕션 노트"))
        blocks.append(_para(vid["production_notes"]))
        blocks.append(_divider())

    # ── 2. 나레이션 타임라인 ──────────────────────────────
    timecodes = _calc_timecodes(scenes)
    blocks.append(_h2("나레이션 타임라인"))
    for i, scene in enumerate(scenes):
        tc = scene.get("timecode") or scene.get("time_range") or timecodes[i]
        audio = scene.get("audio", {})
        vo = audio.get("vo", "") if isinstance(audio, dict) else ""
        if not vo:
            vo = scene.get("vo_text", "") or scene.get("narration", "") or ""
        if vo and "(없음)" not in vo and vo != "null":
            blocks.append(_bullet(f"{tc}  {vo}"))
    blocks.append(_divider())

    # ── 3. 고정자막 / 4. 흘러가는자막 ────────────────────
    fixed_list = []
    flowing_list = []

    for scene in scenes:
        sub_text = _extract_subtitle_text(scene) or scene.get("on_screen_text", "")
        if not sub_text:
            continue
        for line in (l.strip() for l in sub_text.split("\n") if l.strip()):
            if "Brainology" in line or "브레인올로지" in line or "뉴턴젤리" in line:
                fixed_list.append(line)
            else:
                flowing_list.append(line)

    if fixed_list:
        blocks.append(_h2("고정자막"))
        for t in fixed_list:
            blocks.append(_bullet(t))
        blocks.append(_divider())

    if flowing_list:
        blocks.append(_h2("흘러가는자막"))
        for t in flowing_list:
            blocks.append(_bullet(t))
        blocks.append(_divider())

    # ── 5. 영상소스 ───────────────────────────────────────
    blocks.append(_h2("영상소스"))
    for i, scene in enumerate(scenes):
        tc = scene.get("timecode") or scene.get("time_range") or timecodes[i]
        visual = scene.get("visual") or scene.get("visual_description", "")
        if visual:
            blocks.append(_bullet(f"{tc}  {visual}"))
            mg = scene.get("motion_graphics", "")
            if mg and mg not in ("없음", ""):
                blocks.append(_bullet(f"  └ 모션그래픽: {mg}"))

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

def _get_global_max_num(notion, database_id: str) -> int:
    """Notion DB 전체에서 YYMMDD_NNNN_ 패턴의 최대 번호를 반환."""
    import re
    max_num = 0
    cursor = None
    while True:
        kwargs = {"filter": {"value": "page", "property": "object"}, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        res = notion.search(**kwargs)
        for p in res.get("results", []):
            if p.get("parent", {}).get("database_id", "").replace("-", "") != database_id.replace("-", ""):
                continue
            title_list = p["properties"].get("제목", {}).get("title", [])
            if not title_list:
                continue
            title = title_list[0].get("text", {}).get("content", "")
            m = re.search(r'_(\d{2,4})_', title)
            if m:
                max_num = max(max_num, int(m.group(1)))
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return max_num


def _build_page_title(created_at: str, global_num: int, concept_title: str,
                      product_name: str = "") -> str:
    """NNNN_제품명_스크립트제목 형식 제목 생성. 예: 0021_뉴턴젤리_영양제전쟁드디어끝났어요"""
    parts = [f"{global_num:04d}"]
    if product_name:
        parts.append(product_name)
    if concept_title:
        parts.append(concept_title)
    return "_".join(parts)


def create_page(notion, database_id: str, campaign_id: str, product_name: str,
                created_at: str, content_type: str, item: dict,
                global_num: int = 0) -> str | None:
    concept_title = item.get("concept_title") or item.get("brief_id", "")
    duration_sec = item.get("duration_sec")

    page_title = _build_page_title(created_at, global_num, concept_title, product_name)

    properties = {
        "제목": {"title": [{"text": {"content": page_title}}]},
        "제품명": {"rich_text": [{"text": {"content": product_name}}]},
        "생성일": {"date": {"start": created_at[:10]}},
        "유형": {"select": {"name": content_type}},
        "캠페인ID": {"rich_text": [{"text": {"content": campaign_id}}]},
    }
    if duration_sec is not None:
        properties["영상길이(초)"] = {"number": int(duration_sec)}
    video_type = item.get("video_type", "")
    if video_type:
        properties["영상유형"] = {"select": {"name": video_type}}

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
    parser.add_argument("--single_file", default=None,
                        help="단건 배포 시 해당 JSON 파일 경로 지정. 지정하면 이 파일 1개만 배포.")
    args = parser.parse_args()

    from notion_client import Client
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        print("[ERROR] NOTION_DATABASE_ID 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    campaign_json_path = Path(args.campaign_json)
    campaign_data = load_json(str(campaign_json_path))

    # campaign.json이 없으면 자동 생성
    if not campaign_json_path.exists() or not campaign_data:
        from datetime import date
        campaign_data = {
            "campaign_id": args.campaign_id,
            "product_name": args.product_name,
            "created_at": date.today().isoformat(),
        }
        campaign_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(campaign_json_path, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] campaign.json 자동 생성: {campaign_json_path}")

    campaign_dir = campaign_json_path.parent
    created_at = campaign_data.get("created_at", "") or __import__("datetime").date.today().isoformat()

    # 단건 배포 모드
    if args.single_file:
        single_data = load_json(args.single_file)
        if not single_data:
            print(f"[ERROR] 파일을 읽을 수 없습니다: {args.single_file}", file=sys.stderr)
            sys.exit(1)
        content_type = "이미지" if "image" in Path(args.single_file).name else "영상"
        video_files = [single_data] if content_type == "영상" else []
        image_files = [single_data] if content_type == "이미지" else []
    else:
        # 전체 배포 모드: 캠페인 디렉토리 스캔
        video_files = []
        for i in range(1, 20):
            data = load_json(str(campaign_dir / f"video_{i}.json"))
            if not data:
                data = load_json(str(campaign_dir / f"video_vid_{i}.json"))
            if not data:
                data = load_json(str(campaign_dir / f"script_vid_{i}.json"))
            if data:
                video_files.append(data)

        image_files = []
        for i in range(1, 10):
            data = load_json(str(campaign_dir / f"image_{i}.json"))
            if not data:
                data = load_json(str(campaign_dir / f"image_img_{i}.json"))
            if data:
                image_files.append(data)

    # 글로벌 순번: DB 전체 최대값 조회 후 이어서 부여
    global_num = _get_global_max_num(notion, database_id)

    page_urls = []

    for item in video_files:
        global_num += 1
        try:
            url = create_page(notion, database_id, args.campaign_id, args.product_name,
                              created_at, "영상", item, global_num)
            if url:
                page_urls.append(url)
                print(f"[OK] 영상 #{global_num:04d}: {item.get('concept_title', item.get('brief_id', ''))}  →  {url}")
        except Exception as e:
            print(f"[ERROR] 영상 페이지 실패 ({item.get('brief_id', '')}): {e}", file=sys.stderr)

    for item in image_files:
        global_num += 1
        try:
            url = create_page(notion, database_id, args.campaign_id, args.product_name,
                              created_at, "이미지", item, global_num)
            if url:
                page_urls.append(url)
                print(f"[OK] 이미지 #{global_num:04d}: {item.get('concept_title', item.get('brief_id', ''))}  →  {url}")
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
