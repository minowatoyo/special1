"""個別株の弾力性（下げた後に戻る癖）。仕様は docs/w5_protocol.md「個別株の弾力性の検証」。
日 t の引け後に結果が確定している過去の出来事だけから計算する。出力は集計のみ。
"""
from __future__ import annotations

import math
import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd

from . import events, seasonal

Z, FLOOR, MIN_GAP = 2.0, 0.05, 10
SHRINK, MIN_EVENTS = 4, 4
LAG_REBOUND, LAG_RECOV = 12, 22           # 出来事 t の結果を使えるのは、s ≥ t + 12（11 日目の始値）、s ≥ t + 22（21 日以内の回復）
REBOUND_H, RECOV_H = 10, 21
AC_WINDOW, AC_MIN = 100, 60
MIN_PER_GROUP = 5
DEFS = ("D1_rebound_record", "D2_recovery_speed", "D3_weekly_autocorr")


def sub(P, cols: np.ndarray) -> SimpleNamespace:
    """パネルの列を絞った軽い複製（検証に使う行列だけ）。"""
    keys = ("raw_open", "raw_close", "adj_open", "adj_high", "adj_low", "adj_close", "limit_up", "limit_down", "turnover")
    d = {k: getattr(P, k)[:, cols] for k in keys}
    d["dates"], d["codes"] = P.dates, [P.codes[i] for i in cols]
    return SimpleNamespace(**d)


def idio_excess5(adj_close: np.ndarray, universe: np.ndarray) -> tuple:
    """5 営業日リターンと、対象銘柄の平均との差。"""
    r5 = np.full(adj_close.shape, np.nan)
    r5[5:] = adj_close[5:] / adj_close[:-5] - 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        um = np.nanmean(np.where(universe, r5, np.nan), axis=1)
    return r5 - um[:, None], r5


def sigma_daily(adj_close: np.ndarray, lag: int = 5) -> np.ndarray:
    """日次対数リターンの標準偏差（直近 60 営業日、lag 日前まで）。"""
    lr = np.log(pd.DataFrame(adj_close)).diff()
    return lr.rolling(60, min_periods=40).std().shift(lag).to_numpy()


def dedupe(cond: np.ndarray, gap: int = MIN_GAP) -> np.ndarray:
    """同じ銘柄で、直前の出来事から gap 営業日未満の出来事を捨てる。"""
    out = np.zeros(cond.shape, dtype=bool)
    last = np.full(cond.shape[1], -10 ** 9)
    for t in range(cond.shape[0]):
        new = cond[t] & (t - last >= gap)
        out[t] = new
        last = np.where(new, t, last)
    return out


def drop_events(ex5: np.ndarray, sig: np.ndarray, hist_ok: np.ndarray) -> np.ndarray:
    thr = -np.maximum(Z * sig * math.sqrt(5), FLOOR)
    with np.errstate(invalid="ignore"):
        cond = hist_ok & np.isfinite(ex5) & np.isfinite(thr) & (ex5 <= thr)
    return dedupe(cond)


def shifted_cumsum(A: np.ndarray, lag: int) -> np.ndarray:
    """行 s に、行 ≤ s − lag の合計を返す。"""
    cs = np.cumsum(A, axis=0)
    out = np.zeros_like(cs)
    out[lag:] = cs[:-lag]
    return out


def rel_price(adj_close: np.ndarray, universe: np.ndarray) -> np.ndarray:
    """調整後終値 ÷ 対象銘柄の等ウエイト指数。"""
    r = np.full(adj_close.shape, np.nan)
    r[1:] = adj_close[1:] / adj_close[:-1] - 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        d = np.nan_to_num(np.nanmean(np.where(universe, r, np.nan), axis=1))
    return adj_close / np.cumprod(1.0 + d)[:, None]


def weekly_autocorr_score(ex5: np.ndarray, window: int = AC_WINDOW, min_periods: int = AC_MIN) -> np.ndarray:
    """D3: −(1 次の自己相関)。5 営業日ごとの重ならない超過リターンで、日 s の週は含めない。位相ごとに計算する。"""
    T, N = ex5.shape
    out = np.full((T, N), np.nan)
    for p in range(5):
        idx = np.arange(p, T, 5)
        X = pd.DataFrame(ex5[idx])
        corr = X.rolling(window, min_periods=min_periods).corr(X.shift(1))
        out[idx] = -corr.shift(1).to_numpy()
    return out


def scores(Q, hist_ok: np.ndarray, universe: np.ndarray, ex_reb: np.ndarray, ev: np.ndarray, ex5: np.ndarray) -> dict:
    """3 つの弾力性 [日, 銘柄]。ex_reb は、翌営業日始値 → 11 営業日目の始値の超過（買えない日は NaN）。"""
    fin = ev & np.isfinite(ex_reb)
    s1 = shifted_cumsum(np.where(fin, ex_reb, 0.0), LAG_REBOUND)
    n1 = shifted_cumsum(fin.astype(float), LAG_REBOUND)
    d1 = np.where(n1 >= MIN_EVENTS, s1 / (n1 + SHRINK), np.nan)
    R = rel_price(Q.adj_close, universe)
    R0 = np.full(R.shape, np.nan)
    R0[5:] = R[:-5]
    mx = pd.DataFrame(R).rolling(RECOV_H).max().shift(-RECOV_H).to_numpy()          # 日 t の翌日〜21 営業日後の最大
    half = R + 0.5 * (R0 - R)
    with np.errstate(invalid="ignore"):
        rec = np.where(np.isfinite(mx) & np.isfinite(half), (mx >= half).astype(float), np.nan)
    fin2 = ev & np.isfinite(rec)
    s2 = shifted_cumsum(np.where(fin2, rec, 0.0), LAG_RECOV)
    n2 = shifted_cumsum(fin2.astype(float), LAG_RECOV)
    d2 = np.where(n2 >= MIN_EVENTS, (s2 + 0.5 * SHRINK) / (n2 + SHRINK), np.nan)
    d3 = weekly_autocorr_score(ex5)
    return {DEFS[0]: d1, DEFS[1]: d2, DEFS[2]: d3, "n_past_rebound": n1, "n_past_recovery": n2, "recovered": rec}


def groups(score: np.ndarray, floor: np.ndarray) -> tuple:
    """日ごとに、floor の銘柄のうち弾力性が計算できるものの 3 分位。高（上位 1/3 以上）・低（下位 1/3 以下）の真偽 [日, 銘柄]。"""
    hi = np.zeros(score.shape, dtype=bool)
    lo = np.zeros(score.shape, dtype=bool)
    for t in range(score.shape[0]):
        m = floor[t] & np.isfinite(score[t])
        if m.sum() < 30:
            continue
        q1, q2 = np.percentile(score[t][m], [100 / 3, 200 / 3])
        hi[t] = m & (score[t] >= q2)
        lo[t] = m & (score[t] <= q1)
    return hi, lo


def contrast(P, ev: np.ndarray, hi: np.ndarray, lo: np.ndarray, ex_h: np.ndarray, h: int, t_lo: int, t_hi: int, cost: float = 0.006) -> dict:
    """出来事（ev）の、高 − 低 の月ごとの差 → 平均・t 値・p。併記: 各グループの平均超過・件数。"""
    t, j = np.nonzero(ev & (hi | lo) & np.isfinite(ex_h))
    m = (t >= t_lo) & (t <= t_hi)
    t, j = t[m], j[m]
    y, is_hi = ex_h[t, j], hi[t, j]
    ym = np.asarray(P.dates.year[t] * 12 + P.dates.month[t])
    df = pd.DataFrame({"ym": ym, "y": y, "hi": is_hi})
    g = df.groupby(["ym", "hi"])["y"].agg(["mean", "count"]).unstack("hi")
    out = {"events_high": int(is_hi.sum()), "events_low": int((~is_hi).sum()), "months": 0, "diff_mean": None, "t": None, "p": None,
           "high_mean": float(y[is_hi].mean()) if is_hi.any() else None, "low_mean": float(y[~is_hi].mean()) if (~is_hi).any() else None,
           "all_scored_events_mean": float(y.mean()) if len(y) else None}
    if out["high_mean"] is not None:
        out["high_mean_after_round_trip_B"] = out["high_mean"] - cost
    if len(g) and True in g["count"].columns and False in g["count"].columns:
        ok = (g["count"][True] >= MIN_PER_GROUP) & (g["count"][False] >= MIN_PER_GROUP)
        d = (g["mean"][True] - g["mean"][False])[ok]
        out["months"] = int(len(d))
        if len(d) >= 12:
            st_ = seasonal.tstat(d.to_numpy(), lags=math.ceil(h / 21))
            out.update({"diff_mean": st_["mean"], "t": st_["t"] if np.isfinite(st_["t"]) else None, "p": st_["p"] if np.isfinite(st_["p"]) else None})
    return out


def build(P, elig_hist: np.ndarray, floor: np.ndarray) -> dict:
    """検証と診断に共通の行列（列は、floor か elig_hist に一度でも入った銘柄に絞る）。"""
    cols = np.flatnonzero((elig_hist | floor).any(axis=0))
    Q = sub(P, cols)
    eh, fl = elig_hist[:, cols], floor[:, cols]
    ex5, _ = idio_excess5(Q.adj_close, eh)
    sig = sigma_daily(Q.adj_close)
    ev = drop_events(ex5, sig, eh)
    ok2 = eh & events.executable_at_open(Q)
    ex_reb = events.excess_matrix(Q, ok2, REBOUND_H)
    sc = scores(Q, eh, eh, ex_reb, ev, ex5)
    return {"Q": Q, "cols": cols, "elig_hist": eh, "floor": fl, "ex5": ex5, "sigma": sig, "ev": ev, "ok": ok2, "scores": sc, "ex_reb": ex_reb}
