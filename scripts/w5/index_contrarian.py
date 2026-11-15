"""指数レベルの逆張り（TOPIX と 33 業種）。仕様は docs/w5_protocol.md「指数レベルの逆張りの検証」（事前固定。10 検定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/index_contrarian.py        # 1 分ほど
発見期間で BH（q < 0.10）を通り、平均 > 0 のものだけ、確認期間を 1 度読む。
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
from forecastlib import stats as st  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import indexlevel, rules  # noqa: E402

HS = (5, 21)
ETF_COST = 0.002


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(d: dict) -> dict:
    return {k: (_r(v, 2) if k == "t" else _r(v) if isinstance(v, float) else v) for k, v in d.items()}


def load(root: Path):
    tp = pd.read_parquet(root / "processed" / "topix_daily.parquet").sort_values("date").set_index("date")
    f = root / "processed" / "indices_daily.parquet"
    ix = pd.read_parquet(f) if f.exists() else None
    return tp, ix


def main(root: Path, write=True) -> dict:
    tp, ix = load(root)
    dates = tp.index
    n = len(dates)
    b = int(np.searchsorted(dates.values, rules.SPLIT.to_datetime64(), side="left"))
    fl = indexlevel.flags(tp)
    out = {"split": str(rules.SPLIT.date()), "topix_days": int(n), "tests": []}
    rows = []
    for name in indexlevel.NAMES:
        for h in HS:
            F = indexlevel.fwd_open(tp["open"].to_numpy(dtype=float), h)
            act = fl[name].to_numpy()
            rows.append({"test": f"{name}|h={h}", "fn": (lambda lo, hi, F=F, act=act, h=h: indexlevel.market_test(F, act, h, lo, hi)), "h": h})
    if ix is not None and not ix.empty:
        sec = ix[(ix["index_code"] >= "0040") & (ix["index_code"] <= "0060")]
        if sec["index_code"].nunique() >= 20:
            cl = sec.pivot(index="date", columns="index_code", values="close").reindex(dates)
            op = sec.pivot(index="date", columns="index_code", values="open").reindex(dates)
            op = op.where(op.notna(), cl)
            rel = (cl.div(tp["close"], axis=0)).to_numpy()
            out["sectors"] = int(cl.shape[1])
            for lb, nm in ((5, "S1_rel5d_bottom5"), (21, "S2_rel21d_bottom5")):
                for h in HS:
                    Fs = np.column_stack([indexlevel.fwd_open(op.iloc[:, j].to_numpy(dtype=float), h) for j in range(op.shape[1])])
                    rows.append({"test": f"{nm}|h={h}", "fn": (lambda lo, hi, Fs=Fs, lb=lb, h=h: indexlevel.sector_test(rel, Fs, lb, h, lo, hi)), "h": h})
        else:
            out["sectors_note"] = f"業種指数が見つからない（{sec['index_code'].nunique()} 本）。業種の 4 検定は、飛ばす"
    for r in rows:
        r["discovery"] = r["fn"](0, b - r["h"] - 2)
    live = [r for r in rows if r["discovery"].get("p") is not None and np.isfinite(r["discovery"]["p"])]
    if live:
        qv = st.bh_fdr(np.array([r["discovery"]["p"] for r in live], dtype=float))
        for r, q in zip(live, qv):
            r["discovery"]["q"] = float(q)
    passed = [r for r in live if r["discovery"]["q"] < 0.10 and r["discovery"]["mean"] > 0]
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    for r in passed:
        c = r["fn"](b, n - 1)
        r["confirmation"] = c
        r["law_candidate"] = bool(c["mean"] is not None and np.isfinite(c["mean"]) and c["mean"] > 0 and np.isfinite(c["p"]) and c["p"] < 0.05)
    if passed:
        ledger.append_event("confirmation_read", {"family": f"index_contrarian_v1|{sha[:16]}", "tests": [r["test"] for r in passed], "tested": len(live)})
    ledger.append_event("index_contrarian_discovery", {"tested": len(live), "passed": [r["test"] for r in passed], "data_manifest_sha256": sha})
    for r in rows:
        d = r["discovery"]
        o = {"test": r["test"], "discovery": _fmt(d), "after_etf_cost(0.2%)": _r(d["mean"] - ETF_COST) if np.isfinite(d["mean"]) else None,
             "confirmation": _fmt(r["confirmation"]) if "confirmation" in r else "未読（通らなかった、または平均が負）"}
        if "law_candidate" in r:
            o["law_candidate"] = r["law_candidate"]
        out["tests"].append(o)
    out["tests_run"] = len(live)
    out["passed_discovery"] = [r["test"] for r in passed]
    out["law_candidates"] = [r["test"] for r in passed if r.get("law_candidate")]
    out["ledger_chain"] = ledger.verify()
    out["data_manifest_sha256"] = sha
    if write:
        d = root / "results" / "index_contrarian"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
