# バックテスト基盤の比較と、日本株の制度に結びつく設計上の落とし穴
> 要約: backtesting.py・backtrader・vectorbt・bt・zipline-reloaded・QuantConnect LEAN・PyBroker・NautilusTrader を、方式（イベント駆動かベクトル化か）・速度・日本株への適合のしやすさ・保守状況（PyPI 実測）・ライセンスで比較した。
> Python 3.13.18＋pandas 3.1.1 のサンドボックスで backtesting.py・bt・vectorbt は動作し、zipline-reloaded は pandas<3.0 を要求した。速度は 3,000 本・1 銘柄の合成データでの参考値である。
> 後半は、先読み・約定価格・手数料とスリッページ・呼値・値幅制限・売買単位・調整後価格・多重検定を日本株の制度に結びつけて整理する。制度の詳細は 02_japan/04 を参照。取得日 2026-11-09、要再確認。
> 最終更新: 2026-11-09

## 1. 読み方

- 確認日: 2026-11-09（版・ライセンス・制度は要公式確認）。「PyPI 実測」は `https://pypi.org/pypi/<package>/json` の値。README・docstring の記述は PyPI 配布物の README と、サンドボックスに導入したパッケージのソースから読んだもの（✅S）。実行結果は本セッションのサンドボックス（Linux x86_64、4 vCPU、Python 3.13.18）での 1 回の観測である [TL-423]。
- 「日本株への適合」は本稿の判断で、根拠は表中に示した機能の有無に限る。呼値と値幅制限の組込み機能は、ソースを検索した backtesting.py・bt・vectorbt でも、README を読んだ他の基盤でも見つからなかった。売買単位に近い機能は vectorbt の `size_granularity` だけだった（未検証）。自作の層が必要になる前提で比較している。

## 2. 比較表

| 基盤 | 方式 | 速度（実測／ベンダー主張） | 日本株への適合 | 保守（PyPI 実測） | ライセンス | 出典 |
|---|---|---|---|---|---|---|
| backtesting.py | `init()` で指標をベクトル計算し `next()` を 1 本ずつ呼ぶバー駆動。1 回の `Backtest` は 1 本の OHLC(V) DataFrame が対象 | README は「Blazing fast」と主張。実測 33〜50 ms／回（3,000 本）、386 通りのループで 12.5 秒 | 成行は**次の足の始値**で約定（`trade_on_close=True` で当日終値）。`size` は 1 未満で資金比率、1 以上で株数だが**100 株の倍数には丸められない**。手数料は割合・(固定, 割合)・関数。呼値・値幅の機能は見当たらない | 0.6.6（2026-07-22）、Python>=3.9。pandas 3.1.1 で動作するが `Pandas4Warning` | AGPL-3.0（classifier は AGPLv3+）。ネットワーク提供時の扱いは法務確認 | [TL-401] |
| backtrader | イベント駆動（Cerebro）。複数データ・複数戦略・複数時間足、ブローカー模擬、スリッページ、Cheat-on-Close／Open、取引カレンダー、サイザーを README が列挙 | 未計測 | 手数料体系・サイザー・カレンダーの枠組みがあり、100 株単位などは自作 Sizer で表現できる見込み（未検証）。ライブ接続は Interactive Brokers・Oanda・Visual Chart（README） | **1.9.78.123（2023-04-19）、約 3.6 年更新なし**。Python 要件未指定 | GPLv3+ | [TL-402] |
| vectorbt | ベクトル化（NumPy／Numba、任意の Rust エンジン `vectorbt-rust`）。パラメータ掃引向け | 実測: 初回 約 4 秒（JIT）、以後 約 5 ms／回。386 通りの掃引は 2 回目 0.18 秒、初回 3.6〜5.2 秒（JIT 含む、実行ごとにばらつき） | `from_signals` は価格を渡さないと**シグナルと同じ足の終値**で約定（実測）。次足始値にするには `price=` に始値、シグナルは `shift(1)`。注文に `size_granularity`（数量の刻み。docstring: 1.0 で整数株）・`slippage`・`fixed_fees`・`min_size`／`max_size` があり、100 株刻みの指定も可能なはずだが未検証 | 1.2.0（2026-10-19）、Python>=3.11、numpy>=2.4.6・pandas>=3.0.3 | README: Apache 2.0 with Commons Clause（fair-code）。PyPI の license 欄は空。有償版 PRO は別製品 | [TL-403] |
| bt | ポートフォリオ層。Algo（実行頻度・銘柄選択・ウェイト・リバランス）を連結、戦略を木構造に入れ子可能 | 未計測 | 株数は整数に丸める（`integer_positions` 既定 True）が 100 株単位は標準にない。手数料は `fn(数量, 価格)` か、平方根型・Almgren-Chriss 型の `CostModel`（ソース記載） | 1.4.1（2026-10-10）、Python>=3.9、cp313 wheel あり | MIT | [TL-404] |
| zipline-reloaded | イベント駆動（`initialize`／`handle_data`）。データバンドルの取り込みが前提 | 未計測 | 取引カレンダーは exchange_calendars（XTKS あり）に依存。日本株のバンドルは自作。README の例は 100 株単位の `order_target` | 3.2.1（2026-10-25）、Python>=3.11。**README は保守モード（新機能は ML4T Backtest へ）**。**pandas<3.0** | Apache-2.0 | [TL-405] |
| ml4t-backtest | 概要は「設定可能な約定・会計・リスクを持つイベント駆動」。zipline-reloaded の README が新規案件での評価を推奨 | 未計測 | 未確認 | 0.2.0（2026-10-22）、Python>=3.12 | MIT | [TL-406] |
| QuantConnect LEAN | C#/.NET のエンジン＋Python API。`lean` CLI でローカル／クラウドの backtest・最適化・ライブ。多くのコマンドで Docker が必要（README） | 未計測 | CLI README の data provider／brokerage の選択肢に日本の証券会社・取引所は見当たらない。日本株データの提供有無は未確認 | `lean` 1.0.233（2026-10-27）。本体の NuGet 版は unlisted | CLI は Apache（classifier）。LEAN 本体は NuGet が LICENSE への URL のみ示す（Apache-2.0 と記憶 ⚠M） | [TL-407] [TL-408] |
| PyBroker | NumPy＋Numba の高速エンジン。ウォークフォワード、データ・指標・モデルのキャッシュ、並列化、スリッページのモデル化（README） | README は「super-fast」と主張。未計測 | 未確認 | `lib-pybroker` 2.0.2（2026-10-20）、Python>=3.11、sdist のみ | **Apache 2.0 with Commons Clause**、classifier は「Free for non-commercial use」 | [TL-409] |
| NautilusTrader | Rust 製エンジン、決定論的イベント駆動（概要） | 未計測 | 未確認 | 1.231.0（2026-08-02）、Python>=3.12,<3.15 | LGPL-3.0-or-later | [TL-410] |

- 補足（サンドボックス実測）: backtesting.py・bt・vectorbt は pandas 3.1.1／numpy 2.5.4 で合成データの最小戦略が完走した。backtesting.py は `Pandas4Warning`（`DatetimeIndex.dayofweek` の非推奨）を出し、bt と vectorbt は警告なし。zipline-reloaded は pip の dry-run で pandas 2.3.3 への降格を伴った。vectorbt と backtesting.py の約定規則は上表のとおり異なるため、速度比較は処理量の目安にとどまる。
- 周辺（PyPI 実測のみ）: vnpy 4.5.0（MIT、2026-10-06）[TL-411]、rqalpha 6.5.0（Apache-2.0、2026-10-28、sdist のみ）[TL-412]、pyqlib 0.9.7（MIT、2025-08-15、cp313 wheel なし）[TL-413]、lumibot 4.6.48（GPL-3.0、2026-11-07）[TL-414]、FinRL 0.3.7（MIT、2024-04-12）[TL-415]、fastquant 0.1.8.1（GPLv3、2023-01-04、**約 3.8 年更新なし**）[TL-416]。いずれも日本株への適合は未確認。

## 3. 選び方の目安

- **1 銘柄のルール検証・可視化**: backtesting.py（次足始値の既定が安全側）。ただし AGPL とパラメータ掃引の遅さ（約 32 ms／回）に注意。
- **数千通りのパラメータ掃引**: vectorbt。約定規則が既定でシグナル足の終値なので、先読みを自分で防ぐ。ライセンス（Commons Clause）は商用利用前に作者へ確認する（README に問い合わせ先の記載がある）。
- **多銘柄のリバランス・ローテーション**: bt。100 株丸めと呼値は自作層で補う。
- **実運用までの一貫性**: LEAN・NautilusTrader・backtrader（IB 接続）。日本の証券会社との接続は本調査では確認できず、kabuステーション API 等との接続は別途自作になる可能性が高い。
- **参照実装・照合テスト**: 依存を絞るなら次節の pandas だけの最小モデルが、挙動を完全に把握できる。ライブラリは「自作との差分確認」に使う。

## 4. 最小モデル: 次の足の始値で約定する

```python
def run(df, want, cash=1_000_000.0, lot=100, fee=0.0005, slip=0.0005):
    """df: 未調整の open/close を持つ日足。want: 当日終値までの情報で決めた 0/1 の目標。"""
    sh, eq = 0, []
    for t in range(len(df)):
        o, c = df["open"].iat[t], df["close"].iat[t]
        w = want.iat[t - 1] if t else 0           # 前日までのシグナルのみを使う（先読み防止）
        if w and sh == 0:                          # 今日の始値で買い（寄成の近似）
            p = o * (1 + slip)
            k = int(cash // (p * (1 + fee)) // lot) * lot   # 100 株単位に切り下げ
            if k:
                cash -= k * p * (1 + fee); sh = k
        elif not w and sh > 0:                     # 今日の始値で売り
            cash += sh * o * (1 - slip) * (1 - fee); sh = 0
        eq.append(cash + sh * c)                   # 終値で評価
    return pd.Series(eq, index=df.index)
# want = (close > close.rolling(25).mean()).astype(int)  # 当日終値で確定するシグナル
```

pandas 3.1.1／numpy 2.5.4 で合成データに対して実行できることを確認した（数値の妥当性の保証ではない）。呼値への丸め、値幅制限による約定不能、信用取引コストは含まれない。

## 5. 日本株の制度に結びつく設計上の落とし穴

制度の詳細・数値は [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md) と JPX の公式資料で確認すること。以下の制度面の記述は筆者の記憶に基づく（⚠M、要公式確認）[TL-424]。取引時間（2024-11 の延長）、売買単位 100 株（2018 年）、権利落ち、年末年始の休業については、同文書が公式案内等の検索結果を根拠に記している。

### 5.1 先読み（look-ahead）

- **シグナルと約定の分離**: 日足の終値で確定する条件は、早くても翌営業日の寄付、または当日の大引けの引成でしか執行できない。同日終値で約定させる設計は「終値を見てから終値で買う」ことになる。実測では vectorbt の既定がこの形（シグナル足の終値約定）だったため、`shift(1)` と `price=`（始値）で次足始値に直す。
- **調整後価格の将来情報**: 分割・併合を反映した系列は将来のイベントを含む。「株価 1,000 円以下」「売買代金」「呼値」など価格水準に依存する条件は、**当時の未調整価格**で評価する。
- **開示日の使用**: 決算・財務は期末日ではなく開示日以降に使う。決算短信は引け後に出ることが多く、反映は翌営業日以降になる（⚠M）。J-Quants V2 の README には適時開示インデックスと決算発表予定日の API が並ぶ（[02_data_sources.md](02_data_sources.md)）。
- **構成銘柄・市場区分の遡及**: 現在の日経平均・TOPIX 構成銘柄やプライム市場の銘柄を過去に遡って使うと生存者バイアスになる（2022-04 の市場区分再編をまたぐ検証に特に注意）。
- **同一足内の高安順序**: 日足では高値と安値のどちらが先か分からない。損切りと利確が同じ足で両方触れたときは損切り優先など、保守的な規則を固定する。

### 5.2 約定価格の仮定

- **寄付・引け**は板寄せ（単一価格）で決まり、寄成・引成なら始値・終値で約定する近似が成り立つ。ただし板が薄い銘柄や特別気配で寄付が遅れる日は成立しない。自分の注文が価格を動かす影響も日足モデルでは無視される。
- **取引時間の変更**: 大引けの時刻は 2024-11-05 に 15:00 から 15:30 へ延長された（後場は 12:30〜15:30。JPX の売買立会時のページで確認 [PJ-001]）。年をまたぐ出来高・終値の連続性と、15:30 以降に出る開示との前後関係が変わる点を確認する。
- **ザラ場の指値**: 高値・安値に「触れた」だけでは約定とみなさない。同値は待ち行列の後ろになるため、保守的には指値を超えて抜けた場合のみ約定とする。
- 午前終値（J-Quants V2 に `get_eq_bars_daily_am` がある）を使えば前場・後場の分離検証ができる。

### 5.3 手数料・スリッページ

- 手数料は証券会社・プランで異なり改定されるため、パラメータ化して**コストの感応度**（0〜数十 bps）で結論が反転しないか確認する。研究面でも、取引コストと流動性コストを損失関数に入れないと多重検定の制御が歪むこと [TL-422]、低い取引コストでも DJIA 1897〜2011 の技術的ルールの優位が（標本内でも）打ち消されること [TL-421] が示されている。
- スリッページは「半スプレッド（呼値）＋売買代金に対する参加率に応じた衝撃」で近似する。低位株は呼値が価格比で大きい。**売買代金の下限**をユニバース条件にする。bt 1.4.1 は平方根型・Almgren-Chriss 型のコストモデルを備える（ソースの docstring）。
- 信用取引は金利・貸株料・逆日歩、空売りの価格規制がある（⚠M）。需給と空売りは [../02_japan/05_supply_demand_indicators.md](../02_japan/05_supply_demand_indicators.md) を参照。

### 5.4 呼値・値幅制限・売買単位

- **呼値**: 価格帯ごとに刻みが決まる。逆指値・利確の価格は刻みに丸める。損切り幅を「2%」と決めても、低位株では刻みで実効幅が大きく変わる。
- **値幅制限**: 前日終値などを基準とする制限値幅があり、上限（ストップ高）・下限（ストップ安）に張り付くと約定しない。高値がストップ高で終わった日の買い、ストップ安で終わった日の売りは「約定不能日」として除外するか確率的に処理する。
- **売買単位**: 全上場銘柄が 100 株単位に統一されたと記憶する（2018 年、⚠M）。株数は `floor(資金 / (価格 × 100)) × 100` で算出し、小資金では**最低投資金額**が銘柄ユニバースの制約になる。実測と docstring のとおり、backtesting.py の `size`（1 未満）や bt の整数丸めは 100 株の倍数に揃えない。vectorbt は `size_granularity` で刻みを指定できる（docstring、100 株での動作は未検証）。

### 5.5 調整後価格・配当・上場廃止

- 価格水準を使うチャート分析は分割調整のみ、リターン評価は配当込み調整、と目的で使い分ける。yfinance は既定で配当調整済みの価格を返す（`auto_adjust=True`、README）。J-Quants の日足には調整後の列（`AdjC`・`AdjVo`）がある（README の出力例）。調整の定義（配当を含むか）は要確認。
- 配当落ち・権利落ちの日は、基準値段から落ち分が差し引かれ、制限値幅の基準も動く（例: 終値1,100円・配当落ち5円なら1,095円。東証公式株式サポーターによる [PJ-012]）。上場廃止・整理銘柄の扱いは [02_data_sources.md](02_data_sources.md) の「生存者バイアス」を参照。

### 5.6 ウォークフォワードと多重検定

- 期間を学習／検証に分け、ローリングまたはアンカー式で更新する。**試行したパラメータ・ルールの総数を記録**し、成績を補正する。試行回数を考慮するデフレーテッド・シャープレシオ [TL-418]、過剰適合確率（CSCV）[TL-419]、データスヌーピング補正のブートストラップ [TL-417] が代表的である。
- Quantopian の 888 本のアルゴリズムでは、バックテストのシャープレシオは実運用後の成績をほとんど説明せず（R² が 0.025 未満）、バックテストを重ねるほど乖離が拡大した [TL-420]。
- 検証区間を制度変更（2022-04 の市場区分再編、2024-11 の取引時間延長など）の前後に分け、レジスタンス・支持線の効き方が変わっていないかを別々に確認する。一般的な落とし穴は [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md) を参照。

## 6. 検証チェックリスト

| 項目 | 確認方法 | 失敗例 |
|---|---|---|
| シグナル遅延 | シグナルを 1 本ずらして成績が変わるか／同日終値約定になっていないか | `shift(1)` 忘れで成績が過大 |
| 価格系列 | 条件判定は未調整、リターンは調整後（配当込み）か | 調整後価格で「1,000 円以下」を判定 |
| 約定可否 | ストップ高・安日、出来高ゼロ日を約定不能にしたか | 張り付き日の高値で売却 |
| 単元・呼値 | 株数が 100 の倍数、価格が呼値の格子上か | 端数株で小資金のバックテストが過大 |
| コスト感応度 | 手数料・スリッページを 2〜3 倍にしても結論が維持されるか | コスト 0 でのみ有効 |
| 試行回数 | 探索したパラメータ数を記録し補正したか | 最良パラメータだけを報告 |
| ユニバース | 当時の上場銘柄（上場廃止含む）か | 現在の構成銘柄だけで検証 |
| 再現性 | データ取得日・ベンダー・調整日時・ライブラリ版を記録したか | 版の更新で結果が変わる |

## 関連文書

- [02_data_sources.md](02_data_sources.md): 調整後株価・生存者バイアス・暦の落とし穴
- [03_python_libraries.md](03_python_libraries.md): 依存関係の衝突と pandas 3 系の扱い
- [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md): 呼値・値幅制限・取引時間
- [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md): 検証手法の落とし穴
- [../03_evidence/01_academic_literature.md](../03_evidence/01_academic_literature.md): テクニカル分析の学術的エビデンス

## この文書の限界

- Web 検索の上限に達したため、各基盤の公式ドキュメントと日本株向けの事例は確認していない。記述は PyPI のメタデータ・README、導入したパッケージのソース、サンドボックス実測に限る。
- 速度は合成データ 1 銘柄 3,000 本・4 vCPU での参考値で、約定規則が異なる基盤間の厳密な比較ではない。backtrader・bt・zipline-reloaded・LEAN・PyBroker・NautilusTrader は未計測、zipline-reloaded・LEAN・NautilusTrader・PyBroker・backtrader は導入と実行を試していない。
- 東証の制度（取引時間、売買単位、値幅制限、呼値、配当落ちの基準値段）は記憶に基づく。売買単位 100 株、2018 年の統一、2024 年 11 月の大引け延長を除き、呼値と値幅制限の具体的な数値は記載していない。最新の制度は JPX の公式資料で確認すること。
- 学術論文は検索結果の書誌・要旨のみを確認し、本文は読んでいない。日本市場での追試結果は扱っていない。
- ライセンスの解釈（AGPL・Commons Clause・LGPL の適用範囲）は法的助言ではない。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TL-401 | PyPI: backtesting 0.6.6 | Zach Lûster | 2026 | https://kernc.github.io/backtesting.py/ | ✅S | PyPI JSON 実測 |
| TL-402 | PyPI: backtrader 1.9.78.123 | Daniel Rodriguez | 2023 | https://github.com/mementum/backtrader | ✅S | PyPI JSON 実測 |
| TL-403 | PyPI: vectorbt 1.2.0 | — | 2026 | https://github.com/polakowo/vectorbt | ✅S | PyPI JSON 実測 |
| TL-404 | PyPI: bt 1.4.1 | — | 2026 | https://github.com/pmorissette/bt | ✅S | PyPI JSON 実測 |
| TL-405 | PyPI: zipline-reloaded 3.2.1 | Quantopian Inc | 2026 | https://ml4trading.io | ✅S | PyPI JSON 実測 |
| TL-406 | PyPI: ml4t-backtest 0.2.0 | — | 2026 | https://www.ml4trading.io/ | ✅S | PyPI JSON 実測 |
| TL-407 | PyPI: lean 1.0.233 | QuantConnect | 2026 | https://lean.io/cli | ✅S | PyPI JSON 実測 |
| TL-408 | NuGet: QuantConnect.Lean 10730.0.0（unlisted） | QuantConnect | — | https://github.com/QuantConnect/Lean | ✅S | NuGet registration の licenseUrl は https://github.com/QuantConnect/Lean/blob/master/LICENSE（本文未読） |
| TL-409 | PyPI: lib-pybroker 2.0.2 | Edward West | 2026 | http://www.pybroker.com | ✅S | PyPI JSON 実測 |
| TL-410 | PyPI: nautilus-trader 1.231.0 | Nautech Systems | 2026 | https://nautilustrader.io | ✅S | PyPI JSON 実測 |
| TL-411 | PyPI: vnpy 4.5.0 | — | 2026 | https://www.vnpy.com | ✅S | PyPI JSON 実測 |
| TL-412 | PyPI: rqalpha 6.5.0 | — | 2026 | https://github.com/ricequant/rqalpha | ✅S | PyPI JSON 実測 |
| TL-413 | PyPI: pyqlib 0.9.7 | — | 2025 | — | ✅S | PyPI JSON 実測 |
| TL-414 | PyPI: lumibot 4.6.48 | Robert Grzesik | 2026 | https://github.com/Lumiwealth/lumibot | ✅S | PyPI JSON 実測 |
| TL-415 | PyPI: FinRL 0.3.7 | AI4Finance Foundation | 2024 | https://github.com/AI4Finance-Foundation/FinRL | ✅S | PyPI JSON 実測 |
| TL-416 | PyPI: fastquant 0.1.8.1 | Lorenzo Ampil | 2023 | https://github.com/enzoampil/fastquant | ✅S | PyPI JSON 実測 |
| TL-417 | Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | Ryan Sullivan, A. Timmermann, H. White／Journal of Finance | 1999 | — | ✅S | DOI 10.1111/0022-1082.00163。論文検索の書誌・要旨のみ確認 |
| TL-418 | The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality | David H. Bailey, Marcos M. López de Prado／Journal of Portfolio Management | 2014 | — | ✅S | DOI 10.3905/jpm.2014.40.5.094。論文検索の書誌・要旨のみ確認 |
| TL-419 | The probability of back-test over-fitting | David H. Bailey, J. Borwein ほか／SSRN 版 | 2016 | — | ✅S | DOI 10.2139/ssrn.2326253。プレプリント。論文検索の書誌・要旨のみ確認 |
| TL-420 | All That Glitters Is Not Gold: Comparing Backtest and Out-of-Sample Performance on a Large Cohort of Trading Algorithms | Thomas V. Wiecki, Andrew Campbell ほか／Journal of Investing | 2016 | — | ✅S | DOI 10.3905/joi.2016.25.3.069。論文検索の書誌・要旨のみ確認 |
| TL-421 | Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs | P. Bajgrowicz, O. Scaillet／Journal of Financial Economics | 2012 | — | ✅S | DOI 10.1016/j.jfineco.2012.06.001。論文検索の書誌・要旨のみ確認 |
| TL-422 | No pain, no gain: You should always incorporate trading costs for a bias-free evaluation of trading rule overperformance | D. Anghel／Economics Letters | 2022 | — | ✅S | DOI 10.1016/j.econlet.2022.110584。論文検索の書誌・要旨のみ確認 |
| TL-423 | サンドボックス実測（pip install・合成データでの最小実行・pip dry-run・タイミング計測） | 本調査（Linux x86_64、Python 3.13.18） | 2026 | — | ✅S | 実行ログは作業領域のみでリポジトリには含めない。1 回の観測 |
| TL-424 | 東証の売買制度（売買単位、取引時間、板寄せ、値幅制限、呼値、配当落ちの基準値段調整） | 日本取引所グループ | 2026 | https://www.jpx.co.jp/equities/trading/domestic/index.html | ✅P | 取得日 2026-11-11／sha256:433cdca80d23／確認箇所: 売買制度の各ページの一覧。個別の数値は 08_primary_sources/01_jpx_primary.md（PJ-001〜007・PJ-012）で原文照合済み |

