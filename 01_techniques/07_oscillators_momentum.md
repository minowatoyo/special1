# オシレーター・モメンタム系指標（RSI／ストキャスティクス／MACD ほか）
> 要約: RSI、ストキャスティクス、StochRSI、MACD／PPO、CCI、ウィリアムズ%R、ROC／モメンタム、TRIX、アルティメット・オシレーター、MFI、サイコロジカルライン、ダイバージェンスの定義を、TA-Lib に対応関数がある指標は 0.8.3 と数値照合した式で示す。
> RSI は Wilder 平滑と国内で多い単純合計型（Cutler 型）で値が大きく異なり、ストキャスティクスも日本式（分子・分母を合計）と欧米式（%Kの平均）で別物になる。
> 主な限界は、トレンド相場での「張り付き」、パラメータ感度、同系統指標の冗長性である。学術検証は市場・期間で結果が割れている。
> 最終更新: 2026-11-09

## 1. 共通の注意
- 目的は買われすぎ／売られすぎ、転換、モメンタムの測定。前提は平均回帰するレンジであり、トレンド相場では極値圏に長く留まる（張り付き）。合成データ（σ=1.5%/日、2000日×200経路）で RSI(14)>70 の日数割合は、ドリフト0で4.8%、0.05%/日で6.7%、0.1%/日で9.3%、0.2%/日で16.3%（筆者計算）。
- TA-Lib 0.8.3 [TI-122] は複数線の出力を共通の開始添字に揃えて切り詰める（STOCH(5,3,3) は添字8、STOCHRSI(14,5,3) は添字20、MACD は添字33）。値自体は単独計算と一致する。
- 以下の式のうち TA-Lib に対応関数があるものは 0.8.3 と数値照合済み（最大誤差 1e-11 程度以下）。Cutler型RSI、日本式ストキャスティクス、サイコロジカルラインは対応関数がなく、筆者実装で式の整合のみ確認した。移動平均の種値の流儀は [06_moving_averages.md](06_moving_averages.md)。

## 2. 計算式（TA-Lib対応分は照合済み）
```
# RSI（Wilder、talib.RSI）  U=max(P_t-P_{t-1},0)  D=max(P_{t-1}-P_t,0)
AU_n=mean(U_1..U_n)  AD_n=mean(D_1..D_n)       種値＝最初のn個の単純平均、添字nで初出力
AU_t=(AU_{t-1}*(n-1)+U_t)/n  AD_t も同様       (t>n)
RSI_t=100*AU_t/(AU_t+AD_t)                      # =100-100/(1+AU/AD)
# Cutler型（国内に多い単純合計型）  RSI_t=100*sum(U,直近n)/(sum(U)+sum(D))
# ストキャスティクス  HH=max(H,直近n)  LL=min(L,直近n)
%K(Fast %K)=100*(C_t-LL)/(HH-LL)               HH=LLなら0（TA-Lib）
Fast %D=SMA(%K,d)   Slow %K=Fast %D   Slow %D=SMA(Slow %K,d)     # talib.STOCHF／STOCH（既定 5,3,3）
# 日本式（野村）  %D=100*sum(C-LL,m)/sum(HH-LL,m)   SD(スロー%D)=SMA(%D,y)   # n=9,m=3,y=3 など
# StochRSI（talib.STOCHRSI）  fastk=100*(RSI-min(RSI,m))/(max(RSI,m)-min(RSI,m))  fastd=SMA(fastk,d)
# MACD  MACD=EMA12(P)-EMA26(P)  Signal=EMA9(MACD)  Hist=MACD-Signal    PPO=100*(EMA12-EMA26)/EMA26
# CCI  TP=(H+L+C)/3  CCI=(TP-SMA(TP,n))/(0.015*MD)  MD=mean(abs(TP_i-SMA(TP,n)))、直近n本の平均絶対偏差
# ウィリアムズ%R  %R=-100*(HH-C)/(HH-LL)  = Fast %K - 100（厳密に等しい）
# MOM=P_t-P_{t-n}   ROC=100*(P_t/P_{t-n}-1)   ROCP=P_t/P_{t-n}-1   ROCR=P_t/P_{t-n}   ROCR100=100*ROCR
# TRIX  E3=EMA(EMA(EMA(P,n),n),n)   TRIX=100*(E3_t/E3_{t-1}-1)      # TA-Libは価格そのもの（対数価格版との差は小さい）
# アルティメット  BP=C-min(L,C_prev)  TR=max(H,C_prev)-min(L,C_prev)  A_k=sum(BP,k)/sum(TR,k)
UO=100*(4*A7+2*A14+A28)/7
# MFI  TP=(H+L+C)/3  RMF=TP*V  PMF=sum(RMF,TP上昇日,n)  NMF=sum(RMF,TP下落日,n)  MFI=100*PMF/(PMF+NMF)
# サイコロジカルライン  PL=100*(直近12日のうち終値が前日比プラスの日数)/12        # TA-Libになし
```
TA-Lib固有の挙動（0.8.3、合成データで確認）:
- RSI: 最初の出力は添字n。値が全く動かない系列は50を返す（他実装は0やNaNとなり得る）。CMO は `2*RSI-100`（Wilder平滑）で、Chande 原案（単純合計型、⚠M）とは単一サンプルで平均12.6pt異なる。
- MACD: 速いEMAの種値は「遅いEMAの種値の添字（25）で終わる直近12本の単純平均」であり、添字11を種値とする標準的な再帰とは異なる。差は最初の出力で0.047（価格約100）、+50本で1.1e-5、+100本で2.6e-9。pandas `ewm(adjust=False)` 起点との差は最初0.29、+50本で0.005、+200本で5e-8。MACDFIX は係数が 0.15（速い側）と 0.075（遅い側）の固定値で、2/13＝0.154 と 2/27＝0.074 とは異なる（本線のみ確認）。APO／PPO の既定 matype は 0.8.3 で EMA(1)。版により既定が違い得るため matype を明示する。
- CCI は平均絶対偏差。分母に標準偏差を使う記述もあり（Steema [TI-127]）、その場合は尺度が約1.25倍（正規分布の場合）ずれる。
- 全値が同一の系列（値幅0）での出力: RSI=50、STOCH／STOCHF／STOCHRSI／WILLR（0＝買われすぎ側の端）／CCI／MFI／ULTOSC=0、%b=0.5、CHOP=100、Aroon Up=100。ストップ高張り付きで値幅0が続く銘柄はこの特殊値を返す。
- 同一性: WILLR＝Fast%K-100、CMO＝2*RSI-100、PPO＝APO／EMA26×100、APO＝MACD本線（種値の違いのみ）。

## 3. 指標一覧（標準パラメータ・読み方・失敗パターン）
| 指標 | 標準パラメータ | 読み方 | 誤用・失敗パターン | TA-Lib |
|---|---|---|---|---|
| RSI | Wilder 14 [TI-123]。9日などの短縮版も使われる（⚠M）が、国内各社の既定は未確認 | 70超／30未満（楽天証券の目安も70／30 [TI-101]）。50が中立。Wilderのフェイラー・スイング | 上昇相場で70超に張り付き逆張り負け。実装差（第4節） | RSI |
| ストキャスティクス | 欧米14-3-3（慣行、考案者は Lane [TI-124]、⚠M）、国内はn=5や9・3・3が多い [TI-104]、MT4既定5-3-3 [TI-105] | 80／20圏でのクロス。%Kと%Dの交差 | レンジ外では極値に張り付き。高速版はダマシ多数 | STOCH／STOCHF |
| StochRSI | RSI14、窓14が一般的（TA-Lib既定は窓5）。考案は Chande・Kroll [TI-126]（⚠M） | RSIの位置を0〜100に再正規化。感度が高い | 0／100付近で頻繁に飽和。パラメータ依存が強い | STOCHRSI |
| MACD | 12-26-9（考案は Appel [TI-125]、⚠M） | 信号線クロス、ゼロライン越え、ヒストグラムの傾き、ダイバージェンス [TI-107][TI-108] | 価格単位のため銘柄間比較不可（→PPO）。レンジで往復 | MACD／PPO |
| CCI | 20が多い（⚠M）、TA-Lib既定14 [TI-109][TI-110] | ±100の外側。Lambert は-100〜+100に約7〜8割が収まるよう0.015を設定 [TI-109] | 閾値±100は固定的。トレンド中は+100超に長期滞在 | CCI |
| ウィリアムズ%R | 14 | -20超が買われすぎ、-80未満が売られすぎ（慣行、⚠M） | Fast%Kと同一情報（冗長） | WILLR |
| ROC／MOM | 10〜12（慣行、⚠M） | ゼロライン越え、モメンタムの減速 | 基準日の外れ値に弱い（n日前の一点を使う） | ROC／MOM |
| TRIX | TA-Lib既定30、一般に15程度 | ゼロクロス、信号線 | 3段EMAで遅れが大きい | TRIX |
| アルティメット | 7-14-28、重み4:2:1 | 30／70、強気ダイバージェンス＋高値更新（Williams、⚠M） | 3期間の恣意性 | ULTOSC |
| MFI | 14 | 80／20（慣行、⚠M）。出来高込みのRSI類似 | 出来高の質（日本の立会外等）に依存 | MFI |
| サイコロジカルライン | 12日、75%超（12日中9勝）で買われすぎ、25%未満（3勝）で売られすぎ [TI-111][TI-112] | 75%を上から下抜けで売り、25%を下から上抜けで買いとする見方もある [TI-113] | ダマシが多い [TI-113]。変わらず日の扱いが各社で異なる [TI-114] | なし |

## 4. 実装差（日本の証券会社を含む）
- RSI: 楽天証券のヘルプは直近N日の上げ幅合計と下げ幅合計から求める式（Cutler 型に近い）を示す [TI-101]。TradingView の日本語説明つきスクリプトは「日本の証券会社で多いカトラー式」に対応と説明する [TI-103]。Wilder 式の平滑係数は 1/n で、SMA型・EMA型を含め3方式がある [TI-102]。合成データ200経路（500本）で RSI(14) を比べると、平均絶対差は6.4pt、経路ごとの最大差の中央値は24.8pt、「70超」判定が食い違う日は9.1%だった。Wilder 式は種値の影響が減衰するまで約100〜200本かかる（RSI14を100本後に起算し直すと、+50本で差0.48、+100本で0.0125）。ツール間比較は方式と起算日を揃える。
- ストキャスティクス: 野村證券は %D を「m日の分子合計÷m日の分母合計」、SD をその移動平均と定義し、nは5や9、Yは3が多いとする [TI-104]。OANDA／松井証券は「スロー%D＝%Dの移動平均」と呼ぶ [TI-105][TI-106]。名称がずれるため、式で確認する。合成データ（n=9、200経路）で日本式 %D と欧米の Slow %K（Fast%Kの3日平均）の差は平均0.62pt（単一経路での最大は約7.5pt）。
- MACD: 信号線をEMAとするか単純平均とするか、最初のEMAの種値は、国内ツールで異なり得る（未確認）。

## 5. ダイバージェンス
定義（4型）[TI-115]: 強気（通常）＝価格が安値を切り下げ、オシレーターは安値を切り上げ。弱気（通常）＝価格が高値を切り上げ、オシレーターは高値を切り下げ。隠れ強気＝価格は安値切り上げ、オシレーターは安値切り下げ（上昇継続の示唆）。隠れ弱気＝価格は高値切り下げ、オシレーターは高値切り上げ（下落継続の示唆）。強い上昇相場では弱気ダイバージェンスが新高値を何度か更新する間も続き得る [TI-115]。

検証の難しさ（実装時の論点）:
- ピボットの定義: 高値は `H_i = max(H_{i-k..i+k})` で定義するとk本後にしか確定せず、k本の遅れが生じる（確定前に使うと先読み）。
- 比較対象のピボット（直近2点か、さらに前か）、両者の最大間隔、オシレーター側ピボットの位置合わせ許容幅に標準がなく、結果が定義に強く依存する。
- 隠れダイバージェンスの「継続」効果や有効性の統計的検証は、今回の調査では確認できなかった（未確認）。
- イベントが重なる（連続発生）ため、独立標本とみなした検定は有意性を過大評価する。

## 6. エビデンス（概要。詳細は [../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md)、検証手法は [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md)）
- Chong・Ng (2008)：ロンドン証券取引所 FT30 の60年データで、RSI と MACD のルールの多くがバイ・アンド・ホールドを上回った [TI-117]。
- Chong・Ng・Liew (2014)：他のOECD5か国で再検証し、MACD(12,26,0) と RSI(21,50) がミラノとトロントで、RSI(14,30/70) がダウ平均で有意な超過収益を示した [TI-118]。
- Rosillo ほか (2013)：スペイン市場で、成果は銘柄の種類と指標に依存すると報告 [TI-119]。
- Mohd Nor・Wickremasinghe (2017)：豪州 All Ordinaries（1996〜2014）で MACD は概して不振、RSI にはいくらか収益機会 [TI-120]。
- Kitkanasiri・Palahan (2025)：アジア10市場（2013〜2023）で MACD・RSI の4ルールは多くの市場でバイ・アンド・ホールドを有意に上回らず（シンガポールは例外）、パラメータ最適化後も稀にしか上回らない [TI-121]。
結果は市場・期間・パラメータ・データスヌーピング補正の有無で割れており、一般化はできない。日本市場に限った検証は本調査では未確認。

## 7. 限界・失敗パターン・パラメータ感度
- 張り付き: 強トレンドでは極値圏滞在が常態化する（第1節）。対策は、トレンド判定（ADX、移動平均の傾き）との併用、オシレーターを「トレンド方向の押し目」の目安に使う、閾値を静的でなく過去分布の分位点で定める、など。
- パラメータ感度: 期間を短くするほどシグナル数とダマシが増え、長くするほど遅れる。合成データ（日次σ1.5%、ドリフト0.03%/日、2000本×200経路）で RSI>70 の日数割合は n=5で19.5%、9で11.1%、14で6.0%、25で1.8%と期間で10倍変わる。スロー%K>80 は (5,3,3)で18.4%、(9,3,3)で21.6%、(14,3,3)で23.3%で、RSIの70／30とストキャスの80／20は同じ「買われすぎ」でも頻度が全く違う。複数パラメータを試すほど事後最適化の危険が増す（[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md)）。
- 冗長性: RSI・ストキャス・CCI・ROC・%R・%b は互いに強く相関する（合成データ1000本×150経路の平均相関: RSI-ストキャス0.86、ストキャス-CCI0.93、RSI-%b 0.89、RSI-ROC0.88）。同系統の「複数一致」は独立な確認にならない。
- 日本株: 値幅制限（ストップ高・安）の日はオシレーターが飽和しやすい。分割・権利落ちは調整後株価で計算する。制度は [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)。
- 損切り・目標値: オシレーターは価格水準を与えないため、損切りと目標は価格構造やATR（[08_volatility_and_trend_strength.md](08_volatility_and_trend_strength.md)）で別に定める。
- 実装ヒント: 売買判定は確定足の値のみ使い、翌足に適用する。しきい値は 70／30 の固定でなく、銘柄ごとの過去分布（例: 過去250日の分位点）で検証し、パラメータ空間の「平らな領域」を選ぶ。

## 関連文書
- [06_moving_averages.md](06_moving_averages.md)、[08_volatility_and_trend_strength.md](08_volatility_and_trend_strength.md)（ADX＝トレンド判定）、[09_volume_breadth_sentiment.md](09_volume_breadth_sentiment.md)（MFI・出来高系）、[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md)

## この文書の限界
- スニペット中心の確認で、証券会社・取引所・論文の本文は未読。実装差（国内各社の既定期間・MACD信号線の種類など）は未確認の部分が多い。
- ストキャスティクス・MACD・ウィリアムズ・Lane 等の創案者・年は筆者の知識（⚠M）。80／20、-20／-80、30／70 などの閾値は慣行であり、独立に確認していない。
- 張り付き頻度・Wilder と Cutler の差・相関は合成データ（ランダムウォーク）上の筆者計算で、実データの値ではない。
- TA-Lib の挙動は 0.8.3（PyPI、2026-10-28公開）での確認であり、他の版・他言語実装では異なり得る（確認日: 2026-11-09、要版数確認）。
- ダイバージェンスの統計的有効性、日本市場での検証は未確認。

## 出典
| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TI-101 | RSI（MarketSpeed オンラインヘルプ） | 楽天証券 | — | https://www.rakuten-sec.co.jp/MarketSpeed/onLineHelp/msman2_5_2_2.html | ✅S | 上げ幅合計と下げ幅合計の式、70／30 |
| TI-102 | RSI Calculation | macroption | — | https://macroption.com/rsi-calculation | ✅S | Wilder／SMA／EMA の3方式、Wilder は係数1/n |
| TI-103 | RSI（カトラー式対応スクリプト） | TradingView | — | https://in.tradingview.com/script/7PIW859i | ✅S | 国内証券で多いカトラー式に対応と説明（検索要約による） |
| TI-104 | スローストキャスティクス（用語集） | 野村證券 | — | https://www.nomura.co.jp/terms/japan/su/A02580.html | ✅S | %D（分子分母の合計）とSD |
| TI-105 | ストキャスティクスとは | OANDA証券 | — | https://www.oanda.jp/lab-education/technical_analysis/stochastic_oscillator/meaning/ | ✅S | スロー%D、MT4／MT5既定5-3-3 |
| TI-106 | ストキャスティクス（解説） | 松井証券 | — | https://www.matsui.co.jp/fx/study/article/analysis/stochastics/index.html | ✅S | %Kの計算例 |
| TI-107 | MACD (Moving Average Convergence/Divergence Oscillator) | StockCharts ChartSchool | — | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator.md | ✅S | 12-26-9、ヒストグラム、ゼロライン |
| TI-108 | What is the MACD Histogram? | StockCharts | 2009 | https://stockcharts.com/articles/mailbag/2009/09/what-is-the-macd-histogram.html | ✅S | ヒストグラムはMACDに先行して転換 |
| TI-109 | Commodity Channel Index | Barchart | — | https://www.barchart.com/education/technical-indicators/commodity_channel_index | ✅S | 式。Lambert 1980、定数0.015は検索要約 |
| TI-110 | CCI（関数ページ） | AmiBroker | — | https://amibroker.com/guide/t_cci.html | ✅S | 式の確認（検索要約） |
| TI-111 | サイコロジカルライン（用語集） | 野村證券 | — | https://www.nomura.co.jp/terms/japan/sa/psychological.html | ✅S | 12日、75%（9勝3敗）・25%（3勝9敗） |
| TI-112 | サイコロジカルライン（ヘルプ） | 楽天証券 | — | https://www.rakuten-sec.co.jp/MarketSpeedFX/onLineHelp/info/chart/psychological.html | ✅S | 上昇日数÷12×100 |
| TI-113 | サイコロジカルライン | マネックス証券 | — | https://info.monex.co.jp/technical-analysis/indicators/007.html | ✅S | 抜け返し基準、ダマシ多い |
| TI-114 | サイコロジカルライン（解説） | jioinc | — | https://jioinc.jp/investleaders/?p=18644 | ✅S | 変わらず日の扱いの違い（検索要約） |
| TI-115 | RSI divergences: What they are and how they work | Kraken Learn | — | https://www.kraken.com/learn/rsi-divergences-what-they-how-they-work | ✅S | 4型の定義、継続の注意 |
| TI-117 | Technical analysis and the London stock exchange: testing the MACD and RSI rules using the FT30 | Chong, Ng（Applied Economics Letters） | 2008 | https://consensus.app/papers/details/7d7ea470383e5ae6b13a25ae8ca7fee3/ | ✅S | 要旨のみ確認 |
| TI-118 | Revisiting the Performance of MACD and RSI Oscillators | Chong, Ng, Liew（J. Risk Financial Manag.） | 2014 | https://consensus.app/papers/details/7f7d94b2b07d524bb78a67a0d47c97ab/ | ✅S | 要旨のみ確認 |
| TI-119 | Technical analysis and the Spanish stock exchange: testing the RSI, MACD, momentum and stochastic rules | Rosillo, de la Fuente, Brugos（Applied Economics） | 2013 | https://consensus.app/papers/details/5b1c80c0f8395c2da1f1f895f1562ef5/ | ✅S | 要旨のみ確認 |
| TI-120 | The profitability of MACD and RSI trading rules in the Australian stock market | Mohd Nor, Wickremasinghe | 2017 | https://consensus.app/papers/details/dcc8c44de6b25007a8438a649858fba5/ | ✅S | 要旨のみ確認 |
| TI-121 | Market Efficiency and Technical Trading: An Empirical Study of MACD and RSI Indicators in Major Asian Stock Indices | Kitkanasiri, Palahan（ABAC Journal） | 2025 | https://consensus.app/papers/details/49021c3cab525fae942fccf24609109c/ | ✅S | 要旨のみ確認 |
| TI-122 | TA-Lib（PyPI JSON） | PyPI | 2026 | https://pypi.org/pypi/TA-Lib/json | ✅S | 0.8.3（2026-10-28公開）。数値照合は同版 |
| TI-123 | New Concepts in Technical Trading Systems | J. Welles Wilder Jr. | 1978 | — | ⚠M | RSI・ATR・ADX・パラボリックSARの原典 |
| TI-124 | ストキャスティクスの考案 | George C. Lane | — | — | ⚠M | 題名・年は未確認 |
| TI-125 | MACDの考案 | Gerald Appel | — | — | ⚠M | 題名・年は未確認。ヒストグラムの追加者（Thomas Aspray）も記憶による |
| TI-126 | The New Technical Trader | Tushar Chande, Stanley Kroll（Wiley） | 1994 | — | ⚠M | StochRSI・CMOの出典（記憶による） |
| TI-127 | The commodity channel index（関数ページ） | Steema | — | https://steema.com/docs/financialFunctionsRef/cciFunction.htm | ✅S | 分母に標準偏差を使う記述（検索要約） |
