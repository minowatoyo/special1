# ローソク足パターン辞典（欧米式）：規格化・TA-Lib対応・文脈ルール・学術検証
> 要約: ローソク足の構造と規格化（実体比率・影比率・TA-Libの既定閾値）、単一足・2本足・3本足以上の主要パターンとTA-Lib関数名の対応、文脈ルール（先行トレンド・位置・確認足・出来高）を整理した。
> 学術検証は米国・日本・台湾・タイ・中国の研究を要約した。日本株（1975〜2004年）では利益が確認されず、結果は市場・保有戦略・費用・データスヌーピング補正に強く依存する。
> 日本語名と酒田五法の詳細は../02_japan/01_sakata_gohou.mdに委ね、ここは最小限の対応にとどめる。
> 最終更新: 2026-11-09

表記: `[TS-nnn]` は出典ID。⚠Mは記憶に基づく。「通説」は教科書的説明で未検証。

## 1. 構造と規格化
```
body = |C-O|   range = H-L   upper = H-max(O,C)   lower = min(O,C)-L
body_ratio = body/range   upper_ratio = upper/range   lower_ratio = lower/range
陽線: C>O   陰線: C<O   同事: body <= 閾値
```
- 絶対値でなく相対値で判定する。実体の長短は「直近N本の平均実体」との比、同事は「直近N本の平均レンジ」との比とする（TA-Libの方式）。
- TA-Libの既定値[TS-070]（確認日: 2026-11-09、版により変わり得るため要確認）:

| 設定 | 基準 | 平均期間 | 倍率 | 使われ方 |
|---|---|---|---|---|
| BodyLong／BodyVeryLong／BodyShort | 実体 | 10 | 1.0／3.0／1.0 | 実体の長短（包み線・星など） |
| BodyDoji | 高値−安値 | 10 | 0.1 | 同事 |
| ShadowLong／ShadowVeryLong | 実体 | 0 | 1.0／2.0 | ヒゲの長さ（ハンマー等） |
| ShadowShort | ヒゲ | 10 | 1.0 | ヒゲが短い |
| ShadowVeryShort | 高値−安値 | 10 | 0.1 | ほぼヒゲなし（坊主） |
| Near／Far／Equal | 高値−安値 | 5 | 0.2／0.6／0.05 | 近い／遠い／等しい |
- 閾値＝倍率×（過去「平均期間」本の基準範囲の平均）。平均期間0は当該足そのものを使う[TS-070]。例：同事＝実体が直前10本の平均レンジの10%未満。
- 返り値は100（強気）／−100（弱気）／0。R版は1／−1／0が既定で100切替も可能[TS-071][TS-072]。Hikkake系は±200もある（⚠M）。7関数に貫入度引数penetration（R版はeps）がある[TS-071]。パターン関数は61個[TS-071]。Pythonラッパーの最新は0.8.3[TS-073]。
- TA-Libは主にOHLCの形だけで判定し、先行トレンドは確認しない（⚠M）。文脈は§5で自前に加える。
```
import talib
sig = talib.CDLENGULFING(o, h, l, c)             # 100/-100/0
sig = talib.CDLMORNINGSTAR(o, h, l, c, penetration=0.3)   # 貫入度は版で既定値が異なり得る
```

- 自前実装の定義例（設計例。TA-Libの判定とは一致しないことがある。avg_range・avg_bodyは直前10本の平均）:
```
doji       : body <= 0.1*avg_range
hammer     : lower >= 2*body and upper <= 0.1*range and min(O,C) >= L + 0.67*range   # 実体が上位1/3
             + 直前が下降（§5）。首吊り線は同形で直前が上昇
shooting   : upper >= 2*body and lower <= 0.1*range and max(O,C) <= L + 0.33*range    # 直前が上昇
bull_engulf: C1<O1 and C2>O2 and O2<=C1 and C2>=O1 and body2>body1                    # 実体の包み
morning    : 1本目 陰線 body1>=avg_body／2本目 body2<=0.5*avg_body かつ max(O2,C2)<min(O1,C1)／
             3本目 陽線 C3 > (O1+C1)/2        # 貫入度0.5
```

## 2. 単一足
| パターン（和名の例） | 規格化の例 | 読み | TA-Lib |
|---|---|---|---|
| 同事線（Doji） | body<0.1×平均レンジ | 迷い。それ自体は転換の確証でない | CDLDOJI／CDLDOJISTAR |
| 足長同事・トンボ・塔婆（Long-Legged／Dragonfly／Gravestone） | 両ヒゲ長／下ヒゲのみ長／上ヒゲのみ長 | トンボは安値圏で強気、塔婆は高値圏で弱気の示唆。四本値同値の同事は該当関数なし | CDLLONGLEGGEDDOJI／CDLRICKSHAWMAN／CDLDRAGONFLYDOJI／CDLGRAVESTONEDOJI |
| ハンマー（Hammer）／首吊り線（Hanging Man） | 実体が上部、下ヒゲ≧実体の2倍（教育資料の通説）、上ヒゲ僅少 | 同形。下降後ならハンマー（強気）、上昇後なら首吊り線（弱気）。翌足の確認が前提 | CDLHAMMER／CDLHANGINGMAN／CDLTAKURI |
| 逆ハンマー（Inverted Hammer）／流れ星（Shooting Star） | 実体が下部、上ヒゲ≧実体の2倍 | 同形。上昇後の流れ星は弱気、下降後の逆ハンマーは強気（確認要） | CDLINVERTEDHAMMER／CDLSHOOTINGSTAR |
| 丸坊主（Marubozu）／大陽線・大陰線 | ヒゲが極小／実体が平均より大 | 勢いの表れ。寄り付き坊主はBelt Hold | CDLMARUBOZU／CDLCLOSINGMARUBOZU／CDLLONGLINE／CDLSHORTLINE／CDLBELTHOLD |
| コマ（Spinning Top）／High-Wave | 実体小・上下ヒゲが実体より長い | 方向感の喪失 | CDLSPINNINGTOP／CDLHIGHWAVE |

## 3. 2本足
| パターン | 定義（要点） | 文脈・読み | TA-Lib |
|---|---|---|---|
| 包み線（Engulfing） | 2本目の実体が1本目の実体を完全に包む（色が逆）[TS-087] | 下降後の陽の包みは強気、上昇後の陰の包みは弱気。ヒゲまで包む必要はない | CDLENGULFING |
| はらみ線（Harami）／十字はらみ | 2本目の実体が1本目の実体の内側。2本目が同事なら十字はらみ | 包み線より転換シグナルは弱い。高安がすべて内側のインサイドバーとは別概念[TS-088] | CDLHARAMI／CDLHARAMICROSS |
| 切り込み線（Piercing）／かぶせ線（Dark Cloud Cover） | 切り込み線：長い陰線の後、前日安値を割って寄り、前日実体の半ば以上まで陽線で戻す。かぶせ線はその逆（Nison系の標準的説明[TS-074]） | 貫入度（半値）が閾値。深いほど強いとされる（通説） | CDLPIERCING／CDLDARKCLOUDCOVER（penetration） |
| 毛抜き（Tweezer） | 連続する足の高値（安値）が等しい（Equal閾値で自作） | 天井圏／底圏での反転示唆（通説） | 該当なし（CDLMATCHINGLOWが近縁） |
| 入り首・あて首・差し込み | 下降中、陽線が前の陰線の終値付近までしか戻らない | 下降の継続（弱気継続） | CDLINNECK／CDLONNECK／CDLTHRUSTING |
| Kicking／Counterattack／Separating Lines／Homing Pigeon／Matching Low／Doji Star | 窓を伴う逆色の坊主2本／同値引け／継続型の分離線／ほか | 稀。Kickingは強い転換、Separating Linesは継続 | CDLKICKING／CDLKICKINGBYLENGTH／CDLCOUNTERATTACK／CDLSEPARATINGLINES／CDLHOMINGPIGEON／CDLMATCHINGLOW |

## 4. 3本足以上
| パターン | 定義（要点） | 文脈・読み | TA-Lib |
|---|---|---|---|
| 明けの明星（Morning Star）／宵の明星（Evening Star） | 長い陰線→小さな実体（窓下）→1本目の実体の半ばを超える陽線。宵の明星は逆 | 底（天井）での転換。星が同事ならDoji Star版。貫入度で調整 | CDLMORNINGSTAR／CDLEVENINGSTAR／CDLMORNINGDOJISTAR／CDLEVENINGDOJISTAR |
| アバンダンド・ベビー／捨て子線（Abandoned Baby） | 星が同事で、前後の足と影まで窓で分離 | 稀で強い転換形。Bulkowskiでは強気型が総合8位・強気反転率70%[TS-076] | CDLABANDONEDBABY |
| 赤三兵／三羽烏（Three White Soldiers／Black Crows） | 長い陽（陰）線3本。各始値は前の実体内、終値は高値（安値）圏 | 転換または勢いの確認。変種：Identical Three Crows、Advance Block（勢いの衰え）、Stalled | CDL3WHITESOLDIERS／CDL3BLACKCROWS／CDLIDENTICAL3CROWS／CDLADVANCEBLOCK／CDLSTALLEDPATTERN |
| スリー・インサイド／アウトサイド | はらみ（包み）＋3本目の確認足 | 確認足を含むため単独のはらみ・包みより遅いが信頼度は高いとされる（通説） | CDL3INSIDE／CDL3OUTSIDE |
| スリーライン・ストライク／トライスター | 同色3本の後の逆行大足／同事3本 | Bulkowskiでは弱気スリーライン・ストライクが総合1位（弱気継続率61%）[TS-076]だが、別ページには強気反転84%（総合2位）との記載もあり[TS-091]、尺度が異なり比較できない | CDL3LINESTRIKE／CDLTRISTAR |
| 上昇三法・下降三法（Rising／Falling Three Methods）、Mat Hold | 長い陽線→1本目の高安内に収まる小さな逆行3本→長い陽線で高値更新（下降は逆）。Mat Holdは窓を伴う変種 | 継続型（トレンド途中の一服） | CDLRISEFALL3METHODS／CDLMATHOLD（penetration） |
| 並び赤・タスキ・ギャップ・スリー・メソッド | 窓を挟む継続パターン | Upside Gap Three Methodsは強気継続のはずが、弱気反転として働く割合が59%（総合27位）[TS-077] | CDLGAPSIDESIDEWHITE／CDLTASUKIGAP／CDLXSIDEGAP3METHODS |
| その他 | Breakaway、Ladder Bottom、Unique 3 River、3 Stars in the South、Concealing Baby Swallow、Stick Sandwich、Two Crows、Upside Gap Two Crows、Hikkake | 稀少で統計が乏しい。理論上の方向と実測が一致しない例がある[TS-077] | CDLBREAKAWAY／CDLLADDERBOTTOM／CDLUNIQUE3RIVER／CDL3STARSINSOUTH／CDLCONCEALBABYSWALL／CDLSTICKSANDWICH／CDL2CROWS／CDLUPSIDEGAP2CROWS／CDLHIKKAKE／CDLHIKKAKEMOD |

## 5. 文脈ルール
| 要素 | 規則の例（閾値は設計例） | 根拠・注意 |
|---|---|---|
| 先行トレンド | 反転形は前提となるトレンドを機械定義する。例：終値がSMA(n)の上かつSMAが上向き、直近スイング(→01 §2)がHH＋HL、N日リターンの符号 | 3種類のトレンド定義×4種類の保有戦略で比較すると、結論は定義より保有戦略に左右された[TS-082] |
| 位置 | 支持抵抗帯、ボリンジャーバンド端、52週高安値付近のみ有効とする | 通説。位置条件の追加効果は未確認 |
| 確認足 | 翌足の終値がパターンの高値（安値）を超えたら成立。待つ分だけ有利な価格を失う | 通説。入口は確認足の終値または次足始値（足確定後に判定する） |
| 出来高 | パターン足の出来高が平均のk倍以上（k=1.5は設計例） | 通説。効果の検証は未確認 |
| オシレーター併用 | Stochastics／RSI／MFIでの絞込み | SET50ではおおむね改善しなかった[TS-084] |
| 出口 | 期日決済（MYR型）か、保有期間の平均終値での手仕舞い（CL型）か | 同一パターンでもCL型は有利、MYR型は不利という結果がある[TS-082]。損切りの併用で多くのパターンが改善したとの報告もある（台湾）[TS-090] |
| 損切り・目標 | 損切りはパターンの極値の外側（ハンマーなら安値の下）。目標はATR倍数か次の支持抵抗 | 設計例 |

## 6. 学術検証の要約
詳細は../03_evidence/01_academic_literature.md。

| 研究 | 対象 | 結果 |
|---|---|---|
| Caginalp & Laurent 1998[TS-058] | S&P500構成銘柄1992〜96、3本足パターン | 2日保有で約1%の利益と主張（アウトオブサンプル） |
| Marshall, Young & Rose 2006[TS-079] | DJIA構成銘柄、OHLCを生成するブートストラップ | 戦略に価値なし |
| Marshall, Young & Cahan 2008[TS-080] | 日本株1975〜2004 | 全期間・3分割期間・強気弱気のいずれでも利益なし |
| Lu他 2012／Lu 2013[TS-086][TS-083] | 台湾 | 2本足の強気3種（2012）、単一足4種は費用後も（2013）有利と報告 |
| Lu, Chen & Hsu 2015[TS-082] | DJIA | 3本足反転8種はCL型で費用0.5%後も有利、MYR型では不利 |
| Duvinage他 2013[TS-081] | DJIA 5分足 | スヌーピング補正と費用後に買い持ちに勝つルールなし |
| Tharavanij他 2017[TS-084] | タイSET50 | 多くのパターンの平均収益はゼロと有意差なし |
| Deng他 2022[TS-085] | 中国SSE50 2000〜2018 | 強気の一部（Long White等）は有意に正、弱気は予測力なし |
- Bulkowskiは反転率／継続率と10日後の値動きの順位から総合順位を付ける[TS-075]。上位に入るパターンでも理論上の方向と実測が一致しない例がある[TS-076][TS-077]。
- 総括: 日本株で否定的（[TS-080]）、台湾・中国で一部肯定的、米国は否定的か保有戦略次第。効果は小さく、費用・データスヌーピング・保有戦略の置き方で結論が変わる。

## 7. 日本株での留意点と実装
- ローソク足の発祥地である日本株でも利益は確認されていない[TS-080]。ローソク足を単独の売買根拠にせず、位置・確認足・リスク管理とセットで検証する。
- 窓を含むパターン（Abandoned Baby、Tasuki、Gap Three Methods、Breakaway）は、値幅制限・権利落ち・寄付きの板寄せで機械的に窓が生じるため、除外または調整する（→../02_japan/04_tse_market_rules_and_chart_effects.md）。
- 低位株は呼値が粗く、Equal／Near／同事の閾値が1ティック未満になり得る。閾値の下限を1ティック以上とする。
- 日足の定義（前場・後場の通常取引のみか、PTS・先物夜間を含むか）を固定する。判定は足確定後に行い、シグナルは次足以降に反映する。
- 実装の落とし穴: (1)OHLCでは足内の高安の順序が不明で、損切り・利確の同時到達は保守的に処理する。(2)TA-Libは平均期間分の先頭の足が判定不能（0）になる（⚠M）。ウォームアップ期間を捨てる。(3)同一足に複数パターンが重なるため、集計では重複を整理する。(4)Equal／Nearは直前5本の平均レンジに依存し、データ開始位置で結果が変わる。(5)指標・パターン用のOHLCは分割・併合調整後を使う（→01 §8）。
- 日本語名の詳細と酒田五法は../02_japan/01_sakata_gohou.md。画像化＋CNNによる分類の試みもあるが、評価は過学習と期間依存に注意する[TS-089]。

## 関連文書
- ../02_japan/01_sakata_gohou.md／../03_evidence/01_academic_literature.md
- 01_price_structure.md（窓・スイング）／02_chart_patterns.md／07_oscillators_momentum.md

## この文書の限界
- TA-Libの公式関数ページ（各パターンの判定ロジック）は開けず、設定ページと周辺ライブラリ文書の検索要約で確認した。判定ロジックの詳細と返り値（±200等）は記憶による（⚠M）。
- 各パターンの定義は教育資料の通説に基づく。日本語の一次資料（証券会社の用語集）は包み足・はらみ足のみ確認した。
- 表中の和名（トンボ、塔婆、捨て子線、並び赤、タスキ等）は記憶に基づく（⚠M）。確認はJP1文書側で行う。
- Bulkowskiの数値は検索で確認できた範囲のみで、版・更新日で変わる。尺度の異なる数値は比較できない。
- 学術研究は要旨のみ確認。データスヌーピング補正の有無・取引費用の想定は論文ごとに異なる。

## 出典

> 検証タグ: ✅S=検索結果・論文レコード等で書誌と要点を確認（本文は未読）／⚠M=記憶のみ／❓=要確認。URLは検索結果に現れたものだけを記載し、無いものは「—」とした。

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TS-058 | The predictive power of price patterns | Caginalp, Laurent／Applied Mathematical Finance | 1998 | — | ✅S | DOI 10.1080/135048698334637 |
| TS-070 | Candlestick Settings | TA-Lib（公式サイト） | — | https://ta-lib.org/api/candle-settings/ | ✅S | 既定値の表。確認日 2026-11-09 |
| TS-071 | Candlestick Pattern Recognition（R版vignette） | talib (R) | — | https://cran.r-project.org/web/packages/talib/vignettes/candlestick.html | ✅S | 61パターン、eps引数、返り値の切替 |
| TS-072 | pattern recognition（TA-Lib Pythonラッパー文書の要約） | tessl registry | — | https://tessl.io/registry/tessl/pypi-ta-lib/files/docs/pattern-recognition.md | ✅S | penetration引数、返り値100/-100/0 |
| TS-073 | TA-Lib（Python wrapper）パッケージ情報 | PyPI | 2026-10-28（0.8.3公開） | https://pypi.org/pypi/TA-Lib/json | ✅S | 最新版0.8.3。確認日 2026-11-09 |
| TS-074 | Japanese Candlestick Charting Techniques | Nison | 1991 | — | ✅S | 書名・年は検索要約。本文未読 |
| TS-075 | Encyclopedia of Candlestick Charts | Bulkowski | 2008（年は記憶） | https://perlego.com/book/1007524/encyclopedia-of-candlestick-charts-pdf | ✅S | 書誌のみ確認。年は記憶 |
| TS-076 | Candle performers（総合順位） | Bulkowski／thepatternsite.com | — | https://www.thepatternsite.com/CandlePerformers.html | ✅S | 総合順位ページ。更新日で変わる |
| TS-077 | Upside Gap Three Methods | Bulkowski／thepatternsite.com | — | https://thepatternsite.com/UpGap3Methods.html | ✅S | 継続型が反転として働く例 |
| TS-079 | Candlestick technical trading strategies: can they create value for investors? | Marshall, Young, Rose／J. Banking & Finance | 2006 | — | ✅S | DOI 10.1016/j.jbankfin.2005.08.001 |
| TS-080 | Are candlestick technical trading strategies profitable in the Japanese equity market? | Marshall, Young, Cahan／Review of Quantitative Finance and Accounting | 2008 | — | ✅S | DOI 10.1007/s11156-007-0068-1 |
| TS-081 | The intra-day performance of market timing strategies and trading systems based on Japanese candlesticks | Duvinage, Mazza, Petitjean／Quantitative Finance | 2013 | — | ✅S | DOI 10.1080/14697688.2013.768774 |
| TS-082 | Trend definition or holding strategy: What determines the profitability of candlestick charting? | Lu, Chen, Hsu／J. Banking & Finance | 2015 | — | ✅S | DOI 10.1016/j.jbankfin.2015.09.009 |
| TS-083 | The profitability of candlestick charting in the Taiwan stock market | Lu／Pacific-Basin Finance Journal | 2013 | — | ✅S | DOI 10.1016/j.pacfin.2013.10.006 |
| TS-084 | Profitability of Candlestick Charting Patterns in the Stock Exchange of Thailand | Tharavanij ほか／SAGE Open | 2017 | — | ✅S | DOI 10.1177/2158244017736799 |
| TS-085 | Can Japanese Candlestick Patterns be Profitable on the Component Stocks of the SSE50 Index? | Deng ほか／SAGE Open | 2022 | — | ✅S | DOI 10.1177/21582440221117803 |
| TS-086 | Profitable candlestick trading strategies—The evidence from a new perspective | Lu, Shiu, Liu／Review of Financial Economics | 2012 | — | ✅S | DOI 10.1016/j.rfe.2012.02.001 |
| TS-087 | 包み足（解説） | 松井証券 | — | https://www.matsui.co.jp/fx/study/article/analysis/tsutsumi-ashi/ | ✅S | 包み足の説明 |
| TS-088 | はらみ足（インサイド）と包み足（アウトサイド） | OANDA証券 | — | https://www.oanda.jp/lab-education/technical_analysis/price_action/inside_outside/ | ✅S | はらみ足と包み足の違い |
| TS-089 | Encoding candlesticks as images for pattern classification using convolutional neural networks | Chen, Tsai／Financial Innovation | 2020 | — | ✅S | DOI 10.1186/s40854-020-00187-0 |
| TS-090 | Goo ほか: The Application of Japanese Candlestick Trading Strategies in Taiwan | Goo, Chen, Chang／Investment Management & Financial Innovations | 2017 | — | ✅S | 年は記録による（DOIなし） |
| TS-091 | Three Line Strike Bearish（統計） | Bulkowski／thepatternsite.com | — | https://thepatternsite.com/ThreeLineStrikeBear.html | ✅S | 強気反転84%・総合2位の記載（尺度が異なる） |
