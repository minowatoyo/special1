# ボラティリティ系・トレンド強度系指標（ボリンジャー／ATR／ADX／SAR ほか）
> 要約: ボリンジャーバンド、ATR、ケルトナー、ドンチャン、エンベロープ、ヒストリカル・ボラティリティ、ADX／DMI、アルーン、パラボリックSAR、スーパートレンド、ボルテックスの式を、母集団標準偏差・Wilder平滑・種値・初期方向まで TA-Lib 0.8.3 と数値照合して明示する。
> ADX は一般的な解説の種値と TA-Lib の種値が異なる。構造のない乱数系列でも、終値がバンド外に出る頻度は約12%、ADX(14)>25の日は約40%ある。
> ATR に基づく損切り幅・ポジションサイズの考え方を示すが、ギャップや値幅制限では想定損失を超え得る。
> 最終更新: 2026-11-09

## 1. 共通の前提
- 式は TA-Lib 0.8.3 [TI-220] と合成データ（400本等）で照合済み。最初の有効値の添字を併記する。多出力の関数は出力線を同一添字に揃えて切り詰める。
- 全値が同一（値幅0）の系列での特殊出力: ATR・ADX・DX・+DI・VORTEX=0、%b=0.5、BandWidth=0、CHOP=100、Aroon Up=100、SAR・スーパートレンド＝価格。ストップ高・安に張り付いて値幅0が続く銘柄で現れる。

## 2. 計算式（照合済み）
```
# TR / ATR（Wilder、talib.TRANGE／ATR）
TR_t = max(H_t-L_t, abs(H_t-C_{t-1}), abs(L_t-C_{t-1}))          添字0は欠損、最初の有効値は添字1
ATR_n = mean(TR_1..TR_n)（添字n）;  ATR_t = (ATR_{t-1}*(n-1)+TR_t)/n     NATR = 100*ATR/C
# ボリンジャーバンド（talib.BBANDS 20,2,2,matype=0）
M=SMA(C,20); s=sqrt(mean((C_i-M)^2)) 直近20本（母集団、ddof=0）; U=M+2s; L=M-2s
%b=(C-L)/(U-L)（talib.PERCENTB は比率）  BandWidth=(U-L)/M（talib.BBW は×100）  既定ではBandWidth=4*s/M
# ケルトナー（talib.KC 20,10,2）  中心＝EMA20(TP)、TP=(H+L+C)/3;  上下＝中心±2*ATR10（Wilder）
# ドンチャン（talib.DONCHIAN 20）  U=max(H,直近20本、当足を含む)  L=min(L,同)  中心=(U+L)/2
# 加速バンド（talib.ACCBANDS 20）  U=SMA(H*(1+4*(H-L)/(H+L)),20)  L=SMA(L*(1-4*(H-L)/(H+L)),20)  中心=SMA(C,20)
# エンベロープ（TA-Libなし）  U=MA*(1+k)  L=MA*(1-k)
# 標準偏差（talib.STDDEV／VAR）は価格水準の母集団SD（ddof=0）。ヒストリカル・ボラは対数収益率から作る
HV = std(ln(C_t/C_{t-1}), n, ddof=1) * sqrt(A)       A＝年間営業日（米国約252、日本は概ね245前後、要確認）
パーキンソン: HV_P = sqrt( mean(ln(H/L)^2) / (4*ln2) ) * sqrt(A)       # 式は⚠M、未照合
# ADX／DMI（Wilder、talib.ADX／DX／PLUS_DI／MINUS_DI／PLUS_DM／MINUS_DM／ADXR）
up=H_t-H_{t-1}  down=L_{t-1}-L_t
+DM = up   if (up>down and up>0)      else 0
-DM = down if (down>up and down>0)    else 0
S(x)_t = S(x)_{t-1} - S(x)_{t-1}/n + x_t       （x＝+DM, -DM, TR。Wilderの合計型平滑）
PDI(+DI)=100*S(+DM)/S(TR)   MDI(-DI)=100*S(-DM)/S(TR)   DX=100*abs(PDI-MDI)/(PDI+MDI)
ADX_{2n-1}=mean(DX_n..DX_{2n-1});  ADX_t=(ADX_{t-1}*(n-1)+DX_t)/n       ADXR_t=(ADX_t+ADX_{t-n+1})/2
# アルーン（talib.AROON／AROONOSC、出力順は down, up）
Up=100*(n-直近の最高値からの経過本数)/n  Down は最安値  窓は当足を含む n+1 本、同値は最近の方  Osc=Up-Down
# ボルテックス（talib.VORTEX 14）  VM+=abs(H_t-L_{t-1})  VM-=abs(L_t-H_{t-1})  VI+=sum(VM+,n)/sum(TR,n)  VI-=sum(VM-,n)/sum(TR,n)
# チョピネス（talib.CHOP 14）  100*log10(sum(TR,n)/(max(H,n)-min(L,n)))/log10(n)
# VHF（talib.VHF 28）  (max(C,n)-min(C,n))/sum(abs(C_i-C_{i-1}),n)    窓＝直近n本の終値、差分はn個
```
種値と添字: ATR は添字n（TR1..TRnの平均）。+DM／-DM（平滑済み）は添字 n-1 で初出力し、その値は DM_1..DM_{n-1} の合計。DI・DXは添字n、ADXは添字2n-1、ADXRは3n-2（n=14で27／40）。TA-Lib は TR・DM とも「最初のn-1個の合計」を添字n-1の値として、添字nで平滑式を1回適用する。一般的な解説に見られる「最初のn個の合計を添字nの値とする」方式（ChartSchool [TI-204] は手順全体を本調査では未読）とは種値が異なり、ADX の差は最初の出力で0.085、+30本で0.29、+100本で0.004、+200本で4e-6だった（価格約100の合成データ）。ツール間比較では初期200本程度を捨てる。KC のATRは、最初の出力バー（既定で添字19）に直近10本のTRの平均を種値として置き、以後 Wilder 平滑する（通常のATR(10)の種値は添字10）。atrperiod が timeperiod 以下の設定で確認した。

## 3. 指標一覧（標準パラメータ・読み方・失敗パターン）
| 指標 | 標準パラメータ | 読み方 | 誤用・失敗パターン | TA-Lib |
|---|---|---|---|---|
| ATR | Wilder 14（Chandelier 22、Turtle 20） | 値幅の水準、損切り幅・ポジションサイズの基準 | 実装差（SMA型・EMA型）。ギャップ・値幅制限で過小評価 | ATR／NATR／TRANGE |
| ボリンジャー | 20本・±2σ。期間を変えるときは倍率も（50本なら2.5σ、検索要約）[TI-201] | %b、BandWidth、スクイーズ、バンドウォーク | 外側＝反転とみなす誤用（第4節）。BandWidthは変動係数に相当 | BBANDS／PERCENTB／BBW |
| ケルトナー | EMA20±2*ATR10（Raschke流）[TI-209] | トレンドに沿った動的な帯 | 原典は10日SMA（TP）±10日平均レンジ [TI-210]、20日とする説明もあり [TI-211] | KC |
| ドンチャン | 20本（Turtle流の20／55本突破は⚠M）[TI-212] | 高値更新・安値更新の機械的な突破 | 当足を含むため、突破判定は前足までの帯で行う | DONCHIAN |
| エンベロープ | 移動平均±k%（kは銘柄別） | 乖離率の閾値±k%を線として描いたものと等価 | 固定%幅はボラティリティの変化に追随しない | なし |
| ADX | 14。25超でトレンド、20未満でレンジとする慣行（⚠M）[TI-204][TI-205][TI-206] | トレンドの強さ（方向は+DI／-DI） | 遅い。低ADXでのDIクロスはダマシ。ADXの低下＝反転ではない。構造のない乱数系列でもADX(14)>25の日が約40%、>20が約62%ある（合成データ、日次σ1.5%、2000本×200経路） | ADX／ADXR／DX／PLUS_DI／MINUS_DI |
| アルーン | 25（Chande、⚠M）、TA-Lib既定14 [TI-213] | Upが高水準・Downが低水準で上昇トレンド | 横ばいで両線が振れる | AROON／AROONOSC |
| パラボリックSAR | AF 0.02、増分0.02、上限0.20 [TI-207][TI-208] | トレイリングストップ、売買の反転 | レンジで頻繁に反転（往復ビンタ） | SAR（拡張はSAREXT） |
| スーパートレンド | ATR10、倍率3 | ATR帯のラチェット式トレイリング | 同上。起源は未確認 | SUPERTREND |
| ボルテックス | 14 | VI+がVI-を上抜けで上昇トレンド（Botes・Siepman、2010 [TI-214]） | 他のDMI系と高相関 | VORTEX |
| CHOP／VHF | 14／28 | トレンド有無のレジームフィルタ | 閾値（例: CHOP 61.8／38.2）は慣行で未検証 | CHOP／VHF |

## 4. ボリンジャーバンドの詳細
- 標準偏差は母集団（n除算）が原典と説明され [TI-201]、TA-Lib もこれに一致する。標本標準偏差（n-1）なら帯の幅が sqrt(20/19)＝1.026倍に広がる。実装によっては典型価格 HLC/3 を使う、中心線をEMAとする。EMA中心の TA-Lib（matype=1）でも幅は価格の素の母集団SDで決まる（EMA周りの偏差ではない）。
- %b＝(C-L)/(U-L)、BandWidth＝(U-L)/M [TI-202][TI-203]。スクイーズは BandWidth が過去の一定期間（半年など）の最低水準に近い状態、バンドウォークは強いトレンドで終値が帯の外側近くに沿って推移する現象。原著（Bollinger on Bollinger Bands、2001）は3つの手法を提示するとされる（⚠M [TI-222]、細部は未確認）。①ボラティリティ・ブレイクアウト＝スクイーズ後の最初の帯外クローズの方向に追随、②トレンドフォロー＝上昇トレンド中の%b押しで、別系統の指標（例: MFI）の確認を得て参入、③反転＝W底・M天井で2回目の安値（高値）が帯の内側に収まり、確認指標が揃う場合。帯への接触そのものは売買シグナルにならない、と説明される。
- 終値が±2σバンドの外に出る頻度を合成データで測ると、正規収益率で合計11.8%（上6.4%、下5.4%）、裾の厚い t(3) 分布で12.2%だった（200経路×1500本、日次σ=1.5%）。「95%がバンド内」という素朴な理解は成り立たない。バンドの外＝売買シグナルではない。

## 5. ATRに基づく損切り幅・ポジションサイズ
```
損切り幅 = k*ATR_n          例: k=2〜3（慣行の幅、最適値ではない）
リスク額 R = 口座資金*r      例: r=1%（Turtle の「1ユニット」も 1N の値動きが口座の1%相当と説明される [TI-218]）
株数 = floor( R / (k*ATR_n) ) を売買単位の倍数に切り下げ                [TI-217]
Chandelier（買い）: 損切り = max(H,直近n本) - k*ATR_n     n=22,k=3 が古典的設定 [TI-215][TI-216]
```
注意: ATR が拡大すると、新高値がなくても Chandelier の損切りは下がる。ATR は過去の実現レンジであり、ギャップ（寄り付きの飛び）やストップ安・高では想定以上の損失が出る。日本の売買単位・値幅制限の制度は [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)。Turtle の詳細は Faith の著書（Way of the Turtle、2007、⚠M）[TI-224] と [05_practitioner_frameworks.md](05_practitioner_frameworks.md)。

## 6. パラボリックSARとスーパートレンドの手順（TA-Lib一致）
SAR（Wilder 1978 [TI-221]）。TA-Lib は初期方向を -DM（バー1）で決める。(L_0-L_1)>(H_1-H_0) かつ >0 なら下降、それ以外は上昇（バー1の判定に限り、前足の高安にバー1自身の値を用いる）。上昇なら SAR=L_0、EP=H_1、下降なら SAR=H_0、EP=L_1、AF=0.02。以後、各足 t で:
- 上昇中: L_t<=SAR なら反転（SAR=EP を出力、ただし max(H_{t-1},H_t) 以上に切り上げ。AF=0.02、EP=L_t、下降へ）。反転しなければ SAR を出力し、H_t>EP なら EP=H_t、AF=min(AF+0.02,0.20)。次の SAR＝SAR+AF*(EP-SAR) を min(L_{t-1},L_t) 以下に制限。
- 下降中は対称。最初の出力は添字1。
この手順は 90通り（30系列×3設定）で TA-Lib と一致した。乱数系列（日次σ1.5%、2000本×200経路）で終値とSARの位置関係が入れ替わる回数は250本あたり、AF 0.01／上限0.1で15.5回、既定0.02／0.2で24.5回、0.04／0.4で36.5回と、AFを速くするほど増える。

SuperTrend（TA-Lib 10,3）:
```
hl2=(H+L)/2   BU=hl2+m*ATR   BL=hl2-m*ATR            ATRはWilder（talib.ATR）
FU_t = BU_t if (BU_t<FU_{t-1} or C_{t-1}>FU_{t-1}) else FU_{t-1}
FL_t = BL_t if (BL_t>FL_{t-1} or C_{t-1}<FL_{t-1}) else FL_{t-1}
trend_t = +1 if (trend_{t-1}==-1 and C_t>FU_{t-1}); -1 if (trend_{t-1}==+1 and C_t<FL_{t-1}); 他は据置
ST_t = FL_t（trend=+1）／FU_t（trend=-1）
初期: 最初の有効バー（添字n）で FU=BU, FL=BL, trend=+1（上昇）に固定。有効値以前の trend は0
```
60系列で一致した。初期方向が常に「上昇」である点は TA-Lib 0.8.3 の仕様で、他実装は初期方向の決め方が異なり得る（未確認）。その場合は序盤だけ値が食い違う。ATR を単純平均にすると全期間で値が変わる。

## 7. 限界・日本株での留意点
- 全般: これらはボラティリティやトレンド強度の事後的な記述統計であり、将来方向の予測力は指標自体からは得られない。学術的に個別に検証した文献は今回の調査では確認できなかった（未確認）。技術的ルール全般の検証は [../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md)。
- ADX・SAR・スーパートレンドはレンジで機能せず、トレンド相場でも反転時に利益を返す。トレンド有無の判定（ADX、CHOP）とトレイリング型は同じ価格情報に依存し、独立な確認にならない（[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md) の冗長性）。
- 日本株: ストップ高・安で値幅が頭打ちになるとATRやバンド幅が過小に出る。寄り付きのギャップは TR に含まれる。分割・権利落ちは調整後株価で計算する。
- 実装ヒント: ドンチャンの突破は shift(1)。SAR・スーパートレンドは経路依存なので、評価区間の開始日を変えると序盤の値が変わる。閾値（ADX 25 など）は固定せず、銘柄別の分布と取引コスト込みで検証する。スクイーズは BandWidth の直近125本における百分位が低位（閾値は仮置き）といった相対基準で判定する。

## 関連文書
- [06_moving_averages.md](06_moving_averages.md)、[07_oscillators_momentum.md](07_oscillators_momentum.md)、[09_volume_breadth_sentiment.md](09_volume_breadth_sentiment.md)、[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md)
- [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)

## この文書の限界
- 検索スニペットでの確認が中心で、教科書・原典（Wilder、Bollinger、Chande など）や各社ヘルプの本文は未読。ADXの閾値、Chandelierの倍率、ATRの係数 k は慣行である。
- ボリンジャーの母集団SDは Wikipedia ミラーの脚注の検索要約による。ケルトナーの原典定義は出典間で食い違い（10日と20日）、未解決である。
- 数値（バンド外の頻度、ADX種値差）は合成データ上の筆者計算。TA-Lib の挙動は 0.8.3（PyPI、2026-10-28公開）での確認で、他版・他実装では異なり得る（確認日: 2026-11-09、要版数確認）。
- ヒストリカル・ボラの年間営業日、パーキンソンの式、スーパートレンドの起源は未確認または未照合。

## 出典
| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TI-201 | Bollinger Bands | Wikipedia | — | https://en.wikipedia.org/wiki/Bollinger_Bands | ✅S | 20本・2σ。母集団SDの脚注はミラー版の検索要約、倍率の調整例（50本で2.5） |
| TI-202 | Bollinger Bands %B | Barchart | — | https://www.barchart.com/education/technical-indicators/bollinger_bands_percent | ✅S | %bの式 |
| TI-203 | Bollinger Band Width | therighttrader | — | https://therighttrader.com/learn/indicators/bollinger-band-width | ✅S | BandWidthの式（検索要約） |
| TI-204 | Average Directional Index (ADX) | StockCharts ChartSchool | — | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx | ✅S | 14期間、TR・+DM・-DMの手順の第1段のみ確認 |
| TI-205 | Average Directional Index (ADX) | Barchart | — | https://www.barchart.com/education/technical-indicators/average_directional_index | ✅S | 存在のみ確認 |
| TI-206 | ADX（関数ページ） | TA-Lib | — | https://ta-lib.org/functions/adx | ✅S | 存在のみ確認 |
| TI-207 | Parabolic SAR | Wikipedia | — | https://en.wikipedia.org/wiki/Parabolic_SAR | ✅S | 反復式、AFの規則（検索要約） |
| TI-208 | Parabolic SAR (SAR) | TradingView | — | https://www.tradingview.com/wiki/Parabolic_SAR_(SAR) | ✅S | 既定 0.02／0.02／0.20（検索要約） |
| TI-209 | Using Keltner Channels | StockCharts ChartWatchers | 2008 | https://articles.stockcharts.com/article/articles-chartwatchers-2008-08-using-keltner-channels/ | ✅S | Raschke流 EMA20±2*ATR10（検索要約） |
| TI-210 | Keltner Channels | LuxAlgo | — | https://www.luxalgo.com/library/concept/keltner-channels.md | ✅S | 原典（10日SMA）と現代版の説明 |
| TI-211 | Keltner Bands | Barchart | — | https://barchartsolutions.atlassian.net/wiki/spaces/CMDTYV/pages/1094287786/Keltner+Bands | ✅S | 20日SMA／20日平均レンジの記述（原典定義の食い違い） |
| TI-212 | Donchian Channels (DC) | TradingView | — | https://www.tradingview.com/wiki/Donchian_Channels_(DC) | ✅S | 20日高値・安値・中心 |
| TI-213 | Aroon Indicator Formula | WealthCharts | — | https://wealthcharts.com/kb/category/charts/indicator-formulas/Aroon-Indicator-Formula | ✅S | 式（検索要約） |
| TI-214 | Vortex | LuxAlgo | — | https://www.luxalgo.com/library/concept/vortex.md | ✅S | Botes・Siepman、2010、VM／TR（検索要約） |
| TI-215 | Chandelier Stop | LuxAlgo | — | https://www.luxalgo.com/library/concept/chandelier-stop.md | ✅S | 22期間・倍率3 |
| TI-216 | Chandelier Exit | NexusFi | — | https://nexusfi.com/a/indicators/chandelier-exit | ✅S | 最高値-k*ATR |
| TI-217 | ATR for Position Sizing and Stops | Traders Agency | — | https://tradersagency.com/blog/atr-position-sizing-stop-loss-placement | ✅S | 株数＝リスク額÷損切り幅 |
| TI-218 | Turtle Trading Risk-Adjusted Position Size Calculator | TradingView | — | https://in.tradingview.com/script/PGzeZOFD-Turtle-Trading-Risk-Adjusted-Position-Size-Calculator | ✅S | N＝ATR(20)、1ユニットの定義（検索要約） |
| TI-220 | TA-Lib（PyPI JSON） | PyPI | 2026 | https://pypi.org/pypi/TA-Lib/json | ✅S | 0.8.3（2026-10-28公開）。数値照合は同版 |
| TI-221 | New Concepts in Technical Trading Systems | J. Welles Wilder Jr. | 1978 | — | ⚠M | ATR・DMI／ADX・パラボリックSARの原典 |
| TI-222 | Bollinger on Bollinger Bands | John Bollinger（McGraw-Hill） | 2001 | — | ⚠M | 出版社・年は記憶による |
| TI-224 | The Way of the Turtle | Curtis Faith（McGraw-Hill） | 2007 | — | ⚠M | 出版社・年は記憶による |
