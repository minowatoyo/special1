"""除外フィルター（X1〜X4）と、その効果の統計。仕様は docs/w5_protocol.md「除外フィルターの検証」。
日 T の引け後に使える情報だけ（信用残は利用可能日 ≤ T の最新の週次記録、10 暦日より古いものは無効）。出力は集計のみ。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from forecastlib import stats as st

from . import evalsel
from . import margin as mg_mod

BASE_NAMES = ("X1_short_days_top", "X2_ratio_bottom", "X3_surge_light_long", "X4_highvol_light_long")
ALL_NAMES = BASE_NAMES + ("U12", "U1234")
PRIMARY = ("X1_short_days_top", "X2_ratio_bottom", "U12")          # 独立な（定義が発見期間だけから決まった）族
MIN_PER_PERIOD = 5


def margin_matrices(P, mg: pd.DataFrame, t_idx: list) -> dict:
    """判断日 × 銘柄: 買い残・売り残が、20 日平均売買代金の何日分か、と信用倍率。信用残のない銘柄は NaN。"""
    mv = mg_mod.margin_values(P, mg)
    to20 = pd.DataFrame(P.turnover).fillna(0.0).rolling(20, min_periods=15).mean().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        den = np.where(to20 > 0, to20, np.nan)
        long_days = (mv["long_vol"] * P.raw_close / den)[t_idx]
        short_days = (mv["short_vol"] * P.raw_close / den)[t_idx]
        ratio = (mv["long_vol"] / np.where(mv["short_vol"] > 0, mv["short_vol"], np.nan))[t_idx]
    ratio = np.where(np.isfinite(ratio), ratio, np.nan)
    return {"long_days": long_days, "short_days": short_days, "ratio": ratio}


def _row_flag(x: np.ndarray, m: np.ndarray, lo: float | None = None, hi: float | None = None, min_n: int = 30) -> np.ndarray:
    """その日の対象銘柄（m）の中で、x が分位の下側（<= lo 分位）または上側（>= hi 分位）の銘柄。足りない日は全部 False。"""
    out = np.zeros(x.shape, dtype=bool)
    mm = m & np.isfinite(x)
    if mm.sum() < min_n:
        return out
    if lo is not None:
        out[mm] = x[mm] <= np.percentile(x[mm], lo)
    if hi is not None:
        out[mm] = x[mm] >= np.percentile(x[mm], hi)
    return out


def _tertile_row(x: np.ndarray, m: np.ndarray, min_n: int = 30) -> np.ndarray:
    """その日の対象銘柄の 3 分位（0 低・1 中・2 高）。欠損・不足は -1。"""
    out = np.full(x.shape, -1, dtype=np.int8)
    mm = m & np.isfinite(x)
    if mm.sum() >= min_n:
        q1, q2 = np.percentile(x[mm], [33.3, 66.7])
        out[mm] = np.where(x[mm] <= q1, 0, np.where(x[mm] <= q2, 1, 2))
    return out


def flags(mm: dict, chart: dict, mask: np.ndarray) -> dict:
    """フィルターの真偽 [判断日, 銘柄]。mm は margin_matrices、chart は chart_features（ret21、vol60）、mask は対象銘柄。"""
    K, N = mask.shape
    out = {n: np.zeros((K, N), dtype=bool) for n in ALL_NAMES}
    for k in range(K):
        m = mask[k]
        if not m.any():
            continue
        out["X1_short_days_top"][k] = _row_flag(mm["short_days"][k], m, hi=80)
        out["X2_ratio_bottom"][k] = _row_flag(mm["ratio"][k], m, lo=20)
        light = _tertile_row(mm["long_days"][k], m) == 0
        out["X3_surge_light_long"][k] = light & m & np.isfinite(chart["ret21"][k]) & (np.nan_to_num(chart["ret21"][k]) > 0.15)
        out["X4_highvol_light_long"][k] = light & (_tertile_row(chart["vol60"][k], m) == 2)
    out["U12"] = out["X1_short_days_top"] | out["X2_ratio_bottom"]
    out["U1234"] = out["U12"] | out["X3_surge_light_long"] | out["X4_highvol_light_long"]
    return out


def mean_t(x) -> dict:
    """判断日ごとの値の平均、t 値、両側 p（判断日は重ならないので iid）。"""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    out = {"periods": int(n), "mean": float(x.mean()) if n else None, "t": None, "p": None}
    if n >= 8 and x.std(ddof=1) > 0:
        t = float(x.mean() / (x.std(ddof=1) / math.sqrt(n)))
        out["t"], out["p"] = t, float(2 * st.t_sf(abs(t), n - 1))
    return out


def effect(flag: np.ndarray, excess: np.ndarray, mask: np.ndarray, ks: list) -> dict:
    """検証 A: 掛かった銘柄の、判断日ごとの平均超過（掛かった銘柄が 5 以上の日）→ 平均・t・p。掛かった割合も出す。"""
    per, share = [], []
    for k in ks:
        f = flag[k] & mask[k] & np.isfinite(excess[k])
        n_el = int((mask[k] & np.isfinite(excess[k])).sum())
        if n_el:
            share.append(f.sum() / n_el)
        if f.sum() >= MIN_PER_PERIOD:
            per.append(float(excess[k][f].mean()))
    r = mean_t(per)
    r["flagged_share_mean"] = float(np.mean(share)) if share else None
    return r


def picks_excluding(score_row: np.ndarray, flag_row: np.ndarray, n: int = evalsel.TOP_N) -> list:
    """フィルターに掛かった銘柄を除いて、スコアの上位 n（除いた分は次の順位が繰り上がる）。"""
    s = np.where(flag_row, np.nan, score_row)
    return evalsel.top_picks(s, n)


def paired(base: np.ndarray, filt: np.ndarray, ks: list) -> dict:
    """検証 B: 同じ判断日の対の差（フィルター後 − 基準）の平均・t・p。"""
    d = [filt[k] - base[k] for k in ks if np.isfinite(filt[k]) and np.isfinite(base[k])]
    return mean_t(d)


def bh_flags(p_by_name: dict, q: float = 0.10) -> dict:
    names = [n for n, p in p_by_name.items() if p is not None and np.isfinite(p)]
    if not names:
        return {}
    qv = st.bh_fdr(np.array([p_by_name[n] for n in names], dtype=float))
    return {n: float(v) for n, v in zip(names, qv)}
