from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


# Keep only analysis-friendly weather metrics (drop quality/homogeneity columns).
VALUE_COLUMNS = {
    "date": 0,
    "temp_avg_c": 1,
    "temp_max_c": 4,
    "temp_min_c": 7,
    "precip_mm": 10,
    "sunshine_h": 14,
    "snowfall_cm": 18,
    "humidity_pct": 22,
}

# 8-region split (Mie is grouped into Chubu for weather-sales comparison).
STATION_TO_REGION: Dict[str, str] = {
    # Hokkaido
    "稚内": "北海道",
    "網走": "北海道",
    "小樽": "北海道",
    "札幌": "北海道",
    "函館": "北海道",
    "帯広": "北海道",
    "釧路": "北海道",
    "根室": "北海道",
    # Tohoku
    "青森": "東北",
    "八戸": "東北",
    "盛岡": "東北",
    "秋田": "東北",
    "仙台": "東北",
    "山形": "東北",
    "新庄": "東北",
    "福島": "東北",
    "白河": "東北",
    "若松": "東北",  # Assumed to be Aizu-Wakamatsu.
    # Kanto
    "水戸": "関東",
    "宇都宮": "関東",
    "前橋": "関東",
    "熊谷": "関東",
    "秩父": "関東",
    "東京": "関東",
    "横浜": "関東",
    "千葉": "関東",
    "銚子": "関東",
    # Chubu
    "甲府": "中部",
    "長野": "中部",
    "松本": "中部",
    "飯田": "中部",
    "軽井沢": "中部",
    "新潟": "中部",
    "高田": "中部",  # Assumed to be Joetsu-Takada (Niigata).
    "富山": "中部",
    "金沢": "中部",
    "福井": "中部",
    "敦賀": "中部",
    "静岡": "中部",
    "浜松": "中部",
    "名古屋": "中部",
    "四日市": "中部",
    "尾鷲": "中部",
    # Kinki
    "彦根": "近畿",
    "大津": "近畿",
    "京都": "近畿",
    "大阪": "近畿",
    "神戸": "近畿",
    "奈良": "近畿",
    "和歌山": "近畿",
    "姫路": "近畿",
    "舞鶴": "近畿",
    # Chugoku
    "鳥取": "中国",
    "松江": "中国",
    "浜田": "中国",
    "岡山": "中国",
    "広島": "中国",
    "福山": "中国",
    "山口": "中国",
    # Shikoku
    "徳島": "四国",
    "高松": "四国",
    "松山": "四国",
    "高知": "四国",
    # Kyushu/Okinawa
    "福岡": "九州沖縄",
    "佐賀": "九州沖縄",
    "佐世保": "九州沖縄",
    "熊本": "九州沖縄",
    "大分": "九州沖縄",
    "宮崎": "九州沖縄",
    "鹿児島": "九州沖縄",
    "那覇": "九州沖縄",
}

AMBIGUOUS_STATIONS = {
    "若松": "地名が複数あり得るため、会津若松(福島)として仮置き。",
    "高田": "地名が複数あり得るため、上越市高田(新潟)として仮置き。",
}


@dataclass
class Issue:
    issue_type: str
    file_name: str
    station_name: str
    detail: str


def to_float(value: str) -> float | None:
    v = (value or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def detect_weather_dir() -> Path:
    data_root = Path("Kaggle/data")
    candidates = {}
    for p in data_root.rglob("*_2015-25.csv"):
        candidates[p.parent] = candidates.get(p.parent, 0) + 1
    if not candidates:
        raise FileNotFoundError("No *_2015-25.csv files found under Kaggle/data")
    return sorted(candidates.items(), key=lambda x: x[1], reverse=True)[0][0]


def read_station_file(path: Path, issues: List[Issue]) -> pd.DataFrame:
    with path.open("r", encoding="cp932", newline="") as f:
        rows = list(csv.reader(f))

    if len(rows) < 7:
        issues.append(
            Issue(
                issue_type="invalid_format",
                file_name=path.name,
                station_name="",
                detail="Required header/data rows are missing.",
            )
        )
        return pd.DataFrame()

    station = (rows[2][1] if len(rows[2]) > 1 else "").strip()
    file_stem_station = path.stem.replace("_2015-25", "")
    if file_stem_station != station:
        issues.append(
            Issue(
                issue_type="filename_station_mismatch",
                file_name=path.name,
                station_name=station,
                detail=f"Filename '{file_stem_station}' differs from station label '{station}'.",
            )
        )

    records = []
    for row in rows[6:]:
        if len(row) < 23:
            continue
        date_raw = row[VALUE_COLUMNS["date"]].strip()
        if not date_raw:
            continue
        dt = pd.to_datetime(date_raw, format="%Y/%m/%d", errors="coerce")
        if pd.isna(dt):
            continue

        rec = {"date": dt.date(), "station": station, "source_file": path.name}
        for key, idx in VALUE_COLUMNS.items():
            if key == "date":
                continue
            rec[key] = to_float(row[idx])
        records.append(rec)

    return pd.DataFrame.from_records(records)


def main() -> None:
    weather_dir = detect_weather_dir()
    files = sorted(weather_dir.glob("*_2015-25.csv"))
    issues: List[Issue] = []
    frames: List[pd.DataFrame] = []

    for path in files:
        df = read_station_file(path, issues)
        if not df.empty:
            frames.append(df)

    if not frames:
        raise RuntimeError("No weather records parsed.")

    station_daily = pd.concat(frames, ignore_index=True)

    station_daily["region"] = station_daily["station"].map(STATION_TO_REGION)
    unknown = station_daily[station_daily["region"].isna()]["station"].dropna().unique().tolist()
    for st in unknown:
        issues.append(
            Issue(
                issue_type="unmapped_station",
                file_name="",
                station_name=st,
                detail="No region mapping found. Please assign this station manually.",
            )
        )

    for st, note in AMBIGUOUS_STATIONS.items():
        if (station_daily["station"] == st).any():
            issues.append(
                Issue(
                    issue_type="ambiguous_place_name",
                    file_name="",
                    station_name=st,
                    detail=note,
                )
            )

    station_daily = station_daily.dropna(subset=["region"]).copy()
    station_daily = station_daily[
        [
            "date",
            "region",
            "station",
            "temp_avg_c",
            "temp_max_c",
            "temp_min_c",
            "precip_mm",
            "sunshine_h",
            "snowfall_cm",
            "humidity_pct",
        ]
    ].sort_values(["date", "region", "station"])

    region_daily = (
        station_daily.groupby(["date", "region"], as_index=False)
        .agg(
            temp_avg_c=("temp_avg_c", "mean"),
            temp_max_c=("temp_max_c", "mean"),
            temp_min_c=("temp_min_c", "mean"),
            precip_mm=("precip_mm", "mean"),
            sunshine_h=("sunshine_h", "mean"),
            snowfall_cm=("snowfall_cm", "mean"),
            humidity_pct=("humidity_pct", "mean"),
            station_count=("station", "nunique"),
        )
        .sort_values(["date", "region"])
    )

    station_map = (
        station_daily[["station", "region"]]
        .drop_duplicates()
        .sort_values(["region", "station"])
        .reset_index(drop=True)
    )

    issues_df = pd.DataFrame(
        [issue.__dict__ for issue in issues],
        columns=["issue_type", "file_name", "station_name", "detail"],
    )
    if not issues_df.empty:
        issues_df = issues_df.sort_values(
            ["issue_type", "station_name", "file_name"], na_position="last"
        )

    station_out = weather_dir / "weather_station_daily_minimal.csv"
    region_out = weather_dir / "weather_region_daily_minimal.csv"
    station_map_out = weather_dir / "weather_station_region_map.csv"
    issues_out = weather_dir / "weather_place_name_issues.csv"

    station_daily.to_csv(station_out, index=False, encoding="utf-8-sig")
    region_daily.to_csv(region_out, index=False, encoding="utf-8-sig")
    station_map.to_csv(station_map_out, index=False, encoding="utf-8-sig")
    issues_df.to_csv(issues_out, index=False, encoding="utf-8-sig")

    print(f"weather_dir: {weather_dir}")
    print(f"station files: {len(files)}")
    print(f"station records: {len(station_daily)}")
    print(f"region records: {len(region_daily)}")
    print(f"issues: {len(issues_df)}")
    print(f"output: {region_out}")


if __name__ == "__main__":
    main()
