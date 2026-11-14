"""Standard 固有データの取得（信用取引週末残高・業種別空売り比率・投資部門別売買状況）。ローカル PC で実行。取得と保存だけ。

  python scripts/jquants/backfill_extra.py              # 計画（通信なし）
  python scripts/jquants/backfill_extra.py --execute    # 実取得（再開可。W3 と同じチェックポイント・失敗の扱い）
  1) 信用取引週末残高: 営業日ごとに date（基準日）指定。基準日でない日は 0 行で正常。published_date 指定は古い週が取れないので使わない
     （古いデータは公表日が空のため。2026-11 の確認）
  2) 業種別空売り比率: 業種（S33）ごとに from/to 指定
  3) 投資部門別売買状況: from/to 指定
モデル入力にはしない（事前固定した除去実験を通すまで）。生データは data/jquants/raw、取得ログ・チェックポイントは W3 と共通。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import backfill as bf  # noqa: E402
from client import AuthError, Client  # noqa: E402

PRICE_PER_MIN = 100


def plan_extra(days: list, s33: list) -> list:
    jobs = [("/v2/markets/margin-interest", {"date": d.isoformat()}, PRICE_PER_MIN) for d in days]
    first, last = days[0].isoformat(), days[-1].isoformat()
    jobs += [("/v2/markets/short-ratio", {"s33": s, "from": first, "to": last}, PRICE_PER_MIN) for s in s33]
    jobs.append(("/v2/equities/investor-types", {"from": first, "to": last}, PRICE_PER_MIN))
    return jobs


def s33_list(client: Client, day: date) -> list:
    st, rows = client.get_all("/v2/markets/short-ratio", {"date": day.isoformat()}, "backfill_extra:s33-list")
    if st != 200 or not rows:
        raise RuntimeError(f"業種の一覧の取得に失敗: HTTP {st}, {len(rows)} 行")
    return sorted({r["S33"] for r in rows})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--oldest", default=None)
    ap.add_argument("--end", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    oldest = date.fromisoformat(a.oldest) if a.oldest else bf.auto_oldest(date.today())
    end = min(date.fromisoformat(a.end), bf.prev_business_day(date.today())) if a.end else bf.prev_business_day(date.today())
    n = int((end - oldest).days * 245 / 365)
    print(f"[計画] 契約最古日 {oldest}／期間 {oldest}〜{end}（営業日は概算 {n}）")
    print(f"  /v2/markets/margin-interest  約 {n} 回（営業日ごと・date）／/v2/markets/short-ratio  33〜34 回（業種ごと）／/v2/equities/investor-types  1 回")
    print(f"  合計 約 {n + 36} リクエスト／所要の目安 約 {(n + 36) / PRICE_PER_MIN:.0f} 分")
    if not a.execute:
        print("（通信なし。実取得は --execute）")
        return
    c = Client(root=root, per_min=PRICE_PER_MIN)
    try:
        print(bf.check_contract(c, oldest))
        days = bf.trading_days(c, oldest, end, oldest)
        jobs = plan_extra(days, s33_list(c, days[-1]))
        print(f"営業日 {len(days)}／全 {len(jobs)} 件")
        st = bf.run_jobs(c, jobs, root)
    except bf.ContractChanged as ex:
        sys.exit(f"停止: {ex}")
    except AuthError as ex:
        sys.exit(f"認証エラーで停止: {ex}")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    if st["stopped"]:
        sys.exit("429 で停止。再実行で続きから取得します")
    print("完了。次: python scripts/jquants/build_processed.py")


if __name__ == "__main__":
    main()
