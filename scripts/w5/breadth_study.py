"""市場の内部指標（M1〜M5）の極端な日の検証。仕様は docs/w5_protocol.md「市場の内部指標」。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/breadth_study.py        # 約 10 分
家族（20 検定）: 市場水準 10（極端な日の後の TOPIX の先行リターン）＋ 下げ状態の銘柄 10（極端な日 yes − no の反発の差）。
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
from selectlib import breadth, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def stock_table(acc, flags, which: str) -> dict:
    """下げ状態の銘柄の反発（日ごとの超過）を、極端な日（yes）とそれ以外の日（no）で比べる。
    市場の状態は同じ日のすべての銘柄で同じなので、同じ日の yes − no は作れない。日をまたいで、yes の日の超過 − no の日の超過の平均を、
    重ならない yes の日（かたまり）で検定する。"""
    out = {}
    for hi, h in enumerate(acc["horizons"]):
        pm = rules.period_mask(acc["dates"], h, which)
        cnt = acc["cnt"][hi, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            spread = acc["sum"][hi, 0] / cnt - acc["usum"][hi] / acc["ucnt"][hi]
        valid = pm & (cnt >= rules.MIN_SIGNALS) & (acc["ucnt"][hi] > 0)
        for m in breadth.NAMES:
            f = flags[m].to_numpy()
            yes, no = valid & f, valid & ~f
            if yes.sum() == 0 or no.sum() == 0:
                out[(f"stock:{m}:yes-no", h)] = {"days": 0, "mean": float("nan"), "t": float("nan"), "p": float("nan"), "signals_per_day": float("nan"),
                                                 "net_of_round_trip_cost": float("nan"), "mean_by_liquidity_tertile(low,mid,high)": [float("nan")] * 3}
                continue
            d = np.nan_to_num(spread - np.nanmean(spread[no]))
            s = breadth.episode_stats(d, yes, h)
            s.update({"signals_per_day": float("nan"), "net_of_round_trip_cost": float("nan"), "mean_by_liquidity_tertile(low,mid,high)": [float("nan")] * 3})
            out[(f"stock:{m}:yes-no", h)] = s
    return out


def market_table(P, flags, which: str) -> dict:
    out = {}
    for h in rules.HORIZONS:
        f = breadth.topix_forward(P, h)
        pm = rules.period_mask(P.dates, h, which) & np.isfinite(f)
        base = float(f[pm].mean())
        d = np.nan_to_num(f - base)
        for m in breadth.NAMES:
            active = pm & flags[m].to_numpy()
            s = breadth.episode_stats(d, active, h)
            s["signals_per_day"] = float(active.sum())          # 極端な日の数（かたまり前）
            s["net_of_round_trip_cost"] = float("nan")
            s["mean_by_liquidity_tertile(low,mid,high)"] = [float("nan")] * 3
            out[(f"market:{m}", h)] = s
    return out


def _fmt(t):
    f = lambda x, n: round(x, n) if x is not None and np.isfinite(x) else None  # noqa: E731
    return {"episodes_or_days": t["days"], "mean": f(t["mean"], 5), "t": f(t["t"], 2), "p": f(t["p"], 4)}


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    elig = P.eligible_daily(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL)
    ind = breadth.indicators(P, elig)
    flags = breadth.extreme_flags(ind)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    extras = {"mkt_ext": {m: flags[m].to_numpy() for m in breadth.NAMES}}
    acc = rules.run_pass(P, elig, {"drop": rules.drop_builders()["drop"]}, fins, extras=extras, feats=True, progress=lambda a, b: print(f"{a}/{b} 銘柄", flush=True))

    def tables(which):
        t = market_table(P, flags, which)
        t.update(stock_table(acc, flags, which))
        return t

    dis = tables("discovery")
    keys = list(dis)
    qv = st.bh_fdr(np.array([dis[k]["p"] for k in keys]))
    for k, v in zip(keys, qv):
        dis[k]["q"] = float(v)
    passed = [k for k in keys if np.isfinite(dis[k]["q"]) and dis[k]["q"] < 0.10]
    conf = {}
    if passed:
        full = tables("confirmation")
        conf = {k: full[k] for k in passed}
        fam = f"breadth|{sha[:16]}"
        again = any(r["type"] == "confirmation_read" and r["payload"]["family"] == fam for r in ledger._rows())
        ledger.append_event("confirmation_read", {"family": fam, "rules": [f"{a}|h{b}" for a, b in passed], "re_read": again})
    rows = []
    for k in keys:
        row = {"test": k[0], "h": k[1], "discovery": _fmt(dis[k]), "q": round(dis[k]["q"], 4) if np.isfinite(dis[k]["q"]) else None}
        if k in conf:
            c = conf[k]
            row["confirmation"] = _fmt(c)
            row["law_candidate"] = bool(np.isfinite(c["mean"]) and np.sign(c["mean"]) == np.sign(dis[k]["mean"]) and c["p"] < 0.05)
        rows.append(row)
    ext_days = {m: {"discovery": int((flags[m].to_numpy() & rules.period_mask(P.dates, 5, "discovery")).sum()),
                    "confirmation": int((flags[m].to_numpy() & rules.period_mask(P.dates, 5, "confirmation")).sum())} for m in breadth.NAMES}
    out = {"exploratory": False, "n_tests": int(np.isfinite([dis[k]["p"] for k in keys]).sum()), "discovery_passed": len(passed),
           "law_candidates": sum(1 for r in rows if r.get("law_candidate")), "extreme_days": ext_days, "results": rows, "ledger_chain": ledger.verify(),
           "data_manifest_sha256": sha}
    if write:
        d = root / "results" / "breadth"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1))
