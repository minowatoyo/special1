# 引き継ぎ（クラウドから、ローカルの VS Code へ。2026-11-15）

これを読めば、これまでの経緯なしで、作業を続けられる。仕様の全記録は `docs/w5_protocol.md`、結果の要約は `docs/final_report.md`・`docs/w4_w5_status.md`（実行コマンド）。規則は、ルートの `CLAUDE.md`。

## 1. 目的と方針（利用者の決定）
- 日本株の、チャート分析・確率予測・選別の検証。**J-Quants Standard（直近10年）が唯一の正本**。他のデータは、文脈を補うだけで、検証・モデルに混ぜない。
- 生の表は、画面・報告・外部の LLM に出さない（集計だけ）。購入後の削除: `sh scripts/jquants/purge.sh --yes`。
- 単元未満株は使わない。想定資金 1,000 万円（ペーパートレードは 300 万円）。信用売りは、あまりしない方向。モデルの既定は、証拠なしに変えない。
- 進め方: 結果を見る前に、定義を `docs/w5_protocol.md` に固定 → 実装 → 合成データでテスト → 実行 → 出力（集計）を読む。確認期間は、1 つの族につき、1 度だけ。

## 2. データと実行環境（利用者の PC。Windows、PowerShell 5.1）
- 場所: `data/jquants/`（Git の対象外）。更新: `powershell -ExecutionPolicy Bypass -File scripts\update_and_record.ps1`（月に1回以上。キーは、実行時に聞く。`-AskKey`）。追加取得は、取得済みの日を飛ばす（数分）。
- **`.ps1` は、ASCII のみ**（日本語を入れると、PowerShell 5.1 で文字化けして、構文エラー）。
- キー: `JQUANTS_API_KEY`（環境変数）→ なければ `~/.jquants_key`。再発行したら、古いファイルを消す。
- 環境変数 `JQ_EXEC=open`: 買える日の判定の修正版（結果は `results/<名前>_execopen/`）。既定は、従来の判定。
- Python 3.11 以上。テスト: `cd 07_reference_code && python -m pytest tests -q`（全件、合成データ）。

## 3. 結論の要約（約 200 件+追加の検証。確認期間まで通したもの）
- **買いで、確認期間まで残った形は、ほぼない**: チャート規則（約 100 検定）、パターン図鑑、探索マップ、個別株の弾力性、割安×財務の強さ、材料のない下げ、指数・業種の逆張り、除外フィルター（信用残・極端な動き）は、いずれも、確認できず。
- **残ったもの**: S2（配当の権利取り。窓の中 +1.4%。口座では、母集団を年 1〜2pt 上回る程度。確認期間で残ったのは段階 B）／**極端な動きの後の弱さ**（上げでも下げでも。ボラでは説明されない。売り側。順位予測の上位 15 から除いても、改善せず）／**ストップ高引けの貸借銘柄の信用売り**（売り残が軽い群で、1 件 +6%。実行には、貸借・逆日歩・規制の確認が要る。紙の上の記録中）。
- 順位予測（SEL-C1）: 順位を当てる力はある（順位相関 0.04〜0.06）が、100 株単位とコストで、ほぼ消える。
- 台帳（`data/jquants/ledger/`）: `trials.jsonl`（検証の試行・確認期間の読み）、`forward.jsonl`（順位予測）、`forward_s2.jsonl`、`forward_events.jsonl`（信用売りの候補・指数の状態）、`lens.jsonl`、`agents.jsonl`、`watchlist.jsonl`。**新しい行は、書いた時刻もハッシュに含む（hv=2）。古い行の時刻は、改ざんを検出できない。**

## 4. 前向きの記録（動いているもの）
| 記録 | コマンド（`update_and_record.ps1` に、まとめてある） |
|---|---|
| 順位予測 | `forward.py record/score/summary`。独立は 21 営業日あけて数える。12 期まで結論を出さない |
| S2 | `forward_s2.py record/score/summary`。買いの予定日の直前にも、記録し直す。12 か月まで |
| 信用売りの候補・指数 | `forward_events.py record/score/summary`。候補 30 件、指数 10 エピソードまで |
| TradingView AI Agent Lens | `lens_log.py add --kind packet/signal --clip`、`score`、`summary`。銘柄の一覧は、先に固定 |
| TradingAgents（無作為抽出） | `agents_sample.py draw` → `tools/tradingagents_bridge/run_agents.py`（TradingAgents の仮想環境）→ `agents_log.py add/score/summary`。強気 30 件まで。**検出できる差は、件数が少ないと大きい** |
| 指定銘柄 | `watchlist.py add --code ... --dossier <深掘りレポート>`。採点は 21・63・126 営業日 |

## 5. 未完了（次にやること。優先順）
1. **深掘りレポート**（`scripts/w5/deep_dive.py`、`selectlib/deepdive.py`、仕様は `w5_protocol.md`「深掘りレポート」）: 合成データのテストは通過。**実データでの初回の実行は、まだ**（`python scripts/w5/deep_dive.py --code <コード>`。初回は、基準率の観測表を作る）。
2. **文脈を補う層**: EDINET（公式API v2。無料。キーは `~/.edinet_key`）の提出書類・大量保有報告書・自己株式の買付、yfinance の確認、を深掘りレポートに足す。規則: 出どころを記録、食い違ったら J-Quants が正、取得内容は、時点のまま保存（ハッシュ）。EDINET DB（edinetdb.jp、β版、第三者）は、規約を確認してから。
3. **大量保有報告書の検証**（事前固定から。新しい仮説。EDINET の提出日時で、時点を守れる）。
4. **ペーパートレード**（3 人格 + 比較 2: TOPIX 買い持ち、無作為。各 300 万円、現物・買いのみ）。人格案: 機械（SEL-C1）／配当（S2）／AI 裁量（TradingAgents が強気 + 関門 + 建玉の計算）。**腕の評価ではなく、運用の成立の確認**（腕は、件数の多い前向きの記録で見る）。先に `diagnose.py --capital 3000000` で、制約の大きさを測る。**利用者の確認待ち**: 人格の構成、開始時期（12 月の月次更新）、人格 3 の銘柄の選び方。
5. TradingAgents の最初の試運転（3 銘柄）: 6996.T は、`Underweight` で完了。2・3 番目は、途中で止めた。次回は、新しい日付で `agents_sample.py draw` から。モデル名は、TradingAgents の一覧にあるもの（`claude-haiku-4-5`・`claude-sonnet-5`）。使用量と費用を測る（`agents_log.py summary` の `cost_measure`）。
6. 利用者のタスク: `update_and_record.ps1 -AskKey` の最後までの結果の確認（`forward.py score` 以降）、`margin_interest` の期間の確認、EDINET のキーの取得。
7. 未了の技術的な課題: 予測モデル側の FIX-09 の (2)(3)（標本内残差の過小評価、リッジ罰則のパネル検証）。

## 6. 注意（過去に見つかった欠陥と、その扱い）
- 「買える日」の判定が、寄り付き後にストップ高になった銘柄まで除いていた（負の側に偏る）→ `JQ_EXEC=open` で修正版。規則・探索マップへの影響は、小さい。パターン図鑑の「再現 2」は、撤回。
- 上場銘柄表が、価格の最終日より前に終わるとき、最新日の母集団が空になる → `run_selection.extend_master` で修正。
- 台帳の時刻がハッシュに含まれていなかった → 新しい行から修正（古い行は、そのまま検証できる）。
- クラウドで作っていた HTML の報告書（Artifact）の生成器は、`tools/report_html/build.py`（実行すると `final_report.html` を出す）。内容は、2026-11-15 の時点。
