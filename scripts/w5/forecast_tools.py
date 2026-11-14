"""W4（予測台帳）と FIX-05（外側評価）の実行（ローカル PC。J-Quants 加工後データ → 集計のみ）。

  python scripts/w5/forecast_tools.py forecast 7203 5802     # 最新日の予測を、追記専用の台帳に記録（data/jquants/ledger/forecasts.jsonl）
  python scripts/w5/forecast_tools.py score 7203 5802        # 期日が来た予測を採点（outcome の行を追記。予測の行は変えない）
  python scripts/w5/forecast_tools.py outer --n 30           # 流動性上位 N 銘柄で、外側のウォークフォワード評価（集計のみ）
J-Quants 正本のデータだけを使う（アダプタ経由）。台帳には、データの目録ハッシュ・コード版・設定ハッシュを必ず付ける。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
from forecastlib import Config, evaluate, forecast, outer, prepare_asset, walk_forward  # noqa: E402
from forecastlib import jquants_adapter as ja  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402


def manifest_sha(root: Path) -> str:
    h = hashlib.sha256()
    for f in sorted((root / "processed").glob("*.parquet")):
        h.update(f.name.encode() + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def config_sha(cfg) -> str:
    return hashlib.sha256(json.dumps(asdict(cfg), sort_keys=True, default=str).encode()).hexdigest()


def forecast_one(root: Path, code: str, cfg, ledger: AppendOnlyLedger, meta: dict) -> int:
    df = ja.load_ohlcv(code, root=root).dropna(subset=["open", "high", "low", "close"])
    asset = prepare_asset(df, code, cfg)
    wf = walk_forward(asset, cfg)
    dec = evaluate.decide(wf, cfg)
    fc = forecast.final_forecast(asset, wf, dec, cfg)
    return len(ledger.append_forecast(fc, meta))


def liquid_codes(root: Path, n: int) -> list:
    pr = pd.read_parquet(root / "processed" / "prices_daily.parquet", columns=["date", "code", "turnover"])
    last = pr["date"].max()
    w = pr[pr["date"] > last - pd.Timedelta(days=100)].groupby("code")["turnover"].mean()
    return [c[:-1] if c.endswith("0") else c for c in w.sort_values(ascending=False).index[:n]]


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("forecast", "score", "outer"))
    ap.add_argument("codes", nargs="*")
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--step", type=int, default=None, help="評価の間隔（営業日）。既定は forecast/score が 10、outer が 5")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = Config(step=a.step or (5 if a.cmd == "outer" else 10))
    ledger = AppendOnlyLedger(root / "ledger" / "forecasts.jsonl")
    if a.cmd == "forecast":
        meta = {"source": "jquants", "data_manifest_sha256": manifest_sha(root), "code_version": code_version(), "config_sha256": config_sha(cfg)}
        out = {c: forecast_one(root, c, cfg, ledger, meta) for c in a.codes}
        return {"added_rows": out, "ledger": ledger.verify()}
    if a.cmd == "score":
        out = {c: len(ledger.score(ja.load_ohlcv(c, root=root), c)) for c in a.codes}
        return {"outcomes_added": out, "ledger": ledger.verify()}
    codes = a.codes or liquid_codes(root, a.n)
    per_h: dict = {}
    skipped = {"short_history": 0, "too_few_points": 0, "error": 0}
    for c in codes:
        df = ja.load_ohlcv(c, root=root).dropna(subset=["open", "high", "low", "close"])
        if len(df) < 1500:
            skipped["short_history"] += 1
            continue
        try:
            r = outer.outer_evaluate(walk_forward(prepare_asset(df, c, cfg), cfg), cfg)
        except Exception:  # noqa: BLE001
            skipped["error"] += 1
            continue
        for h, v in r.items():
            if "skill_vs_B1" in v:
                per_h.setdefault(h, []).append(v)
            else:
                skipped["too_few_points"] += 1
    summary = {}
    for h, vs in per_h.items():
        sk = np.array([v["skill_vs_B1"] for v in vs])
        opt = np.array([v["optimism(insample_skill - outer_skill)"] for v in vs])
        picks = pd.Series([b["selected"] for v in vs for b in v["blocks"]]).value_counts(normalize=True).round(3).to_dict()
        summary[str(h)] = {"stocks": len(vs), "outer_skill_vs_B1_mean": float(sk.mean()), "outer_skill_vs_B1_median": float(np.median(sk)),
                           "share_positive": float((sk > 0).mean()), "optimism_mean": float(opt.mean()), "selected_model_frequency": picks,
                           "dm_p_below_0.05_share": float(np.mean([v["dm_p_vs_B1"] < 0.05 for v in vs]))}
    d = root / "results" / "outer"
    d.mkdir(parents=True, exist_ok=True)
    (d / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"outer_evaluation": summary, "stocks_requested": len(codes), "stocks_evaluated": max((len(v) for v in per_h.values()), default=0),
            "skipped": skipped, "step": cfg.step}


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=1))
