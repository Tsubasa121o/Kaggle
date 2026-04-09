# Table Join Dictionary

## 1. 頻出テーブル
| テーブル | 役割 | 主要キー/列 | 備考 |
|---|---|---|---|
| `HACH` | 発注ヘッダ | `hach_id`(PK), `hach_jno`(発注No), `hach_jucbi`(発注日), `hach_tcd`(発注先コード) | 発注明細の親 |
| `HACD` | 発注明細 | `hacd_hid`(=HACH.hach_id), `hacd_seq`, `hacd_scd`(JAN), `hacd_suryo`(発注数量) | JAN×発注日分析の主軸 |
| `SYKH` | 売上ヘッダ | `sykh_id`(PK), `sykh_jtan`(担当区分) | 売上明細の親 |
| `SYKD` | 売上明細 | `sykd_hid`(=SYKH.sykh_id), `sykd_uribi`(売上日), `sykd_scd`(JAN), `sykd_tcd`(得意先コード), `sykd_suryo` | 負数数量は返品として扱うケースあり |
| `NYKH` | 入荷ヘッダ | `nykh_id`(PK), `nykh_uribi`(入荷日), `nykh_mjno`(発注No対応) | 入荷明細の親 |
| `NYKD` | 入荷明細 | `nykd_hid`(=NYKH.nykh_id), `nykd_scd`(JAN), `nykd_suryo`(入荷数量) | 発注残計算で使用 |
| `SMS` | 商品マスタ | `sms_scd`(JAN), `sms_mei`, `sms_kikaku`, `sms_color`, `sms_size` | JAN探索や名称補完 |
| `TMS` | 得意先マスタ | `tms_tcd`, `tms_cmsid`, `tms_tkbn1`, `tms_tkbn2`, `tms_tkbn4` | 地域/業種コード接続 |
| `CMS` | 得意先名称 | `cms_id`, `cms_mei1` | 得意先名表示 |
| `EMS` | 区分名称マスタ | `ems_id`, `ems_kbn`, `ems_str` | コード名称化 |
| `ZMSN` | 在庫系 | `zmsn_scd`(JAN), `zmsn_zai`(在庫) | 自動配分入力SQLで使用 |

## 2. 既知の標準JOIN
```sql
-- 発注
HACD.hacd_hid = HACH.hach_id

-- 売上
SYKD.sykd_hid = SYKH.sykh_id

-- 入荷
NYKD.nykd_hid = NYKH.nykh_id

-- 発注と入荷の突合（発注残計算）
HACH.hach_jno = NYKH.nykh_mjno   -- 実装上は po_no 別名で扱う
```

## 3. マスタ名称付与JOIN
```sql
-- 商品名補完
RTRIM(detail.scd) = RTRIM(SMS.sms_scd)

-- 得意先名
RTRIM(SYKD.sykd_tcd) = RTRIM(TMS.tms_tcd)
TMS.tms_cmsid = CMS.cms_id

-- 区分名称（例）
RTRIM(TMS.tms_tkbn1) = RTRIM(EMS.ems_kbn) AND EMS.ems_id = 11  -- 県別地域
RTRIM(TMS.tms_tkbn2) = RTRIM(EMS.ems_kbn) AND EMS.ems_id = 13  -- 業種
RTRIM(TMS.tms_tkbn4) = RTRIM(EMS.ems_kbn) AND EMS.ems_id = 14  -- 区分
```

## 4. 日付列の意味（int yyyymmdd）
- `HACH.hach_jucbi`: 発注日
- `SYKD.sykd_uribi`: 売上日
- `NYKH.nykh_uribi`: 入荷日

表示用のみ文字列化:
```sql
RTRIM(CAST(h.hach_jucbi AS VARCHAR(8))) AS 発注日
```

## 5. 数量列の扱い
- `hacd_suryo`, `nykd_suryo`, `sykd_suryo` は集計対象
- 発注残計算は decimal へキャストして差分を取る
- 売上では `sykd_suryo < 0` を返品として分離するケースあり

## 6. 文字列コード比較の基本
- 固定長文字の空白混入を想定して `RTRIM` を標準化
- JAN比較・JOIN時に `RTRIM` を付与

## 7. 再利用時の注意
- `ems_id` の意味を変えると名称列の意味が崩れる
- 発注残は `発注No + JAN` の両方で対応させる（片方だけで突合しない）
- 集計粒度を変えるとBI出力と突合不能になるため、粒度を明示して保存する
