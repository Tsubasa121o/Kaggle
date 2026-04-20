import argparse
import os
from typing import List

import pandas as pd


REQUIRED_STOCKOUT_COLS = ["商品コード", "在庫切れ日", "入荷再開日", "在庫ゼロ日数", "欠品ステータス"]
REQUIRED_TRANSFER_COLS = ["商品コード", "入出荷日", "伝票識別", "入荷数"]


def project_root() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    return os.path.dirname(base_dir)


def default_stockout_csv(root: str) -> str:
    return os.path.join(root, "データ", "在庫切れ期間一覧_452限定.csv")


def default_transfer_csv(root: str) -> str:
    return os.path.join(root, "データ", "八王子振替入庫クエリ.csv")


def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def normalize_warehouse_code(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(".0", "", regex=False)
    s = s.replace({"nan": "", "None": ""})
    is_digits = s.str.fullmatch(r"\d+")
    s.loc[is_digits] = s.loc[is_digits].str.zfill(4)
    return s


def parse_stockout_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def parse_transfer_date(series: pd.Series) -> pd.Series:
    raw = series.astype(str).str.strip().str.replace(".0", "", regex=False)
    return pd.to_datetime(raw, format="%Y%m%d", errors="coerce")


def validate_columns(df: pd.DataFrame, required: List[str], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"{label} の必要列が不足しています: {missing}")


def build_transfer_events(
    transfers: pd.DataFrame,
    jan_prefix: str,
    hq_code: str,
    hachioji_code: str,
) -> pd.DataFrame:
    validate_columns(transfers, REQUIRED_TRANSFER_COLS, "振替CSV")

    t = transfers.copy()
    t["商品コード"] = t["商品コード"].astype(str).str.strip()
    t["入出荷日_dt"] = parse_transfer_date(t["入出荷日"])
    t["入荷数_num"] = pd.to_numeric(t["入荷数"], errors="coerce")

    mask = t["商品コード"].str.startswith(jan_prefix, na=False)
    mask &= t["入出荷日_dt"].notna()
    mask &= t["伝票識別"].astype(str).str.contains("振替", na=False)
    mask &= t["入荷数_num"] > 0

    if "倉庫コード" in t.columns:
        t["倉庫コード"] = normalize_warehouse_code(t["倉庫コード"])
        mask &= t["倉庫コード"] == hq_code
    if "相手倉庫コード" in t.columns:
        t["相手倉庫コード"] = normalize_warehouse_code(t["相手倉庫コード"])
        mask &= t["相手倉庫コード"] == hachioji_code

    t = t.loc[mask, ["商品コード", "入出荷日_dt"]].copy()
    t = t.drop_duplicates().sort_values(["商品コード", "入出荷日_dt"]).reset_index(drop=True)
    return t


def supplement_open_rows(
    stockouts: pd.DataFrame,
    transfer_events: pd.DataFrame,
    hq_code: str,
    allow_same_day: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_columns(stockouts, REQUIRED_STOCKOUT_COLS, "在庫切れCSV")

    s = stockouts.copy()
    s["商品コード"] = s["商品コード"].astype(str).str.strip()
    s["在庫切れ日_dt"] = parse_stockout_date(s["在庫切れ日"])
    if "倉庫コード" in s.columns:
        s["倉庫コード"] = normalize_warehouse_code(s["倉庫コード"])

    open_mask = s["欠品ステータス"].astype(str).str.upper() == "OPEN"
    open_mask &= s["在庫切れ日_dt"].notna()
    if "倉庫コード" in s.columns:
        open_mask &= s["倉庫コード"] == hq_code

    open_rows = s.loc[open_mask].copy()
    if open_rows.empty or transfer_events.empty:
        s = s.drop(columns=["在庫切れ日_dt"], errors="ignore")
        return s, pd.DataFrame(columns=["商品コード", "倉庫コード", "在庫切れ日", "補完前ステータス", "補完後入荷再開日", "補完後在庫ゼロ日数"])

    tmap = {}
    for code, g in transfer_events.groupby("商品コード", sort=False):
        arr = g["入出荷日_dt"].sort_values().dropna().drop_duplicates().values
        if len(arr) > 0:
            tmap[code] = arr

    matches = []
    side = "left" if allow_same_day else "right"
    for i, row in open_rows.iterrows():
        code = row["商品コード"]
        start_dt = row["在庫切れ日_dt"]
        if pd.isna(start_dt) or code not in tmap:
            continue
        arr = tmap[code]
        pos = arr.searchsorted(start_dt.to_datetime64(), side=side)
        if pos < len(arr):
            matches.append((i, pd.Timestamp(arr[pos])))

    if not matches:
        s = s.drop(columns=["在庫切れ日_dt"], errors="ignore")
        return s, pd.DataFrame(columns=["商品コード", "倉庫コード", "在庫切れ日", "補完前ステータス", "補完後入荷再開日", "補完後在庫ゼロ日数"])

    original_index = pd.Index([m[0] for m in matches])
    supply_dates = pd.Series([m[1] for m in matches], index=original_index)
    stockout_dates = s.loc[original_index, "在庫切れ日_dt"]
    zero_days = (supply_dates.values - stockout_dates.values).astype("timedelta64[D]").astype(int)

    s.loc[original_index, "入荷再開日"] = supply_dates.dt.strftime("%Y-%m-%d").values
    s.loc[original_index, "在庫ゼロ日数"] = zero_days
    s.loc[original_index, "欠品ステータス"] = "CLOSED"

    changes = s.loc[original_index, ["商品コード", "在庫切れ日", "欠品ステータス"]].copy()
    changes["補完前ステータス"] = "OPEN"
    changes["補完後入荷再開日"] = supply_dates.dt.strftime("%Y-%m-%d").values
    changes["補完後在庫ゼロ日数"] = zero_days
    if "倉庫コード" in s.columns:
        changes["倉庫コード"] = s.loc[original_index, "倉庫コード"].values
        changes = changes[["商品コード", "倉庫コード", "在庫切れ日", "補完前ステータス", "補完後入荷再開日", "補完後在庫ゼロ日数"]]
    else:
        changes = changes[["商品コード", "在庫切れ日", "補完前ステータス", "補完後入荷再開日", "補完後在庫ゼロ日数"]]

    s = s.drop(columns=["在庫切れ日_dt"], errors="ignore")
    return s, changes.reset_index(drop=True)


def main() -> None:
    root = project_root()
    default_out_dir = os.path.join(root, "データ")

    parser = argparse.ArgumentParser(description="八王子→本店の振替入庫で OPEN 欠品を補完")
    parser.add_argument("--stockout-csv", default=default_stockout_csv(root), help="在庫切れ期間一覧CSV")
    parser.add_argument("--transfer-csv", default=default_transfer_csv(root), help="八王子振替入庫クエリCSV")
    parser.add_argument("--output-dir", default=default_out_dir, help="出力先ディレクトリ")
    parser.add_argument("--jan-prefix", default="452", help="対象JANプレフィックス")
    parser.add_argument("--hq-code", default="0000", help="本店倉庫コード")
    parser.add_argument("--hachioji-code", default="0003", help="八王子倉庫コード")
    parser.add_argument("--strict-after", action="store_true", help="在庫切れ日より後日(>)のみ補完。同日は除外")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Using stockout CSV: {args.stockout_csv}")
    print(f"Using transfer CSV: {args.transfer_csv}")

    stockouts = load_csv(args.stockout_csv)
    transfers = load_csv(args.transfer_csv)

    transfer_events = build_transfer_events(
        transfers=transfers,
        jan_prefix=args.jan_prefix,
        hq_code=args.hq_code,
        hachioji_code=args.hachioji_code,
    )

    complemented, changes = supplement_open_rows(
        stockouts=stockouts,
        transfer_events=transfer_events,
        hq_code=args.hq_code,
        allow_same_day=not args.strict_after,
    )

    out_main = os.path.join(args.output_dir, "在庫切れ期間一覧_452限定_八王子補完後.csv")
    out_diff = os.path.join(args.output_dir, "在庫切れ期間補完差分_八王子振替入庫.csv")

    complemented.to_csv(out_main, encoding="utf-8-sig", index=False)
    changes.to_csv(out_diff, encoding="utf-8-sig", index=False)

    before_open = (stockouts["欠品ステータス"].astype(str).str.upper() == "OPEN").sum()
    after_open = (complemented["欠品ステータス"].astype(str).str.upper() == "OPEN").sum()
    after_closed = (complemented["欠品ステータス"].astype(str).str.upper() == "CLOSED").sum()

    print("\nDone.")
    print(f"transfer events: {len(transfer_events):,}")
    print(f"complemented rows: {len(changes):,}")
    print(f"OPEN before: {before_open:,}")
    print(f"OPEN after:  {after_open:,}")
    print(f"CLOSED after: {after_closed:,}")
    print(f"Output main: {out_main}")
    print(f"Output diff: {out_diff}")


if __name__ == "__main__":
    main()
