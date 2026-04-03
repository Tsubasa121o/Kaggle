import os
import re
import pandas as pd

# =====================
# Config
# =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
PARQUET_DIR = os.path.join(BASE_DIR, 'parquet_cache_452')
os.makedirs(PARQUET_DIR, exist_ok=True)

BLACKLIST = ['【繰 越 在 庫】', '【期 間 合 計】', 'デグナー八王子店']

# =====================
# Helpers
# =====================
def find_file(pattern_fn):
    candidates = [f for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f))]
    for f in candidates:
        if pattern_fn(f):
            return os.path.join(BASE_DIR, f)
    return None


def parse_target_jans(jan_csv_path):
    jan_set = set()
    with open(jan_csv_path, 'r', encoding='utf-8-sig') as fh:
        for line in fh:
            first_col = line.split(',')[0].strip().strip('"')
            m = re.fullmatch(r'(452\d{10})', first_col)
            if m:
                jan_set.add(m.group(1))
    return jan_set


def save_parquet(csv_path, parquet_path):
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df.to_parquet(parquet_path, index=False)


# =====================
# Locate files
# =====================
excel_path = find_file(lambda f: f.lower().endswith('.xlsx') and not f.startswith('~$') and '在庫受払帳' in f)
if excel_path is None:
    excel_path = find_file(lambda f: f.lower().endswith('.xlsx') and not f.startswith('~$'))

jan_csv_path = find_file(lambda f: f.lower().endswith('.csv') and 'JAN' in f)

if excel_path is None:
    raise FileNotFoundError('在庫受払帳.xlsx が見つかりません。')
if jan_csv_path is None:
    raise FileNotFoundError('JAN一覧.csv が見つかりません。')

print(f'Using Excel: {excel_path}')
print(f'Using JAN CSV: {jan_csv_path}')

# =====================
# Load & cleanse
# =====================
df = pd.read_excel(excel_path)
required_cols = ['入出荷先名', '入出荷日', '商品コード', '伝票識別', '出荷数', '入荷数', '在庫数']
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(f'必要列が不足しています: {missing}')

# Do not mutate original
mask = df['入出荷先名'].apply(lambda x: not any(word in str(x) for word in BLACKLIST))
df_clean = df[mask].copy()

# Robust date parse for float-like yyyymmdd.0
df_clean['入出荷日'] = pd.to_datetime(
    df_clean['入出荷日'].astype(str).str.replace('.0', '', regex=False),
    format='%Y%m%d',
    errors='coerce'
)

df_clean['商品コード'] = df_clean['商品コード'].astype(str).str.strip()
df_clean['_row_no'] = range(len(df_clean))

# Target JAN filter (452... from JAN list)
target_jans = parse_target_jans(jan_csv_path)
df_target = df_clean[df_clean['商品コード'].isin(target_jans)].copy()
df_target = df_target.sort_values(['商品コード', '入出荷日', '_row_no']).reset_index(drop=True)

print(f'Rows(raw): {len(df):,}')
print(f'Rows(clean): {len(df_clean):,}')
print(f'Rows(target 452 JAN): {len(df_target):,}')
print(f'Unique target JAN in list: {len(target_jans):,}')
print(f'Unique target JAN in ledger: {df_target["商品コード"].nunique():,}')

# =====================
# Exports
# =====================
clean_csv = os.path.join(BASE_DIR, '整理済み在庫データ_452限定.csv')
returns_csv = os.path.join(BASE_DIR, '返品データ一覧_452限定.csv')
receipts_csv = os.path.join(BASE_DIR, '入荷データ一覧_452限定.csv')
stockouts_csv = os.path.join(BASE_DIR, '在庫切れ期間一覧_452限定.csv')

# 1) Clean dataset
out_cols = [c for c in df_target.columns if c != '_row_no']
df_target[out_cols].to_csv(clean_csv, encoding='utf-8-sig', index=False)

# 2) Returns
df_target['出荷数_num'] = pd.to_numeric(df_target['出荷数'], errors='coerce')
returns = df_target[(df_target['伝票識別'] == '売上') & (df_target['出荷数_num'] < 0)][['商品コード', '入出荷日', '出荷数']]
returns.to_csv(returns_csv, encoding='utf-8-sig', index=False)

# 3) Receipts
df_target['入荷数_num'] = pd.to_numeric(df_target['入荷数'], errors='coerce')
receipts = df_target[(df_target['伝票識別'] == '仕入') & (df_target['入荷数_num'] > 0)][['商品コード', '入出荷日', '入荷数']]
receipts.to_csv(receipts_csv, encoding='utf-8-sig', index=False)

# 4) Stockout periods (transition-based)
# start: 在庫が >0 から 0 へ落ちた日
# end:   その後、最初の「仕入かつ入荷数>0」日
stockout_periods = []
for code, g in df_target.groupby('商品コード'):
    g = g.sort_values(['入出荷日', '_row_no']).reset_index(drop=True)
    stock = pd.to_numeric(g['在庫数'], errors='coerce')
    in_qty = pd.to_numeric(g['入荷数'], errors='coerce')

    starts = g.index[(stock == 0) & (stock.shift(1).fillna(1) > 0)].tolist()
    for s in starts:
        tail = g.iloc[s+1:]
        supply = tail[(tail['伝票識別'] == '仕入') & (pd.to_numeric(tail['入荷数'], errors='coerce') > 0)]
        if not supply.empty:
            first_supply = supply.iloc[0]
            stockout_date = g.loc[s, '入出荷日']
            supply_date = first_supply['入出荷日']
            if pd.notna(stockout_date) and pd.notna(supply_date):
                days_out = (supply_date - stockout_date).days
                stockout_periods.append({
                    '商品コード': code,
                    '在庫切れ日': stockout_date,
                    '入荷再開日': supply_date,
                    '在庫ゼロ日数': days_out
                })

pd.DataFrame(stockout_periods).to_csv(stockouts_csv, encoding='utf-8-sig', index=False)

# 5) Parquet cache (overwrite to keep sync)
save_parquet(returns_csv, os.path.join(PARQUET_DIR, 'returns_452.parquet'))
save_parquet(receipts_csv, os.path.join(PARQUET_DIR, 'receipts_452.parquet'))
save_parquet(stockouts_csv, os.path.join(PARQUET_DIR, 'stockouts_452.parquet'))

print('\nDone.')
print(f'返品 rows: {len(returns):,}')
print(f'入荷 rows: {len(receipts):,}')
print(f'在庫切れ期間 rows: {len(stockout_periods):,}')
print(f'Output dir: {BASE_DIR}')
print(f'Parquet dir: {PARQUET_DIR}')
