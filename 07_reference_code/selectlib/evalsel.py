"""選別の評価: 重み・期間リターン・超過収益・頑健性・DSR・PBO・試行台帳。"""
from __future__ import annotations

import itertools
import math
from statistics import NormalDist

import numpy as np

N01 = NormalDist()
PERIODS_PER_YEAR = 252 / 21
TOP_N = 15
EULER = 0.5772156649


def top_picks(score_row: np.ndarray, n: int = TOP_N) -> list:
    ok = np.flatnonzero(np.isfinite(score_row))
    if len(ok) == 0:
        return []
    return list(ok[np.argsort(-score_row[ok], kind="stable")[:n]])


def weights(cols: list, scheme: str = "equal", sigma: np.ndarray | None = None, cap_mult: float = 2.0) -> dict:
    """等ウエイト、または逆ボラ（w ∝ 1/σ̂、上限は等ウエイトの cap_mult 倍。上限で余った分は現金）。"""
    if not cols:
        return {}
    eq = 1.0 / len(cols)
    if scheme == "equal":
        return {int(c): eq for c in cols}
    s = np.array([sigma[c] for c in cols], dtype=float)
    s = np.where(np.isfinite(s) & (s > 0), s, np.nanmedian(s[np.isfinite(s) & (s > 0)]) if np.isfinite(s).any() else 1.0)
    w = (1 / s) / (1 / s).sum()
    w = np.minimum(w, cap_mult * eq)
    return {int(c): float(x) for c, x in zip(cols, w)}


def vol_gate(P, t_idx: list, q: float = 0.80, min_hist: int = 250) -> np.ndarray:
    """TOPIX の 63 日実現ボラが、それまでの全履歴の q 分位を超えたら True（全額現金）。"""
    r = np.log(P.topix["close"]).diff()
    rv = r.rolling(63, min_periods=50).std()
    gate = np.zeros(len(t_idx), dtype=bool)
    for i, T in enumerate(t_idx):
        h = rv.iloc[: T + 1].dropna()
        if len(h) >= min_hist and np.isfinite(rv.iloc[T]):
            gate[i] = rv.iloc[T] > h.quantile(q)
    return gate


def period_returns(equity: list) -> np.ndarray:
    e = np.array(equity, dtype=float)
    return e[1:] / e[:-1] - 1.0


def sharpe(r: np.ndarray) -> float:
    return float(r.mean() / r.std(ddof=1)) if len(r) > 2 and r.std(ddof=1) > 0 else float("nan")


def summarize(port: np.ndarray, topix: np.ndarray, univ: np.ndarray) -> dict:
    """期間リターン（ポートフォリオ・TOPIX・母集団の等ウエイト平均）から、年率超過収益と頑健性。"""
    n = len(port)
    ex_t, ex_u = port - topix, port - univ
    def ann(x):
        return float(x.mean() * PERIODS_PER_YEAR)
    out = {"periods": int(n), "port_ann": ann(port), "topix_ann": ann(topix), "univ_ann": ann(univ),
           "excess_vs_topix_ann": ann(ex_t), "excess_vs_univ_ann": ann(ex_u),
           "t_vs_topix": float(ex_t.mean() / (ex_t.std(ddof=1) / math.sqrt(n))) if n > 2 and ex_t.std(ddof=1) > 0 else float("nan"),
           "t_vs_univ": float(ex_u.mean() / (ex_u.std(ddof=1) / math.sqrt(n))) if n > 2 and ex_u.std(ddof=1) > 0 else float("nan"),
           "sharpe_period": sharpe(port), "hit_rate_vs_topix": float((ex_t > 0).mean())}
    for name, ex in (("topix", ex_t), ("univ", ex_u)):
        s = np.sort(ex)[:-3] if n > 6 else ex
        out[f"excess_vs_{name}_ann_without_top3_periods"] = ann(s)
    eq = np.cumprod(1 + port)
    out["max_drawdown"] = float((eq / np.maximum.accumulate(eq) - 1).min())
    return out


def by_year(port: np.ndarray, topix: np.ndarray, years: np.ndarray) -> dict:
    out = {}
    for y in sorted(set(years)):
        m = years == y
        out[int(y)] = {"periods": int(m.sum()), "excess_vs_topix_ann": float((port[m] - topix[m]).mean() * PERIODS_PER_YEAR)}
    return out


def gate_check(summ: dict, yearly: dict) -> dict:
    """採用ゲート（仕様 C）の機械的な判定。採用の判断は利用者。"""
    pos_years = [v["excess_vs_topix_ann"] > 0 for v in yearly.values() if v["periods"] >= 3]
    g = {"excess_vs_topix_positive": summ["excess_vs_topix_ann"] > 0, "excess_vs_univ_positive": summ["excess_vs_univ_ann"] > 0,
         "positive_in_majority_of_years": bool(pos_years) and sum(pos_years) > len(pos_years) / 2,
         "positive_without_top3_periods": summ["excess_vs_topix_ann_without_top3_periods"] > 0 and summ["excess_vs_univ_ann_without_top3_periods"] > 0}
    g["all_pass"] = all(g.values())
    return g


def deflated_sharpe(r: np.ndarray, trial_sharpes: np.ndarray) -> dict:
    """デフレート・シャープ（Bailey & López de Prado）。r: 当該戦略の期間リターン。trial_sharpes: 全試行の期間シャープ。"""
    T = len(r)
    sr = sharpe(r)
    if T < 5 or not np.isfinite(sr):
        return {"dsr": float("nan"), "sr": sr, "trials": int(len(trial_sharpes))}
    x = (r - r.mean()) / r.std(ddof=1)
    skew, kurt = float((x ** 3).mean()), float((x ** 4).mean())
    N = max(len(trial_sharpes), 1)
    v = float(np.nanvar(trial_sharpes, ddof=1)) if N > 1 else 0.0
    sr0 = math.sqrt(v) * ((1 - EULER) * N01.inv_cdf(1 - 1 / N) + EULER * N01.inv_cdf(1 - 1 / (N * math.e))) if N > 1 else 0.0
    den = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr * sr, 1e-12))
    return {"dsr": float(N01.cdf((sr - sr0) * math.sqrt(T - 1) / den)), "sr": sr, "sr_benchmark": sr0, "trials": int(N), "skew": skew, "kurtosis": kurt}


def pbo_cscv(M: np.ndarray, s: int = 8) -> dict:
    """バックテスト過剰適合確率（CSCV）。M: [期, 試行]。S 個のブロックを半分ずつ学習・検証に分ける全組合せ。"""
    T, N = M.shape
    if N < 2 or T < s * 2:
        return {"pbo": float("nan"), "note": "試行または期が少なくて計算しない"}
    blocks = np.array_split(np.arange(T), s)
    lam = []
    for comb in itertools.combinations(range(s), s // 2):
        tr = np.concatenate([blocks[i] for i in comb])
        te = np.concatenate([blocks[i] for i in range(s) if i not in comb])
        best = int(np.argmax(M[tr].mean(axis=0)))
        oos = M[te].mean(axis=0)
        w = (oos.argsort().argsort()[best] + 1) / (N + 1)
        lam.append(math.log(w / (1 - w)))
    lam = np.array(lam)
    return {"pbo": float((lam <= 0).mean()), "combinations": int(len(lam)), "trials": int(N)}
