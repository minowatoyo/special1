"""ボラティリティ（値動きの大きさ）の予測。すべて先読みなし。

なぜここが要るか: 株価の「方向」は予測しにくいが、「値幅」は比較的予測できる（ボラティリティの持続性）。
予測分布の幅を当日の状態に合わせることが、確率予測の精度を上げる最も確かな手段になる。

候補（事前登録、09_forecasting/02_protocol.md）:
  S1  EWMA（終値ベース、λ=0.94、期間は √h で伸ばす）
  S2  HAR 型の直接予測（説明変数はレンジ系の日次分散 GKYZ の 1・5・22 日平均、下落の大きさ（1・5・22 日）、出来高の急増。
      目的変数は先 h 日の実現分散、対数回帰）。下落の項は「下げた後は値動きが大きくなりやすい」非対称性
      （レバレッジ効果）を取り込むためのもので、急騰の後と急落の後で予測が変わる
  S3  S1 と S2 の幾何平均（結合）

返す σ は「先 h 営業日の対数リターンの標準偏差の予測」で、時点 t の値は t の終値までの情報だけで決まる。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

__all__ = ["log_returns", "ewma_variance", "gkyz_variance", "realized_variance_fwd",
           "har_forecast", "sigma_forecasts", "SIGMA_MODELS"]

SIGMA_MODELS = ("S1", "S2", "S3")
_EPS = 2.5e-7          # 日次分散の下限（日次 0.05% 相当）。対数をとるための床


def log_returns(close: pd.Series) -> pd.Series:
    """日次の対数リターン r_t = ln(C_t / C_{t-1})。最初は NaN。"""
    return np.log(close / close.shift(1))


def ewma_variance(r: pd.Series, lam: float = 0.94, init: int = 20) -> pd.Series:
    """EWMA 分散 v_t = λ v_{t-1} + (1-λ) r_t²。最初の init 個の r² の平均で初期化する。
    v_t は r_t までを使う（t の終値で確定）。
    """
    x = r.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    valid = np.flatnonzero(np.isfinite(x))
    if len(valid) < init:
        return pd.Series(out, index=r.index)
    start = valid[init - 1]
    v = float(np.mean(x[valid[:init]] ** 2))
    out[start] = v
    for i in range(start + 1, len(x)):
        if np.isfinite(x[i]):
            v = lam * v + (1.0 - lam) * x[i] * x[i]
        out[i] = v
    return pd.Series(out, index=r.index)


def gkyz_variance(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """レンジ系の日次分散（Garman–Klass に前日終値→当日始値の窓を足した形、GKYZ）。

        v_t = ln(O_t/C_{t-1})² + 0.5·ln(H_t/L_t)² − (2ln2−1)·ln(C_t/O_t)²

    終値だけの r_t² より誤差が小さい（高値・安値の情報を使う）。四本値に欠損・矛盾があれば r_t² で代える。
    """
    pc = close.shift(1)
    on = np.log(open_ / pc)
    hl = np.log(high / low)
    co = np.log(close / open_)
    v = on ** 2 + 0.5 * hl ** 2 - (2.0 * math.log(2.0) - 1.0) * co ** 2
    r2 = np.log(close / pc) ** 2
    bad = ~np.isfinite(v) | (v < 0) | (high < low)
    v = v.where(~bad, r2)
    return v


def realized_variance_fwd(r: pd.Series, h: int) -> pd.Series:
    """先 h 日の実現分散 RV_t = Σ_{k=1..h} r_{t+k}²（t の時点では未知。t+h で確定）。"""
    return (r ** 2).rolling(h).sum().shift(-h)


def har_forecast(v_rng: pd.Series, r: pd.Series, h: int, refit: int = 21, min_train: int = 500,
                 leverage: bool = True, volume: pd.Series | None = None) -> pd.Series:
    """HAR 型の直接予測: 先 h 日の「1 日あたり平均分散」の予測値（時点 t で確定）。

    対数回帰  ln(RV_t^(h)/h) = b0 + b1·ln v_t^(1) + b2·ln v_t^(5) + b3·ln v_t^(22)
                               + g1·r_t^- + g2·r_t^(5)- + g3·r_t^(22)- + e
    を、その時点までに結果が確定した行（t + h <= 現在）だけで推定し、refit 日ごとに推定し直す。
    r^- は下落の大きさ（1 日リターン、5 日・22 日の平均リターンの負の部分。上昇なら 0）で、leverage=False なら使わない。
    volume を渡すと、出来高の急増（当日と 5 日平均の、過去 60 日平均に対する対数比）も説明変数に加える
    （出来高はリターンの方向よりも、その後の値動きの大きさと結びつくという報告に基づく）。
    対数から戻すときの偏りは、残差の exp の平均（スミアリング）で補正する。
    """
    n = len(r)
    v = v_rng.to_numpy(dtype=float)
    lv1 = np.log(np.maximum(v, 0) + _EPS)
    lv5 = np.log(v_rng.rolling(5).mean().to_numpy(dtype=float) + _EPS)
    lv22 = np.log(v_rng.rolling(22).mean().to_numpy(dtype=float) + _EPS)
    cols = [np.ones(n), lv1, lv5, lv22]
    if leverage:
        rr = r.to_numpy(dtype=float)
        cols += [np.minimum(rr, 0.0) * 100.0,
                 np.minimum(r.rolling(5).mean().to_numpy(dtype=float), 0.0) * 100.0,
                 np.minimum(r.rolling(22).mean().to_numpy(dtype=float), 0.0) * 100.0]
    if volume is not None and (volume > 0).sum() > min_train:
        vv = volume.where(volume > 0)
        base = vv.rolling(60).mean().shift(1)
        cols += [np.log(vv / base).to_numpy(dtype=float), np.log(vv.rolling(5).mean() / base).to_numpy(dtype=float)]
    x = np.column_stack(cols)
    y = np.log(realized_variance_fwd(r, h).to_numpy(dtype=float) / h + _EPS)
    x_ok = np.isfinite(x).all(axis=1)
    ok = x_ok & np.isfinite(y)
    xz = np.where(ok[:, None], x, 0.0)
    yz = np.where(ok, y, 0.0)
    cxx = np.cumsum(xz[:, :, None] * xz[:, None, :], axis=0)
    cxy = np.cumsum(xz * yz[:, None], axis=0)
    cnt = np.cumsum(ok)
    out = np.full(n, np.nan)
    beta, smear = None, 1.0
    for t in range(n):
        last = t - h                       # 結果が確定している最後の行
        if last >= 0 and cnt[last] >= min_train and (beta is None or (t % refit) == 0):
            try:
                beta = np.linalg.solve(cxx[last], cxy[last])
            except np.linalg.LinAlgError:
                beta = None
            if beta is not None:
                m = ok[: last + 1]
                res = y[: last + 1][m] - x[: last + 1][m] @ beta
                smear = float(np.mean(np.exp(res)))
        if beta is not None and x_ok[t]:
            out[t] = math.exp(float(x[t] @ beta)) * smear
    return pd.Series(out, index=r.index)


def sigma_forecasts(df: pd.DataFrame, horizons=(5, 21, 63), lam: float = 0.94, refit: int = 21,
                    min_train: int = 500) -> dict:
    """各期間 h について、σ の予測（S1・S2・S3）の DataFrame を返す。 {h: DataFrame[S1,S2,S3]}"""
    r = log_returns(df["close"])
    v1 = ewma_variance(r, lam=lam)
    vr = gkyz_variance(df["open"], df["high"], df["low"], df["close"])
    out = {}
    for h in horizons:
        s1 = np.sqrt(h * v1)
        vh = har_forecast(vr, r, h, refit=refit, min_train=min_train, volume=df["volume"] if "volume" in df else None)
        s2 = np.sqrt(h * vh)
        s3 = np.exp(0.5 * (np.log(s1) + np.log(s2)))
        out[h] = pd.DataFrame({"S1": s1, "S2": s2, "S3": s3})
    return out
