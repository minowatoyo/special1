"""チャートシグナルのイベントスタディ（その銘柄自身の履歴で、シグナルの後に何が起きたか）。

各シグナル D（真偽値）と期間 h について、次の二つを調べる。
  * 平均への効果: シグナルの後の上げ下げの偏り
  * ばらつきへの効果: シグナルの後は値幅の予測が狭すぎ／広すぎか

効果の大きさ（b、ばらつきの比）は、ボラティリティで標準化した先 h 日リターン z を D に回帰して求める。
ただし、重なりのある h 日リターンを、長く続く状態（「200 日線より上」など）に回帰すると、
Newey–West の t 値でも「有意」が出すぎる（合成データで確認した）。そこで検定は逆回帰で行う:
    u_{t+1} = a + b'·S_t + e,   S_t = 直近 h 日のうちシグナルが点灯していた日数
u は 1 日の標準化リターン。先 h 日リターンと D_t の共分散は、1 日リターンと S_t の共分散に等しいので、
同じ帰無仮説（シグナルの後のリターンに偏りがない）を、重なりのない 1 日リターンで検定できる
（Hodrick 1992 の方法）。p 値は、自由度を「シグナルのかたまりの数 − 1」とした t 分布で求める
（点灯日が多くても、独立な機会はかたまりの数しかないため。まれなシグナルほど厳しくなる）。
p 値には Benjamini–Hochberg の補正（q 値）を付ける。

注意: これは全期間を使った記述統計で、ウォークフォワードの検証ではない。「補正後に残るか」を見るためのもので、
残らないシグナルは、この銘柄の履歴では偶然と区別できない。残っても将来の保証ではない。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import stats as st
from .features import SIGNAL_LABELS

__all__ = ["event_study", "MIN_DAYS", "MIN_EPISODES", "EVENT_Q"]

EVENT_Q = 0.10        # 報告に使う q 値のしきい値（偽発見率 10%）
MIN_DAYS = 20
MIN_EPISODES = 8


def _episodes(d: np.ndarray, h: int) -> np.ndarray:
    """シグナルの「かたまり」の開始位置（直前 h 日に点灯がなかった点灯日）。"""
    n = len(d)
    c = np.concatenate([[0], np.cumsum(d.astype(int))])      # c[k] = 先頭 k 日の点灯数
    t = np.arange(n)
    lo = np.maximum(t - h, 0)
    prev = (c[t] - c[lo]) > 0                                 # 直前 h 日（t-h .. t-1）に点灯があったか
    return d & ~prev


def event_study(asset, signals: pd.DataFrame, cfg) -> pd.DataFrame:
    rows = []
    n = len(asset.close)
    u = asset.Fraw["ret1"].to_numpy(dtype=float)              # 1 日の標準化リターン r_t / σ_{t-1}
    u_next = np.r_[u[1:], np.nan]                              # u_{t+1}
    for h in cfg.horizons:
        z = asset.R[h] / asset.sig[h]["S3"]
        mask = np.isfinite(z)
        mask[: cfg.burn] = False
        mask1 = np.isfinite(u_next)
        mask1[: cfg.burn] = False
        if mask.sum() < 300:
            continue
        y = z[mask]
        ybar = y.mean()
        y2 = (y - ybar) ** 2
        lags = max(5, int(math.ceil(1.5 * (h - 1))))
        s3med = float(np.nanmedian(asset.sig[h]["S3"][mask]))
        y1 = u_next[mask1]
        y1sq = (y1 - y1.mean()) ** 2
        for col in signals.columns:
            d_full = signals[col].to_numpy(dtype=bool)
            d = d_full[mask]
            nd = int(d.sum())
            ep = int((_episodes(d_full, h) & mask).sum())
            row = {"signal": col, "label": SIGNAL_LABELS.get(col, col), "h": h, "n_days": nd, "episodes": ep,
                   "now": bool(d_full[n - 1]), "b": np.nan, "t_b": np.nan, "p_b": np.nan, "pct": np.nan,
                   "hit_sig": np.nan, "hit_other": np.nan, "var_ratio": np.nan, "t_c": np.nan, "p_c": np.nan}
            if nd >= MIN_DAYS and ep >= MIN_EPISODES and (len(d) - nd) >= MIN_DAYS:
                x = np.column_stack([np.ones(len(d)), d.astype(float)])
                r1 = st.nw_ols(y, x, lags)                     # 効果の大きさ（重なりあり）
                r2 = st.nw_ols(y2, x, lags)
                cs = np.concatenate([[0], np.cumsum(d_full.astype(float))])
                t_idx = np.arange(n)
                s_run = cs[t_idx + 1] - cs[np.maximum(t_idx + 1 - h, 0)]   # 直近 h 日の点灯日数
                xr = np.column_stack([np.ones(int(mask1.sum())), s_run[mask1]])
                rr1 = st.nw_ols(y1, xr, 5)                     # 検定（逆回帰、重なりなし）
                rr2 = st.nw_ols(y1sq, xr, 10)
                row.update({
                    "b": float(r1["beta"][1]), "t_b": float(rr1["t"][1]), "p_b": 2.0 * st.t_sf(abs(float(rr1["t"][1])), ep - 1),
                    "pct": float(100.0 * r1["beta"][1] * s3med),
                    "hit_sig": float((y[d] > 0).mean()), "hit_other": float((y[~d] > 0).mean()),
                    "var_ratio": float((r2["beta"][0] + r2["beta"][1]) / r2["beta"][0]) if r2["beta"][0] > 0 else np.nan,
                    "t_c": float(rr2["t"][1]), "p_c": 2.0 * st.t_sf(abs(float(rr2["t"][1])), ep - 1),
                })
            rows.append(row)
    df = pd.DataFrame(rows)
    if len(df):
        df["q_b"] = st.bh_fdr(df["p_b"].to_numpy())
        df["q_c"] = st.bh_fdr(df["p_c"].to_numpy())
    return df
