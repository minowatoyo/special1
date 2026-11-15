"""TradingView AI Agent Lens のシグナルの前向きの記録（紙の上）。仕様は docs/w5_protocol.md「TradingView AI Agent Lens のシグナルの前向きの記録」。ローカル PC で実行。

  python scripts/w5/lens_log.py add --kind packet --clip               # クリップボードの、画面のパケット（JSON）を記録
  python scripts/w5/lens_log.py add --kind signal --clip               # クリップボードの、AI の出力（JSON）を記録（LONG・WAIT・SKIP のすべて）
  python scripts/w5/lens_log.py score                                  # J-Quants の日足で採点（結果が出ていないものは待つ）
  python scripts/w5/lens_log.py summary                                # 区分ごとの集計（LONG が 30 件たまるまで結論を出さない）
銘柄の一覧は、先に固定して、毎営業日の引け後に、同じ一覧を記録する（目についた銘柄だけを記録しない）。実際の売買はしない。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import forward_s2 as fs2  # noqa: E402
import schema  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402

HORIZONS = (1, 5, 21)
MIN_LONG = 30
JST = timezone(timedelta(hours=9))


def jq_code(symbol: str) -> str | None:
    """TradingView の銘柄（TSE:7203、TSE:285A など）→ J-Quants のコード（72030、285A0）。日本株でなければ None。"""
    s = str(symbol).strip().upper()
    m = re.match(r"^(?:TSE|JPX|TOKYO)[:/]([0-9][0-9A-Z]{3})(?:\.T)?$", s)
    if m:
        return m.group(1) + "0"
    m = re.match(r"^([0-9][0-9A-Z]{3})\.T$", s)
    return m.group(1) + "0" if m else None


def tf_class(tf: str) -> str:
    t = str(tf).strip().upper()
    return "daily" if t in ("D", "1D", "W", "1W", "M", "1M") else "intraday"


def jst_date(t) -> pd.Timestamp | None:
    """パケットの時刻（ISO 8601 UTC、または エポック秒・ミリ秒）→ 日本時間の日付。"""
    try:
        if isinstance(t, (int, float)) or re.fullmatch(r"\d{10,13}", str(t)):
            x = float(t)
            dt = datetime.fromtimestamp(x / 1000.0 if x > 1e11 else x, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return pd.Timestamp(dt.astimezone(JST).date())
    except Exception:  # noqa: BLE001
        return None


def key_of(d: dict) -> str:
    return f'{d.get("symbol")}|{d.get("timeframe")}|{d.get("time", d.get("packet_time"))}'


def _num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def add(root: Path, kind: str, text: str) -> dict:
    d = json.loads(text)
    if not isinstance(d, dict):
        return {"error": "JSON のオブジェクトではない"}
    ledger = AppendOnlyLedger(root / "ledger" / "lens.jsonl")
    if kind == "packet":
        if d.get("schema") != "ai-agent-lens/v1":
            return {"error": 'schema が "ai-agent-lens/v1" でない'}
        payload = {"key": key_of(d), "symbol": d.get("symbol"), "timeframe": str(d.get("timeframe")), "time": d.get("time"), "event": d.get("event"), "regime": d.get("regime"),
                   "close": _num((d.get("candle") or {}).get("close")), "scores": {k: d.get("scores", {}).get(k) for k in ("long", "short", "threshold")},
                   "trade": {k: (d.get("trade") or {}).get(k) for k in ("side", "status", "entry", "stop", "target_1", "target_2")}}
    else:
        if "decision" not in d or "symbol" not in d:
            return {"error": "AI の出力に、symbol・decision がない"}
        payload = {"key": key_of(d), "symbol": d.get("symbol"), "timeframe": str(d.get("timeframe")), "time": d.get("packet_time"), "decision": str(d.get("decision")).upper(),
                   "confidence": _num(d.get("confidence")), "entry": _num(d.get("entry")), "stop": _num(d.get("stop")), "target_1": _num(d.get("target_1")), "target_2": _num(d.get("target_2")),
                   "check": d.get("verified_context_check")}
    payload["kind"] = kind
    payload["jq_code"] = jq_code(payload["symbol"])
    if any(r["type"] == "lens_" + kind and r["payload"]["key"] == payload["key"] for r in ledger._rows()):
        return {"status": "already_recorded", "key": payload["key"]}
    if jst_date(payload["time"]) is None:
        return {"error": "時刻を読めない（ISO 8601 か、エポック）"}
    ledger.append_event("lens_" + kind, payload)
    return {"status": "recorded", "kind": kind, "key": payload["key"], "scorable_with_jquants": payload["jq_code"] is not None, "timeframe_class": tf_class(payload["timeframe"]), "ledger": ledger.verify()}


def _merged(rows: list) -> dict:
    out = {}
    for r in rows:
        if r["type"] in ("lens_packet", "lens_signal"):
            p = r["payload"]
            m = out.setdefault(p["key"], {"key": p["key"]})
            m[p["kind"]] = p
    return out


def _outcome(P, elig_cache, ci, m) -> dict | None:
    pk, sg = m.get("packet"), m.get("signal")
    base = sg or pk
    code = base.get("jq_code")
    if code is None or code not in ci:
        return {"status": "unscorable", "reason": "日本株でない、または J-Quants にない銘柄"}
    d = jst_date(base["time"])
    t = int(np.searchsorted(P.dates.values, d.to_datetime64(), side="right")) - 1
    if t < 0 or t + 2 > len(P.dates) - 1 or P.dates[-1] < d:
        return None
    j = ci[code]
    if t not in elig_cache:
        elig_cache[t] = P.eligible(m["_iv"], schema.WIDE_MARKETS, [t], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
    res = {"status": "scored", "signal_trading_day": str(P.dates[t].date()), "buy_day": str(P.dates[t + 1].date()), "returns": {}}
    for h in HORIZONS:
        if t + 1 + h >= len(P.dates):
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            f = P.adj_open[t + 1 + h] / P.adj_open[t + 1] - 1.0
        um = float(np.nanmean(np.where(elig_cache[t], f, np.nan)))
        if np.isfinite(f[j]):
            res["returns"][str(h)] = {"ret": round(float(f[j]), 5), "excess": round(float(f[j] - um), 5)}
    entry = (sg or {}).get("entry") or (pk or {}).get("close")
    if entry and np.isfinite(P.raw_close[t, j]) and P.raw_close[t, j] > 0 and np.isfinite(P.adj_close[t, j]):
        res["same_day_close_vs_packet_price"] = round(float(P.raw_close[t, j] / entry - 1.0), 5)
    ratio = P.adj_close[t, j] / P.raw_close[t, j] if P.raw_close[t, j] > 0 else np.nan
    src = {k: (sg or {}).get(k) or ((pk or {}).get("trade") or {}).get(k) for k in ("stop", "target_1", "target_2")}
    side = ((pk or {}).get("trade") or {}).get("side") or ("LONG" if (sg or {}).get("decision") == "LONG" else None)
    if side == "LONG" and src["stop"] and src["target_1"] and np.isfinite(ratio) and t + 1 + 21 < len(P.dates):
        stop, t1, t2 = (src[k] * ratio if src[k] else None for k in ("stop", "target_1", "target_2"))
        result, day = "none", None
        for k in range(1, 22):
            o, hi, lo = P.adj_open[t + k, j], P.adj_high[t + k, j], P.adj_low[t + k, j]
            if not np.isfinite(hi):
                continue
            hit_stop = lo <= stop or o <= stop
            hit_t1 = hi >= t1 or o >= t1
            hit_t2 = t2 is not None and (hi >= t2 or o >= t2)
            if hit_stop and (hit_t1 or hit_t2):
                result, day = "ambiguous(stop_first)", k
            elif hit_stop:
                result, day = "stop", k
            elif hit_t2:
                result, day = "target_2", k
            elif hit_t1:
                result, day = "target_1", k
            if day:
                break
        res["indicator_trade_21d"] = {"result": result, "day": day}
    return res


def score(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "lens.jsonl")
    rows = ledger._rows()
    done = {r["payload"]["key"] for r in rows if r["type"] == "lens_outcome" and r["payload"].get("final")}
    merged = {k: v for k, v in _merged(rows).items() if k not in done}
    if not merged:
        return {"scored_final": 0, "pending": 0, "ledger": ledger.verify()}
    P, iv, _ = fs2.load_panel(root, None)
    ci = {c: i for i, c in enumerate(P.codes)}
    cache = {}
    n_final = pending = unscorable = 0
    for k, m in merged.items():
        m["_iv"] = iv
        o = _outcome(P, cache, ci, m)
        if o is None:
            pending += 1
            continue
        if o["status"] == "unscorable":
            ledger.append_event("lens_outcome", {"key": k, "final": True, **o})
            unscorable += 1
            continue
        if "21" not in o["returns"]:
            pending += 1
            continue
        ledger.append_event("lens_outcome", {"key": k, "final": True, "decision": (m.get("signal") or {}).get("decision"), "timeframe_class": tf_class((m.get("signal") or m.get("packet"))["timeframe"]),
                                              "event": (m.get("packet") or {}).get("event"), "regime": (m.get("packet") or {}).get("regime"), **o})
        n_final += 1
    return {"scored_final": n_final, "unscorable": unscorable, "pending": pending, "ledger": ledger.verify()}


def summary(root: Path) -> dict:
    ledger = AppendOnlyLedger(root / "ledger" / "lens.jsonl")
    rows = ledger._rows()
    outs = [r["payload"] for r in rows if r["type"] == "lens_outcome" and r["payload"].get("status") == "scored"]
    merged = _merged(rows)
    res = {"packets": sum(1 for r in rows if r["type"] == "lens_packet"), "signals": sum(1 for r in rows if r["type"] == "lens_signal"),
           "scored": len(outs), "unscorable": sum(1 for r in rows if r["type"] == "lens_outcome" and r["payload"].get("status") == "unscorable"), "groups": {}}
    for cls in ("daily", "intraday"):
        g = {}
        for dec in ("LONG", "WAIT", "SKIP"):
            sel = [o for o in outs if o.get("timeframe_class") == cls and o.get("decision") == dec]
            if not sel:
                continue
            d = {"n": len(sel)}
            for h in ("1", "5", "21"):
                x = np.array([o["returns"][h]["excess"] for o in sel if h in o["returns"]], dtype=float)
                if len(x):
                    d[f"excess_{h}d"] = {"mean": round(float(x.mean()), 4), "share_positive": round(float((x > 0).mean()), 2),
                                         "t": round(float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))), 2) if len(x) > 2 and x.std(ddof=1) > 0 else None}
            tr = [o["indicator_trade_21d"]["result"] for o in sel if "indicator_trade_21d" in o]
            if tr:
                d["indicator_trade_21d"] = {r: tr.count(r) for r in sorted(set(tr))}
            g[dec] = d
        if "LONG" in g:
            non = [o for o in outs if o.get("timeframe_class") == cls and o.get("decision") in ("WAIT", "SKIP")]
            lg = np.array([o["returns"]["21"]["excess"] for o in outs if o.get("timeframe_class") == cls and o.get("decision") == "LONG" and "21" in o["returns"]], dtype=float)
            nn = np.array([o["returns"]["21"]["excess"] for o in non if "21" in o["returns"]], dtype=float)
            g["LONG_minus_nonLONG_21d"] = round(float(lg.mean() - nn.mean()), 4) if len(lg) and len(nn) else None
            g["conclusion"] = f"LONG が {len(lg)} 件。{MIN_LONG} 件たまるまで、結論を出さない" if len(lg) < MIN_LONG else "LONG が 30 件以上（それでも、標本は小さい）。事前の基準で判断する"
        res["groups"][cls] = g
    res["ledger"] = ledger.verify()
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "score", "summary"])
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--kind", choices=["packet", "signal"])
    ap.add_argument("--file", help="JSON のファイル。省略すると、標準入力")
    ap.add_argument("--clip", action="store_true", help="Windows のクリップボードから読む（日本語の文字化けを避けられる。標準入力より確実）")
    a = ap.parse_args()
    root = Path(a.root)
    if a.cmd == "add":
        if not a.kind:
            sys.exit("--kind packet|signal が必要")
        text = Path(a.file).read_text(encoding="utf-8-sig") if a.file else sys.stdin.read().lstrip("﻿")
        r = add(root, a.kind, text)
    else:
        r = score(root) if a.cmd == "score" else summary(root)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
