"""S2（配当の権利取り）の、口座での売買の模擬。仕様は docs/w5_protocol.md「S2 の実行可能性」（事前固定）。ローカル PC で実行。出力は集計のみ。

  python scripts/w5/s2_portfolio.py        # 約 3〜5 分
1,000 万円・現物・100 株単位・コスト込みで、確認済みの効果が、口座にいくら残るかを計算する（新しい証拠ではない）。
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import rules, s2port, seasonal  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

TRIALS = {"primary_tier_B_only": (1,), "secondary_tier_A_and_B": (0, 1)}


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def universe_index(P, elig: np.ndarray) -> np.ndarray:
    """対象銘柄（前日に対象）の、日次の終値リターンの平均を積み上げた指数。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.full(P.adj_close.shape, np.nan)
        r[1:] = P.adj_close[1:] / P.adj_close[:-1] - 1
    okp = np.zeros_like(elig)
    okp[1:] = elig[:-1]
    d = np.nan_to_num(np.nanmean(np.where(okp, r, np.nan), axis=1))
    return np.cumprod(1 + d)


def main(root: Path, write=True, initial: float = 10_000_000) -> dict:
    warnings.filterwarnings("ignore", message="Mean of empty slice")
    pr, fl, tp, iv, fins = rs.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64(), side="left"))
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    va60 = P.va60()
    cands = s2port.candidates(P, elig, va60, fins)
    ui = universe_index(P, elig)
    tpx = P.topix["close"].to_numpy(dtype=float)
    n = len(P.dates)
    out = {"spec": "買い: 権利付き最終日 L の 40 営業日前の始値／売り: L の始値／候補: 権利月の銘柄の予想配当利回り 上位 1/5／最大 10 銘柄／窓の資金 = 総資産の 1/2／100 株単位／片道 A 15bps・B 30bps",
           "initial_yen": int(initial), "months_with_candidates": len(cands), "trials": {}}
    if not cands:
        return out
    t0 = cands[0]["e"]
    spans = {"discovery": (t0, min(b, n) - 1), "confirmation": (max(b, t0), n - 1), "all": (t0, n - 1)}
    for name, tiers_allowed in TRIALS.items():
        sim = s2port.simulate(P, cands, va60, tiers_allowed, initial=initial)
        eq, cash = sim["equity"], sim["cash"]
        res = {}
        for sp, (a, z) in spans.items():
            if z - a < 60:
                res[sp] = {"note": "期間が短い"}
                continue
            start = initial if a == t0 else eq[a - 1]
            ws = [w for w in sim["windows"] if w["n"] > 0 and w["open"] == 0 and np.isfinite(w["univ"]) and (sp == "all" or seasonal._period(w["e"], w["L"], b) == sp)]
            ex = np.array([w["proceeds"] / w["invested"] - 1 - w["univ"] for w in ws], dtype=float)
            st_ = seasonal.tstat(ex, lags=1) if len(ex) else {"n": 0, "mean": float("nan"), "t": float("nan"), "p": float("nan")}
            allw = [w for w in sim["windows"] if sp == "all" or seasonal._period(w["e"], w["L"], b) == sp]
            acct = s2port.ann(start, eq[z], z - a + 1)
            univ = s2port.ann(ui[a - 1] if a > 0 else 1.0, ui[z], z - a + 1)
            res[sp] = {"account_return_ann": _r(acct), "universe_equal_weight_ann": _r(univ), "topix_price_ann": _r(s2port.ann(tpx[a - 1] if a > 0 else tpx[a], tpx[z], z - a + 1)),
                       "account_minus_universe_ann": _r(acct - univ), "end_equity_yen": int(round(eq[z])),
                       "windows_traded": len(ws), "window_net_excess_vs_universe": {"mean": _r(st_["mean"]), "t": _r(st_["t"], 2), "p": _r(st_["p"]), "share_positive": _r(float((ex > 0).mean()), 2) if len(ex) else None},
                       "window_net_return_on_invested_mean": _r(float(np.mean([w["proceeds"] / w["invested"] - 1 for w in ws]))) if ws else None,
                       "stocks_per_window_mean": _r(float(np.mean([w["n"] for w in allw])), 1) if allw else None,
                       "windows_with_no_trade": int(sum(w["n"] == 0 for w in allw)), "skipped_candidates_total": int(sum(w["skipped"] for w in allw)),
                       "cash_share_mean": _r(float(np.nanmean(cash[a:z + 1] / eq[a:z + 1])), 2), "cost_total_yen": int(round(sum(w["cost"] for w in allw)))}
        c = res.get("confirmation", {})
        res["feasible"] = bool(c.get("window_net_excess_vs_universe", {}).get("mean") is not None and c["window_net_excess_vs_universe"]["mean"] > 0
                               and c.get("account_minus_universe_ann") is not None and c["account_minus_universe_ann"] > 0)
        res["open_positions_at_end"] = sim["open_positions"]
        out["trials"][name] = res
    out["note"] = "確認期間は S2 で既読。新しい証拠ではなく、目減りの計算。配当は、戦略側も比較対象（価格指数）も含まない。"
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    sha = rs.manifest_sha(root)
    for name in out["trials"]:
        c = out["trials"][name].get("confirmation", {})
        ledger.append_event("s2_portfolio_trial", {"trial": name, "feasible": out["trials"][name]["feasible"], "confirmation_account_minus_universe_ann": c.get("account_minus_universe_ann"),
                                                    "data_manifest_sha256": sha})
    out["ledger_chain"] = ledger.verify()
    out["data_manifest_sha256"] = sha
    if write:
        d = root / "results" / "s2_portfolio"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1, default=float))
