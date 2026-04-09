# Query Inventory

## 1. 参照用クエリ（`reference\query_source\クエリ` 配下）
| ファイル | 主用途 | 粒度 | 主テーブル | 主条件 |
|---|---|---|---|---|
| `reference\query_source\クエリ\21SJ-14K_JAN探索_横断クエリ.txt` | 21SJ-14K関連JANの探索 | JAN | SMS, SYKD, HACD | 型番/商品名に21SJ-14K |
| `reference\query_source\クエリ\21SJ-14K_JAN別_発注日_発注数量.txt` | 発注推移 | JAN×発注日 | HACD, HACH | target_jan(60件) |
| `reference\query_source\クエリ\21SJ-14K_JAN別_入荷日_入荷数量.txt` | 入荷推移 | JAN×入荷日 | NYKD, NYKH | target_jan(60件) |
| `reference\query_source\クエリ\21SJ-14K_JAN別_発注入荷_縦持ち.txt` | 発注/入荷イベント時系列 | JAN×日付×種別 | HACD/HACH + NYKD/NYKH | target_jan(60件), UNION ALL |
| `reference\query_source\クエリ\21SJ-14K_JAN別_発注残数_発注No連携.txt` | 発注残分析 | 発注明細/ JAN集計 | HACD/HACH + NYKD/NYKH + SMS | from_yyyymmdd=20210101 |
| `reference\query_source\クエリ\21SJ-14K_自動配分入力データ一括抽出.txt` | 配分ツール入力生成 | JAN | SYKD, HACD/HACH, NYKD/NYKH, SMS, ZMSN | model=21SJ-14K, 452% |
| `reference\query_source\クエリ\JANコード別_発注日_発注数量.txt` | 金襴37JANの発注推移 | JAN×発注日 | HACD, HACH | 20240101以降 + IN(37件) |
| `reference\query_source\クエリ\JAN_発注No_備考_抽出.txt` | 発注Noと備考抽出 | JAN×発注No | HACD, HACH | 20240101以降 |
| `reference\query_source\クエリ\金襴ジャケットのみソート.txt` | 金襴37JAN売上明細 | 売上明細行 | SYKD, SYKH, TMS, CMS, SMS, EMS | 20240101以降 + IN(37件) |
| `reference\query_source\クエリ\NB-1_22SJ-3_売上日次地域別_相関分析用.txt` | NB-1/22SJ-3日次地域別分析 | 売上日×地域×JAN | SYKD, SYKH, SMS, TMS, EMS | 20130101-20991231 |

## 2. 分析派生クエリ（`reference\query_source\21SJ-14K 分析` 配下）
| ファイル | 内容 | 備考 |
|---|---|---|
| `21SJ-14K_JAN別_発注日_発注数量_452限定.txt` | 56件452JAN限定の発注推移 | 正本の限定版 |
| `21SJ-14K_JAN別_入荷日_入荷数量_452限定.txt` | 56件452JAN限定の入荷推移 | 正本の限定版 |
| `21SJ-14K_JAN別_発注入荷_縦持ち_452限定.txt` | 56件452JAN限定イベント縦持ち | 正本の限定版 |
| `21SJ-14K_JANリスト反映_売上明細_全得意先_452限定_2013以降.txt` | 売上明細(452限定) | 正本の用途特化版 |
| `21SJ-14K_JAN別_発注残数_発注No連携.txt` | 発注残分析 | 正本と同等ロジック |

## 3. JAN件数の固定値（2026-04-08確認）
- 金襴系 IN リスト: 37件
  - 出典: `reference\query_source\クエリ\金襴ジャケットのみソート.txt`
  - 同一リスト利用: `reference\query_source\クエリ\JANコード別_発注日_発注数量.txt`
- 21SJ-14K 全target_jan: 60件
  - 出典: `reference\query_source\クエリ\21SJ-14K_JAN別_発注日_発注数量.txt`
- 21SJ-14K 452限定: 56件
  - 出典: `reference\query_source\21SJ-14K 分析\21SJ-14K_JAN別_発注日_発注数量_452限定.txt`

## 4. 正本選定ルール
- まず `reference\query_source\クエリ` をベースにする
- 分析版条件（452限定等）が必要なら該当SQLを参照し新規作成する
- 作成物は `query_output` に保存し、参照元コピーは変更しない
