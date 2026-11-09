# 代替チャート・相対力・マルチタイムフレーム分析
> 要約: 平均足（Heikin-Ashi）、Renko、カギ足、ポイント・アンド・フィギュア（P&F）、スリーライン・ブレイク（新値足）の作図規則と、相対力（RS比・RRG・セクター・ローテーション）、マルチタイムフレーム分析、対数／算術チャート、指標の冗長性、パラメータ最適化の危険を扱う。
> 平均足のみ TA-Lib 0.8.3 と数値照合し、他の作図規則は小さな例で手順を検算しただけで、一次資料は未確認（⚠M）である。
> 最適化の危険は合成データの実験とデータスヌーピング／過剰適合の文献で示す。代替チャート自体の有効性を示す学術的証拠は乏しい。
> 最終更新: 2026-11-09

## 1. 平均足（Heikin-Ashi）
```
HA_Close_t = (O_t+H_t+L_t+C_t)/4
HA_Open_t  = (HA_Open_{t-1}+HA_Close_{t-1})/2          HA_Open_0=(O_0+C_0)/2 （TA-Lib 0.8.3、talib.HA、照合済み [TI-401]）
HA_High_t  = max(H_t, HA_Open_t, HA_Close_t)           HA_Low_t = min(L_t, HA_Open_t, HA_Close_t)
```
- 経路依存: HA_Open は再帰のため、初期値の影響は1本ごとに半減し（10本後に約0.1%）、起算日を変えても序盤の十数本以降はほぼ一致する。
- 読み方（実務上の慣行）: 陽線の連続、下ヒゲのない陽線は上昇の勢い、小さな実体や上下ヒゲの長いコマは転換の警戒。平均化のためローソク足よりノイズが少なく見える。
- 失敗パターン: HA_Close は平均値で実際の約定可能価格ではない（損切り・指値の基準にできない）。ギャップが消える。平均化による遅れがあり、転換の確認が遅い。有効性の学術的検証は今回の調査では確認できなかった（未確認）。
- 日本語の「平均足」はこの手法を指すのが通例だが、国内ツールで始値の初期値や更新式が異なるかは未確認。

## 2. Renko・カギ足・P&F・スリーライン・ブレイク（作図規則）
いずれも時間軸を捨て、価格変化のみで足を作る（⚠M：Nison『Beyond Candlesticks』（1994年）、Dorsey『Point and Figure Charting』[TI-422][TI-423]）。以下は小さな例（Renko: 100,105,112,121,118,108,99,98 でレンガ幅10 → 上昇2本・下降1本）で手順を検算した。
```
# Renko（終値基準、レンガ幅B）
上昇レンガ: 終値 >= 直近レンガの上端+B のたびに1本（複数本あり得る）。下降レンガは 終値 <= 下端-B
反転: 上昇レンガの後の下降レンガは 終値 <= 直近レンガの下端-B（上端から2B以上の下落）で出現し、新レンガは直近レンガの下端から下へ描く
# カギ足（反転幅R、終値基準）
上昇中: 終値が直近高値を更新すれば線を延長、終値 <= 直近高値-R で反転（横線を引き下降へ）。下降中は対称
太線（陽）: 上昇線が直前の肩（直前の戻り高値の反転点）を上回ったら。細線（陰）: 下降線が直前の腰を下回ったら
# P&F（ボックス幅b、転換枚数r＝3が標準）
X列（上昇）中: 高値 >= 最上位X+b なら必要な数のXを積む。そうでなく 安値 <= 最上位X-r*b なら右隣に新しいO列を作り、最上位Xの1ボックス下から安値まで並べる。O列中は対称
終値基準法は高値・安値の代わりに終値を使う（小例 10,11,12,13,12,11,10,9,10,11,12 / b=1 / r=3 → X(10-13), O(9-12), X(10-12)）
# スリーライン・ブレイク（新値足、本数n=3）
上昇線: 終値 > 直前線の高値 で新線。下降線: 終値 < 直前線の安値 で新線
反転: 直近n本の線の最安値を終値が割れたら下降線、最高値を超えたら上昇線。反転線は直前線の始値側から描く
```
| 手法 | パラメータの決め方 | 読み方（慣行） | 失敗パターン |
|---|---|---|---|
| Renko | 固定値、比率、ATR（作図開始時に固定する流儀と動的に変える流儀がある） | 同方向レンガの連続＝トレンド。反転は2B | 時間情報を失う。ATRを動的にすると過去の足が書き換わる（リペイント） |
| カギ足 | 反転幅Rは固定値、価格の％、ATR倍率など | 太線への転換＝強気、細線への転換＝弱気 | Rの恣意性。肩・腰の判定が実装依存 |
| P&F | ボックス幅（固定または価格帯別の伝統的スケール。表は資料により異なり未確認）、転換3枚 | ダブルトップ突破＝買い、ダブルボトム割れ＝売り、トリプル版、45度線の維持、水平／垂直カウントによる目標値（⚠M） | 高値安値法か終値法かで列が変わる。ボックス幅選択で結果が変わる |
| スリーライン・ブレイク | n=3（新値足は[../02_japan/03_other_japanese_methods.md](../02_japan/03_other_japanese_methods.md)） | 3本の逆行を超えたときのみ転換とみなす | 転換が遅い。レンジでは線が増減せず情報量が乏しい |
- 証拠: P&F については、先物の超高頻度データで事前定義の8ルールを検定し、検証期間に利益を確認したという研究がある（Anderson・Faff）[TI-402]。他の手法の学術的検証は今回の調査で確認できなかった（未確認）。

## 3. 相対力（Relative Strength）
「相対力」は3つの意味で使われ、混同しやすい。
| 用語 | 意味 |
|---|---|
| RSI（相対力指数） | 同一銘柄内の上げ幅と下げ幅の比。ベンチマークとは無関係（[07_oscillators_momentum.md](07_oscillators_momentum.md)） |
| RS比・RSライン・RRG | 銘柄（または業種）とベンチマークの価格比 |
| 学術の relative strength 戦略 | 過去の勝ち組を買うクロスセクションのモメンタム（Levy 1967、Jegadeesh・Titman 1993）[TI-403][TI-404] |
```
RS_t = P_t(asset) / P_t(bench)                 いずれも調整後終値。ベンチマークは TOPIX、日経平均、S&P 500 など
RS指数 = 100*RS_t/RS_{t0}                     RSラインの上昇＝ベンチマーク対比でアウトパフォーム
相対リターン(k) = RS_t/RS_{t-k} - 1 ≈ (P_t/P_{t-k})/(B_t/B_{t-k}) - 1       対数では ln(RS_t/RS_{t-k}) = 資産の対数収益率 - ベンチマークの対数収益率
```
- RRG（相対力ローテーション・グラフ、Julius de Kempenaer、⚠M [TI-425]）は、x軸にRS-Ratio（相対トレンド）、y軸にRS-Momentum（その変化率）を取り、両者を100中心に正規化して4象限に分ける。Leading（x>100,y>100）→ Weakening（x>100,y<100）→ Lagging（x<100,y<100）→ Improving（x<100,y>100）の時計回りの回転が典型とされる。JdK の RS-Ratio／RS-Momentum の正規化式は非公開であり、本調査では確認できなかった（未確認）。自作する場合は、例えば RS-Ratio の近似として RS/SMA(RS,n) を過去窓のz値で100中心に変換し、RS-Momentum はその変化率をさらにz値化する、といった筆者の設計案になる（公式式ではない）。
- セクター・ローテーションの証拠: 業種モメンタムは個別株モメンタムの大部分を説明する（Moskowitz・Grinblatt 1999）[TI-405]。業種ファンドの直近上位を買う戦略はS&P 500を上回ったが、リスクも高く、シャープレシオでは上回らなかった（O'Neal 2000）[TI-406]。セクター別の相対力モデル＋トレンドフォローが1920年代以降の米国業種データで買い持ちを上回ったとする報告（Faber 2010、プレプリント）[TI-407]。他方、景気循環に基づく伝統的なセクター・ローテーションには体系的な裏付けがなく、取引コストと景気判断の誤りで優位が消えるとの報告もある（Molchanov・Stangl 2023）[TI-408]。モメンタム研究の総説は [TI-409]。日本市場の業種ローテーションに関する検証は、本調査では確認できなかった（未確認）。
- 日本株: 業種指数（東証33業種、TOPIX-17シリーズなど）を使うのが一般的だが、指数の構成は入れ替わるため、バックテストでは当時の構成を使う（⚠M、要確認）。サイズ・流動性の偏りで業種相対力が特定の大型株に左右される場合がある。

## 4. マルチタイムフレーム分析（MTF）
- 原則: 上位足でバイアス（トレンド方向）を決め、下位足でタイミングを取る。Elder のトリプル・スクリーンは、第1の画面で週足のトレンド、第2の画面で日足のオシレーターによる逆行（押し・戻り）、第3の画面で日中の突破を使い、時間軸の比を約5倍とする（⚠M [TI-421]）。
- 先読み回避が最重要: 上位足の値は、その足が確定した後にのみ下位足へ反映する。例えば日足 t 時点で週足の終値を使うなら、直前に確定した週の値（`shift(1)` 相当）でなければならない。未確定の週足の途中値を「その週の終値」として使うと未来情報が混入する。
```
# pandas の例: 日足→週足（金曜アンカー）→日足へ戻す
w = d.resample('W-FRI').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
sig_w = f(w)                                  # 週足で指標を計算
sig_d = sig_w.shift(1).reindex(d.index, method='ffill')     # 直前に確定した週の値のみ日足に適用
```
- 換算: 13週≒65営業日、26週≒130営業日、1年≒52週≒約245〜252営業日。週足の移動平均（週末終値の平均）と、日足の65日移動平均（全営業日の平均）は別物である。
- 失敗パターン: 上位足のトレンド判定も遅れる。フィルタを重ねるほど自由度が増え過剰適合を招く。各時間軸の指標が同系統（第6節）なら独立な確認にならない。MTFの有効性を直接検証した文献は今回の調査では確認できなかった（未確認）。
- 日本株の足: 休場日を含む週は営業日が4日以下になり、前場・後場の昼休みをまたぐ分足の集約は取引時間の制度に依存する（[../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)）。

## 5. チャートの尺度（対数／算術）
- 算術軸は値幅（円）が等距離、対数軸は変化率（％）が等距離。対数軸上の距離は対数収益率に等しい。例: 100円→200円（+100%）と200円→300円（+50%）は、算術軸では同じ高さ（+100円）だが、対数軸では前者が約1.7倍長い（ln2＝0.693 対 ln1.5＝0.405）。
- 使い分けの目安: 長期チャート、価格が数倍に動く銘柄、成長株では対数軸が比率の比較に適する。値幅が小さい短期の売買では差が小さい。トレンドラインは、対数軸の直線が一定の成長率、算術軸の直線が一定の増分を表す。
- 指標: 多くのツールでは軸の設定は表示のみを変え、移動平均や RSI は素の価格で計算される（ツール依存、要確認）。対数価格に対して移動平均や回帰チャネルを計算すると、率の意味が一貫する。
- 日本株: 分割・併合・権利落ちの調整が前提（未調整だと尺度の議論以前に系列が不連続になる）。低位株は呼値の刻みの影響が大きく、小さな値動きでも率が大きく見える。

## 6. 指標を組み合わせるときの冗長性
TA-Lib 0.8.3 で厳密に成り立つ同一性と、合成データ（ランダムウォーク、1000本×150経路）での平均相関を示す。
| 関係 | 内容 |
|---|---|
| ウィリアムズ%R と Fast %K | %R(n) = Fast %K(n) - 100（誤差1e-14） |
| CMO と RSI | CMO(n) = 2*RSI(n) - 100（TA-Lib） |
| MACD本線・PPO・APO | MACD本線＝APO（EMA）で種値のみ異なる。PPO＝APO／EMA26×100。MACD>0 は EMA12>EMA26 と同値 [TI-420] |
| 相関（合成データ） | RSI14-ストキャスFast%K14: 0.86、ストキャス-CCI14: 0.93、ストキャス-%b(20): 0.95、RSI-%b: 0.89、RSI-ROC14: 0.88、RSI-MFI14: 0.69、MACDヒストグラム%-RSI: 0.64 |
- 実務上の指針: 指標を「トレンド（移動平均・ADX）」「モメンタム／位置（RSI・ストキャス・CCI・%R・%b）」「ボラティリティ（ATR・バンド幅）」「出来高」の系統に分け、同系統からは1つに絞る。同系統の複数一致は、独立な根拠が増えたことにならない。しきい値・期間の個数を数え、自由度を管理する。

## 7. パラメータ最適化の危険
合成データ実験（筆者計算）: 日次対数収益率が平均0・σ1.2%（優位性が存在しない）の10年（2500本）系列を200本作る。SMAの組（短期{5,10,15,20,25,30,40,50}×長期{30,50,75,100,125,150,175,200}、短期<長期の60組）を、ロング／ノーポジション、翌足約定、コスト0で、最初の4年（添字250〜1250）で最適化し、残り5年で検証した。
| 項目 | 結果 |
|---|---|
| 学習期間で最良の組のシャープレシオ（平均） | 0.45 |
| 学習期間で最良の組が0.5超となった経路の割合／1.0超の割合 | 45%／10% |
| 選んだ組の検証期間シャープレシオ（平均） | -0.04 |
| 固定の組（25,75）の学習／検証シャープレシオ（平均） | 0.00／-0.01 |
優位性ゼロでも、60通り試した最良値は「有望」に見える。試行回数が多いほど過剰適合の確率が上がる（Bailey ほか）[TI-416]。
- データスヌーピング補正: White の Reality Check は、同一データの繰り返し利用による偶然の当たりを検定する枠組み [TI-410]。Sullivan ほか (1999) は多数のルール集合に適用 [TI-411]。Hsu・Kuan (2005) は White の Reality Check と Hansen の SPA 検定で補正した結果、有意な収益性のあるルールは「若い」市場（NASDAQ 総合・Russell 2000）には存在するが「成熟した」市場（ダウ平均・S&P 500）には存在せず、前者の最良ルールは取引コスト考慮後も多くの学習・検証期間で買い持ちを上回り、複雑な戦略は単純ルールの利益を改善し得ると報告した [TI-412]。Hsu ほか (2010) は段階的 SPA 検定を提案し、成長・新興市場の指数とそのETFで技術的ルールに有意な予測力があるが、ETF導入後は証拠が弱まると報告した [TI-413]。補正の結果は市場の成熟度と期間で割れる。Bajgrowicz・Scaillet (2012) は誤発見率（FDR）を用いても事前の選択はできず、低コストで利益が消えると報告 [TI-414]。Allen・Karjalainen (1999) は遺伝的アルゴリズムでS&P 500のルールを学習し、1970〜1989の検証期間で取引コスト後に超過収益を得たが、他の期間では得られなかった [TI-418]。
- 過剰適合の確率とシャープレシオ: Bailey ほか (2016) は、バックテスト過剰適合の確率 PBO を推定する枠組み（CSCV）を提案 [TI-415]。Bailey・López de Prado (2014) の Deflated Sharpe Ratio は試行回数と非正規性を補正する [TI-417]。Wiecki ほか (2016) は Quantopian の888戦略の検証で、バックテストのシャープレシオが検証期間成績をほとんど予測しない（決定係数0.025未満）と報告した [TI-419]。
- 対策: 仮説を先に固定し、試した組み合わせ数を記録する。期間分割（学習・検証・最終テスト）やウォークフォワードで評価し、補正（Reality Check／FDR／Deflated Sharpe）を使う。パラメータ空間の「平らな高原」を選び、尖った最適値を避ける。売買コスト・スリッページ・売買単位を含める。複数市場・複数期間での頑健性を確かめる。検証手法の詳細は [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md)。

## 関連文書
- [06_moving_averages.md](06_moving_averages.md)、[07_oscillators_momentum.md](07_oscillators_momentum.md)、[08_volatility_and_trend_strength.md](08_volatility_and_trend_strength.md)、[09_volume_breadth_sentiment.md](09_volume_breadth_sentiment.md)
- [../02_japan/03_other_japanese_methods.md](../02_japan/03_other_japanese_methods.md)（新値足）、[../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md)、[05_practitioner_frameworks.md](05_practitioner_frameworks.md)

## この文書の限界
- この文書の作成時点で、共有のWeb検索回数の上限に達しており、平均足・Renko・カギ足・P&F・新値足・RRG・MTF・対数チャートについてウェブ上の一次資料・解説を確認できていない。作図規則は筆者の知識（⚠M）を小さな例で検算したもの（平均足のみTA-Libで照合）で、実装によって細部（P&Fのボックス幅表、カギ足の反転判定、新値足の本数）が異なり得る。
- RRG の式、Elder のトリプル・スクリーンの詳細、国内ツールの平均足の定義は未確認。
- 学術文献は要旨レベルの確認で、標本・手法の精査はしていない。日本市場での検証は未確認。
- 最適化実験は合成データ（正規収益率）上の単純なロング／ノーポジション戦略で、実市場の値ではない。
- 平均足の照合は TA-Lib 0.8.3（PyPI、2026-10-28公開）での確認であり、他の版・他実装では異なり得る（確認日: 2026-11-09、要版数確認）。

## 出典
| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TI-401 | TA-Lib（PyPI JSON） | PyPI | 2026 | https://pypi.org/pypi/TA-Lib/json | ✅S | 0.8.3（2026-10-28公開）。平均足の数値照合は同版 |
| TI-402 | Point and Figure Charting: A Computational Methodology and Trading Rule Performance in the S&P 500 Futures Market | Anderson, Faff | 2006（記録）／DOIは2004年のIRFAを示す | https://consensus.app/papers/details/7a71bf2e1e9b5b42a01e7cddcf3404bc/ | ✅S | 要旨のみ確認。S&P 500先物の超高頻度データ |
| TI-403 | Relative Strength as a Criterion for Investment Selection | R. Levy（J. Finance） | 1967 | https://consensus.app/papers/details/c5ec427f6eb95738890b7db5548e8d9a/ | ✅S | 冒頭のみ確認 |
| TI-404 | Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency | Jegadeesh, Titman（J. Finance） | 1993 | https://consensus.app/papers/details/e8f30fa76b6554ceb902dd134c4aed1a/ | ✅S | 要旨のみ確認 |
| TI-405 | Do Industries Explain Momentum | Moskowitz, Grinblatt（J. Finance） | 1999 | https://consensus.app/papers/details/d037cdc93c4b5446924ff017d593b49d/ | ✅S | 要旨のみ確認 |
| TI-406 | Industry Momentum and Sector Mutual Funds | O'Neal（Financial Analysts Journal） | 2000 | https://consensus.app/papers/details/88aa95f9ac8b518fab56c472ef3825fc/ | ✅S | 要旨のみ確認 |
| TI-407 | Relative Strength Strategies for Investing | Faber（SSRN） | 2010 | https://consensus.app/papers/details/7495c238cabf58de938d3e0f3d1761f6/ | ✅S | プレプリント。要旨のみ確認 |
| TI-408 | The myth of business cycle sector rotation | Molchanov, Stangl（Int. J. Finance & Economics） | 2023 | https://consensus.app/papers/details/7db296bcb68a5411b465799750e7a884/ | ✅S | 要旨のみ確認 |
| TI-409 | Momentum: what do we know 30 years after Jegadeesh and Titman's seminal paper? | Wiest（Financial Markets and Portfolio Management） | 2022 | https://consensus.app/papers/details/5afae736165853b680de8abf95ebe1a1/ | ✅S | 総説。要旨のみ確認 |
| TI-410 | A Reality Check for Data Snooping | H. White（Econometrica） | 2000 | https://consensus.app/papers/details/f4c4bac11d4b5a55ab4f28e06a668038/ | ✅S | 要旨のみ確認 |
| TI-411 | Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | Sullivan, Timmermann, White（J. Finance） | 1999 | https://consensus.app/papers/details/d44e019194235c9e94e158ebd482f2a1/ | ✅S | 要旨のみ確認 |
| TI-412 | Reexamining the Profitability of Technical Analysis with Data Snooping Checks | Hsu, Kuan（J. Financial Econometrics） | 2005 | https://consensus.app/papers/details/cfdd70da7c2858a6a70b641eccce11d4/ | ✅S | 要旨のみ確認 |
| TI-413 | Testing the Predictive Ability of Technical Analysis Using a New Stepwise Test Without Data Snooping Bias | Hsu, Hsu, Kuan（J. Empirical Finance） | 2010 | https://consensus.app/papers/details/7923a12c2b515dd899d89f3d60634cc8/ | ✅S | 要旨のみ確認（プレプリント版の記録） |
| TI-414 | Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs | Bajgrowicz, Scaillet（J. Financial Economics） | 2012 | https://consensus.app/papers/details/132354490e9a5a0a9fecaa045a94b6b0/ | ✅S | 要旨のみ確認 |
| TI-415 | The probability of back-test over-fitting | Bailey, Borwein, López de Prado, Zhu | 2016 | https://consensus.app/papers/details/f5ef21e8509b544fba76ccc9aa2de55c/ | ✅S | プレプリント。要旨のみ確認 |
| TI-416 | Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance | Bailey, Borwein, López de Prado, Zhu | 2014 | https://consensus.app/papers/details/578104e71df057ee9a03edf926b2950c/ | ✅S | 要旨のみ確認 |
| TI-417 | The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality | Bailey, López de Prado（J. Portfolio Management） | 2014 | https://consensus.app/papers/details/378afd063fd15487a4fcb21af0850767/ | ✅S | 要旨のみ確認 |
| TI-418 | Using genetic algorithms to find technical trading rules | Allen, Karjalainen（J. Financial Economics） | 1999 | https://consensus.app/papers/details/c956bf1fb9a75a268fec3d58b0c2548a/ | ✅S | 要旨のみ確認 |
| TI-419 | All That Glitters Is Not Gold: Comparing Backtest and Out-of-Sample Performance on a Large Cohort of Trading Algorithms | Wiecki, Campbell ほか（J. Investing） | 2016 | https://consensus.app/papers/details/cbf1b88914f55668987babb345905af4/ | ✅S | 要旨のみ確認 |
| TI-420 | MACD (Moving Average Convergence/Divergence Oscillator) | StockCharts ChartSchool | — | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator.md | ✅S | 中心線越え＝EMA12とEMA26の交差 |
| TI-421 | Trading for a Living | Alexander Elder（Wiley） | 1993 | — | ⚠M | トリプル・スクリーンの出典（年は記憶による） |
| TI-422 | Beyond Candlesticks | Steve Nison（Wiley） | 1994 | — | ⚠M | カギ足・Renko・スリーライン・ブレイクの解説（年は記憶による） |
| TI-423 | Point and Figure Charting | Thomas J. Dorsey（Wiley） | — | — | ⚠M | 版により年が異なる。作図規則の解説書 |
| TI-425 | Relative Rotation Graphs（RRG） | Julius de Kempenaer（RRG Research） | — | — | ⚠M | 考案者・発表年は記憶による |
