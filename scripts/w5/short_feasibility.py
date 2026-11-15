"""信用売りの実行可能性（ストップ高の翌朝の空売り）。仕様は docs/w5_protocol.md「信用売りの実行可能性」（事前固定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/short_feasibility.py [--rt-cost 0.004] [--borrow 0.0115]
新しい発見ではなく、確認済みの E4a を、制度信用の売りで取るときの実行条件の計算。逆日歩は含めない。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from selectlib import events, exclude, rules, seasonal  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

HOLD = 5
LOAN = "2"


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _month_stat(vals: np.ndarray, t: np.ndarray, P) -> dict:
    v = np.isfinite(vals)
    if not v.any():
        return {"events": 0}
    ym = np.asarray(P.dates.year[t[v]] * 12 + P.dates.month[t[v]])
    s = pd.Series(vals[v]).groupby(ym).mean()
    st_ = seasonal.tstat(s.to_numpy(), lags=1) if len(s) >= 12 else {"mean": float(s.mean()), "t": float("nan"), "p": float("nan")}
    return {"events": int(v.sum()), "months": int(len(s)), "event_weighted_mean": _r(float(vals[v].mean())), "month_mean": _r(st_["mean"]), "t": _r(st_["t"], 2), "p": _r(st_["p"])}


def main(root: Path, rt_cost: float = 0.004, borrow: float = 0.0115, write=True) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    n = len(P.dates)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    va60 = P.va60()
    (ut, uj), _ = events.limit_closes(P)
    keep = elig[ut, uj] & (ut + 1 + HOLD < n)
    t, j = ut[keep], uj[keep]
    if len(t) == 0:
        return {"events_total": 0, "viable_candidate": False, "note": "ストップ高で引けた出来事がない"}
    cls = events.attr_at(P, iv, t, j, "margin_class")
    loan = np.array([str(c) == LOAN for c in cls])
    # 売れる（始値が高値のストップ高でない）、買い戻せる（t+6 の始値がストップ高でない）
    at_limit = P.limit_up & (P.adj_open >= P.adj_high * (1 - 1e-9))
    sellable = np.isfinite(P.raw_open[t + 1, j]) & ~at_limit[t + 1, j]
    cover_blocked = ~np.isfinite(P.raw_open[t + 1 + HOLD, j]) | at_limit[t + 1 + HOLD, j]
    with np.errstate(divide="ignore", invalid="ignore"):
        r = P.adj_open[t + 1 + HOLD, j] / P.adj_open[t + 1, j] - 1.0
    fwd = np.full(P.adj_open.shape, np.nan)
    fwd[: n - HOLD - 1] = P.adj_open[HOLD + 1:] / P.adj_open[1:n - HOLD] - 1.0         # 日 t に対し、t+1 → t+1+HOLD
    fwd = np.where(elig, fwd, np.nan)
    with np.errstate(invalid="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            umean = np.nanmean(fwd, axis=1)
    cost = rt_cost + borrow * HOLD / 252.0
    short_raw = -r
    short_neutral = -(r - umean[t])
    out = {"assumptions": {"round_trip_cost": rt_cost, "borrow_fee_annual": borrow, "hold_sessions": HOLD, "total_cost_per_trade": _r(cost, 5),
                           "not_included": "逆日歩、踏み上げ時の追証・強制決済、税、委託保証金の金利負担"},
           "events_total": int(len(t)), "loan_share": _r(float(loan.mean())), "periods": {}}
    for sp, (lo, hi) in {"discovery": (0, b - HOLD - 2), "confirmation": (b, n - 1)}.items():
        m = (t >= lo) & (t <= hi)
        mm = m & loan
        ok = mm & sellable & ~cover_blocked
        d = {"events": int(m.sum()), "loan_events": int(mm.sum()), "loan_share": _r(float(mm.sum() / m.sum())) if m.sum() else None,
             "loan_not_sellable_limit_up_open_share": _r(float((mm & ~sellable).sum() / mm.sum())) if mm.sum() else None,
             "loan_cover_blocked_share": _r(float((mm & sellable & cover_blocked).sum() / (mm & sellable).sum())) if (mm & sellable).sum() else None,
             "events_per_day_mean": _r(float(ok.sum() / max(len(np.unique(t[m])), 1)), 2),
             "va60_median_yen": int(np.nanmedian(va60[t[ok], j[ok]])) if ok.any() else None}
        d["unhedged_before_cost"] = _month_stat(np.where(ok, short_raw, np.nan), t, P)
        d["market_neutral_before_cost"] = _month_stat(np.where(ok, short_neutral, np.nan), t, P)
        net = np.where(ok, short_neutral - cost, np.nan)
        d["market_neutral_after_cost"] = _month_stat(net, t, P)
        x = short_raw[ok]
        if len(x):
            d["distribution_unhedged_per_trade"] = {"p5": _r(np.percentile(x, 5)), "p50": _r(np.percentile(x, 50)), "p95": _r(np.percentile(x, 95)),
                                                   "loss_over_10pct_share": _r(float((x < -0.10).mean())), "worst": _r(float(x.min()))}
        out["periods"][sp] = d
    # --- 精査: 売り残の重さ・流動性で分ける。逆日歩の感度。資金配分の計算 ---
    mgf = root / "processed" / "margin_interest.parquet"
    mg = pd.read_parquet(mgf) if mgf.exists() else None
    sd_cls = np.full(len(t), -1)
    if mg is not None and len(mg) and "usable_from" in mg.columns:
        sdv = exclude.margin_matrices(P, mg, list(range(n)))["short_days"]
        for tt in np.unique(t):
            row = sdv[tt]
            m = elig[tt] & np.isfinite(row)
            if m.sum() < 30:
                continue
            q1, q2 = np.percentile(row[m], [100 / 3, 200 / 3])
            idx = np.flatnonzero(t == tt)
            v = row[j[idx]]
            sd_cls[idx] = np.where(~np.isfinite(v), -1, np.where(v <= q1, 0, np.where(v <= q2, 1, 2)))
        del sdv
    va_ev = va60[t, j]
    liq = np.where(va_ev >= 5e8, "A_ge500M", np.where(va_ev >= 5e7, "B_50M_500M", "C_lt50M"))
    sdn = {0: "light", 1: "mid", 2: "heavy", -1: "unknown"}
    base = loan & sellable & ~cover_blocked
    net = short_neutral - cost
    ann_years = lambda lo, hi: max((hi - lo + 1) / 252.0, 1e-9)  # noqa: E731

    def sub(mask, lo, hi):
        ok = base & mask & (t >= lo) & (t <= hi)
        if not ok.any():
            return {"events": 0}
        x = net[ok]
        raw = short_raw[ok] - cost
        d = {"events": int(ok.sum()), "net_event_weighted_mean": _r(float(x.mean())), "net_month": _month_stat(np.where(ok, net, np.nan), t, P),
             "loss_over_10pct_share": _r(float((raw < -0.10).mean())), "p1": _r(np.percentile(raw, 1)), "p5": _r(np.percentile(raw, 5)), "p50": _r(np.percentile(raw, 50)),
             "p95": _r(np.percentile(raw, 95)), "worst": _r(float(raw.min()))}
        d["after_gyaku_hibu_per_5d"] = {f"{g:.1%}": _r(float(x.mean() - g)) for g in (0.005, 0.01, 0.02)}
        return d

    out["refinement"] = {"note": "売り残の分け方は、その日の対象銘柄での 3 分位（売り残 ÷ 20 日平均売買代金）。逆日歩は、5 日あたりの追加費用の感度。", "by_period": {}}
    for sp, (lo, hi) in {"discovery": (0, b - HOLD - 2), "confirmation": (b, n - 1)}.items():
        r = {"all_loan": sub(np.ones(len(t), bool), lo, hi)}
        r["by_short_balance"] = {sdn[k]: sub(sd_cls == k, lo, hi) for k in (0, 1, 2, -1)}
        r["by_liquidity"] = {name: sub(liq == name, lo, hi) for name in ("A_ge500M", "B_50M_500M", "C_lt50M")}
        r["light_and_liquid(B以上)"] = sub((sd_cls == 0) & (liq != "C_lt50M"), lo, hi)
        sizing = {}
        for name, mask in (("all_loan", np.ones(len(t), bool)), ("short_balance_light", sd_cls == 0), ("light_and_liquid(B以上)", (sd_cls == 0) & (liq != "C_lt50M"))):
            ok = base & mask & (t >= lo) & (t <= hi)
            if ok.sum() < 20:
                continue
            tpy = float(ok.sum() / ann_years(lo, hi))
            raw = short_raw[ok] - cost
            sizing[name] = {"trades_per_year": _r(tpy, 1), "net_mean_per_trade": _r(float(net[ok].mean())),
                            "per_position_pct_of_equity": {f"{w:.0%}": {"annual_contribution": _r(tpy * w * float(net[ok].mean())), "worst_single_loss": _r(w * float(raw.min())),
                                                                       "p1_single_loss": _r(w * float(np.percentile(raw, 1)))} for w in (0.01, 0.02, 0.03)},
                            "avg_concurrent_positions(5日保有)": _r(tpy * HOLD / 252.0, 1)}
        r["sizing"] = sizing
        out["refinement"]["by_period"][sp] = r
    c = out["periods"]["confirmation"].get("market_neutral_after_cost", {})
    out["viable_candidate"] = bool(c.get("month_mean") is not None and c["month_mean"] > 0 and c.get("p") is not None and c["p"] < 0.05)
    out["note"] = "新しい発見ではない（E4a は確認済み）。実行には、貸借銘柄の取扱い・信用口座・委託保証金・貸株料・逆日歩を、証券会社で確認する。この計算は売買の推奨ではない。"
    if write:
        d = root / "results" / "short_feasibility"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--rt-cost", type=float, default=0.004)
    ap.add_argument("--borrow", type=float, default=0.0115)
    a = ap.parse_args()
    print(json.dumps(main(Path(a.root), a.rt_cost, a.borrow), ensure_ascii=False, indent=1, default=float))
