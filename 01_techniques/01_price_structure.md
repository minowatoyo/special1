# 価格構造の基礎：ダウ理論・トレンド・支持抵抗・ブレイクアウト・ギャップ・ピボット
> 要約: チャート分析の土台となる価格構造を、定義・規則・計算式・実装時の閾値の決め方まで整理した。
> ダウ理論は6原則と批判、トレンドはスイング／ジグザグの機械的定義、トレンドラインは引き方と対数／算術軸、支持抵抗は強さの測り方を扱う。
> ブレイクアウトは確認フィルタ、ギャップは分類と窓埋めの実証、ピボットは4方式の式を扱う。
> 「当たる」根拠は限定的で、数値の多くは慣行値である。
> 最終更新: 2026-11-09

表記: `[TS-nnn]` は末尾の出典ID。⚠Mは記憶に基づく記述。確認範囲は「この文書の限界」を参照。

## 1. ダウ理論（Dow Theory）
- 成り立ち: Charles Dowは体系を書き残さず、1902年にNelsonが「Dow理論」と命名し、後継のHamiltonの社説（1902〜1929年）とRheaの整理で普及した[TS-005]。以下の6原則は後世の要約であり、Dow本人の条文ではない。Edwards & Magee[TS-004]やMurphy[TS-027]が体系化した。

| # | 原則 | 内容 | 実装・解釈上の注意 |
|---|---|---|---|
| 1 | 平均はすべてを織り込む | 価格は入手可能な情報と期待を反映[TS-001] | 織り込みの速さは効率性の問題（→証拠編） |
| 2 | トレンドは3種類 | 主要・二次・小。大和証券は長期=1年〜数年／中期=3週間〜3か月／短期=3週間未満[TS-001]。英語圏には小トレンドを6日未満とする説明もある[TS-030] | 期間は慣行値。機械化は§2で自前定義 |
| 3 | 主要トレンドは3段階 | 先行期（先行投資家の仕込み）・追随期・利食い期[TS-001] | 判定は事後的 |
| 4 | 平均は相互に確認 | 原典は工業株平均と鉄道株平均が同方向に更新[TS-030] | 現代の対応物（日経225とTOPIX、業種指数等）は分析者の仮説 |
| 5 | 出来高で確認 | 主要トレンド方向に出来高が拡大。強気相場は上昇で増え下落で減る[TS-001][TS-030] | Dowは補助的確認と位置づけた[TS-030] |
| 6 | 明確な転換まで継続 | 高値・安値の切り上げ（下げ）が崩れるまで継続 | 「明確」が主観的。§2で機械化。判断は終値基準（⚠M） |

補足（⚠M）: Rheaは2〜3週間以上、値幅約5%以内の横ばいを「ライン」と呼び、その抜けを重視した。

**批判的検討**
- 主観性と遅れ: 二次トレンドか主要トレンド転換かはリアルタイムで判別しにくく、完成したスイングを要するため信号は遅い[TS-030]。Edwards & Magee自身も、解釈依存で中期トレンドの変化には警告が乏しいと述べる（章要旨）[TS-004]。
- 前提の古さ: 鉄道と工業の時代に基づく原則4は、現代の指数構成では必然性が弱い[TS-030]。日経225（価格加重）とTOPIX（時価総額加重）の乖離は構成方式の違いも反映する。
- 実証: CowlesはHamiltonを否定的に評価したが、リスク調整を欠くとして、BrownらはHamiltonの1902〜1929年の判断に正のαを見出した[TS-003]。標本は一人の裁量判断で、事後解釈の余地が大きい。機械的ルールの検証は§5に続く[TS-017]。

## 2. トレンドの定義とスイング／ジグザグ
**定義**: 上昇トレンド＝確認済みスイング高値・安値がともに切り上がる（HH＋HL）。下降＝ともに切り下がる（LH＋LL）。どちらでもなければレンジ／遷移。

| 現状態 | 警戒 | 転換確定の例 |
|---|---|---|
| 上昇 | 終値が直近確認安値を割る | 戻り高値が直前高値を超えず（LH）、安値も更新（LL） |
| 下降 | 終値が直近確認高値を超える | 押し安値が直前安値を割らず（HL）、高値も更新（HH） |
| レンジ | 上限／下限を終値で抜ける（§5） | 抜けた方向に新スイングが形成 |

**スイング検出**
1. Nバー・フラクタル: H[i]がH[i-N..i+N]の最大ならスイング高値。確認はN本遅れ。N=2（5本）が広く使われる（⚠M）。
2. ジグザグ（反転閾値型）: 極値を追跡し、極値からθ戻した時点で確定する[TS-021]。θは比率・固定幅・ATR倍。比率の目安は5〜20%程度でボラティリティ依存[TS-022]。小さいとノイズを拾い、大きいと反転を逃す。
3. 方向転換（Directional Change）: ジグザグと同型の事象駆動型（⚠M）。

```
# 高安ベースのジグザグ。dir=+1:上昇脚追跡 / -1:下降脚追跡。θ=反転閾値（比率）
if dir == +1:
    if H[t] > ext.price: ext = (H[t], t)
    elif L[t] <= ext.price*(1-θ): pivot_high(ext); dir=-1; ext=(L[t], t)
else:
    if L[t] < ext.price: ext = (L[t], t)
    elif H[t] >= ext.price*(1+θ): pivot_low(ext); dir=+1; ext=(H[t], t)
# ATR型: θ_t = k*ATR(n)_t/ext.price（k=2〜4, n=14は設計例）。外側足の扱い・初期方向は実装依存
```
- 再描画: 最新の脚の端点は新極値で動く[TS-021]。ピボットは「確定足」の時刻で記録する。極値の足に遡って使うとルックアヘッド・バイアスになる。
- θの決め方: (a) 保有期間に見合う脚の大きさ（往復コストとノイズの数倍）から逆算、(b) 年間スイング数が目標（例：中期で年6〜12回）になるようkを調整、(c) 複数θで結論が頑健か確認。評価標本でθを最適化しない。
- 限界: レンジ相場ではθが小さいと転換判定がノコギリ状に頻発し、大きいと遅れる。トレンド強度の補助量には ln P の回帰傾き（日率）とR²を使う。ADX等は08_volatility_and_trend_strength.md。

## 3. トレンドライン／チャネル
| 項目 | 規則 | 備考 |
|---|---|---|
| 基本 | 上昇は2点以上の安値、下降は高値を結ぶ[TS-024] | 終値同士を結ぶ流儀もある[TS-024]。ヒゲ基準か終値基準かを固定 |
| 確定と検証 | 最初の2点で線が決まり、3点目以降で検証[TS-006] | 接触が多く期間が長い線ほど重視 |
| 傾斜 | 急傾斜の線は短期の急変に引かれ信頼性が低い[TS-006] | 傾斜上限を設ける（例：ATR×k／日） |
| ブレイク | 終値が線をATR×kまたは%の幅で超えたら判定。ダマシがあり水平線や山谷分析で確認[TS-006] | 判定幅は慣行値 |

- チャネル: 一方の線を反対側の極値へ平行コピー[TS-024]。回帰チャネル（回帰線±kσ）やAndrewsのピッチフォークも使われる。限界：起点・終点・ヒゲか終値かの自由度が大きく、事後に都合のよい線を引ける。検証には機械的な規則が必須である。
- 実装案: 確認済みスイング安値の全ペア(i<j)から直線を作り、(1)間の終値が線を許容幅τ（例：0.25ATR）以上割らない、(2)傾斜が上限以内、を満たす候補を接触数と長さで採点する。Theil–Sen等のロバスト回帰も使える（⚠M）。
- 対数軸と算術軸: 対数軸は等しい縦距離が等しい変化率、算術軸は等しい価格差[TS-009]。数日〜数か月ではスケールの影響は小さい[TS-008]。長期・大変動では対数が有用で、StockChartsは優劣を好みの問題としつつ長期は対数が通常好ましいとする[TS-008]。ラインは描いたスケールでのみ直線であり、切替で曲がる[TS-009]。数か月以上のラインは ln P 上で当てはめ、傾きを年率成長率として読む。

## 4. 支持線・抵抗線
- 定義: 線でなく価格帯（ゾーン）として扱う。幅はATRの0.25〜1倍など銘柄の揺らぎに合わせる（設計例）。
- 役割転換: 破られた支持線は抵抗線に、抵抗線は支持線になりやすい[TS-007]。旧支持付近で買った投資家の「トントン売り」で説明されるが、教育資料の説明にとどまる。

| 同定方法 | 内容 | 根拠・限界 |
|---|---|---|
| 前回の高値・安値 | §2の確認済みスイング | 基本。θに依存 |
| キリ番 | 100円・500円・1,000円、指数の1,000円刻み等 | 為替では利確注文がキリ番に、損切注文が直外側に集中[TS-013]。DJIAの100の倍数が節目との先行研究もある[TS-016]。日本株の個別銘柄は未確認 |
| 出来高の多い価格帯 | 価格帯別出来高の高ノード | 流動性の価格水準への集中は報告あり[TS-016]。ビン幅に敏感 |
| 52週高安値・窓の端 | 参照点として多用 | アンカリングの仮説（未検証） |

| 強さの要素 | 内容 | 根拠 |
|---|---|---|
| 反発回数 | 多いほど再反発しやすい | 日中データ[TS-014] |
| 新しさ | 古い水準ほど確率が低下。重みを exp(-経過日数/τ) とする | [TS-014] |
| 出来高・反発幅・重なり | 出来高が多い／過去の反発幅が大きい／キリ番・前回高値・移動平均が近接 | 通説。多因子の重なりが確率を上げる検証は未確認 |
| 時間軸 | 週足・月足の水準は日足より重い | 通説 |

- クラスタ化: 確認済みスイング価格を1次元クラスタリング（距離ε=0.5〜1ATR）し、ゾーン＝最小〜最大、強さ＝Σexp(-age/τ)＋出来高の重み（設計例）。
- 実証: 為替会社提供の水準は日中のトレンド中断を予測した[TS-032]。米国株の水平支持抵抗では、支持線の方が抵抗線よりトレンド中断を当てるが買い持ちを上回る超過収益はなかった[TS-015]。反発しやすいことと取引で儲かることは別問題である。

## 5. ブレイクアウトとダマシ
| フィルタ | 例 | 注意 |
|---|---|---|
| 終値基準 | 終値が水準を超えた場合のみ成立 | 大引け待ちで遅れる |
| 幅（ATR） | 終値が水準をATR×k超え。スクリプトの設定例はk=0.10〜0.25[TS-034] | kは市場依存 |
| 出来高 | 突破日が平均（20〜50日）の1.5倍など[TS-034] | 倍率は作者の選択。株式は実出来高だがPTS等の扱いに注意 |
| 連続性 | 2日連続終値、翌足が範囲内に戻らない | 一気に上がる場合は取り逃がす |
| リテスト | 突破後に水準へ戻り反発を確認。許容0.3〜0.6ATR・8〜12本、または0.30〜0.45ATR・30〜50本など設定は食い違う[TS-034] | 戻らず走る突破を取り逃がす |

- 確認はダマシを消す手段ではなく発注位置とサイズの判断で、待てば失敗時の約定は改善するが、続伸時の取りこぼしを払う[TS-023]。ダマシの型：ヒゲだけの突破、窓突破の即時埋め、出来高を伴わない突破、直上に別の抵抗が重なる突破。
- 実証: レンジ・ブレイクと移動平均はDJIA 1897〜1986年で支持された[TS-017]。DJIA構成銘柄1928〜2012年では利益が1960年代中頃〜80年代中頃に集中し空売りに依存[TS-162]、米国株1990〜2004年ではほぼ不利で小型・低流動性で相対的に有利[TS-171]。総覧ではデータスヌーピング等が指摘される[TS-028]。有効性は市場・期間に強く依存する。
- 実装: 水準は前日までの確定情報で作る。窓で水準を超えて始まった場合は始値（スリッページ込み）で約定させる。ATRは分割・併合調整後の系列で計算する。

## 6. ギャップ（窓）
- 定義: 窓＝日足で Low[t]>High[t-1]（上窓）または High[t]<Low[t-1]（下窓）で、取引が成立しなかった価格帯[TS-004]。寄付きギャップ＝Open[t]とClose[t-1]の差で、学術研究はこちらを分析することが多い[TS-019]。

| 種類 | 位置 | 特徴・窓埋め |
|---|---|---|
| コモン（エリア） | 持ち合いの内部 | 方向性なし。早く埋まりやすいとされる（通説） |
| ブレイクアウェイ | 持ち合い・パターンの完成時 | 新しい動きの始まり。出来高を伴い、多いほど埋まりにくい[TS-025] |
| ランナウェイ（継続・測定） | 動きの途中（おおむね中間）[TS-004] | トレンド持続の目安。連続は過熱の兆し[TS-025] |
| エグゾースション（消耗） | 動きの終盤 | 出来高急増、早期に埋まりやすい[TS-025] |
| アイランド・リバーサル | 消耗窓と逆向きのブレイクアウェイ窓に挟まれた島[TS-004] | 反転の強い形とされる（通説） |

- 呼称は資料で揺れる（ランナウェイ＝測定窓等）。種別は窓埋めの有無が分かる後にしか確定しないため、リアルタイム分類は困難。測定の慣行（⚠M）：起点から窓までの値幅を窓から同方向に投影する。
- 窓埋めの実証: 米国株1928〜2018年は窓日に窓の方向へ推移し、「窓は埋まる」説に否定的[TS-019]。株式・為替・商品2000〜2015年は為替を除き効率性と矛盾しない[TS-018]。トレンド除去後の検定では米中株で窓埋め現象が存在し得るとの報告もある[TS-020]。結論は混在。検証では「埋め」の定義（前日終値到達／半値／同日／N日以内）を固定し、窓の大きさ（ATR比）・方向・トレンド・出来高で層別する。
- 日本株: 値幅制限（ストップ高・安）や特別気配は窓の形成を変える。権利落ち日には配当相当分の機械的な窓が生じ得る（⚠M・要確認）。これらは情報ではないので分類から除くか調整する。寄付きは板寄せで、海外市場・先物・PTSの動きを反映する。制度は../02_japan/04_tse_market_rules_and_chart_effects.md。取引時間・呼値・制限値幅は変更され得る（確認日: 2026-11-09、要公式確認）。

## 7. ピボットポイント
フロア・トレーダーが前日の高値H・安値L・終値Cから当日の支持抵抗を決めた手法で、水準は当日中変えない[TS-010]。

```
Classic   : P = (H+L+C)/3
            R1 = 2P-L        S1 = 2P-H
            R2 = P+(H-L)     S2 = P-(H-L)
            R3 = H+2(P-L)    S3 = L-2(H-P)          # R3/S3は⚠M・要照合
Fibonacci : P はClassicと同じ。R1 = P+0.382*(H-L)  R2 = P+0.618*(H-L)  R3 = P+1.000*(H-L)（Sは符号反転）
Woodie    : P = (H+L+2C)/4。R1 = 2P-L  S1 = 2P-H  R2 = P+(H-L)  S2 = P-(H-L)
Camarilla : R = H-L。H4 = C+R*1.1/2  L4 = C-R*1.1/2
            H3 = C+R*1.1/4  H2 = C+R*1.1/6  H1 = C+R*1.1/12（L側は対称。H1〜H3の係数は⚠M）
```
- 出典: Classic/Fibonacci[TS-010]、Woodie[TS-012]、Camarilla H4/L4[TS-011]。Woodieには前日終値の代わりに当日始値を使う版があるなど入力に異説がある[TS-012]。Camarilla H5/L5の定義は実装で異なる。
- 計算例（架空値 H=1050, L=1000, C=1030）: Classic P=1026.67, R1=1053.33, S1=1003.33, R2=1076.67, S2=976.67／Fibonacci R1=1045.77, R2=1057.57, R3=1076.67／Woodie P=1027.50, R1=1055.00, S1=1005.00／Camarilla H4=1057.50, L4=1002.50。
- 参照期間の慣行: 1〜15分足は前日、30〜120分足は前週、日足は前月のデータで算出する[TS-010]。プラットフォームにより異なる。Pより上なら強気寄りと読むのが通例[TS-010]。
- 日本株: 前日の高安終値の定義（通常取引のみか、PTS・先物夜間を含むか）を固定する。株式分割後は前期間データも調整する。
- 限界: ピボット式そのものを独立に検証した査読研究は本調査では未確認。為替で業者提供の水準が日中のトレンド中断を予測した報告[TS-032]は、ピボット式の有効性を示すものではない。方式が重なる水準を「強い」とみなすのは通説で未検証。

## 8. 時間軸と調整後価格
- 週足・月足は日足の集約：始値＝期間初日の始値、高値＝最大、安値＝最小、終値＝最終営業日の終値、出来高＝合計。祝日週は4営業日になる。上位足でトレンドと主要水準を決め下位足でタイミングを取る（→10_alt_charts_relative_strength_mtf.md）。上位足は確定済みの最新足だけを使う（未完成足の参照はルックアヘッド）。

| 用途 | 推奨 | 理由 |
|---|---|---|
| 移動平均・ATR・リターン・トレンドライン | 株式分割・併合を遡及調整した系列 | 水準の連続性 |
| キリ番・窓・権利落ち日の分析 | 未調整（実取引価格）を併用 | 調整するとキリ番が崩れ、機械的な窓が見えない |
| 配当の調整 | 提供者により異なる（要確認） | 総合収益調整の有無で過去価格が変わる |

## 関連文書
- 02_chart_patterns.md／03_candlesticks.md／04_waves_fibonacci_wyckoff_gann.md／05_practitioner_frameworks.md／06_moving_averages.md／08_volatility_and_trend_strength.md／10_alt_charts_relative_strength_mtf.md
- ../02_japan/04_tse_market_rules_and_chart_effects.md、../03_evidence/01_academic_literature.md、../03_evidence/02_methodology_behavioral_japan_ml.md、../05_tools_data_code/02_data_sources.md

## この文書の限界
- 外部ページは開けず、検索結果の要約・書誌・論文レコード（要旨）で確認した。Edwards & Magee、Murphy、Rhea、各社資料の本文は未読。
- 日本語の証券会社資料はダウ理論（大和証券）とトレンドライン（OANDA証券）のみ確認。窓・ピボット・支持抵抗の日本語資料は検索回数の上限で確認できていない。
- ブレイクアウトの閾値（ATR倍率・出来高倍率・リテスト許容）はコミュニティの設定例で検証されていない。本文の設計例は初期値として扱うこと。
- Camarilla H1〜H3の係数、Classic R3/S3、Rheaのライン、フラクタルN=2、方向転換は記憶に基づく（⚠M）。
- 権利落ち日の窓、前日データの定義、取引時間・呼値は東証制度に関わり要公式確認（確認日: 2026-11-09）。

## 出典

> 検証タグ: ✅S=検索結果・論文レコード等で書誌と要点を確認（本文は未読）／⚠M=記憶のみ／❓=要確認。URLは検索結果に現れたものだけを記載し、無いものは「—」とした。

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TS-001 | 金融・証券用語解説「ダウ理論」 | 大和証券 | — | https://www.daiwa.jp/glossary/YST2245.html | ✅S | 6法則・期間区分の記述を確認 |
| TS-003 | The Dow Theory: William Peter Hamilton's Track Record Reconsidered | Brown, Goetzmann, Kumar／Journal of Finance | 1998 | — | ✅S | DOI 10.1111/0022-1082.00054 |
| TS-004 | Technical Analysis of Stock Trends | Edwards, Magee（のちBassetti改訂） | 1948（初版） | — | ✅S | 書誌・目次・章要旨のみ確認 |
| TS-005 | Dow Theory for the 21st Century（第1章） | Schannep／Wiley | 2008 | — | ✅S | DOI 10.1002/9780470428412 |
| TS-006 | ChartSchool: Trend Lines | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/trend-lines | ✅S | 2点で確定・3点目で検証の記述 |
| TS-007 | ChartSchool: Support & Resistance | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/support-and-resistance | ✅S | 役割転換の記述 |
| TS-008 | Log versus Arithmetic Scaling（Mailbag） | StockCharts | 2010 | https://stockcharts.com:443/articles/mailbag/2010/04/log-versus-arithmetic-scaling.html | ✅S | 対数／算術の比較 |
| TS-009 | Logarithmic Scaling（Knowledge Base） | Optuma | — | https://www.optuma.com/kb/optuma/general-usage-and-interface/interface/logarithmic-scaling | ✅S | 対数軸とラインの関係 |
| TS-010 | ChartSchool: Pivot Points | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/pivot-points | ✅S | 標準式・Fibonacci倍率・参照期間 |
| TS-011 | Camarilla Pivot Points | NexusFi（コミュニティ記事） | — | https://nexusfi.com/a/indicators/camarilla-pivot-points | ✅S | H4/L4の式と計算例 |
| TS-012 | other pivot point calculation methods | BabyPips | — | https://www.babypips.com/learn/forex/other-pivot-point-calculation-methods | ✅S | Woodie等の式（個別ページ対応は未確認） |
| TS-013 | Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis | Osler／Journal of Finance | 2003 | — | ✅S | DOI 10.1111/1540-6261.00588 |
| TS-014 | Evidence and Behaviour of Support and Resistance Levels in Financial Time Series | Chung, Bellotti／arXiv | 2021 | — | ✅S | DOI 10.48550/arxiv.2101.07410（プレプリント） |
| TS-015 | Identifying and evaluating horizontal support and resistance levels: an empirical study on US stock markets | Zapranis, Tsinaslanidis／Applied Financial Economics | 2012 | — | ✅S | DOI 10.1080/09603107.2012.663469 |
| TS-016 | An empirical study of liquidity dynamics and resistance and support levels | Gomes, Waelbroeck／Quantitative Finance | 2010 | — | ✅S | DOI 10.1080/14697680902814258 |
| TS-017 | Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | Brock, Lakonishok, LeBaron／Journal of Finance | 1992 | — | ✅S | DOI 10.1111/j.1540-6261.1992.tb04681.x |
| TS-018 | Price gaps: Another market anomaly? | Caporale, Plastun／Investment Analysts Journal | 2017 | — | ✅S | DOI 10.1080/10293523.2017.1333563 |
| TS-019 | Price gap anomaly in the US stock market: The whole story | Plastun ほか／North American Journal of Economics and Finance | 2020 | — | ✅S | DOI 10.2139/ssrn.3461283 |
| TS-020 | Does Exist Gap-Filling Phenomenon in Stock Markets? | Liu ほか | 2021 | — | ✅S | DOI 10.1007/978-3-030-67318-5_13 |
| TS-021 | Zigzag Structure（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/zigzag-structure/ | ✅S | ベンダー解説 |
| TS-022 | ジグザグ指標の解説 | Angel One（証券会社教育ページ） | — | https://uatcdn.angelone.in/knowledge-center/online-share-trading/zig-zag-indicator | ✅S | 証券会社の教育ページ |
| TS-023 | Breakout Confirmation（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/breakout-confirmation/ | ✅S | ベンダー解説 |
| TS-024 | トレンドライン（用語解説） | OANDA証券 | — | https://www.oanda.jp/lab-education/technical_analysis/trend-line/ | ✅S | ライン・チャネルの引き方 |
| TS-025 | Gaps（テクニカル分析講座） | FYERS（証券会社教育ページ） | — | https://fyers.in/school-of-stocks/chapter/technical-analysis/gaps.html | ✅S | 各窓の出来高・窓埋めの記述 |
| TS-027 | Technical Analysis of the Financial Markets | Murphy, J. J. | 1999 | — | ⚠M | 古典（記憶） |
| TS-028 | What Do We Know About the Profitability of Technical Analysis | Park, Irwin／Journal of Economic Surveys | 2007 | — | ✅S | DOI 10.1111/j.1467-6419.2007.00519.x |
| TS-030 | Dow Theory（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/dow-theory.md | ✅S | 複数ページの総合要約。個別対応は未確認 |
| TS-032 | Support for Resistance: Technical Analysis and Intraday Exchange Rates | Osler／FRBNY Economic Policy Review | 2000 | — | ✅S | 原報の年は記憶。検索記録は2006-03-07 |
| TS-034 | False breakout / Breakout & Retest スクリプト一覧 | TradingViewコミュニティ | — | https://id.tradingview.com/scripts/falsebreakout/ | ✅S | スクリプトごとの設定例。個別対応は未確認 |
| TS-162 | The Rise and Fall of Technical Trading Rule Success | Taylor／J. Banking & Finance | 2014 | — | ✅S | DOI 10.1016/j.jbankfin.2013.12.004 |
| TS-171 | Is technical analysis profitable on US stocks with certain size, liquidity or industry characteristics? | Marshall, Sun, Young／Applied Financial Economics | 2009 | — | ✅S | DOI 10.1080/09603100802446591 |
