# 出来高・市場の広がり（ブレッドス）・センチメント系指標
> 要約: OBV、A/Dライン、チャイキン・マネー・フロー、チャイキン・オシレーター、フォース・インデックス、PVT、相対出来高、出来高プロファイル（POC・バリューエリア）の定義を整理し、TA-Lib に対応関数がある指標は 0.8.3 と数値照合した。
> 市場全体の指標（騰落ライン・騰落レシオ・マクレラン・TRIN・新高値新安値・移動平均上回り銘柄比率）とセンチメント指標（VIX・日経VI・プット・コール・レシオ・AAII）の世界共通の定義も扱う。
> 出来高が将来リターンを予測するという主張の頑健性は学術的に限定的で、経験則の多くは検証が不十分である。日本固有の需給指標は別文書に委ねる。
> 最終更新: 2026-11-09

## 1. 出来高分析の位置づけとエビデンス
- 理論: Blume・Easley・O'Hara (1994) は、出来高が価格だけからは分からない情報の質を伝え、価格と出来高の系列が有益になり得ること、市場統計を使う投資家のほうが成績が良いことを均衡モデルで示した [TI-320]。テクニカル分析を学習過程の自然な構成要素と位置づける。
- 実証: 条件付きボラティリティと出来高は正に相関し、大きな価格変動の後に出来高が増える（Gallant・Rossi・Tauchen 1992）[TI-322]。過去の出来高はモメンタムの大きさと持続性を予測し、高出来高の勝ち組は反転が速い（Lee・Swaminathan 2000）[TI-321]。一方、出来高から将来リターンを予測する際の事後的利得は小さく（米国で年率0.73%相当）、他の主要市場ではほぼ消える（Wang ほか 2017）[TI-323]。44本の研究・468推定値のメタ分析は、出版バイアスと推定のばらつきが大きいと結論する（Bajzík 2021）[TI-324]。Gold (2004) は、大きな価格反応が通常の出来高を伴うほうが、高出来高の場合より反転しにくいという仮説を提示する（要旨の文字化けあり）[TI-325]。
- したがって出来高は、価格変動の「質」を読む補助情報として扱い、単独で売買根拠にする経験則（下表）は仮説にとどめる。

| 局面 | よくある解釈（経験則） | 注意 |
|---|---|---|
| 上昇＋出来高増 | 需給の裏付けがあるトレンド継続 | 材料出尽くしの天井でも出来高は増える |
| 上昇＋出来高減 | 勢いの鈍化 | 押し目局面では減るのが通常 |
| 下落＋出来高急増（セリング・クライマックス） | 投げ売りによる底打ち候補 | 下落加速の途中でも起きる。確認が必要 |
| 下落＋出来高減（売り枯れ） | 売り圧力の低下 | 流動性の低下とも区別できない |
| ブレイクアウト＋出来高増 | 突破の信頼度が高い | Gold (2004) の仮説とは必ずしも整合しない [TI-325] |

## 2. 計算式（TA-Lib照合済み）
```
# 出来高の移動平均・相対出来高
VMA_n = SMA(V, n)           RVOL_n = V_t / mean(V_{t-n}..V_{t-1})      当足を含まない直前n本（talib.RVOL、n=20、最初の有効値は添字n）
PVO = 100*(EMA12(V)-EMA26(V))/EMA26(V)                                 talib.PVO（matype=1）
# OBV（talib.OBV）  OBV_0=V_0; OBV_t=OBV_{t-1}+V_t（C_t>C_{t-1}）／-V_t（C_t<C_{t-1}）／+0（同値）
# 資金フロー乗数  CLV_t=((C-L)-(H-C))/(H-L)=(2C-H-L)/(H-L)            H=L のとき 0
# A/Dライン（talib.AD）  AD_t=AD_{t-1}+CLV_t*V_t（添字0から累積、AD_{-1}=0）
# チャイキン・マネー・フロー（talib.CMF、20）  CMF_t=sum(CLV*V,20)/sum(V,20)            最初の有効値は添字19
# チャイキン・オシレーター（talib.ADOSC、3-10）  ADOSC=EMA3(AD)-EMA10(AD)
#   2本のEMAの種値は AD_0（単純平均ではない）。最初の出力は添字9。SMA種値との差は序盤のみで、100本後には小数4桁まで一致する
# フォース・インデックス（talib.EFI、13）  FI_t=(C_t-C_{t-1})*V_t     EFI=EMA13(FI)  種値はFI_1..FI_13の単純平均（添字13）
# PVT（talib.PVT）  PVT_0=0; PVT_t=PVT_{t-1}+V_t*(C_t-C_{t-1})/C_{t-1}
# NVI／PVI（talib.NVI／PVI）  基準値1000。NVI_t=NVI_{t-1}*(C_t/C_{t-1})（V_t<V_{t-1} の日のみ）、他は据置。PVIは V_t>V_{t-1}
# VWAP／VWMA は [06_moving_averages.md]、MFI は [07_oscillators_momentum.md]
```
| 指標 | 標準 | 読み方 | 誤用・失敗パターン |
|---|---|---|---|
| OBV | 累積（Granville、1963、⚠M [TI-332]） | 新高値に伴う上昇か、価格とのダイバージェンス | 水準は起点依存で絶対値に意味がない。大商いの1日で飛ぶ |
| A/Dライン | 累積 [TI-303] | 終値が当日レンジのどこにあるか×出来高 | ギャップを無視（レンジ内の位置のみ）。レンジ0の足は寄与0 |
| CMF | 20本（21本とする説明もあり）[TI-305] | 0超で買い圧力優勢、0未満で売り圧力優勢 | 窓の端で急変。レンジが狭い足の影響 |
| チャイキン・オシレーター | 3-10 EMA [TI-301] | A/Dラインの勢い | 種値の流儀差。A/Dの欠点を引き継ぐ |
| フォース・インデックス | 13 EMA（Elder、慣行）[TI-304] | 0超で買い優勢。2日EMAなど短期版も（⚠M） | 出来高の外れ値に敏感 |
| PVT | 累積 | OBVより価格変化率を反映 | 起点依存 |
| RVOL／出来高移動平均 | 20／25本 | 平常時比の出来高急増（2〜3倍超などは任意の慣行） | 時間帯・イベント日の補正がない |
実装差: TA-Lib は OBV を V_0 から始めるが、0から始める実装もある（形は同じ、水準が違う）。CMF の窓（20／21）、Chaikin のEMA種値、A/D の起点で値が変わる。

## 3. 出来高プロファイル（VAP）とマーケットプロファイル
- 出来高プロファイル（Volume at Price）は、期間内の出来高を価格帯（ビン）ごとに積み上げたヒストグラム。POC（Point of Control）は出来高最大の価格帯、バリューエリア（VA）はPOCを含む連続した価格帯で総出来高の約70%を占める範囲、その上下端が VAH／VAL [TI-307][TI-308][TI-310]。70%は慣例値である。
- 一般的な作り方: POCから始め、現在のVAの上と下で次の2ビンずつの出来高合計を比べ、大きい側の2ビンを追加することを累積70%以上になるまで繰り返す（合成データ40ビンの試算でPOC＋上下に広げ72.8%をカバー）。1ビンずつ追加する、同値の扱い、ビン幅の決め方で VAH／VAL は変わる。ビン幅は呼値（制度は [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)）以上、かつATRの一定割合などで決める。
- マーケットプロファイル（TPO）は出来高ではなく「その価格に滞在した時間枠の数」を数える [TI-309]。トレンド日には出来高POCとTPO POCが乖離し得る。Steidlmayer（CBOT）や Dalton ほか『Mind Over Markets』（1990年頃）が源流とされる（⚠M [TI-336]）。
- 必要データ: 正確な出来高プロファイルにはティックまたは分足が要る。日足から当日の出来高をレンジ全体に均等配分する近似は粗い。データは [../05_tools_data_code/02_data_sources.md](../05_tools_data_code/02_data_sources.md)。
- POC／VAをサポート・レジスタンスとみなす、VA外への動きを「不均衡」とみなす見方は実務家の主張であり、今回の調査では学術的な検証を確認できなかった（未確認）。

## 4. 市場全体の指標（ブレッドス）
```
Adv／Dec／Unch＝値上がり／値下がり／変わらず銘柄数    AdvVol／DecVol＝それぞれの出来高
騰落ライン_t = 騰落ライン_{t-1} + (Adv_t - Dec_t)
騰落レシオ(n) = sum(Adv, n) / sum(Dec, n) * 100                       n=25 が標準 [TI-313]
マクレラン・オシレーター = EMA19(Adv-Dec) - EMA39(Adv-Dec)          EMA係数 0.10 と 0.05（⚠M [TI-333]）
  比率調整版: RANA=(Adv-Dec)/(Adv+Dec)*1000;  MO=EMA19(RANA)-EMA39(RANA);  サメーション・インデックス_t=SI_{t-1}+MO_t
アームズ指数(TRIN) = (Adv/Dec) / (AdvVol/DecVol)                     [TI-311][TI-312]
移動平均上回り銘柄比率 = 100*count(C_i > SMA_n(C_i))/N              n=50や200
新高値-新安値 = 52週（または年初来）高値更新銘柄数 - 安値更新銘柄数       定義は提供元で異なる
ブレッドス・スラスト（Zweig）= EMA10(Adv/(Adv+Dec))  0.40未満から10日以内に0.615超でシグナル（⚠M [TI-337]、数値は記憶）
```
| 指標 | 読み方 | 失敗パターン・留意点 |
|---|---|---|
| 騰落ライン | 指数との乖離（指数は新高値でも騰落ラインは未更新）を市場の広がりの低下とみる | 乖離が数か月続くことがある。時価総額加重の指数と同一母集団でない |
| 騰落レシオ | 100％が均衡、120％前後超で買われ過ぎ、70％前後未満で売られ過ぎ [TI-314] | 120％超が長期に続く例がある [TI-315]。他の指標・ニュースと併用 [TI-316]。母集団の市場区分の再編（2022年、⚠M）で時系列が不連続になり得る |
| マクレラン | 0の上下、極値、サメーション・インデックスの方向 | 母集団（NYSE等）の定義依存。日本株への適用は一般的でない（未確認） |
| TRIN | 1が中立、1超は出来高が下落銘柄に偏る弱気側、1未満は上昇銘柄に偏る強気側（一般的説明、検索要約。式は [TI-311][TI-312]） | 極端な値は強い一方向の日に出て、反転の保証はない。出来高の定義（立会外）に依存 |
| 新高値−新安値 | 市場の強さの確認 | 定義（52週か年初来か）で別物。新規上場・分割の扱い |
| 移動平均上回り比率 | 高水準＝強い広がり。低水準＝売られ過ぎ圏 | 閾値は慣行。市場全体が動くと同時に動く |
日本固有の需給指標（信用残、空売り比率、投資主体別売買動向など）の定義は [../02_japan/05_supply_demand_indicators.md](../02_japan/05_supply_demand_indicators.md)。

## 5. センチメント指標
| 指標 | 定義 | 読み方 | 留意点 |
|---|---|---|---|
| VIX | 米国S&P 500オプション価格から算出する今後30日の期待変動率（CBOE、⚠M [TI-334]） | 急上昇＝恐怖、低水準＝楽観。恐怖指数 | 方向を示さない。水準が長く低位／高位に留まる |
| 日経平均VI | 今後30日間の日経平均の変動率に対する市場の見方を数値化した指標 [TI-318]。日経225オプション価格に基づくインプライド・ボラティリティ指標（算出要領は日本経済新聞社の資料で要確認、⚠M）。VIに連動する先物（JPX上場）と、満期1か月に調整した先物指数が別にある [TI-317][TI-319] | 日本版恐怖指数。急落時に上昇しやすい [TI-318] | 方向性は示さない [TI-318]。現物VIと先物・先物指数を混同しない |
| プット・コール・レシオ（PCR） | プット出来高（または建玉）÷コール出来高（または建玉） | 極端な高水準は悲観、低水準は楽観の逆張り指標として使われる（⚠M） | 株式のみか指数込みか、出来高か建玉かで別物。ヘッジ需要を含む |
| AAII 投資家センチメント調査 | 米国個人投資家協会が毎週実施する調査の強気・中立・弱気の比率（⚠M [TI-335]） | 長期平均からの乖離（極端な強気・弱気）を逆張りの材料にする | 標本の偏り。週次で遅い |
- 学術: Brown・Cliff は投資家センチメントと短期の市場リターンを分析 [TI-326]。Lee・Jiang・Indro は、センチメントの変化とボラティリティ・超過リターンの関係を分析 [TI-327]。Bandopadhyaya・Jones はPCRとVIXをセンチメント指標として比較 [TI-328]。Smales は投資家の「恐怖」と市場リターンの関係を扱う（要旨は未精読）[TI-329]。欧州では、VIX／VSTOXXやPCRなどを含む複数の代理変数が将来リターンを予測するとの報告がある [TI-331]。Baker・Wurgler は、投資家センチメントが銘柄のクロスセクションのリターンに影響すると論じる（NBERワーキングペーパーの記録、要旨は未精読）[TI-330]。
- 限界: 極端値の逆張りは、極端な状態が長引く間に損失を出す。定義・データ提供元の差が大きく、日本市場への一般化（日経VI、信用評価損益率など）は別途検証が必要。詳細は [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md)。

## 6. 日本株での留意点・実装ヒント
- 出来高は株式分割・併合で遡及調整されたか確認する（未調整だと出来高移動平均・OBVが歪む）。銘柄間比較は売買代金や回転率（出来高÷発行済株式数）で行う。
- 出来高に立会外取引やPTSを含むか否かは、データ提供元で異なる（要確認）。
- 特別気配・ストップ高安の日は出来高がゼロ付近または極端になり、CMF・A/D・OBV に外れ値を作る。
- 市場全体の指標は、構成銘柄の入れ替え（新規上場・上場廃止）と市場区分の再編に注意し、ライブ母集団とバックテスト母集団を揃える。
- 日中の出来高は時間帯で偏る（寄り付き・引け前に集中）。RVOL は同時刻の過去平均で比較する。

## 関連文書
- [06_moving_averages.md](06_moving_averages.md)（VWAP）、[07_oscillators_momentum.md](07_oscillators_momentum.md)（MFI）、[08_volatility_and_trend_strength.md](08_volatility_and_trend_strength.md)、[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md)
- [../02_japan/05_supply_demand_indicators.md](../02_japan/05_supply_demand_indicators.md)、[../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md)

## この文書の限界
- スニペット中心の確認で、取引所・証券会社・論文の本文は未読。OBV の原典、マクレランの係数、ブレッドス・スラストの閾値、VIX の算出、AAII の仕様は筆者の知識（⚠M）で、検索で独立に確認していない。
- McClellan の式、新高値新安値の公式定義、日本市場での騰落レシオの母集団は未確認。
- RVOL の定義（当足を除く直前n本）、ADOSC／EFI の種値などは TA-Lib 0.8.3（PyPI、2026-10-28公開）での確認であり、他版・他実装では異なり得る（確認日: 2026-11-09、要版数確認）。VA作成の試算は合成データ。
- 出来高と将来リターンの関係は要旨レベルで確認した。個別論文の標本・手法は精査していない。

## 出典
| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TI-301 | Chaikin Oscillator Formula | Microsoft（MSDN） | — | https://msdn.microsoft.com/en-us/library/dd456722(v=vs.140) | ✅S | 3日EMAと10日EMAの差（検索要約） |
| TI-303 | chaikinAD {TTR} | R（TTR）マニュアル | — | https://search.r-project.org/CRAN/refmans/TTR/html/chaikinAD.html | ✅S | A/Dラインの実装（存在確認） |
| TI-304 | wraquant.ta.volume のソース | wraquant | — | https://wraquant.readthedocs.io/en/stable/_modules/wraquant/ta/volume.html | ✅S | 価格変化×出来高のEMA（既定13とする検索要約） |
| TI-305 | CMF（解説） | EdgeRater | — | https://edgerater.com/docs/trading-strategies-signals/cmf.htm | ✅S | 窓20または21（検索要約） |
| TI-307 | Volume profile indicators: basic concepts | TradingView | — | https://www.tradingview.com/wiki/Volume_Profile | ✅S | POC・VAの基本 |
| TI-308 | The Value Area ... 70% of the Volume | NexusFi | — | https://nexusfi.com/articles/trading/VA | ✅S | バリューエリア70% |
| TI-309 | Time Price Opportunity charts explained | TradingView | — | https://in.tradingview.com/support/solutions/43000725590 | ✅S | TPOの説明 |
| TI-310 | Point of Control | LuxAlgo | — | https://www.luxalgo.com/library/concept/point-of-control.md | ✅S | POC・70%の範囲 |
| TI-311 | Arms Index (TRIN) (Indicator) | TradeStation ヘルプ | — | https://help.tradestation.com/10_00/eng/tradestationhelp/elanalysis/indicator/arms_index__trin__indicator_.htm | ✅S | 式（検索要約） |
| TI-312 | Custom Formula Collection | MetaStock | — | https://www.metastock.com/customer/resources/formulas?id=4 | ✅S | TRIN式、McClellan の項目の存在（式は未確認） |
| TI-313 | 騰落レシオ（用語集） | SBI証券 | — | https://search.sbisec.co.jp/v2/popwin/info/home/pop6040_mailyougo.html | ✅S | 25日合計の式 |
| TI-314 | 騰落レシオ（用語集） | OANDA証券 | — | https://www.oanda.jp/lab-education/dictionary/updown_ratio/ | ✅S | 120／70の目安 |
| TI-315 | 騰落レシオの解説 | マネーフォワード | — | https://media.moneyforward.com/articles/8495 | ✅S | 120％超が長期化した例（2023年初） |
| TI-316 | 騰落レシオの解説 | 松井証券 | — | https://www.matsui.co.jp/stock/study/article/up-down-ratio/ | ✅S | 他指標・ニュースとの併用 |
| TI-317 | 日経平均VI先物 | 日本取引所グループ | — | https://www.jpx.co.jp/derivatives/products/vi/225-vi-futures/ | ✅S | VI先物の商品ページ（存在確認。本文未読） |
| TI-318 | 日経平均VI（用語集） | OANDA証券 | — | https://www.oanda.jp/lab-education/dictionary/nikkei_vi/ | ✅S | 30日、方向性なし、恐怖指数 |
| TI-319 | Nikkei 225 VI futures index factsheet | 日本経済新聞社 | — | https://indexes.nikkei.co.jp/nkave/factsheet?idx=nk225vifi | ✅S | VI先物指数のファクトシート（満期1か月の合成との検索要約） |
| TI-320 | Market Statistics and Technical Analysis: The Role of Volume | Blume, Easley, O'Hara（J. Finance） | 1994 | https://consensus.app/papers/details/b27a550164cb5b09818a6e7ad3a0f49b/ | ✅S | 要旨のみ確認 |
| TI-321 | Price Momentum and Trading Volume | Lee, Swaminathan（J. Finance） | 2000 | https://consensus.app/papers/details/8959743b159b5d34a32ff39f6e8dfb7e/ | ✅S | 要旨のみ確認 |
| TI-322 | Stock Prices and Volume | Gallant, Rossi, Tauchen（Rev. Financial Studies） | 1992 | https://consensus.app/papers/details/c97774607bc85f7683239d1be5f43a0f/ | ✅S | 要旨のみ確認 |
| TI-323 | Dynamic trading volume and stock return relation: Does it hold out of sample? | Wang, Qian, Wang（Int. Rev. Financial Analysis） | 2017 | https://consensus.app/papers/details/da61988b61a7594385427b47c4a62f38/ | ✅S | 要旨のみ確認 |
| TI-324 | Trading volume and stock returns: A meta-analysis | Bajzík（Int. Rev. Financial Analysis） | 2021 | https://consensus.app/papers/details/ebbe31d7f7405a9e96329c5257d64ec5/ | ✅S | 要旨のみ確認 |
| TI-325 | Price-volume relationships and stock returns | Gold（Accounting and Finance Research） | 2004 | https://consensus.app/papers/details/5e2a12209f215983b5671ed8e1cf846f/ | ✅S | 要旨は文字化けあり |
| TI-326 | Investor Sentiment and the Near-Term Stock Market | Brown, Cliff（J. Empirical Finance） | 2001 | https://consensus.app/papers/details/f29c772c8cdb57b2bd55e9183532ed12/ | ✅S | 記録上の年は2001、掲載年は要確認 |
| TI-327 | Stock market volatility, excess returns, and the role of investor sentiment | Lee, Jiang, Indro（J. Banking & Finance） | 2002 | https://consensus.app/papers/details/7ed5becceace571f83c77df53d2ada3b/ | ✅S | 要旨は未精読 |
| TI-328 | Measures Of Investor Sentiment: A Comparative Analysis Put-Call Ratio Vs. Volatility Index | Bandopadhyaya, Jones | 2011 | https://consensus.app/papers/details/d3c7f3b70eec5a6c9a6717cd2983d195/ | ✅S | 要旨は未精読 |
| TI-329 | The importance of fear: investor sentiment and stock market returns | Smales（Applied Economics） | 2017 | https://consensus.app/papers/details/c19ef1aba36656f8b09585296267cc3e/ | ✅S | 要旨は未精読 |
| TI-330 | Investor Sentiment and the Cross-Section of Stock Returns | Baker, Wurgler（NBER WP） | 2003 | https://consensus.app/papers/details/c886e98d906152a68037026b6b98cdc1/ | ✅S | 記録は2003年のWP。要旨は未精読 |
| TI-331 | A Reappraisal of the Causal Relationship between Sentiment Proxies and Stock Returns | Reis, Pinho（J. Behavioral Finance） | 2020 | https://consensus.app/papers/details/249b55a3ed3e510ab895fd37a16d5ef5/ | ✅S | 欧州S&P 350、VIX・VSTOXX・PCR等 |
| TI-332 | Granville's New Key to Stock Market Profits | Joseph Granville | 1963 | — | ⚠M | OBVの出典（記憶による） |
| TI-336 | Mind Over Markets | Dalton, Jones, Dalton | 1990頃 | — | ⚠M | マーケットプロファイルの解説書（年は記憶） |
| TI-333 | McClellan Oscillator の考案 | Sherman McClellan, Marian McClellan | — | — | ⚠M | 題名・年は未確認。係数0.10／0.05も記憶による |
| TI-334 | The CBOE Volatility Index - VIX（ホワイトペーパー） | CBOE | — | — | ⚠M | 算出方法の公式文書。版・年は未確認 |
| TI-335 | AAII Sentiment Survey | American Association of Individual Investors（AAII） | — | — | ⚠M | 週次の強気・中立・弱気調査。仕様は記憶による |
| TI-337 | Winning on Wall Street | Martin Zweig | 1986 | — | ⚠M | ブレッドス・スラストの出典。年・閾値は記憶による |
