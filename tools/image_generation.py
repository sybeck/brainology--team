"""
이미지 생성 도구.
OpenAI GPT Image (gpt-image-1)를 주 생성 엔진으로 사용.
건강 콘텐츠 거부 시 Stability AI SDXL로 폴백.

사용법:
  python tools/image_generation.py \
    --prompt "A happy child eating gummy vitamins..." \
    --output "outputs/images/멀티비타민키즈/campaign_id/image_1.png" \
    --size "1080x1080"
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def generate_with_openai(prompt: str, output_path: str, size: str) -> bool:
    """OpenAI GPT Image API로 이미지 생성."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # GPT Image (gpt-image-1) 사용 - 한국어 텍스트 렌더링 우수
        width, height = size.split("x")
        size_param = f"{width}x{height}"

        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=1,
            size=size_param,
            output_format="png",
        )

        # 이미지 저장
        image_data = response.data[0]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if hasattr(image_data, "b64_json") and image_data.b64_json:
            image_bytes = base64.b64decode(image_data.b64_json)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
        elif hasattr(image_data, "url") and image_data.url:
            import urllib.request
            urllib.request.urlretrieve(image_data.url, output_path)

        print(f"[OK] 이미지 저장: {output_path}")
        return True

    except Exception as e:
        print(f"[ERROR] OpenAI 생성 실패: {e}", file=sys.stderr)
        return False


def generate_with_stability(prompt: str, output_path: str, size: str) -> bool:
    """Stability AI SDXL로 폴백 생성."""
    try:
        import requests

        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            print("[WARN] STABILITY_API_KEY 없음. 폴백 불가.", file=sys.stderr)
            return False

        width, height = map(int, size.split("x"))

        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7,
                "height": height,
                "width": width,
                "steps": 30,
                "samples": 1,
            },
            timeout=60,
        )

        if response.status_code != 200:
            print(f"[ERROR] Stability API 오류: {response.text}", file=sys.stderr)
            return False

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image_data = response.json()["artifacts"][0]["base64"]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data))

        print(f"[OK] 폴백 이미지 저장: {output_path}")
        return True

    except Exception as e:
        print(f"[ERROR] Stability 생성 실패: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="광고 이미지 생성 도구")
    parser.add_argument("--prompt", required=True, help="이미지 생성 프롬프트 (영어)")
    parser.add_argument("--output", required=True, help="저장 경로 (PNG)")
    parser.add_argument(
        "--size",
        default="1080x1080",
        choices=["1080x1080", "1080x1920", "1200x628"],
        help="이미지 사이즈 (기본: 1080x1080 스퀘어)",
    )

    args = parser.parse_args()

    # 1차: OpenAI GPT Image
    if generate_with_openai(args.prompt, args.output, args.size):
        sys.exit(0)

    # 2차 폴백: Stability AI SDXL
    print("[INFO] OpenAI 실패. Stability AI로 폴백합니다.", file=sys.stderr)
    if generate_with_stability(args.prompt, args.output, args.size):
        sys.exit(0)

    print("[FAIL] 이미지 생성 실패. 수동 확인 필요.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
