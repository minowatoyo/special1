# 波動・比率・需給の理論：エリオット波動・フィボナッチ・ワイコフ・ギャン・ハーモニック・SMC
> 要約: エリオット波動（規則とガイドライン、修正波、主観性への批判）、フィボナッチ（比率の由来、計算式、検証）、ワイコフ（3法則、蓄積／分配のフェーズA〜E、スプリング／アップスラスト）、ギャン、ハーモニック、SMC/ICTを整理した。
> いずれも定義の自由度が大きく、検索で確認できた範囲では定量的な支持は乏しい。フィボナッチ比率の50%は数列由来でなくダウ理論由来であること、DJIAの連続トレンド比に黄金比のクラスタがないとの報告も示した。
> 最終更新: 2026-11-09

表記: `[TS-nnn]` は出典ID。⚠Mは記憶に基づく。

## 0. 体系の比較
| 体系 | 核心 | 検証のしやすさ | エビデンス（検索で確認できた範囲） |
|---|---|---|---|
| エリオット波動 | 5波の推進と3波の修正の反復 | 低（カウントが主観的） | 定量的な支持は確認できず。Prechterも価格フィルタ後の値動きは一般にフィボナッチ倍率に従わないと認める[TS-103] |
| フィボナッチ | 比率で戻り・目標を定める | 高（水準が数値で定義される） | 弱い。DJIAの連続トレンド比に黄金比のクラスタなし[TS-104]。ゾーン幅が広いほど反発確率が上がる[TS-105] |
| ワイコフ | 需給の局面（蓄積→上昇→分配→下降） | 中（定性的、ラベル付けは事後） | 査読研究は未確認 |
| ギャン | 角度線・正方形・時間 | 低 | 独立した検証は未確認 |
| ハーモニック | XABCDの比率で反転ゾーン | 中（比率は定義できる） | 体系的検証は未確認（単一事例のみ[TS-125]） |
| SMC/ICT | 流動性・オーダーブロック・FVG | 低〜中 | 査読研究は見当たらないとのベンダー記事のみ[TS-126] |

## 1. エリオット波動
- 構造: 推進波は1-2-3-4-5（1・3・5が推進、2・4が逆行の修正）、修正波はA-B-C。波は階層（degree）を持ち自己相似で、上位の波の内部に下位の波が入る[TS-100]。
- 規則（破れば数え直し）[TS-101]: (1)波2は波1の起点を超えて戻らない、(2)波3は波1・3・5の中で最短にならない、(3)波4は波1の価格領域に入らない（ダイアゴナルは例外）。
- ガイドライン（破ると信頼度が下がる）[TS-102]: オルタネーション（波2が鋭いなら波4は横ばい、など）、等価（推進波の2つが同程度）、チャネリング（平行チャネル内）、エクステンション（推進波の1つが伸びる。株式では波3が多い、⚠M）。

| 修正波 | 内部構造（⚠M） | 特徴 |
|---|---|---|
| ジグザグ | 5-3-5 | 鋭い逆行 |
| フラット | 3-3-5 | 横ばい。拡大型・ランニング型の変種 |
| トライアングル | 3-3-3-3-3 | 収束。波4やB波に出やすい |
| ダブル／トリプル・スリー | W-X-Y（-X-Z） | 修正の連結 |
- 用語（⚠M）: ダイアゴナルは波5（または波1）に現れる楔形の推進波で、波4が波1と重なることが許される。終端型は内部が3-3-3-3-3の構造とされる。切断（トランケーション）は波5が波3の終点に届かない形で、強い反転の示唆とされる。
- フィボナッチ関係の典型例（諸説、⚠M）: 波2は波1の50〜61.8%戻し、波3は波1の1.618倍前後、波4は波3の23.6〜38.2%戻し、波5は波1と同程度または波1〜3の値幅の0.618倍。
- 批判: (a)同じ値動きに複数のカウントが成立し得る、(b)無効化水準を後から動かせる、(c)階層の取り方に自由度があり、反証可能性が低い。DJIA 1914〜2002年の連続トレンド比に黄金比等のクラスタリングは見られなかったと報じられた[TS-104]。Prechter自身も同研究に触れ、価格フィルタ後の値動きは一般にフィボナッチ倍率に従わないと認めている[TS-103]。査読付きの検証（アウトオブサンプル）は検索で確認できていない。
- 実装案: 確認済みピボット列（→01 §2）から候補を列挙し、規則で棄却、ガイドライン適合度でスコア化する。出力は「カウント候補」であり予測ではない。
```
# 上昇推進の候補: 連続6ピボット p0..p5（p0=起点）。w1=p1-p0 w2=p1-p2 w3=p3-p2 w4=p3-p4 w5=p5-p4
規則: p2 > p0   and   w3 >= min(w1, w5)   and   p4 > p1
得点: Σ 適合（w3/w1≈1.618、w2/w1∈[0.5,0.618]、w4/w3∈[0.236,0.382] など）  ※閾値は設計例
```

## 2. フィボナッチ
フィボナッチ数列 0,1,1,2,3,5,8,13,21,34,55,89,144… の隣接比は黄金比 φ=1.6180339… に収束する。

| 比率 | 由来 | 用途 |
|---|---|---|
| 61.8% | F(n)/F(n+1) → 1/φ = 0.618034 | 主要な戻し |
| 38.2% | F(n)/F(n+2) → 1/φ² = 0.381966 | 浅い戻し |
| 23.6% | F(n)/F(n+3) → 1/φ³ = 0.236068 | 最も浅い戻し |
| 78.6% | √(1/φ) = 0.786（導出は資料で異なる[TS-033]）。1−23.6%=76.4%を使う流儀もある[TS-114] | 深い戻し |
| 50% | 数列由来ではなくDow理論の半値戻しに由来[TS-109] | 戻し |
| 127.2%／161.8%／261.8% | √φ／φ／φ² | 拡張・目標 |
- 戻し水準: 上昇（安値Lo→高値Hi）の場合 `水準 = Hi - r*(Hi-Lo)`、r∈{0.236, 0.382, 0.5, 0.618, 0.786}。例：Lo=100, Hi=130 → 38.2%戻し=118.54、50%=115、61.8%=111.46。
- 拡張・目標（AB=CD型）: `D = C + k*(B-A)`。例：A=100, B=130, C=115 → k=1.0で145、k=1.618で163.54。
- 時間帯は起点から1・2・3・5・8・13・21・34・55・89・144…本後[TS-110]、ファンは山から38.2／50／61.8%戻しの水準を通る線[TS-111]、アークは23.6／38.2／50／61.8%の円弧[TS-112]。
- エビデンス: Wikipediaは水準の有意性がデータでは確認できなかったと記す[TS-113]。DJIAの連続トレンド比に黄金比のクラスタなし[TS-104]。3つの株式市場でゾーン化して評価した研究では、ゾーン幅が広いほど反発確率が高いが（幅が広いほど当たりやすいという性質を含む）、収益戦略を意味せず、フィボナッチと非フィボナッチのゾーンで価格挙動に統計的差はないと報じられた[TS-105]。エネルギー株・暗号資産の短期標本（2017-11〜2020-01）で買い持ちを上回ったとする報告もある[TS-106]。多数が見ているため自己成就的に効くという主張は検証されていない。
- クラスタ（コンフルエンス）: 複数のスイングから引いた水準が近接した帯を重視する流儀がある。水準の本数が増えるほど「どこかに当たる」確率が上がるため、近接帯の有意性は水準数と帯幅で補正して評価する必要がある（論理的な注意）。
- 実装: 戻し点は水準でなくゾーン（±k×ATR）として扱う。アンカーはジグザグの確定ピボットで固定する。対照として非フィボナッチ比率（例：30・45・55・70%）を同条件で評価し、反発の定義（戻り幅≧N×ATRをM本以内）を事前に固定する。多重検定に注意する。

## 3. ワイコフ（Wyckoff）
- 3法則[TS-115]: 需給（需要が勝てば上昇、均衡ならレンジ）、原因と結果（レンジの大きさが以後の動きの大きさを決める。ポイント・アンド・フィギュアで目標を数える）、努力と結果（出来高＝努力、価格変化＝結果。努力に結果が伴わなければ弱さの兆候）。
- 大口の意図を擬人化する「コンポジット・マン」という思考法がある（検証不能な仮説、⚠M）。

| 局面 | 蓄積（底圏） | 分配（天井圏）[TS-117] |
|---|---|---|
| A 動きの停止 | PS（予備的支持）、SC（セリング・クライマックス：高出来高・広い値幅）、AR（自動反発）、ST（二次テスト） | PSY（予備的供給）、BC（バイイング・クライマックス）、AR（自動反応）、ST |
| B 原因の構築 | レンジ内の往復で需給を吸収。最も長い。STが複数 | アップスラスト（UT）の反復 |
| C テスト | スプリング（支持を一時割って回復）またはシェイクアウト。無い場合もある（教育資料の記述） | UTAD（分配後アップスラスト）：抵抗を超えて戻る最終的な偽ブレイク。任意 |
| D 優勢の確認 | SOS（強さの兆候：広い値幅・出来高増の上昇）、LPS（最後の支持点）、BU（バックアップ） | SOW（弱さの兆候：支持割れ、広い値幅・出来高増）、LPSY（最後の供給点） |
| E 離脱 | レンジ上抜けとマークアップ | レンジ下抜けとマークダウン |
- スキーマの補助概念（⚠M）: レンジの上限付近の抵抗を「クリーク」、下限付近の支持を「アイス」と呼び、SOSでクリークを超えることを「ジャンプ」、その後の押しをBU／LPSとする。ポイント・アンド・フィギュアでの目標は `カラム数×ボックス幅×転換枚数` を起点から投影して数える（→10_alt_charts_relative_strength_mtf.md）。
- 蓄積→マークアップ→分配→マークダウンが循環するという見取り図で、各局面のイベント名は教育資料で共通性が高い[TS-117][TS-118]。
- 定量化の設計例:
```
spring  : Low[t] < support - ε  かつ  Close[t+j] >= support (j=0〜3)    # ε=0.1〜0.5*ATR
upthrust: High[t] > resistance + ε かつ Close[t+j] <= resistance (j=0〜3)
出来高   : スプリングが低出来高なら「売り枯れ」、高出来高なら「吸収」と解釈が分かれる（要検証）
努力対結果: ER_t = Volume_t / (|Close_t - Close_{t-1}| / ATR_t)         # 大きいほど努力の割に結果が小さい
```
- 批判・限界: 局面ラベルは事後的で、同じレンジが蓄積とも分配とも読める。スキーマは理想化された鋳型である。査読研究は本調査では未確認。検証済みの近縁概念はレンジ・ブレイクとダマシ（→01 §5）、出来高と収益の関係（→09_volume_breadth_sentiment.md）。
- 日本株: 出来高は東証出来高か売買代金か、PTSを含むかを固定する。低位株の仕手的な値動きは蓄積・分配に見えやすく、判断は慎重にする。需給指標は../02_japan/05_supply_demand_indicators.md。

## 4. ギャン（Gann）
- 角度線: 1×1は45度で、時間1単位に価格1単位[TS-119]。ほかに2×1、3×1、4×1、8×1、1×2、1×3、1×4、1×8を重要な高安から扇状に引く（⚠M）。時間と価格の1単位の対応が任意なので、チャートのスケールで1×1の傾きが変わる。
- スクエア・オブ・ナイン: 平方根をずらして二乗する形で水準を作る[TS-120]。
```
Level(Δ) = ( sqrt(P) + Δ/180 )^2     # Δ=±45, ±90, ±180, ±360 度。180度で平方根が+1（⚠M）
例: P=100 → +180度: (10+1)^2=121  +360度: (10+2)^2=144  -180度: (10-1)^2=81
```
- 批判: 公表された成功率がなく、起点・スケール・追加の線の自由度が大きく後付け適合が容易[TS-121]。幾何学・天文学・占星術に基づくとされる[TS-119]。独立した検証は本調査では未確認。検証するなら、起点を確定ピボットでルール化し、線の本数とスケール（対数／算術）を固定し、ランダムな傾きの線と比較する。

## 5. ハーモニック・パターン
- XABCDの5点の比率で反転ゾーン（PRZ）を定義する手法。起源はGartleyの著書で、年は1932/1935と資料で揺れる[TS-122]。Pesaventoがフィボナッチ比率を与え、Carneyが体系化した（⚠M）。ChartSchoolはGartley、Butterfly、Crab、Bat、Shark、Cypherを主要型に挙げる[TS-122]。

| 型 | B点（XAの戻し） | D点（XA基準） |
|---|---|---|
| Gartley | 0.618 | 0.786戻し |
| Bat | 0.382〜0.50 | 0.886戻し |
| Butterfly | 0.786 | 1.27〜1.618拡張 |
| Crab | 0.382〜0.618 | 1.618拡張 |
- 比率の定義（慣行）: B点=|B-A|/|X-A|、D点(XA基準)=|D-A|/|X-A|、拡張はBC基準で|D-C|/|B-C|。X→A→B→C→Dを交互に高安とする。
- 上表は低品質の二次資料2件の一致による[TS-123][TS-124]。C点やBC／ABの比率は資料で異なり省略した。許容±3%の記述がある[TS-124]。
- 限界: 比率の組合せが多く自由度が高いため後付け適合に陥りやすい。体系的な検証は未確認で、単一事例の報告があるのみ[TS-125]。実装は、ジグザグの確定ピボットからXABCDを探索し、比率を±τで判定し、検出数と先行リターンを対照と比較する。

## 6. スマートマネー（SMC／ICT）系
- 用語（標準定義はなく発信者で異なる、⚠M）: 市場構造（BOS=構造の更新、CHoCH/MSS=転換）、流動性（等高値・等安値の外側に溜まる損切り注文を「掃く」）、オーダーブロック（大きな動きの起点の逆色の最終足）、フェアバリューギャップ（FVG：3本足で1本目の高値と3本目の安値の間に残る未約定帯）、プレミアム／ディスカウント（レンジの50%を境に上側／下側）。
```
BOS(強気) : Close[t] > 直前の確認済みスイング高値            # 構造の更新（継続）
CHoCH(弱気): 上昇構造の中で Close[t] < 直前の確認済みスイング安値 # 構造の転換
強気FVG   : Low[t] > High[t-2]  → 未約定帯 [High[t-2], Low[t]]（弱気は High[t] < Low[t-2]）
```
- 古典概念との対応: スイング高安（ダウ）、支持抵抗とダマシ、窓、半値戻しに近く、新規性は用語体系と物語性にある。
- エビデンス: 査読研究が見当たらないとするベンダー記事があり、FVGはランダムウォークでも頻出する（自社シミュレーションで足の29.8%、20本以内に埋まる割合83.4%）ので「埋まる」統計は根拠にならないと主張する[TS-126]。これはベンダーの未検証の主張である。損切り注文がキリ番の直外側に集中する為替の実証[TS-013]は、流動性の掃き出しという機序が現実にあり得ることを示すが、SMCルールの収益性を示すものではない。
- 日本株: 24時間市場向けの概念が多く、寄付き・大引けの板寄せ、昼休み、値幅制限がある東証では、FVGや時間帯ルールの定義が合わない。

## 7. 検証設計の共通原則
- 主観性の高い体系は、(1)ルールと無効化水準を事前に固定、(2)検出器が出した全イベントを対象にし都合のよい事例を選ばない、(3)ランダムな水準・角度・比率（プラセボ）との比較、(4)探索した水準・比率の数に応じた多重検定補正、(5)期間分割と費用控除、を満たして初めて評価に値する。
- 事例集（成功例のチャート）は証拠にならない。検出は確認日時点の情報だけで行い、事後ラベル付けを避ける。

## 関連文書
- 01_price_structure.md（スイング・支持抵抗・窓）／02_chart_patterns.md／05_practitioner_frameworks.md／09_volume_breadth_sentiment.md
- ../02_japan/05_supply_demand_indicators.md／../03_evidence/01_academic_literature.md

## この文書の限界
- 外部ページは開けず、検索結果の要約・論文レコードで確認した。Frost & Prechter、Wyckoff、Gann、Carneyの原典は未読。
- エリオットの修正波構造、フィボナッチ関係、ギャンの角度とスクエア・オブ・ナインの式、コンポジット・マン、ハーモニックの帰属は記憶に基づく（⚠M）。ハーモニックの比率は低品質資料の一致のみ。
- ワイコフのイベント名は教育資料の要約で確認した。一次文献（Wyckoff本人の講座）との照合は未了。
- ワイコフ・ギャン・ハーモニック・SMCについて査読付きの検証は確認できていない（検索回数の上限に到達し追加探索ができなかった）。
- SMCのシミュレーション数値は未検証のベンダー主張である。

## 出典

> 検証タグ: ✅S=検索結果・論文レコード等で書誌と要点を確認（本文は未読）／⚠M=記憶のみ／❓=要確認。URLは検索結果に現れたものだけを記載し、無いものは「—」とした。

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TS-013 | Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis | Osler／Journal of Finance | 2003 | — | ✅S | DOI 10.1111/1540-6261.00588 |
| TS-033 | Tapeboard: What is Fibonacci Retracement | Tapeboard | — | https://tapeboard.com/blog/glossary-what-is-fibonacci-retracement | ✅S | 導出式の例 |
| TS-100 | Elliott Wave Principle: Key to Market Behavior | Frost, Prechter | 1978 | — | ✅S | 書誌確認。本文未読 |
| TS-101 | Elliott Hard Rules | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/elliott-hard-rules/ | ✅S | 3つの鉄則の要約（ベンダー） |
| TS-102 | Elliott Guidelines | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/elliott-guidelines.md | ✅S | ガイドラインの要約（ベンダー） |
| TS-103 | Elliott Waves, Fibonacci and Statistics | Prechter | 2006 | — | ✅S | 実務家コメント。Batchelor & Ramyarに言及 |
| TS-104 | Magic numbers in the Dow | Batchelor, Ramyar（Cass Business School） | 2006 | https://openaccess.city.ac.uk/16276/ | ✅S | 報道ベースの要約。本文未読 |
| TS-105 | Automatic identification and evaluation of Fibonacci retracements: Empirical evidence from three equity markets | Tsinaslanidis, Guijarro, Voukelatos／Expert Systems with Applications | 2022 | — | ✅S | DOI 10.1016/j.eswa.2021.115893 |
| TS-106 | Energy crypto currencies and leading U.S. energy stock prices: are Fibonacci retracements profitable? | Gurrib ほか／Financial Innovation | 2022 | — | ✅S | DOI 10.1186/s40854-021-00311-8 |
| TS-109 | ChartSchool: Fibonacci Retracements | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/fibonacci-retracements | ✅S | 50%はDow理論由来との記述 |
| TS-110 | ChartSchool: Fibonacci Time Zones | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-annotation-tools/fibonacci-time-zones | ✅S | 時間帯の記述 |
| TS-111 | ChartSchool: Fibonacci Fans | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-annotation-tools/fibonacci-fans | ✅S | ファンの記述 |
| TS-112 | ChartSchool: Fibonacci Arcs | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-annotation-tools/fibonacci-arcs | ✅S | アークの記述 |
| TS-113 | Fibonacci retracement | Wikipedia | — | https://en.wikipedia.org/wiki/Fibonacci_retracement | ✅S | 有意性は確認できずとの記述 |
| TS-114 | Which is the real fibonacci level: 78.61% or 76.39%? | BabyPips Forums | — | https://forums.babypips.com/t/which-is-the-real-fibonacci-level-78-61-or-76-39/56409?page=2 | ✅S | スレッド題名のみ確認 |
| TS-115 | The Laws of Wyckoff | StockCharts（Wyckoff Power Charting） | 2015 | https://stockcharts.com/articles/wyckoff/2015/12/the-laws-of-wyckoff.html | ✅S | 3法則の記述 |
| TS-117 | Distribution Definitions | StockCharts（Wyckoff Power Charting） | 2015 | https://my.stockcharts.com/articles/wyckoff/2015/09/distribution-definitions.html | ✅S | 分配局面の用語 |
| TS-118 | Wyckoff Schematics: Visual Templates for Market Timing Decisions | （著者・年はURL名のみで未確認） | — | https://www.prorealcode.com/wp-content/uploads/2019/11/WyckoffSchematics-VisualTemplatesForMarketTimingDecisions.pdf | ✅S | 蓄積スキーマ。著者・年は未確認 |
| TS-119 | Gann angles | Wikipedia | — | https://en.wikipedia.org/wiki/Gann_angles | ✅S | 1×1=45度の記述 |
| TS-120 | Square of 9 Gann Fan | Optuma | — | https://www.optuma.com/kb/gann-and-astro/gann-tools/square-of-9-gann-fan | ✅S | 平方根を動かす式の説明 |
| TS-121 | Gann Square of Nine | The Right Trader（教育サイト） | — | https://therighttrader.com/learn/elliott-wave-and-cycles/gann-square-of-nine | ✅S | 教育サイト。成功率の公表なしとの指摘 |
| TS-122 | ChartSchool: Harmonic Patterns | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/harmonic-patterns | ✅S | 起源・主要型・Fibonacci応用 |
| TS-123 | Harmonic patterns ratio table（コミュニティ資料） | skills.sh | — | https://www.skills.sh/hkuds/vibe-trading/harmonic | ✅S | 低品質の二次資料 |
| TS-124 | Harmonic Pattern（要約文書） | Scribd（投稿者不明） | — | https://www.scribd.com/document/422860118/Harmonic-Pattern | ✅S | 低品質の二次資料 |
| TS-125 | Taking investment decisions on the futures contracts market with the application of Bat harmonic pattern | Bednarz | 2013 | — | ✅S | DOI 10.2478/foli-2013-0002。単一事例 |
| TS-126 | Does ICT / Smart Money Concepts work? | Thor Trade Copier（ベンダーブログ） | 2026 | https://thortradecopier.com/blog/does-ict-smart-money-concepts-work | ✅S | ベンダーの主張。未検証 |
