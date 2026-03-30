"""
정산팀 Notion 도구.

사용법 1 — 정산 대상 조회:
  python tools/settlement_notion.py fetch-targets \
    --output teams/settlement/outputs/{run_id}/targets.json

사용법 2 — 정산서 Notion 페이지에 추가:
  python tools/settlement_notion.py append-report \
    --page_id "abc123..." \
    --report_json "teams/settlement/outputs/{run_id}/report_{name}.json"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SETTLEMENT_DB_ID = "3337b6aa-8429-80a4-a365-ff5ef0e5e8a9"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('NOTION_TOKEN')}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


# ── Notion 블록 헬퍼 ─────────────────────────────────────

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


def _para(text: str) -> dict:
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text[:2000]}}]},
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _table_row(cells: list[str]) -> dict:
    return {
        "type": "table_row",
        "table_row": {
            "cells": [[{"type": "text", "text": {"content": str(c)}}] for c in cells]
        },
    }


def _table(header: list[str], rows: list[list[str]]) -> dict:
    children = [_table_row(header)] + [_table_row(r) for r in rows]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(header),
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        },
    }


def _callout(text: str, emoji: str = "💰") -> dict:
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"text": {"content": text[:2000]}}],
            "icon": {"emoji": emoji},
        },
    }


# ── 정산 대상 조회 ────────────────────────────────────────

def _query_database(db_id: str, filter_body: dict | None = None) -> list[dict]:
    """Notion DB query via httpx (notion-client v3 호환)."""
    url = f"{NOTION_API_BASE}/databases/{db_id}/query"
    headers = _notion_headers()
    all_results = []
    body = {}
    if filter_body:
        body["filter"] = filter_body
    cursor = None

    while True:
        if cursor:
            body["start_cursor"] = cursor
        resp = httpx.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return all_results


def fetch_active_targets(db_id: str) -> list[dict]:
    """상태가 '활성중'인 정산 대상 전체 조회."""
    pages = _query_database(db_id, filter_body={
        "property": "상태",
        "select": {"equals": "활성중"},
    })

    results = []
    for page in pages:
        props = page.get("properties", {})

        def get_text(prop_name: str) -> str:
            p = props.get(prop_name, {})
            ptype = p.get("type", "")
            if ptype == "title":
                items = p.get("title", [])
            elif ptype == "rich_text":
                items = p.get("rich_text", [])
            else:
                return ""
            return "".join(i.get("plain_text", "") for i in items).strip()

        def get_number(prop_name: str) -> float:
            p = props.get(prop_name, {})
            return float(p.get("number") or 0)

        def get_select(prop_name: str) -> str:
            p = props.get(prop_name, {})
            sel = p.get("select") or p.get("status") or {}
            return sel.get("name", "")

        def get_phone(prop_name: str) -> str:
            p = props.get(prop_name, {})
            return p.get("phone_number", "") or get_text(prop_name)

        def get_people_name(prop_name: str) -> str:
            p = props.get(prop_name, {})
            people = p.get("people", [])
            return people[0].get("name", "") if people else ""

        def to_pct(raw: float) -> float:
            """0.2 → 20.0, 20 → 20.0"""
            return raw * 100 if raw < 1 else raw

        raw_base = get_number("기본 수수료율")
        base_fee_rate = to_pct(raw_base)

        raw_special = get_number("특별 수수료율")
        special_fee_rate = to_pct(raw_special) if raw_special else None

        # 특별 기간: date 타입 (start / end)
        sp_prop = props.get("특별 기간", {})
        sp_date = sp_prop.get("date") or {}
        special_period_start = sp_date.get("start") or None    # "2026-03-08"
        special_period_end   = sp_date.get("end")   or None    # "2026-03-14"

        results.append({
            "notion_page_id": page["id"],
            "name": get_text("이름"),
            "product_name": get_select("제품명"),
            "product_code": get_text("상품코드"),
            "base_fee_rate": base_fee_rate,
            "special_fee_rate": special_fee_rate,
            "special_period_start": special_period_start,
            "special_period_end": special_period_end,
            "entity_type": get_select("과세유형"),
            "contact_person": get_people_name("담당자"),
            "contact_phone": get_phone("담당자 연락처"),
            "brand": get_select("브랜드"),
        })

    return results


# ── 정산서 Notion 블록 구성 ──────────────────────────────

def build_settlement_blocks(report: dict) -> list[dict]:
    """새 데이터 구조(segments) 기반 요약 블록."""
    blocks = []
    entity_type = report.get("entity_type", "")
    period = f"{report.get('start_date', '')} ~ {report.get('end_date', '')}"

    blocks.append(_divider())
    blocks.append(_h2(f"브레인올로지 정산서 — {period}"))

    # ── 기본 정보 요약
    base_rate    = report.get("base_fee_rate", report.get("fee_rate", 0))
    special_rate = report.get("special_fee_rate")
    sp_start     = report.get("special_period_start")
    sp_end       = report.get("special_period_end")

    rate_desc = f"기본 {base_rate:.0f}%"
    if special_rate and sp_start and sp_end:
        rate_desc += f"  /  특별 {special_rate:.0f}% ({sp_start} ~ {sp_end})"

    info_lines = [
        f"정산 대상: {report.get('name', '')}",
        f"제품명: {report.get('product_name', '')}  ({report.get('product_code', '')})",
        f"정산 기간: {period}  ({report.get('elapsed_days', '')}일)",
        f"수수료율: {rate_desc}",
        f"과세유형: {entity_type}",
    ]
    blocks.append(_para("\n".join(info_lines)))
    blocks.append(_divider())

    # ── 구간별 매출 테이블
    blocks.append(_h3("구간별 매출 집계"))

    total_amt = int(report.get("total_payment_amount", 0))

    if total_amt == 0:
        blocks.append(_callout(f"해당 기간({period}) 매출 없음", "📭"))
        blocks.append(_divider())
        return blocks

    header = ["구간", "결제건수", "결제금액", "수수료율", "수수료"]
    rows = []
    for seg in report.get("segments", []):
        if seg["total_payment_count"] == 0:
            continue
        rows.append([
            f"[{seg['label']}] {seg['start_date']}~{seg['end_date']}",
            f"{seg['total_payment_count']:,}건",
            f"{int(seg['total_payment_amount']):,}원",
            f"{seg['fee_rate']:.0f}%",
            f"{int(seg['fee_amount']):,}원",
        ])

    if rows:
        # 합계 행
        rows.append([
            "합계",
            f"{int(report.get('total_payment_count', 0)):,}건",
            f"{int(report.get('total_payment_amount', 0)):,}원",
            "—",
            f"{int(report.get('total_fee_amount', 0)):,}원",
        ])
        blocks.append(_table(header, rows))

    blocks.append(_divider())

    # ── 최종 정산 요약 callout
    total_fee = int(report.get("total_fee_amount", 0))
    final     = int(report.get("final_settlement_amount", total_fee))
    withheld  = int(report.get("withholding_tax_amount", 0))

    if "3.3" in entity_type or "원천세" in entity_type:
        callout = (f"합산 수수료 {total_fee:,}원  −  원천세(3.3%) {withheld:,}원\n"
                   f"💰 최종 정산금액: {final:,}원  (원천세 공제 후)")
    else:
        callout = (f"합산 수수료 {total_fee:,}원\n"
                   f"💰 최종 정산금액: {final:,}원  (VAT 포함금액)")

    blocks.append(_callout(callout, "💰"))

    return blocks


def _upload_pdf(pdf_path: str) -> str:
    """PDF를 Notion File Upload API로 업로드하고 file_upload_id 반환."""
    fname = Path(pdf_path).name
    fsize = Path(pdf_path).stat().st_size
    headers_json = _notion_headers()

    # 1) 업로드 세션 생성
    resp = httpx.post(
        f"{NOTION_API_BASE}/file_uploads",
        headers=headers_json,
        json={"content_type": "application/pdf", "size": fsize,
              "name": fname, "mode": "single_part"},
        timeout=30,
    )
    resp.raise_for_status()
    upload_id = resp.json()["id"]

    # 2) 바이너리 전송 (multipart)
    upload_headers = {
        "Authorization": headers_json["Authorization"],
        "Notion-Version": headers_json["Notion-Version"],
    }
    with open(pdf_path, "rb") as f:
        data = f.read()
    resp2 = httpx.post(
        f"{NOTION_API_BASE}/file_uploads/{upload_id}/send",
        headers=upload_headers,
        files={"file": (fname, data, "application/pdf")},
        timeout=60,
    )
    resp2.raise_for_status()

    return upload_id


def _file_block(upload_id: str, filename: str) -> dict:
    """업로드된 파일을 페이지에 첨부하는 블록."""
    return {
        "object": "block",
        "type": "file",
        "file": {
            "type": "file_upload",
            "file_upload": {"id": upload_id},
            "name": filename,
        },
    }


def append_report_to_page(page_id: str, report: dict, pdf_path: str | None = None) -> bool:
    """기존 Notion 페이지 본문 끝에 정산 요약 블록 + PDF 첨부."""
    blocks = build_settlement_blocks(report)

    # PDF 첨부 블록 추가
    if pdf_path and Path(pdf_path).exists():
        upload_id = _upload_pdf(pdf_path)
        blocks.append(_file_block(upload_id, Path(pdf_path).name))

    url = f"{NOTION_API_BASE}/blocks/{page_id}/children"
    headers = _notion_headers()

    chunk_size = 95
    for i in range(0, len(blocks), chunk_size):
        resp = httpx.patch(
            url, headers=headers,
            json={"children": blocks[i: i + chunk_size]},
            timeout=30,
        )
        resp.raise_for_status()
    return True


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    # fetch-targets
    p_fetch = sub.add_parser("fetch-targets")
    p_fetch.add_argument("--output", required=True)

    # append-report
    p_append = sub.add_parser("append-report")
    p_append.add_argument("--page_id", required=True)
    p_append.add_argument("--report_json", required=True)
    p_append.add_argument("--pdf_path", default=None)

    args = parser.parse_args()

    if args.command == "fetch-targets":
        targets = fetch_active_targets(SETTLEMENT_DB_ID)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(targets, f, ensure_ascii=False, indent=2)
        print(f"[OK] {len(targets)}개 정산 대상 조회 완료 → {args.output}")

    elif args.command == "append-report":
        with open(args.report_json, encoding="utf-8") as f:
            report = json.load(f)
        append_report_to_page(args.page_id, report, pdf_path=args.pdf_path)
        print(f"[OK] 정산서 Notion 업로드 완료 → page_id: {args.page_id}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
