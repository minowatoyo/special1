"""予測台帳（出した予測を記録し、期日が来たら実際の結果で採点する）。

過去データでの検証は「作り方」の採点にすぎない。出した予測そのものを後から採点して初めて、
実際の確度が分かる。台帳は CSV で、予測を出すたびに行を足す（同じ銘柄・基準日・期間・データの行は重複させない）。
"""
from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["LEDGER_COLUMNS", "append_forecast", "score_ledger"]

_Q = [("q05", 0.05), ("q10", 0.10), ("q25", 0.25), ("q50", 0.50), ("q75", 0.75), ("q90", 0.90), ("q95", 0.95)]
LEDGER_COLUMNS = (["made_utc", "asset", "asof", "h", "model", "last_close"] + [k for k, _ in _Q]
                  + ["p_up", "sigma_h", "data_sha256", "code_version"])


def append_forecast(ledger_path, fc: dict, meta: dict) -> int:
    """予測を台帳に足す。足した行数を返す。"""
    path = Path(ledger_path)
    existing = set()
    if path.exists():
        with open(path, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                existing.add((r["asset"], r["asof"], str(r["h"]), r["data_sha256"]))
    rows = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for h, hz in fc["horizons"].items():
        key = (fc["asset"], fc["asof"], str(h), meta.get("data_sha256", ""))
        if key in existing:
            continue
        q = {round(x["p"], 2): x["price"] for x in hz["quantiles"]}
        row = {"made_utc": now, "asset": fc["asset"], "asof": fc["asof"], "h": h, "model": hz["model"],
               "last_close": f"{fc['last_close']:.4f}", "p_up": f"{hz['p_up']:.4f}", "sigma_h": f"{hz['sigma_h']:.6f}",
               "data_sha256": meta.get("data_sha256", ""), "code_version": meta.get("code_version", "")}
        for k, p in _Q:
            row[k] = f"{q[p]:.4f}"
        rows.append(row)
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        with open(path, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
            if new:
                w.writeheader()
            w.writerows(rows)
    return len(rows)


def score_ledger(ledger_path, df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """期日が来た予測を採点する。df は最新の日足（index=日付、close 列）。

    採点: 実際の終値、分位点 7 点のピンボール損失の平均（対数リターン単位）、50%・80%・90% 区間に入ったか、
    上昇確率の Brier。期日がまだ来ていない行は realized が空のまま返す。
    """
    led = pd.read_csv(ledger_path, dtype={"asof": str, "asset": str}, keep_default_na=False)   # 銘柄名 "NA" などを欠損にしない
    led = led[led["asset"] == asset].copy()
    close = df["close"]
    pos = {str(d.date()): i for i, d in enumerate(df.index)}
    out = []
    for _, r in led.iterrows():
        res = {**r.to_dict(), "target_date": "", "realized": np.nan, "pinball": np.nan, "in50": np.nan,
               "in80": np.nan, "in90": np.nan, "up": np.nan, "brier_up": np.nan}
        i = pos.get(r["asof"])
        if i is not None and i + int(r["h"]) < len(close):
            c1 = float(close.iloc[i + int(r["h"])])
            c0 = float(r["last_close"])
            y = math.log(c1 / c0)
            loss = []
            for k, p in _Q:
                d = y - math.log(float(r[k]) / c0)
                loss.append(max(p * d, (p - 1.0) * d))
            up = float(c1 > c0)
            res.update({"target_date": str(df.index[i + int(r["h"])].date()), "realized": c1, "pinball": float(np.mean(loss)),
                        "in50": float(float(r["q25"]) <= c1 <= float(r["q75"])), "in80": float(float(r["q10"]) <= c1 <= float(r["q90"])),
                        "in90": float(float(r["q05"]) <= c1 <= float(r["q95"])), "up": up,
                        "brier_up": (float(r["p_up"]) - up) ** 2})
        out.append(res)
    return pd.DataFrame(out)
