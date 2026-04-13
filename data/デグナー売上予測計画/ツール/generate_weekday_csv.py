from datetime import date, datetime, timedelta
import csv
from pathlib import Path
from urllib.request import urlopen


START_DATE = date(2008, 11, 1)
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
HOLIDAY_CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"


def load_holiday_map() -> dict[date, str]:
    with urlopen(HOLIDAY_CSV_URL, timeout=15) as resp:
        csv_text = resp.read().decode("cp932")

    holiday_map: dict[date, str] = {}
    reader = csv.reader(csv_text.splitlines())
    next(reader, None)  # ヘッダー行

    for row in reader:
        if len(row) < 2:
            continue
        d = datetime.strptime(row[0].strip(), "%Y/%m/%d").date()
        holiday_map[d] = row[1].strip()

    return holiday_map


def main() -> None:
    end_date = date.today()

    # ...\デグナー売上予測計画\ツール\generate_weekday_csv.py
    # -> ...\デグナー売上予測計画\データ\曜日一覧_*.csv
    base_dir = Path(__file__).resolve().parent.parent
    out_dir = base_dir / "データ"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / (
        f"曜日一覧_{START_DATE.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    )

    holiday_map = load_holiday_map()

    # Excelでの文字化けを避けるため cp932 で出力
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
