"""個別株の弾力性（下げた後に戻る癖）の検証。仕様は docs/w5_protocol.md「個別株の弾力性の検証」（事前固定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/elasticity_study.py        # 約 5〜10 分
発見期間で BH（q < 0.10）を通り、予測と同じ向き（高 − 低 > 0）のものだけ、確認期間を 1 度読む。
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
from selectlib import elastic, events, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

HS = (5, 21)
FLOOR_VA = 5e7
HIST_VA = schema.WIDE_VA_MIN


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(d: dict) -> dict:
    return {k: (_r(v, 2) if k == "t" else _r(v) if isinstance(v, float) else v) for k, v in d.items()}


def main(root: Path, write=True, min_history: int = 250) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    n = len(P.dates)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig_hist = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=min_history, va_min=HIST_VA)
    floor = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=min_history, va_min=FLOOR_VA)
    B = elastic.build(P, elig_hist, floor)
    Q, ev, fl_ = B["Q"], B["ev"], B["floor"]
    grp = {d: elastic.groups(B["scores"][d], fl_) for d in elastic.DEFS}
    ex = {h: events.excess_matrix(Q, B["ok"], h) for h in HS}
    out = {"split": str(rules.SPLIT.date()), "events_all": int(ev.sum()), "events_in_decision_universe": int((ev & fl_).sum()),
           "stocks_used": int(len(B["cols"])), "tests": []}
    rows = []
    for d in elastic.DEFS:
        for h in HS:
            disc = elastic.contrast(Q, ev & fl_, *grp[d], ex[h], h, 0, b - h - 2)
            rows.append({"def": d, "h": h, "discovery": disc})
    live = [r for r in rows if r["discovery"]["p"] is not None]
    if live:
        qv = st.bh_fdr(np.array([r["discovery"]["p"] for r in live], dtype=float))
        for r, q in zip(live, qv):
            r["discovery"]["q"] = float(q)
    passed = [r for r in live if r["discovery"]["q"] < 0.10 and r["discovery"]["diff_mean"] > 0]
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    for r in passed:                                                            # 通過したものだけ、確認期間を読む
        c = elastic.contrast(Q, ev & fl_, *grp[r["def"]], ex[r["h"]], r["h"], b, n - 1)
        r["confirmation"] = c
        r["law_candidate"] = bool(c["diff_mean"] is not None and c["diff_mean"] > 0 and c["p"] is not None and c["p"] < 0.05)
    if passed:
        ledger.append_event("confirmation_read", {"family": f"elasticity_v1|{sha[:16]}", "tests": [f'{r["def"]}|h={r["h"]}' for r in passed], "tested": len(live)})
    ledger.append_event("elasticity_discovery", {"tested": len(live), "passed": [f'{r["def"]}|h={r["h"]}' for r in passed], "data_manifest_sha256": sha})
    for r in rows:
        o = {"test": f'{r["def"]}|h={r["h"]}', "discovery": _fmt(r["discovery"]),
             "confirmation": _fmt(r["confirmation"]) if "confirmation" in r else "未読（発見期間を通過していない）"}
        if "law_candidate" in r:
            o["law_candidate"] = r["law_candidate"]
        out["tests"].append(o)
    out["passed_discovery"] = [f'{r["def"]}|h={r["h"]}' for r in passed]
    out["law_candidates"] = [f'{r["def"]}|h={r["h"]}' for r in passed if r.get("law_candidate")]
    out["ledger_chain"] = ledger.verify()
    out["data_manifest_sha256"] = sha
    if write:
        d = root / "results" / "elasticity"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
