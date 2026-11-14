"""前向きの記録（W5）。最新日の引け後に、SEL-A/B/C1/C2 のスコアを追記専用の台帳に記録し、T+22 のデータがそろったら採点する。

  python scripts/w5/forward.py record [--asof YYYY-MM-DD]   # 最新日（または指定日以前の最後の営業日）の記録
  python scripts/w5/forward.py score                       # 結果が出た記録を採点
  python scripts/w5/forward.py summary                     # 21 営業日以上あけた記録だけで集計
主モデルは SEL-C1（事前固定）。学習は、そのときまでに売却が確定した期だけ。台帳: data/jquants/ledger/forward.jsonl（ハッシュ連鎖）。
出力は集計のみ。
"""
from __future__ import annotations

import argparse
import json
import subprocess
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
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import evalsel, features, model  # noqa: E402
from selectlib.panel import HOLD, Panel  # noqa: E402

PRIMARY = "SEL-C1"
PROTOCOL = "forward-v1"
SPACING = 21


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_panel(root: Path, asof: str | None):
    pr, fl, tp, iv, fins = rs.load(root)
    if asof:
        a = pd.Timestamp(asof)
        pr, fl, tp = pr[pr["date"] <= a], fl[fl["date"] <= a], tp[tp["date"] <= a]
        fins = fins[fins["usable_from"] <= a]
    return Panel.from_frames(pr, fl, tp), iv, fins


def record(root: Path, asof: str | None = None, models=None, top_n: int = 30) -> dict:
    P, iv, fins = load_panel(root, asof)
    ledger = AppendOnlyLedger(root / "ledger" / "forward.jsonl")
    T = len(P.dates) - 1
    grid = P.rebalance_idx()
    t_all = grid + [T]
    mask = P.eligible(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL, t_all)
    y, _, _ = P.labels(grid)
    y = np.vstack([np.where(mask[:-1], y, np.nan), np.full((1, y.shape[1]), np.nan)])
    sd = features.standardized({**features.chart_features(P, t_all), **features.fins_features(P, fins, t_all)}, mask)
    yr = model.rank_gauss(y, mask)
    data_sha = rs.manifest_sha(root)
    asof_s = str(P.dates[T].date())
    have = {(r["payload"]["asof"], r["payload"]["model"], r["payload"]["data_manifest_sha256"]) for r in ledger._rows() if r["type"] == "selection"}
    added = []
    for mname, (kind, names) in (models or rs.MODELS).items():
        if (asof_s, mname, data_sha) in have:
            continue
        try:
            sc = model.predict_last(sd, names, yr, mask, kind=kind)
        except Exception as e:  # noqa: BLE001
            added.append({"model": mname, "skipped": f"{type(e).__name__}"})
            continue
        cols = np.flatnonzero(np.isfinite(sc))
        order = cols[np.argsort(-sc[cols], kind="stable")]
        payload = {"asof": asof_s, "model": mname, "primary": mname == PRIMARY, "protocol": PROTOCOL, "data_manifest_sha256": data_sha,
                   "code_version": code_version(), "eligible": int(len(cols)), "top": [[P.codes[j], round(float(sc[j]), 6)] for j in order[:top_n]],
                   "scores": [[P.codes[j], round(float(sc[j]), 5)] for j in cols]}
        ledger.append_event("selection", payload)
        added.append({"model": mname, "eligible": int(len(cols))})
    return {"asof": asof_s, "recorded": added, "ledger": ledger.verify()}


def score(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "forward.jsonl")
    rows = ledger._rows()
    done = {r["payload"]["selection_hash"] for r in rows if r["type"] == "outcome"}
    todo = [r for r in rows if r["type"] == "selection" and r["hash"] not in done]
    if not todo:
        return {"scored": 0, "pending": 0, "ledger": ledger.verify()}
    P, _, _ = load_panel(root, None)
    di = {d: i for i, d in enumerate(P.dates)}
    ci = {c: i for i, c in enumerate(P.codes)}
    n = scored = 0
    for r in todo:
        p = r["payload"]
        T = di.get(pd.Timestamp(p["asof"]))
        if T is None or T + 1 + HOLD >= len(P.dates):
            n += 1
            continue
        b, s = T + 1, T + 1 + HOLD
        tp = P.topix["open"].iloc[s] / P.topix["open"].iloc[b] - 1
        codes = [c for c, _ in p["scores"] if c in ci]
        sc = np.array([v for c, v in p["scores"] if c in ci])
        j = np.array([ci[c] for c in codes])
        ret = P.adj_open[s, j] / P.adj_open[b, j] - 1
        ex = ret - tp
        ok = np.isfinite(ex)
        top15 = [ci[c] for c, _ in p["top"][:15] if c in ci]
        ex_top = P.adj_open[s, top15] / P.adj_open[b, top15] - 1 - tp
        payload = {"selection_hash": r["hash"], "asof": p["asof"], "model": p["model"], "primary": p["primary"], "sell_date": str(P.dates[s].date()),
                   "top15_mean_excess": float(np.nanmean(ex_top)) if np.isfinite(ex_top).any() else None, "universe_mean_excess": float(np.nanmean(ex[ok])),
                   "ic": evalsel.rank_ic(sc, ex, np.ones(len(sc), bool)), "n_scored": int(ok.sum()), "top15_missing": int((~np.isfinite(ex_top)).sum())}
        ledger.append_event("outcome", payload)
        scored += 1
    return {"scored": scored, "pending": n, "ledger": ledger.verify()}


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "forward.jsonl")
    outs = [r["payload"] for r in ledger._rows() if r["type"] == "outcome"]
    res = {}
    for m in sorted({o["model"] for o in outs}):
        os_ = sorted([o for o in outs if o["model"] == m], key=lambda o: o["asof"])
        kept, last = [], None
        for o in os_:                                                   # 21 営業日（約 29 暦日）以上あけた記録だけ
            d = pd.Timestamp(o["asof"])
            if last is None or (d - last).days >= 29:
                kept.append(o)
                last = d
        gain = np.array([o["top15_mean_excess"] - o["universe_mean_excess"] for o in kept if o["top15_mean_excess"] is not None])
        ic = np.array([o["ic"] for o in kept if o["ic"] is not None and np.isfinite(o["ic"])])
        t = lambda x: float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else None  # noqa: E731
        res[m] = {"independent_periods": len(kept), "top15_minus_universe_mean": float(gain.mean()) if len(gain) else None, "t": t(gain),
                  "ic_mean": float(ic.mean()) if len(ic) else None, "ic_t": t(ic), "primary": os_[0]["primary"]}
    return {"models": res, "note": "独立な記録が増えるまで（目安 12 期以上）、結論を出さない"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("record", "score", "summary"))
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--asof", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    print(json.dumps({"record": lambda: record(root, a.asof), "score": lambda: score(root), "summary": lambda: summary(root)}[a.cmd](), ensure_ascii=False, indent=1))
