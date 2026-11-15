"""全銘柄での極端な出来事の漂流（段階別・コスト後）。仕様は docs/w5_protocol.md「全銘柄での極端な出来事の漂流と、信用売りの精査」（事前固定。60 検定）。
ローカル PC で実行。出力は集計のみ。

  python scripts/w5/extreme_events.py        # 約 10 分
発見期間で BH（q < 0.10）を通ったセルだけ、確認期間を 1 度読む。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from forecastlib import stats as st  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import events, extremes, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(d: dict) -> dict:
    return {k: (_r(v, 2) if k == "t" else _r(v) if isinstance(v, float) else v) for k, v in d.items()}


def main(root: Path, write=True, min_history: int = extremes.HIST_MIN) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    n = len(P.dates)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=min_history, va_min=extremes.VA_MIN)
    tier = extremes.tier_matrix(P.va60())
    tier = np.where(elig, tier, -1)
    ev = extremes.event_matrices(P, elig)
    ok = elig & events.executable_at_open(P)
    ex = {h: events.excess_matrix(P, ok, h) for h in extremes.HS}
    out = {"split": str(rules.SPLIT.date()), "universe_stocks": int(elig.any(axis=0).sum()), "median_stocks_per_day": int(np.median(elig.sum(axis=1)[elig.any(axis=1)])),
           "events_by_type_and_tier": {e: [int((ev[e] & (tier == k)).sum()) for k in range(len(extremes.TIERS))] for e in extremes.EVENTS},
           "tiers": [{"name": t[0], "round_trip_cost": t[3]} for t in extremes.TIERS]}
    rows = []
    for e in extremes.EVENTS:
        for k in range(len(extremes.TIERS)):
            for h in extremes.HS:
                rows.append({"event": e, "k": k, "h": h, "discovery": extremes.cell(P, ev[e], tier, k, ex[h], h, 0, b - h - 2)})
    live = [r for r in rows if r["discovery"]["p"] is not None]
    if live:
        qv = st.bh_fdr(np.array([r["discovery"]["p"] for r in live], dtype=float))
        for r, q in zip(live, qv):
            r["discovery"]["q"] = float(q)
    passed = [r for r in live if r["discovery"]["q"] < 0.10]
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    for r in passed:
        c = extremes.cell(P, ev[r["event"]], tier, r["k"], ex[r["h"]], r["h"], b, n - 1)
        r["confirmation"] = c
        r["law_candidate"] = bool(c["mean"] is not None and np.sign(c["mean"]) == np.sign(r["discovery"]["mean"]) and c["p"] is not None and c["p"] < 0.05)
    tag = lambda r: f'{r["event"]}|{extremes.TIERS[r["k"]][0]}|h={r["h"]}'  # noqa: E731
    if passed:
        ledger.append_event("confirmation_read", {"family": f"extremes_v1|{sha[:16]}", "cells": [tag(r) for r in passed], "tested": len(live)})
    ledger.append_event("extremes_discovery", {"tested": len(live), "passed": [tag(r) for r in passed], "data_manifest_sha256": sha})
    # 貸借の割合（X1・X2、発見期間）
    loan = {}
    for e in ("X1_limit_up_close", "X2_limit_down_close"):
        loan[e] = []
        for k in range(len(extremes.TIERS)):
            t, j = np.nonzero(ev[e] & (tier == k))
            m = t <= b - 7
            t, j = t[m], j[m]
            cls = events.attr_at(P, iv, t, j, "margin_class") if len(t) else []
            loan[e].append(_r(float(np.mean([str(c) == events.LOAN_CLASS for c in cls])), 2) if len(t) else None)
    cells = []
    for r in rows:
        d = r["discovery"]
        o = {"cell": tag(r), "discovery": _fmt(d)}
        if d["mean"] is not None:
            o["after_cost_discovery"] = {kk: (_r(vv) if isinstance(vv, float) else vv) for kk, vv in extremes.net_after_cost(d["mean"], r["k"], r["h"]).items()}
        o["confirmation"] = _fmt(r["confirmation"]) if "confirmation" in r else "未読（通過していない）"
        if "confirmation" in r and r["confirmation"]["mean"] is not None:
            o["after_cost_confirmation"] = {kk: (_r(vv) if isinstance(vv, float) else vv) for kk, vv in extremes.net_after_cost(r["confirmation"]["mean"], r["k"], r["h"]).items()}
        if "law_candidate" in r:
            o["law_candidate"] = r["law_candidate"]
        cells.append(o)
    out["tests_run"] = len(live)
    out["passed_discovery"] = [tag(r) for r in passed]
    out["law_candidates"] = [tag(r) for r in passed if r.get("law_candidate")]
    out["loan_share_discovery"] = {"tiers": [t[0] for t in extremes.TIERS], **loan}
    out["passed_cells"] = [c for c in cells if c["cell"] in out["passed_discovery"]]
    out["not_passed_cells_discovery_only"] = [{"cell": c["cell"], "events": c["discovery"]["events"], "months": c["discovery"]["months"], "mean": c["discovery"]["mean"],
                                               "t": c["discovery"]["t"], "q": c["discovery"].get("q")} for c in cells if c["cell"] not in out["passed_discovery"] and c["discovery"]["p"] is not None]
    out["ledger_chain"] = ledger.verify()
    out["data_manifest_sha256"] = sha
    if write:
        d = root / "results" / "extremes"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps({**out, "all_cells": cells}, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
