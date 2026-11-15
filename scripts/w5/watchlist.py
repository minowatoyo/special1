"""指定した銘柄の前向きの記録（下げの原因の分類と、戻る・戻らないの予想）。仕様は docs/w5_protocol.md「気になった銘柄の診断と、指定の前向きの記録」。

  python scripts/w5/watchlist.py add --code 7203 --cause 一過性 --view 戻る --type 業績回復 --check "次の決算" --exit "下方修正が出たら撤回" [--note "..."]
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
TYPES = ("需給反発", "業績回復", "期待修正", "経営改革", "未分類")
HOLD = 21
HORIZONS = (21, 63, 126)
MIN_PER_CAUSE = 12


def add(root: Path, code: str, cause: str, view: str, note: str = "", asof: str | None = None, typ: str = "未分類", check: str = "", exit_: str = "",
        dossier: str | None = None) -> dict:
    if cause not in CAUSES or view not in VIEWS or typ not in TYPES:
        raise SystemExit(f"原因は {CAUSES}、予想は {VIEWS}、型は {TYPES} のどれか")
    snap = sp.snapshot(root, code, asof)
    snap.pop("_detail", None)
    if "error" in snap:
        return snap
    layers = None
    if dossier:
        dj = json.loads(Path(dossier).read_text(encoding="utf-8"))
        if dj.get("code") != snap["code"] or dj.get("asof") != snap["asof"]:
            return {"error": f"深掘りレポート（{dj.get('code')}、{dj.get('asof')}）が、記録する銘柄・日付（{snap['code']}、{snap['asof']}）と合わない。deep_dive.py を、実行し直す"}
        layers = dj.get("layers")
    ledger = AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")
    row = ledger.append_event("watch_add", {"code": snap["code"], "asof": snap["asof"], "cause": cause, "view": view, "type": typ, "check_when": check,
                                           "exit_if": exit_, "note": note, "layers": layers, "snapshot": snap})
    return {"recorded": True, "code": snap["code"], "asof": snap["asof"], "cause": cause, "view": view, "seq": row.get("seq"), "ledger": ledger.verify()}


def score(root: Path) -> dict:
    """採点: 翌営業日始値 → 22・64・127 営業日目の始値の、対象銘柄の平均との差（21・63・126 営業日）。"""
    ledger = AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")
    rows = ledger._rows()
    done = {(r["payload"]["add_seq"], r["payload"].get("h", HOLD)) for r in rows if r["type"] == "watch_outcome"}
    adds = [r for r in rows if r["type"] == "watch_add"]
    todo = [(r, h) for r in adds for h in HORIZONS if (r["seq"], h) not in done]
    if not todo:
        return {"scored": 0, "pending": 0, "scored_by_horizon": {}, "ledger": ledger.verify()}
    P, iv, _ = fs2.load_panel(root, None)
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    ci = {c: i for i, c in enumerate(P.codes)}
    by_h = {h: 0 for h in HORIZONS}
    pending = 0
    for r, h in todo:
        pl = r["payload"]
        t = int(np.searchsorted(P.dates.values, pd.Timestamp(pl["asof"]).to_datetime64(), side="left"))
        if t >= len(P.dates) or P.dates[t] != pd.Timestamp(pl["asof"]) or t + 1 + h >= len(P.dates):
            pending += h == HOLD
            continue
        y = seasonal.window_excess(P, elig[t], t + 1, t + 1 + h)
        v = y[ci[pl["code"]]] if pl["code"] in ci else np.nan
        base = {"add_seq": r["seq"], "h": h, "code": pl["code"], "cause": pl["cause"], "view": pl["view"], "type": pl.get("type", "未分類")}
        if not np.isfinite(v):
            ledger.append_event("watch_outcome", {**base, "status": "no_price"})
            continue
        ledger.append_event("watch_outcome", {**base, "status": "scored", "excess": round(float(v), 5), "excess_21d": round(float(v), 5) if h == HOLD else None,
                                              "buy": str(P.dates[t + 1].date()), "sell": str(P.dates[t + 1 + h].date())})
        by_h[h] += 1
    return {"scored": by_h[HOLD], "pending": int(pending), "scored_by_horizon": by_h, "ledger": ledger.verify()}


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")
    allout = [r["payload"] for r in ledger._rows() if r["type"] == "watch_outcome" and r["payload"].get("status") == "scored"]
    out = [o for o in allout if o.get("h", HOLD) == HOLD]
    n_add = sum(r["type"] == "watch_add" for r in ledger._rows())
    res = {"recorded": n_add, "scored": len(out), "by_cause": {}, "by_view": {}}
    for key, name in (("cause", "by_cause"), ("view", "by_view")):
        for k in sorted({o[key] for o in out}):
            x = np.array([o["excess_21d"] for o in out if o[key] == k])
            d = {"n": int(len(x)), "mean_excess_21d": round(float(x.mean()), 4), "share_positive": round(float((x > 0).mean()), 2), "median": round(float(np.median(x)), 4)}
            if name == "by_cause":
                d["conclusion"] = "件数が足りない（12 件未満）。結論を出さない" if len(x) < MIN_PER_CAUSE else "12 件以上（それでも、小さな標本）"
            res[name][k] = d
    res["by_type_and_horizon"] = {}
    for ty in sorted({o.get("type", "未分類") for o in allout}):
        res["by_type_and_horizon"][ty] = {}
        for h in HORIZONS:
            x = np.array([o.get("excess", o.get("excess_21d")) for o in allout if o.get("type", "未分類") == ty and o.get("h", HOLD) == h], dtype=float)
            if len(x):
                res["by_type_and_horizon"][ty][h] = {"n": int(len(x)), "mean_excess": round(float(x.mean()), 4), "share_positive": round(float((x > 0).mean()), 2)}
    adds = {r["seq"]: r["payload"] for r in ledger._rows() if r["type"] == "watch_add"}
    res["by_layer"] = {}
    for key in ("red_flag", "distress", "outside_21d_sign", "lens_daily", "lens_intraday", "agents", "s2_candidate", "sel_top15"):
        g = {}
        for o in allout:
            lay = (adds.get(o["add_seq"]) or {}).get("layers")
            if not lay or lay.get(key) is None:
                continue
            g.setdefault(str(lay[key]), {}).setdefault(o.get("h", HOLD), []).append(o.get("excess", o.get("excess_21d")))
        if g:
            res["by_layer"][key] = {v: {h: {"n": len(x), "mean_excess": round(float(np.mean(x)), 4), "share_positive": round(float(np.mean(np.array(x) > 0)), 2),
                                            "conclusion": "12 件未満。結論を出さない" if len(x) < MIN_PER_CAUSE else "12 件以上"} for h, x in sorted(hs.items())} for v, hs in sorted(g.items())}
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
    ap.add_argument("--type", default="未分類", help="需給反発 / 業績回復 / 期待修正 / 経営改革")
    ap.add_argument("--check", default="", help="確認時期（例: 2027-02 の 3Q 決算）")
    ap.add_argument("--exit", default="", help="反証条件（何が出たら撤回するか）")
    ap.add_argument("--dossier", default=None, help="deep_dive.py の出力（JSON）。各層の値を、一緒に記録する")
    a = ap.parse_args()
    root = Path(a.root)
    if a.cmd == "add":
        if not (a.code and a.cause and a.view):
            sys.exit("--code --cause --view が必要")
        r = add(root, a.code, a.cause, a.view, a.note, a.asof, a.type, a.check, a.exit, a.dossier)
    else:
        r = score(root) if a.cmd == "score" else summary(root)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
