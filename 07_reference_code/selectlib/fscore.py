"""財務の強さ F（Piotroski の F スコアの近似）、財務危機、簿価利回り、開示の有無。仕様は docs/w5_protocol.md「期待と実態の不一致…」。
日 t の引け後に使える開示（usable_from ≤ t）だけを使う。出力は集計のみ。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import seasonal

ALIASES = {"sales": ("Sales", "NetSales"), "op": ("OP", "OperatingProfit"), "np": ("NP", "Profit"), "ta": ("TA", "TotalAssets"), "eq": ("Eq", "Equity"),
           "eqar": ("EqAR", "EquityToAssetRatio"), "cfo": ("CFO", "CashFlowsFromOperatingActivities"), "shout": ("ShOutFY", "ShOut"), "trsh": ("TrShFY", "TrSh"),
           "bps": ("BPS", "BookValuePerShare")}
SIGNALS = ("roa_pos", "cfo_pos", "roa_up", "cfo_gt_np", "equity_ratio_up", "no_issuance", "margin_up", "turnover_up")
F_HIGH, F_LOW, MIN_SIGNALS = 0.7, 0.4, 6
FY_VALID_DAYS, BPS_VALID_DAYS, NEWS_WINDOW = 400, 200, 6
DISTRESS_EQ = 0.20


def _col(f: pd.DataFrame, key: str) -> str | None:
    for n in ALIASES[key]:
        if n in f.columns:
            return n
    return None


def availability(fins: pd.DataFrame) -> dict:
    return {k: _col(fins, k) is not None for k in ALIASES}


def _num(f: pd.DataFrame, key: str) -> pd.Series:
    c = _col(f, key)
    return pd.to_numeric(f[c], errors="coerce") if c else pd.Series(np.nan, index=f.index)


def _place(P, f: pd.DataFrame) -> pd.DataFrame:
    """銘柄の列番号 j と、利用可能日の位置 t を付ける（範囲外は落とす）。"""
    ci = {c: i for i, c in enumerate(P.codes)}
    f = f.copy()
    f["j"] = f["Code"].astype(str).map(ci)
    t = np.searchsorted(P.dates.values, f["usable_from"].to_numpy(), side="left")
    f["t"] = t
    return f[f["j"].notna() & (f["t"] < len(P.dates))].astype({"j": int})


def annual_table(P, fins: pd.DataFrame) -> pd.DataFrame:
    """通期決算ごとの、F の 8 項目・F・財務危機。前期は、同じ銘柄の 330〜400 日前の通期決算。"""
    need = ["Code", "usable_from", "CurFYEn", "CurPerType"]
    if any(c not in fins.columns for c in need):
        return pd.DataFrame()
    f = fins[fins["CurPerType"].astype(str) == "FY"].dropna(subset=["usable_from"]).copy()
    f["fy"] = pd.to_datetime(f["CurFYEn"], errors="coerce")
    f = f.dropna(subset=["fy"]).sort_values(["Code", "usable_from"], kind="stable").drop_duplicates(["Code", "CurFYEn"], keep="first")
    f = _place(P, f)
    if f.empty:
        return f
    d = pd.DataFrame({"Code": f["Code"].astype(str), "usable_from": f["usable_from"], "fy": f["fy"], "j": f["j"], "t": f["t"]})
    for k in ("sales", "op", "np", "ta", "eq", "eqar", "cfo", "shout", "trsh"):
        d[k] = _num(f, k).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        q = P.adj_close[d["t"].to_numpy(), d["j"].to_numpy()] / P.raw_close[d["t"].to_numpy(), d["j"].to_numpy()]
    d["net_sh"] = (d["shout"] - d["trsh"].fillna(0.0)) / q                       # 現在の株数の単位にそろえる
    ta = d["ta"].where(d["ta"] > 0)
    d["roa"] = d["np"] / ta
    eqr = d["eq"] / ta
    alt = d["eqar"].where(d["eqar"] <= 1.0, d["eqar"] / 100.0)                   # ％で入っている場合に備える
    d["eqr"] = eqr.where(eqr.notna(), alt)
    d["margin"] = d["op"] / d["sales"].where(d["sales"] > 0)
    d["turn"] = d["sales"] / ta
    d = d.sort_values(["Code", "fy"], kind="stable")
    g = d.groupby("Code", sort=False)
    gap = (d["fy"] - g["fy"].shift()).dt.days
    prev_ok = gap.between(330, 400)
    def prev(c):
        return g[c].shift().where(prev_ok)
    def flag(cond, *inputs):
        ok = np.ones(len(d), dtype=bool)
        for x in inputs:
            ok &= np.isfinite(np.asarray(x, dtype=float))
        return np.where(ok, np.asarray(cond, dtype=float), np.nan)
    S = {"roa_pos": flag(d["roa"] > 0, d["roa"]), "cfo_pos": flag(d["cfo"] > 0, d["cfo"]),
         "roa_up": flag(d["roa"] > prev("roa"), d["roa"], prev("roa")), "cfo_gt_np": flag(d["cfo"] > d["np"], d["cfo"], d["np"]),
         "equity_ratio_up": flag(d["eqr"] > prev("eqr"), d["eqr"], prev("eqr")),
         "no_issuance": flag(d["net_sh"] <= prev("net_sh") * 1.01, d["net_sh"], prev("net_sh")),
         "margin_up": flag(d["margin"] > prev("margin"), d["margin"], prev("margin")),
         "turnover_up": flag(d["turn"] > prev("turn"), d["turn"], prev("turn"))}
    M = np.column_stack([S[k] for k in SIGNALS])
    n_av = np.isfinite(M).sum(axis=1)
    d["n_signals"] = n_av
    d["F"] = np.where(n_av >= MIN_SIGNALS, np.nansum(M, axis=1) / np.maximum(n_av, 1), np.nan)
    for k in SIGNALS:
        d[k] = S[k]
    bad = np.column_stack([flag(d["np"] < 0, d["np"]), flag(d["cfo"] < 0, d["cfo"]), flag(d["eqr"] < DISTRESS_EQ, d["eqr"])])
    d["distress"] = np.where(np.isfinite(bad).sum(axis=1) >= 2, (np.nansum(bad, axis=1) >= 2).astype(float), np.nan)
    return d


def to_daily(P, tbl: pd.DataFrame, cols: list, valid_days: int) -> dict:
    """開示ごとの値 → 日付の行列 [日, 銘柄]。各日に、利用可能日 ≤ 当日の最新の開示の値。valid_days 暦日より古いものは NaN。"""
    T, N = len(P.dates), len(P.codes)
    out = {c: np.full((T, N), np.nan) for c in cols}
    if tbl is None or len(tbl) == 0:
        return out
    dates = P.dates.values
    ar = np.arange(T)
    for j, g in tbl.sort_values("t", kind="stable").groupby("j", sort=False):
        tt = g["t"].to_numpy()
        idx = np.searchsorted(tt, ar, side="right") - 1
        ok = idx >= 0
        safe = np.where(ok, idx, 0)
        age = (dates - dates[tt[safe]]).astype("timedelta64[D]").astype(int)
        ok &= age <= valid_days
        for c in cols:
            out[c][:, int(j)] = np.where(ok, g[c].to_numpy(dtype=float)[safe], np.nan)
    return out


def daily(P, fins: pd.DataFrame) -> dict:
    """F・財務危機・簿価利回り・開示の有無の行列 [日, 銘柄] と、項目の利用可否。"""
    T, N = len(P.dates), len(P.codes)
    at = annual_table(P, fins)
    d = to_daily(P, at, ["F", "distress", "n_signals"], FY_VALID_DAYS)
    res = {"F": d["F"], "distress": d["distress"], "availability": availability(fins),
           "signals_available_share": {k: float(np.isfinite(at[k]).mean()) for k in SIGNALS} if len(at) else {}}
    # 簿価利回り（全ての開示の BPS。分割は、開示日の調整比で調整）
    by = np.full((T, N), np.nan)
    news = np.zeros((T, N), dtype=bool)
    if "usable_from" in fins.columns and "Code" in fins.columns:
        f = _place(P, fins.dropna(subset=["usable_from"]))
        if len(f):
            news[f["t"].to_numpy(), f["j"].to_numpy()] = True
            news = pd.DataFrame(news.astype(float)).rolling(NEWS_WINDOW, min_periods=1).max().to_numpy() > 0.5
            b = pd.DataFrame({"j": f["j"].to_numpy(), "t": f["t"].to_numpy(), "bps": _num(f, "bps").to_numpy()}).dropna(subset=["bps"])
            if len(b):
                with np.errstate(divide="ignore", invalid="ignore"):
                    b["bps_adj"] = b["bps"] * P.adj_close[b["t"].to_numpy(), b["j"].to_numpy()] / P.raw_close[b["t"].to_numpy(), b["j"].to_numpy()]
                bd = to_daily(P, b.dropna(subset=["bps_adj"]), ["bps_adj"], BPS_VALID_DAYS)["bps_adj"]
                with np.errstate(divide="ignore", invalid="ignore"):
                    by = np.where(P.adj_close > 0, bd / P.adj_close, np.nan)
    res["book_yield"], res["news"] = by, news
    return res


def xsec(dates, A: np.ndarray, B: np.ndarray | None, ex: np.ndarray, grid: list, h: int, lo: int, hi: int, min_n: int = 10) -> dict:
    """判断日ごとの、A の平均超過 −（B の平均超過。B が None なら 0）→ 系列の平均・t 値（Newey–West）。"""
    vals, na, nb = [], [], []
    for t in grid:
        if t < lo or t > hi:
            continue
        a = A[t] & np.isfinite(ex[t])
        if a.sum() < min_n:
            continue
        v = float(ex[t][a].mean())
        if B is not None:
            b = B[t] & np.isfinite(ex[t])
            if b.sum() < min_n:
                continue
            v -= float(ex[t][b].mean())
            nb.append(int(b.sum()))
        vals.append(v)
        na.append(int(a.sum()))
    out = {"dates": len(vals), "mean": None, "t": None, "p": None, "stocks_per_date_A": float(np.mean(na)) if na else None,
           "stocks_per_date_B": float(np.mean(nb)) if nb else None}
    if len(vals) >= 12:
        st_ = seasonal.tstat(np.array(vals), lags=math.ceil(h / 21))
        out.update({"mean": st_["mean"], "t": st_["t"] if np.isfinite(st_["t"]) else None, "p": st_["p"] if np.isfinite(st_["p"]) else None})
    elif vals:
        out["mean"] = float(np.mean(vals))
    return out
