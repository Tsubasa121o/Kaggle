import argparse
import os
import re
from pathlib import Path
from typing import List

import pandas as pd


BLACKLIST = ["【繰 越 在 庫】", "【期 間 合 計】", "デグナー八王子店"]
TARGET_WAREHOUSES = {"0000"}
REQUIRED_COLS = ["商品コード", "入出荷日", "伝票識別", "入荷数", "出荷数", "在庫数", "入出荷先名"]


def project_root() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    return os.path.dirname(base_dir)


def default_input_csv(root: str) -> str:
    data_dir = os.path.join(root, "データ")
    cand = os.path.join(data_dir, "在庫受払帳再現クエリ.csv")
    if os.path.exists(cand):
        return cand
    raise FileNotFoundError(f"入力CSVが見つかりません: {cand}")


def parse_target_jans(jan_csv_path: str, jan_prefix: str) -> set:
    jan_set = set()
    if not jan_csv_path or not os.path.exists(jan_csv_path):
        return jan_set
    pattern = re.compile(rf"({re.escape(jan_prefix)}\d+)")
    with open(jan_csv_path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            first_col = line.split(",")[0].strip().strip('"')
            m = pattern.fullmatch(first_col)
            if m:
                jan_set.add(m.group(1))
    return jan_set


def normalize_yyyymmdd(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series.astype(str).str.replace(".0", "", regex=False),
        format="%Y%m%d",
        errors="coerce",
    )


def normalize_warehouse_code(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(".0", "", regex=False)
    s = s.replace({"nan": "", "None": ""})
    is_digits = s.str.fullmatch(r"\d+")
    s.loc[is_digits] = s.loc[is_digits].str.zfill(4)
    return s


def load_ledger_csv(input_csv: str) -> pd.DataFrame:
    df = pd.read_csv(input_csv, encoding="utf-8-sig", low_memory=False)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"必要列が不足しています: {missing}")
    return df


def cleanse_and_filter(df: pd.DataFrame, jan_prefix: str, target_jans: set) -> pd.DataFrame:
    df2 = df.copy()
    df2["商品コード"] = df2["商品コード"].astype(str).str.strip()
    df2["入出荷日"] = normalize_yyyymmdd(df2["入出荷日"])
    if "倉庫コード" in df2.columns:
        df2["倉庫コード"] = normalize_warehouse_code(df2["倉庫コード"])

    mask = df2["入出荷先名"].astype(str).apply(lambda x: not any(word in x for word in BLACKLIST))
    df2 = df2[mask].copy()
    if "倉庫コード" in df2.columns:
        df2 = df2[df2["倉庫コード"].isin(TARGET_WAREHOUSES)].copy()
    df2 = df2[df2["入出荷日"].notna()].copy()
    df2 = df2[df2["商品コード"].str.startswith(jan_prefix, na=False)].copy()

    if target_jans:
        df2 = df2[df2["商品コード"].isin(target_jans)].copy()

    df2["入荷数_num"] = pd.to_numeric(df2["入荷数"], errors="coerce")
    df2["出荷数_num"] = pd.to_numeric(df2["出荷数"], errors="coerce")
    df2["在庫数_num"] = pd.to_numeric(df2["在庫数"], errors="coerce")
    df2["_row_no"] = range(len(df2))
    return df2


def group_keys(df: pd.DataFrame) -> List[str]:
    keys = ["商品コード"]
    if "倉庫コード" in df.columns:
        keys.append("倉庫コード")
    return keys


def build_stockout_periods(df: pd.DataFrame, include_open: bool = True) -> pd.DataFrame:
    out = []
    keys = group_keys(df)
    as_of_date = df["入出荷日"].max()

    for key_vals, g in df.groupby(keys, dropna=False, sort=False):
        g = g.sort_values(["入出荷日", "_row_no"]).reset_index(drop=True)
        stock = g["在庫数_num"]
        starts = g.index[(stock == 0) & (stock.shift(1).fillna(1) > 0)].tolist()

        for s in starts:
            stockout_date = g.loc[s, "入出荷日"]
            if pd.isna(stockout_date):
                continue

            if isinstance(key_vals, tuple):
                code = key_vals[0]
                wh = key_vals[1] if len(key_vals) > 1 else None
            else:
                code = key_vals
                wh = None

            tail = g.iloc[s + 1 :]
            supply = tail[(tail["伝票識別"] == "仕入") & (tail["入荷数_num"] > 0)]
            if supply.empty:
                if not include_open or pd.isna(as_of_date):
                    continue
                row = {
                    "商品コード": code,
                    "在庫切れ日": stockout_date,
                    "入荷再開日": pd.NaT,
                    "在庫ゼロ日数": (as_of_date - stockout_date).days,
                    "欠品ステータス": "OPEN",
                }
                if wh is not None:
                    row["倉庫コード"] = wh
                out.append(row)
                continue

            first_supply = supply.iloc[0]
            supply_date = first_supply["入出荷日"]
            if pd.isna(stockout_date) or pd.isna(supply_date):
                continue

            row = {
                "商品コード": code,
                "在庫切れ日": stockout_date,
                "入荷再開日": supply_date,
                "在庫ゼロ日数": (supply_date - stockout_date).days,
                "欠品ステータス": "CLOSED",
            }
            if wh is not None:
                row["倉庫コード"] = wh
            out.append(row)

    if not out:
        cols = ["商品コード", "在庫切れ日", "入荷再開日", "在庫ゼロ日数", "欠品ステータス"]
        if "倉庫コード" in df.columns:
            cols = ["商品コード", "倉庫コード", "在庫切れ日", "入荷再開日", "在庫ゼロ日数", "欠品ステータス"]
        return pd.DataFrame(columns=cols)

    res = pd.DataFrame(out)
    sort_cols = ["商品コード", "在庫切れ日"]
    if "倉庫コード" in res.columns:
        sort_cols = ["商品コード", "倉庫コード", "在庫切れ日"]
    res = res.sort_values(sort_cols).reset_index(drop=True)
    return res


def main() -> None:
    root = project_root()
    default_out = os.path.join(root, "データ")
    default_intermediate = os.path.join(root, "ツール", "中間出力")
    parser = argparse.ArgumentParser(description="在庫受払帳再現データから欠品期間を作成")
    parser.add_argument("--input-csv", default=default_input_csv(root), help="在庫受払帳再現CSVのパス")
    parser.add_argument("--jan-csv", default="", help="任意: JAN一覧CSV。指定時はこのJANに限定")
    parser.add_argument("--jan-prefix", default="452", help="対象JANプレフィックス")
    parser.add_argument("--output-dir", default=default_out, help="出力先ディレクトリ")
    parser.add_argument(
        "--write-intermediate",
        action="store_true",
        help="整理済み在庫データCSVを中間出力する場合に指定（既定では最終CSVのみ出力）",
    )
    parser.add_argument(
        "--intermediate-dir",
        default=default_intermediate,
        help="整理済み在庫データCSVの出力先（--write-intermediate 指定時のみ使用）",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    if args.write_intermediate:
        os.makedirs(args.intermediate_dir, exist_ok=True)

    print(f"Using ledger CSV: {args.input_csv}")
    if args.jan_csv:
        print(f"Using JAN CSV: {args.jan_csv}")

    raw = load_ledger_csv(args.input_csv)
    target_jans = parse_target_jans(args.jan_csv, args.jan_prefix) if args.jan_csv else set()
    data = cleanse_and_filter(raw, args.jan_prefix, target_jans)

    print(f"Rows(raw): {len(raw):,}")
    print(f"Rows(filtered): {len(data):,}")
    print(f"Unique JAN(filtered): {data['商品コード'].nunique():,}")

    stockouts = build_stockout_periods(data, include_open=True)

    stockouts_csv = os.path.join(args.output_dir, "在庫切れ期間一覧_452限定.csv")
    legacy_clean_csv = os.path.join(args.output_dir, "整理済み在庫データ_452限定.csv")
    legacy_returns_csv = os.path.join(args.output_dir, "返品データ一覧_452限定.csv")
    legacy_receipts_csv = os.path.join(args.output_dir, "入荷データ一覧_452限定.csv")

    stockouts.to_csv(stockouts_csv, encoding="utf-8-sig", index=False)

    if args.write_intermediate:
        clean_csv = os.path.join(args.intermediate_dir, "整理済み在庫データ_452限定.csv")
        export_cols = [c for c in data.columns if c not in ["入荷数_num", "出荷数_num", "在庫数_num", "_row_no"]]
        data[export_cols].to_csv(clean_csv, encoding="utf-8-sig", index=False)
    else:
        removed = 0
        for p in [legacy_clean_csv, legacy_returns_csv, legacy_receipts_csv]:
            path = Path(p)
            try:
                if path.exists():
                    path.unlink()
                    removed += 1
            except OSError:
                continue

    print("\nDone.")
    print(f"在庫切れ期間 rows: {len(stockouts):,}")
    print(f"最終出力: {stockouts_csv}")
    if args.write_intermediate:
        print(f"中間出力: {args.intermediate_dir}")
    else:
        print(f"既存中間ファイル削除数: {removed}")


if __name__ == "__main__":
    main()
