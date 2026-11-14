"""S2（配当の権利取り）の前向きの記録。仕様は docs/w5_protocol.md「S2 の前向きの記録」。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/forward_s2.py record [--asof YYYY-MM-DD]   # データ更新のたびに
  python scripts/w5/forward_s2.py score                        # 権利付き最終日を過ぎたものを採点
  python scripts/w5/forward_s2.py summary
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
from selectlib import seasonal  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

LEAD = seasonal.RUN_DAYS_S2
HORIZON_DAYS = 100                     # 買いの予定日が、asof から約 3 か月以内の権利月を記録する
COST_B = 0.0060
PROTOCOL = "forward-s2-v1"


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def est_dates(year: int, month: int) -> tuple:
    """権利付き最終日と買いの予定日の目安（祝日を無視した平日で数える。記録の対象月を決めるためだけに使う）。"""
    last = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
    wd = pd.bdate_range(end=last, periods=LEAD + 5)
    L = wd[-3]                                                      # 月末の平日の 2 営業日前
    e = pd.bdate_range(end=L, periods=LEAD + 1)[0]
    return L, e


def load_panel(root: Path, asof: str | None):
    pr, fl, tp, iv, fins = rs.load(root)
    if asof:
        a = pd.Timestamp(asof)
        pr, fl, tp = pr[pr["date"] <= a], fl[fl["date"] <= a], tp[tp["date"] <= a]
        fins = fins[fins["usable_from"] <= a]
    return Panel.from_frames(pr, fl, tp), iv, fins


def record(root: Path, asof: str | None = None) -> dict:
    P, iv, fins = load_panel(root, asof)
    ledger = AppendOnlyLedger(root / "ledger" / "forward_s2.jsonl")
    T = len(P.dates) - 1
    asof_d = P.dates[T]
    elig = P.eligible(iv, schema.WIDE_MARKETS, [T], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
    va60 = P.va60()[T]
    fa = seasonal.fins_asof(P, fins, [T])
    with np.errstate(divide="ignore", invalid="ignore"):
        yld = fa["div"][0] * fa["r_disc"][0] / P.adj_close[T]
    fy = fa["fy_month"][0]
    tr = seasonal.tiers(va60)
    sha = rs.manifest_sha(root)
    added, skipped = [], []
    for k in range(0, 6):
        d = (asof_d + pd.offsets.MonthBegin(1) * k) if k else asof_d
        ym = pd.Period(d, freq="M")
        L, e = est_dates(ym.year, ym.month)
        if not (e > asof_d and (e - asof_d).days <= HORIZON_DAYS):
            continue
        month = ym.month
        rights = (fy == month) | (((fy + 5) % 12) + 1 == month)
        g = rights & elig & np.isfinite(yld) & (yld > 0)
        if g.sum() < seasonal.MIN_GROUP:
            skipped.append({"rights_month": str(ym), "reason": f"銘柄が少ない（{int(g.sum())}）"})
            continue
        j = np.flatnonzero(g)
        payload = {"asof": str(asof_d.date()), "rights_month": str(ym), "est_last_day_with_rights": str(L.date()), "est_entry_day": str(e.date()),
                   "group": [[P.codes[x], round(float(yld[x]), 5), int(tr[x])] for x in j], "n": int(len(j)), "protocol": PROTOCOL,
                   "data_manifest_sha256": sha, "code_version": code_version()}
        ledger.append_event("s2_record", payload)
        added.append({"rights_month": str(ym), "stocks": int(len(j)), "est_entry_day": str(e.date()), "top_quintile": int(len(j) * 0.2),
                      "tier_counts(A,B,C)": [int((tr[j] == q).sum()) for q in range(3)]})
    return {"asof": str(asof_d.date()), "recorded": added, "skipped": skipped, "ledger": ledger.verify()}


def score(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "forward_s2.jsonl")
    rows = ledger._rows()
    done = {r["payload"]["rights_month"] for r in rows if r["type"] == "s2_outcome"}
    recs = [r for r in rows if r["type"] == "s2_record"]
    months = sorted({r["payload"]["rights_month"] for r in recs} - done)
    if not months:
        return {"scored": 0, "pending": 0, "ledger": ledger.verify()}
    P, iv, _ = load_panel(root, None)
    mo = seasonal.months(P)
    pos = {str(p): i for i, p in enumerate(mo["period"])}
    scored, pending, late = 0, 0, 0
    for ym in months:
        i = pos.get(ym)
        if i is None or (i == len(mo["last"]) - 1 and P.dates[-1] < pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0) - pd.offsets.BDay(0)):
            pending += 1                                          # その月の最終営業日まで、データがそろっていない
            continue
        lag = 2 if P.dates[mo["last"][i]] >= seasonal.T2_START else 3
        L = mo["last"][i] - lag
        e = L - LEAD
        ok = [r for r in recs if r["payload"]["rights_month"] == ym and pd.Timestamp(r["payload"]["asof"]) < P.dates[e]]
        if not ok:
            late += 1
            ledger.append_event("s2_outcome", {"rights_month": ym, "status": "no_forward_record", "note": "買いの日より前の記録がない（前向きとして数えない）"})
            continue
        r = ok[-1]
        g = r["payload"]["group"]
        ci = {c: j for j, c in enumerate(P.codes)}
        idx = [ci[c] for c, _, _ in g if c in ci]
        yl = np.array([y for c, y, _ in g if c in ci])
        tier = np.array([t for c, _, t in g if c in ci])
        elig_e = P.eligible(iv, schema.WIDE_MARKETS, [e - 1], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
        y_all = seasonal.window_excess(P, elig_e, e, L)
        y = y_all[idx]
        fin = np.isfinite(y)
        if fin.sum() < seasonal.MIN_GROUP:
            ledger.append_event("s2_outcome", {"rights_month": ym, "status": "too_few", "n": int(fin.sum())})
            continue
        rk = yl.argsort().argsort() / len(yl)

        def mean_of(m):
            m = m & fin
            return float(y[m].mean()) if m.sum() >= 3 else None

        b_rk = np.where(tier == 1, yl, np.nan)
        bsel = tier == 1
        b_rank = np.full(len(yl), np.nan)
        if bsel.sum() >= 5:
            b_rank[bsel] = yl[bsel].argsort().argsort() / bsel.sum()
        a_idx = np.flatnonzero(tier == 0)
        top15a = None
        if len(a_idx) >= 20:
            o = a_idx[np.argsort(-yl[a_idx])[:15]]
            top15a = float(np.nanmean(y[o])) if np.isfinite(y[o]).any() else None
        payload = {"rights_month": ym, "status": "scored", "record_hash": r["hash"], "record_asof": r["payload"]["asof"], "entry_day": str(P.dates[e].date()),
                   "exit_day": str(P.dates[L].date()), "n": int(fin.sum()), "top_quintile": mean_of(rk >= 0.8), "top_decile": mean_of(rk >= 0.9),
                   "tier_B_top_quintile": mean_of(b_rank >= 0.8), "tier_A_top15": top15a, "group_mean": mean_of(np.ones(len(yl), bool)), "records_before_entry": len(ok)}
        del b_rk
        ledger.append_event("s2_outcome", payload)
        scored += 1
    return {"scored": scored, "pending": pending, "no_forward_record": late, "ledger": ledger.verify()}


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "forward_s2.jsonl")
    outs = [r["payload"] for r in ledger._rows() if r["type"] == "s2_outcome" and r["payload"].get("status") == "scored"]
    outs.sort(key=lambda o: o["entry_day"])

    def stat(key, cost=0.0):
        v = np.array([o[key] - cost for o in outs if o.get(key) is not None], dtype=float)
        if len(v) == 0:
            return {"months": 0}
        t = float(v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))) if len(v) > 2 and v.std(ddof=1) > 0 else None
        return {"months": int(len(v)), "mean": round(float(v.mean()), 5), "t": round(t, 2) if t is not None else None, "share_positive": round(float((v > 0).mean()), 2)}

    return {"scored_months": len(outs), "top_quintile": stat("top_quintile"), "top_decile": stat("top_decile"),
            "tier_B_top_quintile_net_of_round_trip": stat("tier_B_top_quintile", COST_B), "tier_A_top15": stat("tier_A_top15"), "group_mean": stat("group_mean"),
            "reference(過去の検証)": {"discovery_top_quintile": 0.0184, "confirmation_top_quintile": 0.0144, "tier_B_net_confirmation": 0.0101},
            "note": "12 か月以上たまるまで、結論を出さない。隣の月の窓は重なる"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("record", "score", "summary"))
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--asof", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    print(json.dumps({"record": lambda: record(root, a.asof), "score": lambda: score(root), "summary": lambda: summary(root)}[a.cmd](), ensure_ascii=False, indent=1))
