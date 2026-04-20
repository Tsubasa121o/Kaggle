from __future__ import annotations

from datetime import date, datetime, timedelta
import csv
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


START_DATE = date(2008, 11, 1)
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
HOLIDAY_CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"


def load_holiday_map_online() -> dict[date, str]:
    with urlopen(HOLIDAY_CSV_URL, timeout=20) as resp:
        csv_text = resp.read().decode("cp932")

    holiday_map: dict[date, str] = {}
    reader = csv.reader(csv_text.splitlines())
    next(reader, None)
    for row in reader:
        if len(row) < 2:
            continue
        try:
            d = datetime.strptime(row[0].strip(), "%Y/%m/%d").date()
        except ValueError:
            continue
        holiday_map[d] = row[1].strip()
    return holiday_map


def load_holiday_map_from_cached_weekday_csv(out_dir: Path) -> dict[date, str]:
    candidates = sorted(out_dir.glob("曜日一覧_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {}

    path = candidates[0]
    holiday_map: dict[date, str] = {}
    with path.open("r", encoding="cp932", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row is None:
                continue
            date_str = (row.get("日付", "") or "").strip()
            holiday_name = (row.get("祝日名", "") or "").strip()
            if not date_str or not holiday_name:
                continue
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            holiday_map[d] = holiday_name
    return holiday_map


def load_holiday_map_with_fallback(out_dir: Path) -> tuple[dict[date, str], str]:
    try:
        return load_holiday_map_online(), "online"
    except URLError:
        cached = load_holiday_map_from_cached_weekday_csv(out_dir)
        if cached:
            return cached, "cached"
        return {}, "none"


def main() -> None:
    end_date = date.today()

    base_dir = Path(__file__).resolve().parent.parent
    out_dir = base_dir / "データ"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"曜日一覧_{START_DATE.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"

    holiday_map, source = load_holiday_map_with_fallback(out_dir)
    if source == "online":
        print("祝日データ取得: online")
    elif source == "cached":
        print("祝日データ取得: cached (ネットワーク失敗のため既存CSVを使用)")
    else:
        print("祝日データ取得: none (祝日名なしで出力)")

    with out_path.open("w", encoding="cp932", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["日付", "曜日", "曜日番号", "祝日名"])

        current = START_DATE
        while current <= end_date:
            weekday_no = current.weekday()  # 0=月 ... 6=日
            writer.writerow(
                [
                    current.strftime("%Y-%m-%d"),
                    WEEKDAY_JP[weekday_no],
                    weekday_no + 1,
                    holiday_map.get(current, ""),
                ]
            )
            current += timedelta(days=1)

    print(f"出力完了: {out_path}")


if __name__ == "__main__":
    main()
