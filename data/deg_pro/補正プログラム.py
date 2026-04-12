import numpy as np
import pandas as pd


DOW_INDEX_FLOOR = 0.4
MAX_CORRECTION_FACTOR = 5.0


def build_base_df(
    sales_path: str = "sku_daily_sales.csv",
    map_path: str = "jan_product_map.csv",
) -> pd.DataFrame:
    # Sales (headerless)
    sales = pd.read_csv(sales_path, dtype=str, header=None, low_memory=False)
    sales.columns = [
        "sku_code",
        "product_name",
        "color",
        "unknown_col",
        "launch_date",
        "sales_date",
        "sales_qty",
    ]

    # JAN -> product mapping
    target = pd.read_csv(map_path, dtype=str, low_memory=False)
    sales.columns = sales.columns.str.strip()
    target.columns = target.columns.str.strip()
    sales["sku_code"] = sales["sku_code"].str.strip()
    target["jan_code"] = target["jan_code"].str.strip()
    target["product_code"] = target["product_code"].str.strip()

    # Join target SKUs only
    df = sales.merge(
        target,
        left_on="sku_code",
        right_on="jan_code",
        how="inner",
    )

    # Type normalization
    df["sales_date"] = pd.to_datetime(df["sales_date"], format="%Y%m%d", errors="coerce")
    df["launch_date"] = pd.to_datetime(df["launch_date"], format="%Y%m%d", errors="coerce")
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")
    df = df.dropna(subset=["product_code", "sales_date"])
    df["sales_qty"] = df["sales_qty"].fillna(0)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    # Base key is JAN(SKU). Keep product_code for later product-level grouping.
    x = df[["jan_code", "product_code", "sales_date", "sales_qty", "launch_date"]].copy()

    # Daily aggregation by JAN(SKU)
    x = x.groupby(["jan_code", "product_code", "sales_date"], as_index=False)["sales_qty"].sum()

    # Launch date by JAN (fallback to first sales_date if launch_date is missing)
    launch_map = (
        df.groupby("jan_code")["launch_date"].min()
        .fillna(df.groupby("jan_code")["sales_date"].min())
        .rename("launch_date")
    )
    x = x.drop(columns=["launch_date"], errors="ignore").merge(launch_map, on="jan_code", how="left")

    # Fill missing days from launch date to global max date
    end_date = x["sales_date"].max()
    rows = []
    for jan, g in x.groupby("jan_code", sort=False):
        start = g["launch_date"].min()
        prod = g["product_code"].iloc[0]
        idx = pd.date_range(start, end_date, freq="D")
        t = (
            g.set_index("sales_date")[["sales_qty"]]
            .reindex(idx, fill_value=0)
            .rename_axis("sales_date")
            .reset_index()
        )
        t["jan_code"] = jan
        t["product_code"] = prod
        t["launch_date"] = start
        rows.append(t[["jan_code", "product_code", "sales_date", "sales_qty", "launch_date"]])
    daily = pd.concat(rows, ignore_index=True)

    # Base features
    daily["day_of_week"] = daily["sales_date"].dt.dayofweek
    daily["month"] = daily["sales_date"].dt.month
    daily["days_since_launch"] = (daily["sales_date"] - daily["launch_date"]).dt.days

    # Reduce large-order spikes by JAN-level p99 clipping.
    # IMPORTANT:
    # - Calculate p99 from positive-sales days only, so sparse JANs do not get p99=0.
    # - For JANs that have any positive sale, enforce p99 >= 1.
    #   This keeps "sold days" from being collapsed to 0 by clipping.
    p99_pos = (
        daily.loc[daily["sales_qty"] > 0]
        .groupby("jan_code")["sales_qty"]
        .quantile(0.99)
        .rename("p99")
    )
    p99_all = daily.groupby("jan_code")["sales_qty"].quantile(0.99).rename("p99_all")
    has_pos = daily.groupby("jan_code")["sales_qty"].max().rename("max_sales_qty")
    p99_df = pd.concat([p99_pos, p99_all, has_pos], axis=1).reset_index()
    p99_df["p99"] = p99_df["p99"].fillna(p99_df["p99_all"])
    p99_df.loc[p99_df["max_sales_qty"] > 0, "p99"] = p99_df.loc[
        p99_df["max_sales_qty"] > 0, "p99"
    ].clip(lower=1)

    daily = daily.merge(p99_df[["jan_code", "p99"]], on="jan_code", how="left")
    daily["sales_qty_clean"] = np.minimum(daily["sales_qty"], daily["p99"])

    # Day-of-week index.
    # Clamp very small indices so weekend rows are not amplified too aggressively,
    # then renormalize to mean 1 for interpretability.
    dow_mean = daily.groupby("day_of_week")["sales_qty_clean"].mean()
    dow_index = dow_mean / dow_mean.mean()
    dow_index = dow_index.clip(lower=DOW_INDEX_FLOOR)
    dow_index = (dow_index / dow_index.mean()).rename("dow_index")
    daily = daily.merge(dow_index, on="day_of_week", how="left")
    daily["sales_dow_adj"] = daily["sales_qty_clean"] / daily["dow_index"]

    # Month index (JAN mix bias mitigation with per-JAN ratio median)
    pm = daily.groupby(["jan_code", "month"], as_index=False)["sales_dow_adj"].mean()
    p_base = (
        daily.groupby("jan_code", as_index=False)["sales_dow_adj"]
        .mean()
        .rename(columns={"sales_dow_adj": "p_mean"})
    )
    pm = pm.merge(p_base, on="jan_code", how="left")
    pm["month_ratio"] = pm["sales_dow_adj"] / pm["p_mean"]
    month_index = pm.groupby("month")["month_ratio"].median()
    month_index = (month_index / month_index.mean()).rename("month_index")

    daily = daily.merge(month_index, on="month", how="left")
    daily["sales_adj"] = daily["sales_dow_adj"] / daily["month_index"]

    # Keep sold-day correction within a practical range.
    sold_mask = daily["sales_qty"] > 0
    sales_adj_cap = daily["sales_qty"] * MAX_CORRECTION_FACTOR
    daily.loc[sold_mask, "sales_adj"] = np.minimum(
        daily.loc[sold_mask, "sales_adj"],
        sales_adj_cap.loc[sold_mask],
    )
    return daily


def main() -> None:
    df = build_base_df()
    daily = build_features(df)
    out_path = "product_daily_features.csv"
    daily.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_path}")
    print(f"Rows: {len(daily):,}, Products: {daily['product_code'].nunique():,}")


if __name__ == "__main__":
    main()
