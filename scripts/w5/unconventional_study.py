"""型破りの探索: 強制的な売買と、会社の癖（12 検定）。仕様は docs/w5_protocol.md「型破りの探索」（事前固定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/unconventional_study.py        # 約 5〜10 分
発見期間で BH（q < 0.10）を通り、予測と同じ向きのものだけ、確認期間を 1 度読む。通らなかったものは、確認期間を読まない。
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
from selectlib import events, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

ROUND_TRIP_B = 0.006


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(s: dict) -> dict:
    return {k: (_r(v, 2) if k == "t" else _r(v) if isinstance(v, float) else v) for k, v in s.items()}


def main(root: Path, write=True, q_level: float = 0.10) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    n = len(P.dates)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    ok = elig & rules.executable(P)
    ev, missing = events.build(P, iv, fins, elig, P.va60())
    E = {}
    rows = []
    for name, h, sign in events.TESTS:
        key = f"{name}|h={h}"
        if name in missing:
            rows.append({"test": key, "skipped": missing[name]})
            continue
        if h not in E:
            E[h] = events.excess_matrix(P, ok, h)
        t, j = ev[name]
        d = events.study(P, E[h], t, j, h, 0, b - h - 2)
        rows.append({"test": key, "name": name, "h": h, "predicted_sign": "+" if sign > 0 else "-", "sign": sign, "discovery": d})
    live = [r for r in rows if "discovery" in r and r["discovery"]["p"] is not None]
    if live:
        qv = st.bh_fdr(np.array([r["discovery"]["p"] for r in live], dtype=float))
        for r, q in zip(live, qv):
            r["discovery"]["q"] = float(q)
    passed = [r for r in live if r["discovery"]["q"] < q_level and np.sign(r["discovery"]["mean"]) == r["sign"]]
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    for r in passed:                                                            # 通過したものだけ、確認期間を読む
        c = events.study(P, E[r["h"]], *ev[r["name"]], r["h"], b, n - 1)
        r["confirmation"] = c
        r["law_candidate"] = bool(c["mean"] is not None and np.sign(c["mean"]) == r["sign"] and c["p"] is not None and c["p"] < 0.05)
    if passed:
        ledger.append_event("confirmation_read", {"family": f"unconventional_v1|{sha[:16]}", "tests": [r["test"] for r in passed], "tested": len(live)})
    ledger.append_event("unconventional_discovery", {"tested": len(live), "passed": [r["test"] for r in passed], "skipped": [r["test"] for r in rows if "skipped" in r],
                                                     "data_manifest_sha256": sha})
    out_rows = []
    for r in rows:
        if "skipped" in r:
            out_rows.append(r)
            continue
        d = r["discovery"]
        o = {"test": r["test"], "predicted_sign": r["predicted_sign"], "discovery": _fmt(d),
             "same_sign_as_predicted": bool(d["mean"] is not None and np.sign(d["mean"]) == r["sign"]),
             "net_of_round_trip_B(0.6%)": _r(abs(d["mean"]) - ROUND_TRIP_B) if d["mean"] is not None else None,
             "confirmation": _fmt(r["confirmation"]) if "confirmation" in r else "未読（発見期間を通過していない）"}
        if "law_candidate" in r:
            o["law_candidate"] = r["law_candidate"]
        out_rows.append(o)
    out = {"split": str(rules.SPLIT.date()), "tests_run": len(live), "passed_discovery": [r["test"] for r in passed], "law_candidates": [r["test"] for r in passed if r.get("law_candidate")],
           "results": out_rows, "ledger_chain": ledger.verify(), "data_manifest_sha256": sha}
    if write:
        d = root / "results" / "unconventional"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
