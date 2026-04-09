# Change Log Template

## 記録ルール
- SQLを新規作成/更新したら必ず1行以上記録
- 「何を」「なぜ」「どこを」変更したかを残す
- JAN件数変更時は件数も記録

## テンプレート
```text
Date: YYYY-MM-DD
Author: <name or codex>
Request: <依頼概要>
Files Added:
- <absolute path>
Files Updated:
- <absolute path>
Key Changes:
- <変更点1>
- <変更点2>
Validation:
- <再読込確認 / 件数確認 / 粒度確認>
Notes:
- <必要時のみ>
```

## Initial Entry
Date: 2026-04-08
Author: codex
Request: DBクエリ作成情報を引き継ぎ可能な専用フォルダへ再編
Files Added:
- codex_query_handover フォルダ配下のドキュメント一式
- lists\jan_list_kinran_37.txt
- lists\jan_list_21sj14k_full_60.txt
- lists\jan_list_21sj14k_452_only_56.txt
Key Changes:
- クエリ作成の参照情報をSOP/辞書/台帳に分離
- 次回用プロンプトを完全版で固定化
- JANリストを既存SQLから抽出して固定ファイル化
Validation:
- 参照元SQLからJAN件数を再計測（37/60/56）
- 新規ファイル作成を確認
Notes:
- 以後のSQL追加時はこの形式で追記

Date: 2026-04-08
Author: codex
Request: kimono_fabric非依存化（データセット配下で自己完結化）
Files Added:
- reference\table_definitions\【使うテーブルのみ】PCA_商魂商管_テーブル定義書.xlsx
- reference\table_definitions\【全部一通り解析】PCA_商魂商管_テーブル定義書 .xlsx
- reference\query_source\クエリ\*.txt
- reference\query_source\21SJ-14K 分析\*.txt
- reference\context\*.txt, *.xlsx
- query_output\ (directory)
Files Updated:
- 00_START_HERE.txt
- 01_PROJECT_SCOPE_AND_PATHS.md
- 03_QUERY_INVENTORY.md
- 04_JAN_LIST_MANAGEMENT.md
- 05_QUERY_AUTHORING_SOP.md
- 07_NEXT_CODEX_PROMPT_FULL.txt
- 08_CHANGELOG_TEMPLATE.md
Key Changes:
- 参照資産（定義書/既存SQL/補助文書）をフォルダ配下へコピー
- 参照先パスを kimono_fabric 依存からデータセット配下へ切替
- 新規SQL保存先を `query_output` に統一
Validation:
- 参照ファイルの存在確認
- JANリスト件数（37/60/56）を維持
Notes:
- 今後はこのフォルダ単体で運用可能
