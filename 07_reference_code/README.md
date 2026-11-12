# 参考実装（検証用）— chartlib と forecastlib

> 要約: 文書（`../01_techniques/`）に書かれた計算式を、pandas のコードとして動かして確かめるための小さな参考実装。
> 主要指標を TA-Lib と数値照合し、平滑化・初期値・ルックバックの「流儀の違い」を実測で明らかにした。
> `forecastlib` は、日足から確率つきの予測（価格の分位点、水準に届く確率）を作り、同じ銘柄の過去で採点するための実装で、手順は `../09_forecasting/02_protocol.md` に事前登録してある。
> **本番の売買システム用ではない**（教育・検証用）。投資助言でもない。
> 最終更新: 2026-11-11

## 何のためにあるか

テクニカル指標の解説は、同じ名前でも計算の流儀が違う（RSI の平滑化、ADX の初期化、EMA の初期値、標準偏差の自由度…）。
文書の数式を鵜呑みにせず、(1) 定義どおりに書いたコードを TA-Lib と突き合わせ、(2) 手計算の例や数学的性質で確かめ、
(3) 先読み（未来のデータの混入）がないことを機械的に検査した。バックテストを自作するときの土台・チェック方法の見本でもある。

## 使い方

```bash
cd 07_reference_code
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest              # 154 件（chartlib 119、forecastlib 35。TA-Lib 未導入なら照合テストは skip）
python examples/demo_chart.py # 合成データのチャート PNG を examples/ に出力
```

```python
import pandas as pd
from chartlib import indicators as ind, candles, swings

df = pd.read_csv("prices.csv", index_col=0, parse_dates=True)   # 列: open, high, low, close, volume
rsi14  = ind.rsi(df.close, 14)                                   # ワイルダー平滑
macd   = ind.macd(df.close, 12, 26, 9)                           # DataFrame: macd / signal / hist
bb     = ind.bollinger(df.close, 20, 2.0)                        # upper / middle / lower / percent_b / bandwidth
ichi   = ind.ichimoku(df.high, df.low, df.close)                 # chikou 列は先読みを含む（後述）
pivots = swings.zigzag(df.high, df.low, threshold=0.05)          # 確定足 confirmed_pos 付き
```

## 構成

| パス | 内容 |
|---|---|
| `chartlib/indicators.py` | 移動平均・モメンタム・ボラティリティ・トレンド強度・出来高系・一目均衡表・平均足・ピボット・窓 |
| `chartlib/candles.py` | ローソク足の基本量と、単純化したパターン判定（しきい値は引数） |
| `chartlib/swings.py` | スイング高安（フラクタル型）とジグザグ。**確定足つき**で先読みを防ぐ |
| `tests/test_vs_talib.py` | TA-Lib との数値照合（NaN の位置＝ルックバックも含め一致を要求） |
| `tests/test_causality.py` | 先読みなしの検査（時点 k で打ち切っても過去の値が変わらない） |
| `tests/test_properties.py` | 手計算の例・定義どおりの愚直実装・数学的性質による検証 |
| `tests/test_candles_swings.py` | 手作りの足によるパターン判定、既知の経路でのスイング検出 |
| `examples/demo_chart.py` | 合成データを描画（日本式配色: 陽線=赤・陰線=青）。生成済み PNG も同梱 |
| `forecastlib/data.py` | 日足 CSV の読み込み（Stooq・Yahoo・日本語の列名）、検査、分割の未調整の検出と調整 |
| `forecastlib/vol.py` | ボラティリティの予測（EWMA、レンジ系の分散を使う HAR 型の対数回帰、両者の結合） |
| `forecastlib/features.py` | 特徴量 15＋3 個（σ 単位に直して標準化）と、チャートシグナル 41 個（chartlib の指標を使う） |
| `forecastlib/walkforward.py` | ウォークフォワード。候補モデル 10 個の予測分布を毎日作って採点する。他銘柄とのプール推定 |
| `forecastlib/stats.py` | CRPS・ピンボール損失、Diebold–Mariano 型の検定、定常ブートストラップ、Reality Check、偽発見率、Newey–West 回帰 |
| `forecastlib/evaluate.py` | 成績表、事前登録した採否ルール（1 銘柄・複数銘柄）、ボラティリティ予測と水準到達確率の採点 |
| `forecastlib/eventstudy.py` | チャートシグナルのイベントスタディ（逆回帰による検定、偽発見率の補正） |
| `forecastlib/forecast.py` | 最終日の予測（価格の分位点、水準に届く確率、期間中の高値・安値、過去の似た局面、補助系列との連動） |
| `forecastlib/report.py`・`ledger.py` | レポート（Markdown と図）の出力、予測台帳への記録と期日後の採点 |
| `forecastlib/synth.py` | 検証用の合成データ（ボラティリティ変動と厚い裾。予測できる成分は指定したときだけ入れる） |
| `tools/forecast_report.py` | 日足 CSV からレポートを作るコマンド |
| `examples/forecast_selfcheck.py` | 合成データによる自己検査（偽陽性、検出力、区間の的中率） |
| `tests/test_forecast_*.py` | forecastlib のテスト（先読みなし、読み込みと分割検出、統計関数、採否、予測の整合、台帳、レポート） |

## forecastlib の使い方

```bash
python tools/forecast_report.py --csv toyota.csv --name "トヨタ自動車 (7203)" --out out/7203 --today 2026-11-11
#   --aux nikkei=nikkei.csv:0 --aux usdjpy=usdjpy.csv:1   補助系列（0 = 同じ取引時間、1 = 前日までの値だけを使う）
#   --panel a.csv b.csv ...                               他銘柄（傾きのプール推定と、複数銘柄での採否判定）
#   --scenarios scen.json --levels 3100,3550              区間・水準ごとの確率
#   --split 2021-09-29:5 / --auto-split                   未調整の分割の調整
#   --ledger ledger.csv                                   予測台帳に記録
python examples/forecast_selfcheck.py --out selfcheck_out --quick   # 自己検査（小さい設定で数分）
```

出力は `report.md`（結論、データの検査、予測分布、水準に届く確率、検証、イベントスタディ、過去の似た局面、限界）、`forecast.json`、図 2 枚、表の CSV。
考え方は `../09_forecasting/01_method_review.md`、固定した数値と採否の基準は `../09_forecasting/02_protocol.md` にある。要点は次のとおり。

- 予測分布は「過去平均の傾き ＋ ボラティリティの予測 × 標準化した過去のリターンの経験分布」。方向の材料（傾き・類似局面）は、多重検定の補正を含む採用基準を通ったときだけ使う。
- **すべて先読みなし**。系列を途中で打ち切っても過去の予測分布が変わらないこと、将来の価格（自分と他銘柄）を書き換えても過去の予測が変わらないことをテストで確かめている。
- テストの検出力は、先読みや計算の誤りをわざと入れた複製 14 通りで確かめ、**14 件すべてテストが失敗**した。
- 自己検査（合成データ）の結果は `../09_forecasting/02_protocol.md` の 7 節。予測できる成分のないデータで方向の材料を誤って採用しないこと、区間の的中率が名目に合うことを確かめた。

## TA-Lib との照合結果（合成データ 1500 本・固定シード）

| 区分 | 指標 | 結果 |
|---|---|---|
| **完全一致**（相対誤差 1e-9、NaN の位置も一致） | SMA / EMA / WMA / VWMA / DEMA / TEMA / KAMA / HMA（√n 切り捨て）/ RMA（＝ワイルダー平滑）/ VWAP（起点からの累積）、RSI(ワイルダー)、CCI、ウィリアムズ%R、ROC、MOM、アルティメット・オシレーター、MFI、ボリンジャー(ddof=0)、TR / ATR / NATR、+DI / −DI / DX / ADX（`variant="talib"`）、パラボリック SAR、アルーン、OBV、A/D ライン | TA-Lib と同じ値 |
| **一致（出力の開始位置のみ TA-Lib 仕様）** | ストキャスティクス（STOCH / STOCHF）、MACD | 値は一致。TA-Lib は複数出力を「最後に有効になる系列」の開始位置にそろえて返す。MACD は速い EMA の初期値が TA-Lib と異なるため、初期の差が消えた 400 本目以降で比較 |
| **初期化の違いが減衰して一致** | TRIX（600 本目以降で比較）、ワイルダー原典の DMI（`variant="wilder"`）→ TA-Lib 版へ収束 | 初期差は (1−α)^k で指数的に減衰 |
| **EMA を最初の値で初期化すれば一致** | チャイキン・オシレーター（ADOSC） | `ema(..., seed="first")` で TA-Lib と一致 |
| **TA-Lib に対応物なし → 手計算・性質で検証** | 日本式ストキャスティクス、一目均衡表、平均足、ピボット、窓、ドンチャン、ケルトナー、CMF、フォース・インデックス、ジグザグ、スイング検出、ローソク足パターン | 愚直実装との照合・解析的に分かる例・不変条件（`tests/test_properties.py` ほか） |

テスト自体の検出力は、数式や符号をわざと壊した複製 8 通り（ボリンジャー ddof、RSI の平滑化差替え、一目均衡表のシフト量、
SMA の中心化＝先読み、SAR の初期方向、ジグザグの確定足、TR 定義、ピボット式）で確認し、**8 件すべてテストが失敗**した。

## 実測で分かった「流儀の違い」（文書との突き合わせ用）

| 項目 | 流儀A | 流儀B | 本実装・TA-Lib |
|---|---|---|---|
| RSI の平滑化 | ワイルダー平滑（最初の n 個の単純平均で初期化、以後 (前値×(n−1)+今値)/n） | 単純移動平均（Cutler） | `method="wilder"` が TA-Lib と一致。`"cutler"` は別物（実測で RSI が 1pt 超ずれる） |
| ADX/DMI の初期化 | ワイルダー原典: 最初の n 個の合計を初期値 | TA-Lib: 最初の n−1 個の合計に平滑を 1 回かけて初期値 | 差は 14 期間で初期に約 0.3 pt、400 本後には 1e-7 未満。`variant` で切替 |
| EMA の初期値 | 最初の n 個の単純平均 | 最初の値（pandas `ewm(adjust=False)`） | `seed="sma"` が TA-Lib、`"first"` が pandas と一致 |
| ボリンジャーの標準偏差 | 母集団（ddof=0）— 原典・TA-Lib | 標本（ddof=1）— 実装により異なる | バンド幅が √(n/(n−1)) 倍違う（n=20 で約 2.6%）。`ddof` で切替 |
| ストキャスの定義 | 欧米: Slow %K = SMA(Fast %K, 3)、Slow %D = SMA(Slow %K, 3) | 日本（野村證券の定義など）: %D = Σ(C−最安値)／Σ(最高値−最安値)（分子・分母を m 日ずつ合計してから割る）、SD = %D の移動平均 | 近いが**別物**（分母のレンジが日々変わるため。手計算例で約3pt差）。`stochastic()` が欧米式、`stochastic_jp()` が日本式 |
| TA-Lib の複数出力 | 各系列が計算可能になった位置から | 最後に有効になる系列の位置にそろえる | TA-Lib は後者（STOCH の slowk など）。比較時に注意 |
| 一目均衡表のシフト本数 | MT4/MT5: 26本先／26本前（`displacement=26`、既定） | 日本の数え方（本日を含め26日）・TradingView: 25本（`displacement=25`） | 雲・遅行スパンの位置が1本ずれる。ソフトの表示と合わない時は最初にここを疑う（詳細と出典は `../02_japan/02_ichimoku_kinko_hyo.md` §3.1） |
| HMA の √n の丸め | 切り捨て（TA-Lib 0.8.3、Pine の一部実装） | 四捨五入する実装もある | n=14, 21 などで最大約 1pt 違う。本実装は切り捨て（`tests/test_vs_talib.py` で n=9/14/21 を照合） |
| 平坦な系列の RSI（分母 0） | 50 を返す（TA-Lib 0.8.3 で実測） | NaN や 0（実装による） | 本実装は定義不能として NaN。値動きのない銘柄（売買の薄い小型株など）では表示ツールごとに値が違いうる |

## 先読み（look-ahead）について

- **すべての指標は因果的**（計算に未来を使わない）。`tests/test_causality.py` が、時点 300/700/1100 で打ち切った結果が全期間計算の先頭と一致することを検査する。この検査は自作の指標・シグナルにもそのまま使える。
- **例外は一目均衡表の `chikou`（遅行スパン）**: 描画位置 t の値は将来の終値 `close[t+26]` であり、シグナル判定に使うと先読みになる。判定には `close` と `close.shift(26)` を比べる（「今日の終値が 26 日前の株価を上回る」）。`senkou_a` / `senkou_b` は「その日に描かれている雲」（26 本前に計算した値）で先読みを含まない。未来側の雲（最新日より先）は返さない。
- **転換点（スイング・ジグザグ）は確定が遅れる**: 高値・安値は「その後に反転が起きた」と分かって初めて確定する。`confirmed_pos`（確定した足）より前の足でその転換点を使うと先読みになる。チャートパターン（ダブルトップ、ヘッド＆ショルダーズ等）のバックテストで最も起きやすい誤りなので、必ず確定足を基準にエントリー判定すること。

## 限界

- ローソク足パターンは本資料集の定義を単純化したもの。TA-Lib の `CDL*` は「直近の平均的な実体・影の長さ」に対する相対判定を使うため、結果は一致しない（一致を主張しない）。
- forecastlib の検証も合成データによる。実データでの予測の確度は、日足を入れて採点し、さらに予測台帳で期日後に採点して初めて分かる。
- 検証は合成データ（幾何ランダムウォーク）のみ。**実市場データでの有効性は何も保証しない**。欠損・出来高ゼロ・ストップ高張り付き・株式分割などの実務上の扱いは含まない（`../02_japan/04_tse_market_rules_and_chart_effects.md` 参照）。
- 性能は考慮していない（Python ループが多い）。大量データには TA-Lib / numba / ベクトル化を検討する。
- TA-Lib との一致は「TA-Lib が正しい」ことを意味しない。流儀が同じことを示すだけである。ツールや証券会社の表示と値がずれるときは、上表の流儀の違いをまず疑う。
- 依存パッケージの版は 2026-11-09 時点の実測（`requirements.txt`）。`mplfinance 0.12.10b0` は `six` を依存宣言していないため明示した。

## 関連文書

- [../01_techniques/06_moving_averages.md](../01_techniques/06_moving_averages.md) / [07_oscillators_momentum.md](../01_techniques/07_oscillators_momentum.md) / [08_volatility_and_trend_strength.md](../01_techniques/08_volatility_and_trend_strength.md) / [09_volume_breadth_sentiment.md](../01_techniques/09_volume_breadth_sentiment.md)
- [../02_japan/02_ichimoku_kinko_hyo.md](../02_japan/02_ichimoku_kinko_hyo.md)
- [../05_tools_data_code/03_python_libraries.md](../05_tools_data_code/03_python_libraries.md)
