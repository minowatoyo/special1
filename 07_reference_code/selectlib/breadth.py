"""市場の内部指標（騰落レシオ・25 日線割れの割合・新安値の割合・投げの割合・深い下落の割合）と、極端な日。

各日の対象銘柄（elig）で計算する。日 t の引け後までの情報だけを使う。極端な日の分位は、直前までの値だけから拡張窓で求める。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forecastlib import stats as st

NAMES = ("M1", "M2", "M3", "M4", "M5")
MIN_HIST = 250


def indicators(P, elig: np.ndarray) -> pd.DataFrame:
    c = pd.DataFrame(P.adj_close)
    vol = pd.DataFrame(P.volume)
    ok = pd.DataFrame(elig) & c.notna()
    ret1 = c / c.shift(1) - 1
    n = ok.sum(axis=1).replace(0, np.nan)
    adv = ((ret1 > 0) & ok).sum(axis=1)
    dec = ((ret1 < 0) & ok).sum(axis=1)
    m1 = 100 * adv.rolling(25, min_periods=20).sum() / dec.rolling(25, min_periods=20).sum().replace(0, np.nan)
    below = ((c < c.rolling(25, min_periods=25).mean()) & ok).sum(axis=1) / n
    newlow = ((c <= c.rolling(252, min_periods=200).min()) & ok).sum(axis=1) / n
    v = vol.where(vol > 0)
    capit = ((ret1 <= -0.03) & (v > 3 * v.rolling(20).mean().shift(1)) & ok).sum(axis=1) / n
    deep = ((c / c.shift(20) - 1 <= -0.15) & ok).sum(axis=1) / n
    out = pd.DataFrame({"M1": m1, "M2": below, "M3": newlow, "M4": capit, "M5": deep})
    out.index = P.dates
    return out


def extreme_flags(ind: pd.DataFrame, min_hist: int = MIN_HIST) -> pd.DataFrame:
    """M1 は過去の分位 5% 以下、M2〜M5 は 95% 以上の日。分位は直前（前日）までの拡張窓。"""
    out = pd.DataFrame(index=ind.index)
    for c in ind.columns:
        if c == "M1":
            thr = ind[c].expanding(min_hist).quantile(0.05).shift(1)
            out[c] = (ind[c] <= thr).fillna(False)
        else:
            thr = ind[c].expanding(min_hist).quantile(0.95).shift(1)
            out[c] = (ind[c] >= thr).fillna(False)
    return out


def topix_forward(P, h: int) -> np.ndarray:
    o = P.topix["open"].to_numpy()
    f = np.full(len(o), np.nan)
    f[: -(h + 1)] = o[h + 1:] / o[1:-h] - 1.0
    return f


def episode_stats(d: np.ndarray, active: np.ndarray, h: int, min_episodes: int = 5) -> dict:
    """点灯日の数が少ないときの検定。重ならない（h 営業日以上あいた）点灯日だけを順に拾い、その平均と t 検定（自由度 = 件数 − 1）。"""
    pos = np.flatnonzero(active)
    kept, last = [], -10 ** 9
    for p in pos:
        if p - last >= h:
            kept.append(p)
            last = p
    x = d[kept]
    n = len(x)
    if n < min_episodes or x.std(ddof=1) == 0:
        return {"days": int(n), "mean": float(x.mean()) if n else float("nan"), "t": float("nan"), "p": float("nan")}
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n)))
    return {"days": int(n), "mean": float(x.mean()), "t": t, "p": float(2 * st.t_sf(abs(t), n - 1))}
