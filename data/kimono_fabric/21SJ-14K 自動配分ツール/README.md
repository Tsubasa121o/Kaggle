# 21SJ-14K 自動配分ツール

21SJ-14Kの配分数を、重み付きスコアで自動計算するツールです。
CLI版とHTML(Web UI)版の両方を用意しています。

## フォルダ構成

- `allocator.py`: CLI版の自動配分本体
- `config/weights.json`: 重み設定
- `data/input/21SJ14K_allocation_input.csv`: 実運用データ格納用（Web版の既定入力）
- `data/input/21SJ14K_allocation_input_sample.csv`: サンプルデータ
- `data/output/`: CLI実行時の出力先
- `web/index.html`: HTML版UI
- `web/app.js`: HTML版ロジック
- `web/styles.css`: HTML版スタイル

## 入力CSVの列

- 必須列: `jan_code`
- 以下の別名列も自動認識
  - `JAN`, `JANコード`, `商品コード` -> `jan_code`
  - `商品名` -> `item_name`
  - `売上数量`, `販売数量`, `出荷数量` -> `sales_qty`
  - `在庫切れ日数`, `在庫ゼロ日数` -> `stockout_days`
  - `現在庫`, `在庫数` -> `current_stock`
  - `返品数量`, `返品数` -> `return_qty`
  - `最低配分数`, `最小配分数` -> `min_allocate`
  - `最大配分数` -> `max_allocate`

`min_allocate`/`max_allocate` は省略可能です。
省略時は `min=0`, `max=総配分数(total)` で処理します。

ヘッダなしCSV（先頭行が13桁JANから始まる8列データ）も読み込み可能です。  
その場合は列順を次にしてください:  
`jan_code,item_name,sales_qty,stockout_days,current_stock,return_qty,min_allocate,max_allocate`

## 重み設定

`config/weights.json` の `feature_weights` を編集します。

- 正の重み: 値が高いほど配分が増える
- 負の重み: 値が低いほど配分が増える
- Web版ではスライダー/数値入力で重みを直接調整できます
- Web版にはプリセット（バランス/売上重視/在庫圧縮重視）があります
- Web版は「重みの絶対値合計=1.000」になるまで実行できません
- 判定許容差は ±0.001 です（例: 0.999〜1.001 はOK）

`return_rate` を重みに入れた場合:

- `return_rate` 列があれば利用
- なければ `return_qty / sales_qty` を自動計算

### 各重みの意味（調整対象）

- `sales_qty`: 売上実績。プラスを上げると、売れているJANへ配分が寄ります。
- `stockout_days`: 在庫切れ日数。プラスを上げると、欠品期間が長いJANを優先します。
- `current_stock`: 現在庫。マイナスを強めると、在庫が少ないJANを優先します。
- `return_rate`: 返品率。マイナスを強めると、返品率が低いJANを優先します。

### プリセットの使い分け

- `バランス`: まず最初に使う基準設定。売上と在庫の両方をバランスします。
- `売上重視`: 実績上位を優先したいとき。短期売上の最大化を狙う用途向けです。
- `在庫圧縮重視`: 在庫偏りを抑えたいとき。欠品側に寄せたい用途向けです。

### 迷わない調整手順

1. まず `バランス` で計算
2. 配分上位10件を確認
3. 1回の変更は1項目だけ（0.05〜0.10）
4. 再計算して差分を見る
5. 意図通りなら確定、違うなら元に戻して別項目を調整

### 実行できないときの確認

- 画面に `NG（1.000に合わせてください）` が出る場合:
  - 重みの絶対値合計が1.000ではありません
  - 画面の「調整目安」表示に従って増減してください
- `重みの絶対値合計を1.000にしてください` エラー:
  - 実行直前チェックで弾かれています
  - 重みを修正して `OK` 表示にしてから再実行してください

## 入力データ抽出SQL（DBから一括作成）

`kimono_fabric/クエリ/21SJ-14K_自動配分入力データ一括抽出.txt` を実行すると、  
以下の8列を一括で出力します。

- `jan_code`
- `item_name`
- `sales_qty`
- `stockout_days`
- `current_stock`
- `return_qty`
- `min_allocate`
- `max_allocate`

出力結果をCSV保存し、`data/input/21SJ14K_allocation_input.csv` に配置して使ってください。

## HTML版の使い方（所定フォルダ運用）

1. 入力CSVを `data/input/21SJ14K_allocation_input.csv` に保存（同名で上書き）
2. ツールフォルダでローカルサーバを起動
3. `http://localhost:8000/web/` を開く
4. 「配分を計算する」を押す
5. 結果CSV/サマリTXTを保存

ローカルサーバ起動コマンド:

```powershell
cd "C:\Users\t.ouchi\OneDrive\デスクトップ\Github\Kaggle\data\kimono_fabric\21SJ-14K 自動配分ツール"
python -m http.server 8000
```

ダブルクリック起動:

- `start_web.bat` を実行（`http://localhost:8000/web/` を自動で開きます）

補足:

- `file://` 直開きでは固定パス読込ができません
- Web画面のCSVパス欄で別ファイル（例: `../data/input/別名.csv`）にも変更可能

## CLI版の使い方

```powershell
cd "C:\Users\t.ouchi\OneDrive\デスクトップ\Github\Kaggle\data\kimono_fabric\21SJ-14K 自動配分ツール"
python allocator.py --input data/input/21SJ14K_allocation_input.csv --weights config/weights.json --total 200
```

サンプルで試す場合:

```powershell
python allocator.py --input data/input/21SJ14K_allocation_input_sample.csv --weights config/weights.json --total 200
```

## CLI出力

- `data/output/allocation_result_YYYYMMDD_HHMMSS.csv`
- `data/output/allocation_result_YYYYMMDD_HHMMSS_summary.txt`
