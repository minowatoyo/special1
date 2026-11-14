"""S2（配当の権利取り）の深掘り診断。仕様は docs/w5_protocol.md「S2 の深掘り診断」。採用する仕様は変えない。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/s2_deep_dive.py        # 約 5〜10 分
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
from selectlib import rules, seasonal  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

COST = {"A": 0.0030, "B": 0.0060, "C": 0.0120}      # 往復
PERIODS = ("discovery", "confirmation")


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def stat(vals) -> dict:
    v = np.asarray([x for x in vals if np.isfinite(x)], dtype=float)
    s = seasonal.tstat(v, lags=2)
    return {"windows": int(len(v)), "mean": _r(s["mean"]), "t": _r(s["t"], 2)}


def by_period(ws, fn) -> dict:
    return {p: stat([fn(w) for w in ws if w["period"] == p]) for p in PERIODS}


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    va60 = P.va60()
    base = seasonal.s2_windows(P, elig, va60, fins, b)
    out = {"spec": "権利付き最終日の 40 営業日前の始値で買い、最終日の始値で売り。予想配当利回りの上位 1/5（事前固定、変更なし）",
           "main": by_period(base, lambda w: seasonal.top_frac(w, 0.8))}
    out["D1_by_rights_month"] = {m: by_period([w for w in base if w["month"] == m], lambda w: seasonal.top_frac(w, 0.8)) for m in range(1, 13)}
    out["D2_yield_quintiles"] = {f"Q{k + 1}({'低' if k == 0 else '高' if k == 4 else ''})": by_period(base, lambda w, k=k: seasonal.top_frac(w, k / 5, (k + 1) / 5 if k < 4 else 1.0))
                                 for k in range(5)}
    out["D2_top_decile"] = by_period(base, lambda w: seasonal.top_frac(w, 0.9))
    d3 = {}
    for k, nm in enumerate("ABC"):
        def fn(w, k=k):
            r = w["yld"].argsort().argsort() / len(w["yld"])
            m = (r >= 0.8) & (w["tier"] == k)
            return float(w["y"][m].mean()) if m.sum() >= 3 else np.nan
        d3[nm] = {p: {**v, "net_of_round_trip": _r(v["mean"] - COST[nm]) if v["mean"] is not None else None} for p, v in by_period(base, fn).items()}
    out["D3_by_liquidity_tier"] = d3
    out["D3_by_year_top_quintile"] = {y: stat([seasonal.top_frac(w, 0.8) for w in base if w["year"] == y]) for y in sorted({w["year"] for w in base})}
    grid = {}
    for lead in (20, 40, 60):
        for ex in (5, 0):
            ws = seasonal.s2_windows(P, elig, va60, fins, b, lead=lead, exit_shift=ex)
            grid[f"buy_{lead}d_before_sell_{'last_day_open' if ex == 0 else '5d_before'}"] = by_period(ws, lambda w: seasonal.top_frac(w, 0.8))
    grid["after_ex_date: last_day_open_to_+10d_open"] = by_period(seasonal.s2_windows(P, elig, va60, fins, b, post=10), lambda w: seasonal.top_frac(w, 0.8))
    out["D4_sensitivity_grid(記述。選ぶためではない)"] = grid
    d5 = {}
    for p in PERIODS:
        v = np.array([seasonal.top_n(w, 15, 0) for w in base if w["period"] == p], dtype=float)
        v = v[np.isfinite(v)]
        s = seasonal.tstat(v, lags=2)
        d5[p] = {"windows": int(len(v)), "mean_excess": _r(s["mean"]), "t": _r(s["t"], 2), "net_of_round_trip_15bps_each_way": _r(s["mean"] - 0.003),
                 "annualized_rough": _r((s["mean"] - 0.003) * 6), "share_positive_windows": _r((v > 0).mean()) if len(v) else None}
    out["D5_top15_tier_A"] = d5
    if write:
        d = root / "results" / "seasonal"
        d.mkdir(parents=True, exist_ok=True)
        (d / "s2_deep_dive.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
