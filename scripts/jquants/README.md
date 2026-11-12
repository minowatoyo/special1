# J-Quants 取得・加工・全消去の手順

正本は J-Quants Standard。データは `data/jquants/`（git 管理外）にだけ置く。生の表は会話・レポートに出さない。

| 目的 | コマンド |
|---|---|
| 鍵を設定（ローカル PC） | `export JQUANTS_API_KEY=...`（Windows は `$env:JQUANTS_API_KEY="..."`）。クラウドのセッションでは環境の秘密情報が自動で置き換える |
| W3 の計画（通信なし） | `python scripts/jquants/backfill.py` |
| W3 の実取得（10 年分・再開可） | `python scripts/jquants/backfill.py --execute` |
| 加工後テーブルの作成 | `python scripts/jquants/build_processed.py`（要 pyarrow） |
| 全消去（解約時） | `sh scripts/jquants/purge.sh --yes`（データ・派生 DB・取得ログをすべて削除） |

- 生データ: `data/jquants/raw/<エンドポイント>/<取得日>/<ハッシュ>.json`。取得ログ: `data/jquants/_meta/fetch_log.csv`（URL・時刻・HTTP・バイト数・sha256。鍵は記録しない）。
- 加工後: `data/jquants/processed/*.parquet`（`prices_daily`、`quality_flags`、`listed_master`、`fins_summary`、`earnings_calendar`、`topix_daily`、`indices_daily`、空の `margin_interest`／`short_ratio`／`investor_types`／`sector_indices`）。
- モデル側は `forecastlib.jquants_adapter` だけを使う（読み取り専用）。
- 実測したレート: 日足系 110 回/分、財務サマリー 56 回/分で 429 なし。バックフィルは 100 回/分と 55 回/分に抑える。429 が出たら停止し、再実行で続きから。
- `JQUANTS_DATA_DIR` で置き場を変えられる。解約時は、その場所にも `purge.sh <場所> --yes` を実行する。
