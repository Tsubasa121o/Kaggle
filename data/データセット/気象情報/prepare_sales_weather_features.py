from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd


WEATHER_NUMERIC_COLUMNS = [
    "temp_avg_c",
    "temp_max_c",
    "temp_min_c",
    "precip_mm",
    "sunshine_h",
    "snowfall_cm",
    "humidity_pct",
]

WEATHER_REGIONS = [
    "北海道",
    "東北",
    "関東",
    "中部",
    "近畿",
    "中国",
    "四国",
    "九州",
    "沖縄",
]

DEFAULT_REFERENCE_SALES_PATH = (
    r"C:\Users\t.ouchi\OneDrive\デスクトップ\Github\Kaggle\data\deg_pro\grouped_by_name\21SJ-10\4524486092411.csv"
)

REGION_ALIASES = {
    "北海道": "北海道",
    "東北": "東北",
    "関東": "関東",
    "中部": "中部",
    "近畿": "近畿",
    "関西": "近畿",
    "中国": "中国",
    "四国": "四国",
    "九州": "九州",
    "沖縄": "沖縄",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "売上データと天気データを1対1で比較できる形に結合します。"
            "地域列がない売上は、地域重みつきの日次天気指標を作って結合します。"
        ),
        epilog=(
            "例:\n"
            "  python prepare_sales_weather_features.py --sales-path sales.csv --date-column date --sales-column sales\n"
            "  python prepare_sales_weather_features.py --sales-path sales.csv --date-column col_5 --sales-column col_6 --date-format %Y%m%d\n"
            f"  python prepare_sales_weather_features.py --sales-path \"{DEFAULT_REFERENCE_SALES_PATH}\" "
            "--date-column col_5 --sales-column col_6 --date-format %Y%m%d "
            "--weights-path region_weights_example.csv --output-path sales_weather_4524486092411.csv"
        ),
    )
    parser.add_argument("--sales-path", help="売上ファイルのパス。csv / xlsx / parquet に対応。")
    parser.add_argument(
        "--weather-path",
        default="weather_region_daily_minimal.csv",
        help="地域別日次天気ファイルのパス。既定: weather_region_daily_minimal.csv",
    )
    parser.add_argument(
        "--output-path",
        default="sales_weather_merged.csv",
        help="出力CSVのパス。既定: sales_weather_merged.csv",
    )
    parser.add_argument(
        "--output-encoding",
        default="cp932",
        help="出力CSVの文字コード。既定: cp932",
    )
    parser.add_argument("--date-column", default="date", help="売上側の日付列名。既定: date")
    parser.add_argument("--sales-column", default="sales", help="売上金額列名。既定: sales")
    parser.add_argument(
        "--date-format",
        default=None,
        help="売上側の日付書式。例: %%Y%%m%%d。指定がなければ自動判定。",
    )
    parser.add_argument(
        "--region-column",
        default=None,
        help="売上側の地域列名。ある場合は日付+地域で直接結合。",
    )
    parser.add_argument(
        "--join-mode",
        choices=["auto", "weighted", "region"],
        default="auto",
        help="auto: 地域列があれば直接結合、なければ重みつき集計。既定: auto",
    )
    parser.add_argument(
        "--weights-json",
        default=None,
        help='地域重みをJSON文字列で指定。例: \'{"関東": 0.45, "近畿": 0.2, "中部": 0.15}\'',
    )
    parser.add_argument(
        "--weights-path",
        default=None,
        help="地域重みCSVのパス。列名は region, weight。",
    )
    parser.add_argument(
        "--season-start-month",
        type=int,
        default=3,
        help="メインシーズン開始月。既定: 3",
    )
    parser.add_argument(
        "--season-end-month",
        type=int,
        default=11,
        help="メインシーズン終了月。既定: 11",
    )
    parser.add_argument(
        "--rain-threshold-mm",
        type=float,
        default=1.0,
        help="雨判定に使う降水量しきい値(mm)。既定: 1.0",
    )
    parser.add_argument(
        "--heavy-rain-threshold-mm",
        type=float,
        default=10.0,
        help="強い雨判定に使う降水量しきい値(mm)。既定: 10.0",
    )
    parser.add_argument(
        "--snow-threshold-cm",
        type=float,
        default=1.0,
        help="雪判定に使う降雪量しきい値(cm)。既定: 1.0",
    )
    if len(sys.argv) == 1:
        parser.print_help()
        print(
            "\n`sales-path` が必要です。"
            "\nこの参考ファイルなら次をそのまま実行してください:\n"
            f"python prepare_sales_weather_features.py --sales-path \"{DEFAULT_REFERENCE_SALES_PATH}\" "
            "--date-column col_5 --sales-column col_6 --date-format %Y%m%d "
            "--weights-path region_weights_example.csv --output-path sales_weather_4524486092411.csv"
        )
        raise SystemExit(2)

    args = parser.parse_args()
    if not args.sales_path:
        parser.error("`--sales-path` が必要です。")
    return args


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "cp932"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("csv", b"", 0, 0, f"Failed to decode {path}")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file type: {path}")


def normalize_region_name(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return REGION_ALIASES.get(text, text)


def load_weather(path: Path) -> pd.DataFrame:
    weather = read_table(path).copy()
    required = {"date", "region", *WEATHER_NUMERIC_COLUMNS}
    missing = required.difference(weather.columns)
    if missing:
        raise ValueError(f"Weather file is missing columns: {sorted(missing)}")

    weather["date"] = pd.to_datetime(weather["date"], errors="coerce").dt.normalize()
    weather["region"] = weather["region"].map(normalize_region_name)
    weather = weather.dropna(subset=["date", "region"]).copy()
    return weather


def parse_date_series(series: pd.Series, date_format: str | None = None) -> pd.Series:
    values = series.copy()

    if date_format:
        return pd.to_datetime(values.astype(str).str.strip(), format=date_format, errors="coerce").dt.normalize()

    if pd.api.types.is_datetime64_any_dtype(values):
        return pd.to_datetime(values, errors="coerce").dt.normalize()

    normalized = values.astype(str).str.strip()
    digits8 = normalized.str.fullmatch(r"\d{8}")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    if digits8.any():
        parsed.loc[digits8] = pd.to_datetime(normalized.loc[digits8], format="%Y%m%d", errors="coerce")

    remaining = ~digits8
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(values.loc[remaining], errors="coerce")

    return parsed.dt.normalize()


def load_sales(path: Path, date_column: str, sales_column: str, date_format: str | None) -> pd.DataFrame:
    sales = read_table(path).copy()
    required = {date_column, sales_column}
    missing = required.difference(sales.columns)
    if missing:
        raise ValueError(f"Sales file is missing columns: {sorted(missing)}")

    sales[date_column] = parse_date_series(sales[date_column], date_format=date_format)
    sales[sales_column] = pd.to_numeric(sales[sales_column], errors="coerce")
    sales = sales.dropna(subset=[date_column]).copy()
    return sales


def read_weights_from_csv(path: Path) -> Dict[str, float]:
    weights_df = read_table(path)
    required = {"region", "weight"}
    missing = required.difference(weights_df.columns)
    if missing:
        raise ValueError(f"Weight file is missing columns: {sorted(missing)}")

    weights: Dict[str, float] = {}
    for _, row in weights_df.iterrows():
        region = normalize_region_name(row["region"])
        if region is None:
            continue
        weights[region] = float(row["weight"])
    return weights


def parse_weights(weights_json: str | None, weights_path: str | None) -> Dict[str, float]:
    if weights_json and weights_path:
        raise ValueError("Specify either --weights-json or --weights-path, not both.")

    if weights_json:
        raw = json.loads(weights_json)
        return {normalize_region_name(k): float(v) for k, v in raw.items() if normalize_region_name(k)}

    if weights_path:
        return read_weights_from_csv(Path(weights_path))

    return {region: 1.0 for region in WEATHER_REGIONS}


def normalize_weights(weights: Dict[str, float], available_regions: Iterable[str]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    region_set = set(available_regions)

    for region, weight in weights.items():
        if region not in region_set:
            continue
        if weight < 0:
            raise ValueError(f"Weight must be >= 0: {region}={weight}")
        normalized[region] = float(weight)

    if not normalized:
        raise ValueError("No valid region weights were matched to the weather dataset.")

    weight_sum = sum(normalized.values())
    if weight_sum <= 0:
        raise ValueError("Weight sum must be > 0.")

    return {region: value / weight_sum for region, value in normalized.items()}


def add_weather_features(
    weather: pd.DataFrame,
    season_start_month: int,
    season_end_month: int,
    rain_threshold_mm: float,
    heavy_rain_threshold_mm: float,
    snow_threshold_cm: float,
) -> pd.DataFrame:
    df = weather.copy()
    month = df["date"].dt.month
    df["wx_in_season"] = month.between(season_start_month, season_end_month).astype("int8")
    df["wx_rain_flag"] = (df["precip_mm"].fillna(0) >= rain_threshold_mm).astype("int8")
    df["wx_heavy_rain_flag"] = (df["precip_mm"].fillna(0) >= heavy_rain_threshold_mm).astype("int8")
    df["wx_snow_flag"] = (df["snowfall_cm"].fillna(0) >= snow_threshold_cm).astype("int8")
    df["wx_bad_weather_flag"] = ((df["wx_rain_flag"] == 1) | (df["wx_snow_flag"] == 1)).astype("int8")
    return df


def weighted_average(values: pd.Series, weights: pd.Series) -> float | None:
    mask = values.notna() & weights.notna()
    if not mask.any():
        return None
    return float(np.average(values[mask], weights=weights[mask]))


def make_weighted_weather_index(weather: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    df = weather.copy()
    df["weight"] = df["region"].map(weights)
    df = df.dropna(subset=["weight"]).copy()

    records = []
    for date, group in df.groupby("date", sort=True):
        record = {
            "date": date,
            "wx_region_weight_sum": float(group["weight"].sum()),
            "wx_region_count_used": int(group["region"].nunique()),
        }

        for column in WEATHER_NUMERIC_COLUMNS:
            record[f"wx_{column}"] = weighted_average(group[column], group["weight"])

        record["wx_rain_region_share"] = float(
            group.loc[group["wx_rain_flag"] == 1, "weight"].sum() / group["weight"].sum()
        )
        record["wx_heavy_rain_region_share"] = float(
            group.loc[group["wx_heavy_rain_flag"] == 1, "weight"].sum() / group["weight"].sum()
        )
        record["wx_snow_region_share"] = float(
            group.loc[group["wx_snow_flag"] == 1, "weight"].sum() / group["weight"].sum()
        )
        record["wx_bad_weather_region_share"] = float(
            group.loc[group["wx_bad_weather_flag"] == 1, "weight"].sum() / group["weight"].sum()
        )
        record["wx_in_season"] = int(round(weighted_average(group["wx_in_season"], group["weight"]) or 0))
        record["wx_rain_flag"] = int(record["wx_rain_region_share"] > 0)
        record["wx_heavy_rain_flag"] = int(record["wx_heavy_rain_region_share"] > 0)
        record["wx_snow_flag"] = int(record["wx_snow_region_share"] > 0)
        record["wx_bad_weather_flag"] = int(record["wx_bad_weather_region_share"] > 0)
        records.append(record)

    return pd.DataFrame.from_records(records)


def make_region_join_weather(weather: pd.DataFrame) -> pd.DataFrame:
    rename_map = {column: f"wx_{column}" for column in WEATHER_NUMERIC_COLUMNS}
    return weather.rename(columns=rename_map)


def merge_sales_and_weather(
    sales: pd.DataFrame,
    weather: pd.DataFrame,
    date_column: str,
    region_column: str | None,
    sales_column: str,
    join_mode: str,
) -> pd.DataFrame:
    if join_mode == "region":
        if not region_column or region_column not in sales.columns:
            raise ValueError("Region join requires a valid --region-column in the sales file.")
        sales = sales.copy()
        sales[region_column] = sales[region_column].map(normalize_region_name)
        merged = sales.merge(
            weather,
            left_on=[date_column, region_column],
            right_on=["date", "region"],
            how="left",
        )
        drop_columns = []
        if date_column != "date" and "date" in merged.columns:
            drop_columns.append("date")
        if region_column != "region" and "region" in merged.columns:
            drop_columns.append("region")
        if drop_columns:
            merged = merged.drop(columns=drop_columns)
        return merged

    merged = sales.merge(weather, left_on=date_column, right_on="date", how="left")
    if date_column != "date" and "date" in merged.columns:
        merged = merged.drop(columns=["date"])
    return merged


def add_analysis_columns(merged: pd.DataFrame, date_column: str, sales_column: str) -> pd.DataFrame:
    df = merged.copy()
    df["year"] = df[date_column].dt.year
    df["month"] = df[date_column].dt.month
    df["day"] = df[date_column].dt.day
    df["day_of_week"] = df[date_column].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype("int8")

    if sales_column in df.columns:
        df["sales_lag_1"] = df[sales_column].shift(1)
        df["sales_rolling_7"] = df[sales_column].rolling(7, min_periods=1).mean()

    return df


def print_summary(output_path: Path, merged: pd.DataFrame, weather_mode: str, weights: Dict[str, float]) -> None:
    print(f"rows: {len(merged)}")
    print(f"weather_mode: {weather_mode}")
    if "wx_temp_avg_c" in merged.columns:
        matched = int(merged["wx_temp_avg_c"].notna().sum())
        print(f"weather_matched_rows: {matched}")
    if weather_mode == "weighted":
        print("normalized_weights:")
        for region, weight in sorted(weights.items()):
            print(f"  {region}: {weight:.4f}")
    print(f"output: {output_path}")


def main() -> None:
    args = parse_args()

    sales_path = Path(args.sales_path)
    weather_path = Path(args.weather_path)
    output_path = Path(args.output_path)

    sales = load_sales(sales_path, args.date_column, args.sales_column, args.date_format)
    weather = load_weather(weather_path)
    weather = add_weather_features(
        weather,
        season_start_month=args.season_start_month,
        season_end_month=args.season_end_month,
        rain_threshold_mm=args.rain_threshold_mm,
        heavy_rain_threshold_mm=args.heavy_rain_threshold_mm,
        snow_threshold_cm=args.snow_threshold_cm,
    )

    if args.join_mode == "auto":
        weather_mode = "region" if args.region_column and args.region_column in sales.columns else "weighted"
    else:
        weather_mode = args.join_mode

    normalized_weights: Dict[str, float] = {}
    if weather_mode == "weighted":
        raw_weights = parse_weights(args.weights_json, args.weights_path)
        normalized_weights = normalize_weights(raw_weights, weather["region"].dropna().unique())
        weather_for_merge = make_weighted_weather_index(weather, normalized_weights)
    else:
        weather_for_merge = make_region_join_weather(weather)

    merged = merge_sales_and_weather(
        sales=sales,
        weather=weather_for_merge,
        date_column=args.date_column,
        region_column=args.region_column,
        sales_column=args.sales_column,
        join_mode=weather_mode,
    )

    merged = add_analysis_columns(merged, args.date_column, args.sales_column)
    merged = merged.sort_values(args.date_column).reset_index(drop=True)
    merged.to_csv(output_path, index=False, encoding=args.output_encoding)

    print_summary(output_path, merged, weather_mode, normalized_weights)


if __name__ == "__main__":
    main()
