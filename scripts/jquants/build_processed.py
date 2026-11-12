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


EXCLUDED: dict = {}
DATE_CHECKED_SLUGS = {"v2_equities_master", "v2_equities_bars_daily", "v2_indices_bars_daily"}


def checkpoint_files(root: Path):
    """完了した取得のページ → 要求日（日付指定でない取得は None）。チェックポイントがなければ None。"""
    p = root / "_meta" / "checkpoint.jsonl"
    if not p.exists():
        return None
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        for x in r.get("files", []):
            out[Path(x).resolve()] = r.get("params", {}).get("date")
    return out


def rows_of(root: Path, slug: str):
    """チェックポイントがあれば、完了した取得のページだけを使う（失敗・途中のページは使わない）。
    日付指定の取得（銘柄日足・上場銘柄表・指数日足）は、返った日付が要求日と違う行を加工に入れない（date_mismatch。
    生データには残る）。除外した行数は EXCLUDED に数え、_build_report.json に出す。"""
    only = checkpoint_files(root)
    for f in sorted((root / "raw" / slug).glob("**/*.json")):
        if only is not None and f.resolve() not in only:
            continue
        try:
            js = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        want = only.get(f.resolve()) if only is not None else None
        for k, v in (js or {}).items():
            if isinstance(v, list):
                if want and slug in DATE_CHECKED_SLUGS:
                    keep = [r for r in v if str(r.get("Date", ""))[:10] == want]
                    if len(keep) != len(v):
                        EXCLUDED[slug] = EXCLUDED.get(slug, 0) + len(v) - len(keep)
                    v = keep
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
    tp = [r for _, rows in rows_of(root, "v2_indices_bars_daily_topix") for r in rows]
    cal = None
    if tp:
        t = schema.normalize_index(tp, "TOPIX")
        save("topix_daily", t)
        cal = t["date"]
    if masters:
        md = pd.concat(masters).drop_duplicates(["asof", "code"], keep="last").reset_index(drop=True)
        rep["listed_master_snapshots"] = int(md["asof"].nunique())
        save("listed_master", schema.master_intervals(md, cal if cal is not None else md["asof"]))
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
    rep["excluded_date_mismatch_rows"] = dict(EXCLUDED)
    (out / "_build_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    print(json.dumps(main(Path(ap.parse_args().root)), ensure_ascii=False, indent=1))
