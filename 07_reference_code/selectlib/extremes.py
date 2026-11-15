"""全銘柄での極端な出来事の漂流（段階別・コスト後）。仕様は docs/w5_protocol.md「全銘柄での極端な出来事の漂流と、信用売りの精査」。
出来事は日 t の引け後に確定。買いは t+1 の始値、売りは t+1+h の始値。出力は集計のみ。
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd

from . import seasonal

TIERS = (("T1_ge500M", 5e8, np.inf, 0.0030), ("T2_50M_500M", 5e7, 5e8, 0.0060), ("T3_20M_50M", 2e7, 5e7, 0.0090),
         ("T4_10M_20M", 1e7, 2e7, 0.0150), ("T5_5M_10M", 5e6, 1e7, 0.0200))
VA_MIN, HIST_MIN = 5e6, 120
EVENTS = ("X1_limit_up_close", "X2_limit_down_close", "X3_up_10pct", "X4_down_10pct", "V1_volume_spike_up", "V2_volume_spike_down")
HS = (5, 21)
BIG, VOL_MULT, VOL_MOVE = 0.10, 5.0, 0.03
MIN_PER_MONTH, MIN_MONTHS = 3, 12
BORROW_ANNUAL = 0.0115


def tier_matrix(va60: np.ndarray) -> np.ndarray:
    """売買代金 60 日平均 → 段階（0 = T1 … 4 = T5、範囲外は −1）。"""
    out = np.full(va60.shape, -1, dtype=np.int8)
    for k, (_, lo, hi, _) in enumerate(TIERS):
        out[(va60 >= lo) & (va60 < hi)] = k
    return out


def daily_excess(adj_close: np.ndarray, universe: np.ndarray) -> np.ndarray:
    r = np.full(adj_close.shape, np.nan)
    r[1:] = adj_close[1:] / adj_close[:-1] - 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        um = np.nanmean(np.where(universe, r, np.nan), axis=1)
    return r - um[:, None]


def event_matrices(P, universe: np.ndarray) -> dict:
    """6 種類の出来事の真偽 [日, 銘柄]（対象銘柄の日だけ）。"""
    ex = daily_excess(P.adj_close, universe)
    up = P.limit_up & np.isfinite(P.adj_close) & (P.adj_close >= P.adj_high * (1 - 1e-9))
    dn = P.limit_down & np.isfinite(P.adj_close) & (P.adj_close <= P.adj_low * (1 + 1e-9))
    to = pd.DataFrame(P.turnover).fillna(0.0)
    to60 = to.rolling(60, min_periods=40).mean().shift(1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        spike = np.isfinite(to60) & (to60 > 0) & (P.turnover >= VOL_MULT * to60)
        e = {"X1_limit_up_close": up, "X2_limit_down_close": dn, "X3_up_10pct": (ex >= BIG) & ~up, "X4_down_10pct": (ex <= -BIG) & ~dn,
             "V1_volume_spike_up": spike & (ex >= VOL_MOVE), "V2_volume_spike_down": spike & (ex <= -VOL_MOVE)}
    return {k: v & universe & np.isfinite(ex) for k, v in e.items()}


def cell(P, ev: np.ndarray, tier: np.ndarray, k: int, ex_h: np.ndarray, h: int, lo: int, hi: int) -> dict:
    """セル（出来事 × 段階 k × 保有 h）の、起きた暦月ごとの平均超過 → 平均・t・p。"""
    t, j = np.nonzero(ev & (tier == k) & np.isfinite(ex_h))
    m = (t >= lo) & (t <= hi)
    t, j = t[m], j[m]
    y = ex_h[t, j]
    out = {"events": int(len(y)), "months": 0, "mean": None, "t": None, "p": None, "event_weighted_mean": float(y.mean()) if len(y) else None,
           "share_positive": float((y > 0).mean()) if len(y) else None}
    if not len(y):
        return out
    ym = np.asarray(P.dates.year[t] * 12 + P.dates.month[t])
    df = pd.DataFrame({"ym": ym, "y": y})
    g = df.groupby("ym")["y"].agg(["mean", "count"])
    g = g[g["count"] >= MIN_PER_MONTH]
    out["months"] = int(len(g))
    if len(g) >= MIN_MONTHS and g["mean"].std(ddof=1) > 0:
        st_ = seasonal.tstat(g["mean"].to_numpy(), lags=math.ceil(h / 21))
        out.update({"mean": st_["mean"], "t": st_["t"] if np.isfinite(st_["t"]) else None, "p": st_["p"] if np.isfinite(st_["p"]) else None})
    return out


def net_after_cost(mean: float | None, tier_k: int, h: int) -> dict:
    """買い側（平均 > 0）と売り側（平均 < 0）の、コスト後の値（月の平均ベース）。"""
    if mean is None:
        return {"side": None, "net": None}
    c = TIERS[tier_k][3]
    if mean >= 0:
        return {"side": "buy", "net": mean - c}
    return {"side": "sell(信用売り)", "net": -mean - c - BORROW_ANNUAL * h / 252.0}
