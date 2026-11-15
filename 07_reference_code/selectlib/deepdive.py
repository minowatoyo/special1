"""深掘りレポートの部品: 外から見た基準率（同じ状態の観測の、その後）、建玉の計算、関門。仕様は docs/w5_protocol.md「深掘りレポート」。出力は集計のみ。"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import atlas, extremes

CHAIN = ("liquidity", "ret21", "drawdown", "trend", "vol", "value")
MIN_CHAIN_OBS = 300
MIN_PER_PERIOD = 5
OBS_KEYS = tuple(atlas.CORE_FEATURES) + ("y", "period")


def obs_arrays(obs: dict) -> dict:
    """観測表から、基準率に使う配列だけを取り出す（保存用）。"""
    return {k: np.asarray(obs[k]) for k in OBS_KEYS}


def _class_stats(y: np.ndarray, period: np.ndarray, sel: np.ndarray) -> dict:
    n = int(sel.sum())
    out = {"obs": n, "periods": 0, "mean": None, "t": None, "share_positive": None}
    if n == 0:
        return out
    yy = y[sel]
    out["share_positive"] = float((yy > 0).mean())
    out["event_weighted_mean"] = float(yy.mean())
    s = pd.DataFrame({"p": period[sel], "y": yy}).groupby("p")["y"].agg(["mean", "count"])
    s = s[s["count"] >= MIN_PER_PERIOD]
    out["periods"] = int(len(s))
    if len(s):
        out["mean"] = float(s["mean"].mean())
    if len(s) >= 8 and s["mean"].std(ddof=1) > 0:
        out["t"] = float(s["mean"].mean() / (s["mean"].std(ddof=1) / math.sqrt(len(s))))
    return out


def reference_classes(arr: dict, codes: dict, j: int) -> dict:
    """銘柄 j の今の状態と、同じ状態だった観測の、その後の超過。条件 1 つずつ（singles）と、条件を順に重ねた連鎖（chain）。"""
    y, period = arr["y"], arr["period"]
    valid = codes.get("_valid", {})
    singles = {}
    for f in atlas.CORE_FEATURES:
        if f in valid and not bool(valid[f][j]):
            singles[f] = {"state": None, "note": "この銘柄では、計算できない"}
            continue
        v = int(codes[f][j])
        singles[f] = {"state": atlas.LABELS[f][v] if v < len(atlas.LABELS[f]) else str(v), **_class_stats(y, period, arr[f] == v)}
    chain, sel = [], np.ones(len(y), dtype=bool)
    for f in CHAIN:
        if f in valid and not bool(valid[f][j]):
            break
        v = int(codes[f][j])
        nxt = sel & (arr[f] == v)
        if nxt.sum() < MIN_CHAIN_OBS:
            chain.append({"added": atlas.LABELS[f][v], "stopped": f"観測が {int(nxt.sum())} で、{MIN_CHAIN_OBS} 未満。ここで止める"})
            break
        sel = nxt
        chain.append({"added": atlas.LABELS[f][v], **_class_stats(y, period, sel)})
    return {"all_observations": _class_stats(y, period, np.ones(len(y), dtype=bool)), "singles": singles, "chain": chain}


def position_size(price: float, ret21_hist: np.ndarray, va60: float, capital: float = 10_000_000, loss_budget: float = 0.01, max_weight: float = 0.10,
                  va_cap: float = 0.01, lot: int = 100, stress_floor: float = 0.05) -> dict:
    """建玉の計算: 株数 ＝ ⌊ 損失の予算 ÷（想定する下落 × 株価）÷ 100 ⌋ × 100。上限は、資金の max_weight、売買代金 60 日平均の va_cap。"""
    x = np.asarray(ret21_hist, dtype=float)
    x = x[np.isfinite(x)]
    out = {"capital_yen": int(capital), "loss_budget_yen": int(capital * loss_budget), "price": round(float(price), 1) if np.isfinite(price) else None}
    if len(x) < 100 or not np.isfinite(price) or price <= 0:
        return {**out, "shares": 0, "note": "履歴が足りない、または価格がない"}
    stress = max(abs(float(np.percentile(x, 5))), stress_floor)
    out.update({"stress_drop_21d_p5": round(stress, 4), "worst_21d_in_750d": round(float(x.min()), 4)})
    raw = capital * loss_budget / (stress * price)
    caps = {"loss_budget": raw, "max_weight": capital * max_weight / price, "liquidity_cap": (va_cap * va60 / price) if np.isfinite(va60) else 0.0}
    shares = int(math.floor(min(caps.values()) / lot)) * lot
    binding = min(caps, key=caps.get)
    out.update({"shares": max(shares, 0), "position_yen": int(max(shares, 0) * price), "weight": round(max(shares, 0) * price / capital, 4), "binding_constraint": binding,
                "one_lot_yen": int(lot * price), "loss_if_stress_yen": int(max(shares, 0) * price * stress)})
    if shares <= 0:
        out["note"] = "100 株が、制約（" + binding + "）に収まらない。買えない"
    return out


def recent_extremes(P, universe: np.ndarray, j: int, days: int = 5) -> list:
    """銘柄 j の、直近 days 営業日（最新日を含む）の、極端な出来事（名前と、何営業日前か）。"""
    ev = extremes.event_matrices(P, universe)
    T = len(P.dates) - 1
    out = []
    for name, m in ev.items():
        for k in range(days):
            if T - k >= 0 and m[T - k, j]:
                out.append({"event": name, "days_ago": k, "date": str(P.dates[T - k].date())})
    return sorted(out, key=lambda d: d["days_ago"])


def gate(extreme_events: list, limit_up_close_today: bool, shares: int, distress) -> dict:
    """関門: 検証済みの回避条件。回避 → 買えない → 回避条件なし、の順。"""
    reasons = []
    if limit_up_close_today:
        reasons.append("最新日に、ストップ高で引けた（翌朝の始値で買うと、5 日で、市場平均より約 3〜4% 負ける）")
    if extreme_events:
        reasons.append("直近 5 営業日に、極端な出来事（" + "、".join(sorted({e["event"] for e in extreme_events})) + "）。その後 1〜4 週は、市場平均より弱い傾向")
    cautions = ["財務危機の区分に当たる（発見期間では弱く、確認期間では有意でない。注意として表示）"] if distress else []
    if reasons:
        return {"verdict": "回避（確認済みの回避条件）", "reasons": reasons, "cautions": cautions}
    if shares <= 0:
        return {"verdict": "買えない（建玉の計算で 0 株）", "reasons": [], "cautions": cautions}
    return {"verdict": "回避条件なし", "reasons": [], "cautions": cautions}
