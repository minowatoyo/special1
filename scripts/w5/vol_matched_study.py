"""ボラを合わせた比較（診断）。仕様は docs/w5_protocol.md「極端な動きの回避フィルターと、ボラを合わせた比較」C（事前固定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/vol_matched_study.py        # 約 10 分
極端な出来事の後の弱さが、「高ボラ株は低リターン」で説明されるかを、事前のボラを合わせた対照で確かめる。
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
from selectlib import elastic, events, extremes, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def verdict(raw_d, raw_c, m_d, m_c) -> str:
    """ボラで説明されるか。合わせた平均が、同じ符号・両期間 p<0.05 なら「ボラでは説明できない」。大きさが元の半分未満、または確認で p≥0.05 なら「ボラで説明される」。"""
    if None in (raw_d["mean"], raw_c["mean"], m_d["mean"], m_c["mean"]) or m_d["p"] is None or m_c["p"] is None:
        return "判定不能（月が足りない）"
    same = np.sign(m_d["mean"]) == np.sign(raw_d["mean"]) and np.sign(m_c["mean"]) == np.sign(raw_c["mean"])
    if same and m_d["p"] < 0.05 and m_c["p"] < 0.05:
        return "ボラでは説明できない"
    if abs(m_c["mean"]) < 0.5 * abs(raw_c["mean"]) or m_c["p"] >= 0.05 or not same:
        return "ボラで説明される"
    return "一部"


def main(root: Path, write=True, min_history: int = extremes.HIST_MIN) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    n = len(P.dates)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=min_history, va_min=extremes.VA_MIN)
    tier = np.where(elig, extremes.tier_matrix(P.va60()), -1)
    ev = extremes.event_matrices(P, elig)
    anyev = np.zeros(elig.shape, dtype=bool)
    for v in ev.values():
        anyev |= v
    clean = elig & ~extremes.recent(anyev, 5)
    sig = elastic.sigma_daily(P.adj_close, lag=5)
    q = extremes.vol_quintiles(sig, tier)
    ok = elig & events.executable_at_open(P)
    out = {"split": str(rules.SPLIT.date()), "cells": [], "vol_effect_clean_tierT2_by_quintile": {}}
    for h in extremes.HS:
        ex = events.excess_matrix(P, ok, h)
        CM = extremes.control_means(ex, clean, tier, q)
        M = extremes.matched_excess(ex, tier, q, CM)
        out["vol_effect_clean_tierT2_by_quintile"][f"h={h}"] = {sp: [_r(v) for v in extremes.vol_effect_clean(ex, clean, tier, q, P, lo, hi)]
                                                                for sp, (lo, hi) in {"discovery": (0, b - h - 2), "confirmation": (b, n - 1)}.items()}
        for e in extremes.EVENTS:
            for k in range(extremes.K_MATCH):
                res = {}
                for sp, (lo, hi) in {"discovery": (0, b - h - 2), "confirmation": (b, n - 1)}.items():
                    res[sp] = {"raw": extremes.cell(P, ev[e], tier, k, ex, h, lo, hi), "matched": extremes.cell(P, ev[e], tier, k, M, h, lo, hi)}
                if res["discovery"]["raw"]["mean"] is None:
                    continue
                f = lambda d: {kk: (_r(vv, 2) if kk == "t" else _r(vv) if isinstance(vv, float) else vv) for kk, vv in d.items() if kk in ("events", "months", "mean", "t", "p")}  # noqa: E731
                out["cells"].append({"cell": f"{e}|{extremes.TIERS[k][0]}|h={h}", "discovery": {"raw": f(res["discovery"]["raw"]), "matched": f(res["discovery"]["matched"])},
                                     "confirmation": {"raw": f(res["confirmation"]["raw"]), "matched": f(res["confirmation"]["matched"])},
                                     "verdict": verdict(res["discovery"]["raw"], res["confirmation"]["raw"], res["discovery"]["matched"], res["confirmation"]["matched"])})
    v = [c["verdict"] for c in out["cells"]]
    out["verdict_counts"] = {k: v.count(k) for k in sorted(set(v))}
    if write:
        d = root / "results" / "vol_matched"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
