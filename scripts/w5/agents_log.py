"""TradingAgents の意見の前向きの記録。仕様は docs/w5_protocol.md「TradingAgents の意見の前向きの記録」。ローカル PC で実行。

  python scripts/w5/agents_log.py add --dir tools/tradingagents_bridge/out     # 実行結果（JSON）を記録（--file で 1 ファイル）
  python scripts/w5/agents_log.py score                                         # J-Quants の日足で採点（データ更新のあと）
  python scripts/w5/agents_log.py summary                                       # 意見ごと・強気/中立/弱気ごとの集計（強気が 30 件たまるまで結論を出さない）
実際の売買はしない。台帳 ledger/agents.jsonl は追記専用。J-Quants のデータは、TradingAgents に渡さない。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import forward_s2 as fs2  # noqa: E402
import lens_log  # noqa: E402
import schema  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402

HORIZONS = (5, 21, 63, 126)
MIN_BULLISH = 30
JST = timezone(timedelta(hours=9))
GROUP = {"buy": "bullish", "overweight": "bullish", "hold": "neutral", "underweight": "bearish", "sell": "bearish"}


def rating_group(r: str) -> str:
    return GROUP.get(str(r).strip().lower(), "review")


def add(root: Path, rec: dict) -> dict:
    if rec.get("schema") != "agents-run/v1":
        return {"error": 'schema が "agents-run/v1" でない'}
    key = f'{rec["ticker"]}|{rec["trade_date"]}'
    ledger = AppendOnlyLedger(root / "ledger" / "agents.jsonl")
    if any(r["type"] == "agents_run" and r["payload"]["key"] == key for r in ledger._rows()):
        return {"status": "already_recorded", "key": key}
    code = lens_log.jq_code("TSE:" + str(rec["ticker"]).split(".")[0]) if str(rec["ticker"]).upper().endswith(".T") else None
    tier = next((name for r in ledger._rows() if r["type"] == "agents_draw" and r["payload"]["date"] == rec["trade_date"]
                 for name, ts in r["payload"]["tickers"].items() if rec["ticker"] in ts), None)
    payload = {"key": key, "ticker": rec["ticker"], "jq_code": code, "trade_date": rec["trade_date"], "rating": rec["rating"], "group": rating_group(rec["rating"]), "backfill": bool(rec.get("backfill")), "tier": tier, "drawn": tier is not None,
               "run_utc": rec.get("run_utc"), "decision_sha256": rec.get("decision_sha256"), "decision_excerpt": rec.get("decision_excerpt"), "config": rec.get("config"),
               "elapsed_sec": rec.get("elapsed_sec"), "usage_tokens": rec.get("usage_tokens")}
    ledger.append_event("agents_run", payload)
    return {"status": "recorded", "key": key, "rating": rec["rating"], "group": payload["group"], "scorable_with_jquants": code is not None, "backfill": payload["backfill"]}


def add_files(root: Path, files: list) -> dict:
    res = [add(root, json.loads(Path(f).read_text(encoding="utf-8-sig"))) for f in sorted(files)]
    return {"files": len(res), "recorded": sum(r.get("status") == "recorded" for r in res), "already": sum(r.get("status") == "already_recorded" for r in res),
            "errors": [r for r in res if "error" in r], "backfill": sum(bool(r.get("backfill")) for r in res if r.get("status") == "recorded"),
            "ledger": AppendOnlyLedger(root / "ledger" / "agents.jsonl").verify()}


def _utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def score(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "agents.jsonl")
    rows = ledger._rows()
    done = {(r["payload"]["key"], r["payload"]["h"]) for r in rows if r["type"] == "agents_outcome"}
    runs = [r for r in rows if r["type"] == "agents_run"]
    todo = [(r, h) for r in runs for h in HORIZONS if (r["payload"]["key"], h) not in done]
    if not todo:
        return {"scored": 0, "pending": 0, "ledger": ledger.verify()}
    P, iv, _ = fs2.load_panel(root, None)
    ci = {c: i for i, c in enumerate(P.codes)}
    cache, n, pending, unscor = {}, 0, 0, set()
    for r, h in todo:
        pl = r["payload"]
        if pl["jq_code"] is None or pl["jq_code"] not in ci:
            if pl["key"] not in unscor and (pl["key"], 0) not in done:
                ledger.append_event("agents_outcome", {"key": pl["key"], "h": 0, "status": "unscorable", "reason": "日本株でない、または J-Quants にない銘柄"})
                unscor.add(pl["key"])
                done.add((pl["key"], 0))
            continue
        d = pd.Timestamp(pl["trade_date"])
        t = int(np.searchsorted(P.dates.values, d.to_datetime64(), side="right")) - 1
        if t < 0 or t + 1 + h >= len(P.dates) or P.dates[-1] < d:
            pending += 1
            continue
        if t not in cache:
            cache[t] = P.eligible(iv, schema.WIDE_MARKETS, [t], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
        j = ci[pl["jq_code"]]
        with np.errstate(divide="ignore", invalid="ignore"):
            f = P.adj_open[t + 1 + h] / P.adj_open[t + 1] - 1.0
        um = float(np.nanmean(np.where(cache[t], f, np.nan)))
        if not np.isfinite(f[j]):
            ledger.append_event("agents_outcome", {"key": pl["key"], "h": h, "status": "no_price"})
            continue
        buy_open = datetime(P.dates[t + 1].year, P.dates[t + 1].month, P.dates[t + 1].day, 9, 0, tzinfo=JST)          # 買いの日の寄り付き（日本時間 9:00）
        valid = (not pl["backfill"]) and _utc(r["utc"]) < buy_open.astimezone(timezone.utc)
        ledger.append_event("agents_outcome", {"key": pl["key"], "h": h, "status": "scored", "rating": pl["rating"], "group": pl["group"], "tier": pl.get("tier"), "drawn": pl.get("drawn"), "buy_day": str(P.dates[t + 1].date()),
                                               "ret": round(float(f[j]), 5), "excess": round(float(f[j] - um), 5), "forward_valid": bool(valid)})
        n += 1
    return {"scored": n, "pending": int(pending), "ledger": ledger.verify()}


def _stats(x: np.ndarray) -> dict:
    d = {"n": int(len(x)), "mean_excess": round(float(x.mean()), 4), "share_positive": round(float((x > 0).mean()), 2)}
    if len(x) > 2 and x.std(ddof=1) > 0:
        d["t"] = round(float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))), 2)
    return d


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "agents.jsonl")
    rows = ledger._rows()
    runs = [r["payload"] for r in rows if r["type"] == "agents_run"]
    outs = [r["payload"] for r in rows if r["type"] == "agents_outcome" and r["payload"].get("status") == "scored"]
    res = {"runs_recorded": len(runs), "backfill_runs_excluded": sum(1 for p in runs if p["backfill"]), "outcomes_scored": len(outs),
           "outcomes_not_forward_valid": sum(1 for o in outs if not o["forward_valid"]), "by_rating": {}, "by_group": {}}
    valid = [o for o in outs if o["forward_valid"]]
    for h in HORIZONS:
        sel = [o for o in valid if o["h"] == h]
        if not sel:
            continue
        res["by_rating"][f"h={h}"] = {r: _stats(np.array([o["excess"] for o in sel if o["rating"] == r])) for r in sorted({o["rating"] for o in sel})}
        res["by_group"][f"h={h}"] = {g: _stats(np.array([o["excess"] for o in sel if o["group"] == g])) for g in ("bullish", "neutral", "bearish", "review") if any(o["group"] == g for o in sel)}
    s21 = [o for o in valid if o["h"] == 21]
    bull = np.array([o["excess"] for o in s21 if o["group"] == "bullish"])
    rest = np.array([o["excess"] for o in s21 if o["group"] != "bullish"])
    if len(bull) and len(rest):
        diff = float(bull.mean() - rest.mean())
        se = float(np.sqrt(bull.var(ddof=1) / len(bull) + rest.var(ddof=1) / len(rest))) if len(bull) > 1 and len(rest) > 1 else float("nan")
        res["bullish_minus_rest_21d"] = {"diff": round(diff, 4), "t": round(diff / se, 2) if se and np.isfinite(se) and se > 0 else None, "bullish_n": int(len(bull)), "rest_n": int(len(rest))}
    sd = np.concatenate([bull, rest]).std(ddof=1) if len(bull) + len(rest) > 2 else float("nan")
    if len(bull) > 1 and len(rest) > 1 and np.isfinite(sd):
        res["detectable_diff_21d_2se"] = round(float(2 * sd * np.sqrt(1 / len(bull) + 1 / len(rest))), 4)
    tiers = {}
    for tname in sorted({o.get("tier") for o in s21 if o.get("tier")}):
        b = np.array([o["excess"] for o in s21 if o.get("tier") == tname and o["group"] == "bullish"])
        r_ = np.array([o["excess"] for o in s21 if o.get("tier") == tname and o["group"] != "bullish"])
        tiers[tname] = {"bullish_n": int(len(b)), "rest_n": int(len(r_)), "diff": round(float(b.mean() - r_.mean()), 4) if len(b) and len(r_) else None}
    res["by_tier_bullish_minus_rest_21d"] = tiers
    draws = [r["payload"] for r in rows if r["type"] == "agents_draw"]
    drawn_total = sum(len(t) for d in draws for t in d["tickers"].values())
    res["draws"] = {"days": len(draws), "tickers_drawn": drawn_total, "runs_recorded_from_draws": sum(1 for p in runs if p.get("drawn")),
                    "drawn_but_not_recorded": drawn_total - sum(1 for p in runs if p.get("drawn"))}
    toks = [sum(u.get("total_tokens", 0) for u in (p.get("usage_tokens") or {}).values()) for p in runs if p.get("usage_tokens")]
    secs = [p["elapsed_sec"] for p in runs if p.get("elapsed_sec")]
    res["cost_measure"] = {"runs_with_usage": len(toks), "mean_total_tokens_per_run": int(np.mean(toks)) if toks else None, "mean_seconds_per_run": round(float(np.mean(secs)), 1) if secs else None}
    res["conclusion"] = f"強気が {len(bull)} 件（21 日で採点済み）。{MIN_BULLISH} 件たまるまで、結論を出さない。既定は「優位性なし」" if len(bull) < MIN_BULLISH \
        else "強気が 30 件以上。事前の基準（強気 − 強気でない > 0、t > 2）で判断する"
    res["ledger"] = ledger.verify()
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "score", "summary"])
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--dir")
    ap.add_argument("--file")
    a = ap.parse_args()
    root = Path(a.root)
    if a.cmd == "add":
        files = [a.file] if a.file else sorted(str(p) for p in Path(a.dir or "tools/tradingagents_bridge/out").glob("*.json"))
        r = add_files(root, files) if files else {"error": "JSON のファイルがない"}
    else:
        r = score(root) if a.cmd == "score" else summary(root)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
