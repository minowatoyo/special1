# 出典台帳（自動生成）
> 要約: 各文書の「出典」表を集計した台帳。検証タグごとの件数、人手での確認が必要な資料（⚠M / ❓）の一覧、URL のドメイン別件数を示す。
> 最終更新: 2026-11-09（`07_reference_code/tools/docs_tool.py sources` で再生成）

## 検証タグの意味

| タグ | 意味 |
|---|---|
| ✅S | 検索結果・論文データベース・パッケージレジストリ（PyPI/npm）の応答に現れ、書名・著者・年などの書誌情報が整合することを確認した。**全文・原ページは読んでいない**（外部サイトの直接取得がこの作業環境では遮断されていたため）。 |
| ⚠M | 作成時の記憶に基づく。広く知られた古典など存在を強く確信できるものに限るが、今回の作業で再確認していない。URL は付けていない。 |
| ❓ | 不確実。人手での確認が必要。 |

## ファイル別の件数

| ファイル | 合計 | ✅S | ⚠M | ❓ |
|---|---:|---:|---:|---:|
| `01_techniques/01_price_structure.md` | 31 | 30 | 1 | 0 |
| `01_techniques/02_chart_patterns.md` | 27 | 26 | 1 | 0 |
| `01_techniques/03_candlesticks.md` | 22 | 22 | 0 | 0 |
| `01_techniques/04_waves_fibonacci_wyckoff_gann.md` | 26 | 26 | 0 | 0 |
| `01_techniques/05_practitioner_frameworks.md` | 32 | 29 | 3 | 0 |
| `01_techniques/06_moving_averages.md` | 29 | 26 | 3 | 0 |
| `01_techniques/07_oscillators_momentum.md` | 26 | 22 | 4 | 0 |
| `01_techniques/08_volatility_and_trend_strength.md` | 22 | 19 | 3 | 0 |
| `01_techniques/09_volume_breadth_sentiment.md` | 35 | 29 | 6 | 0 |
| `01_techniques/10_alt_charts_relative_strength_mtf.md` | 24 | 20 | 4 | 0 |
| `02_japan/01_sakata_gohou.md` | 24 | 24 | 0 | 0 |
| `02_japan/02_ichimoku_kinko_hyo.md` | 32 | 32 | 0 | 0 |
| `02_japan/03_other_japanese_methods.md` | 17 | 17 | 0 | 0 |
| `02_japan/04_tse_market_rules_and_chart_effects.md` | 45 | 45 | 0 | 0 |
| `02_japan/05_supply_demand_indicators.md` | 36 | 36 | 0 | 0 |
| `03_evidence/01_academic_literature.md` | 134 | 119 | 15 | 0 |
| `03_evidence/02_methodology_behavioral_japan_ml.md` | 75 | 70 | 5 | 0 |
| `04_learning/01_books_english.md` | 42 | 42 | 0 | 0 |
| `04_learning/02_books_japanese.md` | 20 | 7 | 13 | 0 |
| `04_learning/03_online_courses_and_sites.md` | 23 | 15 | 8 | 0 |
| `04_learning/04_organizations_journals_certifications.md` | 25 | 11 | 14 | 0 |
| `04_learning/05_study_roadmap.md` | 4 | 4 | 0 | 0 |
| `05_tools_data_code/01_charting_platforms_and_screeners.md` | 24 | 21 | 3 | 0 |
| `05_tools_data_code/02_data_sources.md` | 29 | 28 | 1 | 0 |
| `05_tools_data_code/03_python_libraries.md` | 36 | 36 | 0 | 0 |
| `05_tools_data_code/04_javascript_and_other_libraries.md` | 40 | 39 | 1 | 0 |
| `05_tools_data_code/05_backtesting_frameworks.md` | 24 | 23 | 1 | 0 |
| **合計（延べ）** | **904** | **818** | **86** | **0** |
| **一意な出典（ID で重複排除）** | **891** | **806** | **85** | **0** |

## 人手での確認を推奨する資料（⚠M / ❓）

### `01_techniques/01_price_structure.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TS-027 | Technical Analysis of the Financial Markets | Murphy, J. J. | 1999 | ⚠M | 古典（記憶） |

### `01_techniques/02_chart_patterns.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TS-027 | Technical Analysis of the Financial Markets | Murphy, J. J. | 1999 | ⚠M | 古典（記憶） |

### `01_techniques/05_practitioner_frameworks.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TS-143 | How I Made $2,000,000 in the Stock Market | Darvas | 1960（記憶） | ⚠M | 原典（本調査では未確認） |
| TS-149 | Secrets for Profiting in Bull and Bear Markets | Weinstein | 1988（記憶） | ⚠M | 原典（本調査では未確認） |
| TS-154 | Trade Like a Stock Market Wizard | Minervini | 2013（記憶） | ⚠M | 原典（本調査では未確認） |

### `01_techniques/06_moving_averages.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TI-030 | Granville's New Key to Stock Market Profits | Joseph Granville（Prentice-Hall） | 1963 | ⚠M | グランビルの法則の原典。出版社・年は記憶による |
| TI-031 | DEMA／TEMA の提案論文 | Patrick Mulloy（Technical Analysis of Stocks & Commodities） | 1994 | ⚠M | 題名・号は未確認 |
| TI-032 | Technical Analysis of the Financial Markets | John J. Murphy（New York Institute of Finance） | 1999 | ⚠M | 移動平均の一般的な解説書 |

### `01_techniques/07_oscillators_momentum.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TI-123 | New Concepts in Technical Trading Systems | J. Welles Wilder Jr. | 1978 | ⚠M | RSI・ATR・ADX・パラボリックSARの原典 |
| TI-124 | ストキャスティクスの考案 | George C. Lane | — | ⚠M | 題名・年は未確認 |
| TI-125 | MACDの考案 | Gerald Appel | — | ⚠M | 題名・年は未確認。ヒストグラムの追加者（Thomas Aspray）も記憶による |
| TI-126 | The New Technical Trader | Tushar Chande, Stanley Kroll（Wiley） | 1994 | ⚠M | StochRSI・CMOの出典（記憶による） |

### `01_techniques/08_volatility_and_trend_strength.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TI-221 | New Concepts in Technical Trading Systems | J. Welles Wilder Jr. | 1978 | ⚠M | ATR・DMI／ADX・パラボリックSARの原典 |
| TI-222 | Bollinger on Bollinger Bands | John Bollinger（McGraw-Hill） | 2001 | ⚠M | 出版社・年は記憶による |
| TI-224 | The Way of the Turtle | Curtis Faith（McGraw-Hill） | 2007 | ⚠M | 出版社・年は記憶による |

### `01_techniques/09_volume_breadth_sentiment.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TI-332 | Granville's New Key to Stock Market Profits | Joseph Granville | 1963 | ⚠M | OBVの出典（記憶による） |
| TI-336 | Mind Over Markets | Dalton, Jones, Dalton | 1990頃 | ⚠M | マーケットプロファイルの解説書（年は記憶） |
| TI-333 | McClellan Oscillator の考案 | Sherman McClellan, Marian McClellan | — | ⚠M | 題名・年は未確認。係数0.10／0.05も記憶による |
| TI-334 | The CBOE Volatility Index - VIX（ホワイトペーパー） | CBOE | — | ⚠M | 算出方法の公式文書。版・年は未確認 |
| TI-335 | AAII Sentiment Survey | American Association of Individual Investors（AAII） | — | ⚠M | 週次の強気・中立・弱気調査。仕様は記憶による |
| TI-337 | Winning on Wall Street | Martin Zweig | 1986 | ⚠M | ブレッドス・スラストの出典。年・閾値は記憶による |

### `01_techniques/10_alt_charts_relative_strength_mtf.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TI-421 | Trading for a Living | Alexander Elder（Wiley） | 1993 | ⚠M | トリプル・スクリーンの出典（年は記憶による） |
| TI-422 | Beyond Candlesticks | Steve Nison（Wiley） | 1994 | ⚠M | カギ足・Renko・スリーライン・ブレイクの解説（年は記憶による） |
| TI-423 | Point and Figure Charting | Thomas J. Dorsey（Wiley） | — | ⚠M | 版により年が異なる。作図規則の解説書 |
| TI-425 | Relative Rotation Graphs（RRG） | Julius de Kempenaer（RRG Research） | — | ⚠M | 考案者・発表年は記憶による |

### `03_evidence/01_academic_literature.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| EV1-120 | Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation | Lo, A. W.／Mamaysky, H.／Wang, J.／Journal of Finance 55(4) | 2000 | ⚠M | 第5節。記憶のみ・要原典確認。H&Sなどの技術パターンをカーネル回帰で定義し、条件付き収益分布を検定した基礎論文。Savinほか[EV1-046]とDawson–Steeley[EV1-049]の抄録が追試対象として言及する（間接的な存在確認）。検索記録に出たのは同題の書籍章（Lo 2002）[EV1-056]のみで、原論文の抄録は未確認 |
| EV1-121 | Filter Rules and Stock-Market Trading | Fama, E. F.／Blume, M. E.／Journal of Business 39(1) | 1966 | ⚠M | 第5節。記憶のみ・要原典確認。フィルタールール検証の古典。以後の売買ルール研究の出発点の一つ |
| EV1-122 | Price Movements in Speculative Markets: Trends or Random Walks | Alexander, S. S.／Industrial Management Review 2(2) | 1961 | ⚠M | 第5節。記憶のみ・要原典確認。フィルタールールを用いた初期の検証 |
| EV1-123 | Random Walks and Technical Theories: Some Additional Evidence | Jensen, M. C.／Benington, G. A.／Journal of Finance 25(2) | 1970 | ⚠M | 第5節。記憶のみ・要原典確認。技術的売買ルールをリスク調整後で再検証した古典 |
| EV1-124 | Efficient Capital Markets: A Review of Theory and Empirical Work | Fama, E. F.／Journal of Finance 25(2) | 1970 | ⚠M | 第5節。記憶のみ・要原典確認。効率的市場仮説の標準的な整理（弱い形・準強い形・強い形） |
| EV1-125 | Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test | Lo, A. W.／MacKinlay, A. C.／Review of Financial Studies 1(1) | 1988 | ⚠M | 第5節。記憶のみ・要原典確認。ランダムウォーク仮説の分散比検定。短期の収益に予測可能性があることを示した |
| EV1-126 | Beating the Foreign Exchange Market | Sweeney, R. J.／Journal of Finance 41(1) | 1986 | ⚠M | 第5節。記憶のみ・要原典確認。為替でのフィルタールールの収益性を検証した初期研究 |
| EV1-127 | Momentum Crashes | Daniel, K.／Moskowitz, T. J.／Journal of Financial Economics 122(2) | 2016 | ⚠M | 第5節。記憶のみ・要原典確認。モメンタム戦略の急落（市場の反転局面）の分析。Barroso–Santa-Clara[EV1-098]と併読 |
| EV1-128 | Evidence of Predictable Behavior of Security Returns | Jegadeesh, N.／Journal of Finance 45(3) | 1990 | ⚠M | 第5節。記憶のみ・要原典確認。個別株の短期（1か月）反転の古典 |
| EV1-129 | The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective | Lo, A. W.／Journal of Portfolio Management 30(5) | 2004 | ⚠M | 第5節。記憶のみ・要原典確認。適応的市場仮説の提案論文。Neelyほか[EV1-027]の抄録が「Lo (2004)」として言及する（間接的な存在確認） |
| EV1-130 | Heterogeneous Beliefs and Routes to Chaos in a Simple Asset Pricing Model | Brock, W. A.／Hommes, C. H.／Journal of Economic Dynamics and Control 22 | 1998 | ⚠M | 第5節。記憶のみ・要原典確認。ファンダメンタリストとトレンド追随型の異質なエージェントを置いた資産価格モデルの代表 |
| EV1-131 | Does Academic Research Destroy Stock Return Predictability? | McLean, R. D.／Pontiff, J.／Journal of Finance 71(1) | 2016 | ⚠M | 第5節。記憶のみ・要原典確認。学術発表後に株式のアノマリーがどの程度減衰するかを推定。「時間変化」の論点（EV2文書と併読） |
| EV1-132 | ... and the Cross-Section of Expected Returns | Harvey, C. R.／Liu, Y.／Zhu, H.／Review of Financial Studies 29(1) | 2016 | ⚠M | 第5節。記憶のみ・要原典確認。多重検定を考慮した有意水準の引き上げ（t値で3程度）を提案。方法論はEV2文書の領域 |
| EV1-133 | A Test for Superior Predictive Ability | Hansen, P. R.／Journal of Business and Economic Statistics 23(4) | 2005 | ⚠M | 第5節。記憶のみ・要原典確認。SPA検定。Hsu & Kuan[EV1-012]の抄録が「Hansen's SPA test」として言及する（間接的な存在確認） |
| EV1-134 | Have Capital Market Anomalies Attenuated in the Recent Era of High Liquidity and Trading Activity? | Chordia, T.／Subrahmanyam, A.／Tong, Q.／Journal of Accounting and Economics 58(1) | 2014 | ⚠M | 第5節。記憶のみ・要原典確認。流動性・取引活動の高まりとアノマリーの減衰の関係 |

### `03_evidence/02_methodology_behavioral_japan_ml.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| EV2-071 | Advances in Financial Machine Learning | M. López de Prado | 2018 | ⚠M | 書籍(Wiley)。パージ/エンバーゴ付きCV等の出典として想起。書誌は記憶のみ |
| EV2-072 | On technical analysis | D. P. Brown, R. H. Jennings | 1989 | ⚠M | RFS。過去価格が情報を持つ合理的モデル。記憶のみ |
| EV2-073 | Market statistics and technical analysis: the role of volume | L. Blume, D. Easley, M. O'Hara | 1994 | ⚠M | JF。出来高が情報を持つ合理的モデル。記憶のみ |
| EV2-074 | Prospect theory, mental accounting, and momentum | M. Grinblatt, B. Han | 2005 | ⚠M | JFE。含み益/含み損の保有者行動とモメンタム。記憶のみ |
| EV2-075 | Empirical asset pricing via machine learning | S. Gu, B. Kelly, D. Xiu | 2020 | ⚠M | RFS。ML資産価格の基準文献として想起。記憶のみ |

### `04_learning/02_books_japanese.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| LR-043 | 日本テクニカル分析大全 | 日本テクニカルアナリスト協会 編 | — | ⚠M | 版元・年は記憶／未確認 |
| LR-044 | 一目均衡表 | 細田悟一（一目山人）／経済変動総研 | — | ⚠M | 全七巻と記憶。年は未確認 |
| LR-046 | マーケットのテクニカル分析 | Murphy 邦訳／パンローリング | — | ⚠M | 邦訳版の年・版は未確認 |
| LR-047 | ワイルダーのテクニカル分析入門 | Wilder 邦訳／パンローリング | — | ⚠M | 同上 |
| LR-048 | 投資苑 | Elder 邦訳／パンローリング | — | ⚠M | 同上。続編は『投資苑2』 |
| LR-049 | オニールの成長株発掘法 | O'Neil 邦訳／パンローリング | — | ⚠M | 同上 |
| LR-050 | ミネルヴィニの成長株投資法 | Minervini 邦訳／パンローリング | — | ⚠M | 同上 |
| LR-051 | マーケットの魔術師 | Schwager 邦訳／パンローリング | — | ⚠M | 原著は1989年と記憶 |
| LR-052 | ファイナンス機械学習 | López de Prado 邦訳 | — | ⚠M | 出版社未確認 |
| LR-053 | ウォール街のランダム・ウォーカー | Malkiel 邦訳／日本経済新聞出版 | — | ⚠M | 版数は未確認 |
| LR-054 | 禁断の市場 | Mandelbrot 邦訳／東洋経済新報社 | — | ⚠M | 年は未確認 |
| LR-055 | まぐれ | Taleb 邦訳／ダイヤモンド社 | — | ⚠M | 年は未確認 |
| LR-056 | ファスト&スロー | Kahneman 邦訳／早川書房 | — | ⚠M | 文庫版の有無は未確認 |

### `04_learning/03_online_courses_and_sites.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| LR-061 | Investopedia | Investopedia | — | ⚠M | 講座の有無・料金は未確認 |
| LR-062 | Fidelity 学習センター | Fidelity Investments | — | ⚠M | 名称・内容は未確認 |
| LR-063 | Schwab 教育コンテンツ | Charles Schwab | — | ⚠M | 名称・内容は未確認 |
| LR-064 | TradingView ドキュメント | TradingView | — | ⚠M | 料金は未確認 |
| LR-065 | Financial Markets（Shiller） | Yale University | — | ⚠M | 公開形態・年は未確認 |
| LR-068 | 日本証券業協会 投資者向け教材 | 日本証券業協会 | — | ⚠M | 名称・内容は未確認 |
| LR-072 | トウシル | 楽天証券 | — | ⚠M | 記事の範囲は未確認 |
| LR-074 | NTAA 講座・セミナー | 日本テクニカルアナリスト協会 | — | ⚠M | 04 を参照 |

### `04_learning/04_organizations_journals_certifications.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| LR-078 | CMT Association（旧 MTA） | CMT Association | — | ⚠M | 名称変更の時期は LR-110 で確認（2017年7月）。他の事項は未確認 |
| LR-079 | International Federation of Technical Analysts | IFTA | — | ⚠M | 加盟団体・資格・誌は記憶 |
| LR-080 | 日本テクニカルアナリスト協会 | NTAA | — | ⚠M | 設立年・事業内容は未確認 |
| LR-081 | 日本証券アナリスト協会 | SAAJ | — | ⚠M | CMA制度・機関誌は記憶 |
| LR-082 | 国別協会（英国 STA 等） | 各協会 | — | ⚠M | 名称は記憶 |
| LR-083 | CMT 資格 | CMT Association | — | ⚠M | 試験構成・要件は未確認 |
| LR-084 | CFTe／MFTA | IFTA | — | ⚠M | 試験構成・要件は未確認 |
| LR-085 | NTAA の資格 | NTAA | — | ⚠M | 名称・略称は未確認 |
| LR-086 | 認定アナリスト（CMA） | SAAJ | — | ⚠M | テクニカル分析の扱いは未確認 |
| LR-087 | Journal of Technical Analysis | MTA | — | ⚠M | 刊行状況は未確認 |
| LR-088 | IFTA Journal | IFTA | — | ⚠M | 刊行状況は未確認 |
| LR-089 | Technical Analysis of Stocks & Commodities | 米国の出版社（社名は未確認） | — | ⚠M | 連載名は記憶 |
| LR-091 | 証券アナリストジャーナル | 日本証券アナリスト協会 | — | ⚠M | 刊行状況は未確認 |
| LR-092 | 会社四季報、日経ヴェリタス、ダイヤモンドZAi、日経マネー | 東洋経済新報社、日本経済新聞社、ダイヤモンド社、日経BP | — | ⚠M | 発行元は記憶 |

### `05_tools_data_code/01_charting_platforms_and_screeners.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TL-012 | 海外のチャート・スクリーナー製品（TradingView, StockCharts, Finviz, TC2000, MetaStock, thinkorswim, Interactive Brokers TWS, MetaTrader）の概要 | 各社 | — | ⚠M | 記憶のみ。公式ページ未確認。要公式確認 |
| TL-013 | 日本の証券会社ツール（楽天証券 マーケットスピード II、SBI証券 HYPER SBI 2、松井証券 ネットストック・ハイスピード、マネックストレーダー、kabuステーション）の概要 | 各証券会社 | — | ⚠M | 記憶のみ。公式ページ未確認。要公式確認 |
| TL-014 | 日本の情報サイト（株探、Yahoo!ファイナンス、みんかぶ）の概要 | 各社 | — | ⚠M | 記憶のみ。公式ページ未確認。要公式確認 |

### `05_tools_data_code/02_data_sources.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TL-127 | 日本の取引所・公的機関・証券会社サービスに関する一般知識（JPX 統計、東証の休業日・基準値段の調整・出来高の定義、kabuステーション API、立花証券 e支店、楽天証券の Excel 連携、e-Stat のアプリケーション ID、指数の権利） | 日本取引所グループ、各社・各機関 | — | ⚠M | 記憶のみ。ページ未確認。要公式確認 |

### `05_tools_data_code/04_javascript_and_other_libraries.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TL-340 | TradingView Charting Library（製品の配布形態・ライセンス） | TradingView | — | ⚠M | 記憶のみ。ページ未確認。要公式確認 |

### `05_tools_data_code/05_backtesting_frameworks.md`

| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |
|---|---|---|---|---|---|
| TL-424 | 東証の売買制度（売買単位、取引時間、板寄せ、値幅制限、呼値、配当落ちの基準値段調整） | 日本取引所グループ | — | ⚠M | 記憶のみ。呼値・値幅の数値は記載せず、02_japan/04 と JPX 公式で要確認 |

## URL のドメイン別件数

| ドメイン | 件数 |
|---|---:|
| consensus.app | 278 |
| github.com | 65 |
| chartschool.stockcharts.com | 19 |
| jpx.co.jp | 19 |
| luxalgo.com | 15 |
| oanda.jp | 13 |
| matsui.co.jp | 12 |
| en.wikipedia.org | 11 |
| wiley-vch.de | 11 |
| daiwa.jp | 9 |
| pypi.org | 9 |
| nomura.co.jp | 9 |
| thepatternsite.com | 8 |
| rakuten-sec.co.jp | 7 |
| kabu.com | 7 |
| tradingview.com | 5 |
| indexes.nikkei.co.jp | 5 |
| jpx-jquants.com | 5 |
| smbcnikko.co.jp | 4 |
| media.moneyforward.com | 4 |
| ml4trading.io | 4 |
| optuma.com | 3 |
| nexusfi.com | 3 |
| ta-lib.org | 3 |
| therighttrader.com | 3 |
| media.monex.co.jp | 3 |
| in.tradingview.com | 3 |
| barchart.com | 3 |
| abebooks.com | 3 |
| finance.matsui.co.jp | 3 |
| traders.co.jp | 3 |
| oreilly.com | 3 |
| store.stockcharts.com | 3 |
| schweitzer-online.de | 3 |
| stockcharts.com | 2 |
| prorealcode.com | 2 |
| gaitame.com | 2 |
| crexgroup.com | 2 |
| barchartsolutions.atlassian.net | 2 |
| info.monex.co.jp | 2 |
| search.sbisec.co.jp | 2 |
| myforex.com | 2 |
| media.paypay-sec.co.jp | 2 |
| city.osaka.lg.jp | 2 |
| mahersaham.com | 2 |
| gentosha-go.com | 2 |
| traders.com | 2 |
| support.matsui.co.jp | 2 |
| nli-research.co.jp | 2 |
| fsa.go.jp | 2 |
| books.google.com | 2 |
| goodreads.com | 2 |
| openlibrary.org | 2 |
| press.princeton.edu | 2 |
| opac.lib.hit-u.ac.jp | 2 |
| wowma.jp | 2 |
| s.minkabu.jp | 2 |
| minkabu.jp | 2 |
| pandas-datareader.readthedocs.io | 2 |
| stockcharts.com:443 | 1 |
| babypips.com | 1 |
| uatcdn.angelone.in | 1 |
| fyers.in | 1 |
| id.tradingview.com | 1 |
| nber.org | 1 |
| rpc.cfainstitute.org | 1 |
| cran.r-project.org | 1 |
| tessl.io | 1 |
| perlego.com | 1 |
| tapeboard.com | 1 |
| openaccess.city.ac.uk | 1 |
| forums.babypips.com | 1 |
| my.stockcharts.com | 1 |
| skills.sh | 1 |
| scribd.com | 1 |
| thortradecopier.com | 1 |
| blog.neostox.com | 1 |
| en.wikipedia.com | 1 |
| shareindia.com | 1 |
| shortform.com | 1 |
| mql5.com | 1 |
| gomarkets.com | 1 |
| asktraders.com | 1 |
| dailyforex.com | 1 |
| bollingerbands.us | 1 |
| mhprofessional.com | 1 |
| screener.in | 1 |
| my.tradingview.com | 1 |
| corporatefinanceinstitute.com | 1 |
| macroption.com | 1 |
| amibroker.com | 1 |
| jioinc.jp | 1 |
| kraken.com | 1 |
| steema.com | 1 |
| articles.stockcharts.com | 1 |
| wealthcharts.com | 1 |
| tradersagency.com | 1 |
| msdn.microsoft.com | 1 |
| search.r-project.org | 1 |
| wraquant.readthedocs.io | 1 |
| edgerater.com | 1 |
| help.tradestation.com | 1 |
| metastock.com | 1 |
| smd-am.co.jp | 1 |
| zai.diamond.jp | 1 |
| dime.jp | 1 |
| en.wikipedia-on-ipfs.org | 1 |
| swissquote.com | 1 |
| www-hp.fxtrade.co.jp | 1 |
| research.titanfx.com | 1 |
| forum.ninjatrader.com | 1 |
| financial-field.com | 1 |
| allabout.co.jp | 1 |
| freee.co.jp | 1 |
| finance.logmi.jp | 1 |
| wealth-lab.com | 1 |
| faq.sbisec.co.jp | 1 |
| curythm.com | 1 |
| sakigake.jp | 1 |
| diamond.jp | 1 |
| lfb.mof.go.jp | 1 |
| ma-cp.com | 1 |
| obd.swanlibraries.net | 1 |
| routledge.com | 1 |
| pring.com | 1 |
| pearson.com | 1 |
| findit.library.nd.edu | 1 |
| baumanrarebooks.com | 1 |
| katalog.bg.usz.edu.pl | 1 |
| tenlong.com.tw | 1 |
| agendabookshop.com | 1 |
| cir.nii.ac.jp | 1 |
| ci.nii.ac.jp | 1 |
| mypivots.com | 1 |
| cmtassociation.org | 1 |
| metatrader5.com | 1 |
| interactivebrokers.github.io | 1 |
| rakuten-bank.co.jp | 1 |
| api.edinet-fsa.go.jp | 1 |
| release.tdnet.info | 1 |
| e-stat.go.jp | 1 |
| alphavantage.co | 1 |
| twelvedata.com | 1 |
| eodhd.com | 1 |
| api.stlouisfed.org | 1 |
| pandas.pydata.org | 1 |
| numpy.org | 1 |
| scipy.org | 1 |
| statsmodels.org | 1 |
| numba.pydata.org | 1 |
| matplotlib.org | 1 |
| pandas-ta.dev | 1 |
| plotly.com | 1 |
| bokeh.org | 1 |
| docs.pytest.org | 1 |
| hypothesis.works | 1 |
| klinecharts.com | 1 |
| chartjs.org | 1 |
| echarts.apache.org | 1 |
| highcharts.com | 1 |
| apexcharts.com | 1 |
| d3js.org | 1 |
| d3fc.io | 1 |
| bennycode.com | 1 |
| proxy.golang.org | 1 |
| dotnet.stockindicators.dev | 1 |
| hmg3.github.io | 1 |
| repo1.maven.org | 1 |
| kernc.github.io | 1 |
| lean.io | 1 |
| pybroker.com | 1 |
| nautilustrader.io | 1 |
| vnpy.com | 1 |

## 関連文書

- [README](README.md)

## この文書の限界

- 台帳は各文書の出典表から機械的に集計したもので、URL の到達性は確認していない（作業環境からは外部サイトに接続できなかった）。
- ✅S は書誌情報の整合を確認したことを意味し、内容の正しさや全文の精読を意味しない。
