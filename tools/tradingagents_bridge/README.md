# TradingAgents の意見の前向きの記録（橋渡し）

仕様は `docs/w5_protocol.md`「TradingAgents の意見の前向きの記録」。TradingAgents（https://github.com/TauricResearch/TradingAgents 、Apache-2.0、**コミット 9fa1196 に固定**して読んだ版）は、別のフォルダ・別の仮想環境に入れる。

## 毎営業日（引け後）の流れ
1. `universe.txt` に、固定した銘柄の一覧を書く（最初に 1 回だけ。あとから変えない）。
2. TradingAgents の仮想環境の Python で、実行する（その日の日付だけ。結果は `tools/tradingagents_bridge/out/`）:
   ```
   C:\Users\User\TradingAgents\.venv\Scripts\python.exe tools\tradingagents_bridge\run_agents.py --env C:\Users\User\TradingAgents\.env
   ```
   `--provider anthropic --deep <モデル名> --quick <モデル名>` で、モデルを指定できる（省略すると、TradingAgents の `.env` の設定）。出力言語は、既定で Japanese。
3. special1 の Python で、記録する:
   ```
   python scripts/w5/agents_log.py add --dir tools/tradingagents_bridge/out
   ```
4. データを更新したあと（`update_and_record.ps1`）に、`python scripts/w5/agents_log.py score` と `summary`。

## 守ること
- **過去の日付で実行しない**（`--allow-past` は、動作確認用。記録に backfill の印が付き、集計から除く）。LLM が、結果を知っている可能性がある。
- **J-Quants のデータは、TradingAgents に渡さない。** `.env` と API キーは、special1 のフォルダに置かない。チャットにも貼らない。
- 費用は、銘柄数 × 実行回数に比例する。最初は、**5 銘柄ほどで、1 週間**。Anthropic のコンソールで、月の上限を設定しておく。
- 日本株では、センチメント・ニュースのデータが薄い（StockTwits・Reddit が中心）。適時開示は入らない。意見の質は、割り引いて見る。

## 全銘柄（一般株式）に広げる: 毎営業日、無作為に抽出した銘柄を実行する（推奨）
固定した少数の銘柄ではなく、**一般株式の全体からの無作為抽出**にする（ETF・REIT・優先株は除く。売買代金 60 日平均 2,000 万円以上、約 2,450 銘柄）。全銘柄を毎日実行するのは、費用・時間の面で、できない。
1. **抽出**（special1 の Python。実行する**前**に、台帳に記録される。同じ日は 1 回だけ）:
   ```
   python scripts/w5/agents_sample.py draw --n 9
   ```
   売買代金の段階（A: 5 億円以上、B: 5,000 万〜5 億円、C: 2,000 万〜5,000 万円）に、同数ずつ。`tools/tradingagents_bridge/today.txt` に、その日の一覧が書かれる。直近 30 暦日に抽出した銘柄は除く。
2. **実行**（TradingAgents の仮想環境の Python）:
   ```
   C:\Users\User\TradingAgents\.venv\Scripts\python.exe tools\tradingagents_bridge\run_agents.py --env C:\Users\User\TradingAgents\.env --tickers-file tools\tradingagents_bridge\today.txt --analysts market,news,fundamentals
   ```
   `--analysts` で、日本株でデータの薄い `social`（StockTwits・Reddit）を外すと、費用が減る。使ったトークン数と時間が、結果の JSON に記録される。
3. **記録**: `python scripts/w5/agents_log.py add --dir tools/tradingagents_bridge/out`。データを更新したあとに、`score`・`summary`。
- **最初に、3 銘柄ほど（`--n 3`）で、費用を測る**。`summary` の `cost_measure`（1 実行あたりの平均トークン数と秒数）に、出る。そこから、1 日あたりの費用を見積もって、N を決める（費用の単価は、Anthropic の料金表で確認する）。
- **必要な件数**: 21 日の超過の差を、t > 2 で検出するのに、各グループで、差 4.5% なら約 30 件、2% なら約 160 件、1% なら約 650 件。`summary` の `detectable_diff_21d_2se` が、現在の件数で検出できる差。1 日 9 銘柄なら、約 2 か月で、約 400 件（強気は、その一部）。
