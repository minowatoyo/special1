"""探索マップ（記述。発見期間のみ）。仕様は docs/w5_protocol.md「探索マップ」。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/explore_map.py        # 約 10〜15 分
検定ではない。試行台帳には書かない。確認期間（2022-04-04 以降）のデータには触れない。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from forecastlib import stats as st  # noqa: E402
from selectlib import evalsel, features, margin, rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

HS = (5, 21, 63, 126)
AFFORDABLE_YEN = 3300
REACTION_BINS = [(-9.0, -0.05, "<=-5%"), (-0.05, -0.02, "-5..-2%"), (-0.02, 0.02, "-2..+2%"), (0.02, 0.05, "+2..+5%"), (0.05, 9.0, ">=+5%")]


def boundary(P) -> int:
    return int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))


def mean_t(x, lags: int = 0) -> dict:
    """平均と t 値（重なりがあれば Newey–West）。"""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 8:
        return {"n": int(n), "mean": float(x.mean()) if n else None, "t": None}
    se = math.sqrt(st.hac_variance(x, lags)) if lags > 0 else x.std(ddof=1) / math.sqrt(n)
    return {"n": int(n), "mean": round(float(x.mean()), 5), "t": round(float(x.mean() / se), 2) if se > 0 else None}


def excess_forward(P, ok: np.ndarray, h: int) -> np.ndarray:
    """t+1 始値 → t+1+h 始値のリターン − 同じ日の母集団平均（対象外は NaN）。"""
    F = rules.forward_returns(P, h)
    F = np.where(ok, F, np.nan)
    with np.errstate(invalid="ignore"):
        return F - np.nanmean(F, axis=1, keepdims=True)


def feature_matrix(P, fins, mg, t_idx) -> dict:
    f = {**features.chart_features(P, t_idx), **features.fins_features(P, fins, t_idx)}
    if mg is not None:
        mv = margin.margin_values(P, mg)
        to20 = pd.DataFrame(P.turnover).fillna(0.0).rolling(20, min_periods=15).mean().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            lv = mv["long_vol"] * P.raw_close / np.where(to20 > 0, to20, np.nan)
            sv = mv["short_vol"] * P.raw_close / np.where(to20 > 0, to20, np.nan)
            f["margin_long_days"] = lv[t_idx]                      # 買い残は、売買代金の何日分か
            f["margin_short_days"] = sv[t_idx]
            f["margin_long_short_ratio"] = (mv["long_vol"] / np.where(mv["short_vol"] > 0, mv["short_vol"], np.nan))[t_idx]
    return f


def v1_v2_v3(P, ok, feats, t_idx, b) -> dict:
    va = P.va60()
    out = {"ic_by_horizon": {}, "quintiles": {}, "top_quintile_by_liquidity_tertile_h21": {}, "top_quintile_affordable_only_h21": {}}
    for h in HS:
        E = excess_forward(P, ok, h)
        sel = [i for i, T in enumerate(t_idx) if T <= b - h - 2]
        lags = max(math.ceil(h / 21) - 1, 0)
        for name, X in feats.items():
            ics, top, bot, tl, aff = [], [], [], [[], [], []], []
            for i in sel:
                T = t_idx[i]
                x, y = X[i], E[T]
                m = ok[T] & np.isfinite(x) & np.isfinite(y)
                if m.sum() < 50:
                    continue
                ics.append(evalsel.rank_ic(x, y, m))
                q20, q80 = np.percentile(x[m], [20, 80])
                hi, lo = m & (x >= q80), m & (x <= q20)
                top.append(y[hi].mean())
                bot.append(y[lo].mean())
                if h == 21:
                    r = va[T][m].argsort().argsort() * 3 // m.sum()
                    idx = np.flatnonzero(m)
                    for q in range(3):
                        mm = np.zeros_like(m)
                        mm[idx[r == q]] = True
                        s = mm & (x >= q80)
                        tl[q].append(y[s].mean() if s.any() else np.nan)
                    a = hi & (P.raw_close[T] <= AFFORDABLE_YEN)
                    aff.append(y[a].mean() if a.any() else np.nan)
            out["ic_by_horizon"].setdefault(name, {})[h] = mean_t(ics, lags)
            if h in (21, 63):
                out["quintiles"].setdefault(name, {})[h] = {"top_minus_universe": mean_t(top, lags), "bottom_minus_universe": mean_t(bot, lags)}
            if h == 21:
                out["top_quintile_by_liquidity_tertile_h21"][name] = [mean_t(x)["mean"] for x in tl]
                out["top_quintile_affordable_only_h21"][name] = mean_t(aff)
    return out


def v4_earnings_reaction(P, ok, fins, b) -> dict:
    """決算の開示が使えるようになった最初の営業日（usable_from）の値動きで分け、翌営業日始値からの超過を見る。"""
    c = P.adj_close
    with np.errstate(divide="ignore", invalid="ignore"):
        r1 = np.full(c.shape, np.nan)
        r1[1:] = c[1:] / c[:-1] - 1
    r1x = np.where(ok, r1, np.nan)
    with np.errstate(invalid="ignore"):
        r1x = r1x - np.nanmean(r1x, axis=1, keepdims=True)
    ci = {k: i for i, k in enumerate(P.codes)}
    f = fins[["Code", "usable_from"] + (["DocType"] if "DocType" in fins.columns else [])].dropna(subset=["usable_from"]).copy()
    f["col"] = f["Code"].map(ci)
    f = f.dropna(subset=["col"])
    f["t"] = np.searchsorted(P.dates.values, f["usable_from"].to_numpy(), side="left")
    f = f[(f["t"] < len(P.dates)) & (P.dates.values[np.minimum(f["t"].to_numpy(), len(P.dates) - 1)] == f["usable_from"].to_numpy())]
    kind = f["DocType"].astype(str) if "DocType" in f.columns else pd.Series("FinancialStatements", index=f.index)
    groups = {"earnings_statements": kind.str.contains("FinancialStatements"), "forecast_revisions": kind.str.contains("Revision")}
    out = {}
    for gname, gm in groups.items():
        ev = f[gm.to_numpy()].drop_duplicates(["col", "t"])
        tt, jj = ev["t"].to_numpy(), ev["col"].to_numpy(dtype=int)
        react = r1x[tt, jj]
        res = {}
        for h in (21, 63):
            E = excess_forward(P, ok, h)
            y = E[tt, jj]
            valid = np.isfinite(react) & np.isfinite(y) & (tt <= b - h - 2)
            rows = {}
            for lo, hi, label in REACTION_BINS:
                m = valid & (react > lo) & (react <= hi)
                if m.sum() < 30:
                    rows[label] = {"events": int(m.sum())}
                    continue
                s = pd.Series(y[m]).groupby(tt[m]).mean()                       # 日ごとの平均にしてから、日をまたいで平均
                d = np.zeros(len(P.dates))
                active = np.zeros(len(P.dates), dtype=bool)
                d[s.index.to_numpy()] = s.to_numpy()
                active[s.index.to_numpy()] = True
                stt = rules.spread_stats(d, active, h)
                rows[label] = {"events": int(m.sum()), "days": stt["days"], "mean_excess": round(stt["mean"], 5) if np.isfinite(stt["mean"]) else None,
                               "t": round(stt["t"], 2) if np.isfinite(stt["t"]) else None, "event_weighted_mean": round(float(y[m].mean()), 5)}
            res[h] = rows
        out[gname] = res
    return out


def v5_overnight_intraday(P, ok, b) -> dict:
    with np.errstate(divide="ignore", invalid="ignore"):
        on = np.full(P.adj_close.shape, np.nan)
        on[1:] = P.adj_open[1:] / P.adj_close[:-1] - 1
        intr = P.adj_close / P.adj_open - 1
    okp = np.zeros_like(ok)
    okp[1:] = ok[:-1]                                                       # 前日に対象だった銘柄
    on, intr = np.where(okp, on, np.nan), np.where(okp, intr, np.nan)
    sl = slice(0, b)
    yrs = P.dates.year.to_numpy()[sl]
    with np.errstate(invalid="ignore"):
        on_d, in_d = np.nanmean(on[sl], axis=1), np.nanmean(intr[sl], axis=1)
    out = {"universe_by_year(mean_per_day)": {}, "after_5day_winners_losers": {}}
    for y in sorted(set(yrs)):
        m = (yrs == y) & np.isfinite(on_d)
        if m.sum() > 50:
            out["universe_by_year(mean_per_day)"][int(y)] = {"overnight": round(float(on_d[m].mean()), 5), "intraday": round(float(in_d[m].mean()), 5)}
    out["universe_all"] = {"overnight": mean_t(on_d), "intraday": mean_t(in_d)}
    tp = P.topix
    t_on = (tp["open"] / tp["close"].shift(1) - 1).to_numpy()[sl]
    t_in = (tp["close"] / tp["open"] - 1).to_numpy()[sl]
    out["topix_all"] = {"overnight": mean_t(t_on), "intraday": mean_t(t_in)}
    c = pd.DataFrame(P.adj_close)
    ret5 = (c / c.shift(5) - 1).to_numpy()
    win_on, win_in, los_on, los_in = [], [], [], []
    for t in range(260, b - 1):
        x = np.where(ok[t], ret5[t], np.nan)
        m = np.isfinite(x)
        if m.sum() < 50:
            continue
        q20, q80 = np.percentile(x[m], [20, 80])
        w, lo = m & (x >= q80), m & (x <= q20)
        base_on, base_in = np.nanmean(on[t + 1][m]), np.nanmean(intr[t + 1][m])
        win_on.append(np.nanmean(on[t + 1][w]) - base_on)
        win_in.append(np.nanmean(intr[t + 1][w]) - base_in)
        los_on.append(np.nanmean(on[t + 1][lo]) - base_on)
        los_in.append(np.nanmean(intr[t + 1][lo]) - base_in)
    out["after_5day_winners_losers"] = {"winners_next_overnight": mean_t(win_on), "winners_next_intraday": mean_t(win_in),
                                        "losers_next_overnight": mean_t(los_on), "losers_next_intraday": mean_t(los_in)}
    return out


def v6_calendar(P, ok, b) -> dict:
    c = P.adj_close
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.full(c.shape, np.nan)
        r[1:] = c[1:] / c[:-1] - 1
    okp = np.zeros_like(ok)
    okp[1:] = ok[:-1]
    with np.errstate(invalid="ignore"):
        d = np.nanmean(np.where(okp, r, np.nan), axis=1)[:b]
    dates = P.dates[:b]
    out = {"weekday": {}, "turn_of_month": {}}
    names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    for w in range(5):
        out["weekday"][names[w]] = mean_t(d[dates.day_of_week == w])
    ym = dates.year * 100 + dates.month
    pos_from_start = pd.Series(np.arange(len(dates))).groupby(ym.to_numpy()).cumcount().to_numpy()
    pos_from_end = pd.Series(np.arange(len(dates))).groupby(ym.to_numpy()).cumcount(ascending=False).to_numpy()
    tom = (pos_from_end == 0) | (pos_from_start <= 2)
    out["turn_of_month"] = {"last_day_and_first_3_days": mean_t(d[tom]), "other_days": mean_t(d[~tom])}
    return out


def v7_sectors(root: Path, P, b) -> dict:
    f = root / "processed" / "indices_daily.parquet"
    if not f.exists():
        return {"note": "指数日足がない"}
    ix = pd.read_parquet(f)
    ix = ix[(ix["index_code"] >= "0040") & (ix["index_code"] <= "0060")]
    if ix["index_code"].nunique() < 20:
        return {"note": f"業種指数が見つからない（{ix['index_code'].nunique()} 本）"}
    w = ix.pivot(index="date", columns="index_code", values="close").reindex(P.dates)
    mom = (w / w.shift(21) - 1).to_numpy()
    fwd = (w.shift(-22) / w.shift(-1) - 1).to_numpy()                       # 翌営業日終値 → 21 営業日後
    ics, spread = [], []
    for T in range(21, b - 24, 21):
        x, y = mom[T], fwd[T]
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 20:
            continue
        ics.append(evalsel.rank_ic(x, y, m) if m.sum() >= 20 else np.nan)
        o = np.argsort(x[m])
        yy = y[m][o]
        spread.append(yy[-5:].mean() - yy[:5].mean())
    return {"sectors": int(w.shape[1]), "momentum21_ic": mean_t(ics), "top5_minus_bottom5_next21": mean_t(spread)}


def main(root: Path, write=True) -> dict:
    warnings.filterwarnings("ignore", message="Mean of empty slice")           # 対象銘柄のない日の平均（NaN になるだけ）
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    b = boundary(P)
    elig = P.eligible_daily(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL)
    ok = elig & rules.executable(P)
    ok[b:] = False                                                          # 確認期間には触れない
    mf = root / "processed" / "margin_interest.parquet"
    mg = pd.read_parquet(mf) if mf.exists() else None
    if mg is not None and (mg.empty or "usable_from" not in mg.columns):
        mg = None
    t_idx = [T for T in P.rebalance_idx() if T < b]
    feats = feature_matrix(P, fins, mg, t_idx)
    out = {"scope": "発見期間のみ（点灯日 < 2022-04-04、保有の終わりが境界を越えない日まで）。検定ではなく記述。",
           "rebalance_dates_used": len([T for T in t_idx if ok[T].any()]), "eligible_median": int(np.median(ok.sum(axis=1)[ok.any(axis=1)])) if ok.any() else 0}
    out.update(v1_v2_v3(P, ok, feats, t_idx, b))
    out["earnings_reaction"] = v4_earnings_reaction(P, ok, fins, b)
    out["overnight_intraday"] = v5_overnight_intraday(P, ok, b)
    out["calendar"] = v6_calendar(P, ok, b)
    out["sector_momentum"] = v7_sectors(root, P, b)
    if write:
        d = root / "results" / "explore"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
