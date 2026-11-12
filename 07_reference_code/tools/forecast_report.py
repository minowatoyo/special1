"""日足 CSV から確率予測のレポートを作る。

    python tools/forecast_report.py --csv toyota.csv --name "トヨタ自動車 (7203)" --out out/7203

主な引数:
  --csv PATH              日足 CSV（Stooq 形式など。forecastlib/data.py を参照）
  --name TEXT             レポートの題名に使う名前
  --out DIR               出力先（report.md、forecast.json、図、表の CSV）
  --aux NAME=PATH[:LAG]   補助系列（指数・為替など）。LAG=0 は同じ取引時間の系列、1（既定）は前日までの値だけを使う
  --panel PATH ...        傾きの推定に加える他銘柄の日足（プール推定）
  --scenarios PATH        シナリオ区間の JSON（区間に入る確率を計算する）
  --levels 3100,3550      確率を出したい価格水準（自動抽出の水準に追加）
  --split DATE:FACTOR     未調整の分割の調整（例 2021-09-29:5）。複数可
  --auto-split            検査で見つけた未調整の分割候補を自動で調整する
  --ledger PATH           予測台帳（CSV）に今回の予測を記録する
  --step N                採点する時点の間隔（既定 1。大きくすると速い）
  --today YYYY-MM-DD      データの鮮度の判定に使う基準日
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecastlib import Config, data, evaluate, eventstudy, features, forecast, ledger, prepare_asset, report, walk_forward  # noqa: E402


def _code_version() -> str:
    try:
        v = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10)
        d = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "."], capture_output=True, text=True, timeout=10)
        return v.stdout.strip() + ("+未コミットの変更あり" if d.stdout.strip() else "")
    except Exception:
        return "不明"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aux", action="append", default=[])
    ap.add_argument("--panel", nargs="*", default=[])
    ap.add_argument("--scenarios")
    ap.add_argument("--levels", default="")
    ap.add_argument("--split", action="append", default=[])
    ap.add_argument("--auto-split", action="store_true")
    ap.add_argument("--ledger")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--today")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = data.load_ohlcv(a.csv)
    val = data.validate_ohlcv(df, today=a.today)
    splits = {}
    for s in a.split:
        d, f = s.split(":")
        splits[pd.Timestamp(d)] = float(f)
    if a.auto_split:
        for s in val["suspect_splits"]:
            if s.get("factor"):
                splits.setdefault(pd.Timestamp(s["date"]), float(s["factor"]))
    if splits:
        df = data.adjust_splits(df, splits)
        val2 = data.validate_ohlcv(df, today=a.today)
        val["info"].append(f"分割調整後の再検査: 注意 {len(val2['warnings'])} 件、分割候補 {len(val2['suspect_splits'])} 件")
        val["suspect_splits"] = val2["suspect_splits"]
    if val["errors"]:
        print("データにエラーがあるため中止:", val["errors"], file=sys.stderr)
        return 2
    df = df.dropna(subset=["open", "high", "low", "close"])

    aux = {}
    for spec in a.aux:
        nm, rest = spec.split("=", 1)
        path, lag = (rest.rsplit(":", 1) + ["1"])[:2] if ":" in rest and rest.rsplit(":", 1)[1].isdigit() else (rest, "1")
        aux[nm] = (data.load_ohlcv(path)["close"], int(lag))
    cfg = Config(step=a.step)
    asset = prepare_asset(df, a.name, cfg, aux or None)
    panel = tuple(prepare_asset(data.load_ohlcv(p).dropna(subset=["open", "high", "low", "close"]), Path(p).stem, cfg) for p in a.panel)
    wf = walk_forward(asset, cfg, panel)
    if not wf:
        print("履歴が短く、検証できる期間がない（学習のみの期間 1,250 日＋評価期間が必要）", file=sys.stderr)
        return 3
    summary = evaluate.summarize(wf, cfg)
    decisions = evaluate.decide(wf, cfg)
    panel_info = None
    if panel:
        # 他銘柄にも同じ手順を当て、日付ごとの銘柄平均の損失で採否を決める（1 銘柄だけでは検出力が弱いため）
        wfs = {asset.name: wf}
        for pa in panel:
            others = tuple([asset] + [q for q in panel if q is not pa])
            wfs[pa.name] = walk_forward(pa, cfg, others)
        pooled = evaluate.decide_panel(wfs, cfg)
        panel_info = {"names": [pa.name for pa in panel], "single": decisions}
        decisions = {h: pooled.get(h, d) for h, d in decisions.items()}
    touch = evaluate.touch_summary(wf, cfg)
    events = eventstudy.event_study(asset, features.signal_frame(df), cfg)
    levels = forecast.auto_levels(df)
    for x in [v for v in a.levels.split(",") if v.strip()]:
        levels.append({"name": "指定の水準", "price": float(x)})
    fc = forecast.final_forecast(asset, wf, decisions, cfg, levels)
    scen = None
    if a.scenarios:
        spec = json.loads(Path(a.scenarios).read_text(encoding="utf-8"))
        scen = forecast.scenario_probabilities(fc, spec["scenarios"])
    meta = {
        "データ": f"{Path(a.csv).name}（sha256 {hashlib.sha256(Path(a.csv).read_bytes()).hexdigest()[:16]}、{len(df):,} 行、{df.index[0].date()}〜{df.index[-1].date()}）",
        "補助系列": "、".join(f"{k}（lag={v[1]}）" for k, v in aux.items()) or "なし",
        "プール推定に加えた銘柄": "、".join(p.name for p in panel) or "なし",
        "コードの版": _code_version(),
        "data_sha256": hashlib.sha256(Path(a.csv).read_bytes()).hexdigest(),
        "code_version": _code_version(),
    }
    if splits:
        meta["splits_applied"] = {str(k.date()): v for k, v in splits.items()}
    report.plot_fan(asset, fc, out / "fan.png")
    report.plot_calibration(wf, decisions, out / "calibration.png")
    md = report.build_report(a.name, asset, val, wf, summary, decisions, touch, events, fc, cfg,
                             {k: v for k, v in meta.items() if k not in ("data_sha256", "code_version")}, scen,
                             {"予測区間": "fan.png", "較正（PIT）": "calibration.png"}, panel_info, evaluate.vol_summary(asset, cfg),
                             {nm: forecast.conditional_table(df, ac, lg) for nm, (ac, lg) in aux.items()} or None)
    (out / "report.md").write_text(md, encoding="utf-8")
    (out / "forecast.json").write_text(json.dumps({"forecast": fc, "decisions": decisions, "scenarios": scen}, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    events.to_csv(out / "eventstudy.csv", index=False)
    for h, t in summary.items():
        t.to_csv(out / f"summary_h{h}.csv")
    touch.to_csv(out / "touch.csv", index=False)
    if a.ledger:
        k = ledger.append_forecast(a.ledger, fc, meta)
        print(f"予測台帳に {k} 行を記録: {a.ledger}")
    print(f"レポート: {out / 'report.md'}")
    for h, d in decisions.items():
        print(f"  h={h}: 最終モデル {d['final_model']}（{d.get('reason', '')}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
