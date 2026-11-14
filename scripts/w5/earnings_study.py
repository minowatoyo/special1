"""決算起因の急落（探索的。仕様は docs/w5_protocol.md 「追加の事前固定: 決算起因の急落」）。ローソク・規則の検証と同じ手順。出力は集計のみ。

  python scripts/w5/earnings_study.py        # 約 5〜10 分
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

BASE = ("rsi_lt30", "bb_below_lower", "kairi25_lt_m10", "crash_5d")


def builders() -> dict:
    out = {}
    for r in BASE:
        out[f"{r}&earn_yes"] = lambda x, r=r: x.sig[r].to_numpy() & x.earn5
        out[f"{r}&earn_no"] = lambda x, r=r: x.sig[r].to_numpy() & ~x.earn5
    return out


def pairs() -> list:
    return [(f"{r}:earn_no-earn_yes", f"{r}&earn_no", f"{r}&earn_yes") for r in BASE]


def tables(acc: dict, which: str) -> dict:
    t = rules.rule_table(acc, which)
    t.update(rules.diff_table(acc, which, pairs()))
    return t


def _fmt(t: dict) -> dict:
    return {"days": t["days"], "signals_per_day": round(t["signals_per_day"], 1) if np.isfinite(t["signals_per_day"]) else None,
            "mean_excess": round(t["mean"], 5) if np.isfinite(t["mean"]) else None, "t": round(t["t"], 2) if np.isfinite(t["t"]) else None,
            "p": round(t["p"], 4) if np.isfinite(t["p"]) else None}


def analyze(acc: dict, ledger: AppendOnlyLedger, data_sha: str, q: float = 0.10) -> dict:
    dis = tables(acc, "discovery")
    keys = list(dis)
    qv = st.bh_fdr(np.array([dis[k]["p"] for k in keys]))
    for k, v in zip(keys, qv):
        dis[k]["q"] = float(v)
    passed = [k for k in keys if np.isfinite(dis[k]["q"]) and dis[k]["q"] < q]
    conf = {}
    if passed:
        full = tables(acc, "confirmation")
        conf = {k: full[k] for k in passed}
        fam = f"earnings|{data_sha[:16]}"
        again = any(r["type"] == "confirmation_read" and r["payload"]["family"] == fam for r in ledger._rows())
        ledger.append_event("confirmation_read", {"family": fam, "rules": [f"{a}|h{b}" for a, b in passed], "re_read": again})
    res = []
    for k in keys:
        row = {"test": k[0], "h": k[1], "discovery": _fmt(dis[k]), "q": round(dis[k]["q"], 4) if np.isfinite(dis[k]["q"]) else None}
        if k in conf:
            c = conf[k]
            row["confirmation"] = _fmt(c)
            row["law_candidate"] = bool(np.isfinite(c["mean"]) and np.sign(c["mean"]) == np.sign(dis[k]["mean"]) and c["p"] < 0.05)
        res.append(row)
    return {"n_tests": int(np.isfinite([dis[k]["p"] for k in keys]).sum()), "discovery_passed": len(passed),
            "law_candidates": sum(1 for r in res if r.get("law_candidate")), "results": res}


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    elig = P.eligible_daily(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    acc = rules.run_pass(P, elig, builders(), fins, progress=lambda a, b: print(f"{a}/{b} 銘柄", flush=True))
    out = {"exploratory": True, "note": "段階 1 の結果を見たうえで追加した探索的な検証。確認は前向きの記録で行う。", **analyze(acc, ledger, rs.manifest_sha(root))}
    out["ledger_chain"] = ledger.verify()
    if write:
        d = root / "results" / "earnings"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1))
