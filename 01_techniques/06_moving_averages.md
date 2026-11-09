# 移動平均線（SMA／EMA／WMA ほか）とグランビルの法則
> 要約: 移動平均線13種（SMA／EMA／WMA／HMA／DEMA／TEMA／KAMA／VWMA／VWAP ほか）の計算式・初期値（種値）・遅れ・ノイズ利得を整理し、TA-Lib 0.8.3 と数値照合した。
> 日本の期間慣行（日足5/25/75/200、週足13/26）と欧米慣行、ゴールデン／デッドクロス、グランビルの法則8つ、乖離率、傾きの使い方を扱う。
> 乱数相場でも短期のクロスは年10回超発生し、レンジ相場のダマシは構造的に避けられない。
> 学術検証は、歴史的な有意性の報告と、データスヌーピング補正・取引コスト・期間分割後に弱まる（消える）との報告が併存し、有効性は断定できない。
> 最終更新: 2026-11-09

## 1. 種類別の定義とTA-Lib照合
P＝価格（通常は終値）、n＝期間、a＝平滑係数。数値は TA-Lib 0.8.3 [TI-021] の出力と合成データ（400本、乱数種固定）で照合し、全て一致（最大誤差 1e-11 以下）した。「遅れ」はインパルス応答の重心（直線トレンドに対する定常的な遅れ、単位＝本）、「ノイズ利得」はホワイトノイズ入力に対する出力標準偏差比で、いずれも n=25 の TA-Lib 出力から計測した。

| 名称 | 計算式 | TA-Lib | 最初の有効値の添字 | 遅れ | ノイズ利得 |
|---|---|---|---|---|---|
| SMA | (P_t+…+P_{t-n+1})/n | SMA | n-1 | 12.0 | 0.200 |
| EMA | a=2/(n+1); E_t=a*P_t+(1-a)*E_{t-1}; 種値＝最初のn個の単純平均 | EMA | n-1 | 12.0 | 0.200 |
| WMA | Σ i*P_{t-n+i} / (n(n+1)/2)（i=1..n、最新に重みn） | WMA | n-1 | 8.0 | 0.229 |
| TRIMA | 三角形の重み（SMAのSMA） | TRIMA | n-1 | 12.0 | 0.227 |
| DEMA | 2*E1-E2（E2=EMA(E1)） | DEMA | 2(n-1) | 0.0 | 0.311 |
| TEMA | 3*E1-3*E2+E3 | TEMA | 3(n-1) | 0.0 | 0.393 |
| T3 | GD(x)=E1*(1+v)-E2*v を3回合成（v=0.7） | T3 | 6(n-1) | 10.8 | 0.201 |
| HMA | WMA(2*WMA(int(n/2))-WMA(n), int(sqrt(n))) | HMA | n-1+int(sqrt(n))-1 | 0.67 | 0.420 |
| ZLEMA | EMA(2*P_t-P_{t-L}, n)、L=int((n-1)/2) | ZLEMA | L+n-1 | 0.0 | 0.373 |
| Wilder RMA | a=1/n、種値＝最初のn個の単純平均 | RMA | n-1 | 24.0 | 0.143 |
| KAMA | ER=abs(P_t-P_{t-n})/Σabs(P_i-P_{i-1}); SC=(ER*(2/3-2/31)+2/31)^2; K_t=K_{t-1}+SC*(P_t-K_{t-1}) | KAMA | n | 適応 | 適応 |
| VWMA | Σ(P*V)/ΣV（直近n本） | VWMA | n-1 | — | — |
| VWAP | Σ(TP*V)/ΣV、TP=(H+L+C)/3、起点からの累積 | VWAP | 0 | — | — |

要点:
- a=2/(n+1) の EMA は SMA(n) と遅れ・ノイズ利得が同じになる。Wilder 平滑 RMA(n) は EMA(2n-1) 相当（遅れ n-1）。
- DEMA／TEMA／HMA／ZLEMA は遅れをほぼ零にするが、ノイズ利得が約1.6〜2.1倍（SMAの0.200に対し0.31〜0.42）になり、重みに負値（HMAで最小 -0.033）を含むため転換点で行き過ぎる（オーバーシュート）。DEMA・TEMAの出典は Mulloy の TASC 論文（1994年、⚠M）[TI-031]。HMA は Alan Hull の考案で、n/2 と sqrt(n) を整数に切り捨てる [TI-017][TI-018]。
- TA-Lib の KAMA は timeperiod が効率比（ER）の窓で、速い側2・遅い側30は固定（既定値は30）。Kaufman 推奨の KAMA(10,2,30) は `KAMA(close,10)` に相当 [TI-015][TI-016]。種値は TA-Lib が直前価格、ChartSchool が単純平均とされ、序盤の値は異なる。
- TA-Lib の VWAP は第0本からの累積で、セッション切替を持たない。日中VWAPは日ごとに呼び直し、AVWAP（起点固定VWAP）は起点以降を渡す。式は累積(TP×V)/累積(V)で、TP を終値や OHLC 平均にする流儀もある [TI-019][TI-020]。

## 2. 初期値とウォームアップ
EMA の種値は、(a) 最初のn個の単純平均（TA-Lib）、(b) 最初の価格（pandas `ewm(adjust=False)`）、(c) 有限和の重み付き平均（`adjust=True`）の3流儀があり、差は (1-a)^k で減衰する。種値の影響が1%未満／0.1%未満になる本数は下表のとおり（計算値）。

| 平滑 | a | 1%未満 | 0.1%未満 |
|---|---|---|---|
| EMA(12) | 0.154 | 28本 | 42本 |
| EMA(26) | 0.074 | 60本 | 90本 |
| EMA(50) | 0.039 | 116本 | 173本 |
| EMA(200) | 0.0100 | 461本 | 691本 |
| Wilder(14) | 0.0714 | 63本 | 94本 |

実測例（価格約100、EMA(20)）: TA-Lib と pandas `adjust=False` の差は最初の有効値で0.40、20本後0.054、100本後1.8e-5。ツール間で数値を比較するときは、開始日を揃え、少なくとも 3n〜5n 本の履歴を捨てて比べる。TA-Lib 互換のEMA（照合済み）は次のとおり。

```
def ema_talib(x, n):                  # x: 1次元float配列（NumPy）
    a = 2.0/(n+1); out = np.full(len(x), np.nan)
    out[n-1] = x[:n].mean()           # 種値＝最初のn個の単純平均
    for i in range(n, len(x)):
        out[i] = a*x[i] + (1-a)*out[i-1]
    return out
```

VWAP／AVWAP の補足: 日足のVWAPは各日の典型価格に日次出来高を掛けた近似であり、ティック単位の真のVWAP（約定価格×約定数量）とは一致しない。起点（スイング高安、決算日、上場日、ギャップ）の選び方が結果を左右し、起点の選択自体が恣意的になりやすい。AVWAP の式は [TI-019][TI-020] で確認した。Brian Shannon による普及という説明が検索要約にあったが、出典ページを特定できておらず未確認である。

## 3. 期間の慣行
| 区分 | 慣行 | 根拠 |
|---|---|---|
| 日本・日足 | 5／25／75（＋200、10、100） | 大和証券・野村證券の用語解説 [TI-006][TI-007] |
| 日本・週足 | 13週／26週（約65／130営業日） | 同上 |
| 日本・月足 | 12／24（＋60、120）か月 | 同上 |
| 国内ツール既定値の例 | 5／25／75／100／200日（MarketSpeed FX） | 楽天証券ヘルプ [TI-008]（要確認） |
| 期間の意味づけ | 25日≒約1か月、75日≒約3か月半、200日≒約10か月 | [TI-009] |
| 欧米 | 10／20／50／100／200日（週足の30週線は [05_practitioner_frameworks.md](05_practitioner_frameworks.md) 参照） | ⚠M Murphy [TI-032]。本調査の検索では未検証 |

日足は DMA と呼ばれる（野村）[TI-007]。25日が選ばれる由来には土曜立会があった時代の月間営業日数とする説明が流布するが、出典は未確認。期間は慣行であり法則ではない。5日＝1週、50日≒10週、200日≒40週と換算でき、日本の75日は欧米の50日と200日の中間にあたる。

## 4. クロスとダマシ
- ゴールデンクロス（GC）は短期線が長期線を下から上へ、デッドクロス（DC）はその逆に抜ける [TI-006]。価格と線の交差、3本線の整列（パーフェクトオーダー: 短期＞中期＞長期の順に並び、かつ全て上向き、またはその逆。一般的な定義で、詳細は [../02_japan/03_other_japanese_methods.md](../02_japan/03_other_japanese_methods.md)）も同系統。
- 確認条件の例: 終値ベース、2日連続、一定幅（バンド）の外側、長期線の傾きが同方向、出来高増加。いずれも閾値が増えるほど自由度が増え、事後最適化に陥りやすい（[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md) の最適化の危険を参照）。
- 無構造相場でのクロス頻度（日次リターン正規・平均0・日次σ=1.5%、200経路×5000本、合成データでの筆者計算）:

| 組み合わせ | 250本あたり交差数 | 交差間の平均本数 |
|---|---|---|
| SMA(5)×SMA(25) | 13.7 | 18 |
| SMA(10)×SMA(20) | 13.8 | 18 |
| SMA(25)×SMA(75) | 3.9 | 64 |
| SMA(50)×SMA(200) | 1.6 | 158 |

短期の組み合わせは構造のない値動きでも年10回超のシグナルを出すため、レンジ相場では往復のコストと小さな損失が積み重なる。長期線の組み合わせはダマシが少ない代わりに反応が遅い（第1節の遅れ参照）。

## 5. グランビルの法則（8つ）
Joseph Granville が提唱（Granville's New Key to Stock Market Profits、1963、⚠M）[TI-030]。移動平均線の向きと株価の位置関係で売買を8分類する。必ずしも番号順には現れない [TI-001]。

| 番号 | 移動平均線の向き | 株価の動き | 売買 | 性格 |
|---|---|---|---|---|
| 買い① | 下落後に横ばい〜上向きへ転換 | 線を下から上へ突き抜ける | 買い | 転換の初動 |
| 買い② | 上向きを維持 | 線を一時的に下回るが線は上向きのまま | 買い | 押しの下抜け（ダマシ型） |
| 買い③ | 上向き | 線へ向かって下落するが割り込まず反発 | 買い | 押し目買い |
| 買い④ | 下向き | 線から急落し大きく下方乖離 | 買い（逆張り） | 自律反発狙い |
| 売り⑤ | 上昇後に横ばい〜下向きへ転換 | 線を上から下へ突き抜ける | 売り | 転換の初動 |
| 売り⑥ | 下向きを維持 | 線を一時的に上回るが線は下向きのまま | 売り | 戻りの上抜け（ダマシ型） |
| 売り⑦ | 下向き | 線へ向かって上昇するが上抜けず反落 | 売り | 戻り売り |
| 売り⑧ | 上向き | 線から急騰し大きく上方乖離 | 売り（逆張り） | 反落狙い |

- 確認できた記述: ①②の内容 [TI-001]、①⑤が単純で初心者向き・②③⑥⑦は押し目／戻りを待つ型 [TI-004]、④⑧は乖離した後の平均回帰を狙う逆張りで、乖離したままトレンドが続く損失リスクがある [TI-003][TI-005]、一般的な設定は200日線・日足 [TI-003]。③〜⑧の細部と、④の線の向き（下向き）は検索スニペットで一部のみ確認し、残りは筆者の整理（⚠M）。各条項の統計的検証を行った文献は今回の調査では未確認。
- 失敗パターン: ①⑤は横ばいの線上で往復ビンタ、②⑥は本物の転換との区別が事後でしか付かない、③⑦は「割り込まない」の判定幅が恣意的、④⑧は強いトレンドで乖離が拡大し続ける（最も損失が大きい）。
- 実装ヒント: 向きは正規化した傾き s=(MA_t-MA_{t-k})/(k*ATR(n)) の符号と閾値で3値化し、④⑧は第6節の乖離z値（例: 絶対値2超、閾値は仮置き）で判定する。「押し」は終値が線の ±x*ATR 以内に入った日で定義し、イベントはすべて確定した足のみで評価する。

## 6. 移動平均乖離率
`乖離率(%) = (P_t - MA_t) / MA_t * 100` [TI-012]。上方乖離は買われすぎ、下方乖離は売られすぎの目安とされ、野村證券は日経平均で5%程度、個別株で10%程度が目安としている [TI-010]。SMBC日興は±5% [TI-011]、TradingView の乖離スクリプトは -10%以下を売られすぎの可能性とする [TI-013]。基準が出典で大きく異なる。

乖離の大きさは期間とボラティリティに依存する。ランダムウォークでは `std(P-SMA_n) = σ_d * sqrt((n-1)(2n-1)/(6n))`（σ_d＝価格単位の日次変動）となり、n=25 で 2.80σ_d、n=75 で 4.95σ_d、n=200 で 8.13σ_d（シミュレーション値 2.73／4.98／8.38）。日次変動率1.2%なら25日乖離の1σは約3.4%、2.5%なら約7%である。固定の%閾値は銘柄のボラティリティで正規化したz値に置き換える。

## 7. 傾きの使い方
傾きは MA_t-MA_{t-1} やk日変化率で測る。画面上の「角度」は縦横軸の縮尺に依存し再現性がないため使わない。線の向きの転換は価格の転換より概ね (n-1)/2 本遅れる（第1節の遅れ）。向きの3値化（上向き／横ばい／下向き）はグランビル判定やトレンドフィルタの基礎になるが、横ばい幅の設定が結果を左右する。

## 8. エビデンス（概要。詳細は [../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md)）
- Brock・Lakonishok・LeBaron (1992)：ダウ平均（1897〜1986）で移動平均と取引レンジ突破を検定し、買いシグナル後のリターンが売りシグナル後より高いとして、4つの帰無モデルと整合しないと報告 [TI-022]。
- Sullivan・Timmermann・White (1999)：同研究の26ルールを含む全ルール集合に対して White の Reality Check でデータスヌーピングを補正して再検定 [TI-023]。
- Bajgrowicz・Scaillet (2012)：1897〜2011のダウ平均で、事前に将来の最良ルールを選べず、低水準の取引コストで利益が消えると報告 [TI-024]。
- Zhu・Zhou (2009)：リターンに予測可能性がある場合や不確実な場合、資産配分に移動平均ルールを組み込む価値があるとする理論分析 [TI-025]。
- Marshall ほか (2017)：時系列モメンタムと移動平均ルールを比較し、移動平均はより早い売買シグナルを出し、どちらも大型株の系列より非大型株で成績が良いと報告 [TI-026]。
- Taylor (2014)：ダウ構成銘柄（1928〜2012）のモメンタム型ルールの利益は1960年代半ば〜1980年代半ばに偏り、空売り可能性に依存する [TI-028]。
総合すると、歴史的な有意性の報告と、補正・コスト・期間分割後の消失の報告が併存する。

## 9. 限界・失敗パターンと日本株での留意点
- 遅れ: SMA／EMA は (n-1)/2 本遅れ、転換点で必ず後追いになる。短縮手法（DEMA 等）はノイズとオーバーシュートで代償を払う。
- レンジ相場: 線が横ばいで価格が往復するとクロス・グランビル①⑤が連続損失になる。
- 期間の事後最適化: 「この銘柄は25日線が効く」は多数の期間を試した結果である可能性がある（[10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md) の最適化の危険を参照）。
- 「移動平均線はサポート／レジスタンスとして機能する」という主張の統計的検証は未確認。多数の参加者が見る水準である点は定性的な説明にとどまる。
- 日本株: 株式分割・併合・権利落ちで価格が不連続になるため、調整後株価で計算する。ストップ高・安や特別気配では終値が不連続になり、線の傾きが歪む。制度面は [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)。
- 損切り・目標値の置き方: 買いの損切りを「終値が移動平均線を下回った場合」または「線から k*ATR 下」（kは仮置き）に置く使い方が一般的で、遅れとダマシのトレードオフがある。利食いの目安として線からの乖離（z値）が大きい局面を使う見方もあるが、検証済みの規則ではない。
- 実装: 売買判定は確定した足の値のみ使い、シグナルは翌足に適用する（shift(1)）。TA-Lib との照合は 3n 本以上のウォームアップ後に行う。

## 関連文書
- [10_alt_charts_relative_strength_mtf.md](10_alt_charts_relative_strength_mtf.md)（マルチタイムフレーム・最適化の危険）
- [09_volume_breadth_sentiment.md](09_volume_breadth_sentiment.md)（VWAP／出来高）
- [../02_japan/03_other_japanese_methods.md](../02_japan/03_other_japanese_methods.md)（パーフェクトオーダー）
- [../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md)

## この文書の限界
- 検索結果のスニペットのみで確認し、証券会社・取引所・学術論文の本文は開けていない（WebFetch等が使えない環境）。引用論文は要旨レベルの確認である。
- 欧米の期間慣行（10／20／50／100／200）とグランビル③〜⑧の細部は筆者の知識（⚠M）であり、検索で独立に確認していない。
- 大和証券のグランビル解説（TI-002）は本文を未読で、存在のみ確認した。
- ノイズ利得・遅れ・クロス頻度・乖離の標準偏差は合成データ上の筆者計算であり、実市場の値ではない。
- 日本の25日線の由来、国内ツールの既定値は未確認または要確認（確認日: 2026-11-09）。
- TA-Lib の挙動は 0.8.3（PyPI、2026-10-28公開）での確認であり、他の版・他言語実装では異なり得る（確認日: 2026-11-09、要版数確認）。

## 出典
| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TI-001 | グランビルの法則（解説） | 松井証券 | — | https://www.matsui.co.jp/fx/study/article/analysis/granville/ | ✅S | 8パターン、番号順とは限らない、買い①②の内容 |
| TI-002 | 金融・証券用語解説 グランビルの法則 | 大和証券 | — | https://www.daiwa.jp/glossary/YST0443.html | ✅S | 存在のみ確認（本文未読） |
| TI-003 | グランビルの法則とは?8つの売買パターンや注意点 | OANDA証券 | — | https://www.oanda.jp/lab-education/technical_analysis/moving_average/granville/ | ✅S | 200日・日足が基本、④⑧の乖離リスク |
| TI-004 | granvilles law（解説） | gaitame.com | — | https://www.gaitame.com/beginner/market/technical/granvilles-law.html | ✅S | ①⑤が単純、②③⑥⑦は待ちの型 |
| TI-005 | グランビルの法則の買いサイン4・売りサイン8を使った取引手法 | OANDA証券 | — | https://www.oanda.jp/lab-education/technical_analysis/moving_average/buysign4_sellsign8/ | ✅S | 乖離からの逆張り |
| TI-006 | 金融・証券用語解説 移動平均線 | 大和証券 | — | https://www.daiwa.jp/glossary/YST0080.html | ✅S | 日足5/25/75、週足13/26、月足12/24、GC・DC |
| TI-007 | 移動平均線（用語集） | 野村證券 | — | https://www.nomura.co.jp/terms/japan/i/idoheikin.html | ✅S | 日足期間の列挙、DMA |
| TI-008 | moving average line（MarketSpeed FX ヘルプ） | 楽天証券 | — | https://www.rakuten-sec.co.jp/MarketSpeedFX/onLineHelp/info/chart/moving_average_line.html | ✅S | 既定表示値は検索要約による（要確認） |
| TI-009 | stock moving average guide | crexgroup | — | https://crexgroup.com/ja/sec/stock-investment/stock-moving-average-guide/ | ✅S | 25日≒1か月、75日、200日の意味づけ |
| TI-010 | 乖離率の解説 | 野村證券 | 2024 | https://www.nomura.co.jp/wealthstyle/article/0235/ | ✅S | 日経平均5%程度、個別10%程度 |
| TI-011 | 乖離率の解説 | SMBC日興証券 | — | https://www.smbcnikko.co.jp/first/learn/stock/ouyo01/ | ✅S | ±5% |
| TI-012 | 乖離率（用語集） | マネックス証券 | — | https://media.monex.co.jp/ud/glossary/678f1a30b57622c5a700002d | ✅S | 差を移動平均で割る定義 |
| TI-013 | MA Disparity（オープンソーススクリプト） | TradingView | — | https://my.tradingview.com/script/xejm7UKn | ✅S | -10%以下で売られすぎの可能性 |
| TI-015 | Kaufman's Adaptive Moving Average (KAMA) | StockCharts ChartSchool | — | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/kaufmans-adaptive-moving-average-kama | ✅S | KAMA(10,2,30)、SC式 |
| TI-016 | Kaufman's Adaptive Moving Average (KAMA) | Corporate Finance Institute | — | https://corporatefinanceinstitute.com/resources/equities/kaufmans-adaptive-moving-average-kama/ | ✅S | 更新式 |
| TI-017 | HMA（関数ページ） | TA-Lib | — | https://ta-lib.org/functions/hma | ✅S | Alan Hull、整数切り捨て（検索要約による） |
| TI-018 | Hull Moving Average | Barchart | — | https://barchartsolutions.atlassian.net/wiki/spaces/CMDTYV/pages/1094189401/Hull+Moving+Average | ✅S | 式の確認 |
| TI-019 | Anchored VWAP | Optuma | — | https://www.optuma.com/kb/optuma/tools/averages/anchored-volume-weighted-average-price-vwap | ✅S | 累積(TP×V)/累積(V) |
| TI-020 | Anchored VWAP | LuxAlgo | — | https://www.luxalgo.com/library/concept/anchored-vwap.md | ✅S | 同上、起点の考え方 |
| TI-021 | TA-Lib（PyPI JSON） | PyPI | 2026 | https://pypi.org/pypi/TA-Lib/json | ✅S | 0.8.3（2026-10-28公開）。数値照合は同版で実施、要版数確認 |
| TI-022 | Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | Brock, Lakonishok, LeBaron（J. Finance） | 1992 | https://consensus.app/papers/details/4c4ec203508c5f0e98178eb373930446/ | ✅S | 要旨のみ確認 |
| TI-023 | Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | Sullivan, Timmermann, White（J. Finance） | 1999 | https://consensus.app/papers/details/d44e019194235c9e94e158ebd482f2a1/ | ✅S | 要旨のみ確認 |
| TI-024 | Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs | Bajgrowicz, Scaillet（J. Financial Economics） | 2012 | https://consensus.app/papers/details/132354490e9a5a0a9fecaa045a94b6b0/ | ✅S | 要旨のみ確認 |
| TI-025 | Technical analysis: An asset allocation perspective on the use of moving averages | Zhu, Zhou（J. Financial Economics） | 2009 | https://consensus.app/papers/details/cf9f2cf20c205ed88f14db1aca0d40c2/ | ✅S | 要旨のみ確認 |
| TI-026 | Time series momentum and moving average trading rules | Marshall, Nguyen, Visaltanachoti（Quantitative Finance） | 2017 | https://consensus.app/papers/details/b1ff2fefd38250869a26c1cab6ec8949/ | ✅S | 要旨のみ確認 |
| TI-028 | The Rise and Fall of Technical Trading Rule Success | Taylor（J. Banking & Finance） | 2014 | https://consensus.app/papers/details/ea673f2c3898511db88d25a05486bf36/ | ✅S | 要旨のみ確認（プレプリント版の記録） |
| TI-030 | Granville's New Key to Stock Market Profits | Joseph Granville（Prentice-Hall） | 1963 | — | ⚠M | グランビルの法則の原典。出版社・年は記憶による |
| TI-031 | DEMA／TEMA の提案論文 | Patrick Mulloy（Technical Analysis of Stocks & Commodities） | 1994 | — | ⚠M | 題名・号は未確認 |
| TI-032 | Technical Analysis of the Financial Markets | John J. Murphy（New York Institute of Finance） | 1999 | — | ⚠M | 移動平均の一般的な解説書 |
