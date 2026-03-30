import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional

import pandas as pd

OPTION_COLUMN_CANDIDATES = [
    "옵션",
    "옵션명",
    "상품옵션",
    "상품옵션(기본)",
    "항목명",
    "항목 옵션",
    "상품명(옵션포함)",
    "주문상품명",
    "상품명",
]

COUNT_COLUMN_CANDIDATES = [
    "수량",
    "주문수량",
    "상품수량",
]

STATUS_COLUMN_CANDIDATES = [
    "주문상태",
    "결제상태",
]

PAID_AT_COLUMN_CANDIDATES = [
    "결제일시(입금확인일)",
    "결제일자(입금확인일)",
]

PURCHASE_AMOUNT_COLUMN_CANDIDATES = [
    "상품구매금액(KRW)",
    "상품구매금액",
]

POINT_COLUMN_CANDIDATES = [
    "사용한 적립금액(최종)",
]

COUPON_COLUMN_CANDIDATES = [
    "주문서 쿠폰 할인금액",
    "주문시 쿠폰 할인금액",
]

REFUND_COLUMN_CANDIDATES = [
    "실제 환불금액",
]

EXCLUDE_STATUS_KEYWORDS = [
    "취소",
    "환불",
    "반품",
]


def pick_column(df: pd.DataFrame, candidates: List[str]) -> str | None:
    col_map = {str(c).strip(): c for c in df.columns}
    for c in candidates:
        if c in col_map:
            return col_map[c]
    return None


def to_number(v) -> float:
    if pd.isna(v):
        return 0.0
    s = str(v).strip().replace(",", "").replace("원", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def is_blank(v) -> bool:
    if pd.isna(v):
        return True
    s = str(v).strip()
    return s == "" or s.lower() == "nan"


def normalize_option(option_text: str) -> str:
    if option_text is None:
        return "옵션없음"
    s = str(option_text).strip()
    if not s:
        return "옵션없음"
    # "수량=(…)" 형태 제거 (할인율 포함된 경우도 처리)
    s = re.sub(r"\s*수량=\([^)]*\)\s*", " ", s).strip()
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = s.rstrip(",/|").strip()
    return s if s else "옵션없음"


def should_exclude_row(status_text: str) -> bool:
    s = str(status_text or "").strip()
    return any(k in s for k in EXCLUDE_STATUS_KEYWORDS)


def _compute_segments(
    start_date: date,
    end_date: date,
    special_start: Optional[date],
    special_end: Optional[date],
    base_fee_rate: float,
    special_fee_rate: Optional[float],
) -> List[Dict]:
    """정산 기간을 특별 기간 기준으로 최대 3개 구간으로 분할."""
    if not special_start or not special_end or not special_fee_rate:
        return [{"start": start_date, "end": end_date, "fee_rate": base_fee_rate, "label": "일반"}]

    # 특별 기간을 정산 기간 내로 클램핑
    css = max(start_date, special_start)
    cse = min(end_date, special_end)

    # 겹치지 않으면 단일 구간
    if css > cse:
        return [{"start": start_date, "end": end_date, "fee_rate": base_fee_rate, "label": "일반"}]

    segments = []
    if css > start_date:
        segments.append({"start": start_date, "end": css - timedelta(days=1), "fee_rate": base_fee_rate, "label": "일반"})
    segments.append({"start": css, "end": cse, "fee_rate": special_fee_rate, "label": "특별"})
    if cse < end_date:
        segments.append({"start": cse + timedelta(days=1), "end": end_date, "fee_rate": base_fee_rate, "label": "일반"})

    return segments


def _aggregate_slice(work: pd.DataFrame, qty_col: Optional[str]) -> Dict:
    """DataFrame 슬라이스에 대한 옵션별 집계."""
    total_amount = float(work["__amount__"].sum())
    total_count = int(work["__qty__"].sum())

    option_rows = []
    for option_name, g in work.groupby("__option__", dropna=False):
        option_rows.append({
            "option_name": option_name,
            "payment_amount": float(g["__amount__"].sum()),
            "payment_count": int(g["__qty__"].sum()),
        })
    option_rows = sorted(option_rows, key=lambda x: x["option_name"])

    return {
        "total_payment_amount": total_amount,
        "total_payment_count": total_count,
        "options": option_rows,
    }


def analyze_excel(
    excel_path: str,
    product_code: str,
    start_date: str,
    end_date: str,
    base_fee_rate: float,
    entity_type: str,
    special_fee_rate: Optional[float] = None,
    special_period_start: Optional[str] = None,
    special_period_end: Optional[str] = None,
) -> Dict[str, Any]:
    if excel_path.lower().endswith(".csv"):
        df = pd.read_csv(excel_path)
    else:
        df = pd.read_excel(excel_path, engine="openpyxl")

    option_col = pick_column(df, OPTION_COLUMN_CANDIDATES)
    qty_col = pick_column(df, COUNT_COLUMN_CANDIDATES)
    status_col = pick_column(df, STATUS_COLUMN_CANDIDATES)
    paid_at_col = pick_column(df, PAID_AT_COLUMN_CANDIDATES)
    purchase_amount_col = pick_column(df, PURCHASE_AMOUNT_COLUMN_CANDIDATES)
    point_col = pick_column(df, POINT_COLUMN_CANDIDATES)
    coupon_col = pick_column(df, COUPON_COLUMN_CANDIDATES)
    refund_col = pick_column(df, REFUND_COLUMN_CANDIDATES)

    if option_col is None:
        raise RuntimeError(f"옵션 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")
    if paid_at_col is None:
        raise RuntimeError(f"결제일시 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")
    if purchase_amount_col is None:
        raise RuntimeError(f"'상품구매금액(KRW)' 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")
    if point_col is None:
        raise RuntimeError(f"'사용한 적립금액(최종)' 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")
    if coupon_col is None:
        raise RuntimeError(f"쿠폰 할인금액 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")
    if refund_col is None:
        raise RuntimeError(f"'실제 환불금액' 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")

    work = df.copy()
    work = work[~work[paid_at_col].apply(is_blank)]
    if status_col is not None:
        work = work[~work[status_col].astype(str).apply(should_exclude_row)]

    # 결제일시를 date 객체로 파싱
    work["__paid_date__"] = pd.to_datetime(work[paid_at_col], errors="coerce").dt.date

    work["__option__"] = work[option_col].apply(normalize_option)
    work["__purchase_amount__"] = work[purchase_amount_col].apply(to_number)
    work["__point_amount__"] = work[point_col].apply(to_number) if point_col else 0.0
    work["__coupon_amount__"] = work[coupon_col].apply(to_number)
    work["__refund_amount__"] = work[refund_col].apply(to_number)
    work["__amount__"] = (
        work["__purchase_amount__"]
        - work["__point_amount__"]
        - work["__coupon_amount__"]
        - work["__refund_amount__"]
    )

    if qty_col is not None:
        work["__qty__"] = work.apply(
            lambda r: 0 if r["__refund_amount__"] > 0
            else int(to_number(r[qty_col])) if to_number(r[qty_col]) > 0
            else 1,
            axis=1,
        )
    else:
        work["__qty__"] = work.apply(
            lambda r: 0 if r["__refund_amount__"] > 0 else 1,
            axis=1,
        )

    # 날짜 파싱
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    elapsed_days = (end_dt - start_dt).days + 1

    sp_start = datetime.strptime(special_period_start, "%Y-%m-%d").date() if special_period_start else None
    sp_end = datetime.strptime(special_period_end, "%Y-%m-%d").date() if special_period_end else None

    # 구간 분할
    segments_meta = _compute_segments(start_dt, end_dt, sp_start, sp_end, base_fee_rate, special_fee_rate)

    segments_result = []
    total_fee_amount = 0
    grand_total_amount = 0
    grand_total_count = 0

    for seg in segments_meta:
        seg_start: date = seg["start"]
        seg_end: date = seg["end"]
        fee_rate: float = seg["fee_rate"]
        label: str = seg["label"]

        # 해당 구간 행 필터링
        mask = (work["__paid_date__"] >= seg_start) & (work["__paid_date__"] <= seg_end)
        slice_df = work[mask]

        agg = _aggregate_slice(slice_df, qty_col)
        fee_amount = round(agg["total_payment_amount"] * (fee_rate / 100.0))
        total_fee_amount += fee_amount
        grand_total_amount += agg["total_payment_amount"]
        grand_total_count += agg["total_payment_count"]

        segments_result.append({
            "label": label,
            "start_date": seg_start.isoformat(),
            "end_date": seg_end.isoformat(),
            "fee_rate": fee_rate,
            "total_payment_amount": agg["total_payment_amount"],
            "total_payment_count": agg["total_payment_count"],
            "fee_amount": fee_amount,
            "options": agg["options"],
        })

    return {
        "product_code": product_code,
        "start_date": start_date,
        "end_date": end_date,
        "elapsed_days": elapsed_days,
        "base_fee_rate": base_fee_rate,
        "special_fee_rate": special_fee_rate,
        "special_period_start": special_period_start,
        "special_period_end": special_period_end,
        "entity_type": entity_type,
        "segments": segments_result,
        "total_payment_amount": grand_total_amount,
        "total_payment_count": grand_total_count,
        "total_fee_amount": total_fee_amount,
        "source_file": excel_path,
    }
