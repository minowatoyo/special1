"""W3 本番バックフィル（10 年分）。利用者のローカル PC で実行する。W2 時点では dry-run だけ（--execute を付けるまで通信しない）。

窓の最古日は 2016-11-12（W2 の実測。Standard の契約期間。それより前は HTTP 400）。営業日は TOPIX 日足から決める。
  1) TOPIX 日足（窓全体を 1〜数回）  2) 銘柄日足: 営業日ごとに全銘柄（date 指定。1 リクエスト／日、ページ分割なし）
  3) 財務サマリー: 営業日ごと（date 指定。1 リクエスト／日）  4) 上場銘柄表: 月初の営業日ごと（date 指定）
  5) 指数日足（date 指定）  6) 決算発表予定（版として 1 回）
再開: 取得ログ（_meta/fetch_log.csv）に 200 で記録済みの (パス, パラメータ) は飛ばす。レート制限は --per-min（既定 100。財務は 55）。
鍵: 環境変数 JQUANTS_API_KEY。生データは data/jquants/raw に保存。会話・レポートには件数・ハッシュだけを出す。

  python scripts/jquants/backfill.py              # 計画（リクエスト数・所要時間の見積もり）だけ表示
  python scripts/jquants/backfill.py --execute    # 実取得
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from client import AuthError, Client  # noqa: E402

OLDEST = date(2016, 11, 12)
PRICE_PER_MIN, FINS_PER_MIN = 100, 55


def done_set(root: Path) -> set:
    p = root / "_meta" / "fetch_log.csv"
    s = set()
    if p.exists():
        with open(p, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["http"] == "200":
                    s.add((r["path"], r["params"]))
    return s


def key(path: str, params: dict) -> tuple:
    return (path, json.dumps(params, sort_keys=True))


def trading_days(client: Client, start: date, end: date) -> list[date]:
    days: list[date] = []
    st, rows = client.get_all("/v2/indices/bars/daily/topix", {"from": start.isoformat(), "to": end.isoformat()}, "backfill:calendar")
    if st != 200:
        raise RuntimeError(f"TOPIX の取得に失敗: HTTP {st}")
    for r in rows:
        days.append(date.fromisoformat(r["Date"]))
    return sorted(set(days))


def plan(days: list[date]) -> list[tuple[str, dict, int]]:
    months = sorted({(d.year, d.month) for d in days})
    firsts = [min(d for d in days if (d.year, d.month) == m) for m in months]
    jobs = [("/v2/equities/bars/daily", {"date": d.isoformat()}, PRICE_PER_MIN) for d in days]
    jobs += [("/v2/fins/summary", {"date": d.isoformat()}, FINS_PER_MIN) for d in days]
    jobs += [("/v2/equities/master", {"date": d.isoformat()}, PRICE_PER_MIN) for d in firsts]
    jobs += [("/v2/indices/bars/daily", {"date": d.isoformat()}, PRICE_PER_MIN) for d in days]
    jobs += [("/v2/equities/earnings-calendar", {}, PRICE_PER_MIN)]
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--start", default=OLDEST.isoformat())
    ap.add_argument("--end", default=date.today().isoformat())
    a = ap.parse_args()
    root = Path(a.root)
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    if start < OLDEST:
        sys.exit(f"開始日は {OLDEST} 以降（Standard の契約期間）")
    if not a.execute:
        n_days = int((end - start).days * 245 / 365)           # 営業日の概算（実行時は TOPIX で確定）
        reqs = {"prices": n_days, "fins": n_days, "master": (end.year - start.year) * 12 + 12, "indices": n_days, "calendar": 1}
        minutes = (reqs["prices"] + reqs["master"] + reqs["indices"] + 1) / PRICE_PER_MIN + reqs["fins"] / FINS_PER_MIN
        print(f"[計画] 期間 {start}〜{end}／概算の営業日 {n_days}／リクエスト {sum(reqs.values())} 回 {reqs}／所要の目安 約 {minutes:.0f} 分（通信なし）")
        return
    c = Client(root=root, per_min=PRICE_PER_MIN)
    days = trading_days(c, start, end)
    jobs, seen = plan(days), done_set(root)
    todo = [j for j in jobs if key(j[0], j[1]) not in seen]
    print(f"営業日 {len(days)}／全 {len(jobs)} 件／未取得 {len(todo)} 件")
    bad = 0
    try:
        for i, (path, params, per_min) in enumerate(todo, 1):
            c.limiter.gap = 60.0 / per_min
            st, rows = c.get_all(path, params, "backfill")
            if st != 200:
                bad += 1
                print(f"HTTP {st}: {path} {params}")
                if st == 429 or bad >= 20:
                    sys.exit("429 または失敗が続いたので停止（再実行で続きから再開）")
            if i % 200 == 0:
                print(f"{i}/{len(todo)}")
    except AuthError as e:
        sys.exit(f"認証エラーで停止: {e}")
    print("完了。次: python scripts/jquants/build_processed.py")


if __name__ == "__main__":
    main()
