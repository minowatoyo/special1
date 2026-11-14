"""W5: 銘柄選別と売買の検証（ローカル PC で実行。J-Quants 加工後データ → 集計だけを出力）。

  python scripts/w5/run_selection.py                       # 既定: 2022-04-04 以降の区分（プライム・スタンダード）
  python scripts/w5/run_selection.py --universe-mode proposal_pre2022   # 旧区分の案（未確定）を明示して使うとき

仕様は docs/w5_protocol.md（事前固定）。試行はすべて data/jquants/ledger/trials.jsonl に追記（ハッシュ連鎖）。
出力（標準出力と data/jquants/results/w5/summary.json）は集計のみ。生の表・銘柄ごとの値は出さない。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
import schema  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import evalsel, features, model, portfolio  # noqa: E402
from selectlib.panel import HOLD, Panel  # noqa: E402

COSTS = (0.0, 10.0, 15.0, 30.0)
BASE_COST = 15.0
MODELS = {"SEL-A": ("ridge", features.SEL_A), "SEL-B": ("ridge", features.SEL_B), "SEL-C1": ("ridge", features.SEL_A + features.SEL_B),
          "SEL-C2": ("lgbm", features.SEL_A + features.SEL_B)}


def load(root: Path):
    pr = pd.read_parquet(root / "processed" / "prices_daily.parquet", columns=["date", "code", "open", "close", "adj_open", "adj_high", "adj_low", "adj_close",
                                                                                 "turnover", "limit_up", "limit_down"])
    fl = pd.read_parquet(root / "processed" / "quality_flags.parquet", columns=["code", "date", "no_trade"])
    tp = pd.read_parquet(root / "processed" / "topix_daily.parquet")
    iv = pd.read_parquet(root / "processed" / "listed_master.parquet")
    fins = pd.read_parquet(root / "processed" / "fins_summary.parquet")
    return pr, fl, tp, iv, fins


def manifest_sha(root: Path) -> str:
    h = hashlib.sha256()
    for f in sorted((root / "processed").glob("*.parquet")):
        h.update(f.name.encode() + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def earnings_in_window(P, fins: pd.DataFrame, t_idx: list, picks: dict) -> float:
    """保有銘柄のうち、窓（T+1〜T+22）に財務の開示がある割合（報告用のフラグ。選別には使わない）。"""
    d = fins[["Code", "DiscDate"]].dropna()
    by = {c: np.sort(g["DiscDate"].to_numpy()) for c, g in d.groupby("Code")}
    hit = tot = 0
    for k, w in picks.items():
        a, b = np.datetime64(P.dates[t_idx[k] + 1]), np.datetime64(P.dates[t_idx[k] + 1 + HOLD])
        for j in w:
            ds = by.get(P.codes[j])
            tot += 1
            if ds is not None and ((ds > a) & (ds <= b)).any():
                hit += 1
    return hit / tot if tot else float("nan")


def main(root: Path, mode: str = "post2022", min_history: int = 500, min_periods: int = model.MIN_TRAIN_PERIODS, models=None, costs=COSTS,
         write=True) -> dict:
    pr, fl, tp, iv, fins = load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    markets = schema.POST_2022 + (schema.PRE_2022_PROPOSAL if mode == "proposal_pre2022" else ())
    t_idx = P.rebalance_idx()
    mask = P.eligible(iv, markets, t_idx, min_history=min_history)
    y, raw, top = P.labels(t_idx)
    y = np.where(mask, y, np.nan)
    sd = features.standardized({**features.chart_features(P, t_idx), **features.fins_features(P, fins, t_idx)}, mask)
    yr = model.rank_gauss(y, mask)
    sig = features.sigma_proxy(P, t_idx)
    gate = evalsel.vol_gate(P, t_idx)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    code_ver = "w5-protocol-v1"
    data_sha = manifest_sha(root)
    results, port_returns = {}, {}
    for mname, (kind, names) in (models or MODELS).items():
        if kind == "lgbm":
            try:
                import lightgbm  # noqa: F401
            except ImportError:
                results[mname] = {"skipped": "lightgbm 未導入"}
                continue
        try:
            sc = model.walk_scores(sd, names, yr, mask, kind=kind, min_periods=min_periods)
        except Exception as e:  # noqa: BLE001  一つのモデルの失敗で全体を止めない（理由は集計に残す）
            results[mname] = {"skipped": f"{type(e).__name__}: {str(e)[:200]}"}
            continue
        ks = [k for k in range(len(t_idx)) if np.isfinite(sc[k]).any()]
        if not ks:
            results[mname] = {"skipped": "評価できる期がない"}
            continue
        k0 = ks[0]
        sub = t_idx[k0:]
        univ = np.array([np.nanmean(np.where(mask[k], raw[k], np.nan)) for k in range(k0, len(t_idx))])
        years = np.array([P.dates[T + 1].year for T in sub])
        for wscheme in ("equal", "invvol"):
            for use_gate in (False, True):
                picks_all = {}
                for i, k in enumerate(range(k0, len(t_idx))):
                    if use_gate and gate[k]:
                        picks_all[i] = {}
                        continue
                    cols = evalsel.top_picks(sc[k])
                    picks_all[i] = evalsel.weights(cols, wscheme, sig[k])
                for bps in costs:
                    r = portfolio.simulate(P.raw_open, P.adj_open, P.limit_up, P.limit_down, sub, picks_all, bps=bps)
                    pret = evalsel.period_returns(r["equity"])
                    n = len(pret)
                    s = evalsel.summarize(pret, top[k0:k0 + n], univ[:n])
                    yearly = evalsel.by_year(pret, top[k0:k0 + n], years[:n])
                    tag = f"{mname}|{wscheme}|gate={int(use_gate)}|cost={bps:g}"
                    rec = {"summary": s, "gate": evalsel.gate_check(s, yearly), "by_year": yearly,
                           "fills": {"bought": int(sum(x["bought"] for x in r["info"])), "skipped": int(sum(x["skipped"] for x in r["info"])),
                                     "sell_delayed": int(sum(x.get("sell_delayed", 0) for x in r["info"])),
                                     "sell_forced": int(sum(x.get("sell_forced", 0) for x in r["info"]))},
                           "ledger_reconciles": bool(portfolio.replay_ledger(r["ledger"], 10_000_000) == r["final_cash"])}
                    if bps == BASE_COST and wscheme == "equal" and not use_gate:
                        rec["earnings_in_window_share"] = earnings_in_window(P, fins, t_idx, {k0 + i: list(w) for i, w in picks_all.items() if w})
                    results[tag] = rec
                    port_returns[tag] = pret
                    if write:
                        ledger.append_event("trial", {"tag": tag, "model": mname, "weights": wscheme, "gate": use_gate, "cost_bps": bps,
                                                      "periods": n, "excess_vs_topix_ann": s["excess_vs_topix_ann"], "sharpe_period": s["sharpe_period"],
                                                      "protocol": code_ver, "data_manifest_sha256": data_sha, "universe_mode": mode})
    tags = [t for t in port_returns if t.endswith(f"cost={BASE_COST:g}")]
    out = {"universe_mode": mode, "rebalances_total": len(t_idx), "eligible_median": int(np.median(mask.sum(axis=1)[mask.any(axis=1)])) if mask.any() else 0,
           "trials": results, "n_trials_logged": len(port_returns), "data_manifest_sha256": data_sha}
    if tags:
        n_min = min(len(port_returns[t]) for t in tags)
        sharpes = np.array([evalsel.sharpe(port_returns[t][:n_min]) for t in tags])
        out["pbo"] = evalsel.pbo_cscv(np.column_stack([port_returns[t][:n_min] for t in tags]), s=8)
        for t in tags:
            results[t]["dsr"] = evalsel.deflated_sharpe(port_returns[t][:n_min], sharpes[np.isfinite(sharpes)])
    out["caution"] = ("評価できる期が少ない（約 {} 期）。統計的な力は弱い".format(min((len(v) for v in port_returns.values()), default=0))
                      if port_returns and min(len(v) for v in port_returns.values()) < 40 else "")
    out["ledger_chain"] = ledger.verify()
    if write:
        d = root / "results" / "w5"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--universe-mode", choices=("post2022", "proposal_pre2022"), default="post2022")
    a = ap.parse_args()
    res = main(Path(a.root), a.universe_mode)
    brief = {t: {"excess_vs_topix_ann": round(v["summary"]["excess_vs_topix_ann"], 4), "excess_vs_univ_ann": round(v["summary"]["excess_vs_univ_ann"], 4),
                 "t_vs_topix": round(v["summary"]["t_vs_topix"], 2), "periods": v["summary"]["periods"], "gate_all_pass": v["gate"]["all_pass"],
                 "reconciles": v["ledger_chain"] if False else v["ledger_reconciles"]}
             for t, v in res["trials"].items() if "summary" in v and t.endswith(f"cost={BASE_COST:g}")}
    print(json.dumps({"universe_mode": res["universe_mode"], "eligible_median": res["eligible_median"], "base_cost_trials": brief, "pbo": res.get("pbo"),
                      "caution": res["caution"], "ledger_chain": res["ledger_chain"]}, ensure_ascii=False, indent=1))
    print("詳細（集計のみ）:", Path(a.root) / "results" / "w5" / "summary.json")
