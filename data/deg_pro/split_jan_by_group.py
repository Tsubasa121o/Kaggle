from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pandas as pd


INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*]')


def safe_name(value: str, fallback: str) -> str:
    cleaned = INVALID_PATH_CHARS.sub("_", str(value)).strip().rstrip(".")
    return cleaned or fallback


def load_mapping(
    mapping_csv: Path,
    jan_col: int,
    group_col: int,
    sep: str,
    encoding: str,
) -> dict[str, str]:
    mapping_df = pd.read_csv(
        mapping_csv,
        header=None,
        dtype=str,
        sep=sep,
        encoding=encoding,
        usecols=[jan_col, group_col],
        keep_default_na=False,
    )

    mapping_df.columns = ["jan", "group_name"]
    mapping_df["jan"] = mapping_df["jan"].str.strip()
    mapping_df["group_name"] = mapping_df["group_name"].str.strip()
    mapping_df = mapping_df[(mapping_df["jan"] != "") & (mapping_df["group_name"] != "")]

    duplicated = mapping_df[mapping_df.duplicated("jan", keep=False)]
    if not duplicated.empty:
        conflicts = duplicated.groupby("jan")["group_name"].nunique()
        conflicts = conflicts[conflicts > 1]
        if not conflicts.empty:
            sample = ", ".join(conflicts.index[:5].tolist())
            raise ValueError(
                "同じJANに複数グループが割り当てられています。"
                f" 例: {sample}"
            )

    mapping_df = mapping_df.drop_duplicates("jan", keep="last")
    return dict(zip(mapping_df["jan"], mapping_df["group_name"]))


def split_source(
    source_csv: Path,
    mapping: dict[str, str],
    output_dir: Path,
    source_jan_col: int,
    sep: str,
    source_encoding: str,
    output_encoding: str,
    chunksize: int,
    group_column_name: str,
    max_rows: int | None,
) -> tuple[int, int]:
    total_rows = 0
    matched_rows = 0

    chunk_iter = pd.read_csv(
        source_csv,
        header=None,
        dtype=str,
        sep=sep,
        encoding=source_encoding,
        chunksize=chunksize,
        keep_default_na=False,
    )

    for chunk_index, chunk in enumerate(chunk_iter, start=1):
        if max_rows is not None and total_rows >= max_rows:
            break

        if max_rows is not None and total_rows + len(chunk) > max_rows:
            chunk = chunk.iloc[: max_rows - total_rows].copy()

        total_rows += len(chunk)
        chunk.columns = [f"col_{i}" for i in range(chunk.shape[1])]

        jan_col_name = f"col_{source_jan_col}"
        chunk["jan_key"] = chunk[jan_col_name].str.strip()
        chunk[group_column_name] = chunk["jan_key"].map(mapping)
        chunk = chunk[chunk[group_column_name].notna() & (chunk[group_column_name] != "")]

        if chunk.empty:
            print(f"[chunk {chunk_index}] 対象行なし")
            continue

        matched_rows += len(chunk)
        pair_count = chunk[["jan_key", group_column_name]].drop_duplicates().shape[0]
        print(f"[chunk {chunk_index}] 対象行: {len(chunk):,} / JANペア: {pair_count:,}")

        for (group_name, jan), group_df in chunk.groupby([group_column_name, "jan_key"], sort=False):
            safe_group = safe_name(group_name, "unknown_group")
            safe_jan = safe_name(jan, "unknown_jan")
            group_path = output_dir / safe_group
            group_path.mkdir(parents=True, exist_ok=True)

            output_file = group_path / f"{safe_jan}.csv"
            write_header = not output_file.exists() or output_file.stat().st_size == 0

            to_write = group_df.drop(columns=["jan_key"])
            to_write.to_csv(
                output_file,
                mode="a",
                index=False,
                header=write_header,
                encoding=output_encoding,
            )

    return total_rows, matched_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "分析対象JAN.csvを使って、JANごとの日別売れ数リスト.csvを"
            " グループフォルダ/JAN.csv に分割します。"
        )
    )
    parser.add_argument(
        "--source-csv",
        default="JANごとの日別売れ数リスト.csv",
        help="元データCSVのパス",
    )
    parser.add_argument(
        "--mapping-csv",
        default="分析対象JAN.csv",
        help="1列目JAN、2列目グループ名のCSVパス",
    )
    parser.add_argument(
        "--output-dir",
        default="grouped_by_name",
        help="出力先フォルダ",
    )
    parser.add_argument(
        "--source-jan-col",
        type=int,
        default=0,
        help="元データ内のJAN列インデックス（0始まり）",
    )
    parser.add_argument(
        "--mapping-jan-col",
        type=int,
        default=0,
        help="マッピングCSV内のJAN列インデックス（0始まり）",
    )
    parser.add_argument(
        "--mapping-group-col",
        type=int,
        default=1,
        help="マッピングCSV内のグループ名列インデックス（0始まり）",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=200_000,
        help="分割読み込みサイズ",
    )
    parser.add_argument(
        "--source-sep",
        default=",",
        help="元データCSVの区切り文字",
    )
    parser.add_argument(
        "--mapping-sep",
        default=",",
        help="マッピングCSVの区切り文字",
    )
    parser.add_argument(
        "--source-encoding",
        default="utf-8-sig",
        help="元データCSVの文字コード",
    )
    parser.add_argument(
        "--mapping-encoding",
        default="utf-8-sig",
        help="マッピングCSVの文字コード",
    )
    parser.add_argument(
        "--output-encoding",
        default="utf-8-sig",
        help="出力CSVの文字コード",
    )
    parser.add_argument(
        "--group-column-name",
        default="group_name",
        help="出力CSVに追加するグループ列名",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="テスト用: 先頭から処理する最大行数",
    )
    parser.add_argument(
        "--reset-output",
        action="store_true",
        help="実行前に出力フォルダを削除して作り直す",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    source_csv = Path(args.source_csv)
    mapping_csv = Path(args.mapping_csv)
    output_dir = Path(args.output_dir)

    if not source_csv.exists():
        raise FileNotFoundError(f"元データCSVが見つかりません: {source_csv}")
    if not mapping_csv.exists():
        raise FileNotFoundError(f"マッピングCSVが見つかりません: {mapping_csv}")

    if args.reset_output and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mapping = load_mapping(
        mapping_csv=mapping_csv,
        jan_col=args.mapping_jan_col,
        group_col=args.mapping_group_col,
        sep=args.mapping_sep,
        encoding=args.mapping_encoding,
    )
    print(f"マッピングJAN数: {len(mapping):,}")

    total_rows, matched_rows = split_source(
        source_csv=source_csv,
        mapping=mapping,
        output_dir=output_dir,
        source_jan_col=args.source_jan_col,
        sep=args.source_sep,
        source_encoding=args.source_encoding,
        output_encoding=args.output_encoding,
        chunksize=args.chunksize,
        group_column_name=args.group_column_name,
        max_rows=args.max_rows,
    )

    print("----- 完了 -----")
    print(f"読込行数: {total_rows:,}")
    print(f"抽出行数: {matched_rows:,}")
    print(f"出力先: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
