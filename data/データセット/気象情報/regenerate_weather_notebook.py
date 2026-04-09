import json
from pathlib import Path


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": text,
    }


cells = []

cells.append(
    md(
        "# \u65e5\u672c\u306e\u6c17\u8c61\u30c8\u30ec\u30f3\u30c9\u5206\u6790\uff08\u90fd\u9053\u5e9c\u770c\u5225\u30fb\u30a8\u30ea\u30a2\u5225\uff09\n\n"
        "\u3053\u306e\u30ce\u30fc\u30c8\u306f `*_2015-25.csv` \u3092\u76f4\u63a5\u8aad\u307f\u8fbc\u307f\u3001\u4ee5\u4e0b\u3092\u5206\u6790\u3057\u307e\u3059\u3002\n\n"
        "- \u5730\u70b9\u5225\uff08\u90fd\u9053\u5e9c\u770c\u4ee3\u8868\u5730\u70b9\uff09\u306e\u6c17\u6e29\u30fb\u964d\u6c34\u30fb\u964d\u96ea\u306e\u63a8\u79fb\n"
        "- \u90fd\u9053\u5e9c\u770c\u5225\u306e\u50be\u5411\n"
        "- \u30a8\u30ea\u30a2\u5225\uff08\u5317\u6d77\u9053 / \u6771\u5317 / \u95a2\u6771 / \u4e2d\u90e8 / \u8fd1\u757f / \u4e2d\u56fd / \u56db\u56fd / \u4e5d\u5dde / \u6c96\u7e04\uff09\u306e\u63a8\u79fb\n\n"
        "\u58f2\u4e0a\u30c7\u30fc\u30bf\u3068\u306f\u7d50\u5408\u305b\u305a\u3001\u6c17\u8c61\u30c7\u30fc\u30bf\u5358\u4f53\u3067\u4f7f\u3048\u308b\u5f62\u306b\u3057\u3066\u3044\u307e\u3059\u3002"
    )
)

cells.append(
    code(
        "import csv\n"
        "from pathlib import Path\n\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "import matplotlib.font_manager as fm\n"
        "import seaborn as sns\n\n"
        "sns.set_theme(style='whitegrid')\n\n"
        "# \u65e5\u672c\u8a9e\u8868\u793a\u306e\u6587\u5b57\u5316\u3051\u5bfe\u7b56\n"
        "jp_fonts = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'Noto Sans CJK JP', 'IPAexGothic']\n"
        "available_fonts = {f.name for f in fm.fontManager.ttflist}\n"
        "for font in jp_fonts:\n"
        "    if font in available_fonts:\n"
        "        plt.rcParams['font.family'] = font\n"
        "        break\n"
        "plt.rcParams['axes.unicode_minus'] = False\n\n"
        "BASE_DIR = Path.cwd()\n"
        "print('\\u4f5c\\u696d\\u30d5\\u30a9\\u30eb\\u30c0:', BASE_DIR)\n"
    )
)

cells.append(
    code(
        "HEADER_LABELS = {\n"
        "    'temp_avg_c': '\\u5e73\\u5747\\u6c17\\u6e29(\\u2103)',\n"
        "    'temp_max_c': '\\u6700\\u9ad8\\u6c17\\u6e29(\\u2103)',\n"
        "    'temp_min_c': '\\u6700\\u4f4e\\u6c17\\u6e29(\\u2103)',\n"
        "    'precip_mm': '\\u964d\\u6c34\\u91cf\\u306e\\u5408\\u8a08(mm)',\n"
        "    'sunshine_h': '\\u65e5\\u7167\\u6642\\u9593(\\u6642\\u9593)',\n"
        "    'snowfall_cm': '\\u964d\\u96ea\\u91cf\\u5408\\u8a08(cm)',\n"
        "    'humidity_pct': '\\u5e73\\u5747\\u6e7f\\u5ea6(\\uff05)',\n"
        "}\n\n"
        "STATION_TO_PREF = {\n"
        "    '\\u51fd\\u9928': '\\u5317\\u6d77\\u9053', '\\u5c0f\\u6a3d': '\\u5317\\u6d77\\u9053', '\\u5e2f\\u5e83': '\\u5317\\u6d77\\u9053', '\\u672d\\u5e4c': '\\u5317\\u6d77\\u9053', '\\u6839\\u5ba4': '\\u5317\\u6d77\\u9053', '\\u7a1a\\u5185': '\\u5317\\u6d77\\u9053', '\\u7db2\\u8d70': '\\u5317\\u6d77\\u9053', '\\u91e7\\u8def': '\\u5317\\u6d77\\u9053',\n"
        "    '\\u4ed9\\u53f0': '\\u5bae\\u57ce', '\\u5c71\\u5f62': '\\u5c71\\u5f62', '\\u65b0\\u5e84': '\\u5c71\\u5f62', '\\u767d\\u6cb3': '\\u798f\\u5cf6', '\\u76db\\u5ca1': '\\u5ca9\\u624b', '\\u798f\\u5cf6': '\\u798f\\u5cf6', '\\u79cb\\u7530': '\\u79cb\\u7530', '\\u9752\\u68ee': '\\u9752\\u68ee',\n"
        "    '\\u524d\\u6a4b': '\\u7fa4\\u99ac', '\\u5343\\u8449': '\\u5343\\u8449', '\\u5b87\\u90fd\\u5bae': '\\u6803\\u6728', '\\u6771\\u4eac': '\\u6771\\u4eac', '\\u6a2a\\u6d5c': '\\u795e\\u5948\\u5ddd', '\\u6c34\\u6238': '\\u8328\\u57ce', '\\u718a\\u8c37': '\\u57fc\\u7389', '\\u79e9\\u7236': '\\u57fc\\u7389', '\\u92da\\u5b50': '\\u5343\\u8449',\n"
        "    '\\u540d\\u53e4\\u5c4b': '\\u611b\\u77e5', '\\u56db\\u65e5\\u5e02': '\\u4e09\\u91cd', '\\u5bcc\\u5c71': '\\u5bcc\\u5c71', '\\u5c3e\\u9df2': '\\u4e09\\u91cd', '\\u6566\\u8cc0': '\\u798f\\u4e95', '\\u65b0\\u6f5f': '\\u65b0\\u6f5f', '\\u677e\\u672c': '\\u9577\\u91ce', '\\u7532\\u5e9c': '\\u5c71\\u68a8',\n"
        "    '\\u798f\\u4e95': '\\u798f\\u4e95', '\\u8efd\\u4e95\\u6ca2': '\\u9577\\u91ce', '\\u91d1\\u6ca2': '\\u77f3\\u5ddd', '\\u9577\\u91ce': '\\u9577\\u91ce', '\\u9759\\u5ca1': '\\u9759\\u5ca1', '\\u98ef\\u7530': '\\u9577\\u91ce', '\\u6d5c\\u677e': '\\u9759\\u5ca1',\n"
        "    '\\u4eac\\u90fd': '\\u4eac\\u90fd', '\\u548c\\u6b4c\\u5c71': '\\u548c\\u6b4c\\u5c71', '\\u5927\\u6d25': '\\u6ecb\\u8cc0', '\\u5927\\u962a': '\\u5927\\u962a', '\\u5948\\u826f': '\\u5948\\u826f', '\\u59eb\\u8def': '\\u5175\\u5eab', '\\u5f66\\u6839': '\\u6ecb\\u8cc0', '\\u795e\\u6238': '\\u5175\\u5eab', '\\u821e\\u9db4': '\\u4eac\\u90fd',\n"
        "    '\\u5c71\\u53e3': '\\u5c71\\u53e3', '\\u5ca1\\u5c71': '\\u5ca1\\u5c71', '\\u5e83\\u5cf6': '\\u5e83\\u5cf6', '\\u677e\\u6c5f': '\\u5cf6\\u6839', '\\u6d5c\\u7530': '\\u5cf6\\u6839', '\\u798f\\u5c71': '\\u5e83\\u5cf6', '\\u9ce5\\u53d6': '\\u9ce5\\u53d6',\n"
        "    '\\u5fb3\\u5cf6': '\\u5fb3\\u5cf6', '\\u677e\\u5c71': '\\u611b\\u5a9b', '\\u9ad8\\u677e': '\\u9999\\u5ddd', '\\u9ad8\\u77e5': '\\u9ad8\\u77e5',\n"
        "    '\\u4f50\\u4e16\\u4fdd': '\\u9577\\u5d0e', '\\u4f50\\u8cc0': '\\u4f50\\u8cc0', '\\u5927\\u5206': '\\u5927\\u5206', '\\u5bae\\u5d0e': '\\u5bae\\u5d0e', '\\u718a\\u672c': '\\u718a\\u672c', '\\u798f\\u5ca1': '\\u798f\\u5ca1', '\\u9e7f\\u5150\\u5cf6': '\\u9e7f\\u5150\\u5cf6', '\\u90a3\\u8987': '\\u6c96\\u7e04',\n"
        "}\n\n"
        "PREF_TO_REGION = {\n"
        "    '\\u5317\\u6d77\\u9053': '\\u5317\\u6d77\\u9053',\n"
        "    '\\u9752\\u68ee': '\\u6771\\u5317', '\\u5ca9\\u624b': '\\u6771\\u5317', '\\u5bae\\u57ce': '\\u6771\\u5317', '\\u79cb\\u7530': '\\u6771\\u5317', '\\u5c71\\u5f62': '\\u6771\\u5317', '\\u798f\\u5cf6': '\\u6771\\u5317',\n"
        "    '\\u8328\\u57ce': '\\u95a2\\u6771', '\\u6803\\u6728': '\\u95a2\\u6771', '\\u7fa4\\u99ac': '\\u95a2\\u6771', '\\u57fc\\u7389': '\\u95a2\\u6771', '\\u5343\\u8449': '\\u95a2\\u6771', '\\u6771\\u4eac': '\\u95a2\\u6771', '\\u795e\\u5948\\u5ddd': '\\u95a2\\u6771',\n"
        "    '\\u65b0\\u6f5f': '\\u4e2d\\u90e8', '\\u5bcc\\u5c71': '\\u4e2d\\u90e8', '\\u77f3\\u5ddd': '\\u4e2d\\u90e8', '\\u798f\\u4e95': '\\u4e2d\\u90e8', '\\u5c71\\u68a8': '\\u4e2d\\u90e8', '\\u9577\\u91ce': '\\u4e2d\\u90e8', '\\u5c90\\u961c': '\\u4e2d\\u90e8', '\\u9759\\u5ca1': '\\u4e2d\\u90e8', '\\u611b\\u77e5': '\\u4e2d\\u90e8', '\\u4e09\\u91cd': '\\u4e2d\\u90e8',\n"
        "    '\\u6ecb\\u8cc0': '\\u8fd1\\u757f', '\\u4eac\\u90fd': '\\u8fd1\\u757f', '\\u5927\\u962a': '\\u8fd1\\u757f', '\\u5175\\u5eab': '\\u8fd1\\u757f', '\\u5948\\u826f': '\\u8fd1\\u757f', '\\u548c\\u6b4c\\u5c71': '\\u8fd1\\u757f',\n"
        "    '\\u9ce5\\u53d6': '\\u4e2d\\u56fd', '\\u5cf6\\u6839': '\\u4e2d\\u56fd', '\\u5ca1\\u5c71': '\\u4e2d\\u56fd', '\\u5e83\\u5cf6': '\\u4e2d\\u56fd', '\\u5c71\\u53e3': '\\u4e2d\\u56fd',\n"
        "    '\\u5fb3\\u5cf6': '\\u56db\\u56fd', '\\u9999\\u5ddd': '\\u56db\\u56fd', '\\u611b\\u5a9b': '\\u56db\\u56fd', '\\u9ad8\\u77e5': '\\u56db\\u56fd',\n"
        "    '\\u798f\\u5ca1': '\\u4e5d\\u5dde', '\\u4f50\\u8cc0': '\\u4e5d\\u5dde', '\\u9577\\u5d0e': '\\u4e5d\\u5dde', '\\u718a\\u672c': '\\u4e5d\\u5dde', '\\u5927\\u5206': '\\u4e5d\\u5dde', '\\u5bae\\u5d0e': '\\u4e5d\\u5dde', '\\u9e7f\\u5150\\u5cf6': '\\u4e5d\\u5dde',\n"
        "    '\\u6c96\\u7e04': '\\u6c96\\u7e04',\n"
        "}\n"
    )
)

cells.append(
    code(
        "def to_float(value):\n"
        "    text = str(value).strip() if value is not None else ''\n"
        "    if text == '':\n"
        "        return np.nan\n"
        "    try:\n"
        "        return float(text)\n"
        "    except ValueError:\n"
        "        return np.nan\n\n"
        "def detect_value_indexes(metric_row, subheader_row):\n"
        "    indexes = {'date': 0}\n"
        "    for key, label in HEADER_LABELS.items():\n"
        "        idx = None\n"
        "        for i, metric in enumerate(metric_row):\n"
        "            sub = subheader_row[i] if i < len(subheader_row) else ''\n"
        "            if metric == label and sub == '':\n"
        "                idx = i\n"
        "                break\n"
        "        if idx is None:\n"
        "            for i, metric in enumerate(metric_row):\n"
        "                if metric == label:\n"
        "                    idx = i\n"
        "                    break\n"
        "        indexes[key] = idx\n"
        "    return indexes\n\n"
        "def read_station_csv(path: Path) -> pd.DataFrame:\n"
        "    station = path.stem.replace('_2015-25', '')\n"
        "    with path.open('r', encoding='cp932', newline='') as f:\n"
        "        rows = list(csv.reader(f))\n"
        "    if len(rows) < 7:\n"
        "        return pd.DataFrame()\n"
        "    metric_row = rows[3]\n"
        "    subheader_row = rows[5]\n"
        "    value_idx = detect_value_indexes(metric_row, subheader_row)\n"
        "    required_idx = [idx for idx in value_idx.values() if idx is not None]\n"
        "    if not required_idx:\n"
        "        return pd.DataFrame()\n"
        "    max_idx = max(required_idx)\n"
        "    records = []\n"
        "    for row in rows[6:]:\n"
        "        if len(row) <= max_idx:\n"
        "            continue\n"
        "        date_raw = str(row[value_idx['date']]).strip()\n"
        "        if not date_raw:\n"
        "            continue\n"
        "        dt = pd.to_datetime(date_raw, format='%Y/%m/%d', errors='coerce')\n"
        "        if pd.isna(dt):\n"
        "            continue\n"
        "        rec = {'date': dt.normalize(), 'station': station}\n"
        "        for col, idx in value_idx.items():\n"
        "            if col == 'date':\n"
        "                continue\n"
        "            rec[col] = to_float(row[idx]) if idx is not None and idx < len(row) else np.nan\n"
        "        records.append(rec)\n"
        "    return pd.DataFrame.from_records(records)\n"
    )
)

cells.append(
    code(
        "station_files = sorted(BASE_DIR.glob('*_2015-25.csv'))\n"
        "print('\\u5730\\u70b9CSV\\u6570:', len(station_files))\n\n"
        "frames = []\n"
        "for p in station_files:\n"
        "    df = read_station_csv(p)\n"
        "    if not df.empty:\n"
        "        frames.append(df)\n\n"
        "station_daily = pd.concat(frames, ignore_index=True)\n"
        "station_daily['prefecture'] = station_daily['station'].map(STATION_TO_PREF)\n"
        "station_daily['region'] = station_daily['prefecture'].map(PREF_TO_REGION)\n"
        "station_daily['year'] = station_daily['date'].dt.year\n"
        "station_daily['month'] = station_daily['date'].dt.month\n"
        "station_daily['year_month'] = station_daily['date'].dt.to_period('M').dt.to_timestamp()\n"
        "station_daily['rain_flag'] = (station_daily['precip_mm'].fillna(0) >= 1.0).astype(int)\n"
        "station_daily['snow_flag'] = (station_daily['snowfall_cm'].fillna(0) >= 1.0).astype(int)\n"
        "station_daily['heavy_rain_flag'] = (station_daily['precip_mm'].fillna(0) >= 10.0).astype(int)\n\n"
        "print('\\u30ec\\u30b3\\u30fc\\u30c9\\u6570:', len(station_daily))\n"
        "print('\\u671f\\u9593:', station_daily['date'].min().date(), '\\u301c', station_daily['date'].max().date())\n"
        "print('\\u5730\\u70b9\\u6570:', station_daily['station'].nunique())\n"
        "print('\\u90fd\\u9053\\u5e9c\\u770c\\u6570:', station_daily['prefecture'].nunique())\n"
        "print('\\u30a8\\u30ea\\u30a2:', sorted(station_daily['region'].dropna().unique().tolist()))\n"
    )
)

cells.append(
    code(
        "pref_daily = (\n"
        "    station_daily.groupby(['date', 'prefecture'], as_index=False)\n"
        "    .agg(temp_avg_c=('temp_avg_c', 'mean'), precip_mm=('precip_mm', 'mean'), snowfall_cm=('snowfall_cm', 'mean'), rain_flag=('rain_flag', 'mean'), snow_flag=('snow_flag', 'mean'))\n"
        ")\n"
        "pref_daily['year_month'] = pref_daily['date'].dt.to_period('M').dt.to_timestamp()\n\n"
        "region_daily = (\n"
        "    station_daily.groupby(['date', 'region'], as_index=False)\n"
        "    .agg(temp_avg_c=('temp_avg_c', 'mean'), precip_mm=('precip_mm', 'mean'), snowfall_cm=('snowfall_cm', 'mean'), rain_flag=('rain_flag', 'mean'), snow_flag=('snow_flag', 'mean'))\n"
        ")\n"
        "region_daily['year_month'] = region_daily['date'].dt.to_period('M').dt.to_timestamp()\n\n"
        "national_daily = (\n"
        "    station_daily.groupby('date', as_index=False)\n"
        "    .agg(temp_avg_c=('temp_avg_c', 'mean'), precip_mm=('precip_mm', 'mean'), snowfall_cm=('snowfall_cm', 'mean'), rain_flag=('rain_flag', 'mean'), snow_flag=('snow_flag', 'mean'))\n"
        ")\n"
        "national_daily['year_month'] = national_daily['date'].dt.to_period('M').dt.to_timestamp()\n\n"
        "station_daily['hot25_flag'] = (station_daily['temp_avg_c'] >= 25).astype(int)\n"
        "station_daily['hot30max_flag'] = (station_daily['temp_max_c'] >= 30).astype(int)\n"
        "station_daily['warm20_flag'] = (station_daily['temp_avg_c'] >= 20).astype(int)\n"
    )
)

cells.append(md("## 1. \\u5168\\u56fd\\u306e\\u63a8\\u79fb\\uff08\\u6708\\u6b21\\uff09"))
cells.append(
    code(
        "national_monthly = national_daily.groupby('year_month', as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'), precip_mm=('precip_mm', 'mean'), snowfall_cm=('snowfall_cm', 'mean'), rain_day_ratio=('rain_flag', 'mean'), snow_day_ratio=('snow_flag', 'mean'))\n"
        "fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)\n"
        "axes[0].plot(national_monthly['year_month'], national_monthly['temp_avg_c'], color='tab:red')\n"
        "axes[0].set_title('\\u5168\\u56fd \\u6708\\u6b21\\u5e73\\u5747\\u6c17\\u6e29\\u306e\\u63a8\\u79fb')\n"
        "axes[1].plot(national_monthly['year_month'], national_monthly['precip_mm'], label='\\u964d\\u6c34\\u91cf(mm)')\n"
        "axes[1].plot(national_monthly['year_month'], national_monthly['snowfall_cm'], label='\\u964d\\u96ea\\u91cf(cm)')\n"
        "axes[1].legend()\n"
        "axes[1].set_title('\\u5168\\u56fd \\u6708\\u6b21\\u964d\\u6c34\\u91cf\\u30fb\\u964d\\u96ea\\u91cf')\n"
        "axes[2].plot(national_monthly['year_month'], national_monthly['rain_day_ratio'], label='\\u96e8\\u65e5\\u7387')\n"
        "axes[2].plot(national_monthly['year_month'], national_monthly['snow_day_ratio'], label='\\u96ea\\u65e5\\u7387')\n"
        "axes[2].legend()\n"
        "axes[2].set_title('\\u5168\\u56fd \\u96e8\\u65e5\\u7387\\u30fb\\u96ea\\u65e5\\u7387')\n"
        "plt.tight_layout(); plt.show()\n"
    )
)

cells.append(md("## 2. \\u30a8\\u30ea\\u30a2\\u5225\\u306e\\u6c17\\u6e29\\u63a8\\u79fb\\uff08\\u6708\\u6b21\\uff09"))
cells.append(
    code(
        "region_monthly = region_daily.groupby(['year_month', 'region'], as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'), precip_mm=('precip_mm', 'mean'), snowfall_cm=('snowfall_cm', 'mean'), rain_day_ratio=('rain_flag', 'mean'), snow_day_ratio=('snow_flag', 'mean'))\n"
        "plt.figure(figsize=(16, 6))\n"
        "for region, g in region_monthly.groupby('region'):\n"
        "    plt.plot(g['year_month'], g['temp_avg_c'], label=region)\n"
        "plt.title('\\u30a8\\u30ea\\u30a2\\u5225 \\u6708\\u6b21\\u5e73\\u5747\\u6c17\\u6e29\\u306e\\u63a8\\u79fb')\n"
        "plt.legend(ncol=5)\n"
        "plt.tight_layout(); plt.show()\n"
    )
)

cells.append(md("## 3. \\u90fd\\u9053\\u5e9c\\u770c\\u5225\\u306e\\u6708\\u5225\\u5e73\\u5e74\\u5024\\uff08\\u30d2\\u30fc\\u30c8\\u30de\\u30c3\\u30d7\\uff09"))
cells.append(
    code(
        "pref_climatology = pref_daily.copy()\n"
        "pref_climatology['month'] = pref_climatology['date'].dt.month\n"
        "pref_climatology = pref_climatology.groupby(['prefecture', 'month'], as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'), precip_mm=('precip_mm', 'mean'), snowfall_cm=('snowfall_cm', 'mean'))\n"
        "fig, axes = plt.subplots(3, 1, figsize=(16, 18))\n"
        "sns.heatmap(pref_climatology.pivot(index='prefecture', columns='month', values='temp_avg_c'), cmap='coolwarm', ax=axes[0])\n"
        "axes[0].set_title('\\u90fd\\u9053\\u5e9c\\u770c\\u5225 \\u6708\\u5225\\u5e73\\u5747\\u6c17\\u6e29')\n"
        "sns.heatmap(pref_climatology.pivot(index='prefecture', columns='month', values='precip_mm'), cmap='Blues', ax=axes[1])\n"
        "axes[1].set_title('\\u90fd\\u9053\\u5e9c\\u770c\\u5225 \\u6708\\u5225\\u964d\\u6c34\\u91cf')\n"
        "sns.heatmap(pref_climatology.pivot(index='prefecture', columns='month', values='snowfall_cm'), cmap='Purples', ax=axes[2])\n"
        "axes[2].set_title('\\u90fd\\u9053\\u5e9c\\u770c\\u5225 \\u6708\\u5225\\u964d\\u96ea\\u91cf')\n"
        "plt.tight_layout(); plt.show()\n"
    )
)

cells.append(md("## 4. \\u9ad8\\u6e29\\u65e5\\u306e\\u6bd4\\u7387\\u306e\\u63a8\\u79fb\\uff08\\u5168\\u56fd\\u30fb\\u30a8\\u30ea\\u30a2\\u5225\\uff09"))
cells.append(
    code(
        "national_hot = station_daily.groupby('year', as_index=False).agg(hot25_ratio=('hot25_flag', 'mean'), hot30max_ratio=('hot30max_flag', 'mean'))\n"
        "region_hot = station_daily.groupby(['year', 'region'], as_index=False).agg(hot25_ratio=('hot25_flag', 'mean'), hot30max_ratio=('hot30max_flag', 'mean'))\n\n"
        "fig, axes = plt.subplots(2, 1, figsize=(16, 11), sharex=True)\n"
        "axes[0].plot(national_hot['year'], national_hot['hot25_ratio'], color='tab:red', lw=2, label='\\u5168\\u56fd')\n"
        "for region, g in region_hot.groupby('region'):\n"
        "    axes[0].plot(g['year'], g['hot25_ratio'], lw=1.1, alpha=0.8, label=region)\n"
        "axes[0].set_title('\\u5e73\\u5747\\u6c17\\u6e2925\\u2103\\u4ee5\\u4e0a\\u306e\\u65e5\\u306e\\u6bd4\\u7387\\u63a8\\u79fb')\n"
        "axes[0].set_ylabel('\\u6bd4\\u7387')\n"
        "axes[0].legend(ncol=5)\n\n"
        "axes[1].plot(national_hot['year'], national_hot['hot30max_ratio'], color='tab:orange', lw=2, label='\\u5168\\u56fd')\n"
        "for region, g in region_hot.groupby('region'):\n"
        "    axes[1].plot(g['year'], g['hot30max_ratio'], lw=1.1, alpha=0.8, label=region)\n"
        "axes[1].set_title('\\u6700\\u9ad8\\u6c17\\u6e2930\\u2103\\u4ee5\\u4e0a\\u306e\\u65e5\\u306e\\u6bd4\\u7387\\u63a8\\u79fb')\n"
        "axes[1].set_ylabel('\\u6bd4\\u7387')\n"
        "axes[1].set_xlabel('\\u5e74')\n"
        "plt.tight_layout(); plt.show()\n"
    )
)

cells.append(md("## 5. \\u6708\\u5225\\u30c8\\u30ec\\u30f3\\u30c9\\u6bd4\\u8f03\\uff08\\u3069\\u306e\\u6708\\u304c\\u9ad8\\u6e29\\u5316\\u3057\\u3066\\u3044\\u308b\\u304b\\uff09"))
cells.append(
    code(
        "monthly_trend = station_daily.groupby(['year', 'month'], as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'))\n"
        "trend_rows = []\n"
        "for month, g in monthly_trend.groupby('month'):\n"
        "    slope = np.polyfit(g['year'], g['temp_avg_c'], 1)[0]\n"
        "    trend_rows.append({'month': month, 'temp_trend_per_decade': slope * 10, 'first_temp': g.iloc[0]['temp_avg_c'], 'last_temp': g.iloc[-1]['temp_avg_c']})\n"
        "monthly_trend_summary = pd.DataFrame(trend_rows).sort_values('temp_trend_per_decade', ascending=False)\n\n"
        "plt.figure(figsize=(14, 6))\n"
        "sns.barplot(data=monthly_trend_summary, x='month', y='temp_trend_per_decade', palette='coolwarm')\n"
        "plt.title('\\u6708\\u5225\\u5e73\\u5747\\u6c17\\u6e29\\u30c8\\u30ec\\u30f3\\u30c9\\uff0810\\u5e74\\u3042\\u305f\\u308a\\u4e0a\\u6607\\u5e45\\uff09')\n"
        "plt.xlabel('\\u6708')\n"
        "plt.ylabel('\\u4e0a\\u6607\\u5e45 (\\u2103 / 10\\u5e74)')\n"
        "plt.tight_layout(); plt.show()\n\n"
        "monthly_trend_summary\n"
    )
)

cells.append(md("## 6. \\u90fd\\u9053\\u5e9c\\u770c\\u5225\\u306e\\u30c8\\u30ec\\u30f3\\u30c9\\u30e9\\u30f3\\u30ad\\u30f3\\u30b0"))
cells.append(
    code(
        "pref_yearly = station_daily.groupby(['year', 'prefecture'], as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'), hot25_ratio=('hot25_flag', 'mean'), hot30max_ratio=('hot30max_flag', 'mean'))\n"
        "rows = []\n"
        "for prefecture, g in pref_yearly.groupby('prefecture'):\n"
        "    temp_slope = np.polyfit(g['year'], g['temp_avg_c'], 1)[0] * 10\n"
        "    hot25_slope = np.polyfit(g['year'], g['hot25_ratio'], 1)[0] * 10\n"
        "    hot30_slope = np.polyfit(g['year'], g['hot30max_ratio'], 1)[0] * 10\n"
        "    rows.append({'prefecture': prefecture, 'temp_trend_per_decade': temp_slope, 'hot25_ratio_trend_per_decade': hot25_slope, 'hot30max_ratio_trend_per_decade': hot30_slope})\n"
        "pref_trend = pd.DataFrame(rows)\n\n"
        "fig, axes = plt.subplots(1, 2, figsize=(16, 10))\n"
        "top_temp = pref_trend.sort_values('temp_trend_per_decade', ascending=False).head(15)\n"
        "sns.barplot(data=top_temp, y='prefecture', x='temp_trend_per_decade', ax=axes[0], palette='Reds_r')\n"
        "axes[0].set_title('\\u6c17\\u6e29\\u4e0a\\u6607\\u304c\\u5927\\u304d\\u3044\\u90fd\\u9053\\u5e9c\\u770c \\u4e0a\\u4f4d15')\n"
        "axes[0].set_xlabel('\\u4e0a\\u6607\\u5e45 (\\u2103 / 10\\u5e74)')\n"
        "axes[0].set_ylabel('\\u90fd\\u9053\\u5e9c\\u770c')\n\n"
        "top_hot = pref_trend.sort_values('hot30max_ratio_trend_per_decade', ascending=False).head(15)\n"
        "sns.barplot(data=top_hot, y='prefecture', x='hot30max_ratio_trend_per_decade', ax=axes[1], palette='Oranges_r')\n"
        "axes[1].set_title('\\u6700\\u9ad8\\u6c17\\u6e2930\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387\\u306e\\u4f38\\u3073\\u304c\\u5927\\u304d\\u3044\\u90fd\\u9053\\u5e9c\\u770c \\u4e0a\\u4f4d15')\n"
        "axes[1].set_xlabel('\\u5897\\u52a0\\u5e45 (\\u6bd4\\u7387 / 10\\u5e74)')\n"
        "axes[1].set_ylabel('\\u90fd\\u9053\\u5e9c\\u770c')\n"
        "plt.tight_layout(); plt.show()\n\n"
        "pref_trend.sort_values('temp_trend_per_decade', ascending=False).head(20)\n"
    )
)

cells.append(md("## 7. \\u6625\\u30fb\\u79cb\\u306e\\u9ad8\\u6e29\\u5316\\u6bd4\\u8f03\\uff08\\u5168\\u56fd\\u30fb\\u30a8\\u30ea\\u30a2\\u5225\\uff09"))
cells.append(
    code(
        "spring_months = [3, 4, 5]\n"
        "autumn_months = [9, 10, 11]\n\n"
        "spring = station_daily[station_daily['month'].isin(spring_months)].copy()\n"
        "autumn = station_daily[station_daily['month'].isin(autumn_months)].copy()\n\n"
        "spring_national = spring.groupby('year', as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'), hot25_ratio=('hot25_flag', 'mean'), hot30max_ratio=('hot30max_flag', 'mean'))\n"
        "autumn_national = autumn.groupby('year', as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean'), hot25_ratio=('hot25_flag', 'mean'), hot30max_ratio=('hot30max_flag', 'mean'))\n\n"
        "fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=True)\n"
        "axes[0].plot(spring_national['year'], spring_national['temp_avg_c'], label='\\u6625(3-5\\u6708)', color='tab:green', lw=2)\n"
        "axes[0].plot(autumn_national['year'], autumn_national['temp_avg_c'], label='\\u79cb(9-11\\u6708)', color='tab:red', lw=2)\n"
        "axes[0].set_title('\\u5168\\u56fd \\u6625\\u30fb\\u79cb\\u306e\\u5e73\\u5747\\u6c17\\u6e29\\u63a8\\u79fb')\n"
        "axes[0].set_ylabel('\\u6c17\\u6e29 (\\u2103)')\n"
        "axes[0].legend()\n\n"
        "axes[1].plot(spring_national['year'], spring_national['hot25_ratio'], label='\\u6625 25\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387', color='tab:green', lw=2)\n"
        "axes[1].plot(autumn_national['year'], autumn_national['hot25_ratio'], label='\\u79cb 25\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387', color='tab:red', lw=2)\n"
        "axes[1].set_title('\\u5168\\u56fd 25\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387\\u306e\\u6625\\u79cb\\u6bd4\\u8f03')\n"
        "axes[1].set_ylabel('\\u6bd4\\u7387')\n"
        "axes[1].legend()\n\n"
        "axes[2].plot(spring_national['year'], spring_national['hot30max_ratio'], label='\\u6625 30\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387', color='tab:green', lw=2)\n"
        "axes[2].plot(autumn_national['year'], autumn_national['hot30max_ratio'], label='\\u79cb 30\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387', color='tab:red', lw=2)\n"
        "axes[2].set_title('\\u5168\\u56fd 30\\u2103\\u4ee5\\u4e0a\\u65e5\\u7387\\u306e\\u6625\\u79cb\\u6bd4\\u8f03')\n"
        "axes[2].set_ylabel('\\u6bd4\\u7387')\n"
        "axes[2].set_xlabel('\\u5e74')\n"
        "axes[2].legend()\n"
        "plt.tight_layout(); plt.show()\n\n"
        "def _season_trend(df, season_label):\n"
        "    rows = []\n"
        "    for region, g in df.groupby(['year', 'region'], as_index=False).agg(temp_avg_c=('temp_avg_c', 'mean')).groupby('region'):\n"
        "        slope = np.polyfit(g['year'], g['temp_avg_c'], 1)[0] * 10\n"
        "        rows.append({'region': region, 'season': season_label, 'temp_trend_per_decade': slope})\n"
        "    return pd.DataFrame(rows)\n\n"
        "trend_compare = pd.concat([\n"
        "    _season_trend(spring, '\\u6625(3-5\\u6708)'),\n"
        "    _season_trend(autumn, '\\u79cb(9-11\\u6708)')\n"
        "], ignore_index=True)\n\n"
        "plt.figure(figsize=(14, 6))\n"
        "sns.barplot(data=trend_compare, x='region', y='temp_trend_per_decade', hue='season', palette='Set2')\n"
        "plt.title('\\u30a8\\u30ea\\u30a2\\u5225 \\u6625\\u30fb\\u79cb\\u306e\\u6c17\\u6e29\\u30c8\\u30ec\\u30f3\\u30c9\\uff0810\\u5e74\\u3042\\u305f\\u308a\\uff09')\n"
        "plt.xlabel('\\u30a8\\u30ea\\u30a2')\n"
        "plt.ylabel('\\u4e0a\\u6607\\u5e45 (\\u2103 / 10\\u5e74)')\n"
        "plt.tight_layout(); plt.show()\n\n"
        "trend_compare.pivot(index='region', columns='season', values='temp_trend_per_decade').sort_values('\\u79cb(9-11\\u6708)', ascending=False)\n"
    )
)

cells.append(md("## 8. \\u5206\\u6790\\u7528CSV\\u3092\\u4fdd\\u5b58\\uff08cp932\\uff09"))
cells.append(
    code(
        "station_daily.to_csv('weather_station_daily_for_analysis.csv', index=False, encoding='cp932')\n"
        "pref_daily.to_csv('weather_prefecture_daily_for_analysis.csv', index=False, encoding='cp932')\n"
        "region_daily.to_csv('weather_region_daily_for_analysis.csv', index=False, encoding='cp932')\n"
        "national_daily.to_csv('weather_national_daily_for_analysis.csv', index=False, encoding='cp932')\n"
        "print('\\u4fdd\\u5b58\\u5b8c\\u4e86')\n"
    )
)

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = Path("weather_japan_trend_analysis.ipynb")
out.write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding="utf-8")
print(out.resolve())
