"""AI Agent Lens のシグナルの前向きの記録（合成データ）。記号の変換、時刻、二重記録の防止、採点（超過・損切り/利確・未成熟は待つ）、集計。"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_rules import _write_processed
from test_seasonal import seasonal_panel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
import lens_log as ll  # noqa: E402


def test_symbol_time_and_class_helpers():
    assert ll.jq_code("TSE:7203") == "72030" and ll.jq_code("TSE:285A") == "285A0" and ll.jq_code("7203.T") == "72030"
    assert ll.jq_code("BINANCE:BTCUSDT") is None and ll.jq_code("NASDAQ:AAPL") is None
    assert ll.tf_class("D") == "daily" and ll.tf_class("1D") == "daily" and ll.tf_class("60") == "intraday" and ll.tf_class("5") == "intraday"
    assert ll.jst_date("2026-11-13T06:00:00Z") == pd.Timestamp("2026-11-13")                     # 日本時間 15:00
    assert ll.jst_date("2026-11-13T16:00:00Z") == pd.Timestamp("2026-11-14")                     # 日本時間では翌日
    assert ll.jst_date(1763013600) == ll.jst_date("2025-11-13T06:00:00Z") and ll.jst_date("bad") is None


def _packet(symbol, tf, time, close, event="LONG_SETUP", stop=None, t1=None, t2=None):
    return {"schema": "ai-agent-lens/v1", "event": event, "symbol": symbol, "timeframe": tf, "time": time, "regime": "TREND_UP", "candle": {"close": close},
            "scores": {"long": 80, "short": 0, "threshold": 70}, "trade": {"side": "LONG", "status": "ACTIVE", "entry": close, "stop": stop, "target_1": t1, "target_2": t2}}


def _signal(symbol, tf, time, decision, entry, stop, t1, t2):
    return {"symbol": symbol, "timeframe": tf, "packet_time": time, "decision": decision, "confidence": 55, "entry": entry, "stop": stop, "target_1": t1, "target_2": t2}


def test_record_score_summary_roundtrip(tmp_path):
    P, codes, _ = seasonal_panel(n_codes=30, seed=51, turnover=1e9)
    t = 1500
    P.adj_open[t + 6:, 0] *= 1.05
    P.adj_high[t + 6:, 0] *= 1.05
    P.adj_low[t + 6:, 0] *= 1.05
    P.adj_close[t + 6:, 0] *= 1.05
    P.raw_open[t + 6:, 0] *= 1.05
    P.raw_close[t + 6:, 0] *= 1.05
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    ts = pd.Timestamp(P.dates[t]).strftime("%Y-%m-%d") + "T06:00:00Z"                              # 日本時間 15:00（日足の引け）
    entry = float(P.raw_close[t, 0])
    tv = "TSE:" + codes[0][:4]
    p = _packet(tv, "D", ts, entry, stop=entry * 0.80, t1=entry * 1.03, t2=entry * 1.30)
    s = _signal(tv, "D", ts, "LONG", entry, entry * 0.80, entry * 1.03, entry * 1.30)
    assert ll.add(root, "packet", json.dumps(p))["status"] == "recorded" and ll.add(root, "signal", json.dumps(s))["status"] == "recorded"
    assert ll.add(root, "packet", json.dumps(p))["status"] == "already_recorded"                  # 二重に記録しない
    assert "error" in ll.add(root, "packet", json.dumps({**p, "schema": "x"}))
    # WAIT（比べる相手）と、日本株でない銘柄
    ts2 = pd.Timestamp(P.dates[t]).strftime("%Y-%m-%d") + "T06:05:00Z"
    ll.add(root, "signal", json.dumps(_signal("TSE:" + codes[1][:4], "15", ts2, "WAIT", 100, 90, 110, 120)))
    r = ll.add(root, "signal", json.dumps(_signal("BINANCE:BTCUSDT", "60", ts2, "LONG", 100, 90, 110, 120)))
    assert r["scorable_with_jquants"] is False
    # まだ結果が出ない（直近の日）シグナル
    ts3 = pd.Timestamp(P.dates[-3]).strftime("%Y-%m-%d") + "T06:00:00Z"
    ll.add(root, "signal", json.dumps(_signal("TSE:" + codes[2][:4], "D", ts3, "LONG", 100, 90, 110, 120)))
    sc = ll.score(root)
    assert sc["scored_final"] == 2 and sc["unscorable"] == 1 and sc["pending"] == 1
    assert ll.score(root)["scored_final"] == 0                                                      # 二重に採点しない
    rows = ll.AppendOnlyLedger(root / "ledger" / "lens.jsonl")._rows()
    out = [r["payload"] for r in rows if r["type"] == "lens_outcome" and r["payload"].get("status") == "scored"]
    longs = [o for o in out if o["decision"] == "LONG"][0]
    assert longs["buy_day"] == str(P.dates[t + 1].date()) and longs["returns"]["5"]["excess"] > 0.03 and longs["returns"]["21"]["excess"] > 0.02
    assert longs["indicator_trade_21d"]["result"] == "target_1" and longs["indicator_trade_21d"]["day"] == 6
    assert abs(longs["same_day_close_vs_packet_price"]) < 1e-6
    res = ll.summary(root)
    assert res["packets"] == 1 and res["signals"] == 4 and res["scored"] == 2
    d = res["groups"]["daily"]["LONG"]
    assert d["n"] == 1 and d["excess_5d"]["mean"] > 0.03
    assert "結論を出さない" in res["groups"]["daily"]["conclusion"] and res["groups"]["intraday"] == {"WAIT": res["groups"]["intraday"].get("WAIT")}
    assert res["ledger"]["ok"]
