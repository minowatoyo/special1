"""除外フィルターの検証。仕様は docs/w5_protocol.md「除外フィルターの検証」（事前固定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/exclusion_study.py        # 約 5〜10 分
検証 A: フィルターに掛かった銘柄の超過。検証 B: 順位予測 SEL-C1 の上位 15 から除いたときの、同じ判断日の対の差。
確認期間（買い ≥ 2022-04-04）は 1 度だけ読み、台帳（confirmation_read）に追記する。
"""
from __future__ import annotations

import argparse
import json
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
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import evalsel, exclude, features, model, portfolio, rules  # noqa: E402
from selectlib.panel import HOLD, Panel  # noqa: E402

COST_BPS = 15.0


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _clean(d: dict) -> dict:
    return {k: (_r(v) if isinstance(v, float) else v) for k, v in d.items()}


def main(root: Path, write=True, min_history: int = 500, min_periods: int = model.MIN_TRAIN_PERIODS) -> dict:
    warnings.filterwarnings("ignore", message="Mean of empty slice")
    mf = root / "processed" / "margin_interest.parquet"
    if not mf.exists():
        return {"error": "信用残（margin_interest.parquet）がない。backfill_extra.py と build_processed.py を先に実行する"}
    mg = pd.read_parquet(mf)
    if mg.empty or "usable_from" not in mg.columns:
        return {"error": "信用残が空、または usable_from がない"}
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    t_idx = P.rebalance_idx()
    mask = P.eligible(iv, schema.POST_2022 + schema.PRE_2022_PROPOSAL, t_idx, min_history=min_history)
    y, raw, top = P.labels(t_idx)
    chart = features.chart_features(P, t_idx)
    sd = features.standardized({**chart, **features.fins_features(P, fins, t_idx)}, mask)
    yr = model.rank_gauss(np.where(mask, y, np.nan), mask)
    flg = exclude.flags(exclude.margin_matrices(P, mg, t_idx), chart, mask)
    rawm = np.where(mask, raw, np.nan)
    univ = np.array([rs._nm(rawm[k]) for k in range(len(t_idx))])
    excess = rawm - univ[:, None]
    buy = np.array([P.dates[T + 1] for T in t_idx])
    sell = np.array([P.dates[T + 1 + HOLD] for T in t_idx])
    live = np.array([bool(mask[k].any()) and np.isfinite(univ[k]) for k in range(len(t_idx))])
    ks = {"discovery": [k for k in range(len(t_idx)) if live[k] and sell[k] < rules.SPLIT], "confirmation": [k for k in range(len(t_idx)) if live[k] and buy[k] >= rules.SPLIT]}
    out = {"split": str(rules.SPLIT.date()), "periods": {s: len(v) for s, v in ks.items()}, "filters": list(exclude.ALL_NAMES), "primary_family": list(exclude.PRIMARY)}

    # --- 検証 A ---
    A = {n: {s: exclude.effect(flg[n], excess, mask, ks[s]) for s in ks} for n in exclude.ALL_NAMES}
    qA = exclude.bh_flags({n: A[n]["confirmation"]["p"] for n in exclude.PRIMARY})
    for n in exclude.ALL_NAMES:
        A[n]["confirmation"]["q_primary_family"] = qA.get(n)
        A[n]["works"] = bool(n in exclude.PRIMARY and A[n]["confirmation"]["mean"] is not None and A[n]["confirmation"]["mean"] < 0 and (A[n]["confirmation"]["p"] or 1) < 0.05
                             and (qA.get(n) or 1) < 0.10)

    # --- 検証 B ---
    sc = model.walk_scores(sd, features.SEL_A + features.SEL_B, yr, mask, kind="ridge", min_periods=min_periods)
    scored = [k for k in range(len(t_idx)) if live[k] and np.isfinite(sc[k]).any()]
    B, sim_info = {}, {}
    if scored:
        k0 = scored[0]
        sub = t_idx[k0:]
        base_pk = {k: evalsel.top_picks(sc[k]) for k in scored}
        base_gain = np.full(len(t_idx), np.nan)
        for k in scored:
            base_gain[k] = float(np.nanmean(excess[k][base_pk[k]]))
        ksB = {s: [k for k in v if k in set(scored)] for s, v in ks.items()}

        def sim(pk: dict) -> dict:
            picks_all = {i: evalsel.weights(pk[k], "equal") if k in pk else {} for i, k in enumerate(range(k0, len(t_idx)))}
            r = portfolio.simulate(P.raw_open, P.adj_open, P.limit_up, P.limit_down, sub, picks_all, bps=COST_BPS)
            pret = evalsel.period_returns(r["equity"])
            n = len(pret)
            res = {}
            for s in ks:
                sel = [i for i in range(n) if (k0 + i) in set(ksB[s])]
                x = np.array([pret[i] - univ[k0 + i] for i in sel], dtype=float)
                res[s] = {"periods": int(len(x)), "excess_vs_univ_ann": _r(float(np.nanmean(x) * evalsel.PERIODS_PER_YEAR)) if len(x) else None}
            return res

        sim_info["baseline"] = sim(base_pk)
        for n in exclude.ALL_NAMES:
            fpk = {k: exclude.picks_excluding(sc[k], flg[n][k]) for k in scored}
            gain = np.full(len(t_idx), np.nan)
            removed = np.full(len(t_idx), np.nan)
            for k in scored:
                gain[k] = float(np.nanmean(excess[k][fpk[k]])) if fpk[k] else np.nan
                removed[k] = len(set(base_pk[k]) & set(np.flatnonzero(flg[n][k])))
            B[n] = {s: exclude.paired(base_gain, gain, ksB[s]) for s in ks}
            for s in ks:
                B[n][s]["removed_per_period_mean"] = float(np.nanmean(removed[ksB[s]])) if ksB[s] else None
            sim_info[n] = sim(fpk)
        qB = exclude.bh_flags({n: B[n]["confirmation"]["p"] for n in exclude.PRIMARY})
        for n in exclude.ALL_NAMES:
            B[n]["confirmation"]["q_primary_family"] = qB.get(n)
            c = B[n]["confirmation"]
            B[n]["usable"] = bool(A[n]["works"] and c["mean"] is not None and c["mean"] > 0 and (c["p"] or 1) < 0.05 and (qB.get(n) or 1) < 0.10)
        out["B_periods"] = {s: len(v) for s, v in ksB.items()}
        out["baseline_gain_21d_vs_universe"] = {s: exclude.mean_t([base_gain[k] for k in ksB[s]]) for s in ks}
    out["A_effect_of_flagged_stocks_21d_excess"] = {n: {s: _clean(v) if isinstance(v, dict) else v for s, v in d.items()} for n, d in A.items()}
    out["B_top15_with_exclusion_minus_baseline_21d"] = {n: {s: _clean(v) if isinstance(v, dict) else v for s, v in d.items()} for n, d in B.items()}
    out["simulation_100lot_1000man_15bps_excess_vs_universe_ann"] = sim_info
    out["note"] = "X3・X4・U1234 は、確認期間を見た後に選んだパターン由来で、判定に使わない（記述）。主たる族は X1・X2・U12。"
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    ledger.append_event("confirmation_read", {"family": f"exclusion_v1|{sha[:16]}", "filters": list(exclude.ALL_NAMES), "primary": list(exclude.PRIMARY),
                                              "note": "除外フィルターの検証（検証 A・B）。確認期間を 1 度読む"})
    out["ledger_chain"] = ledger.verify()
    out["data_manifest_sha256"] = sha
    if write:
        d = root / "results" / "exclusion"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
