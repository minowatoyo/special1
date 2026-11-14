"""季節性（毎年同じ時期の上げ下げ）の検証。仕様は docs/w5_protocol.md「季節性と、広い母集団」。

S1 同じ月の持続／S2 配当の権利取り／S3 決算発表前の上昇。すべて、判断の時点までの情報だけを使う。
銘柄ごとの値は返さない（月ごと・日ごとの集計の系列だけ）。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from forecastlib import stats as st

from . import evalsel, rules

TIER_EDGES = (5e8, 5e7)                      # A ≥ 5 億、B 5,000 万〜5 億、C それ未満（下限は母集団の条件）
TIER_COST = {"A": 0.0015, "B": 0.0030, "C": 0.0060}   # 片道
T2_START = pd.Timestamp("2019-07-16")        # 受け渡しが 2 営業日後になった日
MIN_YEARS = 3
MIN_GROUP = 30
RUN_DAYS_S2 = 40
RUN_DAYS_S3 = 10


def tiers(va60_row: np.ndarray) -> np.ndarray:
    """流動性の段階: 0=A、1=B、2=C。"""
    return np.where(va60_row >= TIER_EDGES[0], 0, np.where(va60_row >= TIER_EDGES[1], 1, 2))


def months(P) -> dict:
    """月ごとの、最初と最後の営業日の位置、暦月。"""
    per = P.dates.to_period("M")
    s = pd.Series(np.arange(len(P.dates)), index=per)
    first, last = s.groupby(level=0).first(), s.groupby(level=0).last()
    return {"first": first.to_numpy(), "last": last.to_numpy(), "cal": np.array([p.month for p in first.index]), "period": first.index}


def window_excess(P, elig_row: np.ndarray, e: int, x: int) -> np.ndarray:
    """始値 e → 始値 x のリターン − その時点の対象銘柄の平均（対象外は NaN）。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        r = P.adj_open[x] / P.adj_open[e] - 1.0
    r = np.where(elig_row, r, np.nan)
    m = np.isfinite(r)
    return r - r[m].mean() if m.sum() >= 20 else np.full_like(r, np.nan)


def tstat(x, lags: int = 0) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 8:
        return {"n": int(n), "mean": float(x.mean()) if n else float("nan"), "t": float("nan"), "p": float("nan")}
    se = math.sqrt(st.hac_variance(x, lags)) if lags > 0 else x.std(ddof=1) / math.sqrt(n)
    if not se > 0:
        return {"n": int(n), "mean": float(x.mean()), "t": float("nan"), "p": float("nan")}
    t = float(x.mean() / se)
    return {"n": int(n), "mean": float(x.mean()), "t": t, "p": float(2 * st.t_sf(abs(t), n - 1))}


def _period(entry: int, exit_: int, b: int) -> str:
    return "discovery" if exit_ < b else ("confirmation" if entry >= b else "straddle")


# ---------------------------------------------------------------- S1
def s1_same_month(P, elig: np.ndarray, va60: np.ndarray, b: int) -> dict:
    mo = months(P)
    first, last, cal = mo["first"], mo["last"], mo["cal"]
    M = len(first)
    n_j = P.adj_close.shape[1]
    R = np.full((M, n_j), np.nan)                               # 月 m の超過（月初の始値 → 翌月初の始値）
    for m in range(1, M - 1):
        R[m] = window_excess(P, elig[last[m - 1]], first[m], first[m + 1])
    rows = []
    for m in range(1, M - 1):
        prev = [k for k in range(1, m) if cal[k] == cal[m]]
        if len(prev) < MIN_YEARS:
            continue
        hist = R[prev]
        cnt = np.isfinite(hist).sum(axis=0)
        with np.errstate(invalid="ignore"):
            sig = np.where(cnt >= MIN_YEARS, np.nanmean(hist, axis=0), np.nan)
        y = R[m]
        ok = np.isfinite(sig) & np.isfinite(y)
        if ok.sum() < 100:
            continue
        q80 = np.percentile(sig[ok], 80)
        top = ok & (sig >= q80)
        tr = tiers(va60[last[m - 1]])
        row = {"period": _period(first[m], first[m + 1], b), "ic": evalsel.rank_ic(sig, y, ok), "top": float(y[top].mean()), "n": int(ok.sum()),
               "years": len(prev)}
        for k, nm in enumerate("ABC"):
            tt = top & (tr == k)
            row[f"top_{nm}"] = float(y[tt].mean()) if tt.sum() >= 5 else np.nan
        rows.append(row)
    return {"rows": rows}


# ---------------------------------------------------------------- S2
def fins_asof(P, fins: pd.DataFrame, s_idx: list) -> dict:
    """各判断日 s に使える、銘柄ごとの最新の開示（決算期末の月、年間配当の見込み、開示日の調整比）。"""
    cols = ["Code", "usable_from", "CurFYEn", "FDivAnn", "NxFDivAnn", "DivAnn"]
    f = fins[[c for c in cols if c in fins.columns]].dropna(subset=["usable_from"]).copy()
    for c in ("FDivAnn", "NxFDivAnn", "DivAnn"):
        f[c] = pd.to_numeric(f[c], errors="coerce") if c in f.columns else np.nan
    f["div"] = f["FDivAnn"].where(f["FDivAnn"].notna(), f["NxFDivAnn"]).where(lambda s: s.notna(), f["DivAnn"])
    f["fy_month"] = pd.to_datetime(f["CurFYEn"], errors="coerce").dt.month
    ci = {c: i for i, c in enumerate(P.codes)}
    f["col"] = f["Code"].map(ci)
    f = f.dropna(subset=["col", "fy_month"]).astype({"col": int}).sort_values("usable_from")
    pos = np.searchsorted(P.dates.values, f["usable_from"].to_numpy(), side="left")
    pos = np.minimum(pos, len(P.dates) - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        f["r_disc"] = P.adj_close[pos, f["col"].to_numpy()] / P.raw_close[pos, f["col"].to_numpy()]
    n_j = len(P.codes)
    td = pd.DataFrame({"T": np.repeat(P.dates[s_idx].values, n_j), "col": np.tile(np.arange(n_j), len(s_idx)), "si": np.repeat(np.arange(len(s_idx)), n_j)})
    m = pd.merge_asof(td.sort_values("T"), f[["col", "usable_from", "div", "fy_month", "r_disc"]], left_on="T", right_on="usable_from", by="col", direction="backward")
    out = {k: np.full((len(s_idx), n_j), np.nan) for k in ("div", "fy_month", "r_disc")}
    for k in out:
        out[k][m["si"].to_numpy(), m["col"].to_numpy()] = m[k].to_numpy(dtype=float)
    return out


def s2_dividend_runup(P, elig: np.ndarray, va60: np.ndarray, fins: pd.DataFrame, b: int) -> dict:
    mo = months(P)
    last, cal = mo["last"], mo["cal"]
    events = []
    for m in range(len(last)):
        lag = 2 if P.dates[last[m]] >= T2_START else 3
        L = last[m] - lag                                      # 権利付き最終日
        e = L - RUN_DAYS_S2
        if e - 1 < 0:
            continue
        events.append((m, e - 1, e, L))
    fa = fins_asof(P, fins, [s for _, s, _, _ in events])
    rows = []
    for i, (m, s, e, L) in enumerate(events):
        month = cal[m]
        fy = fa["fy_month"][i]
        rights = (fy == month) | (((fy + 5) % 12) + 1 == month)        # 決算期末の月と、その 6 か月後
        with np.errstate(divide="ignore", invalid="ignore"):
            yld = fa["div"][i] * fa["r_disc"][i] / P.adj_close[s]
        y = window_excess(P, elig[s], e, L)
        g = rights & np.isfinite(yld) & (yld > 0) & np.isfinite(y)
        if g.sum() < MIN_GROUP:
            continue
        q80 = np.percentile(yld[g], 80)
        top = g & (yld >= q80)
        tr = tiers(va60[s])
        row = {"period": _period(e, L, b), "top": float(y[top].mean()), "ic": evalsel.rank_ic(yld, y, g), "group": int(g.sum()),
               "rights_all": float(y[g].mean()), "month": int(month)}
        for k, nm in enumerate("ABC"):
            tt = top & (tr == k)
            row[f"top_{nm}"] = float(y[tt].mean()) if tt.sum() >= 5 else np.nan
        rows.append(row)
    return {"rows": rows}


# ---------------------------------------------------------------- S3
def s3_pre_earnings(P, elig: np.ndarray, va60: np.ndarray, fins: pd.DataFrame, b: int) -> dict:
    f = fins[["Code", "DiscDate"] + (["DocType"] if "DocType" in fins.columns else [])].dropna(subset=["DiscDate"]).copy()
    if "DocType" in f.columns:
        f = f[f["DocType"].astype(str).str.contains("FinancialStatements")]
    ci = {c: i for i, c in enumerate(P.codes)}
    f["col"] = f["Code"].map(ci)
    f = f.dropna(subset=["col"]).astype({"col": int}).drop_duplicates(["col", "DiscDate"])
    pred = pd.to_datetime(f["DiscDate"]) + pd.DateOffset(years=1)          # 前年の開示日の 1 年後を、予想発表日とする
    p = np.searchsorted(P.dates.values, pred.to_numpy(), side="left")
    n_t = len(P.dates)
    keep = (p < n_t) & (p - RUN_DAYS_S3 - 1 >= 0)
    p, col = p[keep], f["col"].to_numpy()[keep]
    e = p - RUN_DAYS_S3
    d_sum, d_cnt = np.zeros(n_t), np.zeros(n_t)
    tier_sum, tier_cnt = np.zeros((3, n_t)), np.zeros((3, n_t))
    for ee in np.unique(e):
        x = ee + RUN_DAYS_S3
        y = window_excess(P, elig[ee - 1], ee, x)
        cols = col[e == ee]
        v = y[cols]
        okv = np.isfinite(v)
        if okv.sum() == 0:
            continue
        d_sum[ee], d_cnt[ee] = v[okv].sum(), okv.sum()
        tr = tiers(va60[ee - 1])[cols]
        for k in range(3):
            mm = okv & (tr == k)
            tier_sum[k, ee], tier_cnt[k, ee] = v[mm].sum(), mm.sum()
    return {"d_sum": d_sum, "d_cnt": d_cnt, "tier_sum": tier_sum, "tier_cnt": tier_cnt}


def s3_stats(acc: dict, dates, b: int, which: str, h: int = RUN_DAYS_S3, min_entries: int = 3) -> dict:
    t = np.arange(len(dates))
    pm = (t + h < b) if which == "discovery" else (t >= b)
    active = pm & (acc["d_cnt"] >= min_entries)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = np.nan_to_num(acc["d_sum"] / acc["d_cnt"])
    s = rules.spread_stats(d, active, h)
    s["entries"] = int(acc["d_cnt"][active].sum())
    tr = {}
    for k, nm in enumerate("ABC"):
        a = pm & (acc["tier_cnt"][k] >= 1)
        tr[nm] = float(acc["tier_sum"][k][a].sum() / acc["tier_cnt"][k][a].sum()) if a.any() else float("nan")
    s["by_tier_event_weighted"] = tr
    return s
