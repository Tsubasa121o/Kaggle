# JAN List Management

## 1. 管理対象
本案件で固定管理するJANリストは次の3種類。

1. 金襴ジャケット37件
2. 21SJ-14K全対象60件（先頭4件は 000... 系を含む）
3. 21SJ-14Kの452限定56件

## 2. 保存先
- `lists\jan_list_kinran_37.txt`
- `lists\jan_list_21sj14k_full_60.txt`
- `lists\jan_list_21sj14k_452_only_56.txt`

## 3. 再生成方針
上記3ファイルは、`reference\query_source` のSQLから抽出して作る。
手入力で増減させない。

## 4. 再生成コマンド（PowerShell）
```powershell
$root = 'C:\Users\t.ouchi\OneDrive\デスクトップ\Github\Kaggle\data\データセット\codex_query_handover'
$out = Join-Path $root 'lists'

$rules = @(
  @{src='reference\query_source\クエリ\金襴ジャケットのみソート.txt'; out='jan_list_kinran_37.txt'},
  @{src='reference\query_source\クエリ\21SJ-14K_JAN別_発注日_発注数量.txt'; out='jan_list_21sj14k_full_60.txt'},
  @{src='reference\query_source\21SJ-14K 分析\21SJ-14K_JAN別_発注日_発注数量_452限定.txt'; out='jan_list_21sj14k_452_only_56.txt'}
)

foreach ($r in $rules) {
  $text = Get-Content -Raw (Join-Path $root $r.src)
  $codes = [regex]::Matches($text, "'([0-9]{13})'") |
    ForEach-Object { $_.Groups[1].Value } |
    Select-Object -Unique
  Set-Content -Path (Join-Path $out $r.out) -Value $codes -Encoding UTF8
}
```

## 5. 同期ルール
- 参照SQLのINリストを変更したら、同日中に `lists` を再生成する
- 変更理由（追加/削除理由）は changelog に記録する
- 件数が変わったら、03_QUERY_INVENTORY.md の件数記述も更新する

## 6. 注意点
- JANは13桁文字列で保持（数値化しない）
- 並び順が意味を持つ依頼があるため、順序は維持
- CSV/Excelへ貼る時に先頭ゼロ欠落しないよう文字列扱いに固定
