"""チャート規則の一斉検証（段階 1〜3。仕様は docs/w5_protocol.md の「追加の事前固定」）。

点灯は日 t の引け後に確定、日 t+1 始値で買い、t+1+h 始値で売る。超過 ＝ 日ごとの「点灯銘柄の平均 − 母集団の平均」。
全銘柄を 1 銘柄ずつ処理し、日ごとの合計・件数だけを蓄積する（銘柄ごとの値は保持しない）。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from chartlib import candles as cn
from chartlib import indicators as ind
from forecastlib import features as ff
from forecastlib import stats as st

HORIZONS = (5, 21)
MIN_SIGNALS = 5            # 点灯が 5 銘柄未満の日は使わない
MIN_PHASE_DAYS = 10
ROUND_TRIP_COST = 0.003
SPLIT = pd.Timestamp("2022-04-04")
COND_NAMES = ("regime_up", "regime_down", "vol_yes", "vol_no", "earn_yes", "earn_no")


# ---------------------------------------------------------------- 規則
def rule_signals(df: pd.DataFrame) -> pd.DataFrame:
    """基本の 49 規則（signal_frame の 41 ＋ 未使用のローソク足 8）。日 t の引け後に確定する真偽値。"""
    s = ff.signal_frame(df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    pt = cn.prior_trend(c, 5)
    down, up = pt.shift(1) < 0, pt.shift(1) > 0                 # 強気は直前が下落、弱気は直前が上昇（signal_frame の包み線と同じ形）
    extra = {"bullish_harami": cn.bullish_harami(o, h, l, c) & down, "bearish_harami": cn.bearish_harami(o, h, l, c) & up,
             "piercing_line": cn.piercing_line(o, h, l, c) & down, "dark_cloud_cover": cn.dark_cloud_cover(o, h, l, c) & up,
             "morning_star": cn.morning_star(o, h, l, c) & down, "evening_star": cn.evening_star(o, h, l, c) & up,
             "three_white_soldiers": cn.three_white_soldiers(o, h, l, c) & down, "three_black_crows": cn.three_black_crows(o, h, l, c) & up}
    for k, v in extra.items():
        s[k] = v.fillna(False).astype(bool)
    return s


def volume_surge(df: pd.DataFrame) -> pd.Series:
    """出来高が前日までの 20 日平均の 2 倍超。"""
    v = df["volume"].where(df["volume"] > 0)
    return (v > 2.0 * ind.sma(v, 20).shift(1)).fillna(False)


def base_builders(names) -> dict:
    return {n: (lambda ctx, n=n: ctx.sig[n].to_numpy()) for n in names}


def type_builders() -> dict:
    """段階 3 の 3 つの型（4 規則）。"""
    def pullback(x):
        S = x.sig
        return (S["sma25_gt_sma75"] & S["above_sma75"] & (S["rsi_lt30"] | S["stoch_lt20"] | S["bb_below_lower"])).to_numpy()

    def breakout(x):
        return (x.sig["donchian20_up"] & x.vol_surge).to_numpy()

    def oversold(x):
        return (x.sig["kairi25_lt_m10"] | x.sig["crash_5d"]).to_numpy()

    return {"type_pullback": pullback, "type_breakout": breakout, "type_oversold_all": oversold,
            "type_oversold_no_earnings": lambda x: oversold(x) & ~x.earn5}


def conditional_builders(base_names) -> dict:
    """段階 2: 基本規則 × 3 条件の各 2 状態。"""
    cond = {"regime_up": lambda x: x.regime, "regime_down": lambda x: ~x.regime, "vol_yes": lambda x: x.vol_surge.to_numpy(),
            "vol_no": lambda x: ~x.vol_surge.to_numpy(), "earn_yes": lambda x: x.earn5, "earn_no": lambda x: ~x.earn5}
    out = {}
    for n in base_names:
        for cn_, f in cond.items():
            out[f"{n}&{cn_}"] = (lambda x, n=n, f=f: x.sig[n].to_numpy() & f(x))
    return out


# ---------------------------------------------------------------- 蓄積
def forward_returns(P, h: int) -> np.ndarray:
    """F[t, j] ＝ 調整後始値の t+1 → t+1+h のリターン。"""
    F = np.full(P.adj_open.shape, np.nan)
    F[: -(h + 1)] = P.adj_open[h + 1:] / P.adj_open[1:-h] - 1.0
    return F


def executable(P) -> np.ndarray:
    """t+1 に始値があり、ストップ高でない。"""
    ex = np.zeros(P.raw_open.shape, dtype=bool)
    ex[:-1] = np.isfinite(P.raw_open[1:]) & ~P.limit_up[1:]
    return ex


def tertiles(P, elig: np.ndarray) -> np.ndarray:
    """日ごとの流動性の 3 分位（0 が低い）。対象銘柄のみ。"""
    va = P.va60()
    out = np.full(elig.shape, -1, dtype=np.int8)
    for t in range(elig.shape[0]):
        m = np.flatnonzero(elig[t])
        if len(m) >= 3:
            r = va[t, m].argsort().argsort()
            out[t, m] = (r * 3 // len(m)).astype(np.int8)
    return out


def earnings_flags(P, fins: pd.DataFrame, days: int = 5) -> np.ndarray:
    """直近 days 営業日（当日含む）に、財務の開示（usable_from）があった日。"""
    flag = np.zeros(P.adj_close.shape, dtype=bool)
    ci = {c: i for i, c in enumerate(P.codes)}
    f = fins[["Code", "usable_from"]].dropna()
    cols = f["Code"].map(ci)
    pos = np.searchsorted(P.dates.values, f["usable_from"].to_numpy(), side="left")
    for j, p in zip(cols.to_numpy(), pos):
        if np.isfinite(j) and p < len(P.dates):
            flag[p: p + days, int(j)] = True
    return flag


def regime_up(P) -> np.ndarray:
    c = P.topix["close"]
    return (c > c.rolling(200, min_periods=200).mean()).fillna(False).to_numpy()


def run_pass(P, elig: np.ndarray, builders: dict, fins: pd.DataFrame, horizons=HORIZONS, progress=None, extras: dict | None = None,
             feats: bool = False) -> dict:
    n_t, n_j = P.adj_close.shape
    names = list(builders)
    R, H = len(names), len(horizons)
    F = [forward_returns(P, h) for h in horizons]
    ex = executable(P)
    tert = tertiles(P, elig)
    ok = elig & ex
    acc = {"names": names, "horizons": list(horizons), "dates": P.dates,
           "cnt": np.zeros((H, R, n_t)), "sum": np.zeros((H, R, n_t)), "cnt3": np.zeros((H, 3, R, n_t)), "sum3": np.zeros((H, 3, R, n_t)),
           "ucnt": np.zeros((H, n_t)), "usum": np.zeros((H, n_t)), "ucnt3": np.zeros((H, 3, n_t)), "usum3": np.zeros((H, 3, n_t))}
    for hi in range(H):
        m = ok & np.isfinite(F[hi])
        acc["ucnt"][hi] = m.sum(axis=1)
        acc["usum"][hi] = np.where(m, F[hi], 0.0).sum(axis=1)
        for q in range(3):
            mq = m & (tert == q)
            acc["ucnt3"][hi, q] = mq.sum(axis=1)
            acc["usum3"][hi, q] = np.where(mq, F[hi], 0.0).sum(axis=1)
    earn = earnings_flags(P, fins)
    reg = regime_up(P)
    cols = np.flatnonzero(ok.any(axis=0))
    for n_done, j in enumerate(cols):
        d = pd.DataFrame({"open": P.adj_open[:, j], "high": P.adj_high[:, j], "low": P.adj_low[:, j], "close": P.adj_close[:, j],
                          "volume": P.volume[:, j]}, index=P.dates)
        v = d.dropna(subset=["open", "high", "low", "close"])
        if len(v) < 300:
            continue
        sig = rule_signals(v).reindex(P.dates, fill_value=False)
        vs = volume_surge(v).reindex(P.dates, fill_value=False)
        ctx = SimpleNamespace(sig=sig, vol_surge=vs, earn5=earn[:, j], regime=reg, v=v, dates=P.dates)
        if feats:
            ctx.f = stock_feats(v).reindex(P.dates)
            ctx.u3 = extras["u3"][:, j] if extras and "u3" in extras else np.zeros(n_t, dtype=bool)
            ctx.mkt_down = extras["mkt_down"] if extras and "mkt_down" in extras else np.zeros(n_t, dtype=bool)
            ctx.mkt_ext = extras.get("mkt_ext", {}) if extras else {}
        valid = ok[:, j]
        for r, nm in enumerate(names):
            s = np.asarray(builders[nm](ctx), dtype=bool) & valid
            if not s.any():
                continue
            for hi in range(H):
                f = F[hi][:, j]
                m = s & np.isfinite(f)
                acc["cnt"][hi, r] += m
                acc["sum"][hi, r] += np.where(m, f[:], 0.0)
                for q in range(3):
                    mq = m & (tert[:, j] == q)
                    acc["cnt3"][hi, q, r] += mq
                    acc["sum3"][hi, q, r] += np.where(mq, f[:], 0.0)
        if progress and n_done % 200 == 0:
            progress(n_done, len(cols))
    return acc


# ---------------------------------------------------------------- 統計
def period_mask(dates, h: int, which: str) -> np.ndarray:
    """発見期間（境界の h+1 営業日前まで）と確認期間（境界以降）の点灯日 t。"""
    b = int(np.searchsorted(pd.DatetimeIndex(dates).values, SPLIT.to_datetime64(), side="left"))
    t = np.arange(len(dates))
    return (t <= b - h - 2) if which == "discovery" else (t >= b)


def spread_stats(d: np.ndarray, active: np.ndarray, h: int) -> dict:
    """日ごとの超過 d（active の日だけ）。重ならない日付の列を h 通りの位相でとり、t 値の平均を使う。平均は全日。"""
    pos = np.flatnonzero(active)
    x = d[pos]
    n = len(x)
    if n < MIN_PHASE_DAYS * 2:
        return {"days": int(n), "mean": float("nan"), "t": float("nan"), "p": float("nan")}
    ts = []
    for ph in range(h):
        y = x[(pos % h) == ph]
        if len(y) >= MIN_PHASE_DAYS and y.std(ddof=1) > 0:
            ts.append(y.mean() / (y.std(ddof=1) / math.sqrt(len(y))))
    t = float(np.mean(ts)) if ts else float("nan")
    p = float(2 * st.norm_sf(abs(t))) if np.isfinite(t) else float("nan")
    return {"days": int(n), "mean": float(x.mean()), "t": t, "p": p}


def rule_table(acc: dict, which: str, names=None) -> dict:
    """規則 × 期間 h の表。which: discovery / confirmation。"""
    out = {}
    for hi, h in enumerate(acc["horizons"]):
        pm = period_mask(acc["dates"], h, which)
        for r, nm in enumerate(acc["names"]):
            if names is not None and nm not in names:
                continue
            cnt = acc["cnt"][hi, r]
            with np.errstate(divide="ignore", invalid="ignore"):
                spread = acc["sum"][hi, r] / cnt - acc["usum"][hi] / acc["ucnt"][hi]
            active = pm & (cnt >= MIN_SIGNALS) & (acc["ucnt"][hi] > 0)
            s = spread_stats(np.nan_to_num(spread), active, h)
            s["signals_per_day"] = float(cnt[active].mean()) if active.any() else float("nan")
            s["net_of_round_trip_cost"] = s["mean"] - ROUND_TRIP_COST if np.isfinite(s["mean"]) else float("nan")
            tert = []
            for q in range(3):
                c3 = acc["cnt3"][hi, q, r]
                with np.errstate(divide="ignore", invalid="ignore"):
                    sp3 = acc["sum3"][hi, q, r] / c3 - acc["usum3"][hi, q] / acc["ucnt3"][hi, q]
                a3 = pm & (c3 >= 3) & (acc["ucnt3"][hi, q] > 0)
                tert.append(float(np.nan_to_num(sp3)[a3].mean()) if a3.any() else float("nan"))
            s["mean_by_liquidity_tertile(low,mid,high)"] = tert
            out[(nm, h)] = s
    return out


def discover(acc: dict, q: float = 0.10) -> dict:
    """発見期間: BH で補正し、補正後に有意な (規則, h) を返す。"""
    tab = rule_table(acc, "discovery")
    keys = list(tab)
    qv = st.bh_fdr(np.array([tab[k]["p"] for k in keys]))
    for k, qq in zip(keys, qv):
        tab[k]["q"] = float(qq)
    return {"table": tab, "passed": [k for k in keys if np.isfinite(tab[k]["q"]) and tab[k]["q"] < q], "n_tests": int(np.isfinite([tab[k]["p"] for k in keys]).sum())}


def confirm(acc: dict, passed: list) -> dict:
    """確認期間（発見期間の通過規則だけを読む）。同じ符号かつ両側 p < 0.05 を「確認」とする。"""
    tab = rule_table(acc, "confirmation", names={k[0] for k in passed})
    return {k: tab[k] for k in passed if k in tab}


def diff_table(acc: dict, which: str, pairs: list, stat_fn=None) -> dict:
    """2 つの規則（例: X&earn_no と X&earn_yes）の、日ごとの超過の差の検定。pairs: [(ラベル, 規則 a, 規則 b)]。差 = a の超過 − b の超過。"""
    out = {}
    names = acc["names"]
    for hi, h in enumerate(acc["horizons"]):
        pm = period_mask(acc["dates"], h, which)
        for label, a, b in pairs:
            ia, ib = names.index(a), names.index(b)
            ca, cb = acc["cnt"][hi, ia], acc["cnt"][hi, ib]
            with np.errstate(divide="ignore", invalid="ignore"):
                sp = (acc["sum"][hi, ia] / ca) - (acc["sum"][hi, ib] / cb)
            active = pm & (ca >= MIN_SIGNALS) & (cb >= MIN_SIGNALS)
            s = (stat_fn or spread_stats)(np.nan_to_num(sp), active, h)
            s["signals_per_day"] = float(min(ca[active].mean(), cb[active].mean())) if active.any() else float("nan")
            s["net_of_round_trip_cost"] = float("nan")
            s["mean_by_liquidity_tertile(low,mid,high)"] = [float("nan")] * 3
            out[(label, h)] = s
    return out


# ---------------------------------------------------------------- 底打ち・上昇しやすい局面・下がり方の特徴
def stock_feats(v: pd.DataFrame) -> pd.DataFrame:
    """1 銘柄の指標（日 t の引け後までの情報だけ）。v は欠損のない日足（open/high/low/close/volume）。"""
    o, h, l, c, vol = v["open"], v["high"], v["low"], v["close"], v["volume"]
    vv = vol.where(vol > 0)
    lr = np.log(c).diff()
    gk = (np.log(o / c.shift(1)) ** 2 + 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2)
    vc = np.sqrt(gk.rolling(5, min_periods=4).mean() / gk.rolling(22, min_periods=18).mean().replace(0, np.nan))
    f = pd.DataFrame(index=v.index)
    f["c"], f["vol"] = c, vol
    f["sma25"], f["sma75"] = ind.sma(c, 25), ind.sma(c, 75)
    f["ret5"], f["ret20"] = c / c.shift(5) - 1, c / c.shift(20) - 1
    f["max252"], f["min252"] = c.rolling(252).max(), c.rolling(252).min()
    f["low60"] = l.rolling(60).min()
    f["newlow60"] = (c <= c.shift(1).rolling(60).min()).astype(float)
    f["rsi"] = ind.rsi(c, 14)
    f["vol_ratio"] = vv / ind.sma(vv, 20).shift(1)
    f["hammer"] = cn.hammer_shape(o, h, l, c).astype(float)
    f["gap"] = o / c.shift(1) - 1
    f["vol5"], f["vol20"] = vol.rolling(5).mean(), vol.rolling(20).mean()
    f["vol60"] = lr.rolling(60).std()
    f["vol60_med252"] = f["vol60"].rolling(252).median()
    f["vc"] = vc
    f["vc_p10"] = vc.rolling(252, min_periods=200).quantile(0.10)
    f["donchian_up"] = (c > h.rolling(20).max().shift(1)).astype(float)
    f["newhigh252"] = (c >= f["max252"]).astype(float)
    return f


def _b(x) -> np.ndarray:
    return np.asarray(pd.Series(x).fillna(False).astype(bool))


def bottom_up_builders() -> dict:
    """家族 1（6 規則）。docs/w5_protocol.md の定義どおり。"""
    def b1(x):
        f = x.f
        return _b((f.c <= 0.70 * f.max252) & (f.newlow60.rolling(10, min_periods=1).sum() == 0) & (f.c > f.sma25) & (f.c.shift(1) <= f.sma25.shift(1)))

    def b2(x):
        f = x.f
        ev = ((f.ret20 <= -0.15) & (f.vol_ratio > 3) & (f.hammer > 0)).fillna(False)
        return _b(ev.shift(5, fill_value=False) & (f.newlow60.rolling(5, min_periods=1).sum() == 0))

    def b3(x):
        f = x.f
        return _b((f.c / f.low60 - 1 >= 0.10) & (f.rsi > 50) & (f.rsi.shift(1) <= 50) & (f.rsi.rolling(10).min() < 40))

    def u1(x):
        f = x.f
        s = (f.newhigh252 > 0).fillna(False).shift(5, fill_value=False)
        shallow = f.c.rolling(5).min() / f.c.shift(5) - 1 >= -0.03
        quiet = f.vol.rolling(5).mean() < f.vol.rolling(20).mean().shift(5)
        return _b(s & shallow & quiet & (f.c > f.sma25))

    def u2(x):
        f = x.f
        return _b((f.vc <= f.vc_p10) & (f.donchian_up > 0) & pd.Series(x.regime, index=f.index))

    def u3(x):
        f = x.f
        return _b(pd.Series(x.u3, index=f.index) & (f.c > f.sma75))

    return {"B1_higher_low_cross": b1, "B2_capitulation_hold": b2, "B3_bounce_rsi": b3, "U1_shallow_pullback": u1, "U2_squeeze_breakout": u2,
            "U3_value_revision_trend": u3}


DROP_DESCRIPTORS = ("D1_capitulation_volume", "D2_fast_drop", "D3_gap_down", "D4_deep", "D5_near_52w_low", "D6_market_wide", "D7_volume_dryup",
                    "D8_vol_expansion", "D9_low_price", "D10_prior_uptrend")


def drop_builders() -> dict:
    """家族 2: 下げ状態（20 営業日リターン ≤ −15%）と、10 特徴の yes / no。"""
    def base(x):
        return (x.f.ret20 <= -0.15).fillna(False)

    def desc(x) -> dict:
        f = x.f
        return {"D1_capitulation_volume": (f.vol_ratio > 3).rolling(10, min_periods=1).max() > 0,
                "D2_fast_drop": f.ret5 <= -0.10,
                "D3_gap_down": (f.gap <= -0.03).rolling(5, min_periods=1).max() > 0,
                "D4_deep": f.ret20 <= -0.25,
                "D5_near_52w_low": f.c <= 1.05 * f.min252,
                "D6_market_wide": pd.Series(x.mkt_down, index=f.index),
                "D7_volume_dryup": f.vol5 < 0.5 * f.vol20,
                "D8_vol_expansion": f.vol60 > f.vol60_med252,
                "D9_low_price": f.c < 500,
                "D10_prior_uptrend": f.c.shift(20) > f.sma75.shift(20)}

    out = {"drop": lambda x: _b(base(x))}
    for d in DROP_DESCRIPTORS:
        out[f"drop&{d}_yes"] = lambda x, d=d: _b(base(x) & desc(x)[d].fillna(False))
        out[f"drop&{d}_no"] = lambda x, d=d: _b(base(x) & ~desc(x)[d].fillna(False))
    return out


def u3_matrix(P, fins: pd.DataFrame, elig: np.ndarray, chunk: int = 150) -> np.ndarray:
    """U3 の横断面の条件 [日付, 銘柄]: 予想益利回りが、その日の対象銘柄の上位 20%、かつ 純利益予想の上方修正（rev_np > 0）。"""
    from selectlib import features as feat
    out = np.zeros(elig.shape, dtype=bool)
    for a in range(0, len(P.dates), chunk):
        idx = list(range(a, min(a + chunk, len(P.dates))))
        raw = feat.fins_features(P, fins, idx)
        ey, rv = raw["earn_yield"], raw["rev_np"]
        for r, t in enumerate(idx):
            m = elig[t] & np.isfinite(ey[r])
            if m.sum() < 20:
                continue
            thr = np.percentile(ey[r][m], 80)
            out[t] = m & (ey[r] >= thr) & (np.nan_to_num(rv[r], nan=0.0) > 0)
    return out


def mkt_down(P, days: int = 20, thr: float = -0.05) -> np.ndarray:
    c = P.topix["close"]
    return (c / c.shift(days) - 1 <= thr).fillna(False).to_numpy()
