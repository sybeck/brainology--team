"""
정산서 PDF 생성 도구 — 디자인 A/B/C 지원.

사용법:
  python tools/settlement_pdf.py \
    --report_json "teams/settlement/outputs/{run_id}/sales_{name}.json" \
    --output_pdf  "teams/settlement/outputs/{run_id}/settlement_{name}.pdf" \
    --design A    # A(미니멀) / B(기업 블루) / C(모던 액센트)

의존성: pip install fpdf2
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

COMPANY_NAME    = "(주)아침아니면저녁"
COMPANY_REG_NO  = "275-86-01005"

FONT_PATH_CANDIDATES = [
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/gulim.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleGothic.ttf",
]
FONT_BOLD_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


def find_font(candidates) -> str | None:
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def krw(amount: float) -> str:
    return f"{int(amount):,}원"


# ─────────────────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────────────────

def setup_fonts(pdf: FPDF) -> tuple[str, str]:
    """폰트 등록 후 (일반체명, 볼드체명) 반환."""
    regular = find_font(FONT_PATH_CANDIDATES)
    bold    = find_font(FONT_BOLD_CANDIDATES)
    if regular is None:
        raise RuntimeError("한국어 TTF 폰트를 찾지 못했습니다. malgun.ttf 또는 NanumGothic.ttf를 설치해 주세요.")

    pdf.add_font("KR",  fname=regular, uni=True)
    if bold and bold != regular:
        pdf.add_font("KRB", fname=bold,    uni=True)
        return "KR", "KRB"
    else:
        pdf.add_font("KRB", fname=regular, uni=True)
        return "KR", "KRB"


def segment_label(seg: dict) -> str:
    label = seg.get("label", "일반")
    s, e = seg["start_date"], seg["end_date"]
    rate = seg["fee_rate"]
    return f"[{label}] {s} ~ {e}  (수수료율 {rate:.0f}%)"


def final_summary_text(report: dict) -> tuple[str, str]:
    """(summary_lines_str, callout_str) 반환."""
    entity_type = report.get("entity_type", "")
    fee = int(report.get("total_fee_amount", 0))
    final = int(report.get("final_settlement_amount", fee))
    withheld = int(report.get("withholding_tax_amount", 0))

    if "3.3" in entity_type or "원천세" in entity_type:
        note = f"원천세(3.3%) {krw(withheld)} 공제 후 최종 정산금액: {krw(final)}"
    else:
        note = f"최종 정산금액: {krw(final)}  (VAT 포함금액)"
    return note


# ─────────────────────────────────────────────────────────
# Design A — 미니멀 (흑백, 얇은 선)
# ─────────────────────────────────────────────────────────

def generate_pdf_A(report: dict, output_path: str) -> str:
    pdf = FPDF(format="A4")
    pdf.add_page()
    KR, KRB = setup_fonts(pdf)

    W = pdf.w - 2 * pdf.l_margin   # 유효 너비

    # ── 제목
    pdf.set_font(KRB, size=22)
    pdf.cell(W, 14, "정  산  서", align="C", ln=True)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
    pdf.ln(5)

    # ── 발행사 / 수취인 2단 구성
    pdf.set_font(KR, size=9)
    col = W / 2 - 3
    left_x = pdf.l_margin
    right_x = pdf.l_margin + W / 2 + 3

    def kv(label, value, x, y, w):
        pdf.set_xy(x, y)
        pdf.set_font(KRB, size=8)
        pdf.cell(28, 6, label, border="B")
        pdf.set_font(KR, size=8)
        pdf.cell(w - 28, 6, value, border="B", ln=False)

    y0 = pdf.get_y()
    kv("발행사",    COMPANY_NAME,            left_x,  y0,      col)
    kv("수취인",    report.get("name", ""),  right_x, y0,      col)
    kv("사업자번호", COMPANY_REG_NO,          left_x,  y0+8,   col)
    kv("제품명",    report.get("product_name",""), right_x, y0+8, col)
    kv("담당자",    report.get("contact_person",""), left_x, y0+16, col)
    kv("상품코드",  report.get("product_code",""),   right_x, y0+16, col)
    kv("연락처",    report.get("contact_phone",""),   left_x, y0+24, col)
    kv("과세유형",  report.get("entity_type",""),     right_x, y0+24, col)

    pdf.set_xy(pdf.l_margin, y0 + 34)
    pdf.set_font(KR, size=8)
    period = f"{report.get('start_date','')} ~ {report.get('end_date','')}  ({report.get('elapsed_days','')}일)"
    pdf.cell(W, 6, f"정산 기간: {period}", border="B", ln=True)
    pdf.ln(6)

    # ── 구간별 매출
    for seg in report.get("segments", []):
        pdf.set_font(KRB, size=9)
        pdf.cell(W, 7, segment_label(seg), ln=True)
        pdf.set_line_width(0.2)

        # 테이블 헤더
        c_widths = [W * 0.55, W * 0.20, W * 0.25]
        pdf.set_font(KRB, size=8)
        pdf.set_fill_color(230, 230, 230)
        for txt, cw in zip(["옵션명", "결제건수", "결제금액"], c_widths):
            pdf.cell(cw, 6, txt, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font(KR, size=8)
        for opt in seg.get("options", []):
            pdf.cell(c_widths[0], 6, opt["option_name"], border=1)
            pdf.cell(c_widths[1], 6, f"{opt['payment_count']:,}건", border=1, align="R")
            pdf.cell(c_widths[2], 6, krw(opt["payment_amount"]), border=1, align="R")
            pdf.ln()

        # 소계
        pdf.set_font(KRB, size=8)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(c_widths[0], 6, "소계", border=1, fill=True)
        pdf.cell(c_widths[1], 6, f"{seg['total_payment_count']:,}건", border=1, align="R", fill=True)
        pdf.cell(c_widths[2], 6, krw(seg["total_payment_amount"]), border=1, align="R", fill=True)
        pdf.ln()
        pdf.set_font(KR, size=8)
        pdf.cell(W, 5, f"  수수료({seg['fee_rate']:.0f}%): {krw(seg['fee_amount'])}", ln=True)
        pdf.ln(3)

    # ── 최종 요약
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
    pdf.ln(3)
    pdf.set_font(KRB, size=10)
    total_amt  = int(report.get("total_payment_amount", 0))
    total_fee  = int(report.get("total_fee_amount", 0))
    pdf.cell(W, 7, f"총 결제금액: {krw(total_amt)}   합산 수수료: {krw(total_fee)}", ln=True)
    pdf.set_font(KRB, size=12)
    pdf.cell(W, 9, final_summary_text(report), ln=True)

    pdf.ln(8)
    pdf.set_font(KR, size=8)
    pdf.cell(W, 5, f"발행일: {datetime.now().strftime('%Y년 %m월 %d일')}", align="R", ln=True)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path


# ─────────────────────────────────────────────────────────
# Design B — 기업 블루 (네이비 헤더 + 파란 강조)
# ─────────────────────────────────────────────────────────

def generate_pdf_B(report: dict, output_path: str) -> str:
    pdf = FPDF(format="A4")
    pdf.add_page()
    KR, KRB = setup_fonts(pdf)

    W   = pdf.w - 2 * pdf.l_margin
    NAVY  = (26, 32, 64)
    BLUE  = (49, 130, 206)
    LBLUE = (235, 248, 255)
    GRAY  = (247, 248, 250)

    # ── 헤더 배너
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, pdf.w, 28, "F")
    pdf.set_font(KRB, size=18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(6)
    pdf.cell(pdf.w, 10, "정  산  서", align="C", ln=True)
    pdf.set_font(KR, size=9)
    pdf.set_y(17)
    pdf.cell(pdf.w, 7, COMPANY_NAME + "  |  " + COMPANY_REG_NO, align="C", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ── 정보 박스
    def section_title(title: str):
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(KRB, size=9)
        pdf.cell(W, 7, f"  {title}", fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)

    def info_row(label, value, fill=False):
        pdf.set_fill_color(*GRAY if fill else (255,255,255))
        pdf.set_font(KRB, size=8)
        pdf.cell(40, 6.5, label, border="B", fill=fill)
        pdf.set_font(KR, size=8)
        pdf.cell(W - 40, 6.5, str(value), border="B", fill=fill, ln=True)

    section_title("정산 정보")
    info_row("수취인",    report.get("name", ""),         fill=False)
    info_row("제품명",    report.get("product_name", ""),  fill=True)
    info_row("상품코드",  report.get("product_code", ""),  fill=False)
    info_row("정산 기간", f"{report.get('start_date','')} ~ {report.get('end_date','')}  ({report.get('elapsed_days','')}일)", fill=True)
    info_row("담당자",    f"{report.get('contact_person','')}  |  {report.get('contact_phone','')}", fill=False)
    info_row("과세유형",  report.get("entity_type", ""),   fill=True)
    pdf.ln(5)

    # ── 구간별 매출
    section_title("매출 집계")
    pdf.ln(2)

    c_widths = [W * 0.52, W * 0.18, W * 0.30]

    for seg in report.get("segments", []):
        pdf.set_fill_color(*LBLUE)
        pdf.set_font(KRB, size=8)
        pdf.cell(W, 6.5, f"  {segment_label(seg)}", fill=True, ln=True)

        pdf.set_fill_color(200, 220, 255)
        for txt, cw in zip(["옵션명", "결제건수", "결제금액"], c_widths):
            pdf.set_font(KRB, size=8)
            pdf.cell(cw, 6, txt, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_fill_color(255, 255, 255)
        for i, opt in enumerate(seg.get("options", [])):
            fill = (i % 2 == 1)
            if fill:
                pdf.set_fill_color(*GRAY)
            pdf.set_font(KR, size=8)
            pdf.cell(c_widths[0], 5.5, opt["option_name"], border="LR", fill=fill)
            pdf.cell(c_widths[1], 5.5, f"{opt['payment_count']:,}건", border="LR", fill=fill, align="R")
            pdf.cell(c_widths[2], 5.5, krw(opt["payment_amount"]), border="LR", fill=fill, align="R")
            pdf.ln()

        pdf.set_fill_color(*LBLUE)
        pdf.set_font(KRB, size=8)
        pdf.cell(c_widths[0], 6, "소계", border=1, fill=True)
        pdf.cell(c_widths[1], 6, f"{seg['total_payment_count']:,}건", border=1, fill=True, align="R")
        pdf.cell(c_widths[2], 6, krw(seg["total_payment_amount"]), border=1, fill=True, align="R")
        pdf.ln()
        pdf.set_font(KR, size=8)
        pdf.set_text_color(*BLUE)
        pdf.cell(W, 5.5, f"  → 수수료 {seg['fee_rate']:.0f}%: {krw(seg['fee_amount'])}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # ── 최종 요약 박스
    pdf.ln(2)
    section_title("정산 요약")
    info_row("총 결제금액", krw(report.get("total_payment_amount", 0)), fill=False)
    info_row("합산 수수료", krw(report.get("total_fee_amount", 0)),     fill=True)

    entity_type = report.get("entity_type", "")
    if "3.3" in entity_type or "원천세" in entity_type:
        info_row("원천세 (3.3%)", krw(report.get("withholding_tax_amount", 0)), fill=False)
    info_row("최종 정산금액", krw(report.get("final_settlement_amount", 0))
             + ("  (VAT 포함)" if "부가세" in entity_type else ""), fill=True)

    pdf.ln(8)
    pdf.set_font(KR, size=8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(W, 5, f"발행일: {datetime.now().strftime('%Y년 %m월 %d일')}", align="R", ln=True)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path


# ─────────────────────────────────────────────────────────
# Design C — 브레인올로지 브랜드 그린 (좌측 컬러바 + 강조 카드)
# ─────────────────────────────────────────────────────────

BRAND_CONFIG = {
    "브레인올로지": {
        "logo":  "brand/images/logo/brainology_logo.png",
        "title": "브레인올로지 정산서",
        "accent": (57, 121, 0),    # #397900 딥 그린
        "light":  (240, 248, 232),
    },
    "부담제로": {
        "logo":  "brand/images/logo/budamzero_logo.png",
        "title": "부담제로 정산서",
        "accent": (20, 20, 20),    # 블랙
        "light":  (245, 245, 245),
    },
}

def _brand_cfg(report: dict) -> dict:
    brand = report.get("brand", "")
    return BRAND_CONFIG.get(brand, BRAND_CONFIG["브레인올로지"])


def generate_pdf_C(report: dict, output_path: str) -> str:
    pdf = FPDF(format="A4")
    pdf.add_page()
    KR, KRB = setup_fonts(pdf)

    # 브랜드별 색상·로고·제목
    cfg    = _brand_cfg(report)
    ACCENT = cfg["accent"]
    LIGHT  = cfg["light"]
    MGRAY  = (80, 80, 80)
    LGRAY  = (240, 240, 240)
    DGRAY  = (51, 51, 51)      # 텍스트 기본색

    L_MARGIN = 14              # 좌측 마진 (액센트 바 6 + 여백 8)
    R_MARGIN = 14
    W = pdf.w - L_MARGIN - R_MARGIN

    # ── 좌측 액센트 바
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 0, 6, pdf.h, "F")

    # ── 우측 상단 로고
    logo_path = Path(cfg["logo"])
    if logo_path.exists():
        logo_w = 44
        logo_h = 11
        pdf.image(str(logo_path), x=pdf.w - R_MARGIN - logo_w, y=10, w=logo_w, h=logo_h)

    # ── 제목
    pdf.set_xy(L_MARGIN, 10)
    pdf.set_font(KRB, size=20)
    pdf.set_text_color(*ACCENT)
    pdf.cell(W - 50, 11, cfg["title"], ln=False)
    pdf.ln(11)

    # ── 발행사 정보
    pdf.set_x(L_MARGIN)
    pdf.set_font(KR, size=8)
    pdf.set_text_color(*MGRAY)
    pdf.cell(W, 5.5, f"{COMPANY_NAME}  ·  사업자번호 {COMPANY_REG_NO}", ln=True)
    pdf.set_text_color(*DGRAY)

    # ── 구분선
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(L_MARGIN, pdf.get_y() + 1, L_MARGIN + W, pdf.get_y() + 1)
    pdf.ln(5)

    # ── 정보 카드 (들여쓰기 없이 L_MARGIN 기준 정렬)
    LABEL_W = 28
    card_y = pdf.get_y()
    card_h = 6.5 * 5 + 4  # 5행 + 상하 패딩
    pdf.set_fill_color(*LIGHT)
    pdf.rect(L_MARGIN, card_y, W, card_h, "F")

    def card_kv(label, value):
        pdf.set_x(L_MARGIN + 3)
        pdf.set_font(KRB, size=8)
        pdf.set_text_color(*ACCENT)
        pdf.cell(LABEL_W, 6.5, label)
        pdf.set_font(KR, size=8)
        pdf.set_text_color(*DGRAY)
        pdf.cell(W - LABEL_W - 3, 6.5, str(value), ln=True)

    pdf.set_y(card_y + 2)
    card_kv("수취인",   report.get("name", ""))
    card_kv("제품명",   f"{report.get('product_name', '')}  ({report.get('product_code', '')})")
    card_kv("담당자",   f"{report.get('contact_person', '')}  |  {report.get('contact_phone', '')}")
    card_kv("과세유형", report.get("entity_type", ""))
    card_kv("정산 기간", (f"{report.get('start_date','')} ~ {report.get('end_date','')} "
                         f"({report.get('elapsed_days','')}일)"))
    pdf.ln(5)

    # ── 구간별 매출 테이블
    # 컬럼 너비: 옵션명 | 결제건수 | 결제금액 | 수수료
    c_widths = [W * 0.44, W * 0.15, W * 0.22, W * 0.19]

    for seg in report.get("segments", []):
        # 구간 헤더 (특별 기간 = 브랜드 그린, 일반 = 다크 그레이)
        hdr_color = ACCENT if seg["label"] == "특별" else (60, 70, 60)
        pdf.set_fill_color(*hdr_color)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(KRB, size=8)
        pdf.set_x(L_MARGIN)
        pdf.cell(W, 6.5, f"  {segment_label(seg)}", fill=True, ln=True)
        pdf.set_text_color(*DGRAY)

        # 컬럼 헤더
        pdf.set_fill_color(*LGRAY)
        pdf.set_x(L_MARGIN)
        for txt, cw in zip(["옵션명", "결제건수", "결제금액", f"수수료({seg['fee_rate']:.0f}%)"], c_widths):
            pdf.set_font(KRB, size=8)
            pdf.cell(cw, 6, txt, border=1, fill=True, align="C")
        pdf.ln()

        # 옵션 데이터 행
        opt_fee_per_row = []  # 옵션별 수수료
        for i, opt in enumerate(seg.get("options", [])):
            row_fee = round(opt["payment_amount"] * seg["fee_rate"] / 100)
            opt_fee_per_row.append(row_fee)
            fill = (i % 2 == 1)
            pdf.set_fill_color(*(LGRAY if fill else (255, 255, 255)))
            pdf.set_x(L_MARGIN)
            pdf.set_font(KR, size=8)
            pdf.cell(c_widths[0], 5.5, opt["option_name"],              border="LR", fill=fill)
            pdf.cell(c_widths[1], 5.5, f"{opt['payment_count']:,}건",   border="LR", fill=fill, align="R")
            pdf.cell(c_widths[2], 5.5, krw(opt["payment_amount"]),      border="LR", fill=fill, align="R")
            pdf.cell(c_widths[3], 5.5, krw(row_fee),                    border="LR", fill=fill, align="R")
            pdf.ln()

        # 소계 행
        pdf.set_x(L_MARGIN)
        pdf.set_fill_color(*LIGHT)
        pdf.set_font(KRB, size=8)
        pdf.set_text_color(*ACCENT)
        pdf.cell(c_widths[0], 6, "소계", border=1, fill=True)
        pdf.set_text_color(*DGRAY)
        pdf.cell(c_widths[1], 6, f"{seg['total_payment_count']:,}건",  border=1, fill=True, align="R")
        pdf.cell(c_widths[2], 6, krw(seg["total_payment_amount"]),     border=1, fill=True, align="R")
        pdf.cell(c_widths[3], 6, krw(seg["fee_amount"]),               border=1, fill=True, align="R")
        pdf.ln()
        pdf.ln(3)

    # ── 최종 정산 강조 카드
    entity_type = report.get("entity_type", "")
    card_lines = 2 + (1 if ("3.3" in entity_type or "원천세" in entity_type) else 0)
    final_card_h = card_lines * 6.5 + 10

    final_y = pdf.get_y()
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.6)
    pdf.set_fill_color(*LIGHT)
    pdf.rect(L_MARGIN, final_y, W, final_card_h, "FD")

    pdf.set_xy(L_MARGIN + 4, final_y + 4)
    pdf.set_font(KR, size=9)
    pdf.set_text_color(*DGRAY)
    pdf.cell(W - 8, 6.5,
             f"총 결제금액: {krw(report.get('total_payment_amount',0))}"
             f"   합산 수수료: {krw(report.get('total_fee_amount',0))}", ln=True)
    pdf.set_x(L_MARGIN + 4)

    if "3.3" in entity_type or "원천세" in entity_type:
        pdf.cell(W - 8, 6.5,
                 f"원천세 (3.3%): {krw(report.get('withholding_tax_amount', 0))} 공제", ln=True)
        pdf.set_x(L_MARGIN + 4)

    pdf.set_font(KRB, size=13)
    pdf.set_text_color(*ACCENT)
    suffix = "  (VAT 포함)" if "부가세" in entity_type else ""
    pdf.cell(W - 8, 9,
             f"최종 정산금액: {krw(report.get('final_settlement_amount', 0))}{suffix}", ln=True)
    pdf.set_text_color(*DGRAY)

    # ── 발행일
    pdf.set_y(final_y + final_card_h + 4)
    pdf.set_x(L_MARGIN)
    pdf.set_font(KR, size=8)
    pdf.set_text_color(*MGRAY)
    pdf.cell(W, 5, f"발행일: {datetime.now().strftime('%Y년 %m월 %d일')}", align="R", ln=True)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────

GENERATORS = {"A": generate_pdf_A, "B": generate_pdf_B, "C": generate_pdf_C}


def generate_pdf(report: dict, output_path: str, design: str = "C") -> str:
    fn = GENERATORS.get(design.upper(), generate_pdf_B)
    return fn(report, output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report_json", required=True)
    parser.add_argument("--output_pdf",  required=True)
    parser.add_argument("--design", default="C", choices=["A", "B", "C"],
                        help="PDF 디자인: A(미니멀) / B(기업 블루) / C(모던 액센트)")
    args = parser.parse_args()

    with open(args.report_json, encoding="utf-8") as f:
        report = json.load(f)

    if report.get("total_payment_amount", 0) == 0:
        print(f"[SKIP] 매출 없음 → PDF 생성 건너뜀 ({report.get('name','')})")
        sys.exit(0)

    out = generate_pdf(report, args.output_pdf, design=args.design)
    print(f"[OK] PDF 생성 완료 (Design {args.design}) → {out}")


if __name__ == "__main__":
    main()
