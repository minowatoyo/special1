"""W3 完了報告用の集計（件数・列名・ハッシュ・検証結果だけ。生の表は出さない）。

使い方: python scripts/jquants/report_w3.py [--root data/jquants]   （先に build_processed.py）
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import backfill  # noqa: E402
import schema  # noqa: E402


def main(root: Path) -> dict:
    ck = backfill.load_checkpoint(root)
    rep: dict = {"endpoints": {}}
    by = collections.defaultdict(lambda: {"ok": 0, "rows": 0, "pages": 0, "zero_rows": 0, "first": None, "last": None})
    for r in ck.values():
        e = by[r["path"]]
        e["ok"] += 1
        e["rows"] += r["rows"]
        e["pages"] += r["pages"]
        e["zero_rows"] += 1 if r.get("zero_rows") else 0
        d = r["params"].get("date")
        if d:
            e["first"] = min(filter(None, [e["first"], d]))
            e["last"] = max(filter(None, [e["last"], d]))
    fails = collections.Counter()
    log = root / "_meta" / "fetch_log.csv"
    if log.exists():
        with open(log, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["http"] != "200":
                    fails[(r["path"], r["http"])] += 1
    rep["endpoints"] = {k: dict(v) for k, v in by.items()}
    rep["non200_responses"] = {f"{p} HTTP {h}": n for (p, h), n in fails.items()}
    out = root / "processed"
    t = {}
    for name in ("prices_daily", "quality_flags", "listed_master", "fins_summary", "earnings_calendar", "topix_daily", "indices_daily"):
        f = out / f"{name}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            t[name] = {"rows": len(df), "cols": len(df.columns), "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
            if "code" in df.columns:
                t[name]["codes"] = int(df["code"].nunique())
    rep["tables"] = t
    if "prices_daily" in t:
        pr = pd.read_parquet(out / "prices_daily.parquet")
        rep["price_period"] = [str(pr["date"].min().date()), str(pr["date"].max().date())]
        rep["adjustment_mismatches"] = int(len(schema.reconcile_adjustment(pr)))
        q = pd.read_parquet(out / "quality_flags.parquet")
        rep["quality_flags"] = {c: int(q[c].sum()) for c in ("ohlc_inconsistent", "nonpositive", "no_trade", "jump_flag")}
        rep["missing"] = {c: int(pr[c].isna().sum()) for c in ("open", "close", "volume", "turnover", "adj_close")}
    size = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    rep["storage_gb"] = round(size / 1024**3, 3)
    rep["raw_manifest_sha256"] = hashlib.sha256("".join(sorted(r.get("files", [""])[0] + str(r["rows"]) for r in ck.values())).encode()).hexdigest()
    # 再開試験: 計画と完了分を突き合わせ、未完了が 0 なら再実行しても何も取らない
    topix = out / "topix_daily.parquet"
    if topix.exists():
        days = [d.date() for d in pd.read_parquet(topix)["date"]]
        todo = [j for j in backfill.plan(days) if backfill.jkey(j[0], j[1]) not in ck]
        rep["resume_check"] = {"planned": len(backfill.plan(days)), "remaining_if_rerun": len(todo)}
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1))
