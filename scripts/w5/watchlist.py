"""指定した銘柄の前向きの記録（下げの原因の分類と、戻る・戻らないの予想）。仕様は docs/w5_protocol.md「気になった銘柄の診断と、指定の前向きの記録」。

  python scripts/w5/watchlist.py add --code 7203 --cause 一過性 --view 戻る [--note "..."]   # 記録（最新日の引け後の状態を保存）
  python scripts/w5/watchlist.py score                                                       # 22 営業日目の始値までそろったものを採点
  python scripts/w5/watchlist.py summary                                                     # 原因の分類ごと・予想ごとの集計
原因の分類: 一過性 / 構造的 / 需給 / 連想 / 不明。予想: 戻る / 戻らない。台帳は追記専用（ledger/watchlist.jsonl）。
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
import schema  # noqa: E402
import stock_profile as sp  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import seasonal  # noqa: E402

CAUSES = ("一過性", "構造的", "需給", "連想", "不明")
VIEWS = ("戻る", "戻らない")
HOLD = 21
MIN_PER_CAUSE = 12


def add(root: Path, code: str, cause: str, view: str, note: str = "", asof: str | None = None) -> dict:
    if cause not in CAUSES or view not in VIEWS:
        raise SystemExit(f"原因は {CAUSES}、予想は {VIEWS} のどれか")
    snap = sp.snapshot(root, code, asof)
    snap.pop("_detail", None)
    if "error" in snap:
        return snap
    ledger = AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")
    row = ledger.append_event("watch_add", {"code": snap["code"], "asof": snap["asof"], "cause": cause, "view": view, "note": note, "snapshot": snap})
    return {"recorded": True, "code": snap["code"], "asof": snap["asof"], "cause": cause, "view": view, "seq": row.get("seq"), "ledger": ledger.verify()}


def score(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")
    rows = ledger._rows()
    done = {r["payload"]["add_seq"] for r in rows if r["type"] == "watch_outcome"}
    todo = [r for r in rows if r["type"] == "watch_add" and r["seq"] not in done]
    if not todo:
        return {"scored": 0, "pending": 0, "ledger": ledger.verify()}
    P, iv, _ = fs2.load_panel(root, None)
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    ci = {c: i for i, c in enumerate(P.codes)}
    scored = pending = 0
    for r in todo:
        pl = r["payload"]
        t = int(np.searchsorted(P.dates.values, pd.Timestamp(pl["asof"]).to_datetime64(), side="left"))
        if t >= len(P.dates) or P.dates[t] != pd.Timestamp(pl["asof"]) or t + 1 + HOLD >= len(P.dates):
            pending += 1
            continue
        y = seasonal.window_excess(P, elig[t], t + 1, t + 1 + HOLD)
        v = y[ci[pl["code"]]] if pl["code"] in ci else np.nan
        if not np.isfinite(v):
            ledger.append_event("watch_outcome", {"add_seq": r["seq"], "status": "no_price", "code": pl["code"]})
            continue
        ledger.append_event("watch_outcome", {"add_seq": r["seq"], "status": "scored", "code": pl["code"], "cause": pl["cause"], "view": pl["view"],
                                              "excess_21d": round(float(v), 5), "buy": str(P.dates[t + 1].date()), "sell": str(P.dates[t + 1 + HOLD].date())})
        scored += 1
    return {"scored": scored, "pending": pending, "ledger": ledger.verify()}


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")
    out = [r["payload"] for r in ledger._rows() if r["type"] == "watch_outcome" and r["payload"].get("status") == "scored"]
    n_add = sum(r["type"] == "watch_add" for r in ledger._rows())
    res = {"recorded": n_add, "scored": len(out), "by_cause": {}, "by_view": {}}
    for key, name in (("cause", "by_cause"), ("view", "by_view")):
        for k in sorted({o[key] for o in out}):
            x = np.array([o["excess_21d"] for o in out if o[key] == k])
            d = {"n": int(len(x)), "mean_excess_21d": round(float(x.mean()), 4), "share_positive": round(float((x > 0).mean()), 2), "median": round(float(np.median(x)), 4)}
            if name == "by_cause":
                d["conclusion"] = "件数が足りない（12 件未満）。結論を出さない" if len(x) < MIN_PER_CAUSE else "12 件以上（それでも、小さな標本）"
            res[name][k] = d
    hit = [(o["view"] == "戻る") == (o["excess_21d"] > 0) for o in out]
    res["view_hit_rate"] = round(float(np.mean(hit)), 2) if hit else None
    res["ledger"] = ledger.verify()
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "score", "summary"])
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--code")
    ap.add_argument("--cause")
    ap.add_argument("--view")
    ap.add_argument("--note", default="")
    ap.add_argument("--asof")
    a = ap.parse_args()
    root = Path(a.root)
    if a.cmd == "add":
        if not (a.code and a.cause and a.view):
            sys.exit("--code --cause --view が必要")
        r = add(root, a.code, a.cause, a.view, a.note, a.asof)
    else:
        r = score(root) if a.cmd == "score" else summary(root)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
