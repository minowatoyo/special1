"""信用残・空売り比率の目印（K1〜K5）の検証。仕様は docs/w5_protocol.md 「信用残・空売り比率による『投げ売り』『売り枯れ』の目印」。
ローカル PC で実行（要: backfill_extra.py と build_processed.py の完了）。出力は集計のみ。

  python scripts/w5/margin_study.py        # 約 10〜15 分
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
from selectlib import margin, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def _fmt(t):
    f = lambda x, n: round(x, n) if x is not None and np.isfinite(x) else None  # noqa: E731
    return {"days": t["days"], "signals_per_day": f(t["signals_per_day"], 1), "mean_excess": f(t["mean"], 5), "t": f(t["t"], 2), "p": f(t["p"], 4)}


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    out_dir = root / "processed"
    mg, sr = pd.read_parquet(out_dir / "margin_interest.parquet"), pd.read_parquet(out_dir / "short_ratio.parquet")
    elig = P.eligible_daily(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL)
    kmat = margin.all_flags(P, mg, sr, iv)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    builders = {"drop": rules.drop_builders()["drop"], **rules.margin_builders(margin.NAMES)}
    acc = rules.run_pass(P, elig, builders, fins, extras={"kmat": kmat}, feats=True, progress=lambda a, b: print(f"{a}/{b} 銘柄", flush=True))
    pairs = [(f"{k}:yes-no", f"drop&{k}_yes", f"drop&{k}_no") for k in margin.NAMES]

    def tables(which):
        return rules.diff_table(acc, which, pairs)

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
        fam = f"margin|{sha[:16]}"
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
    # 記述: 目印ごとの yes / no の水準（発見期間）と、データのある割合（下げ状態の銘柄の日）
    levels = rules.rule_table(acc, "discovery", names={n for n in builders if n != "drop"})
    cov = {}
    for k in margin.NAMES:
        fm, vm = kmat[k]
        e = elig & vm
        cov[k] = {"eligible_stockdays_with_data_share": round(float(e.sum() / max(elig.sum(), 1)), 3), "flag_yes_share_among_with_data": round(float((fm & elig).sum() / max(e.sum(), 1)), 4)}
    out = {"n_tests": int(np.isfinite([dis[k]["p"] for k in keys]).sum()), "discovery_passed": len(passed), "law_candidates": sum(1 for r in rows if r.get("law_candidate")),
           "results": rows, "coverage": cov, "levels_discovery": [{"state": k[0], "h": k[1], **_fmt(v)} for k, v in sorted(levels.items())],
           "ledger_chain": ledger.verify(), "data_manifest_sha256": sha}
    if write:
        d = root / "results" / "margin"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1))
