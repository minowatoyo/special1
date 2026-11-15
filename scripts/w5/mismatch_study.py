"""期待と実態の不一致（割安 × 財務の強さ）、材料のない下げ、財務危機の回避。仕様は docs/w5_protocol.md（事前固定。9 検定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/mismatch_study.py        # 約 10 分
発見期間で BH（q < 0.10）を通り、予測と同じ向きのものだけ、確認期間を 1 度読む。
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
from selectlib import elastic, events, fscore, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

FLOOR_VA = 5e7
COST = 0.006
STEP = 21


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(d: dict) -> dict:
    return {k: (_r(v, 2) if k in ("t", "stocks_per_date_A", "stocks_per_date_B") else _r(v) if isinstance(v, float) else v) for k, v in d.items()}


def _val(d: dict):
    return d.get("mean", d.get("diff_mean"))


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    n = len(P.dates)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig_hist = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    floor = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=FLOOR_VA)
    B = elastic.build(P, elig_hist, floor)
    Q, cols, ev, fl_ = B["Q"], B["cols"], B["ev"] & B["floor"], B["floor"]
    D = fscore.daily(P, fins)
    F, dis, by, news = D["F"][:, cols], D["distress"][:, cols], D["book_yield"][:, cols], D["news"][:, cols]
    cheap, _ = elastic.groups(by, fl_)                                         # 簿価利回りの上位 1/3
    with np.errstate(invalid="ignore"):
        f_hi, f_lo = fl_ & (F >= fscore.F_HIGH), fl_ & (F <= fscore.F_LOW)
        distress = fl_ & (dis > 0.5)
    good = cheap & f_hi
    ex = {h: events.excess_matrix(Q, B["ok"], h) for h in (5, 21, 63, 126)}
    grid = list(range(250, n, STEP))
    X = lambda A, Bm, h, lo, hi: fscore.xsec(Q.dates, A, Bm, ex[h], grid, h, lo, hi)                    # noqa: E731
    C = lambda hi_, lo_, h, lo, hi: elastic.contrast(Q, ev, hi_, lo_, ex[h], h, lo, hi)                 # noqa: E731
    tests = [("M1_cheap_Fhigh_minus_Flow", 63, +1, lambda lo, hi: X(cheap & f_hi, cheap & f_lo, 63, lo, hi)),
             ("M2_cheap_Fhigh_minus_Flow", 126, +1, lambda lo, hi: X(cheap & f_hi, cheap & f_lo, 126, lo, hi)),
             ("M3_cheap_and_Fhigh_vs_universe", 63, +1, lambda lo, hi: X(good, None, 63, lo, hi)),
             ("M4_cheap_and_Fhigh_vs_universe", 126, +1, lambda lo, hi: X(good, None, 126, lo, hi)),
             ("M5_drop_no_news_minus_news", 5, +1, lambda lo, hi: C(~news, news, 5, lo, hi)),
             ("M6_drop_no_news_minus_news", 21, +1, lambda lo, hi: C(~news, news, 21, lo, hi)),
             ("M7_drop_cheap_Fhigh_minus_rest", 21, +1, lambda lo, hi: C(good, ~good, 21, lo, hi)),
             ("M8_drop_cheap_Fhigh_minus_rest", 63, +1, lambda lo, hi: C(good, ~good, 63, lo, hi)),
             ("M9_distress_vs_universe", 63, -1, lambda lo, hi: X(distress, None, 63, lo, hi))]
    rows = []
    for name, h, sign, fn in tests:
        rows.append({"test": f"{name}|h={h}", "h": h, "sign": sign, "fn": fn, "discovery": fn(0, b - h - 2)})
    live = [r for r in rows if r["discovery"].get("p") is not None]
    if live:
        qv = st.bh_fdr(np.array([r["discovery"]["p"] for r in live], dtype=float))
        for r, q in zip(live, qv):
            r["discovery"]["q"] = float(q)
    passed = [r for r in live if r["discovery"]["q"] < 0.10 and np.sign(_val(r["discovery"])) == r["sign"]]
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    for r in passed:
        c = r["fn"](b, n - 1)
        r["confirmation"] = c
        r["law_candidate"] = bool(_val(c) is not None and np.sign(_val(c)) == r["sign"] and c.get("p") is not None and c["p"] < 0.05)
    if passed:
        ledger.append_event("confirmation_read", {"family": f"mismatch_v1|{sha[:16]}", "tests": [r["test"] for r in passed], "tested": len(live)})
    ledger.append_event("mismatch_discovery", {"tested": len(live), "passed": [r["test"] for r in passed], "data_manifest_sha256": sha})
    out = {"split": str(rules.SPLIT.date()), "columns_available": D["availability"], "signals_available_share": {k: _r(v, 2) for k, v in D["signals_available_share"].items()},
           "coverage_last_day": {"floor": int(fl_[-1].sum()), "with_F": int((fl_[-1] & np.isfinite(F[-1])).sum()), "cheap_and_F_high": int(good[-1].sum()),
                                 "distress": int(distress[-1].sum()), "with_book_yield": int((fl_[-1] & np.isfinite(by[-1])).sum())},
           "drop_events": int(ev.sum()), "drop_events_with_news_share": _r(float(news[ev].mean())) if ev.any() else None, "tests": []}
    for r in rows:
        d = r["discovery"]
        v = _val(d)
        o = {"test": r["test"], "predicted_sign": "+" if r["sign"] > 0 else "-", "discovery": _fmt(d),
             "same_sign_as_predicted": bool(v is not None and np.sign(v) == r["sign"]),
             "net_of_round_trip(0.6%)": _r(abs(v) - COST) if v is not None else None,
             "confirmation": _fmt(r["confirmation"]) if "confirmation" in r else "未読（発見期間を通過していない）"}
        if "law_candidate" in r:
            o["law_candidate"] = r["law_candidate"]
        out["tests"].append(o)
    out["passed_discovery"] = [r["test"] for r in passed]
    out["law_candidates"] = [r["test"] for r in passed if r.get("law_candidate")]
    out["ledger_chain"] = ledger.verify()
    out["data_manifest_sha256"] = sha
    if write:
        d = root / "results" / "mismatch"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
