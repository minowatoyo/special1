# チャートパターン辞典：反転型・継続型の定義、測定目標、統計、検出アルゴリズム
> 要約: ヘッド・アンド・ショルダーズ、ダブルトップ／ボトム、トライアングル、フラッグ、カップ・ウィズ・ハンドル等を、形成条件・確認・測定目標・出来高・失敗パターンの表にまとめた。
> Bulkowskiの統計は検索結果で確認できた数値のみを、定義と版の違いとともに示した。学術検証（Lo–Mamaysky–Wang等）では、パターンに一部の条件付き情報はあるが小さく、市場・期間・定義に依存する。
> ジグザグ閾値とカーネル回帰による検出アルゴリズムのヒントも載せた。
> 最終更新: 2026-11-09

表記: `[TS-nnn]` は出典ID。「通説」は教科書的説明で検証未了、⚠Mは記憶に基づく。

## 1. 読み方の前提
- パターンは、(a) 先行トレンド、(b) スイング点で定義される形、(c) 境界（ネックライン等）の終値ブレイクによる確認、(d) 測定目標（形の高さの投影）で構成される。測定目標の考え方はEdwards & Magee[TS-004]やMurphy[TS-027]に遡る。
- 反転型・継続型の区別は事前の傾向にすぎず、トライアングルやレクタングルはどちらにも抜ける。確認前に方向を決め打ちしない。
- Bulkowskiの「失敗」は、ブレイクアウト後に目標方向へ約5%動けないこと（検索要約）で、「パターンが外れた」より緩い定義である。成功率の数字は定義に強く依存する（→§4）。

## 2. 反転型カタログ
| パターン | 形成条件 | 確認 | 測定目標 | 出来高 | 失敗・注意 |
|---|---|---|---|---|---|
| ヘッド・アンド・ショルダーズ天井（H&S、三尊天井） | 上昇後、左肩・頭（最高）・右肩（頭より低く左肩と同程度）の3山。谷2点を結ぶネックライン[TS-041] | ネックラインの終値割れ。右下がりのネックラインでは右脇（右肩手前の谷）割れで成立とするBulkowskiの基準[TS-045] | 頭〜ネックラインの高さをブレイク点から下へ。高さに目標達成率（51%）を掛けて割り引く流儀もある[TS-045] | 右肩で減少、割れで増加が理想（通説） | 割れ後の戻り（プルバック）が68%の標本で発生[TS-045]。割れ前の先回り売りは失敗しやすい |
| 逆H&S（逆三尊） | 下降後の逆形 | ネックライン上抜け | 同上（上方向） | 右肩の反発と上抜けで増加が重要（通説） | 出来高を伴わない上抜けはダマシが多いとされる（通説） |
| ダブルトップ | 2つの山が同水準で、第2の山が第1を超えない。中間の谷を割ると完成[TS-040] | 中間の谷（ネック）の終値割れ | 山〜谷の高さを谷から下へ | 第2の山で減少が典型（通説） | 「二番天井」で売ると上抜け（またはトリプル）に遭う。山の同水準の許容率は定義次第 |
| ダブルボトム（W底） | 逆形。尖った底(Adam)と丸い底(Eve)の組合せ分類があり、Bulkowskiは Eve & Eve が二重底中で最良と評価[TS-067] | 中間の山の終値上抜け | 谷〜山の高さを山から上へ | 第2の谷で減少、上抜けで増加（通説） | 統計は検索結果間で食い違う（平均上昇42〜50%など）ため数値は採用しない |
| トリプルトップ／ボトム | 3つの同水準の山（谷） | 谷（山）2つのうち低い（高い）方の終値割れ（超え） | 高さの投影 | 山ごとに減少（通説） | 稀。ダブルの延長として現れ、事前識別は困難 |
| ソーサー（鍋底） | 数週〜数か月の円弧状の転換 | 抵抗水準の上抜け | 弧の深さの投影（明確な規則なし） | U字（底へ減少、反発で増加）（通説） | 曲線の検出は難しい。ルール化した検証では水平抵抗がソーサーより優位[TS-059] |
| Vトップ／ボトム（スパイク反転） | 持ち合いを作らず急反転。島を含むことがあるが窓なしでも転換[TS-066] | 直前の下げ（上げ）の一定割合の回復など。確定が遅れがち | 規則なし | クライマックス出来高が多い | 事前検出が難しく、中継の一部を反転と誤認しやすい |
| アイランド・リバーサル | 消耗窓と逆向きの窓に挟まれた孤立帯（→01 §6） | 逆向きの窓の成立 | 規則なし。島の水準が支持抵抗化（通説） | 両側の窓で増加（通説） | 窓は値幅制限・権利落ちでも生じる（日本株） |
| ブロードニング（拡大型）トップ／ボトム | 高値が切り上がり安値が切り下がる拡大する値幅（メガホン型） | 下側（上側）境界の終値割れ（超え） | 最大幅の投影（通説） | 不規則 | 境界が一意に決まらず検出が恣意的。Lo–Mamaysky–Wang（LMW）の検出対象に含まれる（⚠M） |
| ダイヤモンド | 値幅拡大のあとに収束する菱形 | ネックライン（V字型）の割れ（通説） | 菱形の最大幅（通説） | 中央で多く末端で減少（通説） | 稀で統計が乏しい。検出は恣意的 |

## 3. 継続型カタログ
| パターン | 形成条件 | 確認 | 測定目標 | 出来高 | 失敗・注意 |
|---|---|---|---|---|---|
| 上昇トライアングル | 水平の抵抗＋切り上がる安値 | 抵抗の終値上抜け | 起点の最大幅を上抜け点から上へ | 収束中は減少、上抜けで増加（通説） | 強気型でも下抜けることがある。方向は確認後に判断 |
| 下降トライアングル | 水平の支持＋切り下がる高値 | 支持の終値割れ | 起点の最大幅を下へ | 同上 | 同上 |
| 対称トライアングル | 切り下がる高値と切り上がる安値が各2点以上[TS-044] | 上下どちらかの終値ブレイク | 起点の最大幅の投影 | 収束中は減少 | 反転より継続が多い[TS-044]。頂点（apex）近くのブレイクは信頼性が低い（⚠M） |
| レクタングル（ボックス） | 水平の支持・抵抗の間の持ち合い | 境界の終値ブレイク | 幅の投影 | 持ち合い中は減少（通説） | 日本の「ボックス相場」と同義。ダーバス・ボックスとは別物（→05） |
| フラッグ | 急騰落（旗竿）後の小さな逆行チャネル。数週間以内[TS-042] | 旗の境界の終値ブレイク | 旗竿の長さをブレイク点から投影 | 旗の間は減少、ブレイクで増加（通説） | 統計は§4。旗竿の定義（何%・何日）が結果を左右する |
| ペナント | 旗竿後の小さな対称三角形[TS-042] | 境界の終値ブレイク | 旗竿の長さの投影 | 同上 | 統計は§4 |
| ウェッジ（上昇／下降） | 2本の線が同方向に傾きつつ収束 | 境界の終値ブレイク | 起点まで戻る（慣行） | 収束で減少（通説） | 上昇ウェッジは弱気、下降ウェッジは強気に抜けやすいとされるが、統計は検索結果間で食い違い採用しない |
| カップ・ウィズ・ハンドル | U字のカップ後に浅い押し（ハンドル）。カップの調整は直前上昇の1/3以下が理想、ハンドルは1〜4週間程度[TS-043] | ハンドル高値（ピボット）の上抜け | カップの深さの投影（慣行）。実績は§4 | ハンドルで枯れ、上抜けで急増（O'Neil流） | 深いカップ・長いハンドルは失敗しやすい（通説）。ダマシ率は市場局面に依存 |

## 4. 統計と成功率の読み方
Bulkowskiのサイトに現れた数値のみ。強気相場、ブレイクアウト方向別、米国株、過去の目視抽出パターンの集計である。

| パターン | 失敗率 | 平均値幅 | 目標達成 | 備考 |
|---|---|---|---|---|
| H&S天井 | 19% | 下落16% | 51% | プルバック率68%、総合順位9/36、統計更新2020年8月。旧版の記載は4%・22%・55%・順位1/21[TS-045] |
| カップ・ウィズ・ハンドル | 5% | 上昇54% | 61% | スローバック率62%、総合順位3/39[TS-046]。別資料に7%・23%等の異なる数値もある |
| フラッグ | 上44%／下45% | 9%／8% | 46% | 順位対象外[TS-047] |
| ペナント | 54%（上下とも） | 7%（上）／6%（下） | — | 順位対象外、統計更新2020年8月[TS-048] |
- 数字の読み方: (1)失敗率は「ブレイク後に約5%動けない割合」で勝率や期待値ではない。「成功率95%」という表現は失敗率5%の言い換えとして流布したものとみられ、勝率ではない。(2)パターンは後から目視で拾われており、事後的選別バイアスの可能性が残る。(3)版・更新日で数値が変わる（確認日: 2026-11-09、要確認）。第2版に63パターンの統計があるとサイトは記載する[TS-050]。日本株での同種集計は本調査では未確認。
- 運用上の含意: H&S天井のプルバック率68%は、戻りを待つ指値エントリーだと約3割は戻らず取り逃がす計算になる（標本・定義の限界つきの単純な算術）。待つか追うかは損切り幅と期待値で決める。

**学術検証**
| 研究 | 対象 | 結果 |
|---|---|---|
| LMW（Lo–Mamaysky–Wang）2000[TS-051] | 米国株1962〜1996、カーネル回帰で5組（H&S、拡大型、三角形、長方形、ダブル：⚠M）を機械検出 | 条件付き収益分布は無条件と異なり、いくつかは追加情報を持ち得る。最頻はダブルトップ／ボトム、次いでH&S[TS-052] |
| Savin他 2006[TS-053] | S&P500・Russell2000 1990〜99、H&S | 単独の売買戦略は支持乏しいが超過収益への予測力は強い。パターン条件付き戦略のリスク調整超過収益は年5〜7%、市場ポートフォリオとの併用で同リスクでの超過収益が有意に増加 |
| Osler & Chang 1995[TS-054] | 為替日次1973〜94、H&Sを機械検出 | ブートストラップ10,000系列と比較（結果は未確認） |
| Lucke 2003[TS-055] | 為替、H&Sルール | 収益は有意に正でなく、非ゼロならむしろ負 |
| Dawson & Steeley 2003[TS-056] | 英国FTSE100／250 1986〜2001 | 英国株はパターンの影響が米国より小さい |
| Friesen他 2009[TS-057] | 理論モデル | 確証バイアスがH&S・ダブルトップ型を生み、価格ジャンプの正の自己相関を確認 |
| Zapranis & Tsinaslanidis 2012[TS-059] | 米国ハイテク7銘柄、ソーサー | 水平抵抗がソーサーに勝り、超過収益は後期に減衰 |
| Cervelló-Royo他 2015／Arévalo他 2017[TS-060][TS-061] | DJIA日中データ、フラッグ | トレンドフィルタと損失制限付きのルールで良好な結果を報告（日中・単一指数） |
総括: 一部のパターンに条件付きの情報はあるが、効果は小さく、定義・市場・期間に依存し、費用控除後の収益は安定しない（総覧は[TS-028]）。

**損切り・目標の置き方（通説。数値は設計例）**
| パターン | 損切り | 目標 |
|---|---|---|
| H&S／ダブル／トリプル | 右肩（第2の山）の外側、またはネックライン回復 | 形の高さの投影。到達率は§4の通り限定的 |
| トライアングル／レクタングル | 反対側の境界の外、または収束内の直近スイングの外 | 起点の最大幅／幅の投影 |
| フラッグ／ペナント | 旗の反対側の端、または旗竿の半値戻し | 旗竿の長さの投影 |
| カップ・ウィズ・ハンドル | ハンドルの安値の下（O'Neilは購入価格から数%での損切りを推奨と記憶、数値は⚠M） | カップの深さ（慣行） |
| 共通 | 「形の無効化水準」と「エントリー±k×ATR（k=2〜3）」の厳しい方 | R倍数（損切り幅の何倍か）で管理し、部分利確を併用 |

## 5. 検出アルゴリズムのヒント
1. 方式: (a)確認済みピボット列（→01 §2）にルールを当てる、(b)平滑化して極値を抽出しルールを当てる、(c)テンプレート照合（DTW等、⚠M）。方向転換（DC）ベースの逆H&S検出も報告がある[TS-062]。
2. ジグザグ型のH&S判定（許容率は設計例。日本株は呼値と価格帯で調整）:
```
入力: 確認済みピボット P = [H1, L1, H2, L2, H3]（高安が交互）
条件: H2 > max(H1, H3)                          # 頭が最高
      |H1 - H3| / mean(H1, H3) <= τ_s           # 両肩の高さが近い（例：3%）
      |L1 - L2| / mean(L1, L2) <= τ_n           # ネックラインの傾きを制限
      0.5 <= (H2.t - H1.t) / (H3.t - H2.t) <= 2 # 時間の対称性
確認: Close < ネックライン(t) - k*ATR           # 以降を「パターン成立」とする
目標: (H2 - ネックライン) をブレイク価格から下へ投影
```
3. カーネル回帰（Lo–Mamaysky–Wang[TS-051]）:
```
m_h(x) = Σ_t K_h(x - t) * P_t / Σ_t K_h(x - t),   K_h(z) = exp(-z^2/(2h^2)) / (h*sqrt(2π))
h = c * h_CV      # h_CV: クロスバリデーション最適値。過平滑を避けるため縮小（原論文はc=0.3、⚠M）
極値: m_h の微分の符号変化点。形は極値E1..E5の大小と近接率で定義
      例: H&S は E1が極大、E3>E1かつE3>E5、E1とE5が平均の1.5%以内（⚠M）。窓は38営業日（⚠M）
```
 平滑化は窓内の将来点を使うため、バックテストでは「確認日までのデータだけで成立するパターン」を使う。確認日をイベント日とする。
4. 評価の手順: イベント＝確認日。前方リターンを複数ホライズン（例：5・10・20・60日）で測り、同一銘柄のランダム日またはマッチした対照イベントと比較する。重複イベントはクラスタ頑健な標準誤差で処理し、費用、パラメータ探索の多重検定、期間分割（ウォークフォワード）を織り込む。勝率だけでなく損益比（R倍数）で報告する。
5. 閾値の決め方: 許容率τは価格水準でなくボラティリティ（ATRや日次σ）に比例させる。最小パターン幅（本数）と最大幅を置く。感度分析でτ・kを動かして結論が頑健か確認する。

## 6. 日本株での留意点
- 呼称: 三尊天井／逆三尊（H&S）、三角保ち合い、W底（ダブルボトム）などが通称として使われるが、資料により表記が揺れる（⚠M）。日本の証券会社によるパターン解説の例は[TS-064]。
- 値幅制限・特別気配で形が欠ける。ストップ高に張り付く日は出来高が極端に少なく、出来高条件が誤作動する。出来高は東証出来高か売買代金か、PTSを含むかを固定する。
- 低位株は呼値が相対的に粗く、許容率τが数ティック未満になり得る。τの下限を呼値の数倍に置く。
- 株式分割・権利落ちの調整（→01 §8）を行わないと、パターンの高さ・ネックラインが歪む。

## 関連文書
- 01_price_structure.md（スイング・窓・ブレイクアウト）／03_candlesticks.md／05_practitioner_frameworks.md（カップ・ウィズ・ハンドルとCAN SLIM）
- ../03_evidence/01_academic_literature.md、../03_evidence/02_methodology_behavioral_japan_ml.md

## この文書の限界
- 外部ページは開けず、検索結果の要約・論文レコード（要旨）で確認した。Bulkowskiの書籍本文、Lo他の原論文は未読。統計は版・更新日で変わる。
- 日本の証券会社資料での裏取りは名称対応（OANDA証券）のみ。日本株でのパターン統計は未確認（検索回数の上限に到達）。
- ウェッジ・トライアングル・レクタングル・ダブルボトムの統計は検索結果間で食い違うか未取得のため採用していない。
- 出来高の振る舞いと測定目標の多くは教科書的通説であり、本調査では個別に検証していない。LMWの定数（c=0.3、1.5%、38日）と頂点付近のブレイクは記憶に基づく（⚠M）。

## 出典

> 検証タグ: ✅S=検索結果・論文レコード等で書誌と要点を確認（本文は未読）／⚠M=記憶のみ／❓=要確認。URLは検索結果に現れたものだけを記載し、無いものは「—」とした。

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TS-004 | Technical Analysis of Stock Trends | Edwards, Magee（のちBassetti改訂） | 1948（初版） | — | ✅S | 書誌・目次・章要旨のみ確認 |
| TS-027 | Technical Analysis of the Financial Markets | Murphy, J. J. | 1999 | — | ⚠M | 古典（記憶） |
| TS-028 | What Do We Know About the Profitability of Technical Analysis | Park, Irwin／Journal of Economic Surveys | 2007 | — | ✅S | DOI 10.1111/j.1467-6419.2007.00519.x |
| TS-040 | ChartSchool: Chart Patterns（索引） | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns | ✅S | 索引。ダブルトップ定義はMurphy由来の記述を確認 |
| TS-041 | ChartSchool: Head and Shoulders Top | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/head-and-shoulders-top | ✅S | H&S天井の定義 |
| TS-042 | ChartSchool: Flag, Pennant | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/flag-pennant | ✅S | フラッグ／ペナントの定義 |
| TS-043 | ChartSchool: Cup With Handle | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/cup-with-handle | ✅S | カップの深さ・ハンドル期間 |
| TS-044 | ChartSchool: Symmetrical Triangle | StockCharts | — | https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/symmetrical-triangle | ✅S | 対称三角形の定義 |
| TS-045 | Head and Shoulders Top（統計） | Bulkowski／thepatternsite.com | 更新2020-08（統計） | https://thepatternsite.com/hst.html | ✅S | 強気相場の統計。旧版は数値が異なる |
| TS-046 | Cup with Handle（統計） | Bulkowski／thepatternsite.com | — | https://thepatternsite.com/cup.html | ✅S | 強気相場の統計。他サイトに別数値あり |
| TS-047 | Flags（統計） | Bulkowski／thepatternsite.com | — | https://www.thepatternsite.com/flags.html | ✅S | 強気相場の統計 |
| TS-048 | Pennants（統計） | Bulkowski／thepatternsite.com | 更新2020-08（統計） | https://thepatternsite.com/pennants.html | ✅S | 強気相場の統計 |
| TS-050 | Encyclopedia of Chart Patterns（第2版） | Bulkowski | 2005（第2版・年は記憶） | — | ✅S | 第2版に63パターンの統計があるとサイトが記載 |
| TS-051 | Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation | Lo, Mamaysky, Wang／Journal of Finance 55(4) | 2000 | https://www.nber.org/papers/w7613 | ✅S | NBER WP w7613 |
| TS-052 | CFA Digest: Foundations of Technical Analysis（要約） | CFA Institute | 2001 | https://rpc.cfainstitute.org/-/media/documents/article/cfa-digest/2001/dig-v31-n1-811-pdf.pdf | ✅S | 最頻パターンの記述 |
| TS-053 | The Predictive Power of Head-and-Shoulders Price Patterns in the U.S. Stock Market | Savin, Weller, Zvingelis／J. Financial Econometrics | 2006 | — | ✅S | DOI 10.1093/jjfinec/nbl012 |
| TS-054 | Head and Shoulders: Not Just a Flaky Pattern | Osler, Chang | 1995 | — | ✅S | DOI 10.2139/ssrn.993938（結果は未確認） |
| TS-055 | Are technical trading rules profitable? Evidence for head-and-shoulder rules | Lucke／Applied Economics | 2003 | — | ✅S | DOI 10.1080/00036840210150884 |
| TS-056 | On the Existence of Visual Technical Patterns in the UK Stock Market | Dawson, Steeley／J. Business Finance & Accounting | 2003 | — | ✅S | DOI 10.1111/1468-5957.00492 |
| TS-057 | Price Trends and Patterns in Technical Analysis: A Theoretical and Empirical Examination | Friesen, Weller, Dunham／J. Banking & Finance | 2009 | — | ✅S | DOI 10.1016/j.jbankfin.2008.12.010 |
| TS-059 | A novel, rule-based technical pattern identification mechanism: Identifying and evaluating saucers and resistant levels in the US stock market | Zapranis, Tsinaslanidis／Expert Systems with Applications | 2012 | — | ✅S | DOI 10.1016/j.eswa.2011.11.079 |
| TS-060 | Stock market trading rule based on pattern recognition and technical analysis: Forecasting the DJIA index with intraday data | Cervelló-Royo, Guijarro, Michniuk／Expert Systems with Applications | 2015 | — | ✅S | DOI 10.1016/j.eswa.2015.03.017 |
| TS-061 | A dynamic trading rule based on filtered flag pattern recognition for stock market price forecasting | Arévalo ほか／Expert Systems with Applications | 2017 | — | ✅S | DOI 10.1016/j.eswa.2017.03.028 |
| TS-062 | Using Directional Changes for Searching Head and Shoulders Bottom Pattern | Li, Tsang | 2018 | — | ✅S | 要旨未確認 |
| TS-064 | チャートパターン（フォーメーション分析）とは | OANDA証券 | — | https://www.oanda.jp/lab-education/beginners/technical_analysis/formation_analysis/ | ✅S | 代表17種の解説 |
| TS-066 | Rounding Top/Bottom・V-top/V-bottom（概念解説） | LuxAlgo（ベンダー） | — | https://www.luxalgo.com/library/concept/v-top-v-bottom.md | ✅S | V字・ラウンディングの概念解説 |
| TS-067 | Double Bottom Types（Adam & Eve分類） | Bulkowski／thepatternsite.com | — | https://thepatternsite.com/DoubleBottomTypes.html | ✅S | Adam／Eve分類 |
