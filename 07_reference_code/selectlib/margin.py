"""信用残・業種別空売り比率の目印（K1〜K5）。日 t の引け後に使える情報だけ（利用可能日 usable_from ≤ t）。仕様は docs/w5_protocol.md。"""
from __future__ import annotations

import numpy as np
import pandas as pd

NAMES = ("K1_long_drop", "K2_low_ratio", "K3_short_surge", "K4_sector_short_high", "K5_sector_short_low")
STALE_DAYS = 10


def _daily(P, usable: np.ndarray, values: np.ndarray, valid_days: int = STALE_DAYS) -> tuple:
    """週次（または日次）の記録 → 日付の列。各日 t に、利用可能日 ≤ t の最新の記録の値を返す。古すぎる記録は無効。"""
    dates = P.dates.values
    idx = np.searchsorted(usable, dates, side="right") - 1
    ok = idx >= 0
    safe = np.where(ok, idx, 0)
    age = (dates - usable[safe]).astype("timedelta64[D]").astype(int)
    ok &= age <= valid_days
    return np.where(ok, values[safe], np.nan), ok


def margin_flags(P, m: pd.DataFrame) -> dict:
    """K1〜K3 の (フラグ, データあり) [日付, 銘柄]。m は processed の margin_interest（code, date, long_vol, short_vol, usable_from）。"""
    ci = {c: i for i, c in enumerate(P.codes)}
    m = m.dropna(subset=["usable_from"]).sort_values(["code", "date"]).copy()
    g = m.groupby("code", sort=False)
    m["long_chg4"] = m["long_vol"] / g["long_vol"].shift(4) - 1
    m["short_chg4"] = m["short_vol"] / g["short_vol"].shift(4) - 1
    ratio = (m["long_vol"] / m["short_vol"].where(m["short_vol"] > 0)).replace([np.inf, -np.inf], np.nan)
    m["ratio"] = ratio
    m["ratio_q20"] = m.groupby("code", sort=False)["ratio"].transform(lambda s: s.rolling(52, min_periods=40).quantile(0.20))
    m["k1"] = np.where(m["long_chg4"].notna(), (m["long_chg4"] <= -0.20).astype(float), np.nan)
    m["k2"] = np.where(m["ratio"].notna() & m["ratio_q20"].notna(), (m["ratio"] <= m["ratio_q20"]).astype(float), np.nan)
    m["k3"] = np.where(m["short_chg4"].notna(), (m["short_chg4"] >= 0.30).astype(float), np.nan)
    n_t, n_j = P.adj_close.shape
    out = {nm: (np.zeros((n_t, n_j), dtype=bool), np.zeros((n_t, n_j), dtype=bool)) for nm in NAMES[:3]}
    for code, d in m.groupby("code", sort=False):
        j = ci.get(code)
        if j is None:
            continue
        u = d["usable_from"].to_numpy()
        for nm, col in zip(NAMES[:3], ("k1", "k2", "k3")):
            v, ok = _daily(P, u, d[col].to_numpy(dtype=float))
            has = ok & np.isfinite(v)
            out[nm][0][:, j] = has & (np.nan_to_num(v) > 0.5)
            out[nm][1][:, j] = has
    return out


def sector_flags(P, sr: pd.DataFrame, intervals: pd.DataFrame) -> dict:
    """K4・K5 の (フラグ, データあり) [日付, 銘柄]。sr は processed の short_ratio（s33, date, short_ratio, usable_from）。"""
    n_t, n_j = P.adj_close.shape
    secs = sorted(sr["s33"].unique())
    si = {s: i for i, s in enumerate(secs)}
    f4, f5, v4 = (np.zeros((n_t, len(secs)), dtype=bool) for _ in range(3))
    for s, d in sr.dropna(subset=["usable_from", "short_ratio"]).sort_values("date").groupby("s33"):
        x = d["short_ratio"].reset_index(drop=True)
        q90 = x.rolling(252, min_periods=200).quantile(0.90)
        m5 = x.rolling(5, min_periods=5).mean()
        q20 = m5.rolling(252, min_periods=200).quantile(0.20)
        k4 = np.where(q90.notna(), (x >= q90).astype(float), np.nan)
        k5 = np.where(q20.notna(), (m5 <= q20).astype(float), np.nan)
        u = d["usable_from"].to_numpy()
        a, oka = _daily(P, u, k4, valid_days=5)
        b, okb = _daily(P, u, k5, valid_days=5)
        i = si[s]
        f4[:, i] = oka & np.isfinite(a) & (np.nan_to_num(a) > 0.5)
        f5[:, i] = okb & np.isfinite(b) & (np.nan_to_num(b) > 0.5)
        v4[:, i] = oka & np.isfinite(a) & okb & np.isfinite(b)
    # 銘柄の業種（S33）を、その日の上場銘柄表の区間から決める
    sec_idx = np.full((n_t, n_j), -1, dtype=np.int32)
    ci = {c: i for i, c in enumerate(P.codes)}
    dates = P.dates.values
    for r in intervals[["code", "s33", "valid_from", "valid_to"]].itertuples(index=False):
        j = ci.get(r.code)
        s = si.get(r.s33)
        if j is None or s is None:
            continue
        a, b = np.searchsorted(dates, r.valid_from.to_datetime64(), side="left"), np.searchsorted(dates, r.valid_to.to_datetime64(), side="right")
        sec_idx[a:b, j] = s
    known = sec_idx >= 0
    safe = np.where(known, sec_idx, 0)
    rows = np.arange(n_t)[:, None]
    has = known & v4[rows, safe]
    return {NAMES[3]: (has & f4[rows, safe], has), NAMES[4]: (has & f5[rows, safe], has)}


def all_flags(P, margin: pd.DataFrame, short_ratio: pd.DataFrame, intervals: pd.DataFrame) -> dict:
    return {**margin_flags(P, margin), **sector_flags(P, short_ratio, intervals)}
