"""日次の前向きの記録（紙の上の売買と、指数の状態）。仕様は docs/w5_protocol.md「前向きの記録（日次）: 紙の上の売買と、指数の状態」。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/forward_events.py record [--asof YYYY-MM-DD]   # データを更新するたびに（最新日の引け後の状態を記録）
  python scripts/w5/forward_events.py score                         # 結果がそろったものを採点
  python scripts/w5/forward_events.py summary                       # 集計（候補 30 件、指数 10 エピソード たまるまで結論を出さない）
実際の売買はしない。台帳 ledger/forward_events.jsonl は追記専用（ハッシュ連鎖）。
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
import forward_s2 as fs2  # noqa: E402
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import events, exclude, extremes, indexlevel  # noqa: E402

COST = 0.004
BORROW = 0.0115
HOLD = 5
MIN_VA = 5e7
MIN_CANDIDATES, MIN_EPISODES = 30, 10
PROTOCOL = "forward-events-v1"


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _topix(root: Path, asof: str | None) -> pd.DataFrame:
    tp = pd.read_parquet(root / "processed" / "topix_daily.parquet").sort_values("date").set_index("date")
    return tp[tp.index <= pd.Timestamp(asof)] if asof else tp


def record(root: Path, asof: str | None = None) -> dict:
    P, iv, fins = fs2.load_panel(root, asof)
    T = len(P.dates) - 1
    ledger = AppendOnlyLedger(root / "ledger" / "forward_events.jsonl")
    asof_s = str(P.dates[T].date())
    if any(r["type"] == "fe_record" and r["payload"]["asof"] == asof_s for r in ledger._rows()):
        return {"asof": asof_s, "status": "already_recorded", "ledger": ledger.verify()}
    elig = P.eligible(iv, schema.WIDE_MARKETS, [T], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
    va = P.va60()[T]
    up = P.limit_up[T] & np.isfinite(P.adj_close[T]) & (P.adj_close[T] >= P.adj_high[T] * (1 - 1e-9)) & elig
    js = np.flatnonzero(up)
    cands = []
    if len(js):
        cls = events.attr_at(P, iv, np.full(len(js), T), js, "margin_class")
        mgf = root / "processed" / "margin_interest.parquet"
        sd = None
        if mgf.exists():
            mg = pd.read_parquet(mgf)
            if len(mg) and "usable_from" in mg.columns:
                row = exclude.margin_matrices(P, mg, [T])["short_days"][0]
                m = elig & np.isfinite(row)
                if m.sum() >= 30:
                    sd = (row, float(np.percentile(row[m], 100 / 3)))
        for j, c in zip(js, cls):
            loan = str(c) == events.LOAN_CLASS
            klass = "unknown" if sd is None or not np.isfinite(sd[0][j]) else "light" if sd[0][j] <= sd[1] else "other"
            cands.append({"code": P.codes[j], "close": _r(float(P.raw_close[T, j]), 2), "va60": int(va[j]) if np.isfinite(va[j]) else None, "loan": bool(loan), "short_balance": klass,
                          "qualifies": bool(loan and klass == "light" and np.isfinite(va[j]) and va[j] >= MIN_VA)})
    tp = _topix(root, asof)
    fl = indexlevel.flags(tp)
    idx = {k: bool(fl[k].iloc[-1]) for k in indexlevel.NAMES}
    payload = {"asof": asof_s, "protocol": PROTOCOL, "limit_up_closes_in_universe": int(len(js)), "candidates": [c for c in cands if c["qualifies"]],
               "limit_up_closes_detail_counts": {"loan": int(sum(c["loan"] for c in cands)), "light": int(sum(c["short_balance"] == "light" for c in cands))},
               "index_flags": idx, "data_manifest_sha256": rs.manifest_sha(root), "code_version": fs2.code_version()}
    ledger.append_event("fe_record", payload)
    return {"asof": asof_s, "status": "recorded", "candidates": len(payload["candidates"]), "limit_up_closes": int(len(js)), "index_flags": idx, "ledger": ledger.verify()}


def score(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "forward_events.jsonl")
    rows = ledger._rows()
    done = {(r["payload"]["rec_seq"], r["payload"]["kind"]) for r in rows if r["type"] == "fe_outcome"}
    recs = [r for r in rows if r["type"] == "fe_record"]
    todo = [r for r in recs if (r["seq"], "candidates") not in done or (r["seq"], "index") not in done]
    if not todo:
        return {"scored_candidate_days": 0, "scored_index_days": 0, "ledger": ledger.verify()}
    P, iv, _ = fs2.load_panel(root, None)
    elig_cache = {}
    tp = _topix(root, None)
    o = tp["open"].to_numpy(dtype=float)
    base = {h: indexlevel.fwd_open(o, h) for h in (5, 21)}
    ci = {c: i for i, c in enumerate(P.codes)}
    n_c = n_i = 0
    for r in todo:
        pl = r["payload"]
        t = int(np.searchsorted(P.dates.values, pd.Timestamp(pl["asof"]).to_datetime64(), side="left"))
        if t >= len(P.dates) or P.dates[t] != pd.Timestamp(pl["asof"]):
            continue
        if (r["seq"], "candidates") not in done and t + 1 + HOLD < len(P.dates):
            if t not in elig_cache:
                elig_cache[t] = P.eligible(iv, schema.WIDE_MARKETS, [t], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
            with np.errstate(divide="ignore", invalid="ignore"):
                fwd = P.adj_open[t + 1 + HOLD] / P.adj_open[t + 1] - 1.0
            um = float(np.nanmean(np.where(elig_cache[t], fwd, np.nan)))
            at_limit = P.limit_up & (P.adj_open >= P.adj_high * (1 - 1e-9))
            res = []
            cost = COST + BORROW * HOLD / 252.0
            for c in pl["candidates"]:
                j = ci.get(c["code"])
                if j is None:
                    res.append({"code": c["code"], "status": "no_price"})
                    continue
                sellable = bool(np.isfinite(P.raw_open[t + 1, j]) and not at_limit[t + 1, j])
                blocked = bool(not np.isfinite(P.raw_open[t + 1 + HOLD, j]) or at_limit[t + 1 + HOLD, j])
                if not sellable:
                    res.append({"code": c["code"], "status": "not_sellable"})
                elif blocked:
                    res.append({"code": c["code"], "status": "cover_blocked"})
                else:
                    raw = -float(fwd[j])
                    res.append({"code": c["code"], "status": "ok", "short_raw": _r(raw), "short_net_neutral": _r(raw + um - cost)})
            ledger.append_event("fe_outcome", {"rec_seq": r["seq"], "kind": "candidates", "asof": pl["asof"], "universe_mean_5d": _r(um), "results": res})
            n_c += 1
        if (r["seq"], "index") not in done and t + 1 + 21 < len(P.dates) and t < len(tp) and tp.index[t] == P.dates[t]:
            out = {}
            for h in (5, 21):
                allm = np.nanmean(base[h][: t + 1]) if np.isfinite(base[h][: t + 1]).any() else float("nan")
                out[f"h={h}"] = {"ret": _r(base[h][t]), "baseline_mean_all_days_to_date": _r(allm), "excess": _r(base[h][t] - allm)}
            ledger.append_event("fe_outcome", {"rec_seq": r["seq"], "kind": "index", "asof": pl["asof"], "flags": pl["index_flags"], "outcomes": out})
            n_i += 1
    return {"scored_candidate_days": n_c, "scored_index_days": n_i, "ledger": ledger.verify()}


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "forward_events.jsonl")
    rows = ledger._rows()
    recs = [r for r in rows if r["type"] == "fe_record"]
    outs = [r["payload"] for r in rows if r["type"] == "fe_outcome"]
    cand = [x for o in outs if o["kind"] == "candidates" for x in o["results"]]
    ok = [x for x in cand if x["status"] == "ok"]
    res = {"recorded_days": len(recs), "first": recs[0]["payload"]["asof"] if recs else None, "last": recs[-1]["payload"]["asof"] if recs else None}
    net = np.array([x["short_net_neutral"] for x in ok], dtype=float)
    res["short_candidates"] = {"recorded_total": int(sum(len(r["payload"]["candidates"]) for r in recs)), "scored_ok": int(len(ok)), "not_sellable": int(sum(x["status"] == "not_sellable" for x in cand)),
                               "cover_blocked": int(sum(x["status"] == "cover_blocked" for x in cand)),
                               "mean_net_after_cost": _r(net.mean()) if len(net) else None, "share_positive": _r(float((net > 0).mean()), 2) if len(net) else None,
                               "worst": _r(float(net.min())) if len(net) else None, "backtest_reference": "確認期間 +6.3%、発見期間 +5.1%（軽い かつ 5,000 万円以上）",
                               "conclusion": "件数が足りない（30 件未満）。結論を出さない" if len(ok) < MIN_CANDIDATES else "30 件以上（それでも、標本は小さい）"}
    idx = {}
    for o in [o for o in outs if o["kind"] == "index"]:
        for k, v in o["flags"].items():
            if v:
                idx.setdefault(k, []).append((o["asof"], o["outcomes"]))
    res["index_states"] = {}
    for k, lst in idx.items():
        d = {}
        for h in (5, 21):
            kept, last = [], None
            for a, oc in sorted(lst):
                dt = pd.Timestamp(a)
                if last is None or np.busday_count(last.date(), dt.date()) >= h:
                    kept.append(oc[f"h={h}"]["excess"])
                    last = dt
            x = np.array([v for v in kept if v is not None], dtype=float)
            d[f"h={h}"] = {"episodes": int(len(x)), "mean_excess": _r(x.mean()) if len(x) else None, "share_positive": _r(float((x > 0).mean()), 2) if len(x) else None}
        d["conclusion"] = "エピソードが足りない（10 未満）。結論を出さない" if d["h=21"]["episodes"] < MIN_EPISODES else "10 エピソード以上（それでも、標本は小さい）"
        res["index_states"][k] = d
    res["ledger"] = ledger.verify()
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["record", "score", "summary"])
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--asof")
    a = ap.parse_args()
    root = Path(a.root)
    r = record(root, a.asof) if a.cmd == "record" else score(root) if a.cmd == "score" else summary(root)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
