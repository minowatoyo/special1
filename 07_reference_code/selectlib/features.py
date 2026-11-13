"""特徴量（銘柄間で日ごとに標準化）。SEL-A: チャートのみ、SEL-B: 財務。仕様は docs/w5_protocol.md。"""
from __future__ import annotations

import numpy as np
import pandas as pd

SEL_A = ["ret5", "ret21", "ret63", "ret126", "vol_contraction", "near_high", "resilience", "vol60", "turn_trend"]
SEL_B = ["rev_op", "rev_np", "div_chg", "earn_yield", "book_yield", "roe"]
DECAY_DAYS = 60.0
STALE_DAYS = 400


def zrows(x: np.ndarray, mask: np.ndarray, clip: float = 3.0) -> np.ndarray:
    """行（日付）ごとに、対象銘柄の平均・標準偏差で標準化し ±clip で打ち切る。対象外・欠損は 0。"""
    out = np.zeros_like(x, dtype=float)
    for i in range(x.shape[0]):
        m = mask[i] & np.isfinite(x[i])
        if m.sum() < 5:
            continue
        v = x[i, m]
        sd = v.std()
        out[i, m] = np.clip((v - v.mean()) / sd, -clip, clip) if sd > 0 else 0.0
    return out


def _gkyz(P) -> pd.DataFrame:
    """日次の GKYZ 分散（夜間の窓 + Garman-Klass）。"""
    o = pd.DataFrame(P.adj_open)
    h, l, c = pd.DataFrame(P.adj_high), pd.DataFrame(P.adj_low), pd.DataFrame(P.adj_close)
    ov = np.log(o / c.shift(1)) ** 2
    return ov + 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2


def chart_features(P, t_idx: list) -> dict:
    """SEL-A の生の値 [len(t_idx), 銘柄]。T の引け時点までの情報だけを使う。"""
    c = pd.DataFrame(P.adj_close)
    lr = np.log(c).diff()
    g = _gkyz(P)
    top = np.log(P.topix["close"]).diff().to_numpy()
    down = top < 0
    ex = lr.sub(np.nan_to_num(top), axis=0).where(np.broadcast_to(down[:, None], lr.shape))
    vc = np.sqrt(g.rolling(5, min_periods=4).mean() / g.rolling(22, min_periods=18).mean().replace(0, np.nan))
    f = {"ret5": c / c.shift(5) - 1, "ret21": c / c.shift(21) - 1, "ret63": c / c.shift(63) - 1, "ret126": c / c.shift(126) - 1,
         "vol_contraction": vc,
         "near_high": c / pd.DataFrame(P.adj_high).rolling(252, min_periods=200).max(),
         "resilience": ex.rolling(63, min_periods=10).mean(),
         "vol60": lr.rolling(60, min_periods=50).std(),
         "turn_trend": np.log(pd.DataFrame(P.turnover).rolling(20, min_periods=15).mean() / pd.DataFrame(P.turnover).rolling(120, min_periods=90).mean().replace(0, np.nan))}
    return {k: v.to_numpy()[t_idx] for k, v in f.items()}


def sigma_proxy(P, t_idx: list) -> np.ndarray:
    """逆ボラ用の σ̂ の簡易版（forecastlib の S3 = S1 と S2 の幾何平均の代わりに、EWMA(0.94) と 22 日 GKYZ の幾何平均）。日次。"""
    lr = np.log(pd.DataFrame(P.adj_close)).diff()
    ew = np.sqrt((lr ** 2).ewm(alpha=0.06, min_periods=30).mean())
    gk = np.sqrt(_gkyz(P).rolling(22, min_periods=18).mean().clip(lower=0))
    return np.sqrt(ew * gk).to_numpy()[t_idx]


def fins_features(P, fins: pd.DataFrame, t_idx: list) -> dict:
    """SEL-B の生の値。開示は usable_from <= T のものだけ（未来の開示は使わない）。"""
    cols = ["Code", "usable_from", "CurFYEn", "FOP", "FNP", "FEPS", "FDivAnn", "BPS", "ROE"]
    f = fins[[c for c in cols if c in fins.columns]].copy()
    for c in ("FOP", "FNP", "FEPS", "FDivAnn", "BPS", "ROE"):
        f[c] = pd.to_numeric(f.get(c), errors="coerce")
    f = f.dropna(subset=["usable_from"]).sort_values(["Code", "usable_from"], kind="stable")
    g = f.groupby(["Code", "CurFYEn"], sort=False)
    for c in ("FOP", "FNP", "FDivAnn"):
        f["prev_" + c] = g[c].shift(1)
    def rev(a, b):
        r = (f[a] - f["prev_" + a]) / f["prev_" + a].abs().replace(0, np.nan)
        return r.clip(-1, 1)
    f["rev_op_raw"], f["rev_np_raw"] = rev("FOP", "FOP"), rev("FNP", "FNP")
    f["div_raw"] = f["FDivAnn"] - f["prev_FDivAnn"]
    didx = pd.Series(np.arange(len(P.dates)), index=P.dates)
    pos = didx.reindex(f["usable_from"].dt.normalize()).ffill()
    pos = np.nan_to_num(pos.to_numpy(), nan=0).astype(int)
    ci = {c: i for i, c in enumerate(P.codes)}
    j = f["Code"].map(ci)
    f = f[j.notna()].copy()
    pos = pos[j.notna().to_numpy()]
    j = j[j.notna()].astype(int).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        r_disc = P.adj_close[pos, j] / P.raw_close[pos, j]
    f["r_disc"] = r_disc
    f["col"] = j
    tdf = pd.DataFrame({"T": np.repeat(P.dates[t_idx].values, len(P.codes)), "col": np.tile(np.arange(len(P.codes)), len(t_idx)),
                        "ti": np.repeat(np.arange(len(t_idx)), len(P.codes))}).sort_values("T")
    m = pd.merge_asof(tdf, f.sort_values("usable_from"), left_on="T", right_on="usable_from", by="col", direction="backward")
    age = (m["T"] - m["usable_from"]).dt.days
    ok = age.le(STALE_DAYS)
    w = np.exp(-age / DECAY_DAYS).where(ok)
    px = P.adj_close[np.array(t_idx)[m["ti"].to_numpy()], m["col"].to_numpy()]
    out = {}
    def put(name, vals):
        a = np.full((len(t_idx), len(P.codes)), np.nan)
        a[m["ti"].to_numpy(), m["col"].to_numpy()] = np.asarray(vals, dtype=float)
        out[name] = a
    put("rev_op", m["rev_op_raw"].fillna(0) * w)
    put("rev_np", m["rev_np_raw"].fillna(0) * w)
    put("div_chg", (m["div_raw"] * m["r_disc"] / px).where(ok) * w)
    put("earn_yield", (m["FEPS"] * m["r_disc"] / px).where(ok))
    put("book_yield", (m["BPS"] * m["r_disc"] / px).where(ok))
    put("roe", m["ROE"].where(ok))
    return out


def standardized(raw: dict, mask: np.ndarray) -> dict:
    return {k: zrows(v, mask) for k, v in raw.items()}
