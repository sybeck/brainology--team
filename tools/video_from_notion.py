"""
video_from_notion.py
노션 페이지의 영상 → 자막(OCR) + 나레이션(Whisper) 분석 → 같은 페이지에 추가

사용법:
    python tools/video_from_notion.py --page_url <노션 페이지 URL>
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_API = "https://api.notion.com/v1"

_FFMPEG_BASE = "C:/Users/k8521/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin"
FFMPEG = f"{_FFMPEG_BASE}/ffmpeg.exe"
FFPROBE = f"{_FFMPEG_BASE}/ffprobe.exe"


# ── 노션 유틸 ─────────────────────────────────────────────

def notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

def notion_get(path: str) -> dict:
    req = urllib.request.Request(f"{NOTION_API}{path}", headers=notion_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def notion_patch(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{NOTION_API}{path}", data=data, headers=notion_headers(), method="PATCH")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def extract_page_id(url_or_id: str) -> str:
    match = re.search(r"([a-f0-9]{32})", url_or_id.replace("-", ""))
    if match:
        raw = match.group(1)
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
    return url_or_id


# ── 영상 찾기 & 다운로드 ──────────────────────────────────

def find_video_in_page(page_id: str) -> tuple[str, str] | None:
    data = notion_get(f"/blocks/{page_id}/children?page_size=100")
    for block in data.get("results", []):
        btype = block.get("type")
        if btype == "video":
            video = block["video"]
            if video.get("type") == "file":
                return video["file"]["url"], block["id"]
            elif video.get("type") == "external":
                return video["external"]["url"], block["id"]
        if btype == "file":
            name = block.get("file", {}).get("name", "")
            if any(name.lower().endswith(ext) for ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]):
                file_block = block["file"]
                if file_block.get("type") == "file":
                    return file_block["file"]["url"], block["id"]
    return None

def download_video(url: str, dest: str) -> str:
    print("  영상 다운로드 중...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    print(f"  다운로드 완료: {os.path.getsize(dest)/1024/1024:.1f}MB")
    return dest


# ── FFmpeg 유틸 ───────────────────────────────────────────

def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, check=True)

def get_duration(video_path: str) -> float:
    result = run_cmd([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", video_path])
    return float(result.stdout.decode().strip())

def extract_audio(video_path: str, out_dir: str) -> str:
    audio_path = os.path.join(out_dir, "audio.mp3")
    run_cmd([FFMPEG, "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k", audio_path])
    return audio_path

def extract_frames(video_path: str, out_dir: str) -> list[dict]:
    """1초 간격으로 프레임 추출 — 자막 변화를 놓치지 않기 위해 1초 단위 사용"""
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    run_cmd([FFMPEG, "-y", "-i", video_path, "-vf", "fps=1", "-q:v", "2",
             os.path.join(frames_dir, "frame_%04d.jpg")])
    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    return [
        {"path": str(f), "timecode_sec": i,
         "timecode": f"{i // 60:02d}:{i % 60:02d}"}
        for i, f in enumerate(frames)
    ]


# ── Step 1: OCR 자막 추출 ─────────────────────────────────

def extract_subtitles_ocr(frames: list[dict]) -> list[dict]:
    """
    EasyOCR로 각 프레임에서 텍스트 추출.
    - 상단(0~35%) / 하단(65~100%) 영역 모두 캡처
    - 연속된 동일 자막은 하나로 합쳐 timecode 범위로 표시
    - 특수문자(!!! 등) 포함
    """
    import easyocr
    import numpy as np
    from PIL import Image

    print("  OCR 모델 로딩 중... (첫 실행 시 약 1분 소요)")
    reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)

    raw_entries = []  # {timecode_sec, timecode, position, text}

    for frame in frames:
        img = Image.open(frame["path"])
        w, h = img.size

        # 메모리 절약을 위해 너비 720으로 리사이즈
        if w > 720:
            ratio = 720 / w
            img = img.resize((720, int(h * ratio)), Image.LANCZOS)
            w, h = img.size

        img_array = np.array(img)

        results = reader.readtext(img_array, detail=1, paragraph=False)

        for (bbox, text, conf) in results:
            if conf < 0.3 or not text.strip():
                continue
            text = text.strip()

            # 바운딩박스 중심 y 좌표로 위치 판단
            ys = [pt[1] for pt in bbox]
            center_y = sum(ys) / len(ys)
            rel_y = center_y / h  # 0=상단, 1=하단

            if rel_y < 0.35:
                position = "top"
            elif rel_y > 0.65:
                position = "bottom"
            else:
                position = "middle"

            raw_entries.append({
                "timecode_sec": frame["timecode_sec"],
                "timecode": frame["timecode"],
                "position": position,
                "text": text,
                "conf": round(conf, 2)
            })

    # 연속된 동일 자막 병합 (같은 텍스트가 여러 프레임에 걸쳐 나오는 경우)
    merged = _merge_consecutive_subtitles(raw_entries)
    print(f"  OCR 자막 추출 완료: {len(merged)}개 항목")
    return merged


def _merge_consecutive_subtitles(entries: list[dict]) -> list[dict]:
    """같은 위치+텍스트가 연속된 프레임에 걸쳐 있으면 하나로 합침"""
    if not entries:
        return []

    # position별로 그룹화 후 병합
    from collections import defaultdict
    by_position = defaultdict(list)
    for e in entries:
        by_position[e["position"]].append(e)

    merged = []
    for position, items in by_position.items():
        items.sort(key=lambda x: x["timecode_sec"])
        current = None
        for item in items:
            if current is None:
                current = dict(item)
                current["timecode_end"] = item["timecode"]
                current["timecode_end_sec"] = item["timecode_sec"]
            else:
                # 텍스트 유사도 확인 (완전 동일 or 90% 유사)
                sim = difflib.SequenceMatcher(None, current["text"], item["text"]).ratio()
                is_consecutive = item["timecode_sec"] - current["timecode_end_sec"] <= 2
                if sim > 0.85 and is_consecutive:
                    current["timecode_end"] = item["timecode"]
                    current["timecode_end_sec"] = item["timecode_sec"]
                else:
                    merged.append(current)
                    current = dict(item)
                    current["timecode_end"] = item["timecode"]
                    current["timecode_end_sec"] = item["timecode_sec"]
        if current:
            merged.append(current)

    # timecode 범위 문자열 생성
    for m in merged:
        start = m["timecode"]
        end = m.get("timecode_end", m["timecode"])
        m["timecode_range"] = start if start == end else f"{start}-{end}"

    merged.sort(key=lambda x: (x["timecode_sec"], x["position"]))
    return merged


# ── Step 2: Claude Vision 자막 추출 ──────────────────────

def _chunks(lst: list, n: int):
    """리스트를 n개씩 나눔"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def extract_subtitles_vision(frames: list[dict]) -> list[dict]:
    """
    Claude Vision으로 각 프레임에서 텍스트 추출.
    5프레임씩 배치로 묶어 1번 호출 → 5배 속도, Haiku 모델 사용.
    반환: [{text, count, first_frame}, ...]
    """
    import anthropic
    import base64
    import io
    from PIL import Image

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    text_tracker: dict[str, dict] = {}
    BATCH = 5

    for batch in _chunks(frames, BATCH):
        content_blocks = []

        for i, frame in enumerate(batch):
            img = Image.open(frame["path"])
            w, h = img.size
            if w > 720:
                ratio = 720 / w
                img = img.resize((720, int(h * ratio)), Image.LANCZOS)
                w, h = img.size

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            content_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg",
                           "data": base64.standard_b64encode(buf.getvalue()).decode()}
            })

        labels = "\n".join(f"프레임{i+1}:" for i in range(len(batch)))
        content_blocks.append({"type": "text", "text": (
            f"위 {len(batch)}개 프레임 각각에서 화면에 보이는 모든 텍스트를 추출해줘.\n"
            "자막, 고정 타이틀, 버튼, 배너 텍스트 모두 포함.\n"
            "형식 (텍스트 없으면 해당 줄 생략):\n"
            + labels + "\n\n"
            "각 프레임 아래에 텍스트를 한 줄에 하나씩. 설명 없이."
        )})

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=800,
            messages=[{"role": "user", "content": content_blocks}]
        )

        current_frame_idx = 0
        current_frame = batch[0]
        for line in msg.content[0].text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # "프레임N:" 헤더 감지
            header_match = re.match(r'^프레임(\d+)\s*[:：]?\s*(.*)', line)
            if header_match:
                idx = int(header_match.group(1)) - 1
                if 0 <= idx < len(batch):
                    current_frame_idx = idx
                    current_frame = batch[current_frame_idx]
                remainder = header_match.group(2).strip()
                if remainder:
                    line = remainder
                else:
                    continue
            text = line
            if not text:
                continue
            matched_key = next(
                (k for k in text_tracker if difflib.SequenceMatcher(None, text, k).ratio() > 0.85),
                None
            )
            if matched_key:
                text_tracker[matched_key]["count"] += 1
            else:
                text_tracker[text] = {"count": 1, "first_frame": current_frame["timecode_sec"]}

    result = sorted(
        [{"text": t, "count": v["count"], "first_frame": v["first_frame"]} for t, v in text_tracker.items()],
        key=lambda x: x["first_frame"]
    )
    print(f"  Claude Vision 자막 추출 완료: {len(result)}개 (원본)")
    return result


def review_subtitles(raw: list[dict], narration: str) -> dict:
    """
    추출된 자막을 Claude가 검수:
    - 소품/배경 텍스트 제거 (책 제목, 제품 라벨, 벽 글씨 등)
    - 내용 연결성 없는 항목 제거
    - 고정자막(3프레임 이상) vs 흘러가는자막으로 분리
    반환: {fixed: [str], flowing: [str]}
    """
    import anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    raw_text = "\n".join(
        f"[{'고정후보' if r['count'] >= 3 else '흘러가는후보'}, {r['count']}프레임] {r['text']}"
        for r in raw
    )

    total_frames = max((r["first_frame"] for r in raw), default=1) + 1

    prompt = f"""아래는 광고 영상에서 추출한 텍스트 목록이야.
영상 길이: 약 {total_frames}초
나레이션: {narration[:300]}

추출된 텍스트 (등장 프레임 수):
{raw_text}

아래 기준으로 엄격하게 검수해서 JSON으로만 반환해줘:

[제거 기준]
- 소품·배경 텍스트 (책 제목, 제품 패키지 라벨, 벽 포스터, 간판, 핸드폰 화면 등)
- 나레이션·광고 내용과 전혀 무관한 텍스트
- OCR 오류로 보이는 의미없는 문자열

[고정자막 기준] — 반드시 아래 조건을 모두 만족해야 함
- 영상 전체 길이의 30% 이상 화면에 유지되는 텍스트
- 브랜드명, 상품명, 보장/환불 안내, CTA 버튼, 혜택 배너처럼 화면 한 구석에 고정된 요소
- 나레이션과 무관하게 독립적으로 표시되는 텍스트
→ 위 조건에 맞지 않으면 고정자막이 아니라 흘러가는자막으로 분류

[흘러가는자막 기준]
- 나레이션에 맞춰 매 2~5초마다 바뀌는 자막
- 화자의 말을 받아쓰는 형태의 자막

반환 형식 (JSON만, 다른 텍스트 없이):
{{"fixed": ["텍스트1", "텍스트2"], "flowing": ["텍스트1", "텍스트2"]}}

고정자막이 없는 영상이면 fixed는 빈 배열로 반환해."""

    msg = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        json_match = re.search(r'\{.*\}', msg.content[0].text.strip(), re.DOTALL)
        reviewed = json.loads(json_match.group()) if json_match else json.loads(msg.content[0].text.strip())
    except Exception:
        reviewed = {
            "fixed": [r["text"] for r in raw if r["count"] >= 3],
            "flowing": [r["text"] for r in raw if r["count"] < 3]
        }

    print(f"  검수 완료: 고정자막 {len(reviewed.get('fixed', []))}개 / 흘러가는자막 {len(reviewed.get('flowing', []))}개")
    return reviewed


# ── Step 2-b: Claude Vision 영상소스 추출 ────────────────

def extract_visual_sources(frames: list[dict]) -> list[dict]:
    """
    Claude Vision으로 각 프레임의 영상소스(장면 유형) 묘사.
    2초 간격 샘플링 후 연속된 유사 장면은 하나로 병합해 타임코드 범위로 표시.
    반환: [{timecode_range, description}, ...]
    """
    import anthropic
    import base64
    import io
    from PIL import Image

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 2초 간격 샘플링 (API 비용 절약)
    sampled = frames[::2]
    raw_scenes = []
    BATCH = 5

    for batch in _chunks(sampled, BATCH):
        content_blocks = []

        for frame in batch:
            img = Image.open(frame["path"])
            w, h = img.size
            if w > 720:
                ratio = 720 / w
                img = img.resize((720, int(h * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            content_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg",
                           "data": base64.standard_b64encode(buf.getvalue()).decode()}
            })

        content_blocks.append({"type": "text", "text": (
            f"위 {len(batch)}개 광고 영상 프레임 각각에서 어떤 영상소스가 사용되는지 한 줄씩 묘사해줘.\n"
            "묘사 예시:\n"
            "- 엄마 얼굴 클로즈업 (직접 카메라 응시, UGC 자기 고백 톤)\n"
            "- 텍스트 카드 화면 (흰 배경에 검정 굵은 텍스트)\n"
            "- 제품 클로즈업 (스틱 포, 밝은 배경)\n"
            "- 아이 행동 장면 (책상에 앉아 공부하는 모습)\n"
            "- 인포그래픽 화면 (성분명 + 화살표 그래픽)\n"
            f"형식 (프레임 순서대로 {len(batch)}줄):\n프레임1: ...\n프레임2: ...\n묘사만. 설명·부연 없이."
        )})

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=400,
            messages=[{"role": "user", "content": content_blocks}]
        )

        lines = [l.strip() for l in msg.content[0].text.strip().splitlines() if l.strip()]
        for i, frame in enumerate(batch):
            desc = ""
            for line in lines:
                m = re.match(rf'^프레임{i+1}\s*[:：]\s*(.*)', line)
                if m:
                    desc = m.group(1).strip()
                    break
            if not desc and i < len(lines):
                desc = re.sub(r'^프레임\d+\s*[:：]\s*', '', lines[i])
            if desc:
                raw_scenes.append({
                    "timecode_sec": frame["timecode_sec"],
                    "timecode": frame["timecode"],
                    "description": desc
                })

    # 연속된 유사 장면 병합 (유사도 60% 이상)
    merged = []
    current = None
    for scene in raw_scenes:
        if current is None:
            current = dict(scene)
            current["timecode_end"] = scene["timecode"]
            current["timecode_end_sec"] = scene["timecode_sec"]
        else:
            sim = difflib.SequenceMatcher(None, current["description"], scene["description"]).ratio()
            if sim > 0.60:
                current["timecode_end"] = scene["timecode"]
                current["timecode_end_sec"] = scene["timecode_sec"]
            else:
                merged.append(current)
                current = dict(scene)
                current["timecode_end"] = scene["timecode"]
                current["timecode_end_sec"] = scene["timecode_sec"]
    if current:
        merged.append(current)

    for m in merged:
        start = m["timecode"]
        end = m.get("timecode_end", m["timecode"])
        m["timecode_range"] = start if start == end else f"{start}-{end}"

    print(f"  영상소스 추출 완료: {len(merged)}개 장면")
    return merged


# ── Step 3: Whisper 나레이션 ──────────────────────────────

def transcribe(audio_path: str) -> list[dict]:
    from faster_whisper import WhisperModel
    print("  Whisper 나레이션 인식 중...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="ko", beam_size=5)
    return [
        {
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "timecode": f"{int(s.start)//60:02d}:{int(s.start)%60:02d}-{int(s.end)//60:02d}:{int(s.end)%60:02d}",
            "text": s.text.strip()
        }
        for s in segments
    ]


# ── Step 3: OCR로 나레이션 오타 교정 ─────────────────────

def correct_narration_with_subtitles(narration_segments: list[dict], reviewed: dict) -> list[dict]:
    """
    검수된 자막(flowing)을 기준으로 Whisper 나레이션 오타 교정.
    유사도 75% 이상인 경우만 교정 적용.
    """
    all_subs = reviewed.get("flowing", []) + reviewed.get("fixed", [])
    corrected = []
    for seg in narration_segments:
        best_match, best_ratio = None, 0.0
        for sub in all_subs:
            ratio = difflib.SequenceMatcher(None, seg["text"], sub).ratio()
            if ratio > best_ratio:
                best_ratio, best_match = ratio, sub
        new_seg = dict(seg)
        if best_match and best_ratio >= 0.75 and best_match != seg["text"]:
            new_seg["text"] = best_match
        corrected.append(new_seg)
    return corrected


# ── Step 4: 분석 통합 ─────────────────────────────────────

def analyze(video_path: str) -> dict:
    duration = get_duration(video_path)
    print(f"  영상 길이: {duration:.1f}초")

    with tempfile.TemporaryDirectory() as tmp:
        print("  오디오 추출 중...")
        audio = extract_audio(video_path, tmp)
        print("  프레임 추출 중... (1초 간격)")
        frames = extract_frames(video_path, tmp)
        raw_subtitles = extract_subtitles_vision(frames)
        print("  영상소스 추출 중... (Claude Vision)")
        visual_sources = extract_visual_sources(frames)
        narration = transcribe(audio)

    full_narration = " ".join(s["text"] for s in narration)
    print("  자막 검수 중... (Claude)")
    subtitles = review_subtitles(raw_subtitles, full_narration)
    print("  나레이션 교정 중... (자막 기준)")
    narration_corrected = correct_narration_with_subtitles(narration, subtitles)
    full_narration = " ".join(s["text"] for s in narration_corrected)

    return {
        "duration_sec": duration,
        "full_narration": full_narration,
        "narration_segments": narration_corrected,
        "subtitles": subtitles,
        "visual_sources": visual_sources,
    }


# ── 노션 블록 헬퍼 ────────────────────────────────────────

def _h2(text: str) -> dict:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": text}}]}}

def _h3(text: str) -> dict:
    return {"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"text": {"content": text}}]}}

def _para(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": text[:2000]}}]}}

def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"text": {"content": text[:2000]}}]}}

def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}

def _split_sentences(text: str) -> list[str]:
    """문장 단위로 분리 (마침표/느낌표/물음표 기준)"""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


# ── 노션 페이지에 결과 추가 ───────────────────────────────

def append_results_to_page(page_id: str, result: dict) -> None:
    narration = result["narration_segments"]

    blocks = [
        _divider(),

        # ── 영상 분석 결과 ──
        _h2("영상 분석 결과"),
        _para(f"영상 길이: {result['duration_sec']:.1f}초  |  고정자막: {len(result['subtitles'].get('fixed', []))}개  |  흘러가는자막: {len(result['subtitles'].get('flowing', []))}개  |  나레이션: {len(narration)}개"),

        # ── 나레이션 타임라인 ──
        _h2("나레이션 타임라인"),
    ]

    for seg in narration:
        blocks.append(_bullet(f"[{seg['timecode']}]  {seg['text']}"))

    # ── 고정자막 ──
    fixed = result["subtitles"].get("fixed", [])
    if fixed:
        blocks.append(_h2("고정자막"))
        for text in fixed:
            blocks.append(_bullet(text))

    # ── 흘러가는자막 ──
    flowing = result["subtitles"].get("flowing", [])
    if flowing:
        blocks.append(_h2("흘러가는자막"))
        for text in flowing:
            blocks.append(_bullet(text))

    # ── 영상소스 ──
    visual_sources = result.get("visual_sources", [])
    if visual_sources:
        blocks.append(_h2("영상소스"))
        for scene in visual_sources:
            blocks.append(_bullet(f"[{scene['timecode_range']}]  {scene['description']}"))

    # 노션은 한 번에 최대 100개 블록
    for i in range(0, len(blocks), 100):
        notion_patch(f"/blocks/{page_id}/children", {"children": blocks[i:i+100]})

    print("  노션 페이지 업데이트 완료!")


# ── 분석완료 체크 ─────────────────────────────────────────

def mark_done(page_id: str) -> None:
    data = json.dumps({"properties": {"분석완료": {"checkbox": True}}}).encode()
    req = urllib.request.Request(
        f"{NOTION_API}/pages/{page_id}",
        data=data, headers=notion_headers(), method="PATCH"
    )
    with urllib.request.urlopen(req):
        pass


# ── 기존 페이지에 영상소스만 추가 ────────────────────────

def append_visual_sources_to_page(page_id: str, visual_sources: list[dict]) -> None:
    """이미 분석된 페이지에 '영상소스' 섹션만 추가."""
    blocks = [
        _divider(),
        _h2("영상소스"),
    ]
    for scene in visual_sources:
        blocks.append(_bullet(f"[{scene['timecode_range']}]  {scene['description']}"))
    for i in range(0, len(blocks), 100):
        notion_patch(f"/blocks/{page_id}/children", {"children": blocks[i:i+100]})
    print("  영상소스 섹션 추가 완료!")


def run_page_add_sources(page_id: str) -> None:
    """분석완료된 페이지에서 영상을 다시 읽어 영상소스만 추출 후 추가."""
    print(f"\n[영상소스 추가] {page_id}")
    print("-" * 50)

    video_info = find_video_in_page(page_id)
    if not video_info:
        print("  영상 없음 — 스킵")
        return

    video_url, _ = video_info
    print("  영상 발견!")

    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "video.mp4")
        download_video(video_url, video_path)
        print("  프레임 추출 중... (1초 간격)")
        frames = extract_frames(video_path, tmp)
        print("  영상소스 추출 중... (Claude Vision)")
        visual_sources = extract_visual_sources(frames)

    append_visual_sources_to_page(page_id, visual_sources)


def fetch_analyzed_pages(db_id: str) -> list[dict]:
    """분석완료=true인 페이지 목록 반환"""
    body = json.dumps({
        "filter": {"property": "분석완료", "checkbox": {"equals": True}}
    }).encode()
    req = urllib.request.Request(
        f"{NOTION_API}/databases/{db_id}/query",
        data=body, headers=notion_headers(), method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    pages = data.get("results", [])
    print(f"  분석완료 페이지: {len(pages)}개")
    return pages


# ── DB에서 미완료 페이지 조회 ─────────────────────────────

def fetch_pending_pages(db_id: str) -> list[dict]:
    """분석완료 체크가 안 된 페이지 목록 반환"""
    body = json.dumps({
        "filter": {"property": "분석완료", "checkbox": {"equals": False}}
    }).encode()
    req = urllib.request.Request(
        f"{NOTION_API}/databases/{db_id}/query",
        data=body, headers=notion_headers(), method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    pages = data.get("results", [])
    print(f"  미완료 페이지: {len(pages)}개")
    return pages


# ── 단일 페이지 처리 ──────────────────────────────────────

def run_page(page_id: str) -> None:
    print(f"\n[페이지 분석] {page_id}")
    print("-" * 50)

    video_info = find_video_in_page(page_id)
    if not video_info:
        print("  영상 없음 — 스킵")
        return

    video_url, _ = video_info
    print("  영상 발견!")

    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "video.mp4")
        download_video(video_url, video_path)
        result = analyze(video_path)

    append_results_to_page(page_id, result)
    mark_done(page_id)
    print(f"  분석완료 체크!")
    print(f"  고정자막: {len(result['subtitles'].get('fixed', []))}개 / 흘러가는자막: {len(result['subtitles'].get('flowing', []))}개")


# ── Main ──────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--page_url", help="단일 노션 페이지 URL")
    parser.add_argument("--db_url", help="노션 DB URL (분석완료 미체크 전체 처리)")
    parser.add_argument("--add_sources_db_url", help="노션 DB URL (분석완료 페이지에 영상소스만 추가)")
    args = parser.parse_args()

    if args.add_sources_db_url:
        db_id = extract_page_id(args.add_sources_db_url)
        print(f"\n영상소스 추가 시작  |  DB ID: {db_id}")
        print("=" * 50)
        pages = fetch_analyzed_pages(db_id)
        if not pages:
            print("분석완료된 페이지가 없습니다.")
            sys.exit(0)
        for i, page in enumerate(pages, 1):
            print(f"\n({i}/{len(pages)})", end="")
            run_page_add_sources(page["id"])
        print(f"\n\n[전체 완료] {len(pages)}개 페이지 영상소스 추가됨")

    elif args.db_url:
        db_id = extract_page_id(args.db_url)
        print(f"\n노션 DB 일괄 처리 시작  |  DB ID: {db_id}")
        print("=" * 50)
        pages = fetch_pending_pages(db_id)
        if not pages:
            print("처리할 페이지가 없습니다.")
            sys.exit(0)
        for i, page in enumerate(pages, 1):
            print(f"\n({i}/{len(pages)})", end="")
            run_page(page["id"])
        print(f"\n\n[전체 완료] {len(pages)}개 페이지 처리됨")

    elif args.page_url:
        page_id = extract_page_id(args.page_url)
        run_page(page_id)

    else:
        print("오류: --page_url, --db_url, --add_sources_db_url 중 하나를 입력해주세요.")
        sys.exit(1)
