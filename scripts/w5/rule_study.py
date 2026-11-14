"""チャート規則の一斉検証（段階 1〜3）。ローカル PC で実行。出力は集計のみ（銘柄ごとの値は出さない）。

  python scripts/w5/rule_study.py            # 約 20〜60 分（全銘柄・約 2,000 銘柄のシグナルを 2 回計算）
仕様は docs/w5_protocol.md の「追加の事前固定」。確認期間は、発見期間の通過規則だけを 1 度読む（読んだ記録を台帳に追記）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
import schema  # noqa: E402
from forecastlib import stats as st  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import rules  # noqa: E402
from selectlib.panel import Panel  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import run_selection  # noqa: E402


def _row(k, t):
    return {"rule": k[0], "h": k[1], "days": t["days"], "signals_per_day": round(t["signals_per_day"], 1), "mean_excess": round(t["mean"], 5),
            "t": round(t["t"], 2), "p": round(t["p"], 4), "net_of_cost": round(t["net_of_round_trip_cost"], 5),
            "by_liquidity_tertile": [round(x, 5) for x in t["mean_by_liquidity_tertile(low,mid,high)"]]}


def family(acc, label, ledger, data_sha, q=0.10):
    """発見 → 補正 → 確認（1 度だけ読む）。"""
    dis = rules.discover(acc, q)
    passed = dis["passed"]
    key = f"{label}|{data_sha[:16]}"
    already = any(r["type"] == "confirmation_read" and r["payload"]["family"] == key for r in ledger._rows())
    conf = {}
    if passed:
        conf = rules.confirm(acc, passed)
        ledger.append_event("confirmation_read", {"family": key, "rules": [f"{a}|h{b}" for a, b in passed], "re_read": already})
    laws = []
    for k in passed:
        c = conf.get(k)
        d = dis["table"][k]
        same = c is not None and np.isfinite(c["mean"]) and np.sign(c["mean"]) == np.sign(d["mean"]) and c["p"] < 0.05
        laws.append({**_row(k, d), "q": round(d["q"], 4), "confirmation": _row(k, c) if c else None, "law": bool(same),
                     "exceeds_round_trip_cost": bool(same and abs(c["mean"]) > rules.ROUND_TRIP_COST)})
    return {"family": label, "n_tests": dis["n_tests"], "discovery_passed": len(passed), "laws": sum(x["law"] for x in laws),
            "results": sorted(laws, key=lambda x: x["q"]), "re_read_of_confirmation": already}, dis


def main(root: Path, write=True) -> dict:
    pr, fl, tp, iv, fins = run_selection.load(root)
    P = Panel.from_frames(pr, fl, tp)
    del pr
    markets = schema.POST_2022 + schema.PRE_2022_PROPOSAL
    elig = P.eligible_daily(iv, markets)
    ledger = AppendOnlyLedger(root / "ledger" / "trials.jsonl")
    data_sha = run_selection.manifest_sha(root)
    t0 = time.time()
    prog = lambda a, b: print(f"[{time.time() - t0:.0f}s] {a}/{b} 銘柄", flush=True)  # noqa: E731
    names = list(rules.rule_signals(pd.DataFrame({"open": np.linspace(100, 200, 400), "high": np.linspace(101, 201, 400), "low": np.linspace(99, 199, 400),
                                                  "close": np.linspace(100, 200, 400), "volume": 1e6}, index=pd.bdate_range("2020-01-01", periods=400))).columns)
    b1 = {**rules.base_builders(names)}
    b3 = rules.type_builders()
    acc1 = rules.run_pass(P, elig, {**b1, **b3}, fins, progress=prog)
    out = {"eligible_median_per_day": int(np.median(elig.sum(axis=1)[elig.any(axis=1)])), "data_manifest_sha256": data_sha}
    base_acc = {**acc1, "names": names, "cnt": acc1["cnt"][:, : len(names)], "sum": acc1["sum"][:, : len(names)],
                "cnt3": acc1["cnt3"][:, :, : len(names)], "sum3": acc1["sum3"][:, :, : len(names)]}
    t_idx = [acc1["names"].index(n) for n in b3]
    type_acc = {**acc1, "names": list(b3), "cnt": acc1["cnt"][:, t_idx], "sum": acc1["sum"][:, t_idx], "cnt3": acc1["cnt3"][:, :, t_idx], "sum3": acc1["sum3"][:, :, t_idx]}
    out["stage1_rules"], dis1 = family(base_acc, "stage1", ledger, data_sha)
    out["stage3_types"], _ = family(type_acc, "stage3", ledger, data_sha)
    sel = sorted({k[0] for k in dis1["passed"]})
    if sel:
        cb = rules.conditional_builders(sel)
        acc2 = rules.run_pass(P, elig, cb, fins, progress=prog)
        out["stage2_conditional"], _ = family(acc2, "stage2", ledger, data_sha)
    else:
        out["stage2_conditional"] = {"note": "発見期間の補正後に有意な基本規則がないため、段階 2 は実施しない"}
    # 参考: 発見期間の全規則の表（集計のみ）。確認期間の値は通過規則以外は出さない。
    out["stage1_discovery_table_top20_by_p"] = [_row(k, v) | {"q": round(v["q"], 4)} for k, v in sorted(dis1["table"].items(), key=lambda kv: kv[1]["p"])[:20]]
    out["ledger_chain"] = ledger.verify()
    if write:
        d = root / "results" / "rules"
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    res = main(Path(ap.parse_args().root))
    brief = {k: ({kk: vv for kk, vv in v.items() if kk != "results"} if isinstance(v, dict) and "results" in v else v)
             for k, v in res.items() if k not in ("stage1_discovery_table_top20_by_p",)}
    brief["laws_and_candidates"] = {k: v["results"] for k, v in res.items() if isinstance(v, dict) and "results" in v}
    brief["stage1_discovery_table_top20_by_p"] = res["stage1_discovery_table_top20_by_p"]
    print(json.dumps(brief, ensure_ascii=False, indent=1))
    print("詳細（集計のみ）:", Path(ap.parse_args().root) / "results" / "rules" / "summary.json")
