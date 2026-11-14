"""段階 0（特徴量ごとの IC・係数の安定性）と H0（理想と実現の差の分解）。診断のみ。試行台帳には書かない。ローカル PC で実行。

  python scripts/w5/diagnose.py
出力は集計のみ。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from selectlib import evalsel, features, model, portfolio  # noqa: E402
from selectlib.panel import HOLD, Panel  # noqa: E402


def _ic_stats(x: np.ndarray) -> dict:
    x = x[np.isfinite(x)]
    n = len(x)
    sd = x.std(ddof=1) if n > 2 else float("nan")
    return {"n": int(n), "mean": round(float(x.mean()), 4) if n else None, "t": round(float(x.mean() / (sd / np.sqrt(n))), 2) if n > 2 and sd > 0 else None,
            "share_positive": round(float((x > 0).mean()), 2) if n else None}


def stage0(P, sd, yr, mask, t_idx) -> dict:
    pre = np.array([P.dates[T + 1] < rs.ERA_SPLIT for T in t_idx])
    out = {}
    for name in features.SEL_A + features.SEL_B:
        ics = np.array([evalsel.rank_ic(sd[name][k], yr[k], mask[k]) if mask[k].any() else np.nan for k in range(len(t_idx))])
        out[name] = {"all": _ic_stats(ics), "old_markets": _ic_stats(ics[pre]), "new_markets": _ic_stats(ics[~pre])}
    names = features.SEL_A + features.SEL_B
    co = model.walk_coefs(sd, names, yr, mask)
    ok = np.isfinite(co).all(axis=1)
    out["_ridge_coefficients_C1"] = {n: {"mean": round(float(co[ok, i].mean()), 4), "share_positive_across_fits": round(float((co[ok, i] > 0).mean()), 2)}
                                     for i, n in enumerate(names)} if ok.any() else {}
    out["_ridge_fits"] = int(ok.sum())
    return out


def h0(P, sd, yr, mask, raw, top, t_idx, sig_proxy, min_periods=model.MIN_TRAIN_PERIODS, capital=10_000_000, lot=100) -> dict:
    out = {}
    for mname, (kind, names) in rs.MODELS.items():
        try:
            sc = model.walk_scores(sd, names, yr, mask, kind=kind, min_periods=min_periods)
        except Exception as e:  # noqa: BLE001
            out[mname] = {"skipped": f"{type(e).__name__}"}
            continue
        ks = [k for k in range(len(t_idx)) if np.isfinite(sc[k]).any()]
        k0 = ks[0]
        sub = t_idx[k0:]
        picks = {i: evalsel.weights(evalsel.top_picks(sc[k]), "equal") for i, k in enumerate(range(k0, len(t_idx)))}
        univ = np.array([rs._nm(np.where(mask[k], raw[k], np.nan)) for k in range(k0, len(t_idx))])
        okp = np.isfinite(univ) & np.isfinite(top[k0:])
        ideal = np.array([rs._nm(raw[k][evalsel.top_picks(sc[k])]) for k in range(k0, len(t_idx))])
        res = {}
        for bps in (0.0, 15.0):
            r = portfolio.simulate(P.raw_open, P.adj_open, P.limit_up, P.limit_down, sub, picks, initial=capital, bps=bps, lot=lot)
            res[bps] = r
        ann = lambda x: float(np.mean(x) * evalsel.PERIODS_PER_YEAR)  # noqa: E731
        pr0 = evalsel.period_returns(res[0.0]["equity"])
        pr15 = evalsel.period_returns(res[15.0]["equity"])
        n = len(pr0)
        sel = okp[:n]
        r0 = res[0.0]
        led = r0["ledger"]
        equity = np.array(r0["equity"][:-1], dtype=float)
        idle, unaff, skipped, delayed, forced = [], 0, 0, 0, 0
        for i, info in enumerate(r0["info"]):
            invested = led[(led["side"] == "buy") & (led["idx"] == info["buy_idx"])]["notional"].sum()
            idle.append(1 - invested / equity[i] if equity[i] > 0 else np.nan)
            target = equity[i] / 15.0
            lotsz = lot
            for j in picks[i]:
                p = P.raw_open[info["buy_idx"], j]
                if np.isfinite(p) and p * lot > target:
                    unaff += 1
            skipped += info["skipped"]
            delayed += info.get("sell_delayed", 0) + info.get("final_sell_delayed", 0)
            forced += info.get("sell_forced", 0) + info.get("final_sell_forced", 0)
        npk = sum(len(w) for w in picks.values())
        res_m = {"ideal_top15_ann": ann(ideal[:n][sel]), "simulated_no_cost_ann": ann(pr0[sel]), "simulated_15bps_ann": ann(pr15[sel]),
                 "gap_lot_and_fill_effect": ann(ideal[:n][sel]) - ann(pr0[sel]), "gap_cost_15bps": ann(pr0[sel]) - ann(pr15[sel]),
                 "gap_total": ann(ideal[:n][sel]) - ann(pr15[sel]), "universe_ann": ann(univ[:n][sel]),
                 "idle_cash_fraction_after_buy_mean": float(np.nanmean(idle)), "picks_total": int(npk),
                 "picks_unaffordable_one_lot_share": unaff / npk if npk else None, "picks_skipped_total": int(skipped),
                 "sell_delayed_total": int(delayed), "sell_forced_total": int(forced), "periods": int(sel.sum())}
        out[mname] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res_m.items()}
    return out


def main(root: Path, capital: int = 10_000_000, lot: int = 100) -> dict:
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    t_idx = P.rebalance_idx()
    mask = P.eligible(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL, t_idx)
    y, raw, top = P.labels(t_idx)
    y = np.where(mask, y, np.nan)
    sd = features.standardized({**features.chart_features(P, t_idx), **features.fins_features(P, fins, t_idx)}, mask)
    yr = model.rank_gauss(y, mask)
    out = {"stage0_feature_ic": stage0(P, sd, yr, mask, t_idx), "h0_ideal_vs_realized_equal_weight_full_rotation": h0(P, sd, yr, mask, raw, top, t_idx, None, capital=capital, lot=lot),
           "h0_conditions": {"capital_yen": capital, "lot": lot, "note": "既定（1,000 万円・100 株）以外は反実仮想の診断（仕様の変更ではなく、試行でもない）"}}
    d = root / "results" / "diagnose"
    d.mkdir(parents=True, exist_ok=True)
    tag = "" if (capital, lot) == (10_000_000, 100) else f"_cap{capital}_lot{lot}"
    (d / f"summary{tag}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--capital", type=int, default=10_000_000)
    ap.add_argument("--lot", type=int, default=100)
    a = ap.parse_args()
    r = main(Path(a.root), a.capital, a.lot)
    if (a.capital, a.lot) != (10_000_000, 100):
        r.pop("stage0_feature_ic", None)                      # 段階 0 は条件に依存しないので、反実仮想の実行では省く
    print(json.dumps(r, ensure_ascii=False, indent=1))
