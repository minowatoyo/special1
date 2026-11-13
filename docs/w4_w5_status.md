# W4・W5・FIX-05 の実装状況と実行手順

**実装とテスト（合成データ）は完了。J-Quants の実データでの実行は未実施**（データはローカル PC にある）。結果が出るまで、採否・モデルの既定変更はしない。

## 実装したもの
| 項目 | 場所 | 内容 |
|---|---|---|
| W4 追記専用の予測台帳（FIX-08） | `forecastlib/ledger.py`（`AppendOnlyLedger`） | ハッシュ連鎖（書き換えを検出。壊れた台帳には追記しない）。J-Quants 正本（`source="jquants"`）以外は拒否。データ目録・コード版・設定のハッシュが必須。採点は別の行で追記（予測の行は変えない）。置き場は `data/jquants/ledger/` |
| FIX-05 外側評価 | `forecastlib/outer.py` | 各ブロックの前に確定した損失だけで採用モデルを選び（余白 h 日）、そのモデルの外側の損失を連結。基準 B1・B0 との比較、全期間で選んだ場合との差（楽観の大きさ）を出す |
| W5 パネル・特徴量 | `selectlib/panel.py`、`features.py` | リバランス日（21 営業日ごと）、ラベル（T+1 始値→T+22 始値−TOPIX）、対象銘柄（内国普通株・市場区分・流動性・履歴）。SEL-A（9 特徴量）・SEL-B（6 特徴量）。先読みがないことをテスト |
| W5 モデル | `selectlib/model.py` | リッジ（α=1.0 固定、平均損失の形で標本数に依存しない）、LightGBM（任意）。k−1 期のラベルは k で使わない（テスト） |
| W5 執行台帳 | `selectlib/portfolio.py` | 現物・買いのみ・100 株単位・全売却→再購入。分割をまたぐ換算、ストップ高で買えない、ストップ安・売買なしの売却繰り延べ（最大 5 日、強制評価）。円単位で整合（3 ケースのテスト） |
| W5 評価 | `selectlib/evalsel.py` | 逆ボラ重み（上限 2 倍）、TOPIX ボラの現金ゲート、年率超過収益、上位 3 期間を除く頑健性、暦年別、採用ゲートの機械的な判定、DSR、PBO（CSCV） |
| 実行 | `scripts/w5/run_selection.py`、`scripts/w5/forecast_tools.py` | 下記 |

## ローカルでの実行（`git pull` のあと、リポジトリのフォルダで）
```
python -m pip install pandas numpy pyarrow lightgbm
python scripts/w5/run_selection.py                    # W5。試行は data/jquants/ledger/trials.jsonl に追記。集計は data/jquants/results/w5/summary.json
python scripts/w5/forecast_tools.py outer --n 30      # FIX-05。流動性上位 30 銘柄（約 10〜30 分）
python scripts/w5/forecast_tools.py forecast 7203 5802   # W4。最新日の予測を台帳へ
python scripts/w5/forecast_tools.py score 7203 5802      # 期日後の採点
```
出力は集計のみ。結果を貼ってください（生の表は不要）。

## 注意（結果の読み方）
- **評価期間が短い**: 既定は 2022-04-04 以降のプライム・スタンダードだけ（旧区分の案は未確定）。リバランスは約 50 回で、学習の最初の 12 回を除くと約 40 回。統計的な力は弱く、DSR・PBO も不安定。旧区分の案を使うと期が増えるが、仕様変更の確定が先。
- σ̂ の簡易版: 逆ボラの σ̂ は、forecastlib の S3 ではなく、EWMA と 22 日 GKYZ の幾何平均の簡易版。
- 全売却→再購入のため、同じ銘柄を続けて持つ場合もコストを 2 回払う（保守的）。
- 採用の判断は利用者。ゲートの機械的な判定は参考。
- FIX-09 (3): リッジ罰則は平均損失の形で標本数に依存しない（テスト済み）。パネルでの検証（標本数・欠損・日付の重みが変わったときの実効的な強さ）は、上の実行結果を見てから。
- FIX-09 (2): 標本内残差の過小評価は、外側評価の結果と並べて診断する（未実施）。
