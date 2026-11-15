"""TradingAgents に見せる銘柄の、毎営業日の無作為抽出（売買代金の段階ごとに同数）。仕様は docs/w5_protocol.md「TradingAgents を、全銘柄（一般株式）に広げる」。ローカル PC で実行。

  python scripts/w5/agents_sample.py draw --n 9                 # 今日（日本時間）の抽出。tools/tradingagents_bridge/today.txt に書き、台帳に記録
抽出の結果は、実行する前に、台帳に記録する。同じ日は 1 回だけ（再実行しても、同じ一覧を書き直すだけ）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import forward_s2 as fs2  # noqa: E402
import schema  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402

JST = timezone(timedelta(hours=9))
TIERS = (("A_ge500M", 5e8, np.inf), ("B_50M_500M", 5e7, 5e8), ("C_20M_50M", 2e7, 5e7))
EXCLUDE_DAYS = 30


def ticker_of(code: str) -> str:
    return str(code)[:4] + ".T"


def draw(root: Path, n: int, date: str | None = None, va_min: float = 2e7, write_file: Path | None = None) -> dict:
    date = date or datetime.now(JST).strftime("%Y-%m-%d")
    ledger = AppendOnlyLedger(root / "ledger" / "agents.jsonl")
    rows = ledger._rows()
    for r in rows:
        if r["type"] == "agents_draw" and r["payload"]["date"] == date:
            res = {"status": "already_drawn", **r["payload"]}
            if write_file:
                write_file.write_text("\n".join(t for ts in r["payload"]["tickers"].values() for t in ts) + "\n", encoding="utf-8")
            return res
    P, iv, _ = fs2.load_panel(root, None)
    T = len(P.dates) - 1
    elig = P.eligible(iv, schema.WIDE_MARKETS, [T], min_history=250, va_min=va_min)[0]
    va = P.va60()[T]
    recent = set()
    cutoff = datetime.fromisoformat(date) - timedelta(days=EXCLUDE_DAYS)
    for r in rows:
        if r["type"] == "agents_draw" and datetime.fromisoformat(r["payload"]["date"]) >= cutoff:
            recent |= {t for ts in r["payload"]["tickers"].values() for t in ts}
    seed = int(hashlib.sha256(f"{date}|agents-draw-v1".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)
    per, extra = divmod(n, len(TIERS))
    tickers, frame = {}, {}
    for k, (name, lo, hi) in enumerate(TIERS):
        idx = [j for j in np.flatnonzero(elig & (va >= lo) & (va < hi)) if ticker_of(P.codes[j]) not in recent]
        cand = sorted(ticker_of(P.codes[j]) for j in idx)
        frame[name] = len(cand)
        m = per + (1 if k < extra else 0)
        tickers[name] = sorted(rng.choice(cand, size=min(m, len(cand)), replace=False).tolist()) if cand else []
    payload = {"date": date, "data_asof": str(P.dates[T].date()), "seed": seed, "n_requested": n, "frame_size": frame, "excluded_recent": len(recent), "tickers": tickers}
    ledger.append_event("agents_draw", payload)
    if write_file:
        write_file.write_text("\n".join(t for ts in tickers.values() for t in ts) + "\n", encoding="utf-8")
    return {"status": "drawn", **payload, "ledger": ledger.verify()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draw"])
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--n", type=int, default=9, help="1 日の抽出数（段階 A・B・C に、同数ずつ）")
    ap.add_argument("--date")
    ap.add_argument("--out", default="tools/tradingagents_bridge/today.txt")
    a = ap.parse_args()
    r = draw(Path(a.root), a.n, a.date, write_file=Path(a.out))
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
