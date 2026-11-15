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
