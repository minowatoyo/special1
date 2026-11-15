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


# ---------------------------------------------------------------- ボラを合わせた比較（C）と、回避フィルター（B）
N_VOL_Q = 5
K_MATCH = 3                      # 段階 T1〜T3
MIN_CTRL = 5
UP_EVENTS = ("X1_limit_up_close", "X3_up_10pct", "V1_volume_spike_up")
DOWN_EVENTS = ("X2_limit_down_close", "X4_down_10pct", "V2_volume_spike_down")


def recent(ev: np.ndarray, days: int = 5) -> np.ndarray:
    """日 t を含む直近 days 営業日に、出来事があった。"""
    x = pd.DataFrame(ev.astype(np.float32)).rolling(days, min_periods=1).max().to_numpy() > 0.5
    return x


def vol_quintiles(sig: np.ndarray, tier: np.ndarray, kmax: int = K_MATCH) -> np.ndarray:
    """日ごと・段階ごとの、事前のボラの 5 分位（0 = 低 … 4 = 高）。対象外は −1。"""
    q = np.full(sig.shape, -1, dtype=np.int8)
    for t in range(sig.shape[0]):
        for k in range(kmax):
            m = (tier[t] == k) & np.isfinite(sig[t])
            if m.sum() < 50:
                continue
            edges = np.percentile(sig[t][m], [20, 40, 60, 80])
            q[t][m] = np.searchsorted(edges, sig[t][m], side="right")
    return q


def control_means(ex_h: np.ndarray, clean: np.ndarray, tier: np.ndarray, q: np.ndarray, kmax: int = K_MATCH) -> np.ndarray:
    """CM[t, k, q]: きれいな銘柄（直近に出来事がない）の、同じ日・段階・ボラ分位の平均超過。対照が MIN_CTRL 未満なら NaN。"""
    T = ex_h.shape[0]
    CM = np.full((T, kmax, N_VOL_Q), np.nan)
    for t in range(T):
        v = clean[t] & (tier[t] >= 0) & (tier[t] < kmax) & (q[t] >= 0) & np.isfinite(ex_h[t])
        if not v.any():
            continue
        key = tier[t][v].astype(int) * N_VOL_Q + q[t][v].astype(int)
        s = np.bincount(key, weights=ex_h[t][v], minlength=kmax * N_VOL_Q)
        c = np.bincount(key, minlength=kmax * N_VOL_Q)
        with np.errstate(invalid="ignore", divide="ignore"):
            CM[t] = np.where(c >= MIN_CTRL, s / np.maximum(c, 1), np.nan).reshape(kmax, N_VOL_Q)
    return CM


def matched_excess(ex_h: np.ndarray, tier: np.ndarray, q: np.ndarray, CM: np.ndarray, kmax: int = K_MATCH) -> np.ndarray:
    """出来事の銘柄の超過 − 対照の平均（段階 T1〜T3 だけ。ほかは NaN）。"""
    T, N = ex_h.shape
    ok = (tier >= 0) & (tier < kmax) & (q >= 0)
    tt = np.broadcast_to(np.arange(T)[:, None], (T, N))
    ctrl = np.full((T, N), np.nan)
    ctrl[ok] = CM[tt[ok], tier[ok].astype(int), q[ok].astype(int)]
    return ex_h - ctrl


def vol_effect_clean(ex_h: np.ndarray, clean: np.ndarray, tier: np.ndarray, q: np.ndarray, P, lo: int, hi: int, k: int = 1) -> list:
    """ボラの 5 分位ごとの、きれいな銘柄の平均超過（段階 k、月ごとの平均の平均）。"""
    out = []
    for qq in range(N_VOL_Q):
        t, j = np.nonzero(clean & (tier == k) & (q == qq) & np.isfinite(ex_h))
        m = (t >= lo) & (t <= hi)
        t, j = t[m], j[m]
        if not len(t):
            out.append(None)
            continue
        ym = np.asarray(P.dates.year[t] * 12 + P.dates.month[t])
        out.append(float(pd.Series(ex_h[t, j]).groupby(ym).mean().mean()))
    return out
