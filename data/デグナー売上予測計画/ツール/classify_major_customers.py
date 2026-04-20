from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_KEYWORDS = ("2りんかん", "ﾅｯﾌﾟｽ", "ﾗｲｺﾗﾝﾄﾞ")


def open_csv_with_fallback(path: Path):
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp932", "shift_jis"):
        try:
            f = path.open("r", encoding=encoding, newline="")
            f.readline()
            f.seek(0)
            return f, encoding
        except Exception as exc:  # pragma: no cover
            last_error = exc
            try:
                f.close()
            except Exception:
                pass
    raise RuntimeError(f"failed to open {path}: {last_error}")


def classify_rows(
    rows: list[dict[str, str]],
    keywords: tuple[str, ...],
    name_col: str = "customer_name",
) -> tuple[list[dict[str, str]], int, int]:
    major_count = 0
    other_count = 0

    for row in rows:
        customer_name = (row.get(name_col) or "").strip()
        is_major = 1 if any(k in customer_name for k in keywords) else 0
        row["major_customer_flag"] = str(is_major)
        row["customer_segment"] = "大口顧客" if is_major == 1 else "その他"

        if is_major == 1:
            major_count += 1
        else:
            other_count += 1

    return rows, major_count, other_count


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    default_input = base_dir / "データ" / "得意先区分クエリ.csv"
    default_output = base_dir / "データ" / "得意先区分クエリ_大口分類.csv"

    parser = argparse.ArgumentParser(
        description=(
            "Add major-customer flag from customer_name by keyword match. "
            "Default keywords: 2りんかん, ﾅｯﾌﾟｽ, ﾗｲｺﾗﾝﾄﾞ"
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"input CSV path (default: {default_input})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"output CSV path (default: {default_output})",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=list(DEFAULT_KEYWORDS),
        help="keyword list for major customer classification",
    )
    args = parser.parse_args()

    input_path: Path = args.input
    output_path: Path = args.output
    keywords = tuple(args.keywords)

    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")

    f, input_encoding = open_csv_with_fallback(input_path)
    with f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "customer_name" not in fieldnames:
            raise ValueError("required column not found: customer_name")
        rows = list(reader)

    rows, major_count, other_count = classify_rows(rows, keywords)

    if "major_customer_flag" not in fieldnames:
        fieldnames.append("major_customer_flag")
    if "customer_segment" not in fieldnames:
        fieldnames.append("customer_segment")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"input: {input_path} (encoding={input_encoding})")
    print(f"output: {output_path}")
    print(f"rows: {len(rows)}")
    print(f"major_customer_flag=1: {major_count}")
    print(f"major_customer_flag=0: {other_count}")
    print(f"keywords: {', '.join(keywords)}")


if __name__ == "__main__":
    main()
