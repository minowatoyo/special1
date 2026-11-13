"""順位予測のモデル（事前固定のリッジ。LightGBM は任意）。拡張窓で、売却が確定した期だけで学習する。"""
from __future__ import annotations

from statistics import NormalDist

import numpy as np

ALPHA = 1.0            # 事前固定。平均二乗誤差 + α‖b‖²（標本数に依存しない形。FIX-09 (3)）
MIN_TRAIN_PERIODS = 12
_N = NormalDist()


def rank_gauss(y: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """行ごとに、対象銘柄の順位を正規スコアにする。対象外・欠損は NaN。"""
    out = np.full_like(y, np.nan, dtype=float)
    for i in range(y.shape[0]):
        m = mask[i] & np.isfinite(y[i])
        n = int(m.sum())
        if n < 5:
            continue
        r = y[i, m].argsort().argsort() + 1
        out[i, m] = [_N.inv_cdf((x - 0.5) / n) for x in r]
    return out


def ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float = ALPHA):
    """切片つきリッジ。平均損失の形: b = (X'X/n + αI)^-1 X'y/n（X, y は中心化）。"""
    n = len(y)
    xm, ym = X.mean(axis=0), y.mean()
    Xc, yc = X - xm, y - ym
    b = np.linalg.solve(Xc.T @ Xc / n + alpha * np.eye(X.shape[1]), Xc.T @ yc / n)
    return b, ym - xm @ b


def stack(feats: list, names: list, k: int, mask: np.ndarray):
    """期 k の [対象銘柄, 特徴量] 行列と、その列番号。"""
    cols = np.flatnonzero(mask[k])
    return np.column_stack([feats[n][k, cols] for n in names]), cols


def walk_scores(feats: dict, names: list, y_rank: np.ndarray, mask: np.ndarray, kind: str = "ridge", alpha: float = ALPHA,
                min_periods: int = MIN_TRAIN_PERIODS, purge: int = 2) -> np.ndarray:
    """期 k のスコア [期, 銘柄]。学習は期 j ≤ k - purge の行だけ（k-1 期の売却は k の引け時点で未確定）。"""
    K, N = mask.shape
    scores = np.full((K, N), np.nan)
    for k in range(K):
        tr = [j for j in range(0, k - purge + 1) if mask[j].any()]
        if len(tr) < min_periods:
            continue
        Xs, ys = [], []
        for j in tr:
            X, cols = stack(feats, names, j, mask)
            y = y_rank[j, cols]
            ok = np.isfinite(y)
            Xs.append(X[ok])
            ys.append(y[ok])
        X, y = np.vstack(Xs), np.concatenate(ys)
        Xk, ck = stack(feats, names, k, mask)
        if kind == "ridge":
            b, a0 = ridge_fit(X, y, alpha)
            scores[k, ck] = Xk @ b + a0
        elif kind == "lgbm":
            import lightgbm as lgb
            mdl = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, max_depth=3, num_leaves=8, min_child_samples=200, subsample=0.8,
                                    subsample_freq=1, random_state=0, verbose=-1)
            mdl.fit(X, y)
            scores[k, ck] = mdl.predict(Xk)
        else:
            raise ValueError(kind)
    return scores
