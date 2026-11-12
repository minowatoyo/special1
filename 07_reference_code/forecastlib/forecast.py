"""最終日の予測の組み立て（価格の分位点、しきい値・水準ごとの確率、期間中の高値・安値、類似局面）。

用語:
  * 終値が水準より上の確率: 期間の終わり（h 営業日後）の終値についての確率
  * 到達確率: 期間中（1〜h 営業日後）の高値（安値）が一度でも水準に届く確率
到達確率は、過去の各時点から h 日間の高値・安値を σ で標準化した経験分布から求める（V3 の σ を使う）。
採用モデルが B0（伸縮なし）のときは、標準化しない過去の高値・安値の分布をそのまま使う。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from chartlib import indicators as ind
from chartlib import swings

from . import stats as st

__all__ = ["auto_levels", "final_forecast", "scenario_probabilities", "conditional_table", "PCT_THRESHOLDS", "QUANT_PROBS"]

QUANT_PROBS = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
PCT_THRESHOLDS = {5: (0.03, 0.05, 0.10), 21: (0.05, 0.10, 0.15), 63: (0.10, 0.15, 0.20, 0.30)}


def _round_step(price: float) -> float:
    mag = 10 ** math.floor(math.log10(price))
    for mult in (0.1, 0.25, 0.5, 1.0):
        step = mag * mult
        if price / step <= 40:
            return step
    return mag


def auto_levels(df: pd.DataFrame, max_dist: float = 0.35) -> list:
    """チャート上の主な水準（移動平均、52 週・20 日の高値安値、一目の雲、確定したスイング、ボリンジャー、切りのよい価格）。"""
    h, l, c = df["high"], df["low"], df["close"]
    c0 = float(c.iloc[-1])
    lv = []

    def add(name, price):
        if price is not None and np.isfinite(price) and price > 0 and abs(price / c0 - 1.0) <= max_dist:
            lv.append({"name": name, "price": float(price)})

    for n in (25, 75, 200):
        add(f"{n}日移動平均", ind.sma(c, n).iloc[-1])
    add("52週高値", h.rolling(252).max().iloc[-1])
    add("52週安値", l.rolling(252).min().iloc[-1])
    add("20日高値", h.rolling(20).max().iloc[-1])
    add("20日安値", l.rolling(20).min().iloc[-1])
    ich = ind.ichimoku(h, l, c)
    add("一目の雲の上限", max(ich["senkou_a"].iloc[-1], ich["senkou_b"].iloc[-1]))
    add("一目の雲の下限", min(ich["senkou_a"].iloc[-1], ich["senkou_b"].iloc[-1]))
    add("一目の基準線", ich["kijun"].iloc[-1])
    bb = ind.bollinger(c, 20, 2.0)
    add("ボリンジャー+2σ", bb["upper"].iloc[-1])
    add("ボリンジャー−2σ", bb["lower"].iloc[-1])
    tail = df.iloc[-260:]
    sw = swings.swing_points(tail["high"], tail["low"], 5, 5)
    if len(sw):
        hs = sw[sw["kind"] == "H"].tail(2)
        ls = sw[sw["kind"] == "L"].tail(2)
        for _, r in hs.iterrows():
            add(f"スイング高値（{pd.Timestamp(r['time']).date()}）", r["price"])
        for _, r in ls.iterrows():
            add(f"スイング安値（{pd.Timestamp(r['time']).date()}）", r["price"])
    step = _round_step(c0)
    add("切りのよい価格（上）", math.floor(c0 / step) * step + step)
    add("切りのよい価格（下）", math.ceil(c0 / step) * step - step)
    lv.sort(key=lambda d: d["price"])
    out = []
    for d in lv:
        if out and abs(d["price"] / out[-1]["price"] - 1.0) < 0.003:
            out[-1]["name"] += "／" + d["name"]
        elif abs(d["price"] / c0 - 1.0) >= 0.002:
            out.append(d)
    return out


def _frac_ge(sorted_x: np.ndarray, x: float) -> float:
    return float("nan") if len(sorted_x) == 0 else 1.0 - float(np.searchsorted(sorted_x, x, side="left")) / len(sorted_x)


def _frac_le(sorted_x: np.ndarray, x: float) -> float:
    return float("nan") if len(sorted_x) == 0 else float(np.searchsorted(sorted_x, x, side="right")) / len(sorted_x)


def final_forecast(asset, wf: dict, decisions: dict, cfg, levels: list | None = None) -> dict:
    """採用モデルによる最終日の予測。戻り値は JSON にできる辞書。"""
    c0 = float(asset.close[-1])
    asof = str(pd.Timestamp(asset.dates[-1]).date())
    levels = levels if levels is not None else auto_levels(asset.df)
    out = {"asset": asset.name, "asof": asof, "last_close": c0, "horizons": {}, "levels": levels}
    for h, res in wf.items():
        fin, taus = res["final"], res["taus"]
        if not fin:
            continue
        dec = decisions[h]
        model = dec["final_model"]
        g = fin["grids"][model]
        if not np.isfinite(g).all():
            model = dec["sigma_model"]
            g = fin["grids"][model]
        s3 = fin["sigma"]["S3"]
        mu = fin["mu"].get(model, 0.0) if model in fin["mu"] else 0.0
        mu = mu if np.isfinite(mu) else 0.0
        used = {"B1": "S1", "V2": "S2"}.get(model, "S3")            # 採用モデルが使う σ（B0 は伸縮なしなので参考値）
        s_used = fin["sigma"][used]
        hz = {"h": h, "model": model, "sigma_h": s_used, "sigma_model": used, "sigma_h_s1": fin["sigma"]["S1"],
              "sigma_h_s2": fin["sigma"]["S2"], "sigma_h_s3": s3, "drift_h": fin.get("drift", 0.0),
              "vol_annual": s_used / math.sqrt(h) * math.sqrt(250.0), "n_eligible": int(fin["n_eligible"]), "tilt_mu_z": mu}
        hz["quantiles"] = [{"p": p, "ret": float(math.expm1(st.quantile_from_grid(p, g, taus))),
                            "price": float(c0 * math.exp(st.quantile_from_grid(p, g, taus)))} for p in QUANT_PROBS]
        hz["p_up"] = 1.0 - st.cdf_from_grid(0.0, g, taus)
        hz["thresholds"] = [{"pct": x, "p_ge": 1.0 - st.cdf_from_grid(math.log1p(x), g, taus),
                             "p_le": st.cdf_from_grid(math.log1p(-x), g, taus)} for x in PCT_THRESHOLDS.get(h, (0.05, 0.10))]
        if model == "B0":                                  # 伸縮なし: 過去の高値・安値の分布をそのまま使う
            mhz, mlz, unit = fin["touch_sorted"]["MH"], fin["touch_sorted"]["ML"], 1.0
        else:
            mhz, mlz, unit = fin["touch_sorted"]["MHz"], fin["touch_sorted"]["MLz"], s3
        shift = 0.5 * mu                                   # 傾きを採用した場合の近似（経路の平均的なずれ）
        lv = []
        for d in levels:
            x = math.log(d["price"] / c0)
            row = {"name": d["name"], "price": d["price"], "dist": d["price"] / c0 - 1.0,
                   "p_close_above": 1.0 - st.cdf_from_grid(x, g, taus)}
            row["p_touch"] = _frac_ge(mhz, x / unit - shift) if x > 0 else _frac_le(mlz, x / unit - shift)
            lv.append(row)
        hz["levels"] = lv
        hz["period_high"] = [{"p": p, "price": float(c0 * math.exp(unit * (np.quantile(mhz, p) + shift)))} for p in (0.25, 0.5, 0.75)] if len(mhz) else []
        hz["period_low"] = [{"p": p, "price": float(c0 * math.exp(unit * (np.quantile(mlz, p) + shift)))} for p in (0.25, 0.5, 0.75)] if len(mlz) else []
        hz["all_models"] = {m: {"median": float(c0 * math.exp(st.quantile_from_grid(0.5, gm, taus))),
                                "q10": float(c0 * math.exp(st.quantile_from_grid(0.10, gm, taus))),
                                "q90": float(c0 * math.exp(st.quantile_from_grid(0.90, gm, taus))),
                                "p_up": 1.0 - st.cdf_from_grid(0.0, gm, taus)}
                            for m, gm in fin["grids"].items() if np.isfinite(gm).all()}
        kd = res["knn_dist"]
        hist = kd[np.isfinite(kd)]
        if len(hist) > 50 and np.isfinite(kd[-1]):
            hz["analog_distance_pct"] = float((hist[:-1] < kd[-1]).mean())
        hz["grid"] = {"taus": [float(t) for t in taus], "logret": [float(v) for v in g]}
        out["horizons"][h] = hz
    out["analogs"] = _analogs(asset, wf, cfg)
    return out


def _analogs(asset, wf: dict, cfg, top: int = 10, min_gap: int = 10) -> list:
    """最長の期間で使った近傍のうち、最も近い過去の日を、互いに min_gap 営業日以上離して top 件まで。"""
    if not wf:
        return []
    hmax = max(wf.keys())
    nb = wf[hmax]["final"].get("neighbors") if wf[hmax]["final"] else None
    if nb is None:
        return []
    idx, dist = nb
    order = np.argsort(dist)
    chosen = []
    for j in order:
        i = int(idx[j])
        if all(abs(i - k) >= min_gap for k, _ in chosen):
            chosen.append((i, float(dist[j])))
        if len(chosen) >= top:
            break
    rows = []
    for i, dj in chosen:
        row = {"date": str(pd.Timestamp(asset.dates[i]).date()), "distance": dj, "close": float(asset.close[i])}
        for h in wf:
            r = asset.R[h][i]
            s_then, s_now = asset.sig[h]["S3"][i], wf[h]["final"]["sigma"]["S3"]
            row[f"ret_{h}"] = float(math.expm1(r)) if np.isfinite(r) else None
            row[f"scaled_{h}"] = float(math.expm1(r / s_then * s_now)) if np.isfinite(r) and np.isfinite(s_then) else None
        rows.append(row)
    return rows


def conditional_table(df: pd.DataFrame, aux_close: pd.Series, lag: int = 0, window: int = 750, k: int = 5) -> dict:
    """補助系列（指数・為替など）との連動。直近 window 営業日の、重ならない k 日リターンどうしの回帰。

    予測のためではなく、「指数（為替）がこれだけ動いたら、この銘柄はどのくらい動きやすいか」という
    条件つきの見方のための表である。為替や指数の変化は同じ時点で株価に織り込まれるとされ、遅れて効く
    という証拠は乏しいので、方向の予測には使わない。終値の時刻がずれる系列（lag=1）でも、k 日リターンに
    すれば時刻のずれの影響は小さい。戻り値: beta、標準誤差、R²、標本数。
    """
    a = aux_close.dropna().sort_index()
    left = pd.DataFrame({"date": df.index})
    right = pd.DataFrame({"date": a.index, "v": a.to_numpy(dtype=float)})
    al = pd.merge_asof(left, right, on="date")["v"].to_numpy()
    lc, la = np.log(df["close"].to_numpy(dtype=float)), np.log(al)
    idx = np.arange(len(lc) - 1, max(len(lc) - 1 - window, k), -k)[::-1]
    ys, xs = np.diff(lc[idx]), np.diff(la[idx])
    ok = np.isfinite(ys) & np.isfinite(xs)
    ys, xs = ys[ok], xs[ok]
    if len(ys) < 30 or xs.std() == 0:
        return {"n": int(len(ys)), "beta": float("nan"), "se": float("nan"), "r2": float("nan"), "k": k, "lag": lag}
    x = np.column_stack([np.ones(len(xs)), xs])
    res = st.nw_ols(ys, x, 2)
    fit = x @ res["beta"]
    r2 = 1.0 - float(((ys - fit) ** 2).sum() / ((ys - ys.mean()) ** 2).sum())
    return {"n": int(len(ys)), "beta": float(res["beta"][1]), "se": float(res["se"][1]), "r2": r2, "k": k, "lag": lag,
            "resid_sd_k": float((ys - fit).std(ddof=2))}


def scenario_probabilities(fc: dict, scenarios: list) -> list:
    """終値が区間 [lo, hi) に入る確率。scenarios = [{h, name, lo, hi, weight}]（lo・hi は None で無限）。"""
    out = []
    c0 = fc["last_close"]
    for s in scenarios:
        hz = fc["horizons"].get(s["h"]) or fc["horizons"].get(str(s["h"]))
        if not hz:
            continue
        taus, g = np.array(hz["grid"]["taus"]), np.array(hz["grid"]["logret"])
        f_hi = 1.0 if s.get("hi") is None else st.cdf_from_grid(math.log(s["hi"] / c0), g, taus)
        f_lo = 0.0 if s.get("lo") is None else st.cdf_from_grid(math.log(s["lo"] / c0), g, taus)
        out.append({**s, "prob": float(max(f_hi - f_lo, 0.0))})
    return out
