# 個別株向け実務家フレームワーク：ダーバス・CAN SLIM・ステージ分析・ミネルヴィニ・タートル・リバモア・コナーズ・エルダー・ボリンジャー・IBD RS
> 要約: 個別株の売買で広く紹介される10の枠組みについて、公開情報の範囲でルールの骨子、必要データ、日本株適用上の注意、既知の批判と検証状況を整理した。
> 数値は複数資料で一致したものを断定し、食い違うもの（CAN SLIMの成長率、ミネルヴィニの52週安値比、タートルの手仕舞い日数等）は併記した。
> 日本ではモメンタムが弱く短期反転が強いという実証があり、トレンドフォロー型の枠組みを日本株に移す際の前提として最初に示した。
> 最終更新: 2026-11-09

表記: `[TS-nnn]` は出典ID。⚠Mは記憶に基づく。教育・研究目的であり売買の推奨ではない。

## 1. 一覧と日本株の共通注意
| 枠組み | 型 | 必要データ | 検証状況（検索で確認できた範囲） |
|---|---|---|---|
| ダーバス・ボックス | 新高値ブレイク | 日足OHLCV | 独立検証は未確認。近縁の52週高値モメンタムは米国で利益[TS-163] |
| CAN SLIM | 成長＋ブレイク | 四半期EPS、株数、機関投資家、RS、指数 | 独立検証は未確認 |
| ステージ分析 | 週足の長期MAトレンド | 週足OHLCV、指数 | 技術ルールの利益は期間依存[TS-162] |
| ミネルヴィニ（TT／VCP） | トレンド＋収縮ブレイク | 日足、52週高安、RS順位 | 実績は自己申告、独立検証は未確認 |
| タートル | チャネルブレイク（先物） | 先物日足、ATR | 商品先物では支持[TS-160]、株式は限定的[TS-162] |
| リバモア | ピボタルポイント | 日足OHLCV、出来高 | 定性的で検証不能 |
| コナーズ RSI(2) | 短期平均回帰 | 日足終値 | 日本は1か月反転が強い[TS-166][TS-167]。2日では未確認 |
| エルダー | 多時間軸 | 週足＋日足 | 独立検証は未確認 |
| ボリンジャー Method I〜III | バンド手法 | 日足＋出来高系指標 | 独立検証は未確認 |
| IBD RSレーティング | 相対モメンタム順位 | 全銘柄の12か月価格 | 日本のモメンタムは弱い[TS-165][TS-168] |

**日本株の共通注意**
- 日本の実証: 東証1975〜97年は1か月の反転が顕著でモメンタムは観察されなかった[TS-166]。コントラリアン戦略は1か月から3年の全ホライズンで有利との報告[TS-167]。Asnessは、バリューとモメンタムを一体の系として見れば日本の結果も他国と整合的でノイズの範囲内だと論じ[TS-165]、Hanauerは市場状態の頻繁な転換で説明する[TS-168]。結論は未確定だが、中期のトレンドフォロー型（CAN SLIM、ミネルヴィニ、RS）を日本株に移すと米国並みの成績にならない可能性がある。
- 価格調整: 株式分割・併合は遡及調整し、権利落ちの機械的な窓に注意する（→01_price_structure.md §6・§8）。
- 値幅制限・特別気配: ストップ高張り付き中は出来高が乏しく、ブレイクアウトの約定が困難。逆指値は窓で不利に約定する。制度は../02_japan/04_tse_market_rules_and_chart_effects.md（要公式確認、確認日: 2026-11-09）。
- 空売り・信用: 貸借銘柄か否か、逆日歩、信用規制で売り側ルールの再現性が変わる（→../02_japan/05_supply_demand_indicators.md）。
- 決算・会計: 3月期決算が多く決算発表後の窓が大きい。会計基準（日本基準／IFRS）の混在でEPS比較に注意（要確認）。
- データ: 上場廃止・銘柄入替を含む生存者バイアスのないデータが必要（→../05_tools_data_code/02_data_sources.md）。流動性フィルタ（売買代金）を必ず置く。

## 2. ダーバス・ボックス（Darvas Box）
- ルール[TS-140]: 新高値の後、3日間その高値が更新されなければボックス上限とする。下限は上限確定後の安値で、次の3日間割られないもの。上抜けで買い（逆指値）、損切りはボックス下限のわずか下に置き、新しいボックスが切り上がるたびに引き上げる（下げない）。出来高や業績の併用に触れる解説もある（検索要約）。
- 食い違い: 高安の判定が日中値か終値か、「3日」の数え方は資料で異なる[TS-140]。原典は[TS-143]（⚠M・未確認）。
- 必要データ: 日足OHLCV（日中高安）。
- 日本株: 日本語の「ボックス相場」（レンジ）とは別物。値幅制限でボックス確定が機械的にずれる。
- 批判: 独立検証は未確認。実質は新高値ブレイク＋トレーリングストップで、近縁の証拠は52週高値への近さがモメンタム利益の大部分を説明するという研究[TS-163]。

## 3. CAN SLIM（O'Neil）
| 要素 | 内容 | 数値例（異説） |
|---|---|---|
| C | 当期四半期EPS成長 | 前年同期比+25%以上[TS-144]。解説により18〜20%、20%超などもある[TS-145] |
| A | 年間EPS成長 | 3〜5年で年20%超〜24%超（資料差）[TS-145] |
| N | 新製品・新経営陣・新高値 | 52週高値の15%以内（スクリーン例）、後版は10%以内との記述[TS-183] |
| S | 需給 | 発行株数が少ない・自社株買い（5,000万株未満のスクリーン例[TS-183]）、ブレイク時の出来高増 |
| L | 主導株 | RSレーティング80以上（スクリーン例）[TS-183] |
| I | 機関投資家 | 一定の保有があり過剰保有でない（スクリーン例[TS-183]） |
| M | 市場の方向 | 指数が上昇局面（フォロースルー日で確認、⚠M） |
- テクニカル面: ベース（カップ・ウィズ・ハンドル[TS-043]等）からのピボット上抜けと出来高増で買う。損切りは購入価格の7〜8%下とされる（⚠M）。原典はHow to Make Money in Stocks[TS-146]。
- 日本株: 四半期決算短信のEPSを使うが決算期のずれや会計基準差に注意。機関投資家の保有データは米国の13Fのように銘柄別に揃わず、代替は大量保有報告書・信用残など（→JP2文書）。
- 批判: 閾値が版・解説で食い違う[TS-144][TS-145]。独立検証は未確認。成長・モメンタム因子の一種と解釈でき、書籍の事例は事後選択の可能性がある。

## 4. ステージ分析（Weinstein）
- 4ステージ[TS-147]: S1底固め（30週MAが横ばい）、S2上昇（価格が上向き30週MAの上。底固めの抵抗を出来高増で突破）、S3天井圏（MAが平ら）、S4下降（価格が下向きMAの下）。買うのはS2のみ。相対力はMansfield型で、ゼロ線の上で上昇が望ましい。
- 日足では150日が30週相当。Mansfield RS: `RS = 株価/指数、MRS = (RS / SMA52週(RS) - 1) * 100`[TS-147]。原典はSecrets for Profiting in Bull and Bear Markets（1988頃）[TS-149]（⚠M）。
```
ma30 = SMA(週足終値, 30);  slope = ma30 / ma30[-4] - 1        # 4週で傾きを判定
S2: 終値>ma30 かつ slope>0 ／ S4: 終値<ma30 かつ slope<0 ／ それ以外: S1またはS3（直前がS4ならS1）
閾値ε（横ばいの許容）は設計例
```
- 必要データ: 週足OHLCVと指数（TOPIX等）。日本株: 祝日週は4日。30週線は遅く、レンジ相場でダマシが多い（論理的な指摘）。
- 批判: ステージ境界の判定が主観的と指摘される[TS-147]。移動平均系ルールの米国株での利益は期間に集中し、空売りに依存した[TS-162]。

## 5. ミネルヴィニ（トレンドテンプレートとVCP）
- トレンドテンプレート[TS-150]: (1)株価が150日・200日MAの上、(2)150日MA＞200日MA、(3)200日MAが少なくとも1か月上向き（4〜5か月が望ましい）、(4)50日MAが150日・200日MAの上、(5)株価が50日MAの上、(6)52週安値から30%以上上、(7)52週高値から25%以内（近いほど良い）、(8)RS順位70以上（IBD）。(6)は25%とするコミュニティ実装もあり食い違う（検索要約）。
- VCP[TS-153]: 押しが2〜4回（5〜6回も）起き、各押しが前回より浅く（目安は約半分とする説明が多いが、1回目20〜35%、2回目10〜20%…と具体例を示す資料もあり不一致）、出来高が枯れ、最終収縮の高値をピボットとして上抜けで買う。ブレイク日の出来高拡大が望ましい（50日平均の2倍などは作者ごとの基準）。損切りは浅く置くとされる（数値は⚠M）。原典はTrade Like a Stock Market Wizard（2013頃）[TS-154]（⚠M）。
- 必要データ: 日足OHLCV、52週高安、RS順位（自作→§11）。
- 日本株: RS順位はユニバースを定義して自作する。流動性の低い銘柄と、グロース市場の高ボラティリティ銘柄の扱いを決める。
- 批判: 実績は自己申告で、第三者検証は本調査では確認していない。テンプレートはステージ2＋52週高値モメンタム[TS-163]の組合せに近い。VCPの独立検証は未確認。

## 6. タートル・システム
- ルール[TS-156][TS-155]: システム1は20日高値（安値）のブレイクで建て、システム2は55日。初期ストップは2N。同一市場で0.5Nごとに最大4ユニットまで追加。システム1は直前のシグナルが勝ちなら見送り、システム2が保険という記述がある（出典は複数ページ）。Donchianの4週間ルールが20日の由来（⚠M）。
- N（ATR）: `N_t = (19*N_{t-1} + TR_t) / 20`、TR=max(H-L, |H-前C|, |L-前C|)[TS-155]。ユニット数量は口座の1%をNで割る形（`Unit = 0.01*Equity / (N*1ポイントの金額)`、⚠M）。ポジション上限（同一市場4、相関の高い群6、片方向12など）は記憶による（⚠M）。
- 手仕舞いは異説: システム1が10日・システム2が20日の逆ブレイクとする版と、20日の逆ブレイクとする版がある[TS-155]。ATRを30日・上限2ATRとする記述（一つの解説ページ）もあり、20日のNと矛盾する。
- 原典はThe Way of the Turtle（2007）[TS-159]。必要データ: 先物の連続足（ロール方式を固定）、ATR、売買代金。
- 日本株: 原型は先物で、空売り・レバレッジ・流動性が株と異なる。日経225先物・TOPIX先物などでの再現は可能だが、個別株ではスリッページと空売り制約が大きい。
- 検証: 商品先物で48年・28市場のうち22市場以上でチャネル戦略が費用後に正[TS-160]。DJIA構成銘柄の技術ルールの利益は1960年代中頃〜80年代中頃に集中した[TS-162]。公開成功談は1980年代の標本に偏る（論理的な指摘）。

## 7. リバモア（ピボタルポイント）
- 概念[TS-172]: 最小抵抗線の方向に動く。ピボタルポイントは性格が変わる価格で、反転型（底固めや売り・買いクライマックスの後）と継続型（トレンド内の持ち合い）。先回りせず確認を待ち、ブレイク後に伸びなければ警告とみなす。How to Trade in Stocks（1940）に由来する整理と要約される[TS-172]。
- 背景: Reminiscences of a Stock Operator（1923）はLivermoreの経歴に基づく脚色的な物語[TS-174]。個人の成績は第三者検証が乏しい。
- 検証: 規則が定性的で検証不能。近縁はレンジ・ブレイク（→01 §5）。必要データは日足OHLCVと出来高。日本株では共通注意（値幅制限・窓）を適用する。

## 8. コナーズ RSI(2)（短期平均回帰）
- ルール[TS-175]: 買い＝終値が200日SMAの上、かつRSI(2)が10未満（5未満とする版もある）。手仕舞い＝終値が5日SMAを上回る。売りは鏡像（終値が200日SMAの下、RSI(2)が90〜95超）。Connors & Alvarez（2008）[TS-176]に帰される。
- RSI(2): `RSI = 100 - 100/(1+RS)`、RS＝n=2の平均上昇/平均下落。n=2では平滑化方式（Wilder／SMA／EMA）で値が大きく変わるため実装を固定する（→07_oscillators_momentum.md）。
- 必要データ: 調整後日足終値（200日以上）。
- 日本株: 東証は1か月反転が強くモメンタムが弱い[TS-166][TS-167]ので平均回帰には追い風の可能性があるが、ホライズンが異なり（2日対1か月）未検証。ストップ安連続では「売られ過ぎ」が続き約定できない。回転が速く費用・呼値の影響が大きい。空売り制約。
- 批判: 公開されている検証の多くはブログやベンダーのバックテスト。損切りなしで暴落局面の損失が大きい（⚠M）。標本・費用・生存者バイアスを再点検する。

## 9. エルダー（トリプルスクリーン）
- 構造[TS-177]: 第1スクリーン（長期足、例：週足）でトレンドを判定（MACDヒストグラムの傾き、または13期間EMAの傾き）。第2スクリーン（日足）でトレンドと逆行するオシレーターのシグナル（Stochastic等。Force Indexも使われる、⚠M）を待つ。第3はトレンド方向への逆指値で入る。時間軸比は約5倍（⚠M）。
- 考案年は1985年または1986年とする記述があり[TS-178]、書籍はTrading for a Living（1993）[TS-179]。
- 必要データ: 週足と日足。日本株: 週足の祝日週に注意。批判: 独立検証は未確認で、再現実装ごとに指標・閾値が異なり同一システムとして評価しにくい。

## 10. ボリンジャー Method I／II／III
- バンド: 20期間SMA±2σが標準（→08_volatility_and_trend_strength.md）。`%b = (終値-下限)/(上限-下限)`、`BandWidth = (上限-下限)/中心線`。
- Method I（ボラティリティ・ブレイクアウト）: スクイーズ（BandWidthの低水準）後にバンド外へ抜ける動き。Method II（トレンドフォロー）: 価格の強さと指標（出来高系など）の強さが揃ったときに順張り。Method III（反転）: バンドへの接触自体は売買信号でなく、指標との乖離で転換を判断。Method IVは書籍後の追加で、連続終値のバンド外とBandWidthで確認する[TS-180][TS-181]。Method IIの具体的閾値（%bとMFIの水準）は書籍に記載があるが未確認（⚠M）。
- 必要データ: 日足OHLCVと出来高系指標（MFI等）。日本株: 日本の表示では±1σ〜±3σの併記が多い（⚠M・要確認）。批判: 独立した性能検証は本調査では未確認。

## 11. IBD 相対力（RS）レーティング
- 定義: 1〜99の百分位。直近12か月の加重リターン（直近四半期を重く）を全銘柄で順位化する。IBDの正式式は非公開で、一般の再現式は`0.4*ROC(63) + 0.2*ROC(126) + 0.2*ROC(189) + 0.2*ROC(252)`である（第三者実装）[TS-182]。
```
score = 0.4*roc63 + 0.2*roc126 + 0.2*roc189 + 0.2*roc252       # roc_n = C/C[-n] - 1（調整後終値）
RS_rating = ceil(percentrank(score, ユニバース) * 99)            # 1〜99。ユニバースと除外条件を固定
```
- Mansfield RS（指数比の52週平均乖離）とは別物。必要データ: 全銘柄の調整後終値（252営業日以上）。日本株: ユニバース（プライムのみか全上場か）、低流動性の除外、上場1年未満の扱い、分割調整を決める。
- 注意: 直近1か月を除外しない設計のため、日本で強い1か月反転[TS-166]の影響を受ける可能性がある（仮説）。日本ではモメンタム自体が弱い[TS-165][TS-168]。

## 12. 総括
- 多くはトレンド確認（MA・RS）×位置（新高値・ブレイク）×浅い損切りの組合せで、コナーズは逆張りである。共通の落とし穴は、データスヌーピング、生存者バイアス、市場局面依存、費用である。
- 各枠組みは「仮説」として自分のユニバースでウォークフォワード検証する。日本株では値幅制限、空売り制約、決算の窓、モメンタムの弱さを前提に条件を調整する。

## 関連文書
- 01_price_structure.md／02_chart_patterns.md（カップ・ウィズ・ハンドル）／06_moving_averages.md／07_oscillators_momentum.md／08_volatility_and_trend_strength.md／10_alt_charts_relative_strength_mtf.md
- ../02_japan/04_tse_market_rules_and_chart_effects.md／../02_japan/05_supply_demand_indicators.md／../03_evidence/01_academic_literature.md／../03_evidence/02_methodology_behavioral_japan_ml.md

## この文書の限界
- 書籍の原典（Darvas、O'Neil、Weinstein、Minervini、Faith、Elder、Connors、Bollinger）は未読で、ブローカー教育ページ・ベンダー解説・コミュニティ実装の検索要約に依拠した。数値は資料間で食い違うものを併記した。
- 日本語資料での裏取りと、日本株への適用例（日本版スクリーナー条件など）は確認できていない（検索回数の上限に到達）。日本株の注意は一般知識と実証論文に基づく。
- 売買ルールの損切り幅、ポジション上限、フォロースルー日の定義、Method IIの閾値は記憶による（⚠M）。IBD RSの式は第三者の再現で、IBDの公式式ではない。
- 各枠組みの成績主張（自己申告・書籍の事例）は検証していない。

## 出典

> 検証タグ: ✅S=検索結果・論文レコード等で書誌と要点を確認（本文は未読）／⚠M=記憶のみ／❓=要確認。URLは検索結果に現れたものだけを記載し、無いものは「—」とした。

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TS-043 | ChartSchool: Cup With Handle | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/cup-with-handle | ✅S | カップの深さ・ハンドル期間 |
| TS-140 | Darvas Box Strategy: rules, entries, stops | Neostox（ブローカー教育ブログ） | — | https://blog.neostox.com/charting/darvas-box-strategy-rules-entries-stops-worked-trade | ✅S | ボックス上限下限・逆指値・ストップ引上げ |
| TS-143 | How I Made $2,000,000 in the Stock Market | Darvas | 1960（記憶） | — | ⚠M | 原典（本調査では未確認） |
| TS-144 | CAN SLIM | Wikipedia | — | https://EN.wikipedia.com/wiki/CAN_SLIM | ✅S | C=前年同期比+25%以上等の記述 |
| TS-145 | CANSLIM Stocks: Overview, Methodology, and Strategy | ShareIndia（証券会社教育ページ） | — | https://www.shareindia.com/knowledge-center/share-market/canslim-stocks-meaning | ✅S | 7要素。閾値は資料で18〜25%等 |
| TS-146 | How to Make Money in Stocks（要約ページ） | O'Neil（要約：Shortform） | 1988（初版・記憶） | https://www.shortform.com/summary/how-to-make-money-in-stocks-complete-investing-system-summary-william-j-oneil | ✅S | 原書の要約ページの存在を確認。数値は未確認 |
| TS-147 | Weinstein Stage Analysis | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/weinstein-stage-analysis.md | ✅S | 4ステージ・30週MA・Mansfield RS |
| TS-149 | Secrets for Profiting in Bull and Bear Markets | Weinstein | 1988（記憶） | — | ⚠M | 原典（本調査では未確認） |
| TS-150 | Trend Template by Mark Minervini | ProRealCode | — | https://prorealcode.com/prorealtime-market-screeners/trend-template-mark-minervini | ✅S | 8条件。52週安値比は30% |
| TS-153 | Volatility Contraction Pattern（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/volatility-contraction-pattern/ | ✅S | 収縮回数・出来高枯れ・ピボット |
| TS-154 | Trade Like a Stock Market Wizard | Minervini | 2013（記憶） | — | ⚠M | 原典（本調査では未確認） |
| TS-155 | Automating Classic Market Methods in MQL5 (Part 5): The Original Turtle Trading Rules | MQL5 | — | https://www.mql5.com/en/articles/23448 | ✅S | Nの式・ユニット追加 |
| TS-156 | Revisiting the Turtle Traders: Applying Lessons to a New Market | GO Markets（ブローカー記事） | — | https://www.gomarkets.com/en/articles/revisiting-the-turtle-traders-applying-lessons-to-a-new-market | ✅S | 20/55日ブレイクと初期ストップ2N |
| TS-159 | The Way of the Turtle | Faith | 2007 | — | ✅S | 書名・年は検索要約。本文未読 |
| TS-160 | Trend-following trading strategies in commodity futures: A re-examination | Szakmary, Shen, Sharma／J. Banking & Finance | 2010 | — | ✅S | DOI 10.1016/j.jbankfin.2009.08.004 |
| TS-162 | The Rise and Fall of Technical Trading Rule Success | Taylor／J. Banking & Finance | 2014 | — | ✅S | DOI 10.1016/j.jbankfin.2013.12.004 |
| TS-163 | The 52-Week High and Momentum Investing | George, Hwang／Journal of Finance 59(5) | 2004 | — | ✅S | 52週高値への近さがモメンタムを説明 |
| TS-165 | Momentum in Japan: The Exception that Proves the Rule | Asness／Journal of Portfolio Management | 2011 | — | ✅S | DOI 10.3905/jpm.2011.37.4.067 |
| TS-166 | The Winner–Loser Effect in Japanese Stock Returns | Iihara, Kato, Tokunaga／Japan and the World Economy | 2004 | — | ✅S | DOI 10.1016/j.japwor.2003.06.001 |
| TS-167 | Sources of contrarian profits in the Japanese stock market | Chou, Wei, Chung／J. Empirical Finance | 2007 | — | ✅S | DOI 10.1016/j.jempfin.2006.07.003 |
| TS-168 | Is Japan Different? Evidence on Momentum and Market Dynamics | Hanauer／International Review of Finance | 2014 | — | ✅S | DOI 10.1111/irfi.12024 |
| TS-172 | Livermore Pivotal Point（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/livermore-pivotal-point/ | ✅S | ピボタルポイント・最小抵抗線 |
| TS-174 | Reminiscences of a Stock Operator | Lefèvre | 1923 | — | ✅S | 脚色的な物語との記述。本文未読 |
| TS-175 | RSI 2（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/rsi-2/ | ✅S | RSI(2)逆張りの解説 |
| TS-176 | Short Term Trading Strategies That Work | Connors, Alvarez | 2008 | — | ✅S | 書名・年は検索要約。本文未読 |
| TS-177 | Elder's triple screening strategy | AskTraders（ブローカー系教育サイト） | — | https://www.asktraders.com/learn-to-trade/trading-guide/elders-triple-screening-strategy/ | ✅S | 3スクリーン構造 |
| TS-178 | What is the Triple Screen Trading System? | DailyForex | 2020 | https://dailyforex.com/forex-articles/2020/09/elder-triple-screen-system/151378 | ✅S | 考案年1985／1986の記述 |
| TS-179 | Trading for a Living | Elder | 1993 | — | ✅S | 書名・年は検索要約。本文未読 |
| TS-180 | Methods Explanation（Bollinger Bandsの手法I-III） | BollingerBands.us（John Bollinger） | — | https://bollingerbands.us/help-methods.php | ✅S | 手法I〜IV |
| TS-181 | Bollinger on Bollinger Bands | Bollinger／McGraw-Hill | 2001（年は記憶） | https://www.mhprofessional.com/bollinger | ✅S | 書籍紹介ページ。年は記憶 |
| TS-182 | RS Rating Multi-Timeframe（IBD型RSの再現スクリプト） | TradingViewコミュニティ | — | https://www.tradingview.com/script/lsLzfQqs-RS-Rating-Multi-Timeframe | ✅S | 40/20/20/20加重は第三者の再現式 |
| TS-183 | CANSLIM Stocks by William O'Neil（スクリーン定義） | Screener.in（ユーザー作成スクリーン） | — | https://screener.in/screens/954590/canslim-stocks-by-william-oneil | ✅S | スクリーン例の数値 |
