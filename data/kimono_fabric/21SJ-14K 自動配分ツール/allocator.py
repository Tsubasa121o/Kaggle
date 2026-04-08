import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "jan_code": ["jan_code", "JAN", "JANコード", "jan", "商品コード"],
    "item_name": ["item_name", "商品名", "品名"],
    "sales_qty": ["sales_qty", "売上数量", "販売数量", "出荷数量"],
    "stockout_days": ["stockout_days", "在庫切れ日数", "在庫ゼロ日数"],
    "current_stock": ["current_stock", "現在庫", "在庫数"],
    "return_qty": ["return_qty", "返品数量", "返品数"],
    "return_rate": ["return_rate", "返品率"],
    "min_allocate": ["min_allocate", "最低配分数", "最小配分数"],
    "max_allocate": ["max_allocate", "最大配分数"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="21SJ-14K向けの重み調整可能な自動配分ツール"
    )
    parser.add_argument(
        "--input",
        default="data/input/21SJ14K_allocation_input.csv",
        help="配分元データCSV",
    )
    parser.add_argument(
        "--weights",
        default="config/weights.json",
        help="重み設定JSON",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=200,
        help="配分総数",
    )
    parser.add_argument(
        "--output",
        default="",
        help="出力CSVパス。未指定なら data/output に日時付きで保存",
    )
    return parser.parse_args()


def load_weights(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    if "feature_weights" not in cfg or not isinstance(cfg["feature_weights"], dict):
        raise ValueError("weights.json に feature_weights(dict) が必要です。")

    if not cfg["feature_weights"]:
        raise ValueError("feature_weights が空です。少なくとも1項目設定してください。")

    score_floor = cfg.get("score_floor", 0.01)
    cfg["score_floor"] = float(score_floor)
    return cfg


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename_map = {}
    existing = set(df.columns)
    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in existing:
            continue
        for a in aliases:
            if a in existing:
                rename_map[a] = canonical
                existing.add(canonical)
                break

    return df.rename(columns=rename_map)


def to_numeric_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


def normalize_minmax(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    min_val = float(s.min())
    max_val = float(s.max())
    if np.isclose(max_val, min_val):
        return pd.Series(1.0, index=s.index, dtype=float)
    return (s - min_val) / (max_val - min_val)


def prepare_features(df: pd.DataFrame, feature_weights: dict) -> pd.DataFrame:
    df = df.copy()
    for feature in feature_weights:
        if feature == "return_rate":
            if "return_rate" in df.columns:
                df["return_rate"] = to_numeric_series(df, "return_rate", default=0.0)
            elif "return_qty" in df.columns:
                sales = to_numeric_series(df, "sales_qty", default=0.0)
                ret = to_numeric_series(df, "return_qty", default=0.0)
                denom = sales.replace(0, np.nan)
                df["return_rate"] = (ret / denom).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            else:
                df["return_rate"] = 0.0
            continue

        if feature not in df.columns:
            cols = ", ".join(df.columns)
            raise KeyError(
                f"重み対象列 '{feature}' が入力CSVにありません。現在の列: {cols}"
            )
        df[feature] = to_numeric_series(df, feature, default=0.0)
    return df


def build_score(df: pd.DataFrame, feature_weights: dict, score_floor: float) -> tuple[pd.Series, pd.DataFrame]:
    contrib = pd.DataFrame(index=df.index)
    score = pd.Series(0.0, index=df.index, dtype=float)

    for feature, weight in feature_weights.items():
        w = float(weight)
        raw = to_numeric_series(df, feature, default=0.0)
        norm = normalize_minmax(raw)

        if w >= 0:
            c = w * norm
        else:
            c = abs(w) * (1.0 - norm)

        contrib[f"norm_{feature}"] = norm
        contrib[f"contrib_{feature}"] = c
        score += c

    return score.clip(lower=float(score_floor)), contrib


def allocate_with_limits(
    scores: np.ndarray,
    min_alloc: np.ndarray,
    max_alloc: np.ndarray,
    total_units: int,
) -> np.ndarray:
    alloc = min_alloc.astype(int).copy()
    remaining = int(total_units - alloc.sum())

    if remaining < 0:
        raise ValueError("最低配分数の合計が総配分数を超えています。")

    loops = 0
    while remaining > 0:
        loops += 1
        if loops > 100000:
            raise RuntimeError("配分計算が収束しませんでした。制約を見直してください。")

        capacity = max_alloc - alloc
        eligible = np.where(capacity > 0)[0]
        if len(eligible) == 0:
            raise ValueError("最大配分数の制約により、総配分数まで割り当てできません。")

        eligible_scores = scores[eligible].astype(float)
        score_sum = float(eligible_scores.sum())
        if score_sum <= 0:
            eligible_scores = np.ones_like(eligible_scores, dtype=float)
            score_sum = float(eligible_scores.sum())

        quota = remaining * (eligible_scores / score_sum)
        step = np.floor(quota).astype(int)
        step = np.minimum(step, capacity[eligible])
        step = np.maximum(step, 0)
        gained = int(step.sum())

        if gained > 0:
            alloc[eligible] += step
            remaining -= gained
            continue

        order = np.argsort(-quota)
        for pos in order:
            idx = eligible[pos]
            if alloc[idx] >= max_alloc[idx]:
                continue
            alloc[idx] += 1
            remaining -= 1
            if remaining == 0:
                break

    return alloc


def build_output_path(base_dir: Path, output_arg: str) -> Path:
    if output_arg:
        p = Path(output_arg)
        return p if p.is_absolute() else (base_dir / p)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / "data" / "output" / f"allocation_result_{ts}.csv"


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = base_dir / input_path

    weights_path = Path(args.weights)
    if not weights_path.is_absolute():
        weights_path = base_dir / weights_path

    if args.total <= 0:
        raise ValueError("--total は1以上で指定してください。")

    df = pd.read_csv(input_path, encoding="utf-8-sig", dtype=str)
    if df.empty:
        raise ValueError("入力CSVが空です。データを投入してください。")

    df = standardize_columns(df)
    if "jan_code" not in df.columns:
        raise KeyError("入力CSVに JANコード列が必要です（jan_code / JAN / 商品コード など）。")

    if "item_name" not in df.columns:
        df["item_name"] = df["jan_code"]

    cfg = load_weights(weights_path)
    feature_weights = cfg["feature_weights"]
    score_floor = cfg["score_floor"]

    df = prepare_features(df, feature_weights)

    df["min_allocate"] = to_numeric_series(df, "min_allocate", default=0.0).round().clip(lower=0).astype(int)
    default_max = float(args.total)
    raw_max = to_numeric_series(df, "max_allocate", default=default_max)
    raw_max = raw_max.where(raw_max > 0, default_max).round()
    df["max_allocate"] = raw_max.clip(lower=df["min_allocate"], upper=args.total).astype(int)

    min_sum = int(df["min_allocate"].sum())
    max_sum = int(df["max_allocate"].sum())
    if min_sum > args.total:
        raise ValueError(f"最低配分数の合計({min_sum})が総配分数({args.total})を超えています。")
    if max_sum < args.total:
        raise ValueError(f"最大配分数の合計({max_sum})が総配分数({args.total})未満です。")

    score, contrib = build_score(df, feature_weights, score_floor)
    allocation = allocate_with_limits(
        scores=score.to_numpy(dtype=float),
        min_alloc=df["min_allocate"].to_numpy(dtype=int),
        max_alloc=df["max_allocate"].to_numpy(dtype=int),
        total_units=args.total,
    )

    result = df.copy()
    result["score_total"] = score.round(6)
    result["allocation_units"] = allocation
    result = pd.concat([result, contrib.round(6)], axis=1)
    result = result.sort_values(
        ["allocation_units", "score_total", "jan_code"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    output_path = build_output_path(base_dir, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary_path = output_path.with_name(output_path.stem + "_summary.txt")
    with summary_path.open("w", encoding="utf-8") as fh:
        fh.write(f"input_csv: {input_path}\n")
        fh.write(f"weights_json: {weights_path}\n")
        fh.write(f"total_units: {args.total}\n")
        fh.write(f"rows: {len(result)}\n")
        fh.write(f"allocated_sum: {int(result['allocation_units'].sum())}\n")
        fh.write(f"min_allocate_sum: {min_sum}\n")
        fh.write(f"max_allocate_sum: {max_sum}\n")
        fh.write("feature_weights:\n")
        for k, v in feature_weights.items():
            fh.write(f"  - {k}: {v}\n")
        fh.write(f"score_floor: {score_floor}\n")

    top = result.loc[:, ["jan_code", "item_name", "allocation_units", "score_total"]].head(10)
    print("=== Allocation Completed ===")
    print(f"output_csv: {output_path}")
    print(f"summary_txt: {summary_path}")
    print(f"allocated_sum: {int(result['allocation_units'].sum())}")
    print("\nTop 10:")
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
