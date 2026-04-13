from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "データ"
QUERY_PATH = DATA_DIR / "工場コードクエリ.csv"
MANUAL_PATH = DATA_DIR / "工場リードタイム手入力.csv"
OUTPUT_PATH = DATA_DIR / "工場リードタイムマスタ.csv"

REQUIRED_QUERY_COLUMNS = ("code", "resolved_name")
REQUIRED_MANUAL_COLUMNS = ("code", "lead_time_days")
READ_ENCODINGS = ("utf-8-sig", "cp932", "utf-8")
WRITE_ENCODING = "cp932"


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    last_error: Exception | None = None

    for encoding in READ_ENCODINGS:
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                rows = [{k: (v or "").strip() for k, v in row.items()} for row in reader]
                return rows, reader.fieldnames or []
        except UnicodeDecodeError as exc:
            last_error = exc

    raise RuntimeError(f"CSVを読めませんでした: {path}") from last_error


def write_csv_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=WRITE_ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_columns(path: Path, actual_columns: list[str], required_columns: tuple[str, ...]) -> None:
    missing_columns = [column for column in required_columns if column not in actual_columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"{path.name} に必要な列がありません: {missing}")


def normalize_code(value: str) -> str:
    return value.strip()


def normalize_lookup_key(value: str) -> str:
    return normalize_code(value).upper()


def parse_lead_time_days(raw_value: str, code: str) -> str | None:
    value = raw_value.strip()
    if not value:
        return None

    try:
        decimal_value = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"lead_time_days が数値ではありません: code={code}, value={raw_value}") from exc

    if decimal_value != decimal_value.to_integral_value():
        raise ValueError(f"lead_time_days は整数で入力してください: code={code}, value={raw_value}")

    if decimal_value < 0:
        raise ValueError(f"lead_time_days は0以上で入力してください: code={code}, value={raw_value}")

    return str(int(decimal_value))


def build_master_rows() -> tuple[list[dict[str, str]], list[str]]:
    query_rows, query_columns = read_csv_rows(QUERY_PATH)
    manual_rows, manual_columns = read_csv_rows(MANUAL_PATH)

    validate_columns(QUERY_PATH, query_columns, REQUIRED_QUERY_COLUMNS)
    validate_columns(MANUAL_PATH, manual_columns, REQUIRED_MANUAL_COLUMNS)

    query_map: dict[str, dict[str, str]] = {}
    for row in query_rows:
        code = normalize_code(row["code"])
        if not code:
            continue
        query_map[normalize_lookup_key(code)] = {
            "code": code,
            "resolved_name": row["resolved_name"].strip(),
        }

    extra_columns = [column for column in manual_columns if column not in ("code", "resolved_name")]
    output_columns = ["code", "resolved_name", *extra_columns]

    merged_rows: list[dict[str, str]] = []
    seen_codes: set[str] = set()
    unknown_codes: list[str] = []

    for row in manual_rows:
        code = normalize_code(row["code"])
        if not code:
            continue

        lead_time_days = parse_lead_time_days(row.get("lead_time_days", ""), code)
        if lead_time_days is None:
            continue

        lookup_key = normalize_lookup_key(code)

        if lookup_key in seen_codes:
            raise ValueError(f"工場コードが重複しています: {code}")
        seen_codes.add(lookup_key)

        query_row = query_map.get(lookup_key)
        if query_row is None:
            unknown_codes.append(code)
            continue

        merged_row = {
            "code": query_row["code"],
            "resolved_name": query_row["resolved_name"],
        }

        for column in extra_columns:
            if column == "lead_time_days":
                merged_row[column] = lead_time_days
            else:
                merged_row[column] = row.get(column, "").strip()

        merged_rows.append(merged_row)

    if unknown_codes:
        unknown_list = ", ".join(sorted(unknown_codes))
        raise ValueError(f"工場コードクエリに存在しない code です: {unknown_list}")

    merged_rows.sort(key=lambda row: row["code"])
    return merged_rows, output_columns


def main() -> None:
    if not QUERY_PATH.exists():
        raise FileNotFoundError(f"工場コードクエリが見つかりません: {QUERY_PATH}")

    if not MANUAL_PATH.exists():
        write_csv_rows(MANUAL_PATH, [], ["code", "lead_time_days", "note", "updated_at"])
        print(f"手入力テンプレートを作成しました: {MANUAL_PATH}")

    master_rows, output_columns = build_master_rows()
    write_csv_rows(OUTPUT_PATH, master_rows, output_columns)

    print(f"工場コード件数: {len(read_csv_rows(QUERY_PATH)[0])}")
    print(f"手入力件数(lead_timeあり): {len(master_rows)}")
    print(f"出力先: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
