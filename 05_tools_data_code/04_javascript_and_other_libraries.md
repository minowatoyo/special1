# JavaScript／TypeScript とその他言語のチャート・指標ライブラリ
> 要約: ブラウザ向けチャート描画（lightweight-charts, klinecharts, ECharts, Highcharts 等）と、JS の指標計算・データ取得クライアントを npm registry の実測値（最新版・公開日・license・description・homepage）で整理した。Rust・Go・.NET・Java は各レジストリに到達できた範囲だけを載せ、R など到達できなかったものは「未確認」とした。
> TradingView の Lightweight Charts は Apache-2.0 だが、README が TradingView の帰属表示とリンクの掲載を求めている。高機能版の Charting Library は npm 上の公式名では見つからなかった。
> technicalindicators は最終公開が 2020-03 で、indicatorts は README が積極開発の終了を表明している。取得日は 2026-11-09、いずれも要再確認。
> 最終更新: 2026-11-09

## 1. 取得方法と読み方

- 確認日: 2026-11-09（版・ライセンスは要公式確認＝再取得）。npm: `https://registry.npmjs.org/<package>` の完全メタデータを同日に curl で取得し、`dist-tags.latest`・`time[latest]`・`license`・`description`・`homepage`、および `readme` を読んだ（✅S）。出典表の URL 列は各パッケージの homepage。
- 他言語: crates.io API（識別用ヘッダ付き）、Go module proxy、NuGet registration API、Maven Central の `maven-metadata.xml` と POM を同日に取得した。CRAN（HTTP 403）と GitHub 系には到達できず、R・Julia・C++ の個別ライブラリは**未確認**。
- 【保守注意】は最終公開から 730 日以上（年数を括弧表示）。古い＝使えないではないが、依存先の更新に追随していない可能性がある。license は package.json 等の記載で、LICENSE 本文は未読。
- Web 検索の上限に達したため、各ライブラリの公式ドキュメント・デモ・ベンチマークは確認していない。性能に関する記述は出していない。

## 2. ブラウザ向けチャート描画ライブラリ

| パッケージ | 最新版 | 公開日（time[latest]） | license | 概要（要約） | 備考 | 出典 |
|---|---|---|---|---|---|---|
| lightweight-charts | 5.2.1 | 2026-08-12 | Apache-2.0 | TradingView 製の軽量な金融チャート（canvas） | README: Apache-2.0 だが**制作者として TradingView を明示する義務**があり、NOTICE の帰属表示と tradingview.com へのリンクをユーザーに見えるページへ載せる。チャートオプション `attributionLogo` でリンク要件を満たせると README が説明。v5 系はプラグイン拡張に対応（README）。 | [TL-301] |
| lightweight-charts-react-wrapper | 2.1.1 | 2024-05-11（2.5 年前） | MIT | Lightweight Charts の React ラッパー（個人作者） | 公開は 2024-05。本体 v5 系への追随は未確認。 【保守注意】 | [TL-302] |
| klinecharts | 10.1.0 | 2026-10-14 | Apache-2.0 | K 線（ローソク足）チャート、canvas 描画 | Apache-2.0。型定義を同梱（README）。10 系。 | [TL-303] |
| chart.js | 4.6.1 | 2026-10-22 | MIT | 汎用 HTML5 canvas チャート | 下の financial 拡張の基盤。 | [TL-304] |
| chartjs-chart-financial | 0.2.1 | 2024-03-23（2.6 年前） | MIT | Chart.js 用のローソク足・OHLC 拡張 | chart.js 本体が別途必要。公開は 2024-03 の 0.2.1 で止まっている。 【保守注意】 | [TL-305] |
| echarts | 6.1.0 | 2026-05-19 | Apache-2.0 | Apache ECharts（汎用可視化） | 商用製品への組込みも可と README が述べる。ローソク足系列の有無は公式ドキュメントで要確認（本調査では未確認）。 | [TL-306] |
| highcharts | 13.1.1 | 2026-09-20 | 独自（URL 記載） | Highsoft 製の汎用チャート | license 欄は独自ライセンスの URL（OSS ではない）。npm の README は空。商用利用の条件は公式ライセンスページで要確認。 | [TL-307] |
| apexcharts | 8.8.1 | 2026-11-08 | 独自（LICENSE.md 参照） | ApexCharts（汎用チャート） | README のバッジは Revenue-based。大半は無償・OSS だが一部の高度機能はライセンスキーが必要と README が説明。candlestick を種別に列挙。 | [TL-308] |
| plotly.js | 4.2.0 | 2026-10-29 | MIT | plotly.js 本体 | Python の plotly（03 章）と同系統。 | [TL-309] |
| plotly.js-finance-dist-min | 4.2.0 | 2026-10-29 | MIT | plotly.js の金融向け部分バンドル（minified） | 本体と同日・同版。ファイルサイズを抑えたいときの選択肢。 | [TL-310] |
| d3 | 7.9.2 | 2026-11-03 | ISC | データ駆動の描画基盤 | 金融専用ではない。 | [TL-311] |
| d3fc | 15.2.13 | 2024-07-30（2.3 年前） | MIT | D3 向け金融チャート部品群 | 公開は 2024-07 が最後。 【保守注意】 | [TL-312] |
| react-financial-charts | 2.0.1 | 2023-05-13（3.5 年前） | MIT | React 向け金融チャート | 公開は 2023-05 が最後。 【保守注意】 | [TL-313] |

- ローソク足系列を持つかどうかは、README で確認できたものに限れば lightweight-charts・klinecharts・chartjs-chart-financial（用途）と ApexCharts（種別の列挙）である。ECharts・Highcharts・Plotly は公式ドキュメントでの確認が必要（未確認）。

## 3. TradingView 製品のライセンス区分（確認できた範囲）

- **Lightweight Charts**（npm `lightweight-charts`）: Apache-2.0 [TL-301]。ただし README は、このライセンスが「TradingView を制作者として明示すること」を要求すると述べ、NOTICE の帰属表示と tradingview.com へのリンクを利用者に見えるページ（Web サイトまたはモバイルアプリ）へ追加するよう求める。チャートオプション `attributionLogo` でチャート上にリンクを出せばリンク要件を満たすとも説明している。公開・配布するなら帰属表示の実装を設計に含める。
- **Charting Library**（高機能版）: npm 上の `@tradingview/charting_library`・`tradingview-charting-library`・`@tradingview/lightweight-charts` は 404（取得 2026-11-09）。`charting_library` は TradingView 名義ではない別の公開物 [TL-323]。したがって `npm install` で標準的に入手できる形ではないと推測できるが、配布条件とライセンス区分は本調査では確認できていない。申請・契約を要する非 OSS 製品と記憶しているが ⚠M [TL-340]、要公式確認。
- 指標・パターンの計算は描画ライブラリの責務ではなく、別途 4 章の計算ライブラリや自前実装で行い、結果を系列として渡す構成が基本になる。

## 4. 指標計算・データ取得のライブラリ

### 4.1 指標計算

| パッケージ | 最新版 | 公開日（time[latest]） | license | 概要（要約） | 備考 | 出典 |
|---|---|---|---|---|---|---|
| technicalindicators | 3.1.0 | 2020-03-16（6.7 年前） | MIT | TypeScript 製のテクニカル指標集 | README は Node.js 10 以上とブラウザ利用を説明。最終公開は 2020-03。 【保守注意】 | [TL-314] |
| trading-signals | 8.3.0 | 2026-08-11 | MIT | 逐次更新型の指標集 | README: `add` メソッドでデータを流し込む逐次更新と、バックテスト向けのバッチ計算の両方に対応。 | [TL-315] |
| indicatorts | 2.6.0 | 2026-11-08 | MIT | 指標と戦略（TypeScript） | README の冒頭に「積極的な開発は終了、新機能の予定なし」との保守状況表示がある。 | [TL-316] |
| tulind | 0.8.20 | 2021-08-08（5.3 年前） | LGPL-3.0 | Tulip Indicators の Node バインディング | LGPL。ネイティブ拡張を含む。 【保守注意】 | [TL-317] |
| talib | 2.0.6 | 2026-10-06 | LGPL-3.0-or-later | node-talib（TA-Lib の Node バインディング） | LGPL。ネイティブ拡張を含む。 | [TL-318] |
| @debut/indicators | 2.0.1 | 2026-05-16 | GPL-3.0 | debut フレームワーク向け指標集 | GPL-3.0。組込み時にライセンスへ注意。 | [TL-319] |

### 4.2 データ取得クライアント

| パッケージ | 最新版 | 公開日（time[latest]） | license | 概要（要約） | 備考 | 出典 |
|---|---|---|---|---|---|---|
| yahoo-finance2 | 4.0.6 | 2026-11-08 | MIT | Yahoo Finance を呼ぶ JS ライブラリ | npm の記述に公式／非公式の明示はない。Yahoo 側の規約確認が前提（02 章）。 | [TL-320] |
| @massive.com/client-js | 10.8.0 | 2026-09-17 | MIT | Massive.com（旧 Polygon.io）の API クライアント | 概要に Stocks／Options／Indices／Futures／Forex／Crypto と記載。パッケージ新設は 2025-11。 | [TL-321] |
| @polygon.io/client-js | 8.2.0 | 2025-08-13 | MIT | Polygon.io の API クライアント（旧名称側） | 2025-08 以降の公開なし。Polygon.io の改称は PyPI `massive` の概要に明記（02 章）。 | [TL-322] |

### 4.3 混同しやすい名前

| パッケージ | 最新版 | 公開日（time[latest]） | license | 概要（要約） | 備考 | 出典 |
|---|---|---|---|---|---|---|
| charting_library | 1.0.2 | 2019-11-22（7.0 年前） | ISC | npm 上の同名パッケージ | maintainers は zhuwenbo、2019-11 公開の 3 版、repository・homepage なし。**TradingView 名義ではない**ので TradingView の Charting Library と混同しない。 【保守注意】 | [TL-323] |
| highcharts-stock | 0.1.7 | 2018-01-15（8.8 年前） | CC | react-highcharts 用モジュール（旧） | deprecated 表示、2018-01 の 0.1.7 のみ、作者 kirjs。Highsoft 名義ではない。 【保守注意】 | [TL-324] |

## 5. 他言語（レジストリで確認できた範囲）

| 言語 | レジストリ | 名前 | 最新版 | 日付 | ライセンス | 備考 | 出典 |
|---|---|---|---|---|---|---|---|
| Rust | crates.io | ta | 0.5.0 | 2021-06-26 | MIT | SMA/EMA/RSI/MACD/Stochastic 等（crate 説明）。 【保守注意】 | [TL-325] |
| Rust | crates.io | yata | 0.7.0 | 2024-03-07 | Apache-2.0 | 「Yet another Technical Analysis library」（crate 説明）。 【保守注意】 | [TL-326] |
| Rust | crates.io | rust_ti | 2.2.0 | 2025-10-19 | MIT | 70 超の指標を設定可能な形で提供と説明。 | [TL-327] |
| Rust | crates.io | kand | 0.2.2 | 2025-03-05 | Apache-2.0 OR MIT | TA-Lib に着想した純 Rust 実装と説明。 | [TL-328] |
| Rust | crates.io | ta-lib | 0.8.3 | 2026-10-25 | BSD-3-Clause | crate 説明は「公式の Rust 移植、C 実装と照合済み」と自称（検証は未実施）。rust_version 1.88。 | [TL-329] |
| Rust | crates.io | polars | 0.55.2 | 2026-08-06 | MIT | Apache Arrow ベースの DataFrame。 | [TL-330] |
| Rust | crates.io | barter | 0.14.0 | 2026-08-20 | MIT | ライブ／ペーパー／バックテスト用フレームワークと説明。 | [TL-331] |
| Go | Go proxy | github.com/markcheno/go-talib | v0.0.0-20260617004048-4ff5e103edd9 | 2026-06-17 | 未確認（proxy の応答に含まれない） | 擬似バージョン（タグなし）。日付は proxy の Time（コミット時刻）。 | [TL-332] |
| Go | Go proxy | github.com/cinar/indicator/v2 | v2.1.44 | 2026-09-12 | 未確認（proxy の応答に含まれない） | タグ付き版。 | [TL-333] |
| Go | Go proxy | github.com/sdcoffey/techan | v0.14.0 | 2026-09-04 | 未確認（proxy の応答に含まれない） | タグ付き版。 | [TL-334] |
| Go | Go proxy | github.com/iamjinlei/go-tart | 擬似バージョン | 2021-06-23 | 未確認（proxy の応答に含まれない） | 2021-06 以降更新なし 【保守注意】 | [TL-335] |
| .NET | NuGet | Skender.Stock.Indicators | 2.7.3 | 2026-06-25 | Apache-2.0 | 最新の安定版（listed）。3.0 系のプレビューは unlisted。 | [TL-336] |
| .NET | NuGet | TALib.NETCore | 0.5.0 | 2025-02-14 | LGPL-3.0-or-later | TA-Lib の C# 移植（NuGet 説明）。 | [TL-337] |
| .NET | NuGet | Trady.Core | 3.2.9 | 2020-03-07 | 未確認（licenseExpression 空） | 2020-03 以降更新なし 【保守注意】 | [TL-338] |
| Java | Maven Central | org.ta4j:ta4j-core | 0.28.0 | 2026-11-03 | 未確認（この POM に license 記載なし、親 POM 未取得） | 日付は maven-metadata.xml の lastUpdated。27 バージョンが列挙されている。 | [TL-339] |

- Go の日付は module proxy の `Time`（コミット時刻）、Rust の日付は crates.io の `updated_at`、Java の日付は `maven-metadata.xml` の `lastUpdated` であり、いずれも「リリース日」と厳密には一致しない場合がある。
- ライセンスが「未確認」とあるのは、そのレジストリの応答に license が含まれなかったことを意味し、無ライセンスという意味ではない。
- R（quantmod・TTR・PerformanceAnalytics の名称は記憶にあるが ⚠M）、Julia、C/C++ の TA-Lib 本体は、CRAN と GitHub に到達できず**未確認**。MetaTrader 5 の Python 連携 `MetaTrader5` は PyPI 上に Windows 向け wheel のみが存在する（[01_charting_platforms_and_screeners.md](01_charting_platforms_and_screeners.md) 参照）。

## 6. 選び方の指針

- **ライセンスを最初に確認する**: GPL（@debut/indicators）、LGPL（tulind, talib: ネイティブ拡張）、独自（Highcharts, ApexCharts）、帰属表示義務（Lightweight Charts）は、社内利用か公開・再配布かで扱いが変わる。ここでの記述は法的助言ではない。
- **保守状況を見る**: technicalindicators（2020-03）、react-financial-charts（2023-05）、indicatorts（README が開発終了方針）のように、機能が足りていても今後の追随は期待しにくいものがある。
- **日本株チャートの実装上の論点**（ライブラリごとの対応可否は未確認）: ① 前場・後場の間（休憩）や夜間が系列に存在しないため、時間軸が実時刻か点番号かで見え方が変わる。② 表示タイムゾーンは JST に固定する。③ 日本では陽線を赤、陰線を青（または緑）とする慣行が広く、米国式の「上昇＝緑」と逆になりうるため色を設定で反転する（⚠M）。④ 価格の小数桁と出来高の単位（株／百株）を明示する。
- **バージョンを固定する**: CDN から読み込む場合も `lightweight-charts@5.2.1` のように正確な版を指定し、可能なら SRI を付ける。メジャー更新で API が変わりうる。
- 配布容量や速度のベンダー主張（例: lightweight-charts の README が「最小・最速級」と述べる）は自社データでの計測に置き換える。

## 関連文書

- [03_python_libraries.md](03_python_libraries.md): Python 側のライブラリ（Python の plotly 等）
- [02_data_sources.md](02_data_sources.md): データ源の規約と落とし穴
- [01_charting_platforms_and_screeners.md](01_charting_platforms_and_screeners.md): 既製のチャート／スクリーナー製品
- [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md): 取引時間・呼値・値幅制限（チャート表示に影響する制度）

## この文書の限界

- Web 検索の上限に達し、各ライブラリの公式ドキュメント・ライセンス全文・デモを確認していない。記述は npm／各レジストリのメタデータと README に限る。
- 描画性能・API の使いやすさ・日本株での挙動（休憩時間の扱い、タイムゾーン）は試していない。
- TradingView Charting Library の配布条件・ライセンス区分は確認できていない（記憶のみ）。
- 他言語は到達できたレジストリ（crates.io, Go proxy, NuGet, Maven Central）の範囲のみ。R・Julia・C++ は未確認。Go と Maven はライセンスが取得できていない。
- 「最新版」は 2026-11-09 時点の表示で、以後変わる（要再確認）。取り上げたのは代表例で網羅ではない。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TL-301 | npm: lightweight-charts 5.2.1 | TradingView, Inc. | 2026 | https://www.tradingview.com/lightweight-charts/ | ✅S | npm registry 実測 |
| TL-302 | npm: lightweight-charts-react-wrapper 2.1.1 | — | 2024 | https://github.com/trash-and-fire/lightweight-charts-react-wrapper#readme | ✅S | npm registry 実測 |
| TL-303 | npm: klinecharts 10.1.0 | liihuu | 2026 | https://klinecharts.com/ | ✅S | npm registry 実測 |
| TL-304 | npm: chart.js 4.6.1 | — | 2026 | https://www.chartjs.org | ✅S | npm registry 実測 |
| TL-305 | npm: chartjs-chart-financial 0.2.1 | — | 2024 | https://github.com/chartjs/chartjs-chart-financial#readme | ✅S | npm registry 実測 |
| TL-306 | npm: echarts 6.1.0 | — | 2026 | https://echarts.apache.org | ✅S | npm registry 実測 |
| TL-307 | npm: highcharts 13.1.1 | Highsoft AS | 2026 | http://www.highcharts.com | ✅S | npm registry 実測 |
| TL-308 | npm: apexcharts 8.8.1 | — | 2026 | https://apexcharts.com | ✅S | npm registry 実測 |
| TL-309 | npm: plotly.js 4.2.0 | Plotly, Inc. | 2026 | https://github.com/plotly/plotly.js#readme | ✅S | npm registry 実測 |
| TL-310 | npm: plotly.js-finance-dist-min 4.2.0 | Plotly, Inc. | 2026 | https://github.com/plotly/plotly.js#readme | ✅S | npm registry 実測 |
| TL-311 | npm: d3 7.9.2 | Mike Bostock | 2026 | https://d3js.org | ✅S | npm registry 実測 |
| TL-312 | npm: d3fc 15.2.13 | — | 2024 | https://d3fc.io | ✅S | npm registry 実測 |
| TL-313 | npm: react-financial-charts 2.0.1 | reactivemarkets | 2023 | https://github.com/reactivemarkets/react-financial-charts#readme | ✅S | npm registry 実測 |
| TL-314 | npm: technicalindicators 3.1.0 | — | 2020 | https://github.com/anandanand84/technicalindicators#readme | ✅S | npm registry 実測 |
| TL-315 | npm: trading-signals 8.3.0 | — | 2026 | https://bennycode.com/trading-signals | ✅S | npm registry 実測 |
| TL-316 | npm: indicatorts 2.6.0 | The Indicator Authors | 2026 | https://github.com/cinar/indicatorts#readme | ✅S | npm registry 実測 |
| TL-317 | npm: tulind 0.8.20 | Lewis Van Winkle | 2021 | https://github.com/TulipCharts/tulipnode#readme | ✅S | npm registry 実測 |
| TL-318 | npm: talib 2.0.6 | Mustafa Oransel | 2026 | https://github.com/oransel/node-talib | ✅S | npm registry 実測 |
| TL-319 | npm: @debut/indicators 2.0.1 | Dmitry Yurov | 2026 | https://github.com/debut-js/Indicators | ✅S | npm registry 実測 |
| TL-320 | npm: yahoo-finance2 4.0.6 | Gadi Cohen | 2026 | https://github.com/gadicc/yahoo-finance2#readme | ✅S | npm registry 実測 |
| TL-321 | npm: @massive.com/client-js 10.8.0 | — | 2026 | https://github.com/massive-com/client-js#readme | ✅S | npm registry 実測 |
| TL-322 | npm: @polygon.io/client-js 8.2.0 | — | 2025 | https://github.com/polygon-io/client-js#readme | ✅S | npm registry 実測 |
| TL-323 | npm: charting_library 1.0.2 | — | 2019 | — | ✅S | npm registry 実測 |
| TL-324 | npm: highcharts-stock 0.1.7 | kirjs | 2018 | — | ✅S | npm registry 実測 |
| TL-325 | crates.io: ta 0.5.0 | — | 2021 | https://github.com/greyblake/ta-rs | ✅S | crates.io 実測 |
| TL-326 | crates.io: yata 0.7.0 | — | 2024 | https://github.com/amv-dev/yata | ✅S | crates.io 実測 |
| TL-327 | crates.io: rust_ti 2.2.0 | — | 2025 | https://github.com/ChironMind/rustTI | ✅S | crates.io 実測 |
| TL-328 | crates.io: kand 0.2.2 | — | 2025 | https://github.com/rust-ta/kand | ✅S | crates.io 実測 |
| TL-329 | crates.io: ta-lib 0.8.3 | — | 2026 | https://github.com/TA-Lib/ta-lib | ✅S | crates.io 実測 |
| TL-330 | crates.io: polars 0.55.2 | — | 2026 | https://github.com/pola-rs/polars | ✅S | crates.io 実測 |
| TL-331 | crates.io: barter 0.14.0 | — | 2026 | https://github.com/barter-rs/barter-rs | ✅S | crates.io 実測 |
| TL-332 | Go proxy: github.com/markcheno/go-talib v0.0.0-20260617004048-4ff5e103edd9 | — | 2026 | https://github.com/markcheno/go-talib | ✅S | Go proxy 実測 |
| TL-333 | Go proxy: github.com/cinar/indicator/v2 v2.1.44 | — | 2026 | https://github.com/cinar/indicator | ✅S | Go proxy 実測 |
| TL-334 | Go proxy: github.com/sdcoffey/techan v0.14.0 | — | 2026 | https://github.com/sdcoffey/techan | ✅S | Go proxy 実測 |
| TL-335 | Go proxy: github.com/iamjinlei/go-tart 擬似バージョン | — | 2021 | https://proxy.golang.org/github.com/iamjinlei/go-tart/@latest | ✅S | Go proxy 実測 |
| TL-336 | NuGet: Skender.Stock.Indicators 2.7.3 | — | 2026 | https://dotnet.stockindicators.dev/ | ✅S | NuGet 実測 |
| TL-337 | NuGet: TALib.NETCore 0.5.0 | — | 2025 | https://hmg3.github.io/TA-Lib.NETCore | ✅S | NuGet 実測 |
| TL-338 | NuGet: Trady.Core 3.2.9 | — | 2020 | https://github.com/lppkarl/Trady | ✅S | NuGet 実測 |
| TL-339 | Maven Central: org.ta4j:ta4j-core 0.28.0 | — | 2026 | https://repo1.maven.org/maven2/org/ta4j/ta4j-core/maven-metadata.xml | ✅S | Maven Central 実測 |
| TL-340 | TradingView Charting Library（製品の配布形態・ライセンス） | TradingView | — | — | ⚠M | 記憶のみ。ページ未確認。要公式確認 |
