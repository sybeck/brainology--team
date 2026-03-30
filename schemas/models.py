"""
에이전트 간 데이터 스키마 정의.
에이전트들은 이 스키마에 맞는 JSON 파일을 outputs/campaigns/{제품명}/{campaign_id}/ 에 저장.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────────────────────
# Phase 0: 제품 정보 (products/*.md에서 파싱)
# ─────────────────────────────────────────

class ProductBrief(BaseModel):
    product_name: str
    price: str
    form: str                          # 구미, 정, 분말 등
    target_age: str                    # "4~12세"
    key_ingredients: list[str]
    approved_functional_claims: list[str]   # KHFA 승인 기능성 문구만
    usp: list[str]                     # 경쟁 제품 대비 차별점
    target_audience: str               # 광고 수신자 (부모) 설명
    pain_points: list[str]             # 타겟의 주요 페인포인트
    prohibited_expressions: list[str]  # 이 제품 관련 금지 표현
    packaging_info: dict               # 색상, 캐릭터 등 비주얼 정보
    promotions: str | None = None      # 현재 프로모션


# ─────────────────────────────────────────
# Phase 1: 리서치 결과
# ─────────────────────────────────────────

class AdFormat(BaseModel):
    format: Literal["single_image", "carousel", "reel", "story"]
    notes: str


class HookPattern(BaseModel):
    type: Literal["공감형", "질문형", "혜택형", "충격형"]
    example: str
    source: str | None = None


class VisualStyle(BaseModel):
    style: str
    color_palette: list[str] = Field(default_factory=list)
    notes: str


class ReferenceBundle(BaseModel):
    campaign_id: str
    collected_at: datetime
    ad_formats: list[AdFormat]
    hook_patterns: list[HookPattern]
    visual_styles: list[VisualStyle]
    cta_examples: list[str]
    compliance_examples: list[dict]
    key_insights: str


class PainPoint(BaseModel):
    pain: str
    verbatim: str                      # 실제 소비자 언어
    frequency: Literal["high", "medium", "low"]


class PurchaseMotivator(BaseModel):
    motivator: str
    channel: str                       # 소아과, 지인, SNS, 광고 등


class EmotionalHook(BaseModel):
    hook: str
    emotion: Literal["불안", "희망", "자부심", "죄책감", "공감"]


class ConsumerInsights(BaseModel):
    campaign_id: str
    collected_at: datetime
    pain_points: list[PainPoint]
    purchase_motivators: list[PurchaseMotivator]
    purchase_barriers: list[dict]
    emotional_hooks: list[EmotionalHook]
    verbatim_quotes: list[str]
    audience_segments: list[dict]
    key_insights: str


# ─────────────────────────────────────────
# Phase 2: 콘텐츠 기획
# ─────────────────────────────────────────

class ContentBrief(BaseModel):
    brief_id: str                      # "img_1" ~ "img_5", "vid_1" ~ "vid_10"
    format: Literal["image", "video"]
    duration: int | None = None        # 영상만: 15 또는 30초
    concept_title: str
    angle: Literal["페인포인트", "성분강조", "라이프스타일", "신뢰", "편의", "감성"]
    core_message: str
    visual_direction: str
    narrative_arc: str | None = None   # 영상만
    target_emotion: Literal["불안해소", "희망", "신뢰", "공감", "자부심"]
    key_copy_direction: str
    compliance_notes: str


class ContentBriefList(BaseModel):
    campaign_id: str
    product_name: str
    created_at: datetime
    image_briefs: list[ContentBrief]   # 5개
    video_briefs: list[ContentBrief]   # 10개


# ─────────────────────────────────────────
# Phase 3: 카피 + 이미지/스크립트
# ─────────────────────────────────────────

class CopyPackage(BaseModel):
    campaign_id: str
    brief_id: str
    format: Literal["image", "video"]
    headline_primary: str              # 최대 20자
    headline_variants: list[str]       # A/B 변형 2개
    body_copy: str                     # 최대 3문장
    cta_text: str
    disclaimer: str = "이 제품은 질병의 예방 및 치료를 위한 의약품이 아닙니다."
    compliance_flags: list[str] = Field(default_factory=list)
    copywriter_notes: str | None = None


class ImageAsset(BaseModel):
    campaign_id: str
    brief_id: str
    product_name: str
    dalle_prompt: str
    image_path_square: str             # 1080x1080
    image_path_story: str              # 1080x1920
    dimensions: dict = Field(default_factory=lambda: {"square": "1080x1080", "story": "1080x1920"})
    generation_attempts: int = 1
    generation_status: Literal["OK", "NEEDS_REVIEW"] = "OK"
    self_review_notes: str | None = None
    ai_disclosure: str = "AI로 제작된 콘텐츠"


class SceneBlock(BaseModel):
    scene_number: int
    start_sec: int
    end_sec: int
    visual_description: str
    vo_text: str
    on_screen_text: str
    bgm_direction: str


class VideoScript(BaseModel):
    campaign_id: str
    brief_id: str
    product_name: str
    duration_seconds: int              # 15 또는 30
    format: str = "9:16 Reel"
    scenes: list[SceneBlock]
    vo_full_transcript: str
    total_character_count: int
    disclaimer_placement: str = "마지막 씬 하단에 작은 텍스트로"
    disclaimer_text: str = "이 제품은 질병의 예방 및 치료를 위한 의약품이 아닙니다."
    compliance_self_check: dict = Field(default_factory=lambda: {
        "approved_claims_only": True,
        "no_prohibited_terms": True,
        "disclaimer_included": True
    })
    production_notes: str | None = None


# ─────────────────────────────────────────
# Phase 4: 컴플라이언스 검수
# ─────────────────────────────────────────

class ComplianceIssue(BaseModel):
    rule: Literal["건강기능식품법", "Meta정책", "브랜드가이드"]
    violation: str
    original_text: str
    suggested_fix: str


class ComplianceItem(BaseModel):
    item_id: str
    item_type: Literal["copy", "image", "script"]
    status: Literal["PASS", "FAIL"]
    issues: list[ComplianceIssue] = Field(default_factory=list)
    required_additions: list[str] = Field(default_factory=list)
    notes: str | None = None


class ComplianceReport(BaseModel):
    campaign_id: str
    reviewed_at: datetime
    overall_status: Literal["PASS", "FAIL", "CONDITIONAL_PASS", "PENDING_REVIEW"]
    items: list[ComplianceItem]
    required_global_modifications: list[str] = Field(default_factory=list)
    ai_disclosure_required: bool = True
    disclaimer_required: str = "이 제품은 질병의 예방 및 치료를 위한 의약품이 아닙니다."
    reviewer_summary: str


# ─────────────────────────────────────────
# Phase 5: 최종 캠페인 패키지
# ─────────────────────────────────────────

class CampaignPackage(BaseModel):
    campaign_id: str
    product_name: str
    created_at: datetime
    overall_compliance_status: Literal["PASS", "FAIL", "CONDITIONAL_PASS", "PENDING_REVIEW"]
    image_count: int = 5
    video_script_count: int = 10
    image_assets: list[str]            # image_{brief_id}.json 경로 목록
    video_scripts: list[str]           # video_{brief_id}.json 경로 목록
    slack_delivered: bool = False
    notion_page_url: str | None = None
    ai_disclosure: str = "AI로 제작된 콘텐츠"
