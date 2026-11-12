# 株式チャート分析 資料集

> 要約: 株式のチャート分析（テクニカル分析）に関する資料を、手法・日本市場の固有事情・学術的エビデンス・学習資源・ツールとデータ・実践手順・検証用コードに分けて集めた日本語の資料集。全37文書・約1228 KB、出典は一意に1192件。出典の実在は作業記録と機械照合し、確認の程度を検証区分で示した。JPX・国会図書館・CiNii・J-STAGE・トヨタ・住友電工の公式ページは、取得して原文と照合した（✅P）。日足から確率つきの予測を作って採点する仕組み（手順の事前登録と実装）も含む。チャート分析の効果は断定せず、エビデンスの強弱と限界を併記している。教育目的であり、投資助言ではない。
> 最終更新: 2026-11-11

## 1. 使い方（目的別の入口）

| 目的 | 読む順 |
|---|---|
| まず全体像と「本当に効くのか」を知りたい | [実践手順](06_workflow/01_analysis_procedure.md) → [学術エビデンス](03_evidence/01_academic_literature.md)の「1. 要約」と「4. 総合評価」 |
| 初めて学ぶ | [学習ロードマップ](04_learning/05_study_roadmap.md) → [価格構造](01_techniques/01_price_structure.md) → [ローソク足](01_techniques/03_candlesticks.md) → [移動平均線](01_techniques/06_moving_averages.md) |
| 日本株で使う | [東証の制度とチャート](02_japan/04_tse_market_rules_and_chart_effects.md) → [需給指標](02_japan/05_supply_demand_indicators.md) → [酒田五法](02_japan/01_sakata_gohou.md) → [一目均衡表](02_japan/02_ichimoku_kinko_hyo.md) |
| 自分で検証・自動化する | [検証手法と落とし穴](03_evidence/02_methodology_behavioral_japan_ml.md) → [チェックリスト](06_workflow/02_checklists_and_templates.md) → [データ源](05_tools_data_code/02_data_sources.md) → [バックテスト基盤](05_tools_data_code/05_backtesting_frameworks.md) → [参考実装](07_reference_code/README.md) |
| 指標の式と「ツールによる値の違い」を確かめる | [移動平均](01_techniques/06_moving_averages.md)・[オシレーター](01_techniques/07_oscillators_momentum.md)・[ボラティリティ](01_techniques/08_volatility_and_trend_strength.md)、および[参考実装の「流儀の違い」の表](07_reference_code/README.md) |
| 日足から確率つきの予測（価格の幅、水準に届く確率）を作り、過去で採点したい | [手法の検討と採否](09_forecasting/01_method_review.md) → [予測手順（事前登録）](09_forecasting/02_protocol.md) → [参考実装](07_reference_code/README.md) |
| 一次資料で確かめた事実・取得できなかった資料を知りたい | [一次資料の取得記録](08_primary_sources/00_index.md) → [JPX で確認した制度・統計](08_primary_sources/01_jpx_primary.md) |

## 2. 構成

### 01_techniques — 手法（世界共通）

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [01_techniques/01_price_structure.md](01_techniques/01_price_structure.md) | ダウ理論、トレンド定義、トレンドライン、支持線・抵抗線、ブレイクアウトとダマシ、ギャップ、ピボットポイント | 24 KB | 0／30／1 |
| [01_techniques/02_chart_patterns.md](01_techniques/02_chart_patterns.md) | 反転型・継続型パターンの辞典、成功率統計の読み方、アルゴリズム検出のヒント | 22 KB | 0／26／1 |
| [01_techniques/03_candlesticks.md](01_techniques/03_candlesticks.md) | ローソク足の構造・規格化、単一〜3本足パターン、文脈ルール、TA-Lib 対応 | 20 KB | 0／22／0 |
| [01_techniques/04_waves_fibonacci_wyckoff_gann.md](01_techniques/04_waves_fibonacci_wyckoff_gann.md) | エリオット波動、フィボナッチ、ワイコフ、ギャン、ハーモニック、SMC/ICT（エビデンスの乏しさを含む） | 21 KB | 0／26／0 |
| [01_techniques/05_practitioner_frameworks.md](01_techniques/05_practitioner_frameworks.md) | ダーバス、CAN SLIM、ステージ分析、ミネルヴィニ、タートル、リバモア、コナーズRSI(2)、エルダー 等 | 24 KB | 0／29／3 |
| [01_techniques/06_moving_averages.md](01_techniques/06_moving_averages.md) | 移動平均線の種類と式（TA-Lib 照合済み）、期間慣行、クロス、グランビルの法則、乖離率 | 22 KB | 0／26／3 |
| [01_techniques/07_oscillators_momentum.md](01_techniques/07_oscillators_momentum.md) | RSI、ストキャスティクス（日本式と欧米式）、MACD、CCI 等。実装差とダイバージェンス | 20 KB | 0／22／4 |
| [01_techniques/08_volatility_and_trend_strength.md](01_techniques/08_volatility_and_trend_strength.md) | ボリンジャーバンド、ATR、ケルトナー、ドンチャン、ADX/DMI、パラボリックSAR、アルーン | 18 KB | 0／19／3 |
| [01_techniques/09_volume_breadth_sentiment.md](01_techniques/09_volume_breadth_sentiment.md) | OBV、A/D、CMF、VWAP、出来高プロファイル、騰落系・センチメント指標 | 22 KB | 0／29／6 |
| [01_techniques/10_alt_charts_relative_strength_mtf.md](01_techniques/10_alt_charts_relative_strength_mtf.md) | 平均足、Renko、カギ足、P&F、相対力、RRG、マルチタイムフレーム | 23 KB | 0／20／4 |

### 02_japan — 日本市場固有

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [02_japan/01_sakata_gohou.md](02_japan/01_sakata_gohou.md) | 酒田五法と日本のローソク足用語、歴史（伝承と史実の区別） | 24 KB | 0／24／0 |
| [02_japan/02_ichimoku_kinko_hyo.md](02_japan/02_ichimoku_kinko_hyo.md) | 一目均衡表の式・シフト本数の流儀差、三役、時間論・波動論、実装上の注意 | 26 KB | 0／32／0 |
| [02_japan/03_other_japanese_methods.md](02_japan/03_other_japanese_methods.md) | 新値足、大循環分析、パーフェクトオーダー、騰落レシオ、相場格言・干支アノマリー（検証状況つき） | 24 KB | 0／17／0 |
| [02_japan/04_tse_market_rules_and_chart_effects.md](02_japan/04_tse_market_rules_and_chart_effects.md) | 東証の制度（取引時間・値幅制限・呼値・権利落ち・信用・空売り規制・SQ 等）がチャートに与える影響 | 43 KB | 26／37／0 |
| [02_japan/05_supply_demand_indicators.md](02_japan/05_supply_demand_indicators.md) | 信用残、空売り、投資部門別、裁定残、日経VI、騰落レシオ等の定義・公表頻度・使い方・限界 | 38 KB | 23／32／0 |

### 03_evidence — 学術的エビデンス

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [03_evidence/01_academic_literature.md](03_evidence/01_academic_literature.md) | テクニカル分析の学術エビデンスの注釈付きサーベイ（約120本）。**§1 要約と §4 総合評価から読む** | 132 KB | 0／119／15 |
| [03_evidence/02_methodology_behavioral_japan_ml.md](03_evidence/02_methodology_behavioral_japan_ml.md) | 検証の落とし穴（スヌーピング・過剰最適化等）、行動ファイナンス、日本市場の実証、機械学習、検証10か条 | 51 KB | 0／70／5 |
| [03_evidence/03_japanese_literature.md](03_evidence/03_japanese_literature.md) | 日本語の学術文献60件（CiNii・J-STAGE の記録を取得して確認、うち抄録を読んだ39件）。テクニカルルール・モメンタム・値幅制限・投資家行動・バックテスト過学習 | 80 KB | 60／0／0 |

### 04_learning — 学習資源

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [04_learning/01_books_english.md](04_learning/01_books_english.md) | 英語圏の定番書（検索で書誌を確認した約40冊） | 25 KB | 0／42／0 |
| [04_learning/02_books_japanese.md](04_learning/02_books_japanese.md) | 日本語書籍。国立国会図書館の書誌で確認（邦訳の確認表46行、日本語の専門書58点、日本発の定番・入門書）。本文は未読で、内容の評価ではない。ニソン・Bulkowski の書籍の邦訳は未確認 | 64 KB | 17／3／0 |
| [04_learning/03_online_courses_and_sites.md](04_learning/03_online_courses_and_sites.md) | オンライン学習資源・証券会社の解説ページ | 17 KB | 0／15／8 |
| [04_learning/04_organizations_journals_certifications.md](04_learning/04_organizations_journals_certifications.md) | 専門家団体・資格・学術誌。団体・資格の概要は記憶ベースが中心（要公式確認）。機関誌・雑誌の発行元は CiNii／NDL で確認 | 18 KB | 4／11／13 |
| [04_learning/05_study_roadmap.md](04_learning/05_study_roadmap.md) | 目的別の学習ロードマップ（基礎→実践→検証→自動化） | 23 KB | 0／4／0 |

### 05_tools_data_code — ツール・データ・ライブラリ

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [05_tools_data_code/01_charting_platforms_and_screeners.md](05_tools_data_code/01_charting_platforms_and_screeners.md) | チャート・スクリーナー・日本の証券会社ツール | 22 KB | 0／21／3 |
| [05_tools_data_code/02_data_sources.md](05_tools_data_code/02_data_sources.md) | データ源（J-Quants、各社API等）と、調整後価格・生存者バイアス等の落とし穴 | 30 KB | 12／26／1 |
| [05_tools_data_code/03_python_libraries.md](05_tools_data_code/03_python_libraries.md) | Python ライブラリの実測カタログ（PyPI 実測、保守状況、RSI 実測差） | 24 KB | 0／36／0 |
| [05_tools_data_code/04_javascript_and_other_libraries.md](05_tools_data_code/04_javascript_and_other_libraries.md) | JS/TS 等のチャート・指標ライブラリ（npm 実測、TradingView のライセンス区分） | 21 KB | 0／39／1 |
| [05_tools_data_code/05_backtesting_frameworks.md](05_tools_data_code/05_backtesting_frameworks.md) | バックテスト基盤の比較と、日本株制度に結びつけた設計上の落とし穴 | 24 KB | 1／23／0 |

### 06_workflow — 実践手順

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [06_workflow/01_analysis_procedure.md](06_workflow/01_analysis_procedure.md) | トップダウンの分析手順（市場→セクター→銘柄→シナリオ→リスク→記録） | 17 KB | — |
| [06_workflow/02_checklists_and_templates.md](06_workflow/02_checklists_and_templates.md) | 分析メモ・ルール仕様書・バックテスト設計チェックリスト・取引日誌の雛形 | 10 KB | — |

### 08_primary_sources — 一次資料の取得記録（✅P）

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [08_primary_sources/00_index.md](08_primary_sources/00_index.md) | 一次資料の取得記録の入口（取得方法、取得できなかった資料、許可したホスト） | 22 KB | 3／0／0 |
| [08_primary_sources/01_jpx_primary.md](08_primary_sources/01_jpx_primary.md) | JPX 公式ページで確認した制度・統計（値幅制限・呼値・取引時間・信用残・J-Quants 等）と、ライブラリ記述の訂正記録 | 61 KB | 70／0／0 |
| [08_primary_sources/02_ndl_cinii_jstage.md](08_primary_sources/02_ndl_cinii_jstage.md) | 国立国会図書館サーチ・CiNii・J-STAGE の利用方法と取得記録 | 46 KB | 50／0／0 |
| [08_primary_sources/03_company_filings_toyota_sumitomo.md](08_primary_sources/03_company_filings_toyota_sumitomo.md) | トヨタ・住友電工の決算（公式PDF）の原文確認と、株価シナリオ回答の訂正 | 12 KB | 7／0／0 |

### 09_forecasting — 確率予測の手法と手順

| 文書 | 内容 | 大きさ | 出典（✅P／✅S／⚠M） |
|---|---|---:|---:|
| [09_forecasting/01_method_review.md](09_forecasting/01_method_review.md) | 予測の確度を上げる手法の検討と採否（資料集の手法と統計的手法を、役割・根拠・検証可能性で評価）。自己検査で分かったこと、追加で要るデータ | 28 KB | 0／0／4 |
| [09_forecasting/02_protocol.md](09_forecasting/02_protocol.md) | 予測手順の事前登録（幅の予測、予測分布、候補モデル 10 個、シグナル 41 個、評価と採否の基準、予測台帳）と、合成データでの自己検査の結果 | 20 KB | 1／0／0 |
| [09_forecasting/03_literature_notes.md](09_forecasting/03_literature_notes.md) | 予測手法の根拠文献（論文データベースで 20 の問いを確認。出典 107 件、要旨レベル） | 110 KB | 0／107／0 |

### 07_reference_code — 検証用コード

[07_reference_code/README.md](07_reference_code/README.md)。`chartlib` は主要指標を pandas で実装し、TA-Lib と数値照合した（119 テスト、先読み検査つき）。日本式ストキャスティクス、一目均衡表（シフト本数の流儀差つき）、ジグザグ、ローソク足パターン、合成データのデモチャート、文書の検査ツールを含む。`forecastlib` は、日足から確率つきの予測を作り、ウォークフォワードで採点する実装（35 テスト。先読みや誤りを入れた複製 14 通りをすべて検出）。

### 取得ログ（CSV）

[08_primary_sources/fetch_logs/](08_primary_sources/fetch_logs/)。一次資料の取得の URL・取得時刻（UTC）・HTTP 状態・バイト数・sha256（JPX 107 行、国会図書館・CiNii・J-STAGE 130 行、取りまとめ役の再取得と株価データの試み 12 行）。取得物の写しは著作権のため置いていない。読み方は [一次資料の取得記録](08_primary_sources/00_index.md)。

### SOURCES.md — 出典台帳

各文書の出典表の集計、検証区分別の件数、**人手での確認を推奨する資料（⚠M／❓）の一覧**。[SOURCES.md](SOURCES.md)

## 3. エビデンスの要点（結論を急がないために）

詳細と出典は [学術エビデンス](03_evidence/01_academic_literature.md)（1. 要約・4. 総合評価）と [方法論・日本・ML](03_evidence/02_methodology_behavioral_japan_ml.md)（1. 要約）。

- **単純ルールの超過収益は、補正すると縮む。** 移動平均・レンジブレイクなどの単純ルールは、データスヌーピングの補正、取引コスト、標本の延長（サンプル外検証）で大きく縮小し、先進国の株式指数では近年ほぼ消えたとする研究が目立つ。新興市場や若い市場では相対的に残るとの報告もあるが、コスト後の優位は限定的。
- **市場・期間・定義で結論が割れる。** トレンドフォロー／時系列モメンタムは長期・多資産で頑健との報告と、統計的証拠が弱いとの再検証が併存する。ローソク足・チャートパターンは厳密な検定で否定的な結果が多いが、肯定的な報告もあり、出口ルールの違いで結論が変わる。
- **単独のオシレーター・バンド系指標**（RSI、MACD、ボリンジャー）は、頑健な超過収益の証拠が乏しい。
- **機能しうる理由はある**（処分効果、アンカリング、注文の集中と支持線・抵抗線など）が、それは有効性の証明ではない。
- **日本株**: 古典的な価格モメンタムは弱く、逆張りが有利とする研究がある（異説あり）。スヌーピング補正つきの大規模なルール検証は、今回の調査では確認できなかった。
- **機械学習**: 画像を使った手法は既知の指標と異なるパターンを見つけたとされる一方、データ漏えいによる偽陽性の懸念が大きい。
- **実務上の含意**: 手法の名前ではなく検証の質（サンプル外・コスト後・補正後・複数市場）で評価する。自分が過去のチャートで見つけた最良のパラメータほど信用しない。

## 4. 日本市場の最近の事項（確認日 2026-11-11、要公式確認）

JPX の公式ページ・PDF で原文を確認した事項（[JPX で確認した制度・統計](08_primary_sources/01_jpx_primary.md)）。

- 取引時間: 前場 9:00〜11:30、後場 12:30〜15:30（2024-11-05 から 15:30 終了）。15:25〜15:30 は注文受付のみで、15:30 に板寄せ。
- 信用取引残高: 銘柄別は 2026-09-28 から毎営業日の公表になった（証券会社・名証の告知による。JPX の無料統計ページに日次の PDF〈直近 5 営業日分、16:00 目安〉があることは確認したが、日次掲載の開始日そのものは JPX の資料では未確認）。JPX総研の有償配信（法人向け）も 9/28（予定）から日次になる。二市場計の信用取引現在高は週次のまま（毎週第 2 営業日の 16:00 目安）。
- 呼値: 現行は TOPIX500 構成銘柄が細かい呼値（1,000 円以下は 0.1 円）で、適用銘柄は毎年 10 月末に見直される（2026 年は 10/30 以降）。**2027-03-01 から、銘柄ごとの流動性（STR）に応じた呼値テーブル（A・B・C・O）に移行する。**
- クロージング・オークションにランダムクローズ（15:29:30〜15:30:00）を 2027-10-12 から導入する予定（延期の可能性がある旨の記載あり）。
- 日銀: ETF の新規買入れは 2024-03 に終了。2025-09 に簿価年 3,300 億円の売却方針、2026-10 の会合で 2027-01 から年 8,600 億円へ加速（野村證券の解説による）。

制度は変わりうる。売買の前に取引所・証券会社の最新情報を確認すること。詳細は [東証の制度とチャート](02_japan/04_tse_market_rules_and_chart_effects.md) と [需給指標](02_japan/05_supply_demand_indicators.md)。

## 5. この資料集を使う前に（収集方法と限界）

**収集方法**: AI アシスタントが、学術論文データベース（Consensus）、Web 検索、パッケージレジストリ（PyPI／npm）、自作コードによる数値検証（TA-Lib との照合）に加え、ユーザーの許可を得て JPX・国会図書館サーチ・CiNii・J-STAGE・トヨタ・住友電工の公式ページを取得して収集・要約した。

**検証区分**（各文書の出典表の「検証」列。集計は [SOURCES.md](SOURCES.md)）:

| 区分 | 意味 | 件数（一意） |
|---|---|---:|
| ✅P | **一次資料（公式ページ・PDF・目録のレコード）を取得して読み、原文と照合した。** 取得日と sha256 の先頭を出典表に残した | 223 |
| ✅S | 検索結果・論文データベース・レジストリの応答に現れ、書誌情報が整合することを確認した。**全文・原ページは読んでいない** | 895 |
| ⚠M | 作成時の記憶に基づく（広く知られた古典など）。今回の作業で再確認していない。URL は付けていない | 74 |
| ❓ | 不確実。人手での確認が必要 | 0 |

**実在確認**: ✅S の出典は、URL・DOI・題名が、作業記録に残るツールの実際の応答に存在することを機械照合した（捏造の検出）。パッケージ表（`05_tools_data_code/03`・`04`）と出典行の PyPI／npm のバージョン表記は、2026-11-09 に現在のレジストリと照合し、全件一致した。✅P の出典は、取得したファイルの sha256 を記録し、取得ログ・保存ファイルと整合することを機械で確認した。JPX の制限値幅表（34 帯）と現行の呼値表は私が再取得して一致を確認し、2027 年からの呼値表（画像）は目視で原画像と照合した。国会図書館・CiNii・J-STAGE の分は、✅P の全行を取得ログと保存ファイルに機械照合し（不一致 0 件）、書籍表104行と論文表39行を取得物と一件ずつ照合し、J-STAGE の2ページを再取得して sha256 の一致を確認した。

**限界（重要）**:

1. 当初は外部サイトの本文を取得できなかったが、ユーザーの許可により、JPX（東証）・国会図書館サーチ・CiNii・J-STAGE・トヨタ・住友電工の公式ページは取得して原文と照合した（✅P）。それ以外の出典は ✅S（存在と書誌情報の確認だけで、**内容を原典で確認したものではない**）か ⚠M（記憶）である。StockCharts ChartSchool は TLS の握手が失敗し、J-Quants の公式サイトはサイト側が 403 を返すため取得できていない（回避は行っていない）。論文は抄録レベルの要約である。
2. Web 検索には共有の利用上限があり、作業の後半は十分に使えなかった。日本語書籍は国立国会図書館の書誌で、邦訳の確認表46行・日本語の専門書58点・日本発の定番を確認したが（2026-11-11）、**本文は読んでおらず、内容や優劣の評価ではない**。ニソンと Bulkowski の書籍の邦訳は確認できていない（国会図書館の応答が約半数 429 で、検索語の表記ゆれも残る）。日本語の学術文献は60件（抄録を読めたのは39件）で、補正つきの大規模なルール検証は確認できず、日本株のモメンタムや処分効果の中心的な論文は書誌のみである。団体・資格の詳細、オンライン教材の無料／有料は記憶ベースが中心（`04_learning`）。
3. 時間依存の情報（制度、料金、パッケージの版、資格）には確認日を付けたが、更新される。
4. Consensus の論文ページ URL は、追跡用パラメータ（`?utm_source=…`）を除いた形で記載している。
5. 参考実装の検証は合成データのみ。実市場での有効性は何も保証しない。予測の仕組み（`09_forecasting`、`forecastlib`）も、現時点では合成データでの自己検査だけで、実データの結果はまだない（日足の自動取得ができなかったため）。
6. JPX は価格の月次 PDF（日報）と適時開示の自動取得を控えるよう案内しているため、取引所の四本値データは取得していない。無料の CSV 配信元（Stooq）も、ブラウザ検証のページで自動取得を弾かれた（回避していない）。株価は二次情報である。
7. 投資助言ではない。

## 6. 保守

```bash
python 07_reference_code/tools/docs_tool.py lint      # 書式・出典表・リンクの検査
python 07_reference_code/tools/docs_tool.py sources   # SOURCES.md を再生成
cd 07_reference_code && python -m pytest              # 参考実装の検証（154 件）
python tools/forecast_report.py --csv <日足CSV> --name <名前> --out <出力先>   # 確率予測のレポート
```
