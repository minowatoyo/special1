"""パターン図鑑: 条件の組み合わせ（最大 3 条件）を網羅し、「どういう銘柄が、どういう状態のとき、どう動いたか」を具体的に見る。
仕様は docs/w5_protocol.md「パターン図鑑」。ローカル PC で実行。出力は集計のみ（銘柄名は出さない）。

  python scripts/w5/pattern_atlas.py        # 約 10〜20 分
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from forecastlib import stats as st  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import atlas, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

TOP_LONG, TOP_AVOID = 30, 15


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def pick(res: list) -> tuple:
    pos = sorted([r for r in res if r["mean"] > 0], key=lambda r: -r["t"])[:TOP_LONG]
    neg = sorted([r for r in res if r["mean"] < 0], key=lambda r: r["t"])[:TOP_AVOID]
    return pos, neg


def main(root: Path, write=True, min_obs: int = atlas.MIN_OBS, min_periods: int = atlas.MIN_PERIODS) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    mf = root / "processed" / "margin_interest.parquet"
    mg = pd.read_parquet(mf) if mf.exists() else None
    if mg is not None and (mg.empty or "usable_from" not in mg.columns):
        mg = None
    obs = atlas.build_obs(P, elig, iv, fins, mg, P.rebalance_idx())
    boundary = rules.SPLIT
    dmask, cmask = atlas.split(obs, boundary)
    res = atlas.mine(obs, dmask, min_obs=min_obs, min_periods=min_periods)
    n_tested = len(res)
    qv = st.bh_fdr(np.array([r["p"] for r in res])) if res else np.array([])
    for r, q in zip(res, qv):
        r["q"] = float(q)
    pos, neg = pick(res)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    chosen = pos + neg
    conf = [atlas.evaluate(obs, cmask, r["sub"], r["key"], r["dims"]) for r in chosen]
    if chosen:
        fam = f"atlas|{sha[:16]}"
        again = any(x["type"] == "confirmation_read" and x["payload"]["family"] == fam for x in ledger._rows())
        ledger.append_event("confirmation_read", {"family": fam, "rules": len(chosen), "tested_combinations": n_tested, "re_read": again})
    cp = np.array([c["p"] for c in conf], dtype=float)
    cq = st.bh_fdr(cp) if len(cp) else np.array([])

    def row(r, c, cq_):
        ys = atlas.year_summary(r)
        net = r["mean"] - atlas.ROUND_TRIP_A if r["mean"] > 0 else r["mean"] + atlas.ROUND_TRIP_A
        same = bool(np.isfinite(c["mean"]) and np.sign(c["mean"]) == np.sign(r["mean"]))
        return {"pattern": atlas.describe(obs, r), "conditions": len(r["sub"]), "obs": r["obs"], "periods": r["periods"],
                "mean_excess_21d": _r(r["mean"]), "t": _r(r["t"], 2), "q_over_all_tested": _r(r["q"]), "net_of_round_trip_A": _r(net),
                "same_sign_years": f'{ys["same_sign_years"]}/{ys["years_with_data"]}', "by_year": ys["by_year"],
                "confirmation": {"obs": c["obs"], "periods": c["periods"], "mean": _r(c["mean"]), "t": _r(c["t"], 2), "p": _r(c["p"]),
                                 "same_sign": same, "q_among_chosen": _r(cq_)},
                "replicated": bool(same and np.isfinite(c["p"]) and c["p"] < 0.05 and np.isfinite(cq_) and cq_ < 0.10)}

    rows = [row(r, c, q) for r, c, q in zip(chosen, conf, cq)]
    out = {"observations": {"discovery": int(dmask.sum()), "confirmation": int(cmask.sum()), "discovery_periods": int(len(np.unique(obs["period"][dmask]))),
                            "confirmation_periods": int(len(np.unique(obs["period"][cmask])))},
           "combinations_tested": n_tested, "bh_q_below_0.10_in_discovery": int((qv < 0.10).sum()) if n_tested else 0,
           "long_patterns": rows[:len(pos)], "avoid_patterns": rows[len(pos):], "replicated_count": sum(x["replicated"] for x in rows),
           "ledger_chain": ledger.verify(), "data_manifest_sha256": sha}
    if write:
        d = root / "results" / "atlas"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
