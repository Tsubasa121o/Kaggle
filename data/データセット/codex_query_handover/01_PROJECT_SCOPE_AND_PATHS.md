# Project Scope And Paths

## 1. 目的
旧 kimono_fabric 案件で使っていたDBクエリ作成情報をこのフォルダへ集約し、
次回Codexでも同じ品質でSQLを作るための作業基盤を作る。

## 2. ルート
- 引き継ぎルート: `C:\Users\t.ouchi\OneDrive\デスクトップ\Github\Kaggle\data\データセット\codex_query_handover`
- 参照用クエリ正本コピー: `...\reference\query_source\クエリ`
- 参照用分析派生クエリ: `...\reference\query_source\21SJ-14K 分析`
- テーブル定義書: `...\reference\table_definitions`
- 参考コンテキスト: `...\reference\context`
- 新規SQL出力先: `...\query_output`

## 3. 参照資料（クエリ作成時の優先度順）
1. `reference\table_definitions\【使うテーブルのみ】PCA_商魂商管_テーブル定義書.xlsx`
2. `reference\table_definitions\【全部一通り解析】PCA_商魂商管_テーブル定義書 .xlsx`
3. `reference\query_source\クエリ\*.txt`
4. `reference\query_source\21SJ-14K 分析\*.txt`
5. `reference\context\次回依頼用_DB解析プロンプト.txt`

## 4. 今回の固定スコープ
- DBクエリ作成
- 既存クエリの再利用・改修
- JAN条件・期間条件・集計粒度の明示

## 5. スコープ外（混ぜない）
- BIアプリUI実装そのもの
- Notebook可視化実装の詳細
- モデル学習ロジックの改造

## 6. 重要な運用前提
- コード項目は固定長文字が多く、空白混在を想定する
- 日付は `int(yyyymmdd)` カラム運用が中心
- 数量は `money` のため、演算時は必要に応じて `decimal` へ明示変換
- 発注残計算は「発注No + JAN」で発注と入荷を対応させる

## 7. 正本方針
- 参照元としては `reference\query_source\クエリ` を正本コピーとして扱う
- 新規作成SQLは `query_output` に保存する
- 条件変更時は新規ファイル化し、参照元コピーを直接上書きしない
