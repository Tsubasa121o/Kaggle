from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path


READ_ENCODINGS = ("cp932", "utf-8-sig", "utf-8")
WRITE_ENCODING = "cp932"
DAYS_PER_MONTH = 30.4375
EPS = 1e-9


@dataclass
class ReceiptEvent:
    receipt_date: date
    receipt_qty: float
    matched_qty: float
    lead_days: int


@dataclass
class OrderLine:
    po_no: str
    po_date: date
    vendor_code: str
    jan_code: str
    item_name: str
    model_no: str
    color: str
    size: str
    po_qty: float = 0.0
    source_row_count: int = 0
    events: list[ReceiptEvent] = field(default_factory=list)


@dataclass
class LineSummary:
    po_no: str
    po_date: date
    vendor_code: str
    jan_code: str
    item_name: str
    model_no: str
    color: str
    size: str
    po_qty: float
    receipt_total_qty: float
    matched_total_qty: float
    full_receipt_date: date | None
    full_lead_days: int | None
    progress_status: str


@dataclass
class JanAgg:
    vendor_code: str
    jan_code: str
    item_name: str
    qty_sum: float = 0.0
    weighted_qty_sum: float = 0.0
    weighted_lead_sum: float = 0.0
    recent_line_count: int = 0

    def add_complete(self, po_qty: float, lead_days: float, weight_factor: float) -> None:
        self.qty_sum += po_qty
        weight = po_qty * weight_factor
        self.weighted_qty_sum += weight
        self.weighted_lead_sum += weight * lead_days
        if weight_factor > 1.0:
            self.recent_line_count += 1

    def add_penalty(self, proxy_lead_days: float, penalty_weight: float) -> None:
        if penalty_weight <= EPS:
            return
        self.weighted_qty_sum += penalty_weight
        self.weighted_lead_sum += penalty_weight * proxy_lead_days


@dataclass
class FactoryAgg:
    vendor_code: str
    jan_count: int = 0
    jan_lt_sum_weighted: float = 0.0
    jan_weight_sum: float = 0.0

    def add(self, jan_lt_days: float, jan_weight: float) -> None:
        self.jan_count += 1
        self.jan_lt_sum_weighted += jan_lt_days * jan_weight
        self.jan_weight_sum += jan_weight


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    last_error: Exception | None = None
    for encoding in READ_ENCODINGS:
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                rows: list[dict[str, str]] = []
                for row in reader:
                    normalized: dict[str, str] = {}
                    for k, v in row.items():
                        if k is None:
                            continue
                        normalized[k.strip()] = (v or "").strip()
                    rows.append(normalized)
                return rows
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"CSVを読めませんでした: {path}") from last_error


def parse_float(value: str) -> float | None:
    s = (value or "").strip()
    if not s or s.upper() == "NULL":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_int(value: str) -> int | None:
    x = parse_float(value)
    if x is None:
        return None
    return int(x)


def parse_yyyymmdd(value: str) -> date | None:
    s = (value or "").strip()
    if not s or s.upper() == "NULL" or len(s) != 8 or not s.isdigit():
        return None
    try:
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def round_or_blank(x: float | None, digits: int = 2) -> str:
    if x is None:
        return ""
    return f"{round(x, digits):.{digits}f}"


def days_to_months(x: float | None) -> float | None:
    return None if x is None else x / DAYS_PER_MONTH


def write_csv_with_fallback(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> Path:
    try:
        with path.open("w", encoding=WRITE_ENCODING, newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        return path
    except PermissionError:
        alt = path.with_name(f"{path.stem}_new{path.suffix}")
        with alt.open("w", encoding=WRITE_ENCODING, newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        return alt


def first_value(row: dict[str, str], aliases: list[str]) -> str:
    for key in aliases:
        if key in row and row[key] != "":
            return row[key]
    return ""


def normalize_code(code: str) -> str:
    return code.strip().upper()


def build_factory_name_map(rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    for r in rows:
        code = first_value(r, ["code", "工場コード", "発注先コード"])
        if not code:
            continue
        name = first_value(r, ["resolved_name", "工場名", "名称", "発注先名"])
        mapping[normalize_code(code)] = (code, name)
    return mapping


def weighted_percentile(pairs: list[tuple[float, float]], percentile: float) -> float | None:
    pts = sorted((x, w) for x, w in pairs if w > EPS)
    if not pts:
        return None
    total_w = sum(w for _, w in pts)
    if total_w <= EPS:
        return None
    threshold = total_w * percentile
    acc = 0.0
    for x, w in pts:
        acc += w
        if acc >= threshold:
            return x
    return pts[-1][0]


def build_line_summaries(detail_rows: list[dict[str, str]]) -> list[LineSummary]:
    grouped: dict[tuple[str, str, str, date], OrderLine] = {}

    for r in detail_rows:
        po_no = first_value(r, ["po_no", "発注No"])
        vendor = first_value(r, ["vendor_code", "工場コード"])
        jan = first_value(r, ["jan_code", "JANコード"])
        po_date = parse_yyyymmdd(first_value(r, ["po_date_yyyymmdd", "発注日_yyyymmdd"]))
        if not po_no or not vendor or not jan or po_date is None:
            continue

        key = (po_no, normalize_code(vendor), jan, po_date)
        if key not in grouped:
            grouped[key] = OrderLine(
                po_no=po_no,
                po_date=po_date,
                vendor_code=normalize_code(vendor),
                jan_code=jan,
                item_name=first_value(r, ["item_name", "商品名"]),
                model_no=first_value(r, ["model_no", "品番"]),
                color=first_value(r, ["color", "カラー"]),
                size=first_value(r, ["size", "サイズ"]),
            )

        line = grouped[key]
        line.source_row_count += 1

        po_qty = parse_float(first_value(r, ["po_qty", "発注数量"]))
        if po_qty is not None:
            line.po_qty = max(line.po_qty, po_qty)

        receipt_date = parse_yyyymmdd(first_value(r, ["receipt_date_yyyymmdd", "入荷日_yyyymmdd"]))
        receipt_qty = parse_float(first_value(r, ["receipt_qty", "入荷数量"])) or 0.0
        matched_qty = parse_float(first_value(r, ["matched_receipt_qty", "発注対応入荷数量"])) or 0.0
        lead_days = parse_int(first_value(r, ["lead_days_from_po", "発注日から入荷日まで日数"]))

        if receipt_date is None or lead_days is None or lead_days < 0:
            continue
        if receipt_qty <= 0 and matched_qty <= 0:
            continue

        line.events.append(
            ReceiptEvent(
                receipt_date=receipt_date,
                receipt_qty=max(receipt_qty, 0.0),
                matched_qty=max(matched_qty, 0.0),
                lead_days=lead_days,
            )
        )

    summaries: list[LineSummary] = []
    for line in grouped.values():
        events = sorted(line.events, key=lambda e: e.receipt_date)
        receipt_total = sum(e.receipt_qty for e in events)
        matched_total = sum(e.matched_qty for e in events)

        full_receipt_date = None
        cum = 0.0
        for e in events:
            cum += e.matched_qty
            if line.po_qty > EPS and full_receipt_date is None and cum + EPS >= line.po_qty:
                full_receipt_date = e.receipt_date

        full_lead_days = None
        if full_receipt_date is not None:
            full_lead_days = (full_receipt_date - line.po_date).days

        if line.po_qty <= EPS:
            status = "ZERO_PO"
        elif matched_total <= EPS:
            status = "UNRECEIVED"
        elif matched_total + EPS < line.po_qty:
            status = "PARTIAL"
        elif receipt_total > line.po_qty + EPS:
            status = "COMPLETE_OVER"
        else:
            status = "COMPLETE"

        summaries.append(
            LineSummary(
                po_no=line.po_no,
                po_date=line.po_date,
                vendor_code=line.vendor_code,
                jan_code=line.jan_code,
                item_name=line.item_name,
                model_no=line.model_no,
                color=line.color,
                size=line.size,
                po_qty=line.po_qty,
                receipt_total_qty=receipt_total,
                matched_total_qty=matched_total,
                full_receipt_date=full_receipt_date,
                full_lead_days=full_lead_days,
                progress_status=status,
            )
        )

    return summaries


def build_factory_clip_map(lines: list[LineSummary], percentile: float) -> dict[str, float]:
    bucket: dict[str, list[tuple[float, float]]] = {}
    for ln in lines:
        if ln.progress_status not in ("COMPLETE", "COMPLETE_OVER"):
            continue
        if ln.full_lead_days is None or ln.po_qty <= EPS:
            continue
        bucket.setdefault(ln.vendor_code, []).append((float(ln.full_lead_days), ln.po_qty))

    clip_map: dict[str, float] = {}
    for code, pairs in bucket.items():
        p = weighted_percentile(pairs, percentile)
        if p is not None and p > 0:
            clip_map[code] = p
    return clip_map


def build_jan_agg(
    lines: list[LineSummary],
    recent_months: int,
    recent_weight: float,
    clip_map: dict[str, float],
    partial_penalty_factor: float,
    unreceived_penalty_factor: float,
    incomplete_clip_multiplier: float,
) -> list[dict[str, str]]:
    cutoff = date.today() - timedelta(days=30 * recent_months)
    today = date.today()
    agg: dict[tuple[str, str], JanAgg] = {}

    for ln in lines:
        if ln.progress_status not in ("COMPLETE", "COMPLETE_OVER"):
            continue
        if ln.full_receipt_date is None or ln.full_lead_days is None:
            continue
        if ln.po_qty <= EPS:
            continue

        key = (ln.vendor_code, ln.jan_code)
        if key not in agg:
            agg[key] = JanAgg(
                vendor_code=ln.vendor_code,
                jan_code=ln.jan_code,
                item_name=ln.item_name,
            )

        factor = recent_weight if ln.full_receipt_date >= cutoff else 1.0
        clipped_days = float(ln.full_lead_days)
        clip = clip_map.get(ln.vendor_code)
        if clip is not None and clipped_days > clip:
            clipped_days = clip

        agg[key].add_complete(po_qty=ln.po_qty, lead_days=clipped_days, weight_factor=factor)

    for ln in lines:
        if ln.po_qty <= EPS:
            continue
        if ln.progress_status not in ("PARTIAL", "UNRECEIVED"):
            continue

        key = (ln.vendor_code, ln.jan_code)
        if key not in agg:
            agg[key] = JanAgg(
                vendor_code=ln.vendor_code,
                jan_code=ln.jan_code,
                item_name=ln.item_name,
            )

        age_days = max((today - ln.po_date).days, 0)
        proxy_days = float(age_days)
        clip = clip_map.get(ln.vendor_code)
        if clip is not None and incomplete_clip_multiplier > 0:
            proxy_days = min(proxy_days, clip * incomplete_clip_multiplier)

        if ln.progress_status == "PARTIAL":
            remain_qty = max(ln.po_qty - ln.matched_total_qty, 0.0)
            penalty_base = remain_qty * max(partial_penalty_factor, 0.0)
        else:
            penalty_base = ln.po_qty * max(unreceived_penalty_factor, 0.0)

        factor = recent_weight if ln.po_date >= cutoff else 1.0
        penalty_weight = penalty_base * factor
        agg[key].add_penalty(proxy_lead_days=proxy_days, penalty_weight=penalty_weight)

    rows: list[dict[str, str]] = []
    for a in agg.values():
        jan_lt_days = None
        if a.weighted_qty_sum > EPS:
            jan_lt_days = a.weighted_lead_sum / a.weighted_qty_sum

        rows.append(
            {
                "工場コード": a.vendor_code,
                "JANコード": a.jan_code,
                "JANリードタイム日数": round_or_blank(jan_lt_days),
                "JANリードタイムカ月": round_or_blank(days_to_months(jan_lt_days)),
                "JAN重み": round_or_blank(max(a.qty_sum, a.weighted_qty_sum)),
                "JAN最近件数": str(a.recent_line_count),
            }
        )

    rows.sort(key=lambda r: (r["工場コード"], r["JANコード"]))
    return rows


def build_factory_agg(
    jan_rows: list[dict[str, str]],
    factory_map: dict[str, tuple[str, str]],
    min_jan_weight_floor: float,
) -> list[dict[str, str]]:
    agg: dict[str, FactoryAgg] = {}

    for r in jan_rows:
        code = normalize_code(first_value(r, ["工場コード"]))
        jan_lt = parse_float(first_value(r, ["JANリードタイム日数"]))
        jan_weight = parse_float(first_value(r, ["JAN重み"])) or 0.0
        if not code or jan_lt is None:
            continue

        if jan_weight > EPS:
            jan_weight = max(jan_weight, max(min_jan_weight_floor, 0.0))

        if code not in agg:
            agg[code] = FactoryAgg(vendor_code=code)
        agg[code].add(jan_lt_days=jan_lt, jan_weight=jan_weight)

    codes = sorted(set(factory_map.keys()) | set(agg.keys()))
    rows: list[dict[str, str]] = []

    for code in codes:
        f = agg.get(code, FactoryAgg(vendor_code=code))
        display_code, name = factory_map.get(code, (code, ""))

        lt_days_weighted = None
        if f.jan_weight_sum > EPS:
            lt_days_weighted = f.jan_lt_sum_weighted / f.jan_weight_sum

        rows.append(
            {
                "工場コード": display_code,
                "工場名": name,
                "工場LTカ月_JAN数量加重平均": round_or_blank(days_to_months(lt_days_weighted)),
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="リードタイム明細CSVから工場別リードタイムを算出")
    parser.add_argument("--recent-months", type=int, default=6)
    parser.add_argument("--recent-weight", type=float, default=1.2)
    parser.add_argument("--clip-percentile", type=float, default=0.95)
    parser.add_argument("--min-jan-weight-floor", type=float, default=30.0)
    parser.add_argument("--partial-penalty-factor", type=float, default=0.35)
    parser.add_argument("--unreceived-penalty-factor", type=float, default=0.20)
    parser.add_argument("--incomplete-clip-multiplier", type=float, default=1.5)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "データ"

    lead_path = data_dir / "リードタイムクエリ.csv"
    factory_path = data_dir / "工場コードクエリ.csv"
    out_factory = data_dir / "工場別リードタイム最終出力.csv"

    detail_rows = read_csv_rows(lead_path)
    factory_rows = read_csv_rows(factory_path)
    factory_map = build_factory_name_map(factory_rows)

    lines = build_line_summaries(detail_rows)
    clip_map = build_factory_clip_map(lines, percentile=args.clip_percentile)
    jan_rows = build_jan_agg(
        lines,
        recent_months=args.recent_months,
        recent_weight=args.recent_weight,
        clip_map=clip_map,
        partial_penalty_factor=args.partial_penalty_factor,
        unreceived_penalty_factor=args.unreceived_penalty_factor,
        incomplete_clip_multiplier=args.incomplete_clip_multiplier,
    )
    factory_rows_out = build_factory_agg(
        jan_rows,
        factory_map,
        min_jan_weight_floor=args.min_jan_weight_floor,
    )

    factory_fields = ["工場コード", "工場名", "工場LTカ月_JAN数量加重平均"]
    out_path = write_csv_with_fallback(out_factory, factory_fields, factory_rows_out)

    complete_count = sum(1 for x in lines if x.progress_status in ("COMPLETE", "COMPLETE_OVER"))
    print(f"入力明細行数: {len(detail_rows)}")
    print(f"発注行サマリ件数: {len(lines)}")
    print(f"完納行件数: {complete_count}")
    print(f"クリップ適用工場数: {len(clip_map)}")
    print(f"最終出力: {out_path}")


if __name__ == "__main__":
    main()
