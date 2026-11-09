# 一目均衡表（いちもくきんこうひょう, Ichimoku Kinkō Hyō）

> 要約: 一目均衡表は細田悟一（筆名・一目山人）が考案したとされる日本発のチャート体系で、転換線・基準線・先行スパン1/2・遅行スパンの5本と「雲」に、時間論・波動論・値幅観測論（水準論）を加えた理論である。5本線の式は高値と安値の中値で、証券会社資料の間で一致する。
> 一方、「本日を含めて26日」の数え方（シフトが25本か26本か）、三役の細部、時間論の数列、NT計算値の表現は資料間で食い違う。標準値（9,26,52）の由来は英語の二次資料にある週6日制説のみで、日本語の一次資料は未確認。
> 学術検証は少数で一貫した優位性は示されていない。コード化ではシフト本数と遅行スパンの先読みに注意が要る。
> 最終更新: 2026-11-09

## 1. 根拠と読み方

- 外部ページ本体は開けず、検索要約と論文の書誌・要旨のみで確認した。出典ID付きは検索で確認した記述、出典なしの解説は筆者の既存知識（⚠M相当）で未検証である。細田氏の原典（著書）は未確認。

## 2. 考案者と歴史

| 論点 | 資料の記述 | 扱い |
|---|---|---|
| 考案者 | 細田悟一、筆名「一目山人」。日英の資料で一致 [JP1-040][JP1-041] | 確定 |
| 経歴 | 1898年生まれ、1924年に都新聞（のち東京新聞）入社、商況部長とする二次資料がある。没年を1982年とする記述も1件あった [JP1-042][JP1-043][JP1-062]（記述と資料の対応は未特定） | ❓ 一次未確認 |
| 完成時期 | 戦前の1936年、都新聞商況部長として7年・延べ約2000人を投入して完成とする記事 [JP1-040]。英語版Wikipedia系は「1930年代後半に開発」[JP1-041] | 両説併存 |
| 書籍での公表 | 1968年とする英語記事の抄録 [JP1-042]、1969年とするポルトガル語解説 [JP1-062]。約30年の研究後、1960年代後半に公表とする記述もある | 1960年代末が有力だが未確定 |
| 組織 | 「経済変動総合研究所」との関係は検索で確認できず | 未確認 |
| 欧米への紹介 | Stocks & Commodities誌2000年10月号に紹介記事の抄録 [JP1-042]。書籍に Patel（2010年）[JP1-060] | 事実 |

1936年説と1960年代説は「完成」と「書籍公表」の区別が曖昧な資料が多く、引用時は両説を併記する。

## 3. 構成要素5本の式とシフト

```
転換線      = ( 本日を含む過去9日の最高値 + 最安値 ) / 2         … 当日に描く
基準線      = ( 本日を含む過去26日の最高値 + 最安値 ) / 2        … 当日に描く
先行スパン1 = ( 転換線 + 基準線 ) / 2                            … 本日を含め26日先に描く
先行スパン2 = ( 本日を含む過去52日の最高値 + 最安値 ) / 2        … 本日を含め26日先に描く
遅行スパン  = 本日の終値                                         … 本日を含め26日前に描く
```

- 式は楽天証券 [JP1-030] と野村證券 [JP1-031] で一致した。最高値・最安値は日中の高値・安値で、終値ではない。他社ページ（マネックス・松井・みんなのFX等）も検索結果に含まれたが、式の個別確認はしていない。
- 転換線・基準線は期間nのドンチャン・チャネルの中値と同一構造で、移動平均線ではなく半値（レンジ中央）であり、突発的な高安の影響を直接受ける。

### 3.1 「26日」の数え方とシフト本数（実装差）

「本日を含めて26日先」は、本日を1日目と数えると計算日から25本先になる。ソフトにより25本と26本が混在する。

| 実装 | 先行スパン／遅行スパン | 根拠 |
|---|---|---|
| 日本の定義（本日を含め26日先／前） | 計算日の25本先／25本前 | 楽天証券の説明 [JP1-030]。FXTF資料は「本来の定義は25本分」とする [JP1-044] |
| MT4／MT5標準 | 26本先／26本前（1本ずれ） | [JP1-044][JP1-045]。OANDAは表示位置を修正した独自版を提供 [JP1-046] |
| TradingViewのPineコード例 | offset＝displacement−1（既定26なら25本） | フォーラム内のコード断片 [JP1-048]。内蔵指標と同一か、公式仕様は未確認 |
| Python stockstats | シフト量を基準線窓（既定26）と同値と記述。出力は雲幅のみ | README [JP1-052] |

「当日を含んで」を反映していないソフトでは1日ずれる、との指摘もある [JP1-047]。国内証券会社の株式チャートの実装・既定値は個別確認していない（確認日: 2026-11-09、要公式確認）。自作と市販ツールの照合では、まずこの1本差を疑う。

## 4. 雲（Kumo）

- 定義: 先行スパン1と2に挟まれた帯 [JP1-030]。上限＝max(1,2)、下限＝min(1,2)、厚み＝絶対値(1−2)。
- 位置関係: 株価が雲の上なら上昇基調、下なら下降基調、雲の中は方向感に乏しい（様子見）と解説される。雲は支持・抵抗帯として扱う [JP1-061]。雲の中の扱いは既存知識。
- 好転／逆転（雲の向き）: 先行スパン1が上にあれば上昇相場の傾向、2が上にあれば下落相場の傾向 [JP1-061]。1が2を下から上へ抜けるのが雲の好転、逆が逆転とされる（呼称は既存知識）。
- 厚み: 厚いほど支持・抵抗が強く反発しやすく、薄いほど突破されやすいと解説される（見出し水準の確認）[JP1-051]。厚みは「転換線と基準線の中点」と「52日中値」の乖離で、トレンドが続くと拡大し、後半に縮む。
- ねじれ: 先行スパン1・2が交差して上下が入れ替わる点。未来の雲は事前に見えるため、薄くなる・ねじれる日を変化の予告とみる解説があるが、有効性の検証は確認できていない（定義は既存知識で、専用解説は検索で未確認）。

## 5. 基準線・転換線・遅行スパンの見方と三役

- 基準線: 過去26日の中心。上向きは上昇基調、横ばいは相場の中心が動かず方向感なし、下向きは下降基調。株価が基準線の上で推移すれば上昇しやすい状態 [JP1-037]。
- 転換線: 基準線よりローソク足に近く動く短期の中心 [JP1-037]。転換線が基準線を下から上に抜けるのが好転、逆が逆転。
- 遅行スパン: 当日の終値を26日前に置く線。26日前の株価を上抜ければ好転 [JP1-050]。

| 条件 | 三役好転 | 三役逆転 |
|---|---|---|
| ① | 転換線＞基準線（基準線が横ばい〜上向きを条件に加える実装あり [JP1-049]） | 転換線＜基準線（基準線が横ばい〜下向き） |
| ② | 遅行スパン＞26日前の株価 | 遅行スパン＜26日前の株価 |
| ③ | 株価＞雲 | 株価＜雲 |

- 3条件が同時に成立した状態を指す [JP1-049][JP1-050]。③の雲の上抜けが最後に揃うことが多い [JP1-050]。日次の好転・逆転銘柄ランキングは終値ベースで判定している [JP1-049]。
- 状態と事象の区別: 状態＝①②③がすべて真。事象＝真に転じた日。判定に使う「26日前」の足は、本日を1日目と数えるとt−25本目になる（§3.1）。

## 6. 時間論

| 項目 | 内容 |
|---|---|
| 基本数値 | 9・17・26。日足を前提とし、考案者は日足を使うべきとした。26を1期とし26本ごとにサイクルがあるとみる [JP1-032][JP1-034] |
| 複合数値 | 資料で列挙が異なる。マネックス記事は33・42・51・65・76・83…[JP1-034]、楽天証券FXヘルプは33・42・52・65・76・129・172・226・676 [JP1-032]。51と52が食い違い、誤記か異説かは未確認 |
| 対等数値 | 高値→高値、高値→安値、安値→高値、安値→安値の日数が先行する波と等しくなるという考え [JP1-034] |
| 変化日 | 基準となる天井・底から基本数値の日数が経った日。必ず転換するとは限らず、基調が加速する日にもなりうる [JP1-034]。最初の該当日に変化がなければ次の該当日を見る [JP1-032] |
| 導出 | 17＝9×2−1 [JP1-034]。26の導出は資料により表現が異なり、「9×3−2」とする要約は算術が25で合わない（9＋17とする説明もある、⚠M）。確定できない |
| 数え方 | 起点日を1日目と数える慣行（⚠M、出典では未確認） |

- 検証: 時間論（変化日）の有効性を検証した研究は今回確認できていない。
- 実装上の危険: 候補日は「複数のスイング点×複数の数値」で増える。直近5つの転換点に8個の数値を当てると、約76日の範囲で候補は約40個（1日あたり0.5個、日数比でおよそ4割）に達し得る（概算）。後付けで当たりやすいため、数値と転換点の選び方を事前に固定し、無作為な日付との反転率比較（並べ替え検定）で評価する。

## 7. 波動論と値幅観測論（水準論）

- 波動論: I波動＝一方向の単純な波、N波動＝上げ→押し→上げの3波（⚠M）。V・E・NT波動の形状判定条件は原典未確認で、計算値の名称としての式のみ確認した。
- 値幅観測論（水準論）: 波動の値幅から目標値を測る。N・E・V・NTの4種が代表 [JP1-037][JP1-039]。

起点A、第1波の頂点B、押し安値Cとして（上昇の場合、下降は符号反転）:

| 計算値 | 目標値 | 解説 |
|---|---|---|
| N計算値 | C＋(B−A) | 第1波と同じ値幅だけ第3波が上昇 [JP1-036][JP1-037] |
| E計算値 | B＋(B−A) | 第1波の2倍の値幅 [JP1-036][JP1-037] |
| V計算値 | B＋(B−C) | 押し（B→C）の2倍の値幅まで伸びる。押しが浅いと強いシグナルと解説 [JP1-037][JP1-038] |
| NT計算値 | C＋(C−A) | A→Cの値幅をCに加算 [JP1-037][JP1-038] |

- 資料差: 松井証券はNTを「第1波と第2波の差の分」と説明する [JP1-036]。(B−A)−(B−C)＝C−Aで代数的には一致するが、加算の起点（BかCか）は要確認。
- 数値例: A=1000、B=1200、C=1100 → N=1300、E=1400、V=1300、NT=1200。A<C<Bなら常に NT<N<E かつ V<E で、Eが最大の目標値になる（式からの導出）。
- 限界: 4つの目標値は互いに離れ、どれを採るかが恣意的になる。到達率を検証した研究は確認できていない。

## 8. パラメータ（9,26,52）の由来とバリエーション

| 項目 | 内容 |
|---|---|
| 標準 | 転換線9、基準線26、先行スパン2は52、シフト26。研究でも既定値として使われる [JP1-053]。日足・週足とも同値が一般的（時間論は日足前提）|
| 由来 | 当時は週6日制（土曜に立会）で、26は当時の標準的な営業月、9は1.5週、52は2か月に当たるとする英語の二次資料 [JP1-041]。日本語の一次資料では未確認。別の英語論文は「9＝日本の取引2週間、26＝1か月、52＝2か月」と記し、9の説明が食い違う [JP1-074] |
| 週5日換算案 | 7（または8）・22・44（1.5週・1か月・2か月）。ライブラリの使用例にも現れる [JP1-052]。標準設定ではなく一提案で、標準維持を支持する見解もある（英語の二次資料、出典の特定は未了）|

## 9. コード実装時の注意

```python
import pandas as pd

def ichimoku(df, tenkan=9, kijun=26, senkou=52, shift=25):
    """df: 昇順の営業日データ(high, low, close。分割・併合は調整済み)。
    shift=25 は『本日を含め26日先/前』(日本の定義)、26 は MT4 型。"""
    mid = lambda n: (df["high"].rolling(n).max() + df["low"].rolling(n).min()) / 2
    o = pd.DataFrame(index=df.index)
    o["tenkan"], o["kijun"] = mid(tenkan), mid(kijun)
    o["a_calc"] = (o["tenkan"] + o["kijun"]) / 2      # 計算日tの値。描画は t+shift
    o["b_calc"] = mid(senkou)
    o["a"], o["b"] = o["a_calc"].shift(shift), o["b_calc"].shift(shift)   # 当日に見える雲(先読みなし)
    o["cloud_top"] = o[["a", "b"]].max(axis=1, skipna=False)
    o["cloud_bot"] = o[["a", "b"]].min(axis=1, skipna=False)
    o["chikou_plot"] = df["close"].shift(-shift)     # 描画専用(未来参照)。シグナルには使わない
    return o

# 三役好転(先読みなし): (tenkan > kijun) & (close > close.shift(shift)) & (close > cloud_top)
```

- 先読み: `chikou_plot[t]` は `close[t+shift]` である。バックテスト・機械学習の特徴量に使うと未来を参照する。遅行スパン条件は `close[t] > close[t-shift]` と書く。
- 未来雲の描画: `a_calc`・`b_calc` を最終足から shift 本先に延ばす。日付軸は暦日でなく営業日（JPXの休場日を除く）で拡張するか、バー番号で描く。
- データ長: `b` が初めて有効になるのは senkou＋shift 本目（52＋25＝77本、シフト26なら78本）。直近上場（IPO）銘柄は77営業日が経つまで雲が出ない。判定の助走として150本以上を読み込む。
- 週足・月足: 日足から `high=max, low=min, close=last` で集約し、確定足のみで判定する（途中の足は値が変わる）。
- 価格: 分割・併合の調整後を用い、全期間で調整方式を統一する。売買停止日は足が欠けるため、期間の数え方（営業日基準）を確認する。
- 照合: 市販ツールとの差は、まずシフト本数（§3.1）、次に高値・安値でなく終値で計算していないか、で説明できる。TA-Libの機能一覧に一目均衡表は見当たらず、finta・technicalindicators（npm）・stockstatsに実装がある [JP1-052][JP1-063]。出力のシフト有無は実装ごとに確認する。

## 10. 日本と海外の使われ方の違い

- 日本の解説は、5本線・雲に加え、時間論・波動論・水準論を応用的活用法として一体で紹介する [JP1-039]。日足・週足で基準線の傾き、雲との位置、遅行スパンを総合して見るのが基本とされる（既存知識）。
- 海外では、雲・転換線と基準線のクロス・遅行スパンを機械的シグナルにして外国為替などで売買する紹介が多い（既存知識）。書籍にはEURUSDの2年間のバックテスト章を含むものがある [JP1-060]。標準実装は1本ずれ [JP1-044][JP1-045]、パラメータを7・22・44に変える提案もある [JP1-052]。
- 研究は中国・インドネシア・ベトナム・米国などが目立ち、日本株を対象にした検証は少ない（日米個別株の比較は未査読の草稿 [JP1-054]）。

## 11. エビデンス

要旨のみ確認（全文未読）。体系的整理は [学術的エビデンス](../03_evidence/01_academic_literature.md)。

- Deng ら（2020）[JP1-053]: 4つの株価指数（1995〜2018年）と4通貨ペア（2003〜2018年）。既定（9,26,52）では前半期間に収益戦略があったが、後半期間は一貫して価値を生まなかった。パラメータ探索では株価指数に有望な設定があり、為替にはなかった（事後最適化は過剰適合の恐れが大きい）。
- Lim ら（2015、未査読）[JP1-054]: 日米の個別株（2005〜2014年）。雲をモメンタム・ブレイクアウト型とみなし、収益分布は正に歪み左裾が小さいと提案。日米比較の結論は要旨に明示なし。
- Lutey・Rayome（2022）[JP1-074]: 米国の次月リターン予測で一目均衡表が既知の指標を上回るとし、日本を含む海外4市場への拡張では移動平均線とモメンタムが有効だったと記す（海外での一目均衡表の成績は要旨に明示なし）。別の論文 [JP1-075] は米国株（1967〜2019年）で、雲の幅が前日の中央値を下回る局面のショート側シグナルに予測力があり、ファクター調整後も残ると報告。
- 単一市場の研究: ベトナム株ではコロナ禍の期間に取引ごとの収益が約8〜9%向上 [JP1-056]、米エネルギー株では銘柄間の差が大きくシグナルの多くがトレンド強化局面の外で発生 [JP1-057]。
- 背景: Park・Irwin（2007）は、技術的売買ルールの近代的研究95件の内訳を肯定56・否定20・混合19とし、データスヌーピングやコスト推定の問題が残ると整理した [JP1-059]。
- 結論: 市場・期間・パラメータへの依存が強く、一貫した優位性の証拠は弱い。

## 12. 限界・失敗パターン

- レンジ相場: 転換線・基準線が絡み合い、雲が薄く頻繁にねじれ、三役の点灯・消灯を繰り返してだまし（whipsaw）が増える。基準線が横ばいの間は信頼度が低い。
- 雲の中の動き: 方向感がなく、雲の上限・下限を行き来する。突破を確認する前の先回りは失敗しやすい。
- 遅れ: 三役好転の時点で既に大きく上昇しており、損切り幅（雲の下限など）が大きく、リスクリワードが悪化しやすい。
- 急変動: 雲は過去の情報に基づくため、決算ギャップで一気に突破・割り込みが起きても雲は追随しない。
- 時間論の後付け（§6）。日本株では決算・権利落ちのギャップ、値幅制限、昼休みの窓が高値・安値の質を変える。

## 関連文書

- [酒田五法・日本のローソク足用語](01_sakata_gohou.md)／[その他の日本の手法](03_other_japanese_methods.md)／[東証の制度とチャートへの影響](04_tse_market_rules_and_chart_effects.md)
- [移動平均線全般](../01_techniques/06_moving_averages.md)／[ボリンジャー・ATR・ADX等](../01_techniques/08_volatility_and_trend_strength.md)
- [学術的エビデンス](../03_evidence/01_academic_literature.md)／[検証手法の落とし穴](../03_evidence/02_methodology_behavioral_japan_ml.md)／[Pythonライブラリ](../05_tools_data_code/03_python_libraries.md)

## この文書の限界

- 外部ページ本体を開けず、検索要約・書誌記録のみで確認した。学術論文は要旨のみで全文未読。
- 細田氏の原典を未確認のため、時間論の数列と導出、波動の形状定義、三役の原義は二次資料に依拠する。
- 検索ツールの利用上限に達し、ねじれの解説、複合数値の導出、波動の形状定義、国内証券会社の株式チャートのシフト実装・既定値、「経済変動総合研究所」の確認が未了である（シフトは FXTF・MT系・Pineコード断片の範囲）。
- 日本株を対象に定義を固定して検証した査読論文は確認できていない。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| JP1-030 | (18) 一目均衡表（MarketSpeed オンラインヘルプ） | 楽天証券 | — | https://www.rakuten-sec.co.jp/MarketSpeed/onLineHelp/msman2_5_2_15.html | ✅S | 5本線の式、26日先の数え方 |
| JP1-031 | 一目均衡表（用語集） | 野村證券 | — | https://www.nomura.co.jp/terms/japan/i/itimoku.html | ✅S | 式の照合 |
| JP1-032 | 一目均衡表（ヘルプページ、タイトル未取得） | 楽天証券 | — | https://www.rakuten-sec.co.jp/ITS/fx_help/chart/new/ichimoku.html | ✅S | 基本数値・変化日 |
| JP1-034 | 時間論に関する記事（タイトル未取得） | マネックス証券（media） | — | https://media.monex.co.jp/articles/-/18351 | ✅S | 時間論 |
| JP1-036 | 一目均衡表（FX学習ページ、タイトル未取得） | 松井証券 | — | https://www.matsui.co.jp/fx/study/article/analysis/ichimoku/ | ✅S | NT計算値の表現が異なる |
| JP1-037 | 一目均衡表（用語解説） | OANDA Lab | — | https://www.oanda.jp/lab-education/dictionary/ichimoku | ✅S | 基準線の見方、N/E/V/NT |
| JP1-038 | FX N計算値の使い方 | CREX | — | https://crexgroup.com/ja/fx/basics/fx-n-value-calculation-usage/ | ✅S | V・NT計算値の解説 |
| JP1-039 | 第5回 一目均衡表 その応用的活用法-時間論、波動論、水準論 | auカブコム証券 | — | https://kabu.com/investment/guide/technical/05.html | ✅S | 水準論の位置づけ |
| JP1-040 | 細田悟一に触れた記事（タイトル未取得） | DIME | — | https://dime.jp/genre/1794798/ | ✅S | 1936年説。二次資料 |
| JP1-041 | Ichimoku Kinkō Hyō | Wikipedia（ミラー） | — | https://en.wikipedia-on-ipfs.org/wiki/Ichimoku_Kink%C5%8D_Hy%C5%8D | ✅S | 1930年代後半、26＝営業月説。二次資料 |
| JP1-042 | CLASSIC TECHNIQUES（Muranaka、抄録） | Technical Analysis of Stocks & Commodities | 2000 | https://traders.com/Documentation/FEEDbk_docs/2000/10/Abstracts_new/Muranaka/Muranaka.html | ✅S | 書籍公表1968年の記述 |
| JP1-043 | Technical Analysis（ブログ記事） | Swissquote | — | https://www.swissquote.com/en-ch/private/inspire/blog/technical-analysis/what-ichimoku-kinko-hyo-trading-method | ✅S | 経歴。記述との対応は未特定 |
| JP1-044 | FXTF Ichimoku（インジケーター資料） | FXトレード・フィナンシャル | — | https://www-hp.fxtrade.co.jp/pdf/indicator/FXTF_Ichimoku.pdf | ✅S | MT4は26本、本来25本 |
| JP1-045 | Titan Ichimoku | Titan FX | — | https://research.titanfx.com/ja/indicators/titan-ichimoku | ✅S | MT4/5の1本ずれ |
| JP1-046 | 一目均衡表の遅行線、先行スパンの表示位置を修正したインジケーター「OANDA_Ichimoku」 | OANDA Lab | — | https://www.oanda.jp/lab-education/blog_column/ichimoku/ | ✅S | 修正版 |
| JP1-047 | 一目均衡表に関する記事（タイトル未取得） | myforex | — | https://myforex.com/ja/news/myf23112204.html | ✅S | 当日を含まないソフトは1日ずれ |
| JP1-048 | help with ichimoku indicator alert（フォーラム） | NinjaTrader Forum | — | https://forum.ninjatrader.com/forum/ninjatrader-8/indicator-development/1090207-help-with-ichimoku-indicator-alert | ✅S | Pine断片。公式未確認 |
| JP1-049 | 本日の【均衡表｜3役好転/逆転】（日次記事） | 松井証券（ニュース） | — | https://finance.matsui.co.jp/news/626682/index | ✅S | 三役条件（基準線の傾き含む） |
| JP1-050 | 三役好転を扱う解説記事（タイトル未取得） | 幻冬舎ゴールドオンライン | — | https://gentosha-go.com/articles/-/76629?page=3 | ✅S | 3条件 |
| JP1-051 | 厚いほど高反発、薄ければ低反発? 一目均衡表の「雲」 | Financial Field | — | https://financial-field.com/assets/entry-148667 | ✅S | 見出し水準 |
| JP1-052 | stockstats 0.6.10（README） | PyPI | 2026 | https://pypi.org/pypi/stockstats/json | ✅S | 既定(9,26,52)、(7,22,44)の例、PSL既定12 |
| JP1-053 | The profitability of Ichimoku Kinkohyo based trading rules in stock markets and FX markets | Deng ほか／Int. J. Finance & Economics | 2020 | https://consensus.app/papers/details/d9bbe7afb93d5f84bdbca05a0090b10c/ | ✅S | DOI 10.1002/ijfe.2067 |
| JP1-054 | Do Ichimoku Cloud Charts Work and Do They Work Better in Japan | Lim, Yanyali, Savidge | 2015 | https://consensus.app/papers/details/932bdaaf8cc35e449b447d8ff8c92d71/ | ✅S | 未査読の草稿 |
| JP1-056 | Profitability of Ichimoku-Based Trading Rule in Vietnam Stock Market in the Context of the COVID-19 Outbreak | Che-Ngoc ほか／Computational Economics | 2022 | https://consensus.app/papers/details/d4ec22ec4d9d577998162fc0b51bd69d/ | ✅S | DOI 10.1007/s10614-022-10319-6 |
| JP1-057 | Can the leading US energy stock prices be predicted using the Ichimoku cloud? | Gurrib ほか／Int. J. Energy Econ. Policy | 2020 | https://consensus.app/papers/details/64c732a82f36595cb8494c0fc35c90c4/ | ✅S | DOI 10.32479/ijeep.10260 |
| JP1-059 | What Do We Know About the Profitability of Technical Analysis | Park, Irwin／J. Economic Surveys | 2007 | https://consensus.app/papers/details/a5d45906f24751c5997dbd1a0e40b481/ | ✅S | DOI 10.1111/j.1467-6419.2007.00519.x |
| JP1-060 | Trading with Ichimoku Clouds: The Essential Guide to Ichimoku Kinko Hyo Technical Analysis | M. Patel／Wiley | 2010 | https://consensus.app/papers/details/c275590e4d1857bd97053e19af223bad/ | ✅S | DOI 10.1002/9781119200208。目次のみ |
| JP1-061 | 一目均衡表の解説記事（タイトル未取得） | All About | — | https://allabout.co.jp/gm/gc/290865 | ✅S | 先行スパン1が上なら上昇傾向 |
| JP1-062 | Ichimoku Cloud（ポルトガル語解説） | The Right Trader | — | https://therighttrader.com/pt/learn/indicators/ichimoku-cloud | ✅S | 書籍1969年の記述 |
| JP1-063 | TA-Lib／finta／technicalindicators のパッケージ情報 | PyPI（TA-Lib, finta）／npm（technicalindicators） | 2021〜2026 | https://pypi.org/pypi/TA-Lib/json | ✅S | 機能一覧のみ確認。TA-Libに記載なし。同様に取得した他の2件: https://pypi.org/pypi/finta/json , https://registry.npmjs.org/technicalindicators |
| JP1-074 | Technical Indicator Risk Premium Forecasting in U.S. and Foreign Markets | Lutey, Rayome／J. Int. Business and Economics | 2022 | https://consensus.app/papers/details/9121fd8d4bef5949a174a1ebc32676c5/ | ✅S | DOI 10.18374/jibe-22-3.3。日本を含む海外市場。要旨のみ |
| JP1-075 | A Primer on the Ichimoku Cloud Indicator | 著者不明（記録に表示なし）／J. Marketing Development and Competitiveness | 2020 | https://consensus.app/papers/details/e943c5813ba05f3ab752ce04a1affacf/ | ✅S | DOI 10.33423/jmdc.v14i3.3058。要旨のみ |
