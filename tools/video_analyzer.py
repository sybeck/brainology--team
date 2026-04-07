"""
video_analyzer.py
영상 파일 → 영상소스 / 나레이션 / 자막 분리 추출 도구

사용법:
    python tools/video_analyzer.py <영상파일경로> [--output <출력경로>]

예시:
    python tools/video_analyzer.py my_video.mp4
    python tools/video_analyzer.py my_video.mp4 --output result.json
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

FFMPEG = "ffmpeg"


# ── 유틸 ──────────────────────────────────────────────────

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, check=check)


def get_video_duration(video_path: str) -> float:
    result = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ])
    return float(result.stdout.decode().strip())


# ── Step 1: 오디오 추출 ────────────────────────────────────

def extract_audio(video_path: str, out_dir: str) -> str:
    audio_path = os.path.join(out_dir, "audio.mp3")
    run([
        FFMPEG, "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k",
        audio_path
    ])
    print(f"  [1/3] 오디오 추출 완료: {audio_path}")
    return audio_path


# ── Step 2: 키프레임 추출 ─────────────────────────────────

def extract_keyframes(video_path: str, out_dir: str, interval_sec: int = 3) -> list[dict]:
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    run([
        FFMPEG, "-y", "-i", video_path,
        "-vf", f"fps=1/{interval_sec}",
        "-q:v", "2",
        os.path.join(frames_dir, "frame_%04d.jpg")
    ])

    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    result = []
    for i, f in enumerate(frames):
        timecode_sec = i * interval_sec
        result.append({
            "path": str(f),
            "timecode_sec": timecode_sec,
            "timecode": f"{timecode_sec // 60:02d}:{timecode_sec % 60:02d}"
        })

    print(f"  [2/3] 키프레임 추출 완료: {len(result)}장")
    return result


# ── Step 3: Whisper로 나레이션 트랜스크립트 ─────────────────

def transcribe_audio(audio_path: str) -> list[dict]:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            language="ko"
        )

    segments = []
    for seg in response.segments:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "timecode": f"{int(seg.start) // 60:02d}:{int(seg.start) % 60:02d}-{int(seg.end) // 60:02d}:{int(seg.end) % 60:02d}",
            "text": seg.text.strip()
        })

    print(f"  [3/3] 나레이션 트랜스크립트 완료: {len(segments)}개 세그먼트")
    return segments


# ── Step 4: Claude Vision으로 씬 설명 ───────────────────────

def describe_frames(frames: list[dict]) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = []

    # 프레임이 많으면 최대 10장만 분석 (비용 절약)
    sample = frames if len(frames) <= 10 else frames[::max(1, len(frames) // 10)][:10]

    for frame in sample:
        with open(frame["path"], "rb") as f:
            img_data = base64.standard_b64encode(f.read()).decode()

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_data
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "이 영상 프레임을 분석해서 아래 3가지를 간결하게 JSON으로 답해줘:\n"
                            "1. scene: 화면에 보이는 것 (인물, 배경, 소품, 텍스트 자막)\n"
                            "2. subtitle_text: 화면에 보이는 자막 텍스트 (없으면 null)\n"
                            "3. visual_type: 실사/모션그래픽/제품샷/텍스트전용 중 하나\n"
                            "JSON 형식으로만 답해줘. 다른 설명 없이."
                        )
                    }
                ]
            }]
        )

        try:
            parsed = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            parsed = {"scene": message.content[0].text, "subtitle_text": None, "visual_type": "unknown"}

        results.append({
            "timecode": frame["timecode"],
            "timecode_sec": frame["timecode_sec"],
            **parsed
        })

    print(f"  [+] 씬 분석 완료: {len(results)}장")
    return results


# ── Step 5: 전체 결과 병합 ────────────────────────────────

def merge_results(
    narration_segments: list[dict],
    scene_descriptions: list[dict],
    duration_sec: float
) -> dict:
    # 나레이션을 씬에 매핑
    scenes_with_narration = []
    for scene in scene_descriptions:
        t = scene["timecode_sec"]
        # 해당 타임코드 범위의 나레이션 찾기
        matching_narration = [
            seg["text"] for seg in narration_segments
            if seg["start"] <= t + 3 and seg["end"] >= t
        ]
        scenes_with_narration.append({
            "timecode": scene["timecode"],
            "visual_type": scene.get("visual_type"),
            "scene": scene.get("scene"),
            "subtitle_text": scene.get("subtitle_text"),
            "narration": " ".join(matching_narration) if matching_narration else None
        })

    # 전체 VO 조합
    full_vo = " ".join(seg["text"] for seg in narration_segments)

    # 자막 목록 추출
    subtitles = [
        {"timecode": s["timecode"], "text": s["subtitle_text"]}
        for s in scenes_with_narration
        if s.get("subtitle_text")
    ]

    return {
        "duration_sec": duration_sec,
        "full_narration": full_vo,
        "narration_segments": narration_segments,
        "scenes": scenes_with_narration,
        "subtitles": subtitles
    }


# ── Main ──────────────────────────────────────────────────

def analyze_video(video_path: str, output_path: str | None = None) -> dict:
    video_path = os.path.abspath(video_path)
    if not os.path.exists(video_path):
        print(f"오류: 파일을 찾을 수 없습니다 — {video_path}")
        sys.exit(1)

    print(f"\n영상 분석 시작: {Path(video_path).name}")
    print("=" * 50)

    duration = get_video_duration(video_path)
    print(f"  영상 길이: {duration:.1f}초")

    # 키프레임 간격 결정 (30초 이하 영상은 2초 간격, 그 이상은 3초)
    interval = 2 if duration <= 30 else 3

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = extract_audio(video_path, tmp)
        frames = extract_keyframes(video_path, tmp, interval_sec=interval)
        narration = transcribe_audio(audio_path)
        scenes = describe_frames(frames)

    result = merge_results(narration, scenes, duration)

    # 출력
    if output_path is None:
        stem = Path(video_path).stem
        output_path = str(Path(video_path).parent / f"{stem}_analyzed.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n완료! 결과 저장: {output_path}")
    print("=" * 50)
    print(f"  전체 나레이션: {result['full_narration'][:80]}...")
    print(f"  씬 수: {len(result['scenes'])}개")
    print(f"  자막 발견: {len(result['subtitles'])}개")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="영상 → 영상소스/나레이션/자막 분리 추출")
    parser.add_argument("video", help="분석할 영상 파일 경로")
    parser.add_argument("--output", "-o", help="결과 JSON 저장 경로 (기본값: 영상과 같은 폴더)")
    args = parser.parse_args()

    analyze_video(args.video, args.output)
