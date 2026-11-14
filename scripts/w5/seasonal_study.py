"""季節性（S1 同じ月の持続、S2 配当の権利取り、S3 決算発表前の上昇）と、広い母集団。仕様は docs/w5_protocol.md。
ローカル PC で実行。出力は集計のみ。

  python scripts/w5/seasonal_study.py        # 約 10 分
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
from selectlib import rules, seasonal  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

WIDE_MIN_HISTORY = 250


def _r(x, n=5):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(s):
    return {"n": int(s.get("n", s.get("days", 0))), "mean": _r(s["mean"]), "t": _r(s["t"], 2), "p": _r(s["p"], 4)}


def series(rows, key, period):
    return np.array([r[key] for r in rows if r["period"] == period], dtype=float)


def tier_table(rows, period, trades_per_obs=1) -> dict:
    out = {}
    for nm in "ABC":
        x = series(rows, f"top_{nm}", period)
        x = x[np.isfinite(x)]
        out[nm] = {"n": int(len(x)), "gross": _r(x.mean()) if len(x) else None,
                   "net_of_round_trip": _r(x.mean() - 2 * seasonal.TIER_COST[nm] * trades_per_obs) if len(x) else None}
    return out


def main(root: Path, write=True, min_history: int = WIDE_MIN_HISTORY) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=min_history, va_min=schema.WIDE_VA_MIN)
    va60 = P.va60()
    s1 = seasonal.s1_same_month(P, elig, va60, b)["rows"]
    s2 = seasonal.s2_dividend_runup(P, elig, va60, fins, b)["rows"]
    s3 = seasonal.s3_pre_earnings(P, elig, va60, fins, b)

    def tests(period):
        t = {"S1_same_month:ic": seasonal.tstat(series(s1, "ic", period)), "S1_same_month:top_quintile": seasonal.tstat(series(s1, "top", period)),
             "S2_dividend_runup:top_quintile": seasonal.tstat(series(s2, "top", period), lags=2), "S2_dividend_runup:ic": seasonal.tstat(series(s2, "ic", period), lags=2)}
        s = seasonal.s3_stats(s3, P.dates, b, period)
        t["S3_pre_earnings:mean"] = {"n": s["days"], "mean": s["mean"], "t": s["t"], "p": s["p"]}
        return t

    dis = tests("discovery")
    keys = list(dis)
    qv = st.bh_fdr(np.array([dis[k]["p"] for k in keys]))
    passed = [k for k, q in zip(keys, qv) if np.isfinite(q) and q < 0.10]
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    conf = {}
    if passed:
        full = tests("confirmation")
        conf = {k: full[k] for k in passed}
        fam = f"seasonal|{sha[:16]}"
        again = any(r["type"] == "confirmation_read" and r["payload"]["family"] == fam for r in ledger._rows())
        ledger.append_event("confirmation_read", {"family": fam, "rules": passed, "re_read": again})
    results = []
    for k, q in zip(keys, qv):
        row = {"test": k, "discovery": _fmt(dis[k]), "q": _r(q, 4)}
        if k in conf:
            c = conf[k]
            row["confirmation"] = _fmt(c)
            row["law_candidate"] = bool(np.isfinite(c["mean"]) and np.sign(c["mean"]) == np.sign(dis[k]["mean"]) and np.isfinite(c["p"]) and c["p"] < 0.05)
        results.append(row)
    n_el = elig.sum(axis=1)
    tr_last = seasonal.tiers(va60[b - 1])[elig[b - 1]] if b > 0 and elig[b - 1].any() else np.array([])
    s3d = seasonal.s3_stats(s3, P.dates, b, "discovery")
    out = {"universe": {"eligible_median_per_day": int(np.median(n_el[n_el > 0])) if (n_el > 0).any() else 0,
                        "tier_counts_at_end_of_discovery(A,B,C)": [int((tr_last == k).sum()) for k in range(3)]},
           "n_tests": int(np.isfinite([dis[k]["p"] for k in keys]).sum()), "discovery_passed": len(passed),
           "law_candidates": sum(1 for r in results if r.get("law_candidate")), "results": results,
           "descriptive_discovery": {
               "S1_months": int(len(series(s1, "ic", "discovery"))), "S1_top_quintile_by_tier": tier_table(s1, "discovery"),
               "S2_rights_months": int(len(series(s2, "top", "discovery"))), "S2_all_rights_stocks_mean": _r(np.nanmean(series(s2, "rights_all", "discovery"))) if s2 else None,
               "S2_top_quintile_by_tier": tier_table(s2, "discovery"),
               "S3_entries": s3d.get("entries"), "S3_by_tier_gross": {k: _r(v) for k, v in s3d["by_tier_event_weighted"].items()},
               "S3_by_tier_net_of_round_trip": {k: _r(v - 2 * seasonal.TIER_COST[k]) for k, v in s3d["by_tier_event_weighted"].items()}},
           "ledger_chain": ledger.verify(), "data_manifest_sha256": sha}
    if write:
        d = root / "results" / "seasonal"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
