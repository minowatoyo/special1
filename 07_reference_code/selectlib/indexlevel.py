"""指数レベルの逆張り（TOPIX と 33 業種指数）。仕様は docs/w5_protocol.md「指数レベルの逆張りの検証」。
日 t の引け後に判定し、t+1 の始値で買い、t+1+h の始値で売る。出力は集計のみ。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forecastlib import stats as st

from . import breadth

NAMES = ("I1_5d_return_bottom5pct", "I2_below_60d_high_8pct", "I3_below_ma25_5pct")


def flags(topix: pd.DataFrame, min_hist: int = 250) -> pd.DataFrame:
    """TOPIX の 3 つの点灯（日 t の引け後に分かる値だけ。分位は、直前日までの拡張窓）。"""
    c = topix["close"]
    r5 = c / c.shift(5) - 1
    thr = r5.expanding(min_hist).quantile(0.05).shift(1)
    out = pd.DataFrame(index=topix.index)
    out[NAMES[0]] = (r5 <= thr).fillna(False)
    out[NAMES[1]] = ((c / c.rolling(60, min_periods=60).max() - 1) <= -0.08).fillna(False)
    out[NAMES[2]] = ((c / c.rolling(25, min_periods=25).mean() - 1) <= -0.05).fillna(False)
    return out


def fwd_open(o: np.ndarray, h: int) -> np.ndarray:
    """日 t に対する、t+1 の始値 → t+1+h の始値のリターン。"""
    f = np.full(len(o), np.nan)
    f[: -(h + 1)] = o[h + 1:] / o[1:-h] - 1.0
    return f


def market_test(F: np.ndarray, active: np.ndarray, h: int, lo: int, hi: int) -> dict:
    """点灯日（lo〜hi の中、h 営業日以上あいた日）の h 日先リターン − その期間の全日の平均 → 平均・t・p。"""
    rng = np.arange(len(F))
    inr = (rng >= lo) & (rng <= hi) & np.isfinite(F)
    base = float(np.nanmean(F[inr])) if inr.any() else float("nan")
    d = F - base
    r = breadth.episode_stats(d, active & inr, h)
    r.update({"baseline_mean_all_days": base, "active_days": int((active & inr).sum())})
    return r


def sector_test(close_rel: np.ndarray, F: np.ndarray, lookback: int, h: int, lo: int, hi: int, n_bottom: int = 5, min_sectors: int = 20) -> dict:
    """判断日 T（h 営業日ごと）に、対 TOPIX 相対リターン（lookback 営業日）が下位 n_bottom の業種の h 日先リターン − 全業種の平均。
    close_rel: [日, 業種] の対 TOPIX 相対価格（業種の終値 ÷ TOPIX の終値）。F: [日, 業種] の h 日先リターン。"""
    vals = []
    for T in range(max(lo, lookback), hi + 1, h):
        x = close_rel[T] / close_rel[T - lookback] - 1.0
        y = F[T]
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < min_sectors:
            continue
        idx = np.flatnonzero(m)
        bottom = idx[np.argsort(x[idx])[:n_bottom]]
        vals.append(float(y[bottom].mean() - y[m].mean()))
    v = np.array(vals)
    n = len(v)
    out = {"dates": int(n), "mean": float(v.mean()) if n else float("nan"), "t": float("nan"), "p": float("nan")}
    if n >= 8 and v.std(ddof=1) > 0:
        t = float(v.mean() / (v.std(ddof=1) / np.sqrt(n)))
        out.update({"t": t, "p": float(2 * st.t_sf(abs(t), n - 1))})
    return out
