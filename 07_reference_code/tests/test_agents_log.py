"""TradingAgents の橋渡し（合成データ・偽のグラフ）。過去日付の拒否、重複の防止、記録・採点・集計、前向きの条件（記録時刻）。"""
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from test_rules import _write_processed
from test_seasonal import seasonal_panel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
import agents_log as al  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_agents", Path(__file__).resolve().parents[2] / "tools" / "tradingagents_bridge" / "run_agents.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)


class FakeGraph:
    def __init__(self, rating="Buy"):
        self.rating, self.calls = rating, []

    def propagate(self, ticker, date):
        self.calls.append((ticker, date))
        return {"final_trade_decision": f"決定: {self.rating} {ticker}"}, self.rating


def test_runner_refuses_past_dates_and_skips_duplicates(tmp_path):
    g = FakeGraph()
    cfg = {"llm_provider": "x"}
    r = ra.run_one(g, "7203.T", "2026-11-10", cfg, tmp_path, allow_past=False, now_date="2026-11-13")
    assert r["status"] == "skipped_past_date" and g.calls == []
    r = ra.run_one(g, "7203.T", "2026-11-13", cfg, tmp_path, now_date="2026-11-13")
    assert r["status"] == "done" and r["rating"] == "Buy" and len(g.calls) == 1
    assert ra.run_one(g, "7203.T", "2026-11-13", cfg, tmp_path, now_date="2026-11-13")["status"] == "already_exists" and len(g.calls) == 1
    rec = json.loads(Path(r["file"]).read_text(encoding="utf-8"))
    assert rec["schema"] == "agents-run/v1" and rec["backfill"] is False and len(rec["decision_sha256"]) == 64 and rec["decision_excerpt"].startswith("決定")
    r2 = ra.run_one(g, "6758.T", "2026-11-10", cfg, tmp_path, allow_past=True, now_date="2026-11-13")
    assert r2["status"] == "done" and json.loads(Path(r2["file"]).read_text(encoding="utf-8"))["backfill"] is True


def test_rating_groups():
    assert [al.rating_group(x) for x in ("Buy", "Overweight", "Hold", "Underweight", "Sell", "REVIEW")] == ["bullish", "bullish", "neutral", "bearish", "bearish", "review"]


def test_record_score_summary_and_forward_validity(tmp_path):
    P, codes, _ = seasonal_panel(n_codes=40, seed=61, turnover=1e9)
    t = 1500
    P.adj_open[t + 6:, 0] *= 1.08                                      # 強気の銘柄: 翌々日以降に 8% 上がる
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    d = str(P.dates[t].date())
    g = FakeGraph("Buy")
    out = tmp_path / "out"
    cfg = {"llm_provider": "anthropic"}
    tick = codes[0][:4] + ".T"
    ra.run_one(g, tick, d, cfg, out, allow_past=True, now_date=d)                               # 日付の判定は now_date で通す（記録時刻の検査は、台帳のほうで行う）
    g2 = FakeGraph("Sell")
    ra.run_one(g2, codes[1][:4] + ".T", d, cfg, out, allow_past=True, now_date=d)
    ra.run_one(FakeGraph("Hold"), "AAPL", d, cfg, out, allow_past=True, now_date=d)             # 日本株でない
    r = al.add_files(root, [str(p) for p in out.glob("*.json")])
    assert r["recorded"] == 3 and r["already"] == 0 and not r["errors"] and r["ledger"]["ok"]
    assert al.add_files(root, [str(p) for p in out.glob("*.json")])["already"] == 3
    # 記録時刻が、買いの日の寄り付き（日本時間 9:00）より後なら、前向きとして数えない（この合成の台帳は、いま書いたので、過去の日付に対しては「後」になる）
    sc = al.score(root)
    assert sc["scored"] >= 8 and sc["ledger"]["ok"]
    s = al.summary(root)
    assert s["runs_recorded"] == 3 and s["outcomes_scored"] >= 8 and s["outcomes_not_forward_valid"] == s["outcomes_scored"]
    assert s["by_group"] == {} and "結論を出さない" in s["conclusion"]                                   # 前向きの有効分がないので、集計は空
    # 前向きの有効性: 台帳の時刻を、買いの日の前（実行日の引け後）にして、採点する
    rows = [json.loads(x) for x in (root / "ledger" / "agents.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert all(r["type"] in ("agents_run", "agents_outcome") for r in rows)


def test_ledger_time_is_tamper_evident_and_old_rows_still_verify(tmp_path):
    from forecastlib.ledger import AppendOnlyLedger
    f = tmp_path / "l.jsonl"
    led = AppendOnlyLedger(f)
    # 古い形式（hv なし。時刻を含まないハッシュ）の行を、先に作る
    old = {"seq": 0, "prev": "0" * 64, "type": "x", "utc": "2026-01-01T00:00:00Z", "payload": {"a": 1}}
    old["hash"] = AppendOnlyLedger._hash("0" * 64, "x", {"a": 1})
    f.write_text(json.dumps(old) + "\n", encoding="utf-8")
    assert led.verify()["ok"]
    led.append_event("y", {"b": 2})                                                                    # 新しい行（hv=2）は、時刻を含む
    assert led.verify()["ok"] and led._rows()[1]["hv"] == 2
    rows = led._rows()
    rows[1]["utc"] = "2026-01-02T00:00:00Z"                                                           # 新しい行の時刻を書き換える → 検出される
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert led.verify() == {"ok": False, "rows": 2, "first_bad": 1}
    rows = led._rows()
    rows[1].pop("hv")                                                                                  # 古い形式に偽装 → 検出される
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert not led.verify()["ok"]


def test_forward_valid_when_recorded_before_the_buy_open(tmp_path, monkeypatch):
    P, codes, _ = seasonal_panel(n_codes=40, seed=62, turnover=1e9)
    t = 1500
    P.adj_open[t + 6:, 0] *= 1.08
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    d = str(P.dates[t].date())
    after_close = datetime(P.dates[t].year, P.dates[t].month, P.dates[t].day, 16, 0, tzinfo=timezone(timedelta(hours=9))).astimezone(timezone.utc)
    import forecastlib.ledger as lg

    class FixedDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return after_close
    monkeypatch.setattr(lg, "datetime", FixedDT)                                                       # 台帳に書く時刻を、実行日の引け後に固定する
    out = tmp_path / "out"
    ra.run_one(FakeGraph("Buy"), codes[0][:4] + ".T", d, {}, out, allow_past=True, now_date=d)
    ra.run_one(FakeGraph("Sell"), codes[1][:4] + ".T", d, {}, out, allow_past=True, now_date=d)
    al.add_files(root, [str(p) for p in out.glob("*.json")])
    monkeypatch.undo()
    al.score(root)
    s = al.summary(root)
    assert s["outcomes_not_forward_valid"] == 0 and s["outcomes_scored"] >= 8
    assert s["by_group"]["h=21"]["bullish"]["mean_excess"] > 0.02 and s["by_group"]["h=21"]["bearish"]["mean_excess"] < 0.02
    assert "結論を出さない" in s["conclusion"] and s["ledger"]["ok"]


def test_draw_is_stratified_reproducible_recorded_before_running_and_excludes_recent(tmp_path):
    import agents_sample as asp
    P, codes, _ = seasonal_panel(n_codes=60, seed=71, turnover=1e9)
    # 段階を作る: 売買代金（turnover）を、銘柄ごとに変える（A: 20 銘柄、B: 20、C: 20）
    to = np.where(np.arange(60) < 20, 1e9, np.where(np.arange(60) < 40, 1e8, 3e7))
    P.turnover[:] = to[None, :]
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    f = root / "processed" / "prices_daily.parquet"
    d = pd.read_parquet(f)
    d["turnover"] = d["code"].map({c: to[i] for i, c in enumerate(codes)})
    d.to_parquet(f, index=False)
    out = tmp_path / "today.txt"
    r1 = asp.draw(root, 9, "2026-11-12", write_file=out)
    assert r1["status"] == "drawn" and [len(v) for v in r1["tickers"].values()] == [3, 3, 3] and r1["frame_size"] == {"A_ge500M": 20, "B_50M_500M": 20, "C_20M_50M": 20}
    assert len(out.read_text(encoding="utf-8").split()) == 9
    r2 = asp.draw(root, 9, "2026-11-12", write_file=out)                         # 同じ日は、同じ一覧（再抽出しない）
    assert r2["status"] == "already_drawn" and r2["tickers"] == r1["tickers"]
    r3 = asp.draw(root, 9, "2026-11-13", write_file=out)                         # 翌日: 直近に抽出した銘柄は、除く
    drawn1 = {t for v in r1["tickers"].values() for t in v}
    assert r3["status"] == "drawn" and not (drawn1 & {t for v in r3["tickers"].values() for t in v}) and r3["excluded_recent"] == 9
    # 抽出の記録が、台帳にある → 実行結果の記録に、段階が付く
    rec = {"schema": "agents-run/v1", "ticker": r1["tickers"]["A_ge500M"][0], "trade_date": "2026-11-12", "rating": "Buy", "run_utc": "2026-11-12T08:00:00Z", "backfill": False,
           "decision_sha256": "x" * 64, "decision_excerpt": "e", "config": {}, "elapsed_sec": 120.5, "usage_tokens": {"m": {"input_tokens": 90000, "output_tokens": 10000, "total_tokens": 100000}}}
    assert al.add(root, rec)["status"] == "recorded"
    s = al.summary(root)
    assert s["draws"] == {"days": 2, "tickers_drawn": 18, "runs_recorded_from_draws": 1, "drawn_but_not_recorded": 17}
    assert s["cost_measure"] == {"runs_with_usage": 1, "mean_total_tokens_per_run": 100000, "mean_seconds_per_run": 120.5}
    # 実行側: トークン数の差を、実行前後から出す
    assert ra._usage_diff({"m": {"total_tokens": 5, "input_tokens": 3, "output_tokens": 2}}, {"m": {"total_tokens": 12, "input_tokens": 8, "output_tokens": 4}}) == {"m": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}}
