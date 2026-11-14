"""型破りの探索: 強制的な売買（市場の昇格、貸借銘柄の選定、株式分割、ストップ高・安、権利落ち後）と、会社の癖（進捗率、自社株買い）。
仕様は docs/w5_protocol.md「型破りの探索」。出来事は、日 t の引け後に分かるものだけ。出力は集計のみ。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import rules, s2port, seasonal

REORG = pd.Timestamp("2022-04-04")
MAIN_OLD, MAIN_NEW = "0101", "0111"
FROM_OLD, FROM_NEW = ("0102", "0104", "0106", "0107"), ("0112", "0113")
LOAN_CLASS = "2"                                 # 貸借銘柄
SPLIT_MIN = 1.5
PROGRESS_GAP = 0.10
BUYBACK_MIN = -0.02
MIN_MONTHS = 12

TESTS = [("E1_market_upgrade", 5, +1), ("E1_market_upgrade", 21, +1), ("E2_loan_designation", 5, +1), ("E2_loan_designation", 21, +1),
         ("E3_split_ex_date", 21, +1), ("E3_split_ex_date", 63, +1), ("E4a_limit_up_close", 5, -1), ("E4b_limit_down_close", 5, +1),
         ("E5_post_ex_rebound", 21, +1), ("E6a_ahead_no_raise", 63, +1), ("E6b_behind_no_cut", 63, -1), ("E7_buyback", 63, +1)]


def _pos(P, dates) -> np.ndarray:
    """日付 → その日（営業日でなければ次の営業日）の位置。範囲外は -1。"""
    p = np.searchsorted(P.dates.values, pd.DatetimeIndex(dates).values, side="left")
    return np.where(p < len(P.dates), p, -1)


def _changes(P, iv: pd.DataFrame, col: str) -> pd.DataFrame:
    """上場銘柄表の区間から、属性 col が変わった日（新しい区間の最初の日）。直前の区間が 7 暦日以内に終わっているものだけ。"""
    d = iv[["code", col, "valid_from", "valid_to"]].sort_values(["code", "valid_from"]).copy()
    d["prev"] = d.groupby("code")[col].shift()
    d["prev_to"] = d.groupby("code")["valid_to"].shift()
    d = d[d["prev"].notna() & (d["prev"].astype(str) != d[col].astype(str)) & ((d["valid_from"] - d["prev_to"]).dt.days <= 7)]
    ci = {c: i for i, c in enumerate(P.codes)}
    d["j"] = d["code"].map(ci)
    d = d.dropna(subset=["j"]).astype({"j": int})
    d["t"] = _pos(P, d["valid_from"])
    return d[d["t"] >= 0]


def market_upgrades(P, iv: pd.DataFrame) -> tuple:
    d = _changes(P, iv, "market")
    new, prev = d["market"].astype(str), d["prev"].astype(str)
    ok = ((new == MAIN_OLD) & prev.isin(FROM_OLD)) | ((new == MAIN_NEW) & prev.isin(FROM_NEW))
    ok &= d["valid_from"] != REORG
    return d["t"].to_numpy()[ok.to_numpy()], d["j"].to_numpy()[ok.to_numpy()]


def loan_designations(P, iv: pd.DataFrame) -> tuple:
    if "margin_class" not in iv.columns:
        return np.array([], int), np.array([], int)
    d = _changes(P, iv, "margin_class")
    ok = (d["margin_class"].astype(str) == LOAN_CLASS).to_numpy()
    return d["t"].to_numpy()[ok], d["j"].to_numpy()[ok]


def splits(P) -> tuple:
    """調整係数（調整後終値 ÷ 未調整終値）が、前の営業日の SPLIT_MIN 倍以上になった日 ＝ 分割の権利落ち日。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        q = P.adj_close / P.raw_close
        r = np.full(q.shape, np.nan)
        r[1:] = q[1:] / q[:-1]
    t, j = np.nonzero(np.isfinite(r) & (r >= SPLIT_MIN))
    return t, j


def limit_closes(P) -> tuple:
    """(ストップ高で引けた, ストップ安で引けた) の位置。終値が、その日の高値（安値）に一致。"""
    up = P.limit_up & np.isfinite(P.adj_close) & (P.adj_close >= P.adj_high * (1 - 1e-9))
    dn = P.limit_down & np.isfinite(P.adj_close) & (P.adj_close <= P.adj_low * (1 + 1e-9))
    return np.nonzero(up), np.nonzero(dn)


def post_ex(P, elig: np.ndarray, va60: np.ndarray, fins: pd.DataFrame, wait: int = 10) -> tuple:
    """権利月の銘柄の予想配当利回り上位 1/5 を、権利付き最終日 L の wait 営業日後の始値で買う（t = L + wait − 1）。"""
    ts, js = [], []
    for c in s2port.candidates(P, elig, va60, fins):
        t = c["L"] + wait - 1
        if t >= len(P.dates):
            continue
        rank = c["yld"].argsort().argsort() / len(c["yld"])
        cols = c["cols"][rank >= 0.8]
        ts.append(np.full(len(cols), t))
        js.append(cols)
    return (np.concatenate(ts), np.concatenate(js)) if ts else (np.array([], int), np.array([], int))


def _col(f: pd.DataFrame, names) -> str | None:
    for n in names:
        if n in f.columns:
            return n
    return None


def progress_events(P, fins: pd.DataFrame) -> dict:
    """E6: 進捗（累計営業利益 ÷ 通期予想）が、その会社の過去の同じ四半期の進捗（累計 ÷ 通期実績）の平均より ±10 ポイント。"""
    op = _col(fins, ("OP", "OperatingProfit"))
    need = ["Code", "usable_from", "CurFYEn", "CurPerType", "FOP"]
    if op is None or any(c not in fins.columns for c in need):
        return {"missing": "営業利益の実績（OP）または CurPerType・FOP の列がない"}
    f = fins[need + [op]].dropna(subset=["usable_from"]).copy()
    f["op"], f["fop"] = pd.to_numeric(f[op], errors="coerce"), pd.to_numeric(f["FOP"], errors="coerce")
    f["q"] = f["CurPerType"].astype(str)
    f = f.sort_values(["Code", "usable_from"], kind="stable")
    f["prev_fop"] = f.groupby(["Code", "CurFYEn"], sort=False)["fop"].shift()          # 同じ決算期の、前回の通期予想
    f = f.drop_duplicates(["Code", "CurFYEn", "q"], keep="first")                       # 各四半期の、最初の開示
    fy = f[f["q"] == "FY"][["Code", "CurFYEn", "op", "usable_from"]].rename(columns={"op": "fy_op", "usable_from": "fy_usable"})
    qs = f[f["q"].isin(["1Q", "2Q", "3Q"])].merge(fy, on=["Code", "CurFYEn"], how="left")
    qs["hist"] = np.where((qs["fy_op"] > 0) & qs["op"].notna(), qs["op"] / qs["fy_op"], np.nan)
    qs = qs.sort_values(["Code", "q", "usable_from"], kind="stable")
    g = qs.groupby(["Code", "q"], sort=False)["hist"]
    qs["norm"] = g.transform(lambda s: s.shift().expanding(min_periods=2).mean())        # 過去の年だけ（2 年以上）
    qs["prev_fy_usable"] = qs.groupby(["Code", "q"], sort=False)["fy_usable"].shift()
    known = qs["prev_fy_usable"].notna() & (qs["prev_fy_usable"] <= qs["usable_from"])   # 直近の過去の通期実績が、すでに開示済み
    qs["prog"] = np.where(qs["fop"] > 0, qs["op"] / qs["fop"], np.nan)
    gap = qs["prog"] - qs["norm"]
    raised = qs["prev_fop"].notna() & (qs["fop"] > qs["prev_fop"] * 1.0001)
    cut = qs["prev_fop"].notna() & (qs["fop"] < qs["prev_fop"] * 0.9999)
    ci = {c: i for i, c in enumerate(P.codes)}
    qs["j"] = qs["Code"].map(ci)
    qs["t"] = _pos(P, qs["usable_from"])
    base = known & qs["j"].notna() & (qs["t"] >= 0) & np.isfinite(gap) & (qs["op"] > 0)
    a = (base & (gap >= PROGRESS_GAP) & ~raised).to_numpy()
    bq = (base & (gap <= -PROGRESS_GAP) & ~cut).to_numpy()
    tt, jj = qs["t"].to_numpy(), qs["j"].fillna(-1).to_numpy(dtype=int)
    return {"ahead": (tt[a], jj[a]), "behind": (tt[bq], jj[bq])}


def buyback_events(P, fins: pd.DataFrame) -> dict:
    """E7: （発行済株式数 − 自己株式数）が、1 年前の同じ四半期より 2% 以上減った（分割・併合は調整係数で調整）。"""
    so, tr = _col(fins, ("ShOutFY", "ShOut", "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock")), _col(fins, ("TrShFY", "TrSh", "NumberOfTreasuryStockAtTheEndOfFiscalYear"))
    if so is None or tr is None or "CurPerType" not in fins.columns:
        return {"missing": "株式数（発行済・自己株式）の列がない"}
    f = fins[["Code", "usable_from", "CurFYEn", "CurPerType", so, tr]].dropna(subset=["usable_from"]).copy()
    f["net"] = pd.to_numeric(f[so], errors="coerce") - pd.to_numeric(f[tr], errors="coerce").fillna(0.0)
    ci = {c: i for i, c in enumerate(P.codes)}
    f["j"] = f["Code"].map(ci)
    f["t"] = _pos(P, f["usable_from"])
    f = f[f["j"].notna() & (f["t"] >= 0) & (f["net"] > 0)].astype({"j": int})
    with np.errstate(divide="ignore", invalid="ignore"):
        q = (P.adj_close / P.raw_close)[f["t"].to_numpy(), f["j"].to_numpy()]
    f["net_adj"] = f["net"] / q                                                          # 現在の株数の単位にそろえる
    f = f.sort_values(["Code", "usable_from"], kind="stable").drop_duplicates(["Code", "CurFYEn", "CurPerType"], keep="first")
    f["fy"] = pd.to_datetime(f["CurFYEn"], errors="coerce")
    f = f.dropna(subset=["fy"]).sort_values(["Code", "CurPerType", "fy"], kind="stable")
    g = f.groupby(["Code", "CurPerType"], sort=False)
    prev, prev_fy = g["net_adj"].shift(), g["fy"].shift()
    yr = ((f["fy"] - prev_fy).dt.days.between(330, 400)).to_numpy()
    chg = (f["net_adj"] / prev - 1).to_numpy()
    m = yr & np.isfinite(chg) & (chg <= BUYBACK_MIN) & (chg > -0.5)
    return {"buyback": (f["t"].to_numpy()[m], f["j"].to_numpy()[m])}


def build(P, iv: pd.DataFrame, fins: pd.DataFrame, elig: np.ndarray, va60: np.ndarray) -> tuple:
    """名前 → (t, j)。データのない出来事は missing に理由を入れる。"""
    ev, missing = {}, {}
    ev["E1_market_upgrade"] = market_upgrades(P, iv)
    ev["E2_loan_designation"] = loan_designations(P, iv)
    ev["E3_split_ex_date"] = splits(P)
    ev["E4a_limit_up_close"], ev["E4b_limit_down_close"] = limit_closes(P)
    ev["E5_post_ex_rebound"] = post_ex(P, elig, va60, fins)
    pe = progress_events(P, fins)
    if "missing" in pe:
        missing["E6a_ahead_no_raise"] = missing["E6b_behind_no_cut"] = pe["missing"]
    else:
        ev["E6a_ahead_no_raise"], ev["E6b_behind_no_cut"] = pe["ahead"], pe["behind"]
    bb = buyback_events(P, fins)
    if "missing" in bb:
        missing["E7_buyback"] = bb["missing"]
    else:
        ev["E7_buyback"] = bb["buyback"]
    return ev, missing


def excess_matrix(P, ok: np.ndarray, h: int) -> np.ndarray:
    F = np.where(ok, rules.forward_returns(P, h), np.nan)
    with np.errstate(invalid="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return F - np.nanmean(F, axis=1, keepdims=True)


def study(P, E: np.ndarray, t: np.ndarray, j: np.ndarray, h: int, lo: int, hi: int) -> dict:
    """出来事（t, j）のうち lo ≤ t ≤ hi のものの超過を、起きた暦月ごとに平均 → 月の系列の平均と t 値（Newey–West）。"""
    t, j = np.asarray(t, dtype=int), np.asarray(j, dtype=int)
    m = (t >= lo) & (t <= hi)
    t, j = t[m], j[m]
    if len(t):
        key = np.unique(t.astype(np.int64) * E.shape[1] + j)
        t, j = (key // E.shape[1]).astype(int), (key % E.shape[1]).astype(int)
    y = E[t, j] if len(t) else np.array([])
    v = np.isfinite(y)
    t, y = t[v], y[v]
    out = {"events": int(len(y)), "months": 0, "mean": None, "t": None, "p": None, "event_weighted_mean": float(y.mean()) if len(y) else None,
           "share_positive_events": float((y > 0).mean()) if len(y) else None}
    if not len(y):
        return out
    ym = P.dates.year[t] * 12 + P.dates.month[t]
    s = pd.Series(y).groupby(np.asarray(ym)).mean()
    out["months"] = int(len(s))
    if len(s) >= MIN_MONTHS:
        st_ = seasonal.tstat(s.to_numpy(), lags=math.ceil(h / 21))
        out.update({"mean": st_["mean"], "t": st_["t"] if np.isfinite(st_["t"]) else None, "p": st_["p"] if np.isfinite(st_["p"]) else None})
    return out
