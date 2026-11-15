# AI Agent Lens（TradingView の指標 → AI エージェント）の取り込み

出所: https://github.com/roan-maverick/tradingview-indicator-for-ai-agents （MIT）。**コミット `f1aa6ce185f943f1e825f638c10b1201ef0e1e0a`（2026-11-13）で固定**。上流の更新は、**中身を読み直してから**取り込む（自動では追従しない）。
改変なしのファイル: `ai-agent-lens.pine`・`examples/webhook_receiver.py`・`docs/`・`examples/*.json`・`LICENSE`。`AGENT_PROMPT_ORIGINAL.md` は、元のエージェント用プロンプト（暗号資産・買いと売りの前提）。**日本株の現物向けに直したものは `AGENT_PROMPT_JP.md`。**

## これは何か
チャートが引けるたびに、ローソク足・トレンド・RSI・MACD・ADX・出来高・ATR・直近の高安・VWAP・「スコア」・損切り/利確の目安を、1 つの JSON にして、TradingView のアラート（Webhook）で送る指標。受け取った AI が、LONG / SHORT / WAIT / SKIP と、理由・損切り・数量を返す。**注文は出さない。**

## 先に知っておくこと（このリポジトリの検証結果との関係）
- **指標の「スコア」は、検証されていない。** 中身は、EMA・RSI・ADX・出来高などの、ふつうのテクニカルの重ね合わせ。当方の検証（日本株、約 100 規則、5・21 日）では、**テクニカルの規則で、確認期間まで残ったものはない**（強い・買われすぎの状態は、むしろ 5 日で負ける傾向）。**この指標の売買シグナルに、優位性があると考えない。** 「画面で状況を整理する道具」「気になった銘柄を AI に説明させる道具」として使う。
- 確認できている材料（極端な動きの直後は弱い、ストップ高・安の翌朝は買わない、など）は、`AGENT_PROMPT_JP.md` に入れてある。
- **データの方針**: J-Quants が正本。TradingView のデータは、**表示・相談用**。モデル・検証には入れない（混ぜない）。
- 日本株の TradingView データは、有料のリアルタイム購読がないと、**約 20 分遅れ**。足の引け値の判定が、遅れる。

## 安全な使い方（推奨）
1. **ネットワークに出さない使い方（最初はこれ）**: Pine Editor に `ai-agent-lens.pine` を貼って、チャートに追加。設定で「Send JSON packet」を `Off`、「Show packet preview on chart」を ON。画面のパケットを、コピーして、Claude に貼る（`AGENT_PROMPT_JP.md` の指示つき）。Webhook も、トンネルも、有料プランも要らない。
2. **Webhook で自動にする場合**（TradingView の有料プラン＋2 要素認証が要る）:
   - 受信プログラムは、**`--host 127.0.0.1`** で起動する（既定の `0.0.0.0` にしない）。`--token` は、長いランダムな文字列にする。
   - 公開は、`cloudflared tunnel --url http://127.0.0.1:8080`。URL は、起動のたびに変わる（アラートの URL を、更新する）。
   - **この受信プログラムは、J-Quants のデータ（`data/jquants`）・API キーのある PC では動かさない、または、専用のフォルダ・専用のユーザーで動かす**（インターネットから届く入口を、機密のある PC に置かない）。保存先は `tools/tradingview_ai_lens/packets/`（Git の対象外）。
   - トークンは、URL の末尾に付く（TradingView は、ヘッダーを付けられない）。ログ・履歴に残りうるので、**使い回さない**。アラートは、Essential・Plus プランで、2 か月で失効する。

## レビューの記録（2026-11-15）
`REVIEW.md` を参照。
