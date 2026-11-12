"""確率予測の採点と、予測どうしの比較・多重検定の補正。

  * ピンボール損失・CRPS（分布全体の採点。小さいほど良い。適切なスコア規則）
  * Diebold–Mariano 型の検定（HAC 分散）と定常ブートストラップ（重なりのある h 日先予測の系列相関に対応）
  * White の Reality Check（複数の候補から最良を選ぶときのデータ・スヌーピング補正）
  * Benjamini–Hochberg の FDR 補正（多数のシグナルを同時に検定するとき）
  * Newey–West 回帰（イベントスタディ用）
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["tau_grid", "predictive_taus", "sorted_quantiles", "pinball", "crps_from_grid", "crps_exact", "cdf_from_grid",
           "quantile_from_grid", "hac_variance", "dm_test", "stationary_bootstrap_indices", "boot_mean_pvalue",
           "reality_check", "bh_fdr", "nw_ols", "norm_sf", "t_sf"]


def tau_grid(q: int = 100) -> np.ndarray:
    """分位点の格子（中点）。q=100 なら 0.005, 0.015, …, 0.995。"""
    return (np.arange(q) + 0.5) / q


def predictive_taus(taus: np.ndarray, n_eff: float) -> np.ndarray:
    """経験分位点を「次の 1 個」の予測に使うときの有限標本補正。

    標本から推定した分位点には推定誤差があるので、そのまま使うと、次の観測が区間の外に出る確率が
    名目より大きくなる（区間が狭すぎる）。独立な標本が N 個相当のとき、水準 τ の経験分位点を
    次の観測が下回る確率は、およそ τ + (1−2τ)/(2N) になる（経験分布関数の分散 u(1−u)/N が u で変わるため）。
    そこで水準を
        τ' = τ − (1−2τ)/(2N)
    に置き換えて、分布の両側を少し広げる。N が大きければ補正はほぼ 0 になる。
    h 日リターンの標本は互いに重なるので、N は標本数そのものではなく、呼び出し側で有効な標本数
    （おおよそ 1.5×標本数÷h）を渡す。
    """
    n_eff = max(float(n_eff), 1.0)
    return np.clip(taus - (1.0 - 2.0 * taus) / (2.0 * n_eff), 0.0, 1.0)


def sorted_quantiles(sorted_x: np.ndarray, taus: np.ndarray) -> np.ndarray:
    """昇順の配列から分位点を線形補間で求める（numpy.quantile の既定と同じ定義）。"""
    m = len(sorted_x)
    if m == 0:
        return np.full(len(taus), np.nan)
    pos = taus * (m - 1)
    lo = np.floor(pos).astype(int)
    hi = np.minimum(lo + 1, m - 1)
    w = pos - lo
    return sorted_x[lo] * (1.0 - w) + sorted_x[hi] * w


def pinball(y: float, q: np.ndarray, taus: np.ndarray) -> np.ndarray:
    """ピンボール損失 ρ_τ(y, q) = max(τ(y−q), (τ−1)(y−q))。"""
    d = y - q
    return np.maximum(taus * d, (taus - 1.0) * d)


def crps_from_grid(y: float, q: np.ndarray, taus: np.ndarray) -> float:
    """CRPS の近似: 分位点格子上のピンボール損失の平均の 2 倍（CRPS = 2∫ρ_τ dτ）。"""
    return float(2.0 * np.mean(pinball(y, q, taus)))


def crps_exact(y: float, sample: np.ndarray) -> float:
    """標本で表した予測分布の CRPS（厳密）: E|X−y| − ½E|X−X'|。検算用。"""
    x = np.sort(np.asarray(sample, dtype=float))
    m = len(x)
    e1 = np.mean(np.abs(x - y))
    i = np.arange(1, m + 1)
    e2 = 2.0 * np.sum((2 * i - m - 1) * x) / (m * m)
    return float(e1 - 0.5 * e2)


def cdf_from_grid(x: float, q: np.ndarray, taus: np.ndarray) -> float:
    """分位点格子から F(x) を線形補間で求める（格子の外側は端の確率に丸める）。"""
    if not np.isfinite(x):
        return float("nan")
    if x <= q[0]:
        return float(taus[0] * 0.5) if x < q[0] else float(taus[0])
    if x >= q[-1]:
        return float(1.0 - (1.0 - taus[-1]) * 0.5) if x > q[-1] else float(taus[-1])
    j = int(np.searchsorted(q, x, side="right")) - 1
    j = max(0, min(j, len(q) - 2))
    dq = q[j + 1] - q[j]
    w = 0.0 if dq <= 0 else (x - q[j]) / dq
    return float(taus[j] + w * (taus[j + 1] - taus[j]))


def quantile_from_grid(p: float, q: np.ndarray, taus: np.ndarray) -> float:
    """分位点格子から任意の確率 p の分位点を線形補間で求める（外側は端の値）。"""
    return float(np.interp(p, taus, q))


def hac_variance(d: np.ndarray, lags: int) -> float:
    """平均の長期分散（Bartlett 核の Newey–West）。戻り値は Var(平均) = S/n。"""
    d = np.asarray(d, dtype=float)
    n = len(d)
    x = d - d.mean()
    s = float(x @ x) / n
    for j in range(1, min(lags, n - 1) + 1):
        w = 1.0 - j / (lags + 1.0)
        s += 2.0 * w * float(x[j:] @ x[:-j]) / n
    return max(s, 1e-300) / n


def norm_sf(z: float) -> float:
    """標準正規の上側確率。"""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _betacf(a: float, b: float, x: float) -> float:
    """不完全ベータ関数の連分数展開（Lentz 法）。"""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / (c if abs(c) > tiny else tiny)
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / (c if abs(c) > tiny else tiny)
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def t_sf(t: float, df: float) -> float:
    """スチューデントの t 分布の上側確率 P(T > t)。df が大きいと正規分布に近づく。"""
    if not math.isfinite(t) or df <= 0:
        return float("nan")
    x = df / (df + t * t)
    a, b = df / 2.0, 0.5
    if x <= 0.0:
        tail = 0.0
    elif x >= 1.0:
        tail = 1.0
    else:
        ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
        if x < (a + 1.0) / (a + b + 2.0):
            tail = math.exp(ln_bt) * _betacf(a, b, x) / a
        else:
            tail = 1.0 - math.exp(ln_bt) * _betacf(b, a, 1.0 - x) / b
    return 0.5 * tail if t > 0 else 1.0 - 0.5 * tail


def dm_test(loss_a: np.ndarray, loss_b: np.ndarray, h: int, step: int = 1) -> dict:
    """「A は B より損失が小さい」の片側検定（Diebold–Mariano 型、HAC 分散、正規近似）。

    h 日先予測の損失差は少なくとも h−1 次まで自己相関するので、ラグを 1.5(h−1) 以上にとる。
    戻り値 p は帰無仮説「A は B より良くない」の p 値。
    """
    d = np.asarray(loss_b, dtype=float) - np.asarray(loss_a, dtype=float)   # 正なら A が良い
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 30:
        return {"n": n, "mean_diff": float("nan"), "stat": float("nan"), "p": float("nan")}
    lags = max(int(math.ceil(1.5 * (h - 1) / step)), int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0))))
    se = math.sqrt(hac_variance(d, lags))
    stat = float(d.mean() / se)
    return {"n": n, "mean_diff": float(d.mean()), "stat": stat, "p": norm_sf(stat), "lags": lags}


def stationary_bootstrap_indices(n: int, block: float, b: int, rng: np.random.Generator) -> np.ndarray:
    """定常ブートストラップ（Politis–Romano）の添字。平均ブロック長 block、b 回分（b×n の配列）。"""
    p = 1.0 / max(block, 1.0)
    new = rng.random((b, n)) < p
    new[:, 0] = True
    starts = rng.integers(0, n, size=(b, n))
    pos = np.arange(n)[None, :]
    last_new = np.maximum.accumulate(np.where(new, pos, -1), axis=1)
    start_val = np.take_along_axis(starts, last_new, axis=1)
    return ((start_val + (pos - last_new)) % n).astype(np.int32)


def boot_mean_pvalue(d: np.ndarray, block: float, b: int = 2000, seed: int = 0) -> dict:
    """損失差 d（正なら候補が良い）の平均が 0 より大きいかを、定常ブートストラップで検定する。
    p は帰無仮説「平均 <= 0」の p 値、ci は平均の 90% 信頼区間。
    """
    d = np.asarray(d, dtype=float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 30:
        return {"p": float("nan"), "ci": (float("nan"), float("nan"))}
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(n, block, b, rng)
    means = d[idx].mean(axis=1)
    centered = means - d.mean()
    p = float((np.sum(centered >= d.mean()) + 1) / (b + 1))
    lo, hi = np.quantile(means, [0.05, 0.95])
    return {"p": p, "ci": (float(lo), float(hi))}


def reality_check(diffs: np.ndarray, block: float, b: int = 2000, seed: int = 0) -> dict:
    """White の Reality Check。diffs は n×K（列 k = 基準の損失 − 候補 k の損失。正なら候補が良い）。

    「K 個の候補のうち最良のものでも基準より良くない」を帰無仮説とする p 値を返す。
    候補を多く試すほど偶然の当たりが出やすいことを補正する。
    """
    d = np.asarray(diffs, dtype=float)
    d = d[np.isfinite(d).all(axis=1)]
    n, k = d.shape if d.ndim == 2 else (len(d), 1)
    if n < 30:
        return {"p": float("nan"), "best": -1, "stat": float("nan")}
    d = d.reshape(n, k)
    mean = d.mean(axis=0)
    stat = float(np.sqrt(n) * mean.max())
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(n, block, b, rng)
    boot_max = np.full(b, -np.inf)
    for j in range(k):
        bm = d[:, j][idx].mean(axis=1)
        boot_max = np.maximum(boot_max, np.sqrt(n) * (bm - mean[j]))
    p = float((np.sum(boot_max >= stat) + 1) / (b + 1))
    return {"p": p, "best": int(mean.argmax()), "stat": stat}


def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg の q 値（FDR）。NaN はそのまま返す。"""
    p = np.asarray(pvals, dtype=float)
    q = np.full(len(p), np.nan)
    ok = np.flatnonzero(np.isfinite(p))
    if len(ok) == 0:
        return q
    order = ok[np.argsort(p[ok])]
    m = len(order)
    ranked = p[order] * m / (np.arange(m) + 1.0)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q[order] = np.minimum(ranked, 1.0)
    return q


def nw_ols(y: np.ndarray, x: np.ndarray, lags: int) -> dict:
    """OLS と Newey–West（Bartlett 核）の標準誤差。x は n×p（定数項を含める）。"""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    n, p = x.shape
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ (x.T @ y)
    e = y - x @ beta
    u = x * e[:, None]
    s = u.T @ u
    for j in range(1, min(lags, n - 1) + 1):
        w = 1.0 - j / (lags + 1.0)
        g = u[j:].T @ u[:-j]
        s += w * (g + g.T)
    cov = xtx_inv @ s @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 1e-300))
    return {"beta": beta, "se": se, "t": beta / se, "n": n}
