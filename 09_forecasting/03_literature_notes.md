# 予測手法の根拠文献（論文データベースでの確認結果）
> 要約: 確率予測の精度を上げる手法（ボラティリティ予測、ボラティリティで調整した過去分布、適正なスコア、予測の比較と多重検定、予測の結合、コンフォーマル予測、リターンの標本外予測、短期リバーサル・モメンタム・出来高・52週高値、日本のイベント後の値動き、為替との連動、類似局面、重なりのあるリターンの推論、過剰適合、銘柄のプール）について、論文データベースで 20 の問いを調べた結果である。出典は 107 件（すべて要旨レベルの確認で、全文は読んでいない）。設計への使い方は [01_method_review.md](01_method_review.md) にまとめた。
> 確認日: 2026-11-11／検索回数: 38 回（Consensus 36、WebSearch 2）。出典表の FM-001〜FM-080 が主要、FM-081〜FM-107 が補足（本文の「補足:」の箇条書きに対応）である。
> 記載は Consensus の記録（題名・著者・年・掲載誌・引用数・要旨）と WebSearch の結果だけに基づく。Consensus 由来の 106 行は、題名・著者・掲載誌・年・引用数・URL を、作業記録に残る検索結果と機械照合した（注記した欠落を除き不一致 0 件）。FM-001 だけは WebSearch の結果による。取りまとめ時に、全 107 行の URL と題名が検索結果に実在することを別のスクリプトで再照合し、設計の判断に使った 10 行は要旨の原文と読み比べた。
> 最終更新: 2026-11-11

読み方: 各問いの箇条書きは、要旨が述べていることだけを書いた。「筆者注」は要旨からの推論、「未確認」は確認できなかったことである。「候補リスト」とは、探索の手がかりとして事前に挙げた著者・年の一覧（記憶に基づく未検証のもの）を指す。記録で確認できた論文だけを出典表に入れ、確認できなかったものは 3 節に挙げた。
## 1. 質問ごとの確認結果

### Q1 レンジに基づくボラティリティ推定量（効率と夜間ギャップ）
- 高値・安値のレンジを使う分散推定は、終値だけを使う推定より効率が高いとされる。原典は、高値・安値のレンジによる方法（効率の倍率は WebSearch の要約にあるだけで、照合していない）、四本値と出来高を使う推定量、ドリフトによらず不偏な推定量である [FM-001][FM-002][FM-003]
- 複数期間の四本値を使う推定量は、ドリフトに依存せず、寄り付きの飛び（夜間ギャップ）にも整合的で、同様の性質を持つ推定量の中で分散が最小とされる [FM-004]
- 4種の推定量を比べた研究では、価格が連続の幾何ブラウン運動なら全て良好だが、寄り付きの飛びや大きなドリフトがあると推定量の間に有意な差が出た。S&P 500 では、レンジ推定は日次の積分分散にかなり近かった [FM-007]
- レンジに基づく代理変数は効率が高く、近似的に正規で、マイクロストラクチャ雑音に頑健とされる。ただしレンジ型も雑音を含む推定値であり、後続の計算でそのことが忘れられがちだと注意されている [FM-005][FM-006]
- 補足: ドイツの個別株25銘柄では、日次レンジ型は古典的な推定量より大幅に優れる一方、離散取引のため強い下方バイアスがあった [FM-081]
- 筆者注: 夜間ギャップの大きい日本の個別株では、日中の高値・安値だけを使う推定量は1日全体の分散を過小に見積もりやすい。寄り付きの飛びを扱う推定量を使うか、夜間リターンの二乗を別に足す形が候補になる。これは要旨からの推論であり、日本株での検証は確認していない。
- 未確認: 日本の個別株でのレンジ推定量のバイアスの大きさ。各推定量の相対効率の数値（確認した要旨には数値がない）。

### Q2 ボラティリティ予測モデル（1日〜3か月先）
- HAR-RV は、異なる期間で実現したボラティリティ成分を足し合わせる単純な自己回帰型のモデルで、長期記憶などの特徴を再現し、予測成績が良いと報告された [FM-008]
- 日次データだけを使う場合について、対数レンジを使う HAR は、実現ボラティリティを使う HAR に近い質の予測になることが多い。推定法・変換・予測方式の簡単な改良が、標準の HAR や HARQ を上回った（3株価指数・16年）。HAR の3成分は、OLS の重みではなく単純平均で結合するほうが精度が高いという報告もある [FM-011][FM-013]
- 1,455銘柄の比較では、推定窓と再推定頻度を整えた HAR を機械学習は上回れなかった。10か国13指数では、日次の予測は HAR、月次はリスクプレミアム補正つきのインプライド・ボラティリティが最良で、GARCH はほぼ全ての場合で劣った [FM-012][FM-015]
- 「GARCH(1,1) は破りにくい」という結果は条件つきである。330モデルの比較では、為替では GARCH(1,1) を上回る証拠がなかったが、IBM 株ではレバレッジ効果を扱うモデルに明確に劣った。93論文のサーベイは、ヒストリカル系の時系列モデルとオプションのインプライドの予測結果を比較している [FM-009][FM-010]
- EWMA は、ボラティリティの変動が中程度の状況では使っても損失が小さく、実系列の多くがこれに当たるとされる。日経225を含む4指数では、実現ボラティリティを使うモデルが日次リターンだけを使うモデルを上回った。為替では、対数実現ボラティリティの予測と標準化リターンの正規性を組み合わせると、較正のよい密度予測になった [FM-014][FM-017][FM-016]
- 補足: 93研究の比較は、インプライドが時系列モデルより正確で、時系列モデルの間に明確な勝者はないとまとめる。EWMA の最適な減衰係数は予測期間で変わる（1か月先は RiskMetrics の提案と整合し、短い期間ほど短期記憶が重要）。著者名が記録にない比較研究では、GARCH(1,1) が EWMA より概して良かった。1〜66日先（農産物）では、HAR の拡張は単純な HAR に勝てなかった。夜間リターンを HAR に加えると、英国以外の株価指数で予測が改善した [FM-084][FM-083][FM-082][FM-085][FM-086]
- 筆者注: 日次の四本値だけを使う設計では、(a) レンジ型の日次分散を HAR の入力にする、(b) EWMA を基準モデルに置く、(c) 両者を等加重で結合する、の3つが要旨と整合する。EWMA と GARCH の優劣は、確認した要旨の間でも一致していない（補足を参照）。
- 未確認: RiskMetrics の技術文書そのもの（減衰係数の標準値）。日本の個別株を対象にした1週間〜3か月先の比較。3か月先の個別株の結果（66日先を扱うのは農産物の研究だけである）。

### Q3 雑音のある代理変数によるボラティリティ予測の評価
- 不偏だが雑音のある代理変数（二乗リターン、日中レンジ、実現ボラティリティ）で予測を比べると、広く使われる損失関数では順位が歪むことがある。雑音があっても順位が保たれる損失関数の必要十分条件が導かれている [FM-018]
- 二乗リターンを条件付き分散の代わりに使うと、劣るモデルが「最良」に選ばれる確率が、標本が増えるにつれて1に近づくことがある。標本外の評価に実現分散を使う論拠とされる [FM-019]
- 批判として、代理変数に頑健な損失関数が二つあっても順位が一致するとは限らず、正反対にもなりうるという指摘があり、尤度に基づく損失関数が提案されている [FM-020]
- 筆者注: QLIKE と平均二乗誤差は、ボラティリティ予測の評価指標として複数の要旨で使われている（例: [FM-012]）。検索結果には両者を「頑健な損失関数」と呼ぶ要旨もあったが、出典表には入れていない。頑健性の条件を導いた原典の要旨は、QLIKE の名を挙げていない。評価には QLIKE と平均二乗誤差の両方を事前に指定し、代理変数にはレンジ型の分散を使うのが無難である。
- 未確認: QLIKE の定義式と、それが「頑健な損失関数」の族に含まれることの原文での確認。

### Q4 フィルター付きヒストリカル・シミュレーション（FHS）と区間・VaR のバックテスト
- 過去のリターンを、当時のボラティリティと現在のボラティリティの差で調整してからヒストリカル・シミュレーションに使う方法は、GARCH でも EWMA でも使え、12通貨と5株価指数の9年の日次データで、調整しない方法より大幅に改善した。記録に著者名はないが、題名は Journal of Risk 1998年秋号の論文である [FM-021]
- FHS は、過去と現在のボラティリティの変化を織り込み、将来の価格変化の統計的性質についての仮定を最小限にする方法と説明され、3種のポートフォリオで2年間検証された。動的分散モデルで濾過したイノベーションを使って将来リターンを模擬すれば、複数の保有期間の VaR や期待ショートフォールを、現在の市況に条件づけて計算できる [FM-022][FM-023]
- 密度予測として比べた研究（15方式・21年超）では、GARCH に基づく GJR-FHS が、密度の全範囲で最も整合的な予測を与えた [FM-024]
- バックテストでは、無条件のカバレッジ（超過の回数）だけでなく、条件付きの評価が必要とされ、その枠組みが提案されている。裾の確率が小さいほど正確さの検証は格段に難しく、極めてまれな事象ではほぼ不可能である [FM-026][FM-025]
- 区間・密度予測の既存の検定は、通常の標本数では検出力が低い。予測分布の全体を使う検定なら、標本数が100程度でも検出力があるとされる [FM-027]
- 補足: Topix を含む指数の1日 VaR では、フィルター付きブートストラップが全指数で条件付きカバレッジを満たし、単純なヒストリカル法は棄却が多かった [FM-087]
- 筆者注: 1週間・1か月・3か月の予測では、重複しない標本が少ない（3か月なら1年に4個）。要旨が示す検出力の限界から、裾（1%・5%）の検証は長い期間ではほとんど力を持たない。長い期間では、分布全体を使う評価（PIT、CRPS）のほうが情報を使える。
- 未確認: 候補リストにある1999年の原論文は、記録としては確認できなかった（2000年の検証論文の要旨に引用がある）。標準化した残差が独立同分布でない場合の FHS の誤差。日本の個別株での FHS の検証。

### Q5 適正スコアリングルール・CRPS・較正と鋭さ・PIT
- 適正なスコアリングルールとは、予測者が自分の本当の予測分布を出すときに期待スコアが最大になるルールである。CRPS は予測の累積分布関数に適用でき、絶対誤差を一般化する。分位点予測と区間予測にも適正スコアがあり、区間スコアは幅と被覆の両方を扱う [FM-028]
- 確率予測の評価は「較正を条件に、予測分布の鋭さを最大化する」という枠組みで整理され、PIT ヒストグラム、周辺較正図、鋭さの図、適正スコアが道具になる [FM-029]
- 密度予測を評価する枠組みは、ボラティリティが時変する資産リターンの密度予測に適用されている [FM-030]
- 複数期間先の密度予測では、PIT が系列相関を持つので評価が難しい。標準的な臨界値で使える、素モーメントに基づく検定が提案されている [FM-032]
- CRPS などの平均は、不確実性の大きい観測に重みが偏り、直観に反する順位になりうる。局所的に尺度不変な scaled CRPS が提案されている [FM-031]
- 補足: 鋭さを別の基準として立てる必要はないという批判がある。予測分布が標本で与えられる場合、CRPS は最小限の仮定で整合的に評価でき、経験分布関数が簡便な選択肢になる。対数スコアはより厳しい条件を要する [FM-088][FM-089]
- 筆者注: ボラティリティが高い時期ほど CRPS の値は大きくなるので、単純平均の CRPS は高ボラティリティ期の成績でほぼ決まる。期間別の比較か、尺度で割ったスコアの併記が要る。
- 未確認: 密度予測の評価の原典の要旨は PIT という語を使っていない（方法の中身は本文を読んでいない）。標本から CRPS を計算する式。

### Q6 予測の比較とデータ・スヌーピングの制御
- 二つの予測の精度に差がないという帰無仮説の検定は、損失関数が二次・対称でなくてもよく、予測誤差の系列相関も許す。その後、元の定式化の欠点を避ける修正が検討され、実務向けに一つの方法が推奨されている [FM-033][FM-034]
- 条件付き予測力の検定は、モデルではなく推定手続きを含む「予測方法」を評価し、入れ子・非入れ子のどちらのモデルも扱える [FM-035]
- 固定平滑化の漸近論を使えば、標本外の観測が少なくても検定のサイズが正しくなる。損失差の自己相関が強いほど検出力は下がり、ある閾値を超えると検出力がなくなって、正しい帰無仮説を誤って棄却する [FM-036][FM-037]
- 多数のモデルを比べるときは、最良のモデルを所定の確率で含む「モデル信頼集合」が使える。既存の資料集にある Reality Check、SPA、ステップワイズ検定も、探索全体を補正する方法である [FM-038][EV2-001][EV2-004][EV2-005]
- 偽発見率による制御は投資信託の成績評価に使われ（75%はアルファがゼロと推定）、テクニカル・ルールの再検証にも使われている。一方、信号対雑音比が低いと検出力が低く保守的になるという批判がある [FM-039][FM-040][EV2-006]
- 補足: 「この検定は予測の比較用であって、モデルの比較用ではない」という提案者自身の論評がある。複数の予測期間を同時に扱う検定も提案されている。検定の有意性でモデルを選ぶ慣行には、シミュレーションで不利な証拠が優勢だった。因子研究では t 値3.0超を求める提案がある [FM-090][FM-091][FM-092][EV2-007]
- 筆者注: 重複する1か月・3か月リターンの損失差は強い自己相関を持つので、この種の検定は重複のない標本で行うか、依存に頑健な方法で行う必要がある。条件付き平均の「傾き」を採用するかどうかを検定の有意性だけで決めることには、要旨の範囲では慎重であるべきである。
- 未確認: 偽発見率の原論文（1995年）は検索していない。モデル信頼集合の2011年の論文は、記録としては確認できなかった（確認したのは2003年の適用論文）。

### Q7 予測の結合
- 予測の結合は、事前に最良に見える単独のモデルより平均的に良い予測になることが多く、誤差の相関を無視した単純な結合が、最適重みを推定する精緻な方式をしばしば上回る [FM-041]
- 理由の一つは重みの推定誤差である。重みが推定値であることを考慮すると、結合予測には偏りが生じ、分散も増えるので、「最適」結合が等加重より良い保証はない [FM-042]
- 株式プレミアムの予測では、個別の予測回帰は標本外で安定して勝てないが、個別予測の結合は、過去平均に対して統計的・経済的に有意な利得を一貫して与えた [FM-043]
- 確率予測では、較正された相異なる確率予測の加重平均（線形プール）は、必ず較正を失い、鋭さを欠く。再較正つきの方法が提案されている [FM-044]
- 分位点の平均の性質は、線形プールと対数プールの中間にある。個別の予測に偏りがあるときは、総じて分位点の平均が望ましいとされる [FM-045]
- 補足: 確率の平均は分布が広がりすぎやすいという議論から分位点の平均が提案されたが、応用結果は割れており、どちらを使うかは実証の問題とされる [FM-093]
- 筆者注: 同じ銘柄・同じ期間について EWMA 型と HAR 型の二つの予測分布を結合するなら、方式（確率の平均か分位点の平均か）を事前に決め、適正スコアで比べるのがよい。重みは推定せず等加重から始めるのが、要旨と整合する。
- 未確認: 候補リストにある2013年の論文（確率と分位点の平均の比較）と2004年の論文（結合予測）は、記録として確認できなかった。

### Q8 時系列の依存・分布の変化の下でのコンフォーマル予測
- 通常のコンフォーマル予測は交換可能性を仮定する。適応的コンフォーマル推論は、分布が未知の形で時変するオンラインの設定で、交換可能性を仮定せずに、長期の被覆頻度を理論的に保証する [FM-046]
- 適応的コンフォーマル推論は、一般の依存を持つ時系列にも有効と論じられ、学習率の影響が分析され、パラメータ不要の集約法が提案されている [FM-047]
- 分布が時間とともに動く場合について、重みつき分位点で頑健性を持たせ、直近の観測を重く扱う手法も許す一般化がある [FM-049]
- 残差の時間的な依存を使って、将来の残差の条件付き分位点を適応的に再推定する方法は、漸近的に妥当な条件付き被覆と、区間幅の縮小を報告する [FM-048]
- 筆者注: 保証の多くは「長期の平均被覆」であり、特定の局面での被覆を保証するものではない。ボラティリティで標準化した残差に対して使えば、FHS の分位点を事後的に補正する層として位置づけられる。3か月先のように重複しない標本が少ない期間では、補正に使えるデータが少ない。
- 未確認: 候補リストにある2019年の論文（分位点回帰型）と2021年の論文（アンサンブル型）は、記録として確認できなかった。確認した4件のうち3件はプレプリント表示の記録である。株式リターンの区間予測での実証。

### Q9 株式リターンの標本外の予測可能性
- 標本内で予測力のある多くの経済変数は、標本外では過去平均に対して安定した利得を出せないとされる（他の要旨が引用する形で確認）。2024年の再検証では、2008年以降に提案された変数の3分の1超が標本内でも有意でなくなり、残りの半数は標本外で不振だった [FM-043][EV1-105][EV1-106]
- 係数の符号と予測値に弱い制約を課すと、多くの予測回帰が過去平均を上回る。ただし標本外の説明力は小さい [FM-050]
- テクニカル指標については、米国の株式リスクプレミアムを標本内外で予測するという報告が既存の資料集にある。短期と長期の移動平均の距離は、クロスセクションで将来リターンを予測し、年率アルファは約9%と報告された [EV1-101][FM-051]
- 機械学習は、株式プレミアム（単一の系列）の予測では、標本外で概して過去平均に勝てなかった。原因は、データの小ささと信号対雑音比の低さとされる [FM-052]
- 補足: 予測回帰の傾きを保守的な定数に固定する方法は、過去平均（傾きゼロ）より偏りが小さく分散は同じで、過去平均を上回ると主張する [FM-094]
- 筆者注: これらは主に米国の市場全体の月次リターンの結果であり、日本の個別株2銘柄の1週間〜3か月先にそのまま当てはまるとはいえない。要旨がそろって示すのは、(a) 基準は過去平均（またはゼロ）、(b) 推定した傾きは強く縮小・制約する、(c) 複数の弱い予測は結合する、の3点である。
- 未確認: 2008年の原論文は、今回は記録として出なかった（既存の EV1-105 は同題の「II」版）。移動平均の距離の、標本外・コスト後の頑健性と日本株での結果（確認した記録は2018年の SSRN 版）。

### Q10 方向（符号）の予測とボラティリティ
- 期待リターンがゼロでなければ、ボラティリティの依存（予測可能性）から符号の依存が生じる。これは、条件付き平均に依存がほとんどないという通常の結果と矛盾しない [FM-053]
- 符号の依存は、符号の自己相関や連の検定では見つけにくい。日次のような高頻度や年次のような低頻度ではなく、中間の期間のリターンで見つかりやすいとされる [FM-053]
- 先進国の株式市場で、条件付き分散に加えて歪度・尖度も使った方向予測が試みられ、ブライア・スコアなどの確率予測のスコアで「ある程度の成功」と報告された [FM-054]
- 筆者注: 標準化したリターンの分布の形が一定なら、上昇確率は「期待リターン÷ボラティリティ」で決まるので、ボラティリティが低いときほど50%から離れ、高いときほど50%に近づく。期待リターンの推定が不確かな個別株では、このずれは小さいはずである（大きさは確認していない）。
- 未確認: 1週間・1か月・3か月のどの期間で符号の予測可能性が最大になるか。日本株での検証。確認した2件は掲載前の版（2003年、2006年）の記録である。

### Q11 短期リバーサル（1週間〜1か月）と日本
- 米国では、ある週の勝者・敗者が翌週に反転し、買値・売値の差と取引コストを補正しても残るとされた。月次リターンの負の1次の系列相関も報告されている（後者は WebSearch の要約による）[FM-055][EV1-128]
- 短期リバーサル戦略のリターンは流動性供給の対価と解釈され、その期待リターンは VIX とともに大きく変動する。ファンダメンタルズで説明できないリターンほど、短期で反転しやすい [FM-056][FM-057]
- 日本では、東証の1975〜1997年に、1か月の有意な反転が支配的で、モメンタムは観察されなかった。逆張りは1か月〜3年の全ての期間で有利だった（特に1か月と2年以上）。週次でも、前週に下落した銘柄は翌週に反転し、前週の出来高が多い敗者株ほど反転が大きかった [FM-059][EV2-053][FM-060]
- 候補リストにある日本の短期逆張りの論文（1995年）は、記録の要旨欄が序論の文章であり、結果を確認できなかった [FM-058]
- 補足: 反転は非流動的な銘柄で大きく、逆張りの利益は想定される取引コストより小さいという結果がある。古典的な短期リバーサルは時間とともに弱まり、大半の地域で消えたという論評（著者名は記録にない）もある。短期の反転から長期のモメンタムへの移行は各国のデータで支持され、決算発表後は反転が弱まる。大型株に限れば取引コスト後も週30〜50bp が残るという反論は、既存の資料集にある [FM-095][FM-096][FM-097][EV1-100]
- 筆者注: 流動性の高い大型の2銘柄では、反転は小さいと見るのが要旨と整合する。日本の結果は1990年代までの標本であり、近年の検証は確認していない。逆張りの利益の一部は銘柄間のリード・ラグから生じるという結果 [EV1-089] があるので、単一銘柄の自己相関としては、ポートフォリオの結果より弱い可能性がある。
- 未確認: 2000年以降の日本の大型株での1週間・1か月リバーサルの大きさ。

### Q12 モメンタム・時系列モメンタム（個別株、日本）
- 個別株では、時系列型とクロスセクション型の戦略の成績差の大部分は、時系列型が取る時変のネット買い持ちで説明される [FM-061]
- 時系列モメンタムは、資産ごとの時系列回帰では証拠が乏しく、プール回帰の大きな t 値もブートストラップの臨界値に届かないという再検証がある。一方、米国の個別株では、1927〜2017年に強い時系列モメンタムが報告されている [EV1-036][EV1-041]
- 日本はクロスセクション・モメンタムが弱い例外とされ、市場状態の転換が多いことが原因の一つとされる（既存の資料集の記述）[EV1-092][EV1-094]
- 補足: 日本株では、時系列型・クロスセクション型のどちらのモメンタムも、市場が同じ状態を続けるときは大きく有意だが、状態が切り替わると損失になる [FM-098]
- 筆者注: 個別株の過去12か月リターンの符号を条件付き平均に使う根拠は、日本の大型株については弱い。使う場合は強く縮小し、標本外で確かめてからにする。
- 未確認: 候補リストにある2010年の論文（個人主義とモメンタム）は検索していない（既存の EV2-052 は同じ著者の2000年の別の論文）。日本の個別株の時系列モメンタムの標本外検証。

### Q13 出来高とその後のリターン
- 1日または1週間の出来高が異常に多い（少ない）銘柄は、その後の1か月に上昇（下落）しやすい。この高出来高リターン・プレミアムは41か国で検証され、先進国・新興国の双方で見られる [EV1-081][FM-062]
- 出来高とリターンの自己相関の関係は、売買の動機による。リスク分担の売買によるリターンは反転し、私的情報に基づく投機的な売買によるリターンは継続しやすい [FM-063]
- 東証の週次では、前週の出来高が多い敗者株ほど翌週の反転が大きい [FM-060]
- 補足: 出来高の標本外の予測力は弱い。米国での経済的利得は年率0.73%相当で、他の主要市場の多くでは予測力がなかった。ニューヨーク・東京・ロンドンの日次では、出来高はリターンをグレンジャーの意味で引き起こさず、ボラティリティとの間に正の相互作用があった [FM-099][FM-100]
- 筆者注: 出来高は、リターンの方向よりも、ボラティリティの予測変数として使うほうが要旨と整合する。
- 未確認: 高出来高プレミアムの日本単独の結果（41か国の内訳は要旨にない）。出来高とリターンのメタ分析は、出版バイアスと異質性の大きさを指摘する（既存の資料集の記述）[EV1-085]

### Q14 52週高値への近さ
- 52週高値への近さは、モメンタム利益の大部分を説明し、長期で反転しないとされる。20市場の検証では、18市場で利益が出て10市場で有意だったが、取引コストを考慮すると大半の市場で有意でなくなった [EV1-087][EV2-033]
- 市場指数では、モメンタム戦略のほうが52週高値戦略より有意に収益的で、52週高値効果はモメンタムほど頑健でないという批判がある [FM-064]
- 補足: 1か月リターンの短期リバーサルは、回転率と52週高値比が高い銘柄ほど弱く、両方が高い銘柄ではモメンタムに転じる [FM-101]
- 筆者注: 52週高値比は、単独の予測変数としてよりも、短期リバーサルの強さを変える条件変数として使う余地がある（高値に近く売買が活発なら反転を弱く見る）。ただし米国の結果である。
- 未確認: 日本単独の52週高値効果（20市場の内訳は要旨にない）。候補リストにある2008年の論文（国際株価指数）は、記録として確認できなかった。

### Q15 日本のイベント後ドリフト（決算、会社予想、自社株買い）
- 日本では経営者の利益予想が実質的に義務になっている。期初の予想は系統的に上方に偏り、期中に下方修正されるため、利益サプライズの大半は非負になる [FM-065]
- 決算発表後ドリフトは日本でも検出されているが、2002〜2020年の標本では縮小している。外国人持株比率が低い企業や、個人持株比率が高い企業では縮小していない [PB-229][FM-066]
- 自社株買いの発表では株価が上昇する。発表時の異常リターンは約5%で、市場は当初は過小反応する（特にバリュー株）。大きな株価下落のあとに買い付けが実行されやすい [FM-068][FM-067]
- 補足: 日本の自社株買い後の長期リターンについては、事前登録型の検証計画が公表されている（要旨に結果はない）[FM-102]
- 筆者注: 外国人持株比率が高い大型株では、決算発表後ドリフトによる傾きは小さいと見るのが要旨と整合する。期初の会社予想が上方に偏ることは、会社予想を基準にした変数（進捗率など）を使うときに、基準のずれとして扱う必要がある。
- 未確認: 会社予想の修正の発表後の株価ドリフトを直接測った日本の研究。2010年代以降の、自社株買い発表後1〜3か月の異常リターンの大きさ。

### Q16 日本の輸出企業・自動車メーカーの為替エクスポージャー
- 日本の多国籍企業171社の約25%で、1979〜1993年に有意な正の為替エクスポージャーが見られた。輸出比率が高いほど、また規模が大きいほど大きかった [FM-069]
- 東証の1,079社（1975〜1995年）では、同時点の株式リターンと予期しない円の変動に有意な関係があり、多国籍・高輸出の企業で大きかった。ラグつきの為替変化は有意でなく、為替の影響は遅れずに株価に織り込まれるとされる [FM-073]
- 米国・日本・ドイツの自動車企業には有意なエクスポージャーがあり、業界の競争環境の変化とともに時変する。輸出先での現地生産は、一定の水準を超えるとヘッジとして働く [FM-070]
- 為替の価格転嫁とエクスポージャーは関連し、日本の8つの輸出産業で推定されている。国際比較では、貿易の多い企業ほどエクスポージャーが小さい傾向があり、ヘッジのためと解釈されている [FM-071][FM-072]
- 補足: 東証上場企業では、海外売上への依存と米ドル建ての比率が高いほどエクスポージャーが大きく、ヘッジと円建ては小さくする。日本の自動車メーカーの円へのエクスポージャーは、2016年に過去12年で最大だった [FM-103][FM-104]
- 筆者注: 為替は「同時点」の説明変数であり、ラグつきの為替変化に予測力はないという結果なので、為替を条件付き平均の予測に使う根拠は弱い。使い道は、(a) 為替のボラティリティを株価のボラティリティ予測に加える、(b) 為替の前提を置いたシナリオの条件づけ、に限るのが整合的である。エクスポージャーは時変するので、係数は直近の窓で推定する。
- 未確認: トヨタ・住友電工の個別の係数。2020年代の推定。候補リストにある2006年の論文は記録として確認できなかった（確認したのは同じ著者の2001年の論文）。

### Q17 最近傍・アナログ（パターン照合）予測
- 為替の日次では、同時最近傍法が、誤差の尺度で酔歩や ARIMA をわずかに上回り、方向の予測ではより優れていた（欧州9通貨、1978〜1994年）[FM-074]
- 日経225（1986〜1997年）では、最近傍予測は誤差の尺度で酔歩に劣り、全期間では酔歩のほうが有意に良かった。方向の予測では酔歩を上回った [FM-075]
- カーネル回帰でチャート・パターンを定義する研究は、既存の資料集にある（記憶に基づく行と、同題の書籍章の記録。今回は検索していない）[EV1-120][EV1-056]
- 補足: 主要10通貨のノンパラメトリック予測は、非線形性を点予測の改善に使えるという見方に否定的だった。ボラティリティ（S&P 100 の実現分散）では、統計的にはモデル型の予測が優れるが、混乱期には最近傍予測のほうがリスク調整後の収益性が高かった [FM-105][FM-106]
- 筆者注: 要旨が示すのは、リターンの水準（点予測）では、最近傍法は酔歩に勝てないか、勝っても僅差ということである。使うなら、平均の予測ではなく、「似た局面」を条件にした分布（とくにボラティリティと裾）の再標本化に限るのが整合的である。
- 未確認: 最近傍法による確率分布の予測を適正スコアで評価した研究。近傍の数や距離の選び方による過剰適合の程度。

### Q18 重複する複数期間リターンの推論
- 持続的な説明変数を使う長期リターンの回帰では、予測可能性がないという帰無仮説の下でも、推定量が期間をまたいでほぼ完全に相関し、係数と R2 は期間にほぼ比例して大きくなる。これは実際のデータに見られるパターンそのものである [FM-076]
- 重複観測の長期回帰では、自己相関に頑健な標準誤差を使う代わりに、通常の t 統計量を予測期間の平方根で割れば、重複の影響を補正できる。そうすると、予測可能性は長期ほど強くはならない [FM-077]
- 複数期間先の密度予測では PIT も系列相関を持つので、較正の検定にも同じ注意が要る。予測比較の検定は、損失差の自己相関が強いと誤った棄却を起こす [FM-032][FM-037]
- 補足: 長期リターンの回帰は実質的に小標本であり、重複リターンを使う利点はわずかで、従来の補正は t 統計量を過大にしてきたという論評がある [FM-107]
- 筆者注: 3か月（約63営業日）の重複リターンを日次で評価する場合、有効な標本数は「日数÷63」に近い。10年でも約40個である。区間の被覆率や PIT の検定は、重複のない標本でも併せて報告するのが安全である。
- 未確認: 候補リストにある1980年・1987年・2011年の論文（重複観測の標準誤差）は、記録として確認できなかった。

### Q19 バックテストの過剰適合・パージ付き交差検証・事前登録
- 既存の資料集に、試行数と非正規性で補正するシャープ比、バックテスト過剰適合の確率（組合せ対称交差検証）、試行数に応じたヘアカット、多重検定の閾値がある。過剰適合の確率の論文は、単純なホールドアウトは投資のバックテストでは不正確になりやすいと述べる（今回も記録を確認）[EV2-010][EV2-011][EV2-008][EV2-009]
- 合成データでの比較では、組合せパージ交差検証が、K 分割・パージ K 分割・ウォークフォワードより過剰適合を抑え、ウォークフォワードは偽発見の防止に弱点があった（プレプリント）[FM-078]
- 時系列の交差検証の妥当性と、パージ・エンバーゴの整理は、既存の資料集にある（後者は記憶に基づく行）[EV2-027][EV2-071]
- 補足: 金融での事前登録の例として、日本の自社株買いアノマリーを対象にした事前登録型の報告がある [FM-102]
- 筆者注: 2銘柄・3期間という小さな問題では、試す仕様の数（特徴量×窓×縮小の強さ）がすぐに標本の情報量を超える。仕様・評価指標・採否の基準を先に書き、試行数を記録することが、どの検定よりも効く。
- 未確認: 候補リストにある2017年の論文（金融経済学の科学的展望）は、記録として確認できなかった。組合せパージ交差検証の優位は合成データの結果であり、実データでの検証は確認していない。

### Q20 多数の銘柄をプールすると予測は良くなるか
- 予測の文献では、全系列に一つの関数を当てる大域的手法は、局所的手法（系列ごとのモデル）より制約的ではない。局所法の複雑さは系列数とともに増えるが、大域法では一定で、大域的な線形モデルでも競争力のある精度が出るとされる [FM-079]
- ボラティリティでは、資産の間で実現ボラティリティのパターンがよく似ており、その類似性を使うパネル推定が、標本外のリスク予測を改善した（50超の資産、20年超）[FM-080]
- リターンでは、多数の銘柄をプールした機械学習が大きな経済的利得を報告し、支配的な予測信号はモメンタム・流動性・ボラティリティの変種である（今回、記録を確認）。日本株や国際市場の結果は、既存の資料集にある [EV2-075][EV2-069][EV2-070]
- 一方、単一の系列（株式プレミアム）では、機械学習は標本外で過去平均に勝てなかった。プール回帰の大きな t 値が、ブートストラップの臨界値に届かない例もある [FM-052][EV1-036]
- 筆者注: 要旨から言えるのは次の2点である。(a) ボラティリティ・モデルの係数（HAR の重みなど）は、多数の銘柄でプールして推定するほうが安定する見込みが高い。(b) リターンの条件付き平均は、プールすれば検出力は上がるが、得られるのは平均的な銘柄の関係であり、2銘柄に固有の関係ではない。プールした推定の標準誤差は、銘柄間の相関を考慮する必要がある。
- 未確認: 銘柄別の時系列回帰とパネル回帰を、個別株の確率予測の精度で直接比べた研究。

## 2. 既存の出典の再利用
| 質問 | 既存 ID | 文書 | 何を述べるか（1行） |
|---|---|---|---|
| Q6 | EV2-001 | 03_evidence/02_methodology_behavioral_japan_ml.md | Reality Check。候補全体の中の最良ルールが偶然を超えるかをブートストラップで検定する枠組み（資料集の記述。今回は記録を再確認していない） |
| Q6 | EV2-004（EV1-133 は同じ論文の ⚠M 行） | 同上 | SPA 検定。劣悪・無関係な候補に左右されにくい（資料集の記述） |
| Q6 | EV2-005 | 同上 | ステップワイズの多重検定（資料集の記述） |
| Q6 | EV2-006（EV1-013 と同じ論文） | 同上 | 偽発見率を使ったテクニカル・ルールの再検証。将来の優良ルールを事前に選べなかった（資料集の記述） |
| Q6・Q19 | EV2-007（EV1-132 は同じ論文の ⚠M 行） | 同上 | 新しい因子には t 値3.0超を求める提案。今回、検索 12 で NBER 版（2014年）の記録を確認 |
| Q6・Q19 | EV2-009 | 同上 | 200万超の戦略から求めた多重検定の閾値（時系列3.8、クロスセクション3.4）と、補正しない場合の誤棄却約45%。今回、検索 29 で再確認 |
| Q9 | EV1-105 | 03_evidence/01_academic_literature.md | 既存の予測変数は標本内外で不安定（資料集の記述。記録は同題の「II」版）。今回は他の要旨内の引用として確認 |
| Q9 | EV1-106 | 同上 | 2008年以降の29変数の再検証。3分の1超が標本内でも有意でなく、残りの半数は標本外で不振。今回、検索 16 で再確認 |
| Q9 | EV1-101 | 同上 | テクニカル指標が米国の株式リスクプレミアムを標本内外で予測（資料集の記述） |
| Q9 | EV1-039、EV1-053 | 同上 | 移動平均タイミングのクロスセクション収益、チャート画像からの予測（資料集の記述。今回は検索していない） |
| Q9・Q20 | EV2-075（⚠M） | 03_evidence/02_methodology_behavioral_japan_ml.md | 機械学習による資産価格。今回、検索 31 で記録を確認した（題名 Empirical Asset Pricing via Machine Learning、著者欄なし、年 2018、プレプリント表示、引用数 2399、URL https://consensus.app/papers/details/w:09f6a517-658f-436e-9d3d-afb83fd2ffff/ ）。要旨: 木とニューラルネットが最良で、支配的な予測信号はモメンタム・流動性・ボラティリティの変種 |
| Q11 | EV1-128（⚠M） | 03_evidence/01_academic_literature.md | 個別株の月次リターンの負の系列相関。今回、WebSearch で書誌を確認した（Journal of Finance 45(3): 881–898、DOI 10.2307/2328797、URL https://econpapers.repec.org/RePEc:bla:jfinan:v:45:y:1990:i:3:p:881-98 ）。要旨の原文は未確認 |
| Q11 | EV2-053 | 03_evidence/02_methodology_behavioral_japan_ml.md | 東証で逆張りが1か月〜3年の全期間で有利（特に1か月と2年以上）。利益は主にリード・ラグ効果。今回、検索 20 で再確認 |
| Q11 | EV1-100 | 03_evidence/01_academic_literature.md | 大型株に限れば、短期リバーサルは取引コスト後も週30〜50bp。今回、検索 19 で再確認 |
| Q11 | EV1-089 | 同上 | 逆張りの利益は過剰反応だけでなく銘柄間のリード・ラグからも生じる。今回、検索 20 で再確認 |
| Q12 | EV1-035 | 同上 | 58の先物で1〜12か月の時系列モメンタム（今回、検索 21 に出たのは要約誌の版の記録） |
| Q12・Q20 | EV1-036 | 同上 | 資産ごとの時系列回帰では証拠が乏しく、プール回帰の大きな t 値はブートストラップの臨界値に届かない。今回、検索 21 で再確認 |
| Q12 | EV1-041 | 同上 | 米国の個別株で1927〜2017年に強い時系列モメンタム。今回、検索 21 で再確認 |
| Q12 | EV1-092、EV1-093（=EV2-050）、EV1-094（=EV2-051）、EV1-095 | 同上 | 日本はモメンタムが弱い例外／価値と合わせて見れば整合的／市場状態の転換が多い／残差モメンタムは有効（資料集の記述） |
| Q12 | EV2-052 | 03_evidence/02_methodology_behavioral_japan_ml.md | 日本を除くアジアでモメンタムが高収益（同じ著者の2000年の論文。候補リストの2010年の論文ではない） |
| Q13 | EV1-081 | 03_evidence/01_academic_literature.md | 1日または1週間の出来高が異常に多い（少ない）銘柄は、翌月に上昇（下落）しやすい。今回、検索 22 で再確認 |
| Q13 | EV1-082、EV1-085 | 同上 | 過去の回転率がモメンタムの大きさと持続を予測（今回、検索 22 で再確認）／出来高とリターンのメタ分析（資料集の記述） |
| Q14 | EV1-087（=EV2-032） | 同上 | 52週高値への近さがモメンタム利益の大部分を説明し、長期で反転しない。今回、検索 23 で再確認（記録は著者欄なし） |
| Q14 | EV2-033 | 03_evidence/02_methodology_behavioral_japan_ml.md | 20市場中18で利益、10で有意。取引コスト後は大半の市場で有意でない。今回、検索 23 で再確認 |
| Q15 | PB-229 | 03_evidence/03_japanese_literature.md | 日本の決算発表後ドリフトは主要なファクター・モデルで説明できない（資料集の記述） |
| Q17 | EV1-120（⚠M）、EV1-056 | 03_evidence/01_academic_literature.md | カーネル回帰で技術パターンを定義する研究（記憶に基づく行と、同題の書籍章の記録。今回は検索していない） |
| Q19 | EV2-010、EV2-008 | 03_evidence/02_methodology_behavioral_japan_ml.md | 試行数と非正規性で補正するシャープ比／試行数に応じたヘアカット（資料集の記述） |
| Q19 | EV2-011 | 同上 | バックテスト過剰適合の確率と組合せ対称交差検証。単純なホールドアウトは不正確になりやすい。今回、検索 29 で再確認 |
| Q19 | EV2-012、EV2-013 | 同上 | バックテストから実運用への成績低下の実例（資料集の記述） |
| Q19 | EV2-027、EV2-071（⚠M） | 同上 | 時系列の交差検証の妥当性／パージ・エンバーゴ（資料集の記述。後者は記憶に基づく行） |
| Q19 | EV2-068 | 同上 | 探索的な仕様選択は、予測可能性がなくても有意なバックテストを生む。今回、検索 29 で再確認 |
| Q19 | PB-238、PB-240、PB-256 | 03_evidence/03_japanese_literature.md | バックテスト過剰適合を扱う日本語の文献（資料集の記述） |
| Q20 | EV2-069、EV2-070 | 03_evidence/02_methodology_behavioral_japan_ml.md | 日本株の深層学習によるクロスセクション予測／46市場の機械学習（資料集の記述） |

注: 今回の Consensus の URL は、末尾が `w:` と UUID（ハイフン区切り）の形で返った。既存の出典の URL（末尾が32桁の英数字）とは形が違う。同じ論文かどうかは題名と著者で判断した。再利用した ID は 45 個（かっこ内の別 ID は数えていない）。

注: 既存の出典の再利用は 03_evidence の文書を対象にした。その外に、同じ論文の行が 3 件ある。[FM-059] は TS-166（01_techniques/05_practitioner_frameworks.md）、[FM-066] は JP2-021（02_japan/04_tse_market_rules_and_chart_effects.md）、[FM-099] は TI-323（01_techniques/09_volume_breadth_sentiment.md）と同じ論文である。対象外なので FM の行を残した。資料集の全文書と題名の先頭で照合した結果であり、表記の違う重複は拾えていない可能性がある。

## 3. 見つからなかった文献
- Andersen・Bollerslev・Christoffersen・Diebold（2006、ボラティリティ予測のサーベイ）— 検索語: "forecasting volatility in financial markets: a review of historical volatility, EWMA RiskMetrics, GARCH and implied volatility forecasts"（1回）。出たのは別の論文 [FM-016]
- RiskMetrics の技術文書（EWMA の原典）— 検索語: 同上（1回）。EWMA を比べた研究は [FM-014][FM-082][FM-083]
- Barone-Adesi・Giannopoulos・Vosper（1999、原論文）— 検索語: "filtered historical simulation for value at risk: bootstrapping volatility-standardized returns, incorporating volatility updating into historical simulation"（1回）。同じ著者の2000年の検証論文 [FM-022] と、その要旨内の引用だけを確認
- Stock・Watson（2004）— 検索語: "forecast combination puzzle: simple average of forecasts is hard to beat compared with estimated optimal combination weights"（1回）
- Lichtendahl・Grushka-Cockayne・Winkler（2013）— 検索語: "combining probability forecasts: is it better to average probabilities or quantiles? linear opinion pool calibration and sharpness"（1回）。同じ論点は [FM-045][FM-093] で確認
- Romano・Patterson・Candès（2019）、Xu・Xie（2021）— 検索語: "adaptive conformal inference under distribution shift; conformal prediction intervals for time series with dependence"（1回）。後者は同じ著者の2022年の別の論文 [FM-048] を確認
- Welch・Goyal（2008）— 検索語: "out-of-sample equity premium prediction: predictors fail to beat the historical average; economically motivated restrictions and forecast combination improve out-of-sample forecasts"（1回）。他の要旨内の引用としてのみ確認。既存の [EV1-105][EV1-106] を再利用
- Chui・Titman・Wei（2010）— 検索していない（既存の [EV2-052] は同じ著者の2000年の別の論文）
- Du（2008）— 検索語: "52-week high momentum strategy: nearness to the 52-week high and subsequent stock returns in Japan and international markets"（1回）
- Dominguez・Tesar（2006）— 検索語: "Exchange rate exposure and competition: evidence from the automotive industry; firm-level exchange rate exposure across countries"（1回）。同じ著者の2001年の論文 [FM-072] を確認
- Lo・Mamaysky・Wang（2000）— 検索していない（既存の [EV1-120][EV1-056]）
- Hansen・Hodrick（1980）、Newey・West（1987）、Britten-Jones・Neuberger・Nolte（2011）— 検索語: "inference with overlapping observations in long-horizon return regressions: autocorrelation-consistent standard errors and the myth of long-horizon predictability"（1回）
- Harvey（2017）— 検索語: "backtest overfitting in investment strategies: purged and combinatorial cross-validation for financial time series; pre-registration and p-hacking in financial economics"（1回）
- Benjamini・Hochberg（1995、原論文）— 検索していない（金融への応用は [FM-039]）

Consensus では記録が出ず、WebSearch で確認したもの:
- Parkinson（1980）— Consensus の検索 1・2（2回）では記録なし。WebSearch（1回）で書誌と要約を確認 [FM-001]
- Jegadeesh（1990）— Consensus の検索 19・33（2回）では記録なし（検索 20 の別の論文の要旨に引用がある）。WebSearch（1回）で書誌を確認。既存の [EV1-128] を再利用

候補リストと記録の食い違い（年・版・論文）:
- 記録の年が候補リストより早いもの（オンライン公開や草稿の年とみられる）: [FM-006] 2011（候補リストは 2012）、[FM-008] 2008（2009）、[FM-018] 2010（2011）、[FM-019] 2005（2006）、[FM-043] 2009（2010）、[FM-050] 2007（2008）、[FM-057] 2013（2014）、[FM-059] 2003（2004）、[FM-067] 2003（2004）、[FM-061] 2017（2018）、[FM-062] 2011（2012）、[FM-076] 2005（2008）
- 記録の年が候補リストより遅いもの: [FM-033] 2002（候補リストは 1995）、[FM-069] 1999（1998。掲載誌の欄も不自然で、誤登録の可能性がある）
- 掲載前の版の記録だったもの: [FM-053]（2003年の NBER 版）、[FM-054]（2006年のプレプリント）、[FM-051]（2018年の SSRN 版。題名が違う）、[FM-063]（2000年。著者欄なし）
- 候補リストとは別の論文だったもの: [FM-048]（同じ著者の2022年の論文）、[FM-072]（同じ著者の2001年の論文）、[FM-022]（同じ著者の2000年の検証論文）、既存の [EV2-052]（同じ著者の2000年の論文）
- 著者名が記録にないもの: [FM-021][FM-063][FM-082][FM-096]

## 4. 検索の記録
| # | 検索語 | 主に対応する質問 | 使った結果の件数 |
|---|---|---|---|
| 1 | range-based volatility estimator using high, low, open and close prices: efficiency compared with close-to-close estimator | Q1 | 6 |
| 2 | drift-independent volatility estimation based on high, low, open, and close prices with opening jumps (overnight gap) | Q1 | 1 |
| 3 | heterogeneous autoregressive model of realized volatility (HAR-RV) forecast | Q2・Q7 | 6 |
| 4 | A forecast comparison of volatility models: does anything beat a GARCH(1,1)? | Q2・Q6 | 5 |
| 5 | forecasting volatility in financial markets: a review of historical volatility, EWMA RiskMetrics, GARCH and implied volatility forecasts | Q2 | 3 |
| 6 | volatility forecast comparison using imperfect volatility proxies: robust loss functions, QLIKE | Q3 | 2 |
| 7 | filtered historical simulation for value at risk: bootstrapping volatility-standardized returns, incorporating volatility updating into historical simulation | Q4 | 4 |
| 8 | evaluating interval forecasts: unconditional and conditional coverage tests for value-at-risk backtesting | Q4・Q5 | 2 |
| 9 | strictly proper scoring rules, prediction, and estimation; continuous ranked probability score for probabilistic forecasts | Q5 | 3 |
| 10 | probabilistic forecasts, calibration and sharpness; evaluating density forecasts with the probability integral transform | Q5・Q18 | 3 |
| 11 | comparing predictive accuracy: test of equal forecast accuracy (Diebold-Mariano), small-sample modification, tests of conditional predictive ability | Q6・Q18 | 8 |
| 12 | false discovery rate in finance: false discoveries in mutual fund performance, luck versus skill in estimated alphas; model confidence set | Q6 | 2（＋既存 1 件を再確認） |
| 13 | forecast combination puzzle: simple average of forecasts is hard to beat compared with estimated optimal combination weights | Q7 | 2 |
| 14 | combining probability forecasts: is it better to average probabilities or quantiles? linear opinion pool calibration and sharpness | Q7 | 3 |
| 15 | adaptive conformal inference under distribution shift; conformal prediction intervals for time series with dependence | Q8 | 4 |
| 16 | out-of-sample equity premium prediction: predictors fail to beat the historical average; economically motivated restrictions and forecast combination improve out-of-sample forecasts | Q9・Q7・Q20 | 4（＋既存 1 件を再確認） |
| 17 | moving average distance as a predictor of equity returns (distance between short- and long-run moving averages of prices) | Q9 | 1 |
| 18 | financial asset returns, direction-of-change forecasting, and volatility dynamics: sign predictability without mean predictability | Q10 | 2 |
| 19 | short-term return reversal in weekly and monthly individual stock returns: contrarian profits as compensation for liquidity provision | Q11・Q14 | 4（＋既存 1 件を再確認） |
| 20 | short-term contrarian strategy and return reversal in the Japanese stock market (Tokyo Stock Exchange): winner-loser effect at one-week and one-month horizons | Q11・Q13 | 3（＋既存 2 件を再確認） |
| 21 | cross-sectional and time-series tests of return predictability: what is the difference? time-series momentum versus cross-sectional momentum in individual stocks | Q12 | 2（＋既存 3 件を再確認） |
| 22 | high-volume return premium cross-country evidence; dynamic volume-return relation of individual stocks (volume and subsequent return continuation or reversal) | Q13 | 4（＋既存 2 件を再確認） |
| 23 | 52-week high momentum strategy: nearness to the 52-week high and subsequent stock returns in Japan and international markets | Q14 | 1（＋既存 2 件を再確認） |
| 24 | post-earnings announcement drift in Japan; management earnings forecasts and forecast revisions and subsequent stock returns in Japanese firms | Q15 | 2 |
| 25 | share repurchase announcements in Japan: stock price reaction and long-run stock performance after buyback announcements | Q15・Q19 | 3 |
| 26 | foreign exchange exposure of Japanese multinational corporations and exporters: yen exchange rate and stock returns, automotive industry exposure | Q16 | 4 |
| 27 | nearest-neighbour (analog, pattern-matching) nonparametric forecasting of exchange rates and stock returns compared with random walk | Q17 | 3 |
| 28 | inference with overlapping observations in long-horizon return regressions: autocorrelation-consistent standard errors and the myth of long-horizon predictability | Q18 | 3 |
| 29 | backtest overfitting in investment strategies: purged and combinatorial cross-validation for financial time series; pre-registration and p-hacking in financial economics | Q19 | 1（＋既存 3 件を再確認） |
| 30 | global versus local forecasting models: principles for forecasting groups of time series with one pooled model across series (locality and globality, cross-learning) | Q20 | 1 |
| 31 | pooled panel predictive regressions versus stock-specific time-series regressions for forecasting individual stock returns; empirical asset pricing via machine learning | Q20・Q9 | 0（＋既存 1 件を再確認） |
| 32 | Evaluating density forecasts with applications to financial risk management; techniques for verifying the accuracy of risk measurement models | Q5・Q4 | 3 |
| 33 | Fads, martingales, and market efficiency; evaporating liquidity: returns of short-term reversal strategies as a proxy for returns from liquidity provision | Q11 | 3 |
| 34 | Exchange rate exposure and competition: evidence from the automotive industry; firm-level exchange rate exposure across countries | Q16 | 3 |
| 35 | The model confidence set; consistent ranking of volatility models with a noisy volatility proxy | Q6・Q3・Q2 | 3 |
| 36 | similarity-based (analog, k-nearest-neighbour) forecasting of volatility and conditional return distributions or value-at-risk from similar past market states | Q17・Q20 | 2 |
| W1 | Parkinson 1980 "The Extreme Value Method for Estimating the Variance of the Rate of Return" Journal of Business | Q1 | 1 |
| W2 | Jegadeesh 1990 "Evidence of Predictable Behavior of Security Returns" Journal of Finance 45 abstract | Q11 | 0（＋既存 1 件の書誌を確認） |

注: 「使った結果の件数」は、出典表の行のうち、その検索で初めて出たものの数である。かっこ内は、既存の出典をその検索で再確認した数。Consensus の検索は全てフィルターなしで行った。4 回目以降は、全文抜粋の表示（include_full_text_chunks）だけをオフにした（表示の設定であり、絞り込みの条件ではない）。

## 関連文書
- [手法の検討と採否](01_method_review.md)（この確認結果を設計にどう使ったか）
- [予測手順（事前登録）](02_protocol.md)
- [学術エビデンス](../03_evidence/01_academic_literature.md)（テクニカル分析の有効性の文献。EV1 の出典）
- [検証手法の落とし穴・行動ファイナンス・日本市場・機械学習](../03_evidence/02_methodology_behavioral_japan_ml.md)（EV2 の出典）
- [日本語の学術文献](../03_evidence/03_japanese_literature.md)（PB の出典）

## この文書の限界
- 確認は要旨レベルである。全文は読んでおらず、数値や条件は要旨に書かれた範囲に限られる。要旨が欠けている記録、著者名や年が欠けている記録がある（出典表のメモに記した）。
- 記録の年は、論文データベースに登録された版の年で、掲載年と異なることがある（3 節の「候補リストと記録の食い違い」）。掲載前の版（ワーキングペーパー、プレプリント）の記録も含む。
- 多くは米国の指数・個別株や為替の結果で、日本の大型株 2 銘柄の 1 週間〜3 か月先にそのまま当てはまるとは限らない。日本の結果は 1990 年代までの標本が多い。
- 探した論文のうち、記録が出なかったものがある（3 節）。それらに依存する主張は書いていない。
- 検索は 38 回で、網羅的な文献調査ではない。問いごとに 1〜3 回の検索で得た記録に基づく。
## 出典
| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| FM-001 | The Extreme Value Method for Estimating the Variance of the Rate of Return | Michael Parkinson／Journal of Business 53(1): 61–65 | 1980 | https://econpapers.repec.org/RePEc:ucp:jnlbus:v:53:y:1980:i:1:p:61-65 | ✅S | WebSearch の結果と要約のみ（要旨は未読）。高値・安値のレンジから分散を推定する方法で、終値による従来の推定より効率が高いと述べる（倍率の数値は未照合）。引用数 約1,190（WebSearch の要約の値）／DOI: 10.1086/296071 |
| FM-002 | On the Estimation of Security Price Volatilities from Historical Data | Mark B. Garman and Michael J. Klass／The Journal of Business | 1980 | https://consensus.app/papers/details/w:4c29d784-e8de-424a-a8e0-596024e3dcbd/ | ✅S | 要旨のみ。始値・高値・安値・終値と出来高を使う推定量を定式化。標準的な推定量より相対効率がかなり高い。引用数 1550（記録の値） |
| FM-003 | Estimating Variance From High, Low and Closing Prices | L. C. G. Rogers and Stephen Satchell／The Annals of Applied Probability | 1991 | https://consensus.app/papers/details/w:156c9053-8191-420f-b26b-9ce35fb19ac5/ | ✅S | 要旨のみ。高値・安値・終値による推定量で、ドリフトによらず不偏。離散観測が生む誤差と、その簡単な補正を示す。引用数 678（記録の値） |
| FM-004 | Drift Independent Volatility Estimation Based on High, Low, Open, and Close Prices | Dennis Tao Yang and Qiang Zhang／The Journal of Business | 2000 | https://consensus.app/papers/details/w:36ac72b3-0577-4267-8265-25e770712d0f/ | ✅S | 要旨のみ。複数期間の四本値による推定量。ドリフトに依存せず寄り付きの飛びにも整合的で、終値法より大幅に精密。引用数 487（記録の値） |
| FM-005 | Range‐Based Estimation of Stochastic Volatility Models | Sassan Alizadeh, Michael W. Brandt, and Francis X. Diebold／The Journal of Finance | 2002 | https://consensus.app/papers/details/w:a94fdaa7-1db3-483c-bcc5-bc07ec9d9381/ | ✅S | 要旨のみ。レンジに基づくボラティリティの代理変数は効率が高く、近似的に正規で、マイクロストラクチャ雑音に頑健。引用数 1260（記録の値） |
| FM-006 | Properties of range-based volatility estimators | Péter Molnár／International Review of Financial Analysis | 2011 | https://consensus.app/papers/details/w:4bba6391-5ccd-4158-820c-467e74147046/ | ✅S | 要旨のみ。終値だけの推定は不正確で、レンジ型は大幅に精密だが、なお雑音を含む推定値であると注意する。引用数 142（記録の値）。記録の年は2011（候補リストは2012） |
| FM-007 | Testing range estimators of historical volatility | Jinghong Shu and Jin E. Zhang／Journal of Futures Markets | 2006 | https://consensus.app/papers/details/w:88f128a0-d31a-47cf-8a6c-b5e815b97b36/ | ✅S | 要旨のみ。4種のレンジ推定量を比較。連続の幾何ブラウン運動では良好だが、寄り付きの飛びや大きなドリフトで差が出る。引用数 124（記録の値） |
| FM-008 | A Simple Approximate Long-Memory Model of Realized Volatility | Fulvio Corsi／Journal of Financial Econometrics | 2008 | https://consensus.app/papers/details/w:01cf5eeb-c365-4cfe-b556-d4d8a7cf88cd/ | ✅S | 要旨のみ。異なる期間で実現したボラティリティ成分を足す HAR-RV を提案。簡素だが長期記憶等を再現し予測成績が良い。引用数 2586（記録の値）。記録の年は2008（要旨の著作権表示と候補リストは2009） |
| FM-009 | A forecast comparison of volatility models: does anything beat a GARCH(1,1)? | Peter Reinhard Hansen and Asger Lunde／Journal of Applied Econometrics | 2005 | https://consensus.app/papers/details/w:506f0a29-7f58-4c3a-8389-b6d0a726b095/ | ✅S | 要旨のみ。ARCH 型330モデルを標本外で比較。為替では GARCH(1,1) を上回る証拠なし、IBM 株ではレバレッジを扱うモデルに劣る。引用数 1892（記録の値） |
| FM-010 | Forecasting Volatility in Financial Markets: A Review | Ser‐Huang Poon and Clive W. J. Granger／Journal of Economic Literature | 2003 | https://consensus.app/papers/details/w:aee28b68-9749-4a1b-9903-20437911970c/ | ✅S | 要旨のみ。【サーベイ】過去20年の93論文のボラティリティ予測結果を、ヒストリカル系とオプションのインプライドとで比較する。引用数 3947（記録の値） |
| FM-011 | A Practical Guide to Harnessing the HAR Volatility Model | Adam E. Clements and Daniel P. A. Preve／Journal of Banking & Finance | 2019 | https://consensus.app/papers/details/w:edaa9bc8-b177-4390-be47-57bca745b593/ | ✅S | 要旨のみ。16年・3株価指数の標本外検証。簡単な改良が標準 HAR と HARQ を上回り、対数レンジでも RV に近い質の予測が多い。引用数 87（記録の値） |
| FM-012 | HARd to beat: The overlooked impact of rolling windows in the era of machine learning | Jonathan Chassot and Francesco Audrino／International Journal of Forecasting | 2025 | https://consensus.app/papers/details/w:592bfa4f-7dfd-4d0c-bdfc-59c3cb0406a3/ | ✅S | 要旨のみ。1,455銘柄。推定窓と再推定頻度を整えた HAR を、機械学習は調整を尽くしても上回れなかった。引用数 8（記録の値） |
| FM-013 | Forecast combination puzzle in the HAR model | Adam E. Clements and Andrey L. Vasnev／Journal of Forecasting | 2023 | https://consensus.app/papers/details/w:66a952e8-3de5-4ace-9f9c-fa204936fa48/ | ✅S | 要旨のみ。HAR を3予測子の結合とみなす。OLS の最適重みより単純平均の結合が、指数・個別株・他資産で精度が高い。引用数 11（記録の値） |
| FM-014 | Forecasting accuracy of stochastic volatility, GARCH and EWMA models under different volatility scenarios | Jie Ding and Nigel Meade／Applied Financial Economics | 2010 | https://consensus.app/papers/details/w:d5533e6e-1ba4-4aef-9d81-bb17245b679d/ | ✅S | 要旨のみ。ボラティリティの変動が中程度の状況では EWMA を使う損失は小さく、実系列の多くはこれに当たる。引用数 34（記録の値） |
| FM-015 | An International Comparison of Implied, Realized, and GARCH Volatility Forecasts | Apostolos Kourtis, Raphael N. Markellos, and Lazaros Symeonidis／Journal of Futures Markets | 2016 | https://consensus.app/papers/details/w:62d0fe8b-d5c5-4f3e-a5d6-f4511bf9ad00/ | ✅S | 要旨のみ。10か国13指数。日次は HAR、月次はリスクプレミアム補正つきインプライドが最良。GARCH はほぼ全ての場合で劣る。引用数 52（記録の値） |
| FM-016 | Modeling and Forecasting Realized Volatility | Torben G. Andersen, Tim Bollerslev B, and 2 others／Econometrica | 2003 | https://consensus.app/papers/details/w:fbe8698d-6515-465e-bc75-ea106fdcf006/ | ✅S | 要旨のみ。対数実現ボラティリティの長期記憶 VAR は日次 ARCH 系より良好。標準化リターンの正規性と合わせ較正のよい密度予測になる。引用数 3942（記録の値） |
| FM-017 | Forecasting Daily Volatility of Stock Price Index Using Daily Returns and Realized Volatility | Makoto Takahashi, Toshiaki Watanabe, and Yasuhiro Omori／Econometrics and Statistics | 2021 | https://consensus.app/papers/details/w:0caee44e-b4a4-42f5-8235-7a230a6003c6/ | ✅S | 要旨のみ。ダウ・日経225など4指数。実現ボラティリティを使うモデルは、日次リターンだけのモデル（EGARCH・SV）を上回る。引用数 23（記録の値） |
| FM-018 | Volatility forecast comparison using imperfect volatility proxies | Andrew J. Patton／Journal of Econometrics | 2010 | https://consensus.app/papers/details/w:3dd5e501-f490-4850-ae9c-95f463f6c537/ | ✅S | 要旨のみ。雑音のある代理変数でも予測の順位が保たれる損失関数の必要十分条件を導き、広く使われる損失関数の歪みを示す。引用数 1359（記録の値）。記録の年は2010（候補リストは2011） |
| FM-019 | Consistent ranking of volatility models | Peter Reinhard Hansen and Asger Lunde／Journal of Econometrics | 2005 | https://consensus.app/papers/details/w:e11bad2d-c339-4a7a-85f9-f7d66262dea6/ | ✅S | 要旨のみ。代理変数で評価すると順位が真の順位と食い違いうる。二乗リターンで代用すると劣るモデルが「最良」に選ばれうる。引用数 384（記録の値）。記録の年は2005（候補リストは2006） |
| FM-020 | Volatility forecasts, proxies and loss functions | Erhard Reschenhofer, Manveer Kaur Mangat, and Thomas Stark／Journal of Empirical Finance | 2020 | https://consensus.app/papers/details/w:5de190a2-6599-4b72-aa2e-71ddfeabb566/ | ✅S | 要旨のみ。【批判】代理変数に頑健な損失関数どうしでも順位が一致するとは限らず、正反対にもなりうる。尤度に基づく損失関数を提案。引用数 17（記録の値） |
| FM-021 | Published: Journal of Risk, Fall 1998 Incorporating Volatility Updating into the Historical Simulation Method for Value at Risk Incorporating Volatility Updating into the Historical Simulation Method for Value at Risk | （記録に著者名なし）／Unknown Journal | 記載なし | https://consensus.app/papers/details/w:f3d18ae1-6762-4b2d-8e17-ea6071ceeb01/ | ✅S | 要旨のみ。GARCH か EWMA で、過去データを当時と現在のボラティリティの差で調整して使う方法。12通貨・5株価指数で大幅に改善。引用数 291（記録の値）。著者と年は記録に欠落（題名に Journal of Risk, Fall 1998 とある） |
| FM-022 | Filtering Historical Simulation. Backtest Analysis | Giovanni Barone‐Adesi, Kostas Giannopoulos, and Les Vosper／（掲載誌不明。記録の掲載誌欄はウェブ上の PDF の所在） | 2000 | https://consensus.app/papers/details/w:2c90c9f5-0175-442c-bfdf-2fe95b37c6fd/ | ✅S | 要旨のみ。過去と現在のボラティリティの変化を織り込むフィルター付きヒストリカル・シミュレーションを、3種のポートフォリオで2年間検証。引用数 20（記録の値）。候補リストの1999年の原論文は記録として未確認 |
| FM-023 | Value–at–Risk Models | Peter Christoffersen／Springer eBooks | 2009 | https://consensus.app/papers/details/w:6594807f-21bd-4575-a7c9-cdb2df6cdcf9/ | ✅S | 要旨のみ。【書籍の章】動的分散モデルで濾過した過去のイノベーションから将来リターンを模擬し、複数の保有期間の VaR 等を現在の市況に条件づけて計算。引用数 148（記録の値） |
| FM-024 | Financial density forecasts: A comprehensive comparison of risk‐neutral and historical schemes | Ricardo Crisóstomo and Lorena Couso／Journal of Forecasting | 2018 | https://consensus.app/papers/details/w:c7575107-a6f3-4cdc-a669-2c93e4957434/ | ✅S | 要旨のみ。21年超・15の予測方式の比較。GARCH に基づく GJR-FHS が、密度の全範囲で最も整合的な予測を与える。引用数 11（記録の値） |
| FM-025 | Techniques for Verifying the Accuracy of Risk Measurement Models | Paul Kupiec／The Journal of Derivatives | 1995 | https://consensus.app/papers/details/w:2cf51be4-8852-4d6f-a76d-4fc5d90b7532/ | ✅S | 要旨のみ。裾の確率の推定値は、検証する確率が小さいほど正確さの検証が格段に難しく、極めてまれな事象ではほぼ不可能。引用数 2779（記録の値） |
| FM-026 | Evaluating Interval Forecasts | Peter Christoffersen／International Economic Review | 1998 | https://consensus.app/papers/details/w:79071ecc-4d1c-4dd2-94a6-3902d67ccf64/ | ✅S | 要旨のみ。従来は無条件カバレッジの検定にとどまるとし、高次モーメントに動学があるとき重要な条件付きの区間予測評価の枠組みを構築。引用数 2716（記録の値） |
| FM-027 | Testing Density Forecasts, With Applications to Risk Management | Jeremy Berkowitz／Journal of Business and Economic Statistics | 2001 | https://consensus.app/papers/details/w:938a9b9e-b427-4efe-b32c-ec4524d0f891/ | ✅S | 要旨のみ。既存の区間・密度予測の検定は通常の標本数では検出力が低い。予測分布の全体を評価すれば標本数100程度でも検出力がある。引用数 902（記録の値） |
| FM-028 | Strictly Proper Scoring Rules, Prediction, and Estimation | Tilmann Gneiting and Adrian E. Raftery／Journal of the American Statistical Association | 2007 | https://consensus.app/papers/details/w:88b102ab-1e7f-4482-8d10-e65b467c478c/ | ✅S | 要旨のみ。適正スコアリングルールの理論。CRPS は絶対誤差の一般化。分位点・区間予測の適正スコアと、幅と被覆を扱う区間スコアを提案。引用数 7614（記録の値） |
| FM-029 | Probabilistic Forecasts, Calibration and Sharpness | Tilmann Gneiting, Fadoua Balabdaoui, and Adrian E. Raftery／Journal of the Royal Statistical Society Series B (Statistical Methodology) | 2007 | https://consensus.app/papers/details/w:2f5c0f29-4735-4546-bc45-96ef0207631f/ | ✅S | 要旨のみ。「較正を条件に予測分布の鋭さを最大化する」評価の枠組み。PIT ヒストグラム、周辺較正図、鋭さの図、適正スコアを道具とする。引用数 2048（記録の値） |
| FM-030 | Evaluating Density Forecasts with Applications to Financial Risk Management | Francis X. Diebold, Todd A. Gunther, and Anthony S. Tay／International Economic Review | 1998 | https://consensus.app/papers/details/w:ce194e73-32e0-481a-92bc-a9d49837018a/ | ✅S | 要旨のみ。密度予測の評価のための簡単で実用的な枠組みを示し、ボラティリティが時変する環境の資産リターンの密度予測に適用。引用数 1541（記録の値）。要旨は PIT の語を使っていない |
| FM-031 | Local scale invariance and robustness of proper scoring rules | David Bolin and Jonas Wallin／Statistical Science | 2022 | https://consensus.app/papers/details/w:3c32d1d7-85eb-4a8b-afe0-5114243dc9a2/ | ✅S | 要旨のみ。CRPS などの平均は不確実性の大きい観測に重みが偏り、直観に反する順位になりうる。尺度不変な scaled CRPS を提案。引用数 34（記録の値） |
| FM-032 | Evaluating the Calibration of Multi-Step-Ahead Density Forecasts Using Raw Moments | Malte Knüppel／Journal of Business and Economic Statistics | 2014 | https://consensus.app/papers/details/w:499a14a9-03a2-4adc-a9a8-b31da4d85a25/ | ✅S | 要旨のみ。複数期間先の密度予測は PIT が系列相関を持ち評価が難しい。標準的な臨界値で使える素モーメントに基づく検定を提案。引用数 71（記録の値） |
| FM-033 | Comparing Predictive Accuracy | Francis X. Diebold and Roberto S. Mariano／Journal of Business and Economic Statistics | 2002 | https://consensus.app/papers/details/w:19b48d14-88f5-4fe3-8a5b-c3983cf026e7/ | ✅S | 要旨のみ。二つの予測の精度に差がないという帰無仮説の検定。損失は二次・対称でなくてよく、予測誤差の系列相関も許す。引用数 5797（記録の値）。記録の年は2002（他の記録の要旨は1995年の論文として引用。候補リストも1995） |
| FM-034 | Testing the equality of prediction mean squared errors | David I. Harvey, Stephen J. Leybourne, and Paul Newbold／International Journal of Forecasting | 1997 | https://consensus.app/papers/details/w:c6144a0f-e230-44de-8c44-5e0831c4fde3/ | ✅S | 要旨のみ。予測精度が等しいという仮説の検定の挙動を分析し、元の定式化の欠点を避ける修正を検討して、実務向けに一つの方法を推奨。引用数 2205（記録の値） |
| FM-035 | Tests of Conditional Predictive Ability | Raffaella Giacomini and Halbert White／Econometrica | 2006 | https://consensus.app/papers/details/w:dca52fe6-bf1e-404e-a134-f6dae5bd1561/ | ✅S | 要旨のみ。条件付き期待に基づく標本外比較。モデルではなく推定手続きを含む「予測方法」を評価し、入れ子・非入れ子の双方を扱える。引用数 1685（記録の値） |
| FM-036 | Comparing predictive accuracy in small samples using fixed‐smoothing asymptotics | Laura Coroneo and Fabrizio Iacone／Journal of Applied Econometrics | 2020 | https://consensus.app/papers/details/w:b8dfc14e-d5bd-4623-a66b-a038a2a405d5/ | ✅S | 要旨のみ。固定平滑化漸近論を使うと、標本外観測が少数でも検定のサイズが正しくなる。専門家予測の優位は一部が見かけと報告。引用数 52（記録の値） |
| FM-037 | Testing for equal predictive accuracy with strong dependence | Laura Coroneo and Fabrizio Iacone／International Journal of Forecasting | 2024 | https://consensus.app/papers/details/w:7fc4ce78-71ed-4501-a98e-35b533b8e698/ | ✅S | 要旨のみ。損失差の自己相関が強いほど検定の検出力が下がり、ある閾値を超えると正しい帰無仮説を誤って棄却する。引用数 15（記録の値） |
| FM-038 | Choosing the Best Volatility Models: The Model Confidence Set Approach* | Peter Reinhard Hansen, Asger Lunde, and James M. Nason／Oxford Bulletin of Economics and Statistics | 2003 | https://consensus.app/papers/details/w:42b58666-c7ab-4f56-a00a-b36d500fab7a/ | ✅S | 要旨のみ。モデル信頼集合は最良の予測モデルを所定の確率で含む集合。55のボラティリティ・モデルで、平均二乗誤差では約3分の1が残る。引用数 212（記録の値） |
| FM-039 | False Discoveries in Mutual Fund Performance: Measuring Luck in Estimated Alphas | Laurent Barras, Olivier Scaillet B, and Russ R. Wermers／The Journal of Finance | 2010 | https://consensus.app/papers/details/w:0d822e11-0fd4-4c86-91fb-c4d1004fabf2/ | ✅S | 要旨のみ。運だけで有意に見える「偽発見」を制御する方法。投資信託の75%はアルファがゼロ。持続的な成績のファンドを見つけやすくなる。引用数 836（記録の値） |
| FM-040 | Reassessing False Discoveries in Mutual Fund Performance: Skill, Luck, or Lack of Power? | Angie Andrikogiannopoulou and Filippos Papakonstantinou／The Journal of Finance | 2019 | https://consensus.app/papers/details/w:eaeffae9-6aee-466d-8c8e-bc520d23dbd7/ | ✅S | 要旨のみ。【批判】偽発見率の方法は信号対雑音比が低いと検出力が低く保守的で、アルファが非ゼロのファンドの割合を過小推定する。引用数 56（記録の値） |
| FM-041 | Chapter 4 Forecast Combinations | Allan Timmermann／Handbook of economic forecasting | 2006 | https://consensus.app/papers/details/w:7e60231d-2aa5-4c98-9ce1-a1cb2fcdff95/ | ✅S | 要旨のみ。【サーベイ（ハンドブックの章）】結合は事前に最良の単独モデルより平均的に良く、単純な結合が最適重みを推定する精緻な方式をしばしば上回る。引用数 1339（記録の値） |
| FM-042 | The forecast combination puzzle: A simple theoretical explanation | Gerda Claeskens, Jan R. Magnus, and 2 others／International Journal of Forecasting | 2016 | https://consensus.app/papers/details/w:b176f537-0ace-4ad5-9bbf-90421b5e1bac/ | ✅S | 要旨のみ。重みが推定値であることを考慮すると結合予測に偏りが生じ分散も増える。「最適」結合が等加重より良い保証はない。引用数 272（記録の値） |
| FM-043 | Out-of-Sample Equity Premium Prediction: Combination Forecasts and Links to the Real Economy | David E. Rapach, Jack Strauss, and Guofu Zhou／Review of Financial Studies | 2009 | https://consensus.app/papers/details/w:3a533ea9-854e-40bf-98a8-83149b926330/ | ✅S | 要旨のみ。個別の予測回帰は標本外で安定して勝てない。個別予測の結合は過去平均に対して統計的・経済的に有意な利得を一貫して与える。引用数 1642（記録の値）。記録の年は2009（候補リストは2010） |
| FM-044 | Combining Probability Forecasts | Roopesh Ranjan and Tilmann Gneiting／Journal of the Royal Statistical Society Series B (Statistical Methodology) | 2010 | https://consensus.app/papers/details/w:08917104-ab29-4a30-8409-4eb86eca1b46/ | ✅S | 要旨のみ。較正された相異なる確率予測の加重平均は必ず較正を失い鋭さを欠く。線形プールには再較正が必要で、ベータ変換つきの方法を提案。引用数 279（記録の値） |
| FM-045 | Quantile Aggregation of Density Forecasts | Fabio Busetti／Oxford Bulletin of Economics and Statistics | 2017 | https://consensus.app/papers/details/w:46ba830b-74dc-4462-8c76-76d4522ee626/ | ✅S | 要旨のみ。分位点の平均の性質は線形プールと対数プールの中間。個別予測に偏りがあるときは、総じて分位点の平均が望ましい。引用数 106（記録の値） |
| FM-046 | Adaptive Conformal Inference Under Distribution Shift | Isaac Gibbs and Emmanuel J. Candès／arXiv (Cornell University) | 2021 | https://consensus.app/papers/details/w:455f856a-ac3d-4ab7-ba55-e40a4e847dae/ | ✅S | 要旨のみ（プレプリント表示）。分布が未知の形で時変するオンライン設定で、交換可能性を仮定せず、長期の被覆頻度を理論的に保証する適応的な方法。引用数 744（記録の値） |
| FM-047 | Adaptive Conformal Predictions for Time Series | Margaux Zaffran, Aymeric Dieuleveut, and 3 others／arXiv (Cornell University) | 2022 | https://consensus.app/papers/details/w:678e01c2-570f-41af-8ea7-16875e3aa9aa/ | ✅S | 要旨のみ（プレプリント表示）。適応的コンフォーマル推論は一般の依存を持つ時系列にも有効と論じ、学習率の影響を分析。パラメータ不要の集約法を提案。引用数 312（記録の値） |
| FM-048 | Sequential Predictive Conformal Inference for Time Series | Xu, Chen and Yao Xie／arXiv (Cornell University) | 2022 | https://consensus.app/papers/details/w:d775f3aa-d013-4499-bff8-51fe49c2ac2c/ | ✅S | 要旨のみ（プレプリント表示）。残差の時間的依存を使い、将来の残差の条件付き分位点を適応的に再推定する。漸近的な条件付き被覆と区間幅の縮小を報告。引用数 132（記録の値）。候補リストの Xu & Xie 2021 とは別の論文 |
| FM-049 | Conformal prediction beyond exchangeability | Rina Foygel Barber, Emmanuel J. Candès, and 2 others／The Annals of Statistics | 2023 | https://consensus.app/papers/details/w:dacd439b-71f0-4bb9-9e7e-2a5996b27fcf/ | ✅S | 要旨のみ。分布が時間とともに動くと交換可能性は崩れる。重みつき分位点で頑健にし、直近の観測を重く扱う非対称な手法も許す一般化。引用数 677（記録の値） |
| FM-050 | Predicting Excess Stock Returns Out of Sample: Can Anything Beat the Historical Average? | John Y. Campbell and Samuel Brodsky Thompson／Review of Financial Studies | 2007 | https://consensus.app/papers/details/w:b99e525b-18be-4249-a261-84ca63005b89/ | ✅S | 要旨のみ。係数の符号と予測値に弱い制約を課すと、多くの予測回帰が過去平均を上回る。標本外の説明力は小さいが経済的に意味がある。引用数 2882（記録の値）。記録の年は2007（候補リストは2008） |
| FM-051 | The Predictability of Equity Returns from Past Returns: A New Moving Average-Based Perspective | Doron Avramov, Guy Kaplanski, and Avanidhar Subrahmanyam／SSRN Electronic Journal | 2018 | https://consensus.app/papers/details/w:e6de346b-ab12-4e86-8658-4edacdd25374/ | ✅S | 要旨のみ。短期と長期の移動平均の距離がクロスセクションで将来リターンを予測。年率アルファ約9%で、モメンタムや52週高値を超える。引用数 35（記録の値）。記録は2018年の SSRN 版で題名が異なる（候補リストは2021） |
| FM-052 | Forecasting the equity premium: can machine learning beat the historical average? | Xingfu Xu and Wei‐Han Liu／Quantitative Finance | 2024 | https://consensus.app/papers/details/w:21bd04c9-204b-4ede-92eb-70a20ca9a83f/ | ✅S | 要旨のみ。機械学習は標本内では強いが、標本外では概して過去平均に勝てない。原因をデータの小ささと信号対雑音比の低さに求める。引用数 5（記録の値） |
| FM-053 | Financial Asset Returns, Direction-of-Change Forecasting, and Volatility Dynamics | Peter Christoffersen and Francis X. Diebold／National Bureau of Economic Research | 2003 | https://consensus.app/papers/details/w:d612ee40-3506-412e-963f-576bf041789e/ | ✅S | 要旨のみ。期待リターンが非ゼロなら、ボラティリティの依存は符号の依存を生む。平均の予測可能性がなくても成り立ち、中間の期間で見つかりやすい。引用数 259（記録の値）。記録は2003年の NBER 版（候補リストは2006） |
| FM-054 | Direction-of-Change Forecasts Based on Conditional Variance, Skewness and Kurtosis Dynamics: International Evidence | Anthony S. Tay, Peter Christoffersen, and 3 others／RePEc: Research Papers in Economics | 2006 | https://consensus.app/papers/details/w:8afadc60-9d26-4a6a-87cf-bd3ec08774d9/ | ✅S | 要旨のみ（プレプリント表示）。先進国の株式市場で、条件付き分散に加え歪度・尖度も使った方向予測を試み、ブライア・スコア等で「ある程度の成功」と報告。引用数 52（記録の値）。記録の年は2006（候補リストは2007） |
| FM-055 | Fads, Martingales, and Market Efficiency | Bruce N. Lehmann／The Quarterly Journal of Economics | 1990 | https://consensus.app/papers/details/w:f255c184-be84-4d7f-ab36-420954f96367/ | ✅S | 要旨のみ。ある週の勝者・敗者は翌週にかなりのリターン反転を経験し、買値・売値の差と妥当な取引コストを補正しても残る。引用数 1573（記録の値） |
| FM-056 | Evaporating Liquidity | Stefan Nagel／Review of Financial Studies | 2012 | https://consensus.app/papers/details/w:ece36a96-cefd-4641-bb84-0461236d3ba3/ | ✅S | 要旨のみ。短期リバーサル戦略のリターンは流動性供給のリターンの代理。期待リターンは強く時変し VIX で予測でき、混乱期に大きく上昇。引用数 588（記録の値） |
| FM-057 | A Closer Look at the Short-Term Return Reversal | Zhi Da, Qianqiu Liu, and Ernst Schaumburg／Management Science | 2013 | https://consensus.app/papers/details/w:39294432-1bc1-423d-8dfb-cfa19cca6d58/ | ✅S | 要旨のみ。ファンダメンタルズで説明できないリターンほど短期で反転しやすい。流動性ショックと投資家センチメントの双方が寄与する。引用数 208（記録の値）。記録の年は2013（候補リストは2014） |
| FM-058 | SHORT‐TERM ABNORMAL RETURNS OF THE CONTRARIAN STRATEGY IN THE JAPANESE STOCK MARKET | Rosita P. Chang, Dennis W. McLeavey, and S. Ghon Rhee／Journal of Business Finance & Accounting | 1995 | https://consensus.app/papers/details/w:a4233e2c-04a5-4f31-b424-341551efb111/ | ✅S | 要旨のみ。記録の要旨欄は序論の文章（先行研究の整理）で、結果の記述がない。日本株の短期逆張り戦略を扱う論文であることのみ確認。引用数 102（記録の値） |
| FM-059 | The winner–loser effect in Japanese stock returns | Yoshio Iihara, Hideaki Kiyoshi Kato, and Toshifumi Tokunaga／Japan and the World Economy | 2003 | https://consensus.app/papers/details/w:b110c6cd-1099-40cc-8ada-4f4b7dcac37c/ | ✅S | 要旨のみ。東証1975〜1997年。1か月など短期で有意なリターン反転が支配的で、モメンタムは観察されない。過剰反応が説明の候補。引用数 75（記録の値）。記録の年は2003（候補リストは2004） |
| FM-060 | Volume and individual security returns on the Tokyo Stock Exchange | Marc Bremer and Takato Hiraki／Pacific-Basin Finance Journal | 1999 | https://consensus.app/papers/details/w:e352afe3-ec5b-49bb-8289-2c1fe6982217/ | ✅S | 要旨のみ。東証一部1981〜1998年の週次。前週に下落した銘柄は翌週に反転し、前週の出来高が多い敗者株ほど反転が大きい。引用数 26（記録の値） |
| FM-061 | Cross-Sectional and Time-Series Tests of Return Predictability: What Is the Difference? | Amit Goyal and Narasimhan Jegadeesh／Review of Financial Studies | 2017 | https://consensus.app/papers/details/w:d1afeaf8-dc8c-444a-9946-5f327f1fe129/ | ✅S | 要旨のみ。個別株では、時系列型とクロスセクション型の戦略の成績差は、時系列型が取る時変のネット買い持ちで大部分が説明される。引用数 139（記録の値）。記録の年は2017（候補リストは2018） |
| FM-062 | The high volume return premium: Cross-country evidence | Ron Kaniel, Arzu Ozoguz, and Laura T. Starks／Journal of Financial Economics | 2011 | https://consensus.app/papers/details/w:7d6b4a08-e18d-4d09-a7f7-648b5442fc44/ | ✅S | 要旨のみ。41か国で高出来高リターン・プレミアムを検証。先進国・新興国の双方で見られ、リスクや流動性の系統的な差では説明されない。引用数 94（記録の値）。記録の年は2011（候補リストは2012） |
| FM-063 | Dynamic Volume-Return Relation of Individual Stocks | （記録に著者名なし）／Econometrics: Applied Econometrics & Modeling eJournal | 2000 | https://consensus.app/papers/details/w:dc8370ac-970e-4b80-a40a-35edb2f16892/ | ✅S | 要旨のみ（プレプリント表示）。リスク分担の売買によるリターンは反転し、私的情報に基づく投機的売買によるリターンは継続しやすい。NYSE・AMEX の日次で検証。引用数 808（記録の値）。著者名は記録に欠落。記録の年は2000（候補リストは2002） |
| FM-064 | Is the 52-week high effect as strong as momentum? Evidence from developed and emerging market indices | Graham N. Bornholt and Mirela D. Malin／Applied Financial Economics | 2011 | https://consensus.app/papers/details/w:95ae6902-f7da-4fb8-bb52-b48729592516/ | ✅S | 要旨のみ。【批判】先進国・新興国の市場指数では、モメンタム戦略が52週高値戦略より有意に収益的。52週高値効果はモメンタムほど頑健でない。引用数 10（記録の値） |
| FM-065 | Management Forecasts in Japan: An Empirical Study of Forecasts that Are Effectively Mandated | Kazuo Kato, Douglas J. Skinner, and Michio Kunimura／The Accounting Review | 2009 | https://consensus.app/papers/details/w:f5dec5b6-155e-459a-ad8d-ad3f0b8725fe/ | ✅S | 要旨のみ。日本の経営者の期初利益予想は系統的に上方に偏り、期中に下方修正されるため、利益サプライズの大半は非負になる。引用数 165（記録の値） |
| FM-066 | Post-Earnings Announcement Drift and Ownership Structure in the Modern Japanese Stock Market | Junko Jinushi／The Japanese Accounting Review | 2023 | https://consensus.app/papers/details/w:2016f456-6b15-4d35-8084-855674955e2e/ | ✅S | 要旨のみ。日本2002〜2020年。決算発表後ドリフトは縮小。ただし外国人持株比率が低い、または個人持株比率が高い企業では縮小していない。引用数 0（記録の値） |
| FM-067 | Stock price behavior surrounding stock repurchase announcements: Evidence from Japan | Takashi Hatakeda and Nobuyuki Isagawa／Pacific-Basin Finance Journal | 2003 | https://consensus.app/papers/details/w:09a3e5f1-3642-4e56-92ba-2cd52b757208/ | ✅S | 要旨のみ。日本企業の1995〜1998年の自社株買い発表。米国と同様に発表で株価は上昇。大きな株価下落が買い付けの実行を促す。引用数 57（記録の値）。記録の年は2003（候補リストは2004） |
| FM-068 | Share repurchases under the Commercial Law 212-2 in Japan: Market reaction and actual implementation | Hua Zhang／Pacific-Basin Finance Journal | 2002 | https://consensus.app/papers/details/w:0d49785d-3694-4e0b-9608-2f0e81639724/ | ✅S | 要旨のみ。日本の自社株買い発表時の異常リターンは約5%で有意。市場は当初は過小反応し、特にバリュー株で顕著。引用数 64（記録の値） |
| FM-069 | The Foreign Exchange Exposure of Japanese Multinational Corporations | Jia He and Lilian Ng／African Journal of Finance and Management | 1999 | https://consensus.app/papers/details/w:97199466-7f4b-4001-b288-e3c04201fc1e/ | ✅S | 要旨のみ。日本の多国籍企業171社の約25%が1979〜1993年に有意な正のエクスポージャー。輸出比率が高く規模が大きいほど大きい。引用数 630（記録の値）。記録の掲載誌と年は誤登録の可能性がある（候補リストは1998）。要確認 |
| FM-070 | Exchange rate exposure and competition: evidence from the automotive industry | R Williamson／Journal of Financial Economics | 2001 | https://consensus.app/papers/details/w:642cce6b-1ee6-455e-87e0-6bb6d30ca1c2/ | ✅S | 要旨のみ。米国・日本・ドイツの自動車企業。為替ショックへの有意なエクスポージャーがあり、業界の競争環境の変化と整合的に時変する。引用数 303（記録の値） |
| FM-071 | Pass‐through and Exposure | Gordon M. Bodnar, Bernard Dumas, and Richard C. Marston／The Journal of Finance | 2002 | https://consensus.app/papers/details/w:c9a0d501-1031-4737-81d4-be47a019f26a/ | ✅S | 要旨のみ。不完全競争下の輸出企業のモデルで為替の価格転嫁とエクスポージャーの関係を導き、日本の8つの輸出産業で推定する。引用数 314（記録の値） |
| FM-072 | Trade and Exposure | Kathryn M.E. Dominguez and Linda L. Tesar／American Economic Review | 2001 | https://consensus.app/papers/details/w:9bcb10a1-ccb6-4c65-9fb7-5f15d50b4f11/ | ✅S | 要旨のみ。かなりの割合の企業が為替変動にさらされるが、貿易との系統的な関係の証拠は乏しく、貿易の多い企業ほど小さい傾向。引用数 75（記録の値）。候補リストの2006年の論文とは別の論文 |
| FM-073 | Exchange Rate Exposure at the Firm and Industry Level | John A. Doukas, Patricia H. Hall, and Larry H.P. Lang／Financial Markets Institutions and Instruments | 2003 | https://consensus.app/papers/details/w:8c4c4384-8861-4fec-a7cf-527360860376/ | ✅S | 要旨のみ。東証1,079社、1975〜1995年。同時点の株式リターンと予期しない円の変動に有意な関係。ラグつきの為替変化は有意でない。引用数 98（記録の値） |
| FM-074 | Exchange-rate forecasts with simultaneous nearest-neighbour methods: evidence from the EMS | Fernando Fernández Rodríguez, Simón Sosvilla‐Rivero, and Julián Andrada Félix／International Journal of Forecasting | 1999 | https://consensus.app/papers/details/w:36672c5c-86d3-4205-80ef-4afe86aeb237/ | ✅S | 要旨のみ。欧州9通貨の日次、1978〜1994年。同時最近傍法は Theil の U で酔歩や ARIMA をわずかに上回り、方向の予測ではより優れる。引用数 99（記録の値） |
| FM-075 | Dancing with bulls and bears: Nearest-neighbour forecasts for the Nikkei index | Fernando Fernández Rodríguez, Simón Sosvilla‐Rivero, and María Dolores García Artiles／Japan and the World Economy | 1999 | https://consensus.app/papers/details/w:e39c71ae-3ac5-4d2b-b6d6-a5cfbc1ebd0d/ | ✅S | 要旨のみ。日経225、1986〜1997年。最近傍予測は Theil の U で酔歩に劣り、全期間では酔歩が有意に良い。方向の予測では酔歩を上回る。引用数 37（記録の値） |
| FM-076 | The Myth of Long-Horizon Predictability | Jacob Boudoukh A, Matthew P. Richardson, and Robert Whitelaw／Review of Financial Studies | 2005 | https://consensus.app/papers/details/w:5b00b8b0-55b1-45b6-86e1-29af3dc1293f/ | ✅S | 要旨のみ。持続的な説明変数では、予測可能性がなくても推定量が期間をまたいでほぼ完全に相関し、係数と R2 は期間にほぼ比例して増える。引用数 452（記録の値）。記録の年は2005（候補リストは2008） |
| FM-077 | New Methods for Inference in Long-Horizon Regressions | Erik Hjalmarsson／Journal of Financial and Quantitative Analysis | 2011 | https://consensus.app/papers/details/w:fbd63725-bba6-44f7-a97e-cf7eb7e9ccf7/ | ✅S | 要旨のみ。重複観測の長期回帰では、通常の t 統計量を予測期間の平方根で割れば重複の影響を補正できる。予測可能性は長期ほど強くはならない。引用数 89（記録の値） |
| FM-078 | Backtest Overfitting in the Machine Learning Era: A Comparison of Out-of-Sample Testing Methods in a Synthetic Controlled Environment | Hamid R. Arian, Daniel Norouzi Mobarekeh, and Luis Seco／SSRN Electronic Journal | 2024 | https://consensus.app/papers/details/w:5d377ec1-4c5f-4633-a323-afed6cb5eb4f/ | ✅S | 要旨のみ（プレプリント表示）。合成データで比較。組合せパージ交差検証は K 分割・パージ K 分割・ウォークフォワードより過剰適合を抑える。引用数 21（記録の値） |
| FM-079 | Principles and algorithms for forecasting groups of time series: Locality and globality | Pablo Montero‐Manso and Rob J. Hyndman／International Journal of Forecasting | 2021 | https://consensus.app/papers/details/w:eb93d016-9f58-4c7d-bd2a-fbd096b3ca3b/ | ✅S | 要旨のみ。全系列に一つの関数を当てる大域的手法は局所的手法より制約的でない。局所法の複雑さは系列数とともに増えるが大域法では一定。引用数 249（記録の値） |
| FM-080 | Risk Everywhere: Modeling and Managing Volatility | Tim Bollerslev B, Benjamin T. Hood, and 2 others／Review of Financial Studies | 2018 | https://consensus.app/papers/details/w:26b59928-5ad0-4446-95dd-43b506d4344f/ | ✅S | 要旨のみ。50超の資産、20年超。実現ボラティリティのパターンは資産間でよく似ており、それを使うパネル推定は標本外のリスク予測を改善。引用数 383（記録の値） |
| FM-081 | A comparative study of range‐based stock return volatility estimators for the German market | Neda Todorova and Sven Husmann／Journal of Futures Markets | 2011 | https://consensus.app/papers/details/w:94e58aa5-59e8-4cbe-83e5-b0e091e5d661/ | ✅S | 【補足】要旨のみ。ドイツ25銘柄。日次レンジ型は古典的推定量より大幅に優れるが、離散取引のため強い下方バイアスがある。引用数 29（記録の値） |
| FM-082 | FORECASTING VOLATILITY | （記録に著者名なし）／Unknown Journal | 2003 | https://consensus.app/papers/details/w:1a27f3f7-4a2e-46fd-b43b-80fc274ab07e/ | ✅S | 【補足】要旨のみ。複雑なモデルは標本内で良く標本外で悪い。GARCH(1,1) は概してヒストリカル標準偏差や EWMA より良い予測を与える。引用数 337（記録の値）。著者と掲載誌は記録に欠落 |
| FM-083 | Asset volatility forecasting:The optimal decay parameter in the EWMA model | Axel A. Araneda／RePEc: Research Papers in Economics | 2021 | https://consensus.app/papers/details/w:12cdc4c9-e9b4-45bb-bbf2-2d34ec68a9ec/ | ✅S | 【補足】要旨のみ（プレプリント表示）。米国大型株。EWMA の最適な減衰係数は予測期間の関数で、1か月先は RiskMetrics の提案と整合し、短期ほど短期記憶が重要。引用数 8（記録の値） |
| FM-084 | Practical Issues in Forecasting Volatility | Ser‐Huang Poon and Clive W. J. Granger／Financial Analysts Journal | 2005 | https://consensus.app/papers/details/w:e1114862-eb81-4602-b1e9-b69f2dd08c09/ | ✅S | 【補足】要旨のみ。93研究の比較。インプライドが時系列モデルより正確で、時系列モデル間に明確な勝者はない。高頻度データは短期の予測を改善。引用数 250（記録の値） |
| FM-085 | Forecasting realized volatility of agricultural commodities | Stavros Antonios Degiannakis, George N. Filis, and 2 others／International Journal of Forecasting | 2020 | https://consensus.app/papers/details/w:32d4db58-8e2a-4aab-ad2c-685e28dc0a80/ | ✅S | 【補足】要旨のみ。農産物5品目、1〜66日先。ジャンプ分解やレバレッジを加えた HAR の拡張は、標本外で単純な HAR に有意に勝てない。引用数 63（記録の値） |
| FM-086 | Forecasting realized volatility: The role of implied volatility, leverage effect, overnight returns, and volatility of realized volatility | Dimos S. Kambouroudis, David G. McMillan, and Katerina Tsakou／Journal of Futures Markets | 2021 | https://consensus.app/papers/details/w:fecbb91b-3486-4680-b4a8-f17e185d4f56/ | ✅S | 【補足】要旨のみ。10の株価指数。HAR にインプライド・ボラティリティを加えると精度が上がり、夜間リターンの追加も英国以外で有効。引用数 58（記録の値） |
| FM-087 | Backtesting Value-at-Risk: A Comparison between Filtered Bootstrap and Historical Simulation | Dario Brandolini and Stefano Colucci／The Journal of Risk Model Validation | 2011 | https://consensus.app/papers/details/w:0d194c14-6984-44ba-a70b-f2e12ab1cdfe/ | ✅S | 【補足】要旨のみ。Topix を含む指数の1日 VaR。フィルター付きブートストラップは全指数で条件付きカバレッジを満たし、単純なヒストリカル法は棄却が多い。引用数 26（記録の値） |
| FM-088 | Evaluating density forecasts: forecast combinations, model mixtures, calibration and sharpness | James Mitchell and Kenneth Frank Wallis／Journal of Applied Econometrics | 2010 | https://consensus.app/papers/details/w:0d75163a-0923-4d0f-a7b0-bebcbf711d6f/ | ✅S | 【補足】要旨のみ。【批判】鋭さの基準を導入する根拠となった例は非現実的とし、既存の情報量に基づく方法で識別でき、補助基準は不要と結論。引用数 163（記録の値） |
| FM-089 | Predictive Inference Based on Markov Chain Monte Carlo Output | Fabian Krüger, Sebastian Lerch, and 2 others／International Statistical Review | 2020 | https://consensus.app/papers/details/w:27253260-27a5-4256-a6cb-e5cb564e4694/ | ✅S | 【補足】要旨のみ。標本で与えられる予測分布の評価。対数スコアは厳しい条件を要するが、CRPS は最小限の仮定で整合的で、経験分布関数が簡便。引用数 120（記録の値） |
| FM-090 | Comparing Predictive Accuracy, Twenty Years Later: A Personal Perspective on the Use and Abuse of Diebold-Mariano Tests | Francis X. Diebold／National Bureau of Economic Research | 2012 | https://consensus.app/papers/details/w:b2a8e7d5-fded-439d-8226-821e68cf848d/ | ✅S | 【補足】要旨のみ。【論評】この検定は予測の比較用でモデルの比較用ではない。疑似標本外分析が過剰適合への最良の保険という見方は概ね誤りとする。引用数 571（記録の値） |
| FM-091 | Multi-Horizon Forecast Comparison | Rogier Quaedvlieg／Journal of Business and Economic Statistics | 2019 | https://consensus.app/papers/details/w:87896d4b-8653-4a2b-9aa4-c7a8360be0b2/ | ✅S | 【補足】要旨のみ。予測期間ごとに別々に比べず、全期間を同時に扱う優越的予測力の検定（一様・平均）を提案。モデル信頼集合の複数期間版も与える。引用数 73（記録の値） |
| FM-092 | On using predictive-ability tests in the selection of time-series prediction models: A Monte Carlo evaluation | Mauro Costantini and Robert M. Kunst／International Journal of Forecasting | 2020 | https://consensus.app/papers/details/w:ff5ec221-b31f-4783-adf8-c1f16b92e2f7/ | ✅S | 【補足】要旨のみ。シミュレーション。精度検定の有意性でモデルを選ぶ慣行には不利な証拠が優勢で、検定なしの訓練標本評価が多くの場合に最良。引用数 27（記録の値） |
| FM-093 | Angular Combining of Forecasts of Probability Distributions | James W. Taylor and Xiaochun Meng／Management Science | 2025 | https://consensus.app/papers/details/w:d583c1eb-3214-41d5-8aa5-fc2e84406858/ | ✅S | 【補足】要旨のみ。確率の平均（線形プール）は分布が広がりすぎやすく、分位点の平均が代案だが、応用結果は割れており実証の問題とする。引用数 3（記録の値） |
| FM-094 | How to Dominate the Historical Average | Kai Li, Yingying Li, and 2 others／Review of Financial Studies | 2025 | https://consensus.app/papers/details/w:fb023f1f-a037-4845-9cfd-7b08297fe287/ | ✅S | 【補足】要旨のみ。予測回帰の傾きを保守的な定数に置く方法。過去平均が使うゼロの傾きより偏りが小さく分散は同じで、過去平均を上回ると主張。引用数 7（記録の値） |
| FM-095 | Liquidity and Autocorrelations in Individual Stock Returns | Doron Avramov, Tarun Chordia, and Amit Goyal／The Journal of Finance | 2006 | https://consensus.app/papers/details/w:96ab8e3b-5531-4e07-bca8-661a22705373/ | ✅S | 【補足】要旨のみ。短期リバーサルは非流動性と強く関係し、高回転・低流動性の銘柄で最大。ただし逆張りの利益は想定される取引コストより小さい。引用数 475（記録の値） |
| FM-096 | Reversing the Trend of Short-Term Reversal | （記録に著者名なし）／Social Science Research Network | 2023 | https://consensus.app/papers/details/w:e7e00bac-0c2f-463a-9163-836a580694da/ | ✅S | 【補足】要旨のみ。【論評】古典的な短期リバーサル効果は時間とともに弱まり、大半の地域で完全に消えた。短期モメンタムに逆らわない改良版は有効。引用数 2（記録の値）。著者名は記録に欠落 |
| FM-097 | Short-Term Reversals and Longer-Term Momentum around the World: Theory and Evidence | Narasimhan Jegadeesh, Jiang Luo, and 2 others／Review of Financial Studies | 2025 | https://consensus.app/papers/details/w:e2fe286e-d8bb-45e8-8a62-61f8a676eb11/ | ✅S | 【補足】要旨のみ。短期ではリバーサル、長期に向けてモメンタムに移行する。決算発表後はリバーサルが弱まる。米国と各国のデータで支持。引用数 28（記録の値） |
| FM-098 | Cross-sectional and time-series momentum returns and market dynamics: evidence from Japan | Muhammad Ahmad Cheema, Gilbert V. Nartea, and Kenneth Szulczyk／Applied Economics | 2017 | https://consensus.app/papers/details/w:a54463fd-c2f7-4fd9-802b-ad824c197133/ | ✅S | 【補足】要旨のみ。日本株。両型のモメンタムとも、市場が同じ状態を続けるときは大きく有意だが、市場の状態が切り替わると損失になる。引用数 10（記録の値） |
| FM-099 | Dynamic trading volume and stock return relation: Does it hold out of sample? | Zijun Wang, Yan Qian, and Shiwen Wang／International Review of Financial Analysis | 2017 | https://consensus.app/papers/details/w:c332a107-c885-4540-8ac8-5aff0dab6cc5/ | ✅S | 【補足】要旨のみ。米国では活発な売買の後に高いリターンが続くが、標本外の経済的利得は年率0.73%相当と小さく、他の主要市場の多くでは予測力がない。引用数 18（記録の値） |
| FM-100 | The dynamic relationship between stock returns and trading volume: Domestic and cross-country evidence | Bong‐Soo Lee and Oliver Meng Rui／Journal of Banking & Finance | 2002 | https://consensus.app/papers/details/w:89998595-1156-498f-abbb-02b09c07fa51/ | ✅S | 【補足】要旨のみ。ニューヨーク・東京・ロンドンの日次。出来高はリターンをグレンジャーの意味で引き起こさない。出来高とボラティリティは正の相互作用。引用数 404（記録の値） |
| FM-101 | Short-term momentum and reversals, turnover, and a stock’s price-to-52-week-high ratio | Chen Chen, Chris T. Stivers, and Licheng Sun／Journal of Empirical Finance | 2024 | https://consensus.app/papers/details/w:e331a519-1056-43e5-843f-36d5d4617b91/ | ✅S | 【補足】要旨のみ。1か月リターンの短期リバーサルは、回転率と52週高値比が高いほど弱まり、両方が高い銘柄ではモメンタムに転じる。引用数 7（記録の値） |
| FM-102 | Do buyback anomalies explain the stock return in Japan? A pre-registered report | Hideaki Sakawa, Naoki Watanabel, and Kenji Hiramatsu／Pacific-Basin Finance Journal | 2025 | https://consensus.app/papers/details/w:f0298dd7-a0b2-4236-8427-4b1ef54b76a1/ | ✅S | 【補足】要旨のみ。【事前登録型の報告】日本で自社株買い発表後の長期リターンのアノマリーが続くかを検証する計画を述べる。要旨に結果の記述はない。引用数 3（記録の値） |
| FM-103 | Exchange rate exposure and risk management: The case of Japanese exporting firms | Takatoshi Ito, Satoshi Koibuchi, and 2 others／Journal of the Japanese and International Economies | 2016 | https://consensus.app/papers/details/w:28016d08-1a4f-421f-867c-d5c973c7e271/ | ✅S | 【補足】要旨のみ。東証上場企業。海外売上依存と米ドル建て比率が高いほどエクスポージャーが大きく、金融・事業上のヘッジと円建ては小さくする。引用数 86（記録の値） |
| FM-104 | A Yen for Change: The strong yen and the Japanese automobile industry | Willem Thorbecke／RePEc: Research Papers in Economics | 2017 | https://consensus.app/papers/details/w:427f5817-9395-469b-88c8-19b45f662f7b/ | ✅S | 【補足】要旨のみ（プレプリント表示）。株式リターンを為替に回帰すると、日本の自動車メーカーの円へのエクスポージャーは2016年に過去12年で最大。引用数 20（記録の値） |
| FM-105 | Nonparametric exchange rate prediction? | Francis X. Diebold and James M. Nason／Journal of International Economics | 1990 | https://consensus.app/papers/details/w:e3caeb67-beed-4c53-b2a3-027df42540eb/ | ✅S | 【補足】要旨のみ。主要10通貨（1973〜1987年）の条件付き平均をノンパラメトリックに推定。非線形性を点予測の改善に使えるという見方に否定的。引用数 547（記録の値） |
| FM-106 | Combining nearest neighbor predictions and model-based predictions of realized variance: Does it pay? | Julián Andrada Félix, Fernando Fernández Rodríguez, and Ana-María Fuertes／International Journal of Forecasting | 2016 | https://consensus.app/papers/details/w:637b3458-d80b-4feb-bfd6-abd21f5cb5c4/ | ✅S | 【補足】要旨のみ。S&P 100 の実現分散。統計的にはモデル型の予測が優れるが、混乱期には最近傍予測のほうがリスク調整後の収益性が高い。引用数 19（記録の値） |
| FM-107 | Long-Horizon Predictability: A Cautionary Tale | Jacob Boudoukh A, Ronen Israel, and Matthew P. Richardson／Financial Analysts Journal | 2019 | https://consensus.app/papers/details/w:2e14d2a6-f382-41ea-8505-bae84228b275/ | ✅S | 【補足】要旨のみ。【論評】長期リターン回帰は実質的に小標本で、重複リターンを使う利点はわずか。重複観測の補正は t 統計量を過大にしてきた。引用数 26（記録の値） |
