# 株式チャート分析 資料集

> 要約: 株式のチャート分析（テクニカル分析）に関する資料を、手法・日本市場の固有事情・学術的エビデンス・学習資源・ツールとデータ・実践手順・検証用コードに分けて集めた日本語の資料集。全29文書・約748 KB、出典は一意に875件。出典の実在は作業記録と機械照合し、確認の程度を検証区分で示した。チャート分析の効果は断定せず、エビデンスの強弱と限界を併記している。教育目的であり、投資助言ではない。
> 最終更新: 2026-11-09

## 1. 使い方（目的別の入口）

| 目的 | 読む順 |
|---|---|
| まず全体像と「本当に効くのか」を知りたい | [実践手順](06_workflow/01_analysis_procedure.md) → [学術エビデンス](03_evidence/01_academic_literature.md)の「1. 要約」と「4. 総合評価」 |
| 初めて学ぶ | [学習ロードマップ](04_learning/05_study_roadmap.md) → [価格構造](01_techniques/01_price_structure.md) → [ローソク足](01_techniques/03_candlesticks.md) → [移動平均線](01_techniques/06_moving_averages.md) |
| 日本株で使う | [東証の制度とチャート](02_japan/04_tse_market_rules_and_chart_effects.md) → [需給指標](02_japan/05_supply_demand_indicators.md) → [酒田五法](02_japan/01_sakata_gohou.md) → [一目均衡表](02_japan/02_ichimoku_kinko_hyo.md) |
| 自分で検証・自動化する | [検証手法と落とし穴](03_evidence/02_methodology_behavioral_japan_ml.md) → [チェックリスト](06_workflow/02_checklists_and_templates.md) → [データ源](05_tools_data_code/02_data_sources.md) → [バックテスト基盤](05_tools_data_code/05_backtesting_frameworks.md) → [参考実装](07_reference_code/README.md) |
| 指標の式と「ツールによる値の違い」を確かめる | [移動平均](01_techniques/06_moving_averages.md)・[オシレーター](01_techniques/07_oscillators_momentum.md)・[ボラティリティ](01_techniques/08_volatility_and_trend_strength.md)、および[参考実装の「流儀の違い」の表](07_reference_code/README.md) |

## 2. 構成

### 01_techniques — 手法（世界共通）

| 文書 | 内容 | 大きさ | 出典（✅S／⚠M） |
|---|---|---:|---:|
| [01_techniques/01_price_structure.md](01_techniques/01_price_structure.md) | ダウ理論、トレンド定義、トレンドライン、支持線・抵抗線、ブレイクアウトとダマシ、ギャップ、ピボットポイント | 24 KB | 30／1 |
| [01_techniques/02_chart_patterns.md](01_techniques/02_chart_patterns.md) | 反転型・継続型パターンの辞典、成功率統計の読み方、アルゴリズム検出のヒント | 22 KB | 26／1 |
| [01_techniques/03_candlesticks.md](01_techniques/03_candlesticks.md) | ローソク足の構造・規格化、単一〜3本足パターン、文脈ルール、TA-Lib 対応 | 20 KB | 22／0 |
| [01_techniques/04_waves_fibonacci_wyckoff_gann.md](01_techniques/04_waves_fibonacci_wyckoff_gann.md) | エリオット波動、フィボナッチ、ワイコフ、ギャン、ハーモニック、SMC/ICT（エビデンスの乏しさを含む） | 21 KB | 26／0 |
| [01_techniques/05_practitioner_frameworks.md](01_techniques/05_practitioner_frameworks.md) | ダーバス、CAN SLIM、ステージ分析、ミネルヴィニ、タートル、リバモア、コナーズRSI(2)、エルダー 等 | 24 KB | 29／3 |
| [01_techniques/06_moving_averages.md](01_techniques/06_moving_averages.md) | 移動平均線の種類と式（TA-Lib 照合済み）、期間慣行、クロス、グランビルの法則、乖離率 | 22 KB | 26／3 |
| [01_techniques/07_oscillators_momentum.md](01_techniques/07_oscillators_momentum.md) | RSI、ストキャスティクス（日本式と欧米式）、MACD、CCI 等。実装差とダイバージェンス | 20 KB | 22／4 |
| [01_techniques/08_volatility_and_trend_strength.md](01_techniques/08_volatility_and_trend_strength.md) | ボリンジャーバンド、ATR、ケルトナー、ドンチャン、ADX/DMI、パラボリックSAR、アルーン | 18 KB | 19／3 |
| [01_techniques/09_volume_breadth_sentiment.md](01_techniques/09_volume_breadth_sentiment.md) | OBV、A/D、CMF、VWAP、出来高プロファイル、騰落系・センチメント指標 | 22 KB | 29／6 |
| [01_techniques/10_alt_charts_relative_strength_mtf.md](01_techniques/10_alt_charts_relative_strength_mtf.md) | 平均足、Renko、カギ足、P&F、相対力、RRG、マルチタイムフレーム | 23 KB | 20／4 |

### 02_japan — 日本市場固有

| 文書 | 内容 | 大きさ | 出典（✅S／⚠M） |
|---|---|---:|---:|
| [02_japan/01_sakata_gohou.md](02_japan/01_sakata_gohou.md) | 酒田五法と日本のローソク足用語、歴史（伝承と史実の区別） | 24 KB | 24／0 |
| [02_japan/02_ichimoku_kinko_hyo.md](02_japan/02_ichimoku_kinko_hyo.md) | 一目均衡表の式・シフト本数の流儀差、三役、時間論・波動論、実装上の注意 | 26 KB | 32／0 |
| [02_japan/03_other_japanese_methods.md](02_japan/03_other_japanese_methods.md) | 新値足、大循環分析、パーフェクトオーダー、騰落レシオ、相場格言・干支アノマリー（検証状況つき） | 24 KB | 17／0 |
| [02_japan/04_tse_market_rules_and_chart_effects.md](02_japan/04_tse_market_rules_and_chart_effects.md) | 東証の制度（取引時間・値幅制限・呼値・権利落ち・信用・空売り規制・SQ 等）がチャートに与える影響 | 26 KB | 45／0 |
| [02_japan/05_supply_demand_indicators.md](02_japan/05_supply_demand_indicators.md) | 信用残、空売り、投資部門別、裁定残、日経VI、騰落レシオ等の定義・公表頻度・使い方・限界 | 25 KB | 36／0 |

### 03_evidence — 学術的エビデンス

| 文書 | 内容 | 大きさ | 出典（✅S／⚠M） |
|---|---|---:|---:|
| [03_evidence/01_academic_literature.md](03_evidence/01_academic_literature.md) | テクニカル分析の学術エビデンスの注釈付きサーベイ（約120本）。**§1 要約と §4 総合評価から読む** | 132 KB | 119／15 |
| [03_evidence/02_methodology_behavioral_japan_ml.md](03_evidence/02_methodology_behavioral_japan_ml.md) | 検証の落とし穴（スヌーピング・過剰最適化等）、行動ファイナンス、日本市場の実証、機械学習、検証10か条 | 50 KB | 70／5 |

### 04_learning — 学習資源

| 文書 | 内容 | 大きさ | 出典（✅S／⚠M） |
|---|---|---:|---:|
| [04_learning/01_books_english.md](04_learning/01_books_english.md) | 英語圏の定番書（検索で書誌を確認した約40冊） | 25 KB | 42／0 |
| [04_learning/02_books_japanese.md](04_learning/02_books_japanese.md) | 日本語書籍。**邦訳11点は記憶ベース、日本人著者の解説書は未収録**（選書の観点を記載） | 13 KB | 3／13 |
| [04_learning/03_online_courses_and_sites.md](04_learning/03_online_courses_and_sites.md) | オンライン学習資源・証券会社の解説ページ | 17 KB | 15／8 |
| [04_learning/04_organizations_journals_certifications.md](04_learning/04_organizations_journals_certifications.md) | 専門家団体・資格・学術誌（記憶ベースが中心。要公式確認） | 14 KB | 11／14 |
| [04_learning/05_study_roadmap.md](04_learning/05_study_roadmap.md) | 目的別の学習ロードマップ（基礎→実践→検証→自動化） | 23 KB | 4／0 |

### 05_tools_data_code — ツール・データ・ライブラリ

| 文書 | 内容 | 大きさ | 出典（✅S／⚠M） |
|---|---|---:|---:|
| [05_tools_data_code/01_charting_platforms_and_screeners.md](05_tools_data_code/01_charting_platforms_and_screeners.md) | チャート・スクリーナー・日本の証券会社ツール | 17 KB | 11／3 |
| [05_tools_data_code/02_data_sources.md](05_tools_data_code/02_data_sources.md) | データ源（J-Quants、各社API等）と、調整後価格・生存者バイアス等の落とし穴 | 22 KB | 26／1 |
| [05_tools_data_code/03_python_libraries.md](05_tools_data_code/03_python_libraries.md) | Python ライブラリの実測カタログ（PyPI 実測、保守状況、RSI 実測差） | 24 KB | 36／0 |
| [05_tools_data_code/04_javascript_and_other_libraries.md](05_tools_data_code/04_javascript_and_other_libraries.md) | JS/TS 等のチャート・指標ライブラリ（npm 実測、TradingView のライセンス区分） | 21 KB | 39／1 |
| [05_tools_data_code/05_backtesting_frameworks.md](05_tools_data_code/05_backtesting_frameworks.md) | バックテスト基盤の比較と、日本株制度に結びつけた設計上の落とし穴 | 23 KB | 23／1 |

### 06_workflow — 実践手順

| 文書 | 内容 | 大きさ | 出典（✅S／⚠M） |
|---|---|---:|---:|
| [06_workflow/01_analysis_procedure.md](06_workflow/01_analysis_procedure.md) | トップダウンの分析手順（市場→セクター→銘柄→シナリオ→リスク→記録） | 17 KB | — |
| [06_workflow/02_checklists_and_templates.md](06_workflow/02_checklists_and_templates.md) | 分析メモ・ルール仕様書・バックテスト設計チェックリスト・取引日誌の雛形 | 10 KB | — |

### 07_reference_code — 検証用コード

[07_reference_code/README.md](07_reference_code/README.md)。主要指標を pandas で実装し、TA-Lib と数値照合した（119 テスト、先読み検査つき）。日本式ストキャスティクス、一目均衡表（シフト本数の流儀差つき）、ジグザグ、ローソク足パターン、合成データのデモチャート、文書の検査ツールを含む。

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

## 4. 日本市場の最近の事項（確認日 2026-11-09、要公式確認）

- 東証の現物取引は 2024-11-05 から 15:30 終了（15:25〜15:30 は注文受付のみで、15:30 に板寄せ）。
- 信用取引残高は 2026-09-28 から日次公表（JPX総研、前営業日分を毎営業日 16 時頃）。従来は週次。
- 呼値: TOPIX500 構成銘柄は 2023-06-05 から細かい呼値（1,000 円以下は 0.1 円）。適用銘柄は毎年 10 月末に見直される。
- 日銀: ETF の新規買入れは 2024-03 に終了。2025-09 に簿価年 3,300 億円の売却方針、2026-10 の会合で 2027-01 から年 8,600 億円へ加速（野村證券の解説による）。

制度は変わりうる。売買の前に取引所・証券会社の最新情報を確認すること。詳細は [東証の制度とチャート](02_japan/04_tse_market_rules_and_chart_effects.md) と [需給指標](02_japan/05_supply_demand_indicators.md)。

## 5. この資料集を使う前に（収集方法と限界）

**収集方法**: AI アシスタントが、学術論文データベース（Consensus）、Web 検索、パッケージレジストリ（PyPI／npm）、および自作コードによる数値検証（TA-Lib との照合）で収集・要約した。

**検証区分**（各文書の出典表の「検証」列。集計は [SOURCES.md](SOURCES.md)）:

| 区分 | 意味 | 件数（一意） |
|---|---|---:|
| ✅S | 検索結果・論文データベース・レジストリの応答に現れ、書誌情報が整合することを確認した。**全文・原ページは読んでいない** | 790 |
| ⚠M | 作成時の記憶に基づく（広く知られた古典など）。今回の作業で再確認していない。URL は付けていない | 85 |
| ❓ | 不確実。人手での確認が必要 | 0 |

**実在確認**: ✅S の出典は、URL・DOI・題名が、作業記録に残るツールの実際の応答に存在することを機械照合した（捏造の検出）。パッケージ表（`05_tools_data_code/03`・`04`）と出典行の PyPI／npm のバージョン表記は、2026-11-09 に現在のレジストリと照合し、全件一致した。

**限界（重要）**:

1. 外部サイトの本文を直接取得できなかった（名前解決が遮断される環境だった）。✅S は「存在と書誌情報の確認」であって、**内容を原典で確認したものではない**。論文は抄録レベルの要約である。
2. Web 検索には共有の利用上限があり、作業の後半は十分に使えなかった。そのため **日本語書籍は13点すべてが記憶ベース**（邦訳11点＋国内の2点）で、ローソク足・酒田五法・個別株の売買ルールなど日本人著者の解説書は収録できていない。団体・資格の詳細、オンライン教材の無料／有料も記憶ベースが中心（`04_learning`）。日本語の学術文献（J-STAGE／CiNii）も未確認。
3. 時間依存の情報（制度、料金、パッケージの版、資格）には確認日を付けたが、更新される。
4. Consensus の論文ページ URL は、追跡用パラメータ（`?utm_source=…`）を除いた形で記載している。
5. 参考実装の検証は合成データのみ。実市場での有効性は何も保証しない。
6. 投資助言ではない。

## 6. 保守

```bash
python 07_reference_code/tools/docs_tool.py lint      # 書式・出典表・リンクの検査
python 07_reference_code/tools/docs_tool.py sources   # SOURCES.md を再生成
cd 07_reference_code && python -m pytest              # 参考実装の検証（119 件）
```
