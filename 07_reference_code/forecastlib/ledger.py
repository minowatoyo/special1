"""予測台帳（出した予測を記録し、期日が来たら実際の結果で採点する）。

過去データでの検証は「作り方」の採点にすぎない。出した予測そのものを後から採点して初めて、
実際の確度が分かる。台帳は CSV で、予測を出すたびに行を足す（同じ銘柄・基準日・期間・データの行は重複させない）。
"""
from __future__ import annotations

import csv
import os
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


# ---------------------------------------------------------------------------------------------
# 追記専用の予測台帳（改訂仕様 FIX-08）。J-Quants 正本のデータだけから作った予測を、ハッシュ連鎖で記録する。
#   * 行は追記のみ（書き換え・削除は検出される: 各行が直前の行のハッシュを含む）
#   * 予測の行（forecast）と、期日後の採点の行（outcome）は別の行。採点は予測の行を変えない
#   * 暫定（異種ソース混在）のデータからの予測は記録しない（source が "jquants" でなければ拒否）
#   * 置き場は data/jquants/ledger/（J-Quants 由来の派生物。解約時の全消去に含まれる）
# ---------------------------------------------------------------------------------------------
import hashlib
import json

__all__ = ["AppendOnlyLedger", "LedgerError"]
GENESIS = "0" * 64
SOURCE_OK = "jquants"


class LedgerError(RuntimeError):
    pass


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class AppendOnlyLedger:
    def __init__(self, path):
        self.path = Path(path)

    def _rows(self) -> list:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    @staticmethod
    def _hash(prev: str, typ: str, payload: dict) -> str:
        return hashlib.sha256((prev + typ + _canon(payload)).encode("utf-8")).hexdigest()

    def verify(self) -> dict:
        """連鎖を検証する。戻り値: {ok, rows, first_bad}（先頭から数えた最初の不整合の行番号。なければ None）。"""
        prev, n = GENESIS, 0
        for i, r in enumerate(self._rows()):
            n += 1
            if r.get("seq") != i or r.get("prev") != prev or r.get("hash") != self._hash(prev, r["type"], r["payload"]):
                return {"ok": False, "rows": n, "first_bad": i}
            prev = r["hash"]
        return {"ok": True, "rows": n, "first_bad": None}

    def _append(self, typ: str, payload: dict) -> dict:
        v = self.verify()
        if not v["ok"]:
            raise LedgerError(f"台帳の連鎖が壊れている（{v['first_bad']} 行目）。追記しない")
        rows = self._rows()
        prev = rows[-1]["hash"] if rows else GENESIS
        row = {"seq": len(rows), "prev": prev, "type": typ, "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "payload": payload}
        row["hash"] = self._hash(prev, typ, payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            fh.write(_canon(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return row

    def append_event(self, typ: str, payload: dict) -> dict:
        """任意の種類の行（例: trial）を追記する。連鎖と追記専用は同じ。"""
        return self._append(typ, payload)

    def append_forecast(self, fc: dict, meta: dict) -> list:
        """forecast.final_forecast の出力を足す。meta: source（"jquants" 必須）、data_manifest_sha256、code_version、config_sha256。
        同じ (asset, asof, h, data_manifest_sha256) は足さない。戻り値は足した行。"""
        if meta.get("source") != SOURCE_OK:
            raise LedgerError("J-Quants 正本以外（または暫定）のデータから作った予測は、台帳に記録しない")
        for k in ("data_manifest_sha256", "code_version", "config_sha256"):
            if not meta.get(k):
                raise LedgerError(f"meta に {k} が必要（予測を後から再現できるように）")
        have = {(r["payload"]["asset"], r["payload"]["asof"], r["payload"]["h"], r["payload"]["data_manifest_sha256"])
                for r in self._rows() if r["type"] == "forecast"}
        added = []
        for h, hz in fc["horizons"].items():
            key = (fc["asset"], fc["asof"], int(h), meta["data_manifest_sha256"])
            if key in have:
                continue
            payload = {"asset": fc["asset"], "asof": fc["asof"], "h": int(h), "model": hz["model"], "last_close": float(fc["last_close"]),
                       "quantiles": {f"{x['p']:.2f}": float(x["price"]) for x in hz["quantiles"]}, "p_up": float(hz["p_up"]),
                       "sigma_h": float(hz["sigma_h"]), "source": SOURCE_OK, "data_manifest_sha256": meta["data_manifest_sha256"],
                       "code_version": meta["code_version"], "config_sha256": meta["config_sha256"]}
            added.append(self._append("forecast", payload))
        return added

    def score(self, df: pd.DataFrame, asset: str) -> list:
        """期日が来た予測を採点し、outcome の行として追記する（予測の行は変えない。採点済みは飛ばす）。df は日足（index=日付、close 列）。"""
        rows = self._rows()
        done = {r["payload"]["forecast_hash"] for r in rows if r["type"] == "outcome"}
        pos = {str(d.date()): i for i, d in enumerate(df.index)}
        added = []
        for r in rows:
            if r["type"] != "forecast" or r["hash"] in done or r["payload"]["asset"] != asset:
                continue
            p = r["payload"]
            i = pos.get(p["asof"])
            if i is None or i + p["h"] >= len(df):
                continue
            c1, c0 = float(df["close"].iloc[i + p["h"]]), p["last_close"]
            y = math.log(c1 / c0)
            loss = []
            for tau, price in p["quantiles"].items():
                d = y - math.log(price / c0)
                t = float(tau)
                loss.append(max(t * d, (t - 1.0) * d))
            q = p["quantiles"]
            payload = {"forecast_hash": r["hash"], "asset": asset, "target_date": str(df.index[i + p["h"]].date()), "realized_close": c1,
                       "pinball": float(np.mean(loss)), "in80": bool(q["0.10"] <= c1 <= q["0.90"]), "up": bool(c1 > c0),
                       "brier_up": float((p["p_up"] - float(c1 > c0)) ** 2)}
            added.append(self._append("outcome", payload))
        return added
