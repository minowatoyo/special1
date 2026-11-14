"""底打ち・上昇しやすい局面（家族 1・12 検定）と、下がり方の特徴（家族 2・探索的・22 検定）。仕様は docs/w5_protocol.md。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/bottom_study.py        # 約 10〜20 分
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
from selectlib import rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def _fmt(t):
    f = lambda x, n: round(x, n) if x is not None and np.isfinite(x) else None  # noqa: E731
    return {"days": t["days"], "signals_per_day": f(t["signals_per_day"], 1), "mean_excess": f(t["mean"], 5), "t": f(t["t"], 2), "p": f(t["p"], 4)}


def run_family(P, elig, fins, builders, extras, level_names, pairs, label, ledger, data_sha, q=0.10, feats=True):
    acc = rules.run_pass(P, elig, builders, fins, extras=extras, feats=feats, progress=lambda a, b: print(f"[{label}] {a}/{b} 銘柄", flush=True))

    def tables(which):
        t = rules.rule_table(acc, which, names=set(level_names))
        if pairs:
            t.update(rules.diff_table(acc, which, pairs))
        return t

    dis = tables("discovery")
    keys = list(dis)
    qv = st.bh_fdr(np.array([dis[k]["p"] for k in keys]))
    for k, v in zip(keys, qv):
        dis[k]["q"] = float(v)
    passed = [k for k in keys if np.isfinite(dis[k]["q"]) and dis[k]["q"] < q]
    conf = {}
    if passed:
        full = tables("confirmation")
        conf = {k: full[k] for k in passed}
        fam = f"{label}|{data_sha[:16]}"
        again = any(r["type"] == "confirmation_read" and r["payload"]["family"] == fam for r in ledger._rows())
        ledger.append_event("confirmation_read", {"family": fam, "rules": [f"{a}|h{b}" for a, b in passed], "re_read": again})
    rows = []
    for k in keys:
        row = {"test": k[0], "h": k[1], "discovery": _fmt(dis[k]), "q": round(dis[k]["q"], 4) if np.isfinite(dis[k]["q"]) else None,
               "net_of_round_trip_cost": round(dis[k]["net_of_round_trip_cost"], 5) if np.isfinite(dis[k]["net_of_round_trip_cost"]) else None,
               "by_liquidity_tertile": dis[k]["mean_by_liquidity_tertile(low,mid,high)"]}
        if k in conf:
            c = conf[k]
            row["confirmation"] = _fmt(c)
            row["law_candidate"] = bool(np.isfinite(c["mean"]) and np.sign(c["mean"]) == np.sign(dis[k]["mean"]) and c["p"] < 0.05)
        rows.append(row)
    return acc, {"n_tests": int(np.isfinite([dis[k]["p"] for k in keys]).sum()), "discovery_passed": len(passed),
                 "law_candidates": sum(1 for r in rows if r.get("law_candidate")), "results": rows}


def descriptive_levels(acc, names) -> list:
    """家族 2: 特徴ごとの yes / no の水準（発見期間。検定の族には入れない）。"""
    t = rules.rule_table(acc, "discovery", names=set(names))
    return [{"state": k[0], "h": k[1], **_fmt(v)} for k, v in sorted(t.items())]


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    elig = P.eligible_daily(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    extras = {"u3": rules.u3_matrix(P, fins, elig), "mkt_down": rules.mkt_down(P)}
    f1b = rules.bottom_up_builders()
    _, fam1 = run_family(P, elig, fins, f1b, extras, list(f1b), [], "bottom_up", ledger, sha)
    f2b = rules.drop_builders()
    pairs = [(f"{d}:yes-no", f"drop&{d}_yes", f"drop&{d}_no") for d in rules.DROP_DESCRIPTORS]
    acc2, fam2 = run_family(P, elig, fins, f2b, extras, ["drop"], pairs, "drop_descriptors", ledger, sha)
    out = {"family1_bottom_and_uptrend": fam1, "family2_drop_descriptors_exploratory": fam2,
           "family2_descriptive_levels_discovery": descriptive_levels(acc2, [n for n in f2b if n != "drop"]), "ledger_chain": ledger.verify(),
           "data_manifest_sha256": sha}
    if write:
        d = root / "results" / "bottom"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    r = main(Path(ap.parse_args().root))
    brief = {k: v for k, v in r.items() if k != "family2_descriptive_levels_discovery"}
    print(json.dumps(brief, ensure_ascii=False, indent=1))
    print("特徴ごとの yes / no の水準（発見期間）は summary.json の family2_descriptive_levels_discovery")
