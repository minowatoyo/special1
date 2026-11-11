# 検証手法の落とし穴・行動ファイナンス・日本市場の実証・機械学習（チャート分析のエビデンス：方法論編）
> 要約: チャート分析の「勝てそうな結果」を歪める要因（データスヌーピング・多重検定・過剰最適化・公表後の劣化・生存バイアス・コスト・レジーム変化）を、査読論文の書誌・要旨に基づいて整理する。
> あわせて、チャートが機能し得る行動・微細構造上の理由、東証での実証、機械学習（画像CNN・LSTM等）の成果と落とし穴をまとめる。
> 補正後に弱まる証拠が多い一方、市場・期間・手法により残る証拠もあり、結論は一様でない。末尾に「ルール検証の10か条」を置く。教育目的であり売買の推奨ではない。
> 最終更新: 2026-11-11

## 1. 要約

- 探索全体の補正で結論が変わる。多数のルールから最良を選ぶ検証は偶然の勝者を拾う。Reality Check・SPA・ステップワイズ検定が整備され [EV2-001][EV2-004][EV2-005]、FDRを用いたDJIA 1897–2011の再検証では将来の優良ルールを事前に選べず、低コストでも標本内の利益が相殺された [EV2-006]。
- 多重検定。因子研究ではt>3.0の基準が提案され [EV2-007]、約210万戦略の分析では補正なしの誤棄却が約45%と推定された [EV2-009]。シャープ比は試行数に応じて割り引く [EV2-008][EV2-010]。
- バックテストは実運用より良く見える。215戦略で実運用のシャープ比が中央値73%低下 [EV2-012]、888アルゴではバックテストのシャープ比のOOS説明力はR²<0.025 [EV2-013]。
- 公表後の劣化。97変数でOOS-26%・公表後-58% [EV2-014]。ただし米国以外では有意な公表後減衰は確認されず [EV2-016]、「どこでも消える」とも言えない。
- 生存バイアス・上場廃止リターンの欠落は見かけの予測力を生み [EV2-017][EV2-018]、高回転戦略はコストで消えやすい [EV2-019][EV2-021]。
- 行動・微細構造は「機能し得る理由」を与えるが有効性の証明ではない。処分効果・52週高値のアンカリング・注意・フィードバック取引 [EV2-030][EV2-032][EV2-034][EV2-035]、注文集中と支持抵抗 [EV2-040][EV2-041]。支持抵抗の直接証拠は外為の注文データと株式の板データ（市場は要旨に明記なし）で、東証での検証は未確認。
- 日本株。ローソク足は1975–2004年で付加価値なし [EV2-046]。移動平均・MACDは先進市場で説明力が低く、標準パラメータでは負・最適化で正と、設定依存が大きい [EV2-044][EV2-048]。古典的な価格モメンタムは弱く、逆張りが1か月〜3年で有利 [EV2-051][EV2-053]。ただしAsnessは価値と併せ見れば整合的とする [EV2-050]。
- 東証の値幅制限は価格発見の遅延など副作用の証拠がある [EV2-054]。投資主体別の行動は研究ごとに異なり単純化できない [EV2-057][EV2-059]。日本語文献は CiNii・J-STAGE で抄録まで確認し [03_japanese_literature.md](03_japanese_literature.md) に整理した（補正つきの大規模なルール検証は確認できなかった）。
- 機械学習。画像CNNは既知指標と異なる予測パターンを見つけたとされる [EV2-061]が、LSTM系の好成績の多くはリークや時間文脈の無視による偽陽性の恐れがあり [EV2-064][EV2-066][EV2-065]、2010年以降に超過収益が消えた例もある [EV2-063]。LLMは学習期間との重なり（先読み）に注意 [EV2-067]。
- 実務。事前登録・試行数の記録・探索全体の補正・最終ホールドアウト・保守的コスト・レジーム別確認を「10か条」（E節）にまとめた。

## 2. A. 検証手法と落とし穴

数値は各論文の報告値で、独立には再現していない。

| 論点 | 何か | 歪み方 | 対策 | 代表文献 |
|---|---|---|---|---|
| データスヌーピング | 同一データでルールを選ぶと偶然の好成績が混入する。Whiteのリアリティ・チェックは、候補全体の中の最良ルールが偶然を超えるかをブートストラップで検定する枠組み [EV2-001][EV2-002]。Hansenは劣悪・無関係な候補に左右されにくい検定（SPA）を提案 [EV2-004]。Romano-Wolfは段階的に個別ルールを判定 [EV2-005] | 期間×閾値×フィルタの総当たりで、ルール宇宙から最良を選べば有意に見える。Sullivan他はBrock他の26ルールを拡張しDJIA 100年分で調整 [EV2-002]。Brock他の元研究はDJIA 1897–1986で、ブートストラップの帰無に乱数歩行・AR(1)・GARCH-M・EGARCHを使った [EV2-003] | 試した全ルール数を記録し、RC／SPA／ステップワイズ検定／FDRで補正。補正後に生き残るかを見る [EV2-006] | [EV2-001][EV2-002][EV2-003][EV2-004][EV2-005][EV2-006] |
| 多重検定・p-hacking | 検定回数が増えるほど偶然の有意が増える。因子研究ではt>3.0を要求する提案 [EV2-007]。約210万のランダム戦略から、補正後の閾値は時系列回帰3.8・クロスセクション回帰3.4、補正しなければ誤棄却約45%と推定 [EV2-009] | 指標・期間・銘柄・時間足を試す個人検証は暗黙の多重検定になる | 試行数を数える。報告シャープ比を試行数に応じて割り引く（ヘアカット）[EV2-008]。t>3は因子研究向けの目安で、チャート戦略への適用は類推 | [EV2-007][EV2-008][EV2-009] |
| 過剰最適化・Deflated Sharpe | 試行が増えるほど、真の優位がなくても高い見かけ性能が出る。DSRは試行数（選択バイアス）と非正規性で補正 [EV2-010]。PBOは標本内最良が標本外で振るわない確率を推定し、単純なホールドアウトは投資バックテストでは不正確になりやすいとする [EV2-011] | 銀行系215戦略でバックテスト→実運用のシャープ比が中央値73%低下、複雑なほど悪化 [EV2-012]。888アルゴでバックテストのシャープ比のOOS説明力はR²<0.025 [EV2-013] | パラメータ数を絞る。試行数Nを記録しDSRを計算。最終OOSは一度だけ使う | [EV2-010][EV2-011][EV2-012][EV2-013] |
| OOS劣化・出版バイアス | 公表・普及した手法は超過収益が縮む。97変数でOOS-26%・公表後-58%（OOS分はデータマイニングの上限推定）[EV2-014]。452アノマリーの65%は単一検定t≥1.96を満たさず（マイクロキャップ抑制の設定）、t≥2.78では82%が不合格 [EV2-015] | 書籍やツールで普及した手法の過去成績は将来より良く見える。米国以外では公表後の有意な減衰が見られず（138アノマリー・39市場）[EV2-016] | 発見・普及の前後で成績を分ける。新しい期間で検証する | [EV2-014][EV2-015][EV2-016] |
| 生存バイアス・先読み・ポイント・イン・タイム | 現在の構成銘柄だけで過去を検証する／上場廃止後の収益が欠落する／当時入手不能な情報を使う。生存で切り詰めた標本は見かけの予測可能性を生み得る（投信の分析）[EV2-017]。CRSPでは悪い理由の上場廃止リターンの欠落が偏りを生む [EV2-018] | チャート特有: 当日終値でシグナルを出し同じ終値で約定／確定が遅れるパターン（ジグザグ・ピボット・ヘッドアンドショルダー）を遡って描く／日足の高値安値の順序不明で指値・逆指値を楽観約定（一般知識）。日本株は上場廃止・合併・分割併合・指数入替・市場区分再編でユニバースが変わる（一般知識・ベンダー仕様は要確認） | 次足始値で約定。上場廃止込み・当時の構成のデータ。調整済み株価の作り方を確認 | [EV2-017][EV2-018] |
| コスト・容量・流動性 | 回転率が高いほどコストが利益を食う。建玉条件を厳しく維持条件を緩くする設計が最有効なコスト対策で、これを施せば月次回転率50%未満の大半は純スプレッドが有意、高回転で有意なものは少なく、容量は回転率と逆相関 [EV2-019]。モメンタムは高コスト銘柄の頻繁売買を要しコストで実行不能 [EV2-021]。ただし大手機関の実約定データ（19先進国・1998–2011）では実コストが従来推定の1/10未満 [EV2-020]（個人の小口への一般化は不可） | 終値約定・ゼロコスト・無限流動性の仮定。日本は呼値、値幅制限（張り付きで約定不可）、売買単位、信用金利・貸株料・逆日歩が効く（要公式確認、確認日2026-11-09）。詳細は ../02_japan/04_tse_market_rules_and_chart_effects.md | 片道コスト×回転率の感度分析。板の厚みに対する数量上限。ストップ高/安の張り付きは約定不可と扱う | [EV2-019][EV2-021][EV2-020] |
| レジーム変化・AMH | 進化の原理（競争・適応・自然淘汰）で市場と投資家行動を捉え、効率性を環境に応じて変わるものとみなす [EV2-022]。FXで1970–80年代の超過収益はデータマイニングではなかったが、フィルタ・MAルールは1990年代初めまでに消えた [EV2-023]。一方、30通貨・45年・2.1万超のルールの検証では補正後も予測可能性が残り期間・地域差が大きい [EV2-024] | 全期間平均は異質なレジーム（トレンド相場・レンジ相場・危機）の混合になる | ローリング窓・サブ期間別の成績。劣化時の停止基準を事前に決める | [EV2-022][EV2-023][EV2-024] |
| シャープ比の統計 | 推定誤差を持つ。月次SRの√12倍が正しいのは特殊条件のみで、系列相関によりヘッジファンドの年率SRが最大65%過大になった例 [EV2-025]。SR差のJobson-Korkie検定は裾が重い・時系列依存では無効で、スチューデント化した時系列ブートストラップが提案される [EV2-026] | 逆張り・オプション的な損益は歪度尖度が大きくSRを過大評価しやすい（一般知識） | 信頼区間・ブートストラップ・DSR。歪度・尖度・最大ドローダウンを併記 | [EV2-025][EV2-026] |
| ウォークフォワード・パージ付きCV | 時系列はK-foldの独立性を満たさない。純粋な自己回帰で誤差が無相関なら標準K-foldが使える場合もあるが一般には自明でない [EV2-027]。パージ（検証期間と重なる訓練標本の除去）とエンバーゴ（検証直後の除外）はLópez de Prado [EV2-071]（⚠M）が整理。組合せ型のパージCV（CPCV）も同書の提案（記憶）。暗号資産の実験ではパージ＋エンバーゴで汎化誤差の評価が改善 [EV2-028] | ラベルが数日先リターンなら訓練と検証が時間的に重なりリークする。WFの窓長・再最適化頻度を事後に選ぶと再びスヌーピング | WF設計（窓・頻度）を事前固定。探索は標本内、OOSは一度。重なりがあればパージ/エンバーゴ | [EV2-027][EV2-028][EV2-071] |
| ブートストラップ・帰無モデル | 経路は歴史の1本だけなので、帰無モデルから擬似経路を作り比較する [EV2-003][EV2-002] | 帰無の選択（独立／ブロック、ボラ過程の維持）で結論が変わる | 複数の帰無、ブロック長の感度、同回転率のランダム売買との比較 | [EV2-003][EV2-002][EV2-026] |

計算式（i.i.d.近似）。式の一部は筆者の記憶に基づくため要確認。

```
年率シャープ比（月次から）  SR_年 = SR_月 × √12                 （i.i.d.のときのみ）
系列相関ρ_kを考慮           SR(q) = SR × q / √( q + 2 × Σ_{k=1..q-1} (q-k) × ρ_k )   （Lo 2002の式・要確認）
t統計量                     t ≈ SR_年 × √(年数)
t≥3.0を満たす年率SRの下限   SR_年 ≥ 3.0 / √(年数)   → 5年で約1.34、10年で約0.95
ボンフェローニ補正          N本検定のとき各検定の有意水準 = α / N
```

## 3. B. 行動ファイナンス・市場微細構造

「チャートとの接点」欄は多くが仮説であり、論文が直接検証したものではない。行動バイアスの存在は、取引可能な超過収益を意味しない（裁定の限界・コスト）。

| 現象・理論 | 内容 | チャートとの接点（仮説） | 強さ・限界 |
|---|---|---|---|
| 処分効果 | 勝ち玉を早く売り負け玉を持ち続ける傾向。Shefrin-Statmanが命名 [EV2-029]。Odeanは米ディスカウント証券1万口座（1987–93）で勝ち銘柄が売られやすく、リバランスや低位株のコストでは説明できず、課税口座では不利と報告 [EV2-030] | 含み益帯の利食い売りや含み損帯の戻り売りが、過去の価格帯を売り圧力の厚い層（抵抗帯）にする可能性。含み益・含み損と将来リターンの関係は [EV2-074]（⚠M） | 売却確率は損益に対しV字で、損益ゼロでの跳ね上がりは明確でなく、実現選好よりも信念更新が説明し得る [EV2-031] |
| アンカリング・52週高値 | 現在価格の52週高値への近さがモメンタム利益の大部分を説明し、過去リターンを上回る予測力を持ち、長期反転を伴わない [EV2-032]。20市場中18で利益・10で有意だが、取引コスト控除後は多くの市場で有意性が消えた [EV2-033] | 年初来高値・52週高値更新のブレイクアウト系手法（CAN SLIM型）の学術的裏付け候補 | コスト後に弱い。日本単独の結果は上記要旨では未確認 |
| 投資家の注意 | 個人はニュース・異常出来高・極端な日次リターンの銘柄を純買いする（探索コストのため）[EV2-034] | 出来高急増・急騰銘柄に買いが集中し、その後の反動が出る可能性 | 収益性は市場・期間依存 |
| フィードバック取引・ハーディング | 上がれば買う投資家がいると、合理的投機家が先回りして価格変動を拡大し得る [EV2-035]。情報が徐々に拡散して過小反応し、モメンタム取引が追随して長期で過剰反応する [EV2-036] | トレンドの持続とその後の行き過ぎ（反転）を同一モデルで説明 | 順張り・逆張りの両方に根拠を与え、反証しにくい |
| 過小反応・過剰反応 | 単一の投資家心理モデルで過小反応と過剰反応を説明 [EV2-037]。過信と自己帰属バイアスで私的情報への過剰反応・公的情報への過小反応・短期モメンタム・長期反転を説明 [EV2-038]。極端な過去リターン銘柄の反転 [EV2-039] | 順張り（中期）と逆張り（超短期・長期）のホライズン依存の根拠 | 日本は古典的モメンタムが弱く逆張りが優位（C-2） |
| 注文の集中と支持抵抗 | 為替ディーラーの注文データで、利食い注文は丸い数字に、損切り注文はその少し外側に集中し、反転とブレイク後の急伸を説明し得る [EV2-040]。株式の板では支持線・抵抗線が板の厚みのピークと一致し、MAシグナルが板上の相対位置の情報を持つ [EV2-041] | 「節目」が機能する微細構造上の理由（注文が集中＝流動性が厚い／損切りが連鎖） | 外為と株式の板（市場は要旨に記載なし）が中心。東証の板・日本の注文行動での検証は未確認。公知になれば先回りされ得る（一般知識） |
| 確証バイアス | 確証バイアスがパターンや自己相関を生み、パターン取引が利益を持つ理論 [EV2-042] | パターン売買の成否が参加者の心理に依存する | 理論モデルであり実証の裏付けは限定的 |
| 合理的説明（⚠M） | 過去価格や出来高が情報を含むとする合理的モデル [EV2-072][EV2-073] | 行動バイアスを仮定しなくてもテクニカル指標に情報価値が生じ得る | 記憶のみ。内容は一次文献で確認が必要 |

## 4. C. 日本市場の実証

### C-1. テクニカルルール・ローソク足

| 文献 | 対象・方法 | 結果 | 注意 |
|---|---|---|---|
| Ito 1999 [EV2-043] | Brock型ルールを日・米・加・インドネシア・メキシコ・台湾の株価指数に適用 | 通常の検定では米国以外で予測力。時間変動する期待収益のモデルでブートストラップすると、日本・米国・台湾等の取引ルール収益と整合 | 「非効率」と「リスクプレミアムの時間変動」の区別が必要 |
| Bessembinder-Chan 1995 [EV2-044] | アジア市場の移動平均等 | マレーシア・タイ・台湾で有効、香港・日本など先進市場では説明力が低い。ブレークイーブン往復コストは平均1.57% | 刊行1995年の古い研究 |
| Urquhart他 2015 [EV2-045] | 移動平均ルールを米・英・日（TOPIX）で1987–2013に検証 | 3市場で予測力が低下。市場はシグナル当日でなく前日に反応する | AMHと整合 |
| Yamamoto 2012 [EV2-047] | 日経225構成銘柄の日中データ。価格ベースと注文フロー・板の不均衡ベースのルール | 短期リターンは不均衡情報で予測できるが、指値取引を含むどの戦略も買い持ちに勝てなかった | 標本期間内の結果 |
| Kang 2021 [EV2-048] | 日経225先物2011–2019のMACD | 標準(12,26,9)は成績が負、最適化したパラメータでは有意な正のリターン | 19,456通りのMACDから選ぶ設計で、最適化は標本内選択。過剰適合・多重検定の恐れ（筆者注） |
| Deng他 2020 [EV2-049] | 一目均衡表の標準設定(9,26,52)を4株価指数（1995–2018）と4通貨ペアで検証 | 前半期間は利益の出る戦略があったが後半期間は一貫せず。パラメータ探索では株価指数で利益的な戦略があり得るが通貨ではなし | 対象市場に東証が含まれるかは要旨に記載なし。../02_japan/02_ichimoku_kinko_hyo.md 参照 |
| Marshall他 2008 [EV2-046] | 日本株のローソク足戦略（1975–2004） | 全期間・3つの10年・強気/弱気相場のいずれでも付加価値なし | ../02_japan/01_sakata_gohou.md 参照 |

総括: 日本の結果は「先進市場ではルールが効きにくい」寄りだが、方法・期間・パラメータで割れる。補正後の確認が済んだ日本株向けの汎用ルールは、今回の検索範囲では確認できなかった。

### C-2. モメンタムと逆張り

- 日本は価格モメンタムの「例外」とされてきた [EV2-050]。Chui他はアジア8市場で、日本を除きモメンタム戦略が高収益で、法体系の違いで有無を説明した [EV2-052]。
- Asnessは、価値とモメンタムが強く負相関のため両者を一つの体系として評価すれば、日本の結果も統計ノイズの範囲で他市場と整合するとした [EV2-050]。
- Hanauerは、日本では市場状態の遷移が米国より頻繁で、モメンタム収益は状態維持時に高く遷移時に低く、それが平均を押し下げると報告 [EV2-051]。
- Chou他は、東証では逆張りが1か月〜3年のどのホライズンでも利益的で、特に1か月と2年以上が強いと報告 [EV2-053]。
- チャート上の含意（仮説）: 順張り系指標（移動平均クロス等）は日本では市場状態に強く依存し、短期の逆張りが有利な局面があり得る。ただしコストと多重検定の補正後の確認は未了。

### C-3. 値幅制限・呼値（東証）

- Kim-Rheeは、東証の値幅制限制度でボラティリティ波及・価格発見の遅延・取引阻害の3仮説すべてが支持され、制限は有効でない可能性を示した [EV2-054]。
- George-Hwangは、東証株の寄り付きと引けから計算した24時間リターンの分散を比べ、寄り付きの分散が引けより大きいのは最も活発な銘柄に限られると報告し、東証の値幅制限が値動きの動態に有意な影響を持つという仮説と整合的とした [EV2-055]。
- 東証は1998年4月13日に特定の価格帯の呼値単位を変更し、気配スプレッドは20〜50%、実効スプレッドは24〜60%低下したが、出来高の増加は明確でなかった [EV2-056]。
- チャートへの含意（一般知識・仮説）: 張り付きの日は日足の高値・安値・終値が需給を反映せず、窓や翌日以降のボラティリティの持ち越しが生じ得る。現行の値幅・呼値は本調査で取得できず、確認日2026-11-09時点で要公式確認。詳細は ../02_japan/04_tse_market_rules_and_chart_effects.md。

### C-4. 投資主体別の行動

| 文献 | データ | 知見 |
|---|---|---|
| Kamesaka他 2003 [EV2-057] | 週次の主体別フロー | 外国人・証券会社・銀行は好成績、個人は不振。外国人は正のフィードバック型のタイミングで高収益、個人も正のフィードバック型だが低収益 |
| Bae他 2008 [EV2-058] | 東証の取引 | 個人は市場タイミングが悪いが短い取引間隔では売値が買値を上回る。外国人はタイミングで一貫して利益 |
| Komai他 2018 [EV2-059] | オンライン証券793人・3,420銘柄・2013年4月〜2016年3月 | 個人は平均して逆張りで、日中リターンに関して処分効果を示す |

注意: 「外国人は順張り・個人は逆張り」と一般化できない。[EV2-057]は個人も正のフィードバック型とし、[EV2-059]は逆張りとする。期間・データ・定義が異なる。投資部門別売買動向の読み方は ../02_japan/05_supply_demand_indicators.md。

### C-5. カレンダー・アノマリー

- 年前半が高く後半が低い「デカンショ節効果」が30年超持続し、1月効果等と独立との報告 [EV2-060]。
- カレンダー・ルールは検定数が多く、A節の多重検定の影響を強く受ける。

### C-6. 日本語文献

2026-11-11 に CiNii Research と J-STAGE を取得して確認し、[03_japanese_literature.md](03_japanese_literature.md) に整理した（抄録を読めたのは39件、書誌のみ21件。本文は読んでいない）。要点は次のとおり。
- 実データで株式のテクニカルルールの収益性を示した日本語論文として抄録を読めたのは、佐藤（2017）のペアトレード1件[PB-201]。一方、後藤ほか（1988）はチャート分析ルールの正解率を約35〜45%と報告し[PB-204]、竹原（2012）は取引コストの低下でアノマリーのリスク調整後リターンが縮小しうると示す[PB-202]。
- 工学系の提案手法（遺伝的アルゴリズム、ニューラルネット、CNN）が多く、抄録に取引コスト・多重検定・標本外の扱いが書かれていないものが大半。データ・スヌーピングを題名に掲げる北島（2011）は抄録がなく内容は未確認。
- 値幅制限・空売り規制の日本語論文は人工市場シミュレーションが中心で、結論は仮定に依存する。日本株のモメンタム／リバーサルや処分効果の中心的な日本語論文は、抄録を取得できず書誌のみ。

## 5. D. 機械学習・深層学習

- 画像CNN。Jiang・Kelly・Xiu（2023）[EV2-061]は、事前に定めたパターンでなく、銘柄別の価格チャート画像から予測力の高いパターンを機械学習で抽出した。既存のトレンド信号と有意に異なり、収益性が高く、短期パターンが長い時間軸でも機能し、米国で学習したパターンが国際市場でも有効としている。日本の個別結果は要旨に記載がなく未確認。画像表現でも入力は価格・出来高で、新しい情報源ではない。
- パターン認識アルゴリズム。Savin他（2006）[EV2-062]は、Lo他（2000）の認識アルゴリズムを修正してS&P500・Russell2000（1990–99）のヘッドアンドショルダーを検証し、単独の売買戦略としては支持が乏しいが超過収益の予測力は強く、条件付き戦略でリスク調整後年5〜7%と報告。検出アルゴリズムのパラメータ自体が探索対象になる点に注意。
- LSTM・深層学習の評価。Fischer・Krauss（2017）[EV2-063]はS&P500構成銘柄（1992–2015）でコスト前に日次0.46%・シャープ比5.8を報告したが、2010年以降は超過収益が裁定され、コスト後は0付近になった。Radfar（2025）[EV2-064]は、代表的なLSTM・DNN研究が予測の時間的文脈を無視すると偽陽性になり得ると分析し、具体的な誤りを指摘した。Transformer系の指数予測でも同じ検証上の注意が必要だが、独立の批判的検証は今回確認できていない。
- データリーク・再現性。Kapoor・Narayanan（2023）[EV2-065]は17分野294論文でリークを確認し8分類を提示（金融に限らない）。Albelali・Ahmed（2025）[EV2-066]は分割前に入出力系列を作るリークがLSTMの評価を歪めると検証。Nikolopoulos（2026、プレプリント）[EV2-068]は、予測不能な帰無の下でも適応的な仕様探索が有意なバックテストを生むとして、合成データによる反証監査を提案。
- 2023–2026年の動向。Glasserman・Lin（2023）[EV2-067]は、LLMの学習期間と重なるバックテストが先読みバイアスと注意散漫効果を生むと指摘。Cakici他（2023）[EV2-070]は46市場・148特性で、MLの予測力の主な源泉がモメンタム・リバーサル・バリュー・サイズ等の単純で既知の要因だと報告。日本株ではAbe・Nakayama（2018、プレプリント）[EV2-069]が1か月先のクロスセクション予測でDNNが浅いNN等を上回るとした（取引コスト等は要旨では未確認）。ML資産価格の基準文献は [EV2-075]（⚠M）。
- 実装上の注意: 買い持ち・単純モメンタム/リバーサルとの比較、ラベルの時間重複とリーク、コスト、乱数・データ・コードの公開による再現性、少数の窓での「奇跡的」成績の疑い。

## 6. E. 個人投資家向け「ルール検証の10か条」

| # | 規則 | 根拠 |
|---|---|---|
| 1 | 検証前に仮説・ルール・パラメータ範囲・銘柄/期間・約定仮定・評価指標を書き出し、後から変えない | [EV2-007][EV2-008][EV2-009] |
| 2 | 試した本数（ルール×パラメータ×銘柄×期間）を数えて報告する | [EV2-001][EV2-010][EV2-011] |
| 3 | 総当たりをしたなら、探索全体を補正する検定（RC／SPA／ステップワイズ／FDR）かDSR・ヘアカットで評価する | [EV2-001][EV2-004][EV2-005][EV2-006][EV2-010][EV2-008] |
| 4 | データを探索用・検証用・最終ホールドアウトに分け、最終は一度だけ使う。単純なホールドアウトに頼らず複数期間・ウォークフォワードで補う。ラベルが重なるならパージ/エンバーゴ | [EV2-011][EV2-012][EV2-013][EV2-027][EV2-028] |
| 5 | 生存バイアス・先読みを排除する（上場廃止込み、当時のデータ、次足始値約定、確定遅れのパターンは確定時点から使う） | [EV2-017][EV2-018] |
| 6 | コストと約定可能性を保守的に置く（スプレッド・呼値・手数料・金利・貸株料、ストップ高/安で約定不可、回転率感度） | [EV2-019][EV2-021][EV2-044][EV2-054][EV2-056] |
| 7 | パラメータの頑健性を見る。最適値の近傍で成績が崩れるなら採用しない。最適化したパラメータで初めて有意になる結果は過剰適合を疑う | [EV2-048][EV2-049] |
| 8 | 期間・レジーム別の安定性を確認し、劣化を前提に停止基準を決める | [EV2-014][EV2-016][EV2-023][EV2-024][EV2-045][EV2-051] |
| 9 | 点推定でなく不確実性で読む（信頼区間、系列相関・非正規性を考慮したシャープ比、ドローダウン） | [EV2-025][EV2-026] |
| 10 | 経済的・微細構造的な理由と、買い持ち・単純ルールとの比較を求める。MLは特徴量・ラベルのリークとLLMの先読みを点検する。少額・短期の前向き検証を経てから拡大する | [EV2-040][EV2-041][EV2-064][EV2-065][EV2-066][EV2-067][EV2-068] |

## 7. 未検証だが重要な文献（⚠M）

この節の文献は筆者の記憶に基づき、今回の検索では固有レコードを確認していない。URLは記載しない。引用前に一次文献で確認すること。

- [EV2-071]: パージ/エンバーゴ付きCVなど、時系列ML検証の標準的な参照先。A節のウォークフォワード行で言及。
- [EV2-072]、[EV2-073]: 過去価格・出来高が情報を含むとする合理的モデル。B節で言及。
- [EV2-074]: 含み益・含み損の保有者行動とモメンタム。処分効果と価格帯別の売り圧力を結ぶ文献として重要。
- [EV2-075]: 機械学習による資産価格予測の基準文献。D節で言及。
- 参考: Jegadeesh-Titman型モメンタム、Lo他（2000）のパターン認識、Moskowitz他の時系列モメンタム等の核心文献は ../03_evidence/01_academic_literature.md を参照（本稿では重複しない）。

## 関連文書

- [学術的エビデンス（核心文献）](./01_academic_literature.md)
- [東証の制度とチャートへの影響](../02_japan/04_tse_market_rules_and_chart_effects.md)
- [需給指標（投資部門別売買動向・信用取引等）](../02_japan/05_supply_demand_indicators.md)
- [酒田五法・日本のローソク足](../02_japan/01_sakata_gohou.md)
- [一目均衡表](../02_japan/02_ichimoku_kinko_hyo.md)
- [移動平均線全般](../01_techniques/06_moving_averages.md)
- [バックテストフレームワーク](../05_tools_data_code/05_backtesting_frameworks.md)
- [データソース](../05_tools_data_code/02_data_sources.md)

## この文書の限界

- 根拠は検索で得た書誌・要旨のみで、全文は未読である。✅Sは存在と書誌・要旨の整合の確認を意味し、数値は各論文の報告値を独立に再現したものではない。
- WebSearchは呼び出し上限により実行できず、Elicitは契約上APIが使えなかった。日本語文献は 2026-11-11 に CiNii・J-STAGE で抄録まで確認した（[03_japanese_literature.md](03_japanese_literature.md)）が、本文は読んでいない。
- 年はレコード上の日付（ワーキングペーパー日付を含む）で、掲載年と異なる場合がある（出典表のメモ参照）。Consensusレコードの URL は、追跡用クエリ文字列（?utm_source=...）を除いて記載した。一部レコードは要旨欄が欠落・不整合（Shefrin-Statmanは無関係な内容、George-Hwang 2004は著者欄なし）。
- 日本の制度の現行値（値幅制限・呼値・売買単位）は、2026-11-11 に JPX の公式ページで確認した（[JPX の一次資料](../08_primary_sources/01_jpx_primary.md)）。制度は変わるので、売買前に最新を確認すること。
- 「チャートとの接点」「チャートへの含意」とした記述のうち論文が直接検証していないものは、筆者の仮説または一般知識でありエビデンスではない。
- ⚠Mの文献はメモリ由来で未検証。式（Lo 2002の系列相関補正）も記憶に基づく。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| EV2-001 | A Reality Check for Data Snooping | H. White | 2000 | https://consensus.app/papers/details/f4c4bac11d4b5a55ab4f28e06a668038/ | ✅S | Econometrica／DOI:10.1111/1468-0262.00152／被引1894 |
| EV2-002 | Data‐Snooping, Technical Trading Rule Performance, and the Bootstrap | Ryan Sullivan, A. Timmermann, H. White | 1999 | https://consensus.app/papers/details/d44e019194235c9e94e158ebd482f2a1/ | ✅S | JF／DOI:10.1111/0022-1082.00163／被引1105 |
| EV2-003 | Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | W. Brock, J. Lakonishok, B. LeBaron | 1992 | https://consensus.app/papers/details/4c4ec203508c5f0e98178eb373930446/ | ✅S | JF／DOI:10.1111/j.1540-6261.1992.tb04681.x／被引2439 |
| EV2-004 | A Test for Superior Predictive Ability | P. Hansen | 2005 | https://consensus.app/papers/details/9decc6f21ba757f5a549d9b90a77a380/ | ✅S | JBES／DOI:10.1198/073500105000000063／被引1308 |
| EV2-005 | Stepwise Multiple Testing as Formalized Data Snooping | Joseph P. Romano, Michael Wolf | 2005 | https://consensus.app/papers/details/8e614eeb00e65926b9b05fb5db5d767d/ | ✅S | Econometrica（他記録の引用）／被引939／記録の年欄はN/A；年は別記録(Hsu他2010 JEF要旨)の引用による |
| EV2-006 | Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs | P. Bajgrowicz, O. Scaillet | 2012 | https://consensus.app/papers/details/132354490e9a5a0a9fecaa045a94b6b0/ | ✅S | JFE／DOI:10.1016/j.jfineco.2012.06.001／被引199 |
| EV2-007 | … and the Cross-Section of Expected Returns | Campbell R. Harvey, Yan Liu, He-Yan Zhu | 2015 | https://consensus.app/papers/details/3568af295ac75e38b7e082106da51311/ | ✅S | RFS／DOI:10.1093/rfs/hhv059／被引195／記録日付2015-10-09 |
| EV2-008 | Backtesting | Campbell R. Harvey, Yan Liu | 2015 | https://consensus.app/papers/details/26c79e6752075f64842d5bd2e1a67f72/ | ✅S | JPM／DOI:10.3905/jpm.2015.42.1.013／被引123 |
| EV2-009 | Anomalies and False Rejections | T. Chordia, Amit Goyal, Alessio Saretto | 2020 | https://consensus.app/papers/details/1d8418a8125a5f258abb205a4bc0658e/ | ✅S | RFS／DOI:10.1093/rfs/hhaa018／被引116 |
| EV2-010 | The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality | David H. Bailey, Marcos M. López de Prado | 2014 | https://consensus.app/papers/details/378afd063fd15487a4fcb21af0850767/ | ✅S | JPM／DOI:10.3905/jpm.2014.40.5.094／被引191 |
| EV2-011 | The probability of back-test over-fitting | David H. Bailey, J. Borwein ほか | 2016 | https://consensus.app/papers/details/f5ef21e8509b544fba76ccc9aa2de55c/ | ✅S | DOI:10.2139/ssrn.2326253／被引114／記録日付2016-09-19 |
| EV2-012 | Quantifying Backtest Overfitting in Alternative Beta Strategies | Antti Suhonen, Matthias Lennkh, Fabrice Perez | 2017 | https://consensus.app/papers/details/df15834241b85f16a52df4f546753386/ | ✅S | JPM／DOI:10.3905/jpm.2017.43.2.090／被引26 |
| EV2-013 | All That Glitters Is Not Gold: Comparing Backtest and Out-of-Sample Performance on a Large Cohort of Trading Algorithms | Thomas V. Wiecki, Andrew Campbell ほか | 2016 | https://consensus.app/papers/details/cbf1b88914f55668987babb345905af4/ | ✅S | J Investing／DOI:10.3905/joi.2016.25.3.069／被引20 |
| EV2-014 | Does Academic Research Destroy Stock Return Predictability | R. D. McLean, Jeffrey E. Pontiff | 2016 | https://consensus.app/papers/details/91c15861c4fc5b96bc84c44174fcd8ec/ | ✅S | JF／DOI:10.1111/jofi.12365／被引909 |
| EV2-015 | Replicating Anomalies | Ke-Wei Hou, Chen Xue, Lu Zhang | 2018 | https://consensus.app/papers/details/3e48cf703b9a5de2b2629125e0be1143/ | ✅S | RFS／DOI:10.1093/rfs/hhy131／被引875 |
| EV2-016 | Anomalies across the globe: Once public, no longer existent? | Heiko Jacobs, Sebastian Müller | 2020 | https://consensus.app/papers/details/eae18571c78b55a8b4cc1738688b7200/ | ✅S | JFE／DOI:10.2139/ssrn.2816490／被引177 |
| EV2-017 | Survivorship Bias in Performance Studies | S. J. Brown, W. Goetzmann ほか | 1992 | https://consensus.app/papers/details/94e72b165d1952e0b49c510652434499/ | ✅S | RFS／DOI:10.1093/rfs/5.4.553／被引1129 |
| EV2-018 | The Delisting Bias in CRSP Data | Tyler Shumway | 1997 | https://consensus.app/papers/details/8a726f253774536482f55e4e75289a3a/ | ✅S | JF／DOI:10.1111/j.1540-6261.1997.tb03818.x／被引1146 |
| EV2-019 | A Taxonomy of Anomalies and Their Trading Costs | Robert Novy-Marx, Mihail Velikov | 2014 | https://consensus.app/papers/details/d5f3ed8437095786b3fdcf577c257df9/ | ✅S | RFS（DOIより）／DOI:10.1093/rfs/hhv063／被引553 |
| EV2-020 | Trading Costs of Asset Pricing Anomalies | Andrea Frazzini, Ronen Israel, Tobias J. Moskowitz | 2012 | https://consensus.app/papers/details/e6cee44c314c5c0aa8e74b1abee0d672/ | ✅S | DOI:10.2139/ssrn.2294498／被引242 |
| EV2-021 | The Illusory Nature of Momentum Profits | David A. Lesmond, Michael J. Schill, Chunsheng Zhou | 2004 | https://consensus.app/papers/details/2340bdf0853c5a89b49ae32192013ddd/ | ✅S | JFE／DOI:10.1016/s0304-405x(03)00206-x／被引693 |
| EV2-022 | The Adaptive Markets Hypothesis | Andrew W. Lo | 2004 | https://consensus.app/papers/details/37573e2816675d48a98f3aab3609966c/ | ✅S | （誌名は記録に無し／DOI接頭辞はJPM）／DOI:10.3905/jpm.2004.442611／被引1531 |
| EV2-023 | The Adaptive Markets Hypothesis: Evidence from the Foreign Exchange Market | Christopher J. Neely, Paul A. Weller, Joshua M. Ulrich | 2009 | https://consensus.app/papers/details/1c51f2f28e7a55f480e812bc901aa04c/ | ✅S | JFQA／DOI:10.1017/s0022109009090103／被引268 |
| EV2-024 | Technical Trading: Is it Still Beating the Foreign Exchange Market? | Po-Hsuan Hsu, M. Taylor, Zi-Gan Wang | 2016 | https://consensus.app/papers/details/01d0500bc8875edc9b296433f6301a37/ | ✅S | JIE／DOI:10.1016/j.jinteco.2016.03.012／被引91 |
| EV2-025 | The Statistics of Sharpe Ratios | Andrew W. Lo | 2002 | https://consensus.app/papers/details/ae10105da6315c3da6ea60251ec0b456/ | ✅S | FAJ／DOI:10.2469/faj.v58.n4.2453／被引802 |
| EV2-026 | Robust Performance Hypothesis Testing with the Sharpe Ratio | Olivier Ledoit, Michael Wolf | 2008 | https://consensus.app/papers/details/86e0717f26b85e2daaaa5f62ba4fce77/ | ✅S | JEF／DOI:10.1016/j.jempfin.2008.03.002／被引929 |
| EV2-027 | A note on the validity of cross-validation for evaluating autoregressive time series prediction | C. Bergmeir, Rob J Hyndman, Bonsoo Koo | 2018 | https://consensus.app/papers/details/fe5093b7ccba53cf812ebbb5a7505e42/ | ✅S | CSDA／DOI:10.1016/j.csda.2017.11.003／被引758 |
| EV2-028 | Novel insights into the modeling financial time-series through machine learning methods: Evidence from the cryptocurrency market | M. Khosravi, Majid Mirzaee Ghazani | 2023 | https://consensus.app/papers/details/9cf23248bbba51279421617df132de0e/ | ✅S | ESWA／DOI:10.1016/j.eswa.2023.121012／被引23 |
| EV2-029 | The disposition to sell winners too early and ride losers too long | H. Shefrin, M. Statman | 1985 | https://consensus.app/papers/details/27df25b96d0d5a5f8a5d3abcd4198f17/ | ✅S | （誌名は記録に無し／DOIはJF）／DOI:10.1111/j.1540-6261.1985.tb05002.x／被引2170／記録の要旨欄は無関係な内容のため不採用・書誌のみ利用 |
| EV2-030 | Are Investors Reluctant to Realize Their Losses | T. Odean | 1998 | https://consensus.app/papers/details/0a000b2e6f935848916b78f445f32894/ | ✅S | JF／DOI:10.2139/ssrn.94142／被引3457／記録は1996-11のSSRN版。公刊年は別記録の要旨が「Odean [1998]」（pp.1775）と引用していることから1998 |
| EV2-031 | Are Investors Really Reluctant to Realize their Losses? Trading Responses to Past Returns and the Disposition Effect | Itzhak Ben-David, D. Hirshleifer | 2012 | https://consensus.app/papers/details/af4cb2bd08c65be8a91940fda02169cd/ | ✅S | RFS／DOI:10.2139/ssrn.1876594／被引314 |
| EV2-032 | The 52-Week High and Momentum Investing | T. J. George, C. Hwang | 2004 | https://consensus.app/papers/details/d21da47677dd500882783af64c01a0f0/ | ✅S | 記録は題名のみ・著者欄なし；著者は他記録の要旨内の引用(JF 59, 2145-2176)で確認 |
| EV2-033 | The 52-Week High Momentum Strategy in International Stock Markets | Ming Liu, Qian-Qiu Liu, Tongshu Ma | 2011 | https://consensus.app/papers/details/6c909a4ac6095a66a61d713ad0d10c62/ | ✅S | JIMF／DOI:10.2139/ssrn.1364566／被引115 |
| EV2-034 | All that Glitters: The Effect of Attention and News on the Buying Behavior of Individual and Institutional Investors | Brad M. Barber, T. Odean | 2008 | https://consensus.app/papers/details/80a44688a7a55b9ba0dc8e55727c1739/ | ✅S | RFS／DOI:10.1093/rfs/hhm079／被引4607 |
| EV2-035 | Positive Feedback Investment Strategies and Destabilizing Rational Speculation | J. B. De Long, A. Shleifer ほか | 1990 | https://consensus.app/papers/details/915715911da35e44a39fd47d11d5ee9d/ | ✅S | JF（DOIより）／DOI:10.1111/j.1540-6261.1990.tb03695.x／被引2657／記録日付1989-03／DOIは1990年のJF号を示す |
| EV2-036 | A Unified Theory of Underreaction, Momentum Trading and Overreaction in Asset Markets | Harrison G. Hong, Jeremy C. Stein | 1999 | https://consensus.app/papers/details/f26c79dc7da85aec9edc036be97af9da/ | ✅S | JF／DOI:10.1111/0022-1082.00184／被引4230 |
| EV2-037 | A Model of Investor Sentiment | N. Barberis, A. Shleifer, R. Vishny | 1998 | https://consensus.app/papers/details/f43d050806495d0e9333d9570bc7bc6a/ | ✅S | NBER WP（DOIより）／DOI:10.3386/w5926／被引5412／記録はNBER WP w5926（1997-02）。公刊年1998（JFE）は記憶によるもので、今回のツール結果では未確認 |
| EV2-038 | A Theory of Overconfidence, Self-Attribution, and Security Market Under- and Over-reactions | Kent D. Daniel, David A. Hirshleifer, A. Subrahmanyam | 1998 | https://consensus.app/papers/details/1a4f620befe55e50af41b0645925c6ba/ | ✅S | SSRN WP／DOI:10.2139/ssrn.2017／被引359／記録は1997-02のSSRN版。公刊年は別記録の要旨が「Daniel, Hirshleifer, and Subrahmanyam (1998)」と引用していることから1998 |
| EV2-039 | Does the Stock Market Overreact | Werner F. M. de Bondt, R. Thaler | 1985 | https://consensus.app/papers/details/a1086de13dbf5aba972f90c2d98f9b4c/ | ✅S | JF／DOI:10.1111/j.1540-6261.1985.tb05004.x／被引7512 |
| EV2-040 | Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis | C. Osler | 2003 | https://consensus.app/papers/details/5b50677bb3085b2c9867db15f6dbca0c/ | ✅S | JF／DOI:10.1111/1540-6261.00588／被引220 |
| EV2-041 | Technical Analysis and Liquidity Provision | K. A. Kavajecz, E. R. Odders-White | 2004 | https://consensus.app/papers/details/64b0781eaca052bea873858414422122/ | ✅S | RFS／DOI:10.2139/ssrn.315660／被引109 |
| EV2-042 | Price Trends and Patterns in Technical Analysis: A Theoretical and Empirical Examination | Geoffrey C. Friesen, P. Weller, Lee M. Dunham | 2009 | https://consensus.app/papers/details/5d7400fe0d2354dfb22d91347292f61f/ | ✅S | JBF／DOI:10.1016/j.jbankfin.2008.12.010／被引87 |
| EV2-043 | Profits on technical trading rules and time-varying expected returns: evidence from Pacific-Basin equity markets | Akitoshi Ito | 1999 | https://consensus.app/papers/details/8ec3c00e746659c6a74ab74bbf18f7eb/ | ✅S | PBFJ／DOI:10.1016/s0927-538x(99)00008-6／被引74 |
| EV2-044 | The profitability of technical trading rules in the Asian stock markets | H. Bessembinder, Ka-Lok Chan | 1995 | https://consensus.app/papers/details/586f0e91ff845be6b507563b6e72b92b/ | ✅S | PBFJ／DOI:10.1016/0927-538x(95)00002-3／被引344 |
| EV2-045 | How exactly do markets adapt? Evidence from the moving average rule in three developed markets | Andrew Urquhart, Bartosz Gebka, Robert Hudson | 2015 | https://consensus.app/papers/details/2eb8bd967e40572a8cb6f4860dcf56d5/ | ✅S | JIFMIM／DOI:10.1016/j.intfin.2015.05.019／被引47 |
| EV2-046 | Are candlestick technical trading strategies profitable in the Japanese equity market? | Ben R. Marshall, M. Young, Rochester H. Cahan | 2008 | https://consensus.app/papers/details/6196561e6d985d26a28c5e1322a2d14b/ | ✅S | RQFA／DOI:10.1007/s11156-007-0068-1／被引65 |
| EV2-047 | Intraday technical analysis of individual stocks on the Tokyo Stock Exchange | Ryuichi Yamamoto | 2012 | https://consensus.app/papers/details/df09898edea45fc9afa00af0b4857dd7/ | ✅S | JBF／DOI:10.1016/j.jbankfin.2012.07.006／被引59 |
| EV2-048 | Improving MACD Technical Analysis by Optimizing Parameters and Modifying Trading Rules: Evidence from the Japanese Nikkei 225 Futures Market | Byung-Kook Kang | 2021 | https://consensus.app/papers/details/f9f61a9d14375108891176b0d248baef/ | ✅S | JRFM（DOIより）／DOI:10.3390/jrfm14010037／被引28 |
| EV2-049 | The profitability of Ichimoku Kinkohyo based trading rules in stock markets and FX markets | Shangkun Deng, Haoran Yu ほか | 2020 | https://consensus.app/papers/details/d9bbe7afb93d5f84bdbca05a0090b10c/ | ✅S | Int J Finance & Economics／DOI:10.1002/ijfe.2067／被引21 |
| EV2-050 | Momentum in Japan: The Exception that Proves the Rule | Cliff Asness | 2011 | https://consensus.app/papers/details/443b93e7aae157f193de4af4f8d5f98f/ | ✅S | JPM／DOI:10.3905/jpm.2011.37.4.067／被引38 |
| EV2-051 | Is Japan Different? Evidence on Momentum and Market Dynamics | M. Hanauer | 2014 | https://consensus.app/papers/details/fbc619bfd09453a4b0de4f270763e96a/ | ✅S | IRF／DOI:10.1111/irfi.12024／被引44 |
| EV2-052 | Momentum, Legal Systems and Ownership Structure: An Analysis of Asian Stock Markets | Andy C. W. Chui, S. Titman, K. Wei | 2000 | https://consensus.app/papers/details/c67ec7de76f0555a9e80fea5f15e20af/ | ✅S | DOI:10.2139/ssrn.265848／被引280 |
| EV2-053 | Sources of contrarian profits in the Japanese stock market | Pin-Huang Chou, K. C. John Wei, Hui-Min Chung | 2007 | https://consensus.app/papers/details/71770209cb265b8eb54818a53eafe58e/ | ✅S | JEF／DOI:10.1016/j.jempfin.2006.07.003／被引95 |
| EV2-054 | Price Limit Performance: Evidence from the Tokyo Stock Exchange | Kenneth A. Kim, S. Rhee | 1997 | https://consensus.app/papers/details/8c8e923f44ef5acfbf367b5e7139a7d7/ | ✅S | JF／DOI:10.1111/j.1540-6261.1997.tb04827.x／被引378 |
| EV2-055 | Transitory Price Changes and Price-Limit Rules: Evidence from the Tokyo Stock Exchange | Thomas J. George, C. Hwang | 1995 | https://consensus.app/papers/details/56b65c741ea15c729b211221619ea264/ | ✅S | JFQA／DOI:10.2307/2331123／被引79 |
| EV2-056 | Tick size change and liquidity provision on the Tokyo Stock Exchange | Hee-Joon Ahn, Jun Cai ほか | 2007 | https://consensus.app/papers/details/e10295a4816750f3b2b0e2046b7541b7/ | ✅S | J Japanese & Int'l Economies／DOI:10.1016/j.jjie.2005.10.008／被引48 |
| EV2-057 | Investment patterns and performance of investor groups in Japan | Akiko Kamesaka, J. Nofsinger, H. Kawakita | 2003 | https://consensus.app/papers/details/18f011d4f2765f7b96f11f7b2a1bd40e/ | ✅S | PBFJ／DOI:10.1016/s0927-538x(02)00095-1／被引133 |
| EV2-058 | How do Individual, Institutional, and Foreign Investors Win and Lose in Equity Trades? Evidence from Japan | Kee-Hong Bae, Takeshi Yamada, Keiichi Ito | 2008 | https://consensus.app/papers/details/bf02d0e49923548099954376a2be3392/ | ✅S | IRF／DOI:10.1111/j.1468-2443.2007.00062.x／被引33 |
| EV2-059 | Contrarian Trades and Disposition Effect: Evidence from Online Trade Data | Hayato Komai, R. Koyano, Daisuke Miyakawa | 2018 | https://consensus.app/papers/details/a84964734c805d8e805984204a82f613/ | ✅S | SSRNプレプリント／DOI:10.2139/ssrn.3109297／被引4 |
| EV2-060 | The Calendar Structure of the Japanese Stock Market: The ‘Sell in May Effect’ Versus the ‘Dekansho-Bushi Effect’ | S. Sakakibara, Takashi Yamasaki, Katsuhiko Okada | 2013 | https://consensus.app/papers/details/9937518d7d945a27ad20832b6f67f31a/ | ✅S | IRF／DOI:10.1111/irfi.12003／被引17 |
| EV2-061 | (Re‐)Imag(in)ing Price Trends | Jingwen Jiang, Bryan T. Kelly, D. Xiu | 2023 | https://consensus.app/papers/details/0944e0cb8c43532e9b3712bdbf7e4f64/ | ✅S | JF／DOI:10.1111/jofi.13268／被引80 |
| EV2-062 | The Predictive Power of Head-and-Shoulders Price Patterns in the U.S. Stock Market | G. Savin, P. Weller, Jānis Zvingelis | 2006 | https://consensus.app/papers/details/7a285e34a0865f7e92d28420a77d71b7/ | ✅S | JFEC／DOI:10.1093/jjfinec/nbl012／被引73 |
| EV2-063 | Deep learning with long short-term memory networks for financial market predictions | Thomas G. Fischer, Christopher Krauss | 2017 | https://consensus.app/papers/details/b41811acd90b5298b24503e5d10e2ece/ | ✅S | EJOR／DOI:10.1016/j.ejor.2017.11.054／被引2735 |
| EV2-064 | Stock market trend prediction using deep neural network via chart analysis: a practical method or a myth? | Erfan Radfar | 2025 | https://consensus.app/papers/details/14e2bb6eaa4159c598fa165effa7b795/ | ✅S | HSSC／DOI:10.1057/s41599-025-04761-8／被引15 |
| EV2-065 | Leakage and the reproducibility crisis in machine-learning-based science | Sayash Kapoor, Arvind Narayanan | 2023 | https://consensus.app/papers/details/f7b850c06abb58db8d431f9ce35d007c/ | ✅S | Patterns／DOI:10.1016/j.patter.2023.100804／被引1502 |
| EV2-066 | Hidden Leaks in Time Series Forecasting: How Data Leakage Affects LSTM Evaluation Across Configurations and Validation Strategies | Salma Albelali, Moataz Ahmed | 2025 | https://consensus.app/papers/details/150a8d1c3bbf54fc8573652b2df8568c/ | ✅S | arXiv／DOI:10.48550/arxiv.2512.06932／被引10 |
| EV2-067 | Assessing Look-Ahead Bias in Stock Return Predictions Generated by GPT Sentiment Analysis | P. Glasserman, Caden Lin | 2023 | https://consensus.app/papers/details/beaf2b42d3315951a7601fd1c1ee7c5a/ | ✅S | DOI:10.48550/arxiv.2309.17322／被引58／記録の題名は末尾が「Analy…」と途中で切れており「Analysis」と補った |
| EV2-068 | Spurious Predictability in Financial Machine Learning | S. Nikolopoulos | 2026 | https://consensus.app/papers/details/340ed2f9a00a5a10ab678bbc4b70c4eb/ | ✅S | DOI:10.48550/arxiv.2604.15531／被引1 |
| EV2-069 | Deep Learning for Forecasting Stock Returns in the Cross-Section | Masaya Abe, Hideki Nakayama | 2018 | https://consensus.app/papers/details/c6526d12bc915f10bc14ab46fd217143/ | ✅S | arXivプレプリント／DOI:10.48550/arxiv.1801.01777／被引103 |
| EV2-070 | Machine Learning Goes Global: Cross-Sectional Return Predictability in International Stock Markets | Nusret Cakici, C. Fieberg ほか | 2023 | https://consensus.app/papers/details/bea44f90dacc508887194dda3b9609c8/ | ✅S | JEDC／DOI:10.1016/j.jedc.2023.104725／被引27 |
| EV2-071 | Advances in Financial Machine Learning | M. López de Prado | 2018 | — | ⚠M | 書籍(Wiley)。パージ/エンバーゴ付きCV等の出典として想起。書誌は記憶のみ |
| EV2-072 | On technical analysis | D. P. Brown, R. H. Jennings | 1989 | — | ⚠M | RFS。過去価格が情報を持つ合理的モデル。記憶のみ |
| EV2-073 | Market statistics and technical analysis: the role of volume | L. Blume, D. Easley, M. O'Hara | 1994 | — | ⚠M | JF。出来高が情報を持つ合理的モデル。記憶のみ |
| EV2-074 | Prospect theory, mental accounting, and momentum | M. Grinblatt, B. Han | 2005 | — | ⚠M | JFE。含み益/含み損の保有者行動とモメンタム。記憶のみ |
| EV2-075 | Empirical asset pricing via machine learning | S. Gu, B. Kelly, D. Xiu | 2020 | — | ⚠M | RFS。ML資産価格の基準文献として想起。記憶のみ |
