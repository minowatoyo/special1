"""forecastlib の自己検査（合成データ。実市場データではない）。

    python examples/forecast_selfcheck.py --out selfcheck_out --parts A      # 部分ごとに実行できる（並行可）
    python examples/forecast_selfcheck.py --out selfcheck_out --summarize    # 保存済みの結果を表にまとめる
    python examples/forecast_selfcheck.py --out selfcheck_out --quick        # 小さい設定で全部

調べること:
  A.  偽陽性: 予測できる成分のないデータ（ボラティリティ変動と厚い裾だけ）で、
      傾き・類似局面のモデルを誤って採用する割合、区間の的中率、イベントスタディの誤検出数
  B.  検出力（1 銘柄）: 埋め込んだ成分の強さごとに、採用できる割合
  C0. 偽陽性（8 銘柄をまとめた判定）
  C.  検出力（8 銘柄をまとめた判定、成分の係数 0.05）
  C3. 検出力（8 銘柄をまとめた判定、成分の係数 0.03）
各判定の p 値を保存するので、採用のしきい値を変えたときの割合も後から数えられる。乱数の種は固定。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from forecastlib import Config, evaluate, eventstudy, features, prepare_asset, synth, walk_forward  # noqa: E402

HS = (5, 21, 63)
KEEP = ("adopted_tilt", "final_model", "sigma_model", "best_candidate", "best_skill", "rc_p", "dm_p", "boot_p",
        "half1_gain", "half2_gain", "sigma_skill", "sigma_dm_p")


def _dec_row(dec: dict) -> dict:
    row = {}
    for h in HS:
        for k in KEEP:
            v = dec[h].get(k)
            row[f"{k}_{h}"] = (float(v) if isinstance(v, (float, np.floating)) else v)
    return row


def part_a(n_rep, n, cfg):
    rows = []
    for i in range(n_rep):
        df = synth.make_garch_ohlcv(n=n, seed=5000 + i)
        a = prepare_asset(df, "S", cfg)
        wf = walk_forward(a, cfg)
        dec, sm = evaluate.decide(wf, cfg), evaluate.summarize(wf, cfg)
        ev = eventstudy.event_study(a, features.signal_frame(df), cfg)
        row = {"seed": 5000 + i, "false_mean_signals": int((ev["q_b"] < 0.10).sum()),
               "false_mean_signals_05": int((ev["q_b"] < 0.05).sum()), "tested": int(np.isfinite(ev["p_b"]).sum()), **_dec_row(dec)}
        for h in HS:
            t = sm[h]
            for m in ("B0", "B1", "V3"):
                for c in ("cov50", "cov80", "cov90", "crps"):
                    row[f"{c}_{m}_{h}"] = float(t.loc[m, c])
        rows.append(row)
        print("A", i, [row[f"adopted_tilt_{h}"] for h in HS], row["false_mean_signals"], flush=True)
    return rows


def part_b(n_rep, n, cfg, coefs):
    rows = []
    for coef in coefs:
        for i in range(n_rep):
            df = synth.make_garch_ohlcv(n=n, seed=7000 + i, signal={"type": "momentum", "coef": coef, "window": 63})
            wf = walk_forward(prepare_asset(df, "S", cfg), cfg)
            rows.append({"coef": coef, "seed": 7000 + i, **_dec_row(evaluate.decide(wf, cfg))})
            print("B", coef, i, [rows[-1][f"adopted_tilt_{h}"] for h in HS], flush=True)
    return rows


def part_c(n_rep, n, cfg, coef, n_assets):
    rows = []
    for i in range(n_rep):
        sig = {"type": "momentum", "coef": coef, "window": 63} if coef else None
        dfs = [synth.make_garch_ohlcv(n=n, seed=9000 + 100 * i + j + (0 if coef else 50), signal=sig) for j in range(n_assets)]
        assets = [prepare_asset(d, f"A{j}", cfg) for j, d in enumerate(dfs)]
        wfs = {a.name: walk_forward(a, cfg, tuple(b for b in assets if b is not a)) for a in assets}
        rows.append({"coef": coef, "rep": i, "n_assets": n_assets, **_dec_row(evaluate.decide_panel(wfs, cfg))})
        print("C", coef, i, [rows[-1][f"adopted_tilt_{h}"] for h in HS], flush=True)
    return rows


def _adopt(r: dict, h: int, p: float) -> bool:
    v = [r.get(f"rc_p_{h}"), r.get(f"dm_p_{h}"), r.get(f"boot_p_{h}")]
    if any(x is None for x in v):
        return False
    return all(x < p for x in v) and r[f"half1_gain_{h}"] > 0 and r[f"half2_gain_{h}"] > 0


def _rate(rows, h, p) -> str:
    return f"{sum(_adopt(r, h, p) for r in rows)}/{len(rows)}"


def summarize(out: Path) -> str:
    res = {}
    for part in ("A", "B", "C0", "C3", "C"):
        f = out / f"selfcheck_{part}.json"
        if f.exists():
            res[part] = json.loads(f.read_text(encoding="utf-8"))
    L = ["# forecastlib 自己検査の結果（合成データ）", ""]
    for part, d in res.items():
        L.append(f"- {part}: {d['n_days']} 日 × {len(d['rows'])} 回、採点間隔 {d['step']} 日、{d['seconds']} 秒")
    L.append("")
    if "A" in res:
        A = res["A"]["rows"]
        L += ["## A. 予測できる成分のないデータ（1 銘柄での判定）", "", "| 項目 | 1週間 | 1か月 | 3か月 |", "|---|---:|---:|---:|"]
        for p in (0.10, 0.05):
            L.append(f"| 傾き・類似局面を誤って採用（しきい値 p<{p:.2f}） | " + " | ".join(_rate(A, h, p) for h in HS) + " |")
        L.append("| 幅のモデルに V3 を選んだ回数 | " + " | ".join(f"{sum(r[f'sigma_model_{h}'] == 'V3' for r in A)}/{len(A)}" for h in HS) + " |")
        for m in ("B1", "V3"):
            L.append(f"| {m} の CRPS 改善率（B0 比）の平均 | " + " | ".join(
                f"{100 * np.mean([1 - r[f'crps_{m}_{h}'] / r[f'crps_B0_{h}'] for r in A]):+.2f}%" for h in HS) + " |")
        for m in ("B0", "B1", "V3"):
            for c, nm in (("cov50", "50%"), ("cov80", "80%"), ("cov90", "90%")):
                L.append(f"| {m}: {nm} 区間の的中率（平均、最小〜最大） | " + " | ".join(
                    f"{100 * np.mean([r[f'{c}_{m}_{h}'] for r in A]):.1f}%（{100 * min(r[f'{c}_{m}_{h}'] for r in A):.0f}〜{100 * max(r[f'{c}_{m}_{h}'] for r in A):.0f}）"
                    for h in HS) + " |")
        fs, fs5 = [r["false_mean_signals"] for r in A], [r["false_mean_signals_05"] for r in A]
        L += ["", f"イベントスタディ（1 系列あたり平均 {np.mean([r['tested'] for r in A]):.0f} 通りを検定）で残った数: "
              f"q<0.10 は {sum(v > 0 for v in fs)}/{len(fs)} 系列で 1 個以上（合計 {sum(fs)} 個、最大 {max(fs)} 個）、"
              f"q<0.05 は {sum(v > 0 for v in fs5)}/{len(fs5)} 系列で 1 個以上（合計 {sum(fs5)} 個）。", ""]
    if "B" in res:
        B = res["B"]["rows"]
        L += ["## B. 成分を埋め込んだデータ（1 銘柄での判定）", "", "| 成分の強さ（係数） | しきい値 | 1週間 | 1か月 | 3か月 |", "|---|---|---:|---:|---:|"]
        for coef in sorted({r["coef"] for r in B}):
            rs = [r for r in B if r["coef"] == coef]
            for p in (0.10, 0.05):
                L.append(f"| {coef:.2f} | p<{p:.2f} | " + " | ".join(_rate(rs, h, p) for h in HS) + " |")
        L.append("")
    if "C0" in res or "C" in res or "C3" in res:
        L += ["## C. 8 銘柄をまとめた判定", "", "| 成分の強さ（係数） | しきい値 | 1週間 | 1か月 | 3か月 |", "|---|---|---:|---:|---:|"]
        for part in ("C0", "C3", "C"):
            if part in res:
                rs = res[part]["rows"]
                for p in (0.10, 0.05):
                    L.append(f"| {rs[0]['coef']:.2f} | p<{p:.2f} | " + " | ".join(_rate(rs, h, p) for h in HS) + " |")
        L.append("")
    text = "\n".join(L) + "\n"
    (out / "selfcheck.md").write_text(text, encoding="utf-8")
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--parts", default="A,B,C0,C")
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.summarize:
        print(summarize(out))
        return 0
    n = 3000 if a.quick else 5000
    cfg = Config(step=5 if a.quick else 3, boot_b=300 if a.quick else 1000)
    na, nb, nc = (6, 4, 2) if a.quick else (60, 20, 12)
    for part in [p.strip() for p in a.parts.split(",") if p.strip()]:
        t0 = time.time()
        if part == "A":
            rows = part_a(na, n, cfg)
        elif part == "B":
            rows = part_b(nb, n, cfg, (0.03, 0.05, 0.10))
        elif part == "C0":
            rows = part_c(nc, n, cfg, 0.0, 8)
        elif part == "C":
            rows = part_c(nc, n, cfg, 0.05, 8)
        elif part == "C3":
            rows = part_c(nc, n, cfg, 0.03, 8)
        else:
            raise SystemExit(f"unknown part {part}")
        (out / f"selfcheck_{part}.json").write_text(json.dumps(
            {"n_days": n, "step": cfg.step, "seconds": round(time.time() - t0), "rows": rows}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(summarize(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
