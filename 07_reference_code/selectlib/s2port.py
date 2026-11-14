"""S2（配当の権利取り）の、口座での売買の模擬。仕様は docs/w5_protocol.md「S2 の実行可能性」。出力は集計のみ。"""
from __future__ import annotations

import math

import numpy as np

from . import portfolio, seasonal

N_MAX = 10
SLEEVE = 0.5
VA_CAP = 0.01
COST = {0: 0.0015, 1: 0.0030, 2: 0.0060}          # 片道（段階 A・B・C）


def candidates(P, elig: np.ndarray, va60: np.ndarray, fins) -> list:
    """月ごとの候補: 判断日 s（= e − 1）、買い e、売り L、権利月の銘柄の列番号・予想配当利回り・流動性の段階。"""
    mo = seasonal.months(P)
    last, cal = mo["last"], mo["cal"]
    ev = []
    for m in range(len(last)):
        L = last[m] - (2 if P.dates[last[m]] >= seasonal.T2_START else 3)
        e = L - seasonal.RUN_DAYS_S2
        if e - 1 < 0 or L >= len(P.dates):
            continue
        ev.append((m, e - 1, e, L))
    fa = seasonal.fins_asof(P, fins, [s for _, s, _, _ in ev])
    out = []
    for i, (m, s, e, L) in enumerate(ev):
        fy = fa["fy_month"][i]
        rights = (fy == cal[m]) | (((fy + 5) % 12) + 1 == cal[m])
        with np.errstate(divide="ignore", invalid="ignore"):
            yld = fa["div"][i] * fa["r_disc"][i] / P.adj_close[s]
        g = np.flatnonzero(rights & elig[s] & np.isfinite(yld) & (yld > 0))
        if len(g) < seasonal.MIN_GROUP:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.where(elig[s], P.adj_open[L] / P.adj_open[e] - 1.0, np.nan)
        out.append({"s": s, "e": e, "L": L, "cols": g, "yld": yld[g], "tier": seasonal.tiers(va60[s])[g], "univ": float(np.nanmean(r)) if np.isfinite(r).sum() >= 20 else float("nan")})
    return out


def simulate(P, cands: list, va60: np.ndarray, tiers_allowed=(1,), n_max: int = N_MAX, initial: float = 10_000_000, lot: int = 100) -> dict:
    """日ごとに、売り → 買い → 引けで評価。戻り値: 日ごとの総資産、窓ごとの記録。"""
    n_days = len(P.dates)
    buys = {c["e"]: c for c in cands}
    cash = float(initial)
    pos = []                                     # {"j", "shares", "buy_px", "adj_buy", "sell_at", "w", "tier"}
    equity = np.full(n_days, np.nan)
    cash_s = np.full(n_days, np.nan)
    wins = []

    def value(p, t, use_open=False):
        a = P.adj_open[t, p["j"]] if use_open else P.adj_close[t, p["j"]]
        if not np.isfinite(a):                   # 売買のない日は、直近の値で評価
            k = t
            while k > 0 and not np.isfinite(P.adj_close[k, p["j"]]):
                k -= 1
            a = P.adj_close[k, p["j"]]
        return p["shares"] * p["buy_px"] * a / p["adj_buy"]

    for t in range(n_days):
        keep = []
        for p in pos:                            # 売り（始値）
            if p["sell_at"] == t:
                gross = value(p, t, use_open=True)
                c = gross * COST[p["tier"]]
                cash += gross - c
                p["w"]["proceeds"] += gross - c
                p["w"]["cost"] += c
                p["w"]["open"] -= 1
            else:
                keep.append(p)
        pos = keep
        c = buys.get(t)
        if c is not None:                        # 買い（始値）
            total = cash + sum(value(p, t, use_open=True) for p in pos)
            sleeve = min(total * SLEEVE, cash)
            budget = sleeve / n_max
            rank = c["yld"].argsort().argsort() / len(c["yld"])
            ok = (rank >= 0.8) & np.isin(c["tier"], tiers_allowed)
            order = np.flatnonzero(ok)[np.argsort(-c["yld"][ok], kind="stable")]
            w = {"e": c["e"], "L": c["L"], "invested": 0.0, "proceeds": 0.0, "cost": 0.0, "n": 0, "skipped": 0, "univ": c["univ"], "candidates": int(ok.sum()), "open": 0}
            for k in order:
                if w["n"] >= n_max:
                    break
                j = int(c["cols"][k])
                px, tier = P.raw_open[t, j], int(c["tier"][k])
                if not np.isfinite(px) or px <= 0 or bool(P.limit_up[t, j]):
                    w["skipped"] += 1
                    continue
                cap = min(budget, VA_CAP * va60[c["s"], j]) if np.isfinite(va60[c["s"], j]) else 0.0
                shares = int(math.floor(cap / (px * lot * (1 + COST[tier])))) * lot
                if shares <= 0:
                    w["skipped"] += 1
                    continue
                notional = shares * px
                fee = notional * COST[tier]
                if notional + fee > cash:
                    w["skipped"] += 1
                    continue
                cash -= notional + fee
                s_at, _, _ = portfolio._sell_index(P.adj_open, P.limit_down, j, c["L"])
                pos.append({"j": j, "shares": shares, "buy_px": px, "adj_buy": P.adj_open[t, j], "sell_at": s_at, "w": w, "tier": tier})
                w["invested"] += notional + fee
                w["cost"] += fee
                w["n"] += 1
                w["open"] += 1
            wins.append(w)
        equity[t] = cash + sum(value(p, t) for p in pos)
        cash_s[t] = cash
    return {"equity": equity, "cash": cash_s, "windows": wins, "open_positions": len(pos)}


def ann(start: float, end: float, days: int) -> float:
    return float((end / start) ** (252.0 / days) - 1.0) if days > 0 and start > 0 and end > 0 else float("nan")
