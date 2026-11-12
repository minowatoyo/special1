"""data/jquants/raw の応答を、加工後テーブル（Parquet）にまとめる。生データは変更しない。

使い方: python scripts/jquants/build_processed.py [--root data/jquants]
出力は件数・列数・ハッシュだけ（中身は表示しない）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import schema


def rows_of(root: Path, slug: str):
    for f in sorted((root / "raw" / slug).glob("**/*.json")):
        try:
            js = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for k, v in (js or {}).items():
            if isinstance(v, list):
                yield f, v


def main(root: Path) -> dict:
    out = root / "processed"
    out.mkdir(parents=True, exist_ok=True)
    rep = {}

    def save(name, df):
        p = out / f"{name}.parquet"
        df.to_parquet(p, index=False)
        rep[name] = {"rows": len(df), "cols": len(df.columns), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16]}

    prices = [r for _, rows in rows_of(root, "v2_equities_bars_daily") for r in rows]
    if prices:
        pr = schema.normalize_prices(prices)
        save("prices_daily", pr)
        save("quality_flags", schema.quality_flags(pr))
        bad = schema.reconcile_adjustment(pr)
        rep["adjustment_reconciliation_mismatches"] = len(bad)
    masters = [schema.normalize_master(rows) for _, rows in rows_of(root, "v2_equities_master")]
    if masters:
        save("listed_master", pd.concat(masters).drop_duplicates(["asof", "code"], keep="last").reset_index(drop=True))
    tp = [r for _, rows in rows_of(root, "v2_indices_bars_daily_topix") for r in rows]
    cal = None
    if tp:
        t = schema.normalize_index(tp, "TOPIX")
        save("topix_daily", t)
        cal = t["date"]
    ix = [r for _, rows in rows_of(root, "v2_indices_bars_daily") for r in rows]
    if ix:
        save("indices_daily", schema.normalize_index(ix))
    ec = []
    for f, rows in rows_of(root, "v2_equities_earnings-calendar"):
        ec.append(schema.normalize_calendar(rows, f.parent.name))
    if ec:
        save("earnings_calendar", pd.concat(ec).reset_index(drop=True))
    fs = [r for _, rows in rows_of(root, "v2_fins_summary") for r in rows]
    if fs:
        days = cal if cal is not None else (pr["date"].drop_duplicates() if prices else pd.Series(dtype="datetime64[ns]"))
        save("fins_summary", schema.normalize_fins(fs, days))
    for name, cols in schema.EMPTY_SLOTS.items():
        save(name, pd.DataFrame(columns=cols))
    (out / "_build_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1))
