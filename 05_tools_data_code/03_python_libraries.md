# Python ライブラリ（データ・指標・可視化・検証）の実測カタログ
> 要約: データ取得・指標計算・可視化・パターン検出・パフォーマンス評価・テストに使う Python パッケージ 33 件を、PyPI の JSON API で実測した値（最新版・リリース日・ライセンス・requires_python）で整理した。
> 参照実装向けに pandas / numpy / TA-Lib / mplfinance / matplotlib / pytest の 6 点を Python 3.13.18（Linux x86_64）で実際に導入して動作確認した結果を載せる。mplfinance は宣言されていない依存（six）が必要という実測上の落とし穴があった。
> 依存衝突（pandas-ta の numba 固定、zipline-reloaded の pandas<3 など）と、最終リリースが 2 年以上前のパッケージの注意も記す。取得日 2026-11-09、要再確認。
> 最終更新: 2026-11-09

## 1. 調査方法と読み方

- 取得: `curl https://pypi.org/pypi/<package>/json` を 2026-11-09 に実行し、`info` の version・requires_python・license・classifiers・project_urls、`urls` の upload_time_iso_8601・filename、README 本文（`info.description`）を読んだ。出典表の URL 列は各パッケージの Homepage／Project URL。
- 「最新版リリース日」は最新版のファイルのうち最も早いアップロード日（UTC）。最終リリースから 730 日以上経過したものは年数を括弧で示し【保守注意】を付けた（古い＝使えないではないが、pandas・numpy の更新に追随していない可能性がある）。
- 「3.13」列: **W** = cp313 または abi3 の wheel あり／**P** = 純 Python wheel（py3-none-any）あり／**△** = wheel はあるが cp313 向けは無い（sdist からビルド）／**S** = sdist のみ（ビルドが必要）。
- 「実測」は本セッションのサンドボックス（Linux x86_64、Python 3.13.18、pip 26.2.2）で `pip install` と合成データでの最小実行を行った 1 回の観測であり、他 OS・実データ・全 API の保証ではない [TL-236]。

## 2. 参照実装向け: Python 3.13 での 6 パッケージ

| パッケージ | PyPI 最新版 | requires_python | pip が選んだ配布物（Linux x86_64） | 実測結果 |
|---|---|---|---|---|
| pandas | 3.1.1 | >=3.11 | cp313 manylinux_2_24／2_28 wheel | 導入・import とも成功 |
| numpy | 2.5.4 | >=3.12 | cp313 manylinux_2_27／2_28 wheel | 成功 |
| TA-Lib | 0.8.3 | >=3.9 | `ta_lib-0.8.3-cp313` manylinux2014 wheel | 成功。システムに TA-Lib の C ライブラリが無い環境で import でき、拡張モジュールは約 11.5 MB の単一 `.so` |
| mplfinance | 0.12.10b0 | 未指定 | py3-none-any | **初回は `six` 不足で ImportError**（`mplfinance/_utils.py` が `six.moves` を import）。`six` 1.17.0 を追加後、ローソク足＋移動平均＋出来高の PNG 保存に成功 |
| matplotlib | 3.11.2 | >=3.11 | cp313 manylinux2014 wheel | 成功 |
| pytest | 9.2.0 | >=3.10 | py3-none-any | 成功（ダミーテスト 1 件が通過） |

- 一括導入 `python -m pip install pandas numpy TA-Lib mplfinance matplotlib pytest six` は解決できた（python-dateutil 4.0.0・tzdata 2026.6 ほか付随）。
- `six` が欠ける理由: mplfinance の `requires_dist` は matplotlib と pandas のみで、入った python-dateutil 4.0.0 の依存は tzdata だけ。six を連れてくる別パッケージがある環境では表面化しないため、「手元では動く」が再現性を損なう例になる。
- TA-Lib の README は、バイナリ wheel が C ライブラリを同梱しコンパイラ不要と述べる。0.8.3 からソースビルドは TA-Lib C 0.8.3 を取得して静的リンクする（ネットワーク・C コンパイラ・CMake が必要）。互換表は 0.4.x が numpy 1、0.5〜0.8.x が numpy 2 向け。
- 最小の動作確認（実測で成功したもの）:

```python
import matplotlib
matplotlib.use("Agg")                      # ヘッドレス環境
import talib, mplfinance as mpf            # df: Open/High/Low/Close/Volume と DatetimeIndex
sma5 = talib.SMA(df["Close"], timeperiod=5)   # Series を渡すと Series が返る（実測）
mpf.plot(df, type="candle", mav=(5, 10), volume=True, savefig="chart.png")
```

## 3. パッケージ表

### 3.1 基盤

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| pandas | 3.1.1 | 2026-11-04 | BSD-3-Clause | >=3.11 | W | 表形式・時系列の基盤。3 系では文字列列が `str`、日付列が `datetime64[us]` になる場合があると [TL-209] の README が注記。zipline-reloaded 3.2.1 は pandas<3.0 を要求する（5 章）。 | [TL-201] |
| numpy | 2.5.4 | 2026-10-10 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | >=3.12 | W | 配列計算。requires_python が >=3.12 のため、3.11 以下の環境には本版を導入できない。 | [TL-202] |
| scipy | 1.18.1 | 2026-08-21 | BSD（classifier） | >=3.12 | W | `scipy.signal` のピーク検出（`find_peaks`）などをピボット抽出に流用できる。requires_python >=3.12。 | [TL-203] |
| statsmodels | 0.15.0 | 2026-08-27 | BSD-3-Clause | >=3.10 | W | 回帰・単位根検定・時系列モデル。 | [TL-204] |
| numba | 0.68.1 | 2026-10-27 | BSD | >=3.10 | W | JIT コンパイラ。vectorbt 1.2.0 は numba>=0.66、pandas-ta 0.4.71b0 は numba==0.61.2 を要求する（依存衝突の原因）。 | [TL-205] |
| matplotlib | 3.11.2 | 2026-09-11 | matplotlib 独自（PSF 系） | >=3.11 | W | 描画基盤。3.11.2 は requires_python >=3.11。 | [TL-206] |

### 3.2 データ取得・補助（暦・日本語表示を含む）

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| pandas-datareader | 0.11.1 | 2026-06-24 | BSD-3-Clause | >=3.11 | P | README はマクロ・ファクター系（FRED, Fama/French, Bank of Canada, World Bank, OECD, Eurostat）を主対象と説明。価格系リーダー（Yahoo, Stooq 等）の現状は README から確認できず**未確認**。 | [TL-207] |
| yfinance | 1.8.0 | 2026-11-03 | Apache-2.0 | 未指定 | P | Yahoo! の公開 API を使う非公式ツール。README は「研究・教育目的」「Yahoo! の API は個人利用限定」と明記。**既定 `auto_adjust=True`（配当調整済み価格）**。curl_cffi 等に依存。 | [TL-208] |
| jquants-api-client | 2.8.0 | 2026-09-30 | Apache-2.0 | <4.0,>=3.10 | P | J-Quants API **V2**（API キー認証）の Python クライアント（作者表記 J-Quants Project Contributors）。README は Python 3.13・Colab で動作確認、pandas 3 系対応、J-Quants は有償サービスと記載。import 名は `jquantsapi`。 | [TL-209] |
| edinet-tools | 0.9.1 | 2026-10-13 | メタデータ未記載（README バッジは MIT） | >=3.11 | P | 個人名義の EDINET 書類パーサ（依存なし）。取得には無料の EDINET API キーが必要と README に記載。 | [TL-210] |
| exchange_calendars | 4.13.2 | 2026-03-10 | Apache-2.0 | <4,>=3.10 | P | 取引所カレンダー。README の表に東京証券取引所 **XTKS** がある。寄付・引けのオークション時間は「閉場」扱い。カレンダーは利用者貢献で維持と README が明記 → 臨時休場は公式と照合すること。 | [TL-211] |
| pandas_market_calendars | 5.6.0 | 2026-10-31 | MIT | >=3.10 | P | README によれば exchange_calendars のカレンダーをミラーしている（XTKS 含む）。 | [TL-212] |
| jpholiday | 1.0.3 | 2025-12-26 | MIT | >=3.9 | P | 内閣府公表データに基づく**国民の祝日のみ**（README: 2026 年までは公式発表で動作確認済み）。取引所休業日（年末年始等）は含まれない。 | [TL-213] |
| japanize-matplotlib | 1.1.3 | 2020-10-21（6.1 年前） | MIT License | 未指定 | S | matplotlib の日本語フォント自動設定。sdist のみで 2020-10 以降更新なし。代替は `rcParams` で日本語フォントを直接指定する方法。 【保守注意】 | [TL-214] |

- 取引所カレンダーと祝日の違い、年末年始休業などは [02_data_sources.md](02_data_sources.md) の「休場カレンダー」を参照。

### 3.3 テクニカル指標

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| TA-Lib | 0.8.3 | 2026-10-28 | メタデータ未記載 | >=3.9 | W | C 実装 TA-Lib の Cython ラッパー。README: バイナリ wheel は C ライブラリ同梱でコンパイラ不要。0.8.x は numpy 2 向け。導入の実測は 2 章。 | [TL-215] |
| pandas-ta-classic | 0.9.0 | 2026-10-28 | MIT | >=3.11 | P | pandas-ta のコミュニティ・フォーク（初回リリース 2025-08）。README: 224 指標＋62 ローソク足パターンをネイティブ実装し TA-Lib 不要（`talib=True` で一部高速化）。numpy>=2.0 / pandas>=2.0。 | [TL-216] |
| pandas-ta | 0.4.71b0 | 2025-09-14 | メタデータ未記載 | >=3.12 | P | PyPI 上のリリースは 0.4.67b0 と 0.4.71b0（いずれもベータ、2025-09）の 2 件のみ。**numba==0.61.2 固定**のため、numpy 2.5.4 の環境では numpy 2.2.6 への降格を伴う解決になった（pip dry-run）。 | [TL-217] |
| ta | 0.11.0 | 2023-11-02（3.0 年前） | MIT | 未指定 | S | sdist のみ・`requires_dist` が空（numpy/pandas を自動導入しない）。実測: pandas 3.1.1 で `RSIIndicator`・`BollingerBands` が警告なしで動作。 【保守注意】 | [TL-218] |
| finta | 1.3 | 2021-04-03（5.6 年前） | LGPL-3.0 以降 | 未指定 | P | 更新は 2021-04 が最後。実測: pandas 3.1.1 で `TA.RSI` が動作。 【保守注意】 | [TL-219] |
| stockstats | 0.6.10 | 2026-10-26 | BSD-3-Clause | >=3.9 | P | DataFrame の列アクセス（例 `rsi_14`）で指標を計算。実測: 動作。 | [TL-220] |
| technical | 1.7.0 | 2026-07-21 | GPL-3.0 | >=3.11 | P | freqtrade チームの指標ライブラリ。GPL のため組込み時はライセンスに注意。 | [TL-221] |

- 日本の慣行（移動平均 5・25・75 日、一目均衡表 9・26・52 など）で計算するときは、ライブラリの既定値に頼らず期間を明示指定する。

### 3.4 可視化

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| mplfinance | 0.12.10b0 | 2023-08-02（3.3 年前） | BSD 系（classifier） | 未指定 | P | ローソク足・出来高・移動平均の描画。ベータ表記のまま 2023-08 以降更新なし。**`six` が未導入だと ImportError**（実測、2 章）。 【保守注意】 | [TL-222] |
| plotly | 7.1.0 | 2026-09-15 | MIT | >=3.8 | P | 対話型グラフ（`graph_objects.Candlestick` 等）。 | [TL-223] |
| bokeh | 3.10.2 | 2026-11-05 | BSD-3-Clause | >=3.12 | P | backtesting.py の描画に使用。3.10.2 は requires_python >=3.12。 | [TL-224] |
| lightweight-charts | 2.1 | 2024-09-28（2.1 年前） | MIT | >=3.8 | P | TradingView の Lightweight Charts を pywebview 上で表示する Python ラッパー（非公式）。GUI ウィンドウが前提。派生に lightweight-charts-v5（1.0.2, 2025-03）。 【保守注意】 | [TL-225] |

### 3.5 パターン検出・統計

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| ruptures | 1.1.10 | 2025-09-10 | BSD-2-Clause | <3.14,>=3.9 | W | 変化点検出。requires_python に上限 <3.14。 | [TL-226] |
| zigzag | 0.3.2 | 2022-08-06（4.3 年前） | BSD-3-Clause | >=3.8 | △ | ZigZag（スイング高安）抽出。wheel は cp38（Linux）のみで、3.13 では sdist ビルドになる。 【保守注意】 | [TL-227] |
| trendln | 0.1.18 | 2026-04-09 | MIT | >=3.10 | P | サポート／レジスタンスのトレンドライン検出。 | [TL-228] |

- 指標とパターンの定義・限界は [../01_techniques/02_chart_patterns.md](../01_techniques/02_chart_patterns.md)、効果の検証は [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md) を参照。

### 3.6 パフォーマンス評価

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| quantstats | 0.0.86 | 2026-09-27 | Apache-2.0 | >=3.10 | P | リターン系列の指標・レポート。依存に yfinance・seaborn。実測: `stats.sharpe`・`stats.max_drawdown` が動作。 | [TL-229] |
| empyrical-reloaded | 0.7.2 | 2026-11-02 | Apache-2.0 | >=3.11 | P | Sharpe・最大ドローダウン等。実測: `sharpe_ratio`・`max_drawdown` が動作。旧 empyrical は 2020 以降更新なし。 | [TL-230] |
| pyfolio-reloaded | 0.10.2 | 2026-11-02 | Apache-2.0 | <3.16,>=3.11 | P | ティアシート。実測: import のみ確認。旧 pyfolio は 2019 以降更新なし。 | [TL-231] |

### 3.7 テスト・開発

| パッケージ | 最新版 | 最新版リリース日 | ライセンス | requires_python | 3.13 | 要点・注意 | 出典 |
|---|---|---|---|---|---|---|---|
| pytest | 9.2.0 | 2026-10-27 | MIT | >=3.10 | P | 実測: 導入・実行 OK。 | [TL-232] |
| hypothesis | 6.170.15 | 2026-11-06 | MPL-2.0 | >=3.11 | W | プロパティベーステスト（指標の不変条件テスト向き）。 | [TL-233] |

## 4. 実測: 指標ライブラリ間の RSI(14) の差

同一の合成データ（`numpy.random.default_rng(0)` によるランダムウォーク 120 本）で最終足の RSI(14) を比較した。

| 実装 | RSI(14) 最終値 | TA-Lib との差 |
|---|---|---|
| TA-Lib 0.8.3 `RSI` | 60.327968 | — |
| 自前: Wilder 平滑（最初の 14 本の単純平均で初期化） | 60.327968 | 0 |
| pandas-ta-classic 0.9.0 `rsi` | 60.327968 | 0 |
| 自前: `ewm(alpha=1/14, adjust=False)`（最初の差分は NaN のまま） | 60.327529 | −4.4e-4 |
| ta 0.11.0 `RSIIndicator`／finta 1.3 `TA.RSI`／stockstats 0.6.10 `rsi_14` | 60.328995（3 者同値） | +1.0e-3 |

- 差は平滑化の初期値の取り方の違いによると考えられる（原因の特定までは未検証）。TA-Lib と ta の差は、同じシードで水準を +50 した別の合成データで測ると、120 本の最終足で 1.0e-3、500 本で 7.1e-15、2000 本で 0 となった一方、30 本目では 1.63 あった。**照合テストでは助走区間（数百本）を除外するか許容誤差を設定する**必要がある。RSI の平滑化の流儀そのものは [../01_techniques/07_oscillators_momentum.md](../01_techniques/07_oscillators_momentum.md) を参照。

## 5. 依存衝突と pandas 3 系の扱い（実測を含む）

- **pandas-ta 0.4.71b0**: `numba==0.61.2` を固定。numba 0.61.2 は `numpy<2.3` を要求するため、numpy 2.5.4 の環境では numpy 2.2.6 への降格を伴う解決になった（pip dry-run）。numpy>=2.4.6 を要求する vectorbt 1.2.0 とは同居できない。
- **vectorbt 1.2.0**: `numpy>=2.4.6`・`pandas>=3.0.3`・`numba>=0.66`（requires_dist）。
- **zipline-reloaded 3.2.1**: `pandas<3.0`（Python 3.14 未満）。pandas 3.1.1 入りの環境へは pandas 2.3.3 への降格解決になり、`pandas>=3` を併記すると zipline-reloaded 3.0.4 に巻き戻った（いずれも dry-run）。巻き戻し先が pandas 3 で動くかは未検証。
- **backtesting.py 0.6.6**: pandas 3.1.1 で実行できたが `Pandas4Warning`（`DatetimeIndex.dayofweek` 非推奨）を出す（[05](05_backtesting_frameworks.md)）。
- **jquants-api-client 2.8.0**: pandas 3 系で文字列列が `object`→`str`、日付列が `datetime64[ns]`→`datetime64[us]` に変わると README が注記する。dtype に依存する処理は再点検する。
- quantstats 0.0.86 は yfinance を、lightweight-charts（Python）は pywebview（GUI）を依存に含む。CI に入れる前に依存の木を確認する。
- 表中の「実測: 動作」は、合成データへの 1〜2 関数の呼び出しが例外なく終了したことのみを意味し、数値の正しさの保証ではない。

## 6. 更新が古い／置換済みのパッケージと、PyPI で見つからなかった名前

| パッケージ | 最新版 | 最新版リリース日 | 状況 |
|---|---|---|---|
| talib-binary / ta-lib-bin | 0.4.19 / 0.4.26 | 2019-04-18（7.6 年前） / 2022-06-11（4.4 年前） | 旧来の非公式バイナリ配布（wheel は cp34〜cp37 または cp36〜cp311）。公式 TA-Lib に cp313 wheel がある |
| tulipy | 0.4.0 | 2019-04-11（7.6 年前） | Tulip Indicators のバインディング。wheel は cp37（Windows）のみ |
| mpl-finance | 0.10.1 | 2020-02-21（6.7 年前） | README が deprecated と明記し mplfinance への移行を案内 |
| empyrical / pyfolio / alphalens / zipline | 0.5.5 / 0.9.2 / 0.4.0 / 1.4.1 | 2020-10-13（6.1 年前） / 2019-04-15（7.6 年前） / 2020-04-27（6.5 年前） / 2020-10-05（6.1 年前） | 最終リリースが 2019〜2020 年。同名の `-reloaded` フォーク（上表）が現行リリースを継続 |
| edinet-xbrl | 0.2.0 | 2018-01-28（8.8 年前） | EDINET XBRL パーサ。2018-01 以降更新なし、sdist のみ |
| investpy | 1.0.8 | 2022-01-24（4.8 年前） | Investing.com からのデータ抽出ライブラリ。2022-01 以降リリースなし |
| tradingview-ta | 3.3.0 | 2022-10-05（4.1 年前） | TradingView の非公式ラッパー（概要に Unofficial と明記）。2022-10 以降リリースなし |
| Quandl | 3.7.0 | 2021-11-11（5.0 年前） | 旧 Quandl クライアント。nasdaq-data-link（02 章参照）が別パッケージとして存在 |

- 上表の出典は [TL-234]。
- PyPI JSON が **404（見つからず）** だった名前: `pybroker`（実体は `lib-pybroker`、05 章参照）、`mlfinlab`、`vectorbtpro`（vectorbt の README が別製品 PRO として案内する有償版で、公開パッケージとしては見つからず）、`tvdatafeed`（別名の `tradingview-datafeed` と `tvdatafeed-enhanced` は存在）、`stooq`、`kabusapi`、`jquants`、`jquantsapi`（J-Quants クライアントの PyPI 名は `jquants-api-client`、import 名が `jquantsapi`）、`tradingpatterns` [TL-235]。存在しないことの確認であり、別名・別配布で存在する可能性は排除しない。

## 関連文書

- [02_data_sources.md](02_data_sources.md): データ源の規約・調整後株価・暦の落とし穴
- [04_javascript_and_other_libraries.md](04_javascript_and_other_libraries.md): JS／他言語のライブラリ
- [05_backtesting_frameworks.md](05_backtesting_frameworks.md): バックテスト基盤の比較
- [../07_reference_code/](../07_reference_code/): 参照実装と TA-Lib 照合テスト（リポジトリ管理者が作成）

## この文書の限界

- Web 検索の上限に達したため、各ライブラリの公式ドキュメント（API 仕様・指標の定義・サポート方針）は確認していない。記述は PyPI JSON（メタデータと README）とサンドボックス実測に限る。
- 実測は Linux x86_64・Python 3.13.18・合成データでの 1 回の観測。Windows／macOS、実データ、未試験の関数は未確認。
- ライセンスは PyPI メタデータの記載に基づき、LICENSE 本文は未読（TA-Lib・pandas-ta・edinet-tools はメタデータ未記載）。商用利用・再配布の可否は各 LICENSE で確認すること。
- 「最新版」は 2026-11-09 時点の表示（要再確認）。
- 取り上げたのは代表的な 33 件で網羅ではない。「更新が古い」は最終リリース日のみを根拠とし、安定して更新が要らないだけのパッケージも含まれうる。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TL-201 | PyPI: pandas 3.1.1 | — | 2026 | https://pandas.pydata.org | ✅S | PyPI JSON 実測 |
| TL-202 | PyPI: numpy 2.5.4 | Travis E. Oliphant et al. | 2026 | https://numpy.org | ✅S | PyPI JSON 実測 |
| TL-203 | PyPI: scipy 1.18.1 | — | 2026 | https://scipy.org/ | ✅S | PyPI JSON 実測 |
| TL-204 | PyPI: statsmodels 0.15.0 | — | 2026 | https://www.statsmodels.org | ✅S | PyPI JSON 実測 |
| TL-205 | PyPI: numba 0.68.1 | — | 2026 | https://numba.pydata.org | ✅S | PyPI JSON 実測 |
| TL-206 | PyPI: matplotlib 3.11.2 | John D. Hunter, Michael Droettboom | 2026 | https://matplotlib.org | ✅S | PyPI JSON 実測 |
| TL-207 | PyPI: pandas-datareader 0.11.1 | — | 2026 | https://pandas-datareader.readthedocs.io/en/latest/ | ✅S | PyPI JSON 実測 |
| TL-208 | PyPI: yfinance 1.8.0 | — | 2026 | https://github.com/ranaroussi/yfinance | ✅S | PyPI JSON 実測 |
| TL-209 | PyPI: jquants-api-client 2.8.0 | J-Quants Project Contributors | 2026 | https://github.com/J-Quants/jquants-api-client-python | ✅S | PyPI JSON 実測 |
| TL-210 | PyPI: edinet-tools 0.9.1 | Matt Helmer | 2026 | https://github.com/matthelmer/edinet-tools | ✅S | PyPI JSON 実測 |
| TL-211 | PyPI: exchange_calendars 4.13.2 | Gerry Manoim | 2026 | https://github.com/gerrymanoim/exchange_calendars | ✅S | PyPI JSON 実測 |
| TL-212 | PyPI: pandas_market_calendars 5.6.0 | — | 2026 | https://github.com/rsheftel/pandas_market_calendars | ✅S | PyPI JSON 実測 |
| TL-213 | PyPI: jpholiday 1.0.3 | Vatis | 2025 | https://github.com/Lalcs/jpholiday | ✅S | PyPI JSON 実測 |
| TL-214 | PyPI: japanize-matplotlib 1.1.3 | uehara1414 | 2020 | https://github.com/uehara1414/japanize-matplotlib | ✅S | PyPI JSON 実測 |
| TL-215 | PyPI: TA-Lib 0.8.3 | — | 2026 | http://github.com/ta-lib/ta-lib-python | ✅S | PyPI JSON 実測 |
| TL-216 | PyPI: pandas-ta-classic 0.9.0 | xgboosted | 2026 | https://github.com/xgboosted/pandas-ta-classic | ✅S | PyPI JSON 実測 |
| TL-217 | PyPI: pandas-ta 0.4.71b0 | — | 2025 | https://www.pandas-ta.dev | ✅S | PyPI JSON 実測 |
| TL-218 | PyPI: ta 0.11.0 | Dario Lopez Padial (Bukosabino) | 2023 | https://github.com/bukosabino/ta | ✅S | PyPI JSON 実測 |
| TL-219 | PyPI: finta 1.3 | Peerchemist | 2021 | https://github.com/peerchemist/finta | ✅S | PyPI JSON 実測 |
| TL-220 | PyPI: stockstats 0.6.10 | — | 2026 | https://github.com/jealous/stockstats | ✅S | PyPI JSON 実測 |
| TL-221 | PyPI: technical 1.7.0 | Freqtrade Team | 2026 | https://github.com/freqtrade/technical | ✅S | PyPI JSON 実測 |
| TL-222 | PyPI: mplfinance 0.12.10b0 | MPL Developers | 2023 | http://github.com/matplotlib/mplfinance | ✅S | PyPI JSON 実測 |
| TL-223 | PyPI: plotly 7.1.0 | — | 2026 | https://plotly.com/python/ | ✅S | PyPI JSON 実測 |
| TL-224 | PyPI: bokeh 3.10.2 | Bokeh Team | 2026 | https://bokeh.org | ✅S | PyPI JSON 実測 |
| TL-225 | PyPI: lightweight-charts 2.1 | louisnw | 2024 | https://github.com/louisnw01/lightweight-charts-python | ✅S | PyPI JSON 実測 |
| TL-226 | PyPI: ruptures 1.1.10 | Charles Truong ほか | 2025 | https://github.com/deepcharles/ruptures/ | ✅S | PyPI JSON 実測 |
| TL-227 | PyPI: zigzag 0.3.2 | generativist | 2022 | https://github.com/jbn/ZigZag | ✅S | PyPI JSON 実測 |
| TL-228 | PyPI: trendln 0.1.18 | Gregory Morse | 2026 | https://github.com/GregoryMorse/trendln | ✅S | PyPI JSON 実測 |
| TL-229 | PyPI: quantstats 0.0.86 | — | 2026 | https://github.com/ranaroussi/quantstats | ✅S | PyPI JSON 実測 |
| TL-230 | PyPI: empyrical-reloaded 0.7.2 | Quantopian Inc | 2026 | https://ml4trading.io | ✅S | PyPI JSON 実測 |
| TL-231 | PyPI: pyfolio-reloaded 0.10.2 | Quantopian Inc | 2026 | https://ml4trading.io | ✅S | PyPI JSON 実測 |
| TL-232 | PyPI: pytest 9.2.0 | Brianna Laugher ほか | 2026 | https://docs.pytest.org/en/latest/ | ✅S | PyPI JSON 実測 |
| TL-233 | PyPI: hypothesis 6.170.15 | — | 2026 | https://hypothesis.works | ✅S | PyPI JSON 実測 |
| TL-234 | PyPI JSON（6 節の表の各パッケージ） | 各パッケージの作者 | — | — | ✅S | 個別 URL は省略（取得 2026-11-09） |
| TL-235 | PyPI JSON 照会（404 を確認した名前の一覧） | PyPI | 2026 | — | ✅S | 取得 2026-11-09 |
| TL-236 | サンドボックス実測（pip install・pip dry-run・合成データでの最小実行・RSI 比較） | 本調査（Linux x86_64、Python 3.13.18、pip 26.2.2） | 2026 | — | ✅S | 実行ログは作業領域のみでリポジトリには含めない。1 回の観測 |
