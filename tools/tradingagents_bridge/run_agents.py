"""TradingAgents を、固定した銘柄の一覧に対して、その日（日本時間）だけ実行し、結果を JSON で保存する（前向きの記録用）。

TradingAgents の仮想環境の Python で動かす（このファイルは、TradingAgents 以外に何も要らない）:
  C:\\Users\\User\\TradingAgents\\.venv\\Scripts\\python.exe tools\\tradingagents_bridge\\run_agents.py --env C:\\Users\\User\\TradingAgents\\.env --tickers-file tools\\tradingagents_bridge\\universe.txt
結果は tools/tradingagents_bridge/out/<銘柄>_<日付>.json（Git の対象外）。そのあと、special1 の Python で:
  python scripts/w5/agents_log.py add --dir tools/tradingagents_bridge/out
J-Quants のデータは、TradingAgents に渡さない。API キーは、.env に（チャットに貼らない）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
SCHEMA = "agents-run/v1"


def today_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


def safe(t: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in t)[:40]


def _usage_diff(before: dict, after: dict) -> dict:
    """モデルごとのトークン数の、実行前後の差（langchain の UsageMetadataCallbackHandler.usage_metadata）。"""
    out = {}
    for model, u in (after or {}).items():
        b = (before or {}).get(model, {})
        d = {k: int(u.get(k, 0)) - int(b.get(k, 0)) for k in ("input_tokens", "output_tokens", "total_tokens") if isinstance(u.get(k, 0), (int, float))}
        if any(d.values()):
            out[model] = d
    return out


def run_one(graph, ticker: str, trade_date: str, config_summary: dict, out_dir: Path, allow_past: bool = False, now_date: str | None = None, usage_fn=None) -> dict:
    """1 銘柄を実行して JSON を保存する。同じ銘柄・同じ日は、すでにあればスキップ。過去日付は、allow_past のときだけ（backfill の印）。"""
    now_date = now_date or today_jst()
    backfill = trade_date < now_date
    if backfill and not allow_past:
        return {"ticker": ticker, "status": "skipped_past_date", "note": "過去日付は、前向きとして数えない。--allow-past で、backfill の印つきで実行できる"}
    path = out_dir / f"{safe(ticker)}_{trade_date}.json"
    if path.exists():
        return {"ticker": ticker, "status": "already_exists", "file": str(path)}
    u0 = json.loads(json.dumps(usage_fn())) if usage_fn else None
    t0 = time.time()
    final_state, rating = graph.propagate(ticker, trade_date)
    elapsed = round(time.time() - t0, 1)
    decision = str((final_state or {}).get("final_trade_decision", ""))
    rec = {"schema": SCHEMA, "ticker": ticker, "trade_date": trade_date, "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rating": str(rating),
           "backfill": bool(backfill), "decision_sha256": hashlib.sha256(decision.encode("utf-8")).hexdigest(), "decision_excerpt": decision[:600], "decision_full": decision,
           "config": config_summary, "elapsed_sec": elapsed, "usage_tokens": _usage_diff(u0, usage_fn()) if usage_fn else None}
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ticker": ticker, "status": "done", "rating": str(rating), "file": str(path)}


def make_graph(args):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    config = DEFAULT_CONFIG.copy()
    if args.provider:
        config["llm_provider"] = args.provider
    if args.deep:
        config["deep_think_llm"] = args.deep
    if args.quick:
        config["quick_think_llm"] = args.quick
    if args.language:
        config["output_language"] = args.language
    summary = {k: config.get(k) for k in ("llm_provider", "deep_think_llm", "quick_think_llm", "output_language", "max_debate_rounds", "max_risk_discuss_rounds", "temperature")}
    try:
        import tradingagents
        summary["tradingagents_version"] = getattr(tradingagents, "__version__", None)
        summary["tradingagents_git"] = subprocess.run(["git", "-C", str(Path(tradingagents.__file__).resolve().parents[1]), "rev-parse", "--short", "HEAD"],
                                                      capture_output=True, text=True).stdout.strip() or None
    except Exception:  # noqa: BLE001
        pass
    handler = None
    try:
        from langchain_core.callbacks import UsageMetadataCallbackHandler
        handler = UsageMetadataCallbackHandler()
    except Exception:  # noqa: BLE001
        pass
    kw = {"callbacks": [handler]} if handler else {}
    analysts = [x.strip() for x in args.analysts.split(",")] if args.analysts else None
    if analysts:
        kw["selected_analysts"] = analysts
        summary["selected_analysts"] = analysts
    return TradingAgentsGraph(debug=False, config=config, **kw), summary, (lambda: handler.usage_metadata) if handler else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers-file", default=str(Path(__file__).parent / "universe.txt"))
    ap.add_argument("--tickers", nargs="*", help="ファイルの代わりに、銘柄を直接指定（固定した一覧を使うこと）")
    ap.add_argument("--date", default=None, help="既定は、今日（日本時間）。過去日付は --allow-past が要る")
    ap.add_argument("--allow-past", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).parent / "out"))
    ap.add_argument("--env", default=None, help="TradingAgents の .env のパス（API キーを読む）")
    ap.add_argument("--provider")
    ap.add_argument("--deep")
    ap.add_argument("--quick")
    ap.add_argument("--language", default="Japanese")
    ap.add_argument("--analysts", default=None, help="使うアナリスト（コンマ区切り: market,social,news,fundamentals）。日本株は、social（StockTwits・Reddit）のデータが薄いので、外すと、費用が減る。使った一覧は、記録に残る")
    a = ap.parse_args()
    if a.env:
        from dotenv import load_dotenv
        load_dotenv(a.env)
    tickers = a.tickers or [x.strip() for x in Path(a.tickers_file).read_text(encoding="utf-8").splitlines() if x.strip() and not x.strip().startswith("#")]
    if not tickers:
        sys.exit("銘柄がない。universe.txt に、固定した一覧を書く（1 行に 1 銘柄、例: 7203.T）")
    date = a.date or today_jst()
    graph, summary, usage_fn = make_graph(a)
    for t in tickers:
        try:
            print(json.dumps(run_one(graph, t, date, summary, Path(a.out), a.allow_past, usage_fn=usage_fn), ensure_ascii=False))
        except Exception as e:  # noqa: BLE001  1 銘柄の失敗で全体を止めない
            print(json.dumps({"ticker": t, "status": "error", "error": f"{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
