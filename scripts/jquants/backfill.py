"""W3 本番バックフィル（取得と保存だけ）。利用者のローカル PC で実行する。共有セッションでは実行しない。

取得は母集団で絞らない。日付指定の全銘柄データを保存し、普通株・市場区分・流動性のフィルタは後段（schema.universe）で適用する。
  1) TOPIX 日足で営業日を決める  2) 銘柄日足: 営業日ごと・全銘柄（1 リクエスト／日）  3) 上場銘柄表: 営業日ごとの日次スナップショット
  4) 財務サマリー: 営業日ごと  5) 指数日足: 営業日ごと  6) 決算発表予定（版として 1 回）
実行前に契約上の取得可能期間を再確認する。利用者が --oldest で明示した最古日（既定 2016-11-12）と違えば、開始日を変えずに停止して報告する。契約期間は実行日の 10 年前から始まる窓で、日々ずれる。
チェックポイント（_meta/checkpoint.jsonl）は、1 件の取得が全ページそろって成功した後にだけ追記する。失敗は未完了のまま残り、
正常な 0 行とは区別される（銘柄日足・上場銘柄表・指数が営業日に 0 行なら失敗扱い）。再実行は未完了分だけを取る。429 が出たら停止する。
終了日は実行日の前営業日（当日分は未確定）。3 周しても解消しない日は全体を止めず「要調査」（_meta/investigate.jsonl）に記録して残りを進める。
上場銘柄表・銘柄日足・指数は、返った日付が要求日と一致するか検証し、不一致は date_mismatch として記録する。

  python scripts/jquants/backfill.py              # 計画（期間・エンドポイント・リクエスト数・所要時間・容量）だけ表示。通信なし
  python scripts/jquants/backfill.py --execute    # 実取得（鍵は環境変数 JQUANTS_API_KEY）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from client import AuthError, Client  # noqa: E402

OLDEST = date(2016, 11, 12)                 # W2 の実測（Standard の契約期間の最古日）
PRICE_PER_MIN, FINS_PER_MIN = 100, 55
MAX_PASSES = 3
# 1 日あたりの生データの目安（W2 の実測の最大値に近い値）
MB_PER_DAY = {"/v2/equities/bars/daily": 1.2, "/v2/equities/master": 1.5, "/v2/fins/summary": 0.3, "/v2/indices/bars/daily": 0.01}
MUST_HAVE_ROWS = {"/v2/equities/bars/daily", "/v2/equities/master", "/v2/indices/bars/daily", "/v2/equities/earnings-calendar"}
CAL_PATH = "/v2/indices/bars/daily/topix"
DATE_CHECKED = {"/v2/equities/master", "/v2/equities/bars/daily", "/v2/indices/bars/daily"}


class ContractChanged(RuntimeError):
    pass


def jkey(path: str, params: dict) -> str:
    return path + "?" + json.dumps(params, sort_keys=True)


def load_checkpoint(root: Path) -> dict:
    p = root / "_meta" / "checkpoint.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue                          # 途中で切れた最後の行は無視（その件は未完了として再取得）
            out[jkey(r["path"], r["params"])] = r
    return out


def append_checkpoint(root: Path, rec: dict) -> None:
    p = root / "_meta" / "checkpoint.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def prev_business_day(today: date) -> date:
    """実行日の前営業日（土日を除く。祝日は後段の TOPIX 営業日で自然に落ちる）。当日分は未確定なので取得しない。"""
    d = date.fromordinal(today.toordinal() - 1)
    while d.weekday() >= 5:
        d = date.fromordinal(d.toordinal() - 1)
    return d


def log_investigate(root: Path, path: str, params: dict, reason: str, detail: str = "") -> None:
    p = root / "_meta" / "investigate.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"path": path, "date": params.get("date"), "reason": reason, "detail": detail,
                             "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def load_investigate(root: Path) -> list:
    p = root / "_meta" / "investigate.jsonl"
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def date_mismatches(path: str, params: dict, rows: list) -> int:
    """返ってきた行の日付が要求日と一致しない件数（銘柄日足・上場銘柄表・指数日足）。"""
    if path not in DATE_CHECKED or not params.get("date"):
        return 0
    return sum(1 for r in rows if str(r.get("Date", ""))[:10] != params["date"])


def check_contract(client: Client, oldest: date = OLDEST) -> str:
    """契約上の最古日を再確認する。最古日の前日を問い合わせ、400 かつ案内が最古日と一致することを期待する。"""
    prev = date.fromordinal(oldest.toordinal() - 1).isoformat()
    st, js, _ = client.get_page("/v2/equities/bars/daily", {"date": prev}, "backfill:contract-check")
    msg = json.dumps(js, ensure_ascii=False) if js is not None else ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s*~", msg)
    if st == 400 and m and m.group(1) == oldest.isoformat():
        return f"契約期間の最古日 {oldest}（実測と一致）"
    raise ContractChanged(f"契約期間が実測({oldest})と一致しない: 前日 {prev} の応答 HTTP {st}, 案内の開始日 {m.group(1) if m else '不明'}。開始日は変更せず停止")


def trading_days(client: Client, start: date, end: date, oldest: date = OLDEST) -> list[date]:
    st, rows = client.get_all(CAL_PATH, {"from": start.isoformat(), "to": end.isoformat()}, "backfill:calendar")
    if st != 200 or not rows:
        raise RuntimeError(f"営業日（TOPIX）の取得に失敗: HTTP {st}, {len(rows)} 行")
    days = sorted({date.fromisoformat(r["Date"]) for r in rows})
    if days[0] < oldest:
        raise ContractChanged("契約期間より前の日が含まれる")
    return days


def plan(days: list[date]) -> list[tuple[str, dict, int]]:
    jobs = []
    for path, per in (("/v2/equities/bars/daily", PRICE_PER_MIN), ("/v2/equities/master", PRICE_PER_MIN),
                      ("/v2/indices/bars/daily", PRICE_PER_MIN), ("/v2/fins/summary", FINS_PER_MIN)):
        jobs += [(path, {"date": d.isoformat()}, per) for d in days]
    jobs.append(("/v2/equities/earnings-calendar", {}, PRICE_PER_MIN))
    return jobs


def estimate(n_days: int) -> dict:
    per_ep = {p: n_days for p in MB_PER_DAY}
    reqs = sum(per_ep.values()) + 1 + 2           # 決算予定 1、営業日の取得と契約確認 2（ページ分割がなければ）
    minutes = (n_days * 3 + 3) / PRICE_PER_MIN + n_days / FINS_PER_MIN
    gb = sum(MB_PER_DAY[p] * n_days for p in MB_PER_DAY) / 1024
    return {"endpoints": per_ep, "requests": reqs, "minutes": minutes, "raw_gb": gb}


def run_jobs(client: Client, jobs: list, root: Path, sleep=time.sleep) -> dict:
    """未完了の件だけを取る。成功（全ページ・必要なら 1 行以上）の後にだけチェックポイントを追記する。"""
    ckpt = load_checkpoint(root)
    stats = {"done_before": 0, "ok": 0, "fail": {}, "rows": {}, "pages": {}, "zero_rows_accepted": 0, "stopped": ""}
    todo = [j for j in jobs if jkey(j[0], j[1]) not in ckpt]
    stats["done_before"] = len(jobs) - len(todo)
    for attempt in range(MAX_PASSES):
        failed = []
        for path, params, per_min in todo:
            client.limiter.gap = 60.0 / per_min
            st, rows = client.get_all(path, params, f"backfill:pass{attempt + 1}")
            if st == 429:
                stats["stopped"] = "429 のため停止（再実行で続きから）"
                stats["fail"][path] = stats["fail"].get(path, 0) + 1
                return stats
            bad = st != 200 or (path in MUST_HAVE_ROWS and not rows)
            if bad:
                failed.append((path, params, per_min))
                continue
            rec = {"path": path, "params": params, "rows": len(rows), "pages": client.last_pages, "files": client.last_files,
                   "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            if not rows:
                rec["zero_rows"] = True
                stats["zero_rows_accepted"] += 1
            mm = date_mismatches(path, params, rows)
            if mm:
                rec["date_mismatch"] = mm
                stats["date_mismatch"] = stats.get("date_mismatch", 0) + 1
                log_investigate(root, path, params, "date_mismatch", f"{mm}/{len(rows)} 行の日付が要求日と不一致")
            append_checkpoint(root, rec)
            stats["ok"] += 1
            stats["rows"][path] = stats["rows"].get(path, 0) + len(rows)
            stats["pages"][path] = stats["pages"].get(path, 0) + client.last_pages
        todo = failed
        if not todo:
            break
        sleep(30)
    for path, params, _ in todo:
        stats["fail"][path] = stats["fail"].get(path, 0) + 1
        log_investigate(root, path, params, "unresolved_after_retries", "0 行または HTTP 失敗が 3 周しても解消しない")
    stats["failed_jobs"] = [jkey(p, q) for p, q, _ in todo]
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--oldest", default=OLDEST.isoformat(),
                    help="契約上の最古日（利用者が明示する。契約期間は実行日の 10 年前から始まる窓で、日々ずれる）。開始日の既定にもなる")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None, help="既定は実行日の前営業日。それより後は指定できない")
    a = ap.parse_args()
    root = Path(a.root)
    oldest = date.fromisoformat(a.oldest)
    start = date.fromisoformat(a.start) if a.start else oldest
    last_ok = prev_business_day(date.today())
    end = min(date.fromisoformat(a.end), last_ok) if a.end else last_ok
    if start < oldest:
        sys.exit(f"開始日は {oldest} 以降（契約期間）")
    n_days = int((end - start).days * 245 / 365)
    e = estimate(n_days)
    print(f"[計画] 期間 {start}〜{end}（営業日は概算 {n_days}、実行時に TOPIX で確定）")
    for p, n in e["endpoints"].items():
        print(f"  {p}  {n} 回（全銘柄・日付指定）")
    print("  /v2/equities/earnings-calendar  1 回（上場銘柄表は営業日ごとの日次スナップショット）。ほか営業日の取得・契約確認 2 回")
    print(f"  合計 約 {e['requests']} リクエスト／所要の目安 約 {e['minutes']:.0f} 分（{PRICE_PER_MIN}回/分、財務は {FINS_PER_MIN}回/分）／生データ 約 {e['raw_gb']:.1f} GB")
    if not a.execute:
        print("（通信なし。実取得は --execute）")
        return
    root.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(root).free / 1024**3
    if free < e["raw_gb"] * 1.5:
        sys.exit(f"空き容量が足りない: {free:.1f} GB（必要の目安 {e['raw_gb'] * 1.5:.1f} GB）")
    c = Client(root=root, per_min=PRICE_PER_MIN)
    try:
        print(check_contract(c, oldest))
        days = trading_days(c, start, end, oldest)
        jobs = plan(days)
        print(f"営業日 {len(days)}／全 {len(jobs)} 件")
        st = run_jobs(c, jobs, root)
    except ContractChanged as ex:
        sys.exit(f"停止: {ex}")
    except AuthError as ex:
        sys.exit(f"認証エラーで停止: {ex}")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    if st["stopped"]:
        sys.exit("429 で停止。再実行で続きから取得します")
    if st["fail"] or st.get("date_mismatch"):
        print("要調査の日付あり（_meta/investigate.jsonl。report_w3.py に一覧）。残りの取得は完了。")
    print("完了。次: python scripts/jquants/build_processed.py && python scripts/jquants/report_w3.py")


if __name__ == "__main__":
    main()
