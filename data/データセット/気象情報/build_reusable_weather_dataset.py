from __future__ import annotations

import argparse
import csv
import json
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

REGION_NAME_TO_CODE = {
    "北海道": "hokkaido",
    "東北": "tohoku",
    "関東": "kanto",
    "中部": "chubu",
    "近畿": "kinki",
    "中国": "chugoku",
    "四国": "shikoku",
    "九州": "kyushu",
    "沖縄": "okinawa",
}

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

DEFAULT_WEIGHTS = {
    "北海道": 0.05,
    "東北": 0.08,
    "関東": 0.42,
    "中部": 0.16,
    "近畿": 0.15,
    "中国": 0.05,
    "四国": 0.03,
    "九州": 0.05,
    "沖縄": 0.01,
}

HEADER_LABELS = {
    "temp_avg_c": "平均気温(℃)",
    "temp_max_c": "最高気温(℃)",
    "temp_min_c": "最低気温(℃)",
    "precip_mm": "降水量の合計(mm)",
    "sunshine_h": "日照時間(時間)",
    "snowfall_cm": "降雪量合計(cm)",
    "humidity_pct": "平均湿度(％)",
}

STATION_TO_REGION = {
    "函館": "北海道",
    "小樽": "北海道",
    "帯広": "北海道",
    "札幌": "北海道",
    "根室": "北海道",
    "稚内": "北海道",
    "網走": "北海道",
    "釧路": "北海道",
    "仙台": "東北",
    "山形": "東北",
    "新庄": "東北",
    "白河": "東北",
    "盛岡": "東北",
    "福島": "東北",
    "秋田": "東北",
    "青森": "東北",
    "前橋": "関東",
    "千葉": "関東",
    "宇都宮": "関東",
    "東京": "関東",
    "横浜": "関東",
    "水戸": "関東",
    "熊谷": "関東",
    "秩父": "関東",
    "銚子": "関東",
    "名古屋": "中部",
    "四日市": "中部",
    "富山": "中部",
    "尾鷲": "中部",
    "敦賀": "中部",
    "新潟": "中部",
    "松本": "中部",
    "甲府": "中部",
    "福井": "中部",
    "軽井沢": "中部",
    "金沢": "中部",
    "長野": "中部",
    "静岡": "中部",
    "飯田": "中部",
    "京都": "近畿",
    "和歌山": "近畿",
    "大津": "近畿",
    "大阪": "近畿",
    "奈良": "近畿",
    "姫路": "近畿",
    "彦根": "近畿",
    "神戸": "近畿",
    "舞鶴": "近畿",
    "山口": "中国",
    "岡山": "中国",
    "広島": "中国",
    "松江": "中国",
    "浜田": "中国",
    "福山": "中国",
    "鳥取": "中国",
    "徳島": "四国",
    "松山": "四国",
    "高松": "四国",
    "高知": "四国",
    "佐世保": "九州",
    "佐賀": "九州",
    "大分": "九州",
    "宮崎": "九州",
    "熊本": "九州",
    "福岡": "九州",
    "鹿児島": "九州",
    "那覇": "沖縄",
}


def resolve_input_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="天気データだけを、日付1行の分析用CSVに整形します。",
        epilog=(
            "例:\n"
            "  python build_reusable_weather_dataset.py\n"
            "  python build_reusable_weather_dataset.py --weights-path region_weights_example.csv\n"
            "  python build_reusable_weather_dataset.py --weights-json '{\"関東\": 0.5, \"近畿\": 0.2, \"中部\": 0.15}'"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--weather-path",
        default="weather_region_daily_minimal.csv",
        help="地域別日次天気CSV。既定: weather_region_daily_minimal.csv",
    )
    parser.add_argument(
        "--output-path",
        default="weather_daily_feature_matrix.csv",
        help="出力CSV。既定: weather_daily_feature_matrix.csv",
    )
    parser.add_argument(
        "--output-encoding",
        default="cp932",
        help="出力CSVの文字コード。既定: cp932",
    )
    parser.add_argument(
        "--weights-path",
        default=None,
        help="地域重みCSV。列名は region, weight。",
    )
    parser.add_argument(
        "--weights-json",
        default=None,
        help="地域重みをJSON文字列で指定。",
    )
    parser.add_argument(
        "--season-start-month",
        type=int,
        default=3,
        help="シーズン開始月。既定: 3",
    )
    parser.add_argument(
        "--season-end-month",
        type=int,
        default=11,
        help="シーズン終了月。既定: 11",
    )
    parser.add_argument(
        "--rain-threshold-mm",
        type=float,
        default=1.0,
        help="雨判定しきい値(mm)。既定: 1.0",
    )
    parser.add_argument(
        "--heavy-rain-threshold-mm",
        type=float,
        default=10.0,
        help="強い雨判定しきい値(mm)。既定: 10.0",
    )
    parser.add_argument(
        "--snow-threshold-cm",
        type=float,
        default=1.0,
        help="雪判定しきい値(cm)。既定: 1.0",
    )
    return parser.parse_args()


def read_table(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 0, f"Failed to decode {path}")


def to_float(value: object) -> float | None:
    text = str(value).strip() if value is not None else ""
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def detect_station_files(base_dir: Path) -> list[Path]:
    return sorted(base_dir.glob("*_2015-25.csv"))


def read_station_file(path: Path) -> pd.DataFrame:
    station = path.stem.replace("_2015-25", "")
    region = STATION_TO_REGION.get(station)
    if region is None:
        return pd.DataFrame()

    with path.open("r", encoding="cp932", newline="") as f:
        rows = list(csv.reader(f))

    if len(rows) < 7:
        return pd.DataFrame()

    metric_row = rows[3]
    subheader_row = rows[5]

    value_indexes: dict[str, int] = {"date": 0}
    for key, label in HEADER_LABELS.items():
        index = None
        for i, metric in enumerate(metric_row):
            subheader = subheader_row[i] if i < len(subheader_row) else ""
            if metric == label and subheader == "":
                index = i
                break
        if index is None:
            for i, metric in enumerate(metric_row):
                if metric == label:
                    index = i
                    break
        value_indexes[key] = index

    records = []
    required_indexes = [idx for idx in value_indexes.values() if idx is not None]
    max_required_index = max(required_indexes) if required_indexes else 0
    for row in rows[6:]:
        if len(row) <= max_required_index:
            continue
        date_raw = str(row[value_indexes["date"]]).strip()
        if not date_raw:
            continue
        date = pd.to_datetime(date_raw, format="%Y/%m/%d", errors="coerce")
        if pd.isna(date):
            continue

        record = {"date": date.normalize(), "region": region, "station": station}
        for column, index in value_indexes.items():
            if column == "date":
                continue
            record[column] = to_float(row[index]) if index is not None and index < len(row) else None
        records.append(record)

    return pd.DataFrame.from_records(records)


def load_weather_long(args: argparse.Namespace) -> pd.DataFrame:
    weather_path = resolve_input_path(args.weather_path)
    if weather_path.exists():
        weather = read_table(weather_path)
        required = {"date", "region", *WEATHER_NUMERIC_COLUMNS}
        missing = required.difference(weather.columns)
        if missing:
            raise ValueError(f"Weather file is missing columns: {sorted(missing)}")
        return weather

    base_dir = Path(__file__).resolve().parent
    station_files = detect_station_files(base_dir)
    if not station_files:
        raise FileNotFoundError("No weather source files were found.")

    records = []
    for path in station_files:
        frame = read_station_file(path)
        if not frame.empty:
            records.extend(frame.to_dict("records"))

    if not records:
        raise ValueError("No station weather data could be parsed.")

    station_daily = pd.DataFrame.from_records(records)
    weather = (
        station_daily.groupby(["date", "region"], as_index=False)
        .agg(
            temp_avg_c=("temp_avg_c", "mean"),
            temp_max_c=("temp_max_c", "mean"),
            temp_min_c=("temp_min_c", "mean"),
            precip_mm=("precip_mm", "mean"),
            sunshine_h=("sunshine_h", "mean"),
            snowfall_cm=("snowfall_cm", "mean"),
            humidity_pct=("humidity_pct", "mean"),
        )
        .sort_values(["date", "region"])
        .reset_index(drop=True)
    )
    return weather


def normalize_region_name(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return REGION_ALIASES.get(text, text)


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
        return read_weights_from_csv(resolve_input_path(weights_path))
    return DEFAULT_WEIGHTS.copy()


def normalize_weights(weights: Dict[str, float], available_regions: Iterable[str]) -> Dict[str, float]:
    region_set = set(available_regions)
    normalized: Dict[str, float] = {}
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


def add_weather_flags(
    weather: pd.DataFrame,
    season_start_month: int,
    season_end_month: int,
    rain_threshold_mm: float,
    heavy_rain_threshold_mm: float,
    snow_threshold_cm: float,
) -> pd.DataFrame:
    df = weather.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["region"] = df["region"].map(normalize_region_name)
    df = df.dropna(subset=["date", "region"]).copy()

    month = df["date"].dt.month
    df["in_season"] = month.between(season_start_month, season_end_month).astype("int8")
    df["rain_flag"] = (df["precip_mm"].fillna(0) >= rain_threshold_mm).astype("int8")
    df["heavy_rain_flag"] = (df["precip_mm"].fillna(0) >= heavy_rain_threshold_mm).astype("int8")
    df["snow_flag"] = (df["snowfall_cm"].fillna(0) >= snow_threshold_cm).astype("int8")
    df["bad_weather_flag"] = ((df["rain_flag"] == 1) | (df["snow_flag"] == 1)).astype("int8")
    df["region_code"] = df["region"].map(REGION_NAME_TO_CODE)
    return df


def weighted_average(values: pd.Series, weights: pd.Series) -> float | None:
    mask = values.notna() & weights.notna()
    if not mask.any():
        return None
    return float(np.average(values[mask], weights=weights[mask]))


def build_weighted_daily_features(weather: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    df = weather.copy()
    df["weight"] = df["region"].map(weights)
    df = df.dropna(subset=["weight"]).copy()

    records = []
    for date, group in df.groupby("date", sort=True):
        row = {
            "date": date,
            "wx_region_weight_sum": float(group["weight"].sum()),
            "wx_region_count_used": int(group["region"].nunique()),
        }

        for column in WEATHER_NUMERIC_COLUMNS:
            row[f"wx_{column}"] = weighted_average(group[column], group["weight"])

        row["wx_rain_region_share"] = float(group.loc[group["rain_flag"] == 1, "weight"].sum() / group["weight"].sum())
        row["wx_heavy_rain_region_share"] = float(
            group.loc[group["heavy_rain_flag"] == 1, "weight"].sum() / group["weight"].sum()
        )
        row["wx_snow_region_share"] = float(group.loc[group["snow_flag"] == 1, "weight"].sum() / group["weight"].sum())
        row["wx_bad_weather_region_share"] = float(
            group.loc[group["bad_weather_flag"] == 1, "weight"].sum() / group["weight"].sum()
        )
        row["wx_rain_flag"] = int(row["wx_rain_region_share"] > 0)
        row["wx_heavy_rain_flag"] = int(row["wx_heavy_rain_region_share"] > 0)
        row["wx_snow_flag"] = int(row["wx_snow_region_share"] > 0)
        row["wx_bad_weather_flag"] = int(row["wx_bad_weather_region_share"] > 0)
        row["wx_in_season"] = int(round(weighted_average(group["in_season"], group["weight"]) or 0))
        records.append(row)

    return pd.DataFrame.from_records(records)


def build_region_wide_features(weather: pd.DataFrame) -> pd.DataFrame:
    value_columns = WEATHER_NUMERIC_COLUMNS + [
        "rain_flag",
        "heavy_rain_flag",
        "snow_flag",
        "bad_weather_flag",
        "in_season",
    ]

    wide_frames = []
    for region_code, group in weather.groupby("region_code", sort=True):
        if not region_code:
            continue
        region_df = group[["date", *value_columns]].copy()
        rename_map = {column: f"rg_{region_code}_{column}" for column in value_columns}
        region_df = region_df.rename(columns=rename_map)
        wide_frames.append(region_df.set_index("date"))

    if not wide_frames:
        raise ValueError("No region data was available to pivot.")

    return pd.concat(wide_frames, axis=1).reset_index()


def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["year"] = out["date"].dt.year
    out["month"] = out["date"].dt.month
    out["day"] = out["date"].dt.day
    out["day_of_week"] = out["date"].dt.dayofweek
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype("int8")
    return out


def build_dataset(args: argparse.Namespace) -> tuple[pd.DataFrame, Dict[str, float]]:
    weather = load_weather_long(args)
    weather = add_weather_flags(
        weather=weather,
        season_start_month=args.season_start_month,
        season_end_month=args.season_end_month,
        rain_threshold_mm=args.rain_threshold_mm,
        heavy_rain_threshold_mm=args.heavy_rain_threshold_mm,
        snow_threshold_cm=args.snow_threshold_cm,
    )

    normalized_weights = normalize_weights(
        parse_weights(args.weights_json, args.weights_path),
        weather["region"].dropna().unique(),
    )

    weighted_daily = build_weighted_daily_features(weather, normalized_weights)
    region_wide = build_region_wide_features(weather)
    merged = weighted_daily.merge(region_wide, on="date", how="outer").sort_values("date").reset_index(drop=True)
    merged = add_calendar_columns(merged)
    return merged, normalized_weights


def main() -> None:
    args = parse_args()
    dataset, weights = build_dataset(args)
    output_path = Path(args.output_path)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / output_path
    dataset.to_csv(output_path, index=False, encoding=args.output_encoding)

    print(f"rows: {len(dataset)}")
    print(f"date_min: {dataset['date'].min().date()}")
    print(f"date_max: {dataset['date'].max().date()}")
    print("normalized_weights:")
    for region, weight in sorted(weights.items()):
        print(f"  {region}: {weight:.4f}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
