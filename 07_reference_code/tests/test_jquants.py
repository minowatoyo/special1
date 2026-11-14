"""J-Quants 基盤（スキーマ・アダプタ・クライアント・全消去）のテスト。合成データのみ。実データは使わない。"""
import subprocess
import sys
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
import schema  # noqa: E402


def bars(code="12340", n=10, start="2024-01-04", price=100.0, factor_on=None, factor=0.5):
    """合成の日足（API の列名）。factor_on の日に分割（その日の AdjFactor=factor。それ以前の調整後価格は factor 倍）。"""
    d = pd.bdate_range(start, periods=n)
    c = np.full(n, price)
    f = np.ones(n)
    if factor_on is not None:
        f[factor_on] = factor
    ratio = np.ones(n)                      # AdjC/C: 後の日の係数を掛けていく
    for t in range(n - 2, -1, -1):
        ratio[t] = ratio[t + 1] * f[t + 1]
    rows = []
    for i in range(n):
        rows.append({"Date": d[i].strftime("%Y-%m-%d"), "Code": code, "O": c[i], "H": c[i] * 1.01, "L": c[i] * 0.99, "C": c[i],
                     "UL": "0", "LL": "0", "Vo": 1000.0, "Va": 1000.0 * c[i], "AdjFactor": f[i],
                     "AdjO": c[i] * ratio[i], "AdjH": c[i] * 1.01 * ratio[i], "AdjL": c[i] * 0.99 * ratio[i],
                     "AdjC": c[i] * ratio[i], "AdjVo": 1000.0 / ratio[i], "MktCap": 1.0, "ExRT": None})
    return rows


def test_normalize_keeps_adjusted_and_unadjusted_separate_and_dedups():
    rows = bars(factor_on=5) + bars(factor_on=5)[:2]
    df = schema.normalize_prices(rows)
    assert len(df) == 10 and df["date"].is_monotonic_increasing
    assert {"open", "adj_open", "adj_factor", "volume", "adj_volume", "turnover"} <= set(df.columns)
    assert df["close"].iloc[0] == 100.0 and df["adj_close"].iloc[0] == 50.0 and df["adj_close"].iloc[-1] == 100.0


def test_adjustment_reconciliation_ok_and_detects_tampering():
    df = schema.normalize_prices(bars(factor_on=5))
    assert schema.reconcile_adjustment(df).empty
    df.loc[2, "adj_close"] *= 1.01
    bad = schema.reconcile_adjustment(df)
    assert len(bad) >= 1 and (bad["date"] == df.loc[2, "date"]).any()


def test_reconciliation_skips_gaps_in_data():
    df = schema.normalize_prices(bars(n=4) + bars(n=4, start="2024-06-03", factor_on=0))
    df = df[df["adj_close"].notna()]
    df.loc[df["date"] >= "2024-06-03", "adj_close"] *= 1.0
    assert schema.reconcile_adjustment(df).empty           # 取得の飛びは検査対象外（誤検知しない）


def test_quality_flags_separate_causes():
    df = schema.normalize_prices(bars(n=8))
    df.loc[1, "high"] = df.loc[1, "low"] * 0.9              # 高値 < 安値 → OHLC 矛盾
    df.loc[3, ["open", "high", "low", "close"]] = np.nan    # 売買なし
    df.loc[3, "volume"] = np.nan
    df.loc[5, "adj_close"] = df.loc[4, "adj_close"] * 1.40  # +40% の跳び
    f = schema.quality_flags(df).set_index("date")
    assert f.loc[df.loc[1, "date"], "ohlc_inconsistent"]
    assert f.loc[df.loc[3, "date"], "no_trade"] and not f.loc[df.loc[3, "date"], "nonpositive"]
    assert f.loc[df.loc[5, "date"], "jump_flag"]
    assert not f.loc[df.loc[7, "date"], ["ohlc_inconsistent", "no_trade", "nonpositive"]].any()


@pytest.mark.parametrize("t,expect", [("15:29:00", "2024-01-04"), ("15:30:00", "2024-01-05"), ("15:00", "2024-01-04"),
                                      (None, "2024-01-05"), ("", "2024-01-05"), ("23:59", "2024-01-05")])
def test_usable_from_cutoff_rule(t, expect):
    days = pd.bdate_range("2024-01-01", "2024-01-31")
    assert schema.usable_from("2024-01-04", t, days) == pd.Timestamp(expect)


def test_usable_from_non_trading_day_and_end_of_calendar():
    days = pd.bdate_range("2024-01-01", "2024-01-31")
    assert schema.usable_from("2024-01-06", "10:00", days) == pd.Timestamp("2024-01-08")   # 土曜 → 翌営業日
    assert pd.isna(schema.usable_from("2024-01-31", "16:00", days))


def test_fins_usable_never_returns_future(tmp_path):
    days = pd.bdate_range("2024-01-01", "2024-02-29")
    rows = [{"DiscDate": "2024-01-10", "DiscTime": "15:30:00", "Code": "12340", "DiscNo": "1", "OP": 1}]
    f = schema.normalize_fins(rows, days)
    assert f["usable_from"].iloc[0] == pd.Timestamp("2024-01-11")


def master(asof, codes, market="0111", prod="011"):
    return pd.DataFrame({"asof": pd.Timestamp(asof), "code": codes, "name": "n", "s17": "1", "s33": "1", "scale_cat": "-",
                         "margin_class": "2", "market": market, "prod_cat": prod})


def test_is_domestic_common_rules():
    pc = ["011", "011", "011", "013", "014", "011", "011", "011", None, "011", "021"]
    cd = ["72030", "72031", "130A0", "13060", "89510", "7203", "720300", None, "72030", "72 30", "10010"]
    got = schema.is_domestic_common(pc, cd).tolist()
    assert got == [True, False, True, False, False, False, False, False, False, False, False]
    # コードは文字列のまま（数値化して先頭の 0 や英字を失わない）
    assert schema.is_domestic_common(["011"], ["00010"]).tolist() == [True]


def test_market_filter_is_separate_from_common_stock_rule():
    pc, cd, mk = ["011", "011", "013"], ["72030", "40000", "13060"], ["0111", "0113", "0111"]
    common = schema.is_domestic_common(pc, cd).tolist()
    assert common == [True, True, False]
    assert schema.market_in(mk, schema.POST_2022).tolist() == [True, False, True]
    assert schema.market_in(["0101", "0102", "0106", "0111"], schema.PRE_2022_PROPOSAL).tolist() == [True, True, True, False]


def test_master_intervals_ipo_delisting_and_market_change_within_month():
    cal = pd.bdate_range("2024-03-01", "2024-03-29")
    snaps = []
    for i, d in enumerate(cal):
        codes = [("10000", "0111"), ("20000", "0112")]
        if i >= 9:
            codes.append(("30000", "0113"))                      # 月の途中で新規上場
        if i < 14:
            codes.append(("40000", "0111"))                      # 月の途中で上場廃止
        if i >= 6:
            codes[1] = ("20000", "0111")                         # 月の途中で市場変更（スタンダード→プライム）
        for c, m in codes:
            snaps.append(master(d, [c], market=m))
    iv = schema.master_intervals(pd.concat(snaps), cal)
    g = iv.set_index("code")
    assert len(iv[iv.code == "20000"]) == 2 and iv[iv.code == "20000"]["market"].tolist() == ["0112", "0111"]
    assert g.loc["30000", "valid_from"] == cal[9] and g.loc["30000", "valid_to"] == cal[-1]
    assert g.loc["40000", "valid_from"] == cal[0] and g.loc["40000", "valid_to"] == cal[13]
    assert len(iv[iv.code == "10000"]) == 1                      # 変化なしは 1 区間


def test_master_intervals_gap_in_snapshots_splits_interval():
    cal = pd.bdate_range("2024-03-01", periods=6)
    m = pd.concat([master(d, ["10000"]) for i, d in enumerate(cal) if i != 3])
    assert len(schema.master_intervals(m, cal)) == 2


def test_universe_filters_market_product_code_liquidity_and_listing_dates():
    n = 80
    d = pd.bdate_range("2024-01-04", periods=n)
    ids = {"10000": 6e8, "20000": 4e8, "30000": 9e8, "40000": 9e8, "50000": 9e8, "60001": 9e8, "70000": 9e8}
    p = pd.concat([pd.DataFrame({"date": d if c != "50000" else d[:70], "code": c, "turnover": v}) for c, v in ids.items()])
    base = pd.bdate_range("2024-01-04", periods=n)
    snaps = []
    for i, day in enumerate(base):
        for c, mk, pc in [("10000", "0111", "011"), ("20000", "0111", "011"), ("30000", "0113", "011"), ("40000", "0111", "013"),
                          ("60001", "0111", "011"), ("70000", "0112", "011")]:
            snaps.append(master(day, [c], market=mk, prod=pc))
        if i < 70:
            snaps.append(master(day, ["50000"]))                 # 途中で上場廃止
    iv = schema.master_intervals(pd.concat(snaps), base)
    u = schema.universe(p, iv)
    assert u["date"].min() == d[59]
    assert set(u["code"]) == {"10000", "50000", "70000"}          # 流動性不足・グロース・ETF・末尾非 0 は除外
    assert u.loc[u["code"] == "50000", "date"].max() <= d[69]
    assert (u["code"] == "10000").sum() == n - 59
    # 市場区分は別に指定できる（旧区分の案を渡すと、0111/0112 の銘柄は対象外になる）
    assert schema.universe(p, iv, markets=schema.PRE_2022_PROPOSAL).empty


def test_client_never_logs_key_and_stops_on_403(tmp_path, monkeypatch):
    import client
    monkeypatch.setattr(client.time, "sleep", lambda s: None)

    def boom(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 403, "no", {}, __import__("io").BytesIO(b'{"message":"not available"}'))

    monkeypatch.setattr(client.urllib.request, "urlopen", boom)
    c = client.Client(root=tmp_path, per_min=6000, key="SECRET-KEY-VALUE")
    with pytest.raises(client.AuthError):
        c.get_page("/v2/fins/dividend", {"code": "72030"})
    log = (tmp_path / "_meta" / "fetch_log.csv").read_text(encoding="utf-8")
    assert "403" in log and "SECRET-KEY-VALUE" not in log
    assert "SECRET-KEY-VALUE" not in "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "raw").rglob("*.json"))


def test_client_retries_429_then_succeeds(tmp_path, monkeypatch):
    import client, io
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class R:
        status = 200
        headers = {}
        def read(self): return b'{"data": []}'
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "slow", {}, io.BytesIO(b"{}"))
        return R()

    monkeypatch.setattr(client.urllib.request, "urlopen", fake)
    st, js, _ = client.Client(root=tmp_path, per_min=6000, key="k").get_page("/v2/equities/bars/daily", {"date": "2024-01-04"})
    assert st == 200 and js == {"data": []} and calls["n"] == 2


def test_rate_limiter_spacing():
    import client
    rl = client.RateLimiter(120)
    assert abs(rl.gap - 0.5) < 1e-12


def test_purge_requires_yes_and_removes_everything(tmp_path):
    d = tmp_path / "jq"
    (d / "raw").mkdir(parents=True)
    (d / "processed").mkdir()
    (d / "raw" / "a.json").write_text("{}")
    sh = str(ROOT / "scripts" / "jquants" / "purge.sh")
    r = subprocess.run(["sh", sh, str(d)], capture_output=True, text=True)
    assert r.returncode != 0 and d.exists()
    r = subprocess.run(["sh", sh, str(d), "--yes"], capture_output=True, text=True)
    assert r.returncode == 0 and not d.exists()


pq = pytest.importorskip("pyarrow")


def write_processed(tmp_path):
    root = tmp_path / "jq"
    out = root / "processed"
    out.mkdir(parents=True)
    pr = schema.normalize_prices(bars(factor_on=5))
    pr.to_parquet(out / "prices_daily.parquet", index=False)
    fl = schema.quality_flags(pr)
    fl.loc[2, "no_trade"] = True
    fl.to_parquet(out / "quality_flags.parquet", index=False)
    return root


def test_adapter_returns_forecastlib_format_without_writing(tmp_path):
    from forecastlib import jquants_adapter as ja
    root = write_processed(tmp_path)
    before = sorted(p.name for p in root.rglob("*"))
    adj = ja.load_ohlcv("1234", root=root)
    raw = ja.load_ohlcv("12340", root=root, adjusted=False)
    assert list(adj.columns) == ["open", "high", "low", "close", "volume"] and adj.index.is_monotonic_increasing
    assert len(adj) == 9 and len(ja.load_ohlcv("1234", root=root, drop_no_trade=False)) == 10   # 売買なしの日を除く
    assert adj["close"].iloc[0] == 50.0 and raw["close"].iloc[0] == 100.0
    assert before == sorted(p.name for p in root.rglob("*"))


def test_adapter_missing_table_message(tmp_path):
    from forecastlib import jquants_adapter as ja
    with pytest.raises(FileNotFoundError):
        ja.load_ohlcv("1234", root=tmp_path)


# ---- backfill（通信なし。擬似クライアント） ----
import backfill  # noqa: E402


class FakeLimiter:
    gap = 0.0


class FakeClient:
    """script: {(path, date): [(status, rows, pages), ...]}（呼ぶたびに先頭から消費。最後の値は繰り返す）"""
    def __init__(self, script, interrupt_at=None):
        self.limiter, self.script, self.calls, self.interrupt_at = FakeLimiter(), script, [], interrupt_at
        self.last_pages, self.last_files = 0, []

    def get_all(self, path, params, note=""):
        self.calls.append((path, params.get("date")))
        if self.interrupt_at and len(self.calls) == self.interrupt_at:
            raise KeyboardInterrupt
        seq = self.script.get((path, params.get("date")), [(200, [{"x": 1, "Date": params.get("date")}], 1)])
        st, rows, pages = seq[0] if len(seq) == 1 else seq.pop(0)
        self.last_pages, self.last_files = pages, [f"{path}/{params.get('date')}/p{i}.json" for i in range(pages)]
        return st, rows


def jobs3():
    return backfill.plan([pd.Timestamp("2024-01-04").date(), pd.Timestamp("2024-01-05").date()])


def test_backfill_interrupt_and_resume_has_no_duplicates_or_gaps(tmp_path):
    jobs = jobs3()
    c1 = FakeClient({}, interrupt_at=4)
    with pytest.raises(KeyboardInterrupt):
        backfill.run_jobs(c1, jobs, tmp_path, sleep=lambda s: None)
    assert len(backfill.load_checkpoint(tmp_path)) == 3
    c2 = FakeClient({})
    st = backfill.run_jobs(c2, jobs, tmp_path, sleep=lambda s: None)
    assert st["done_before"] == 3 and st["ok"] == len(jobs) - 3 and not st["fail"]
    assert len(backfill.load_checkpoint(tmp_path)) == len(jobs)
    lines = (tmp_path / "_meta" / "checkpoint.jsonl").read_text().splitlines()
    assert len(lines) == len(jobs) == len(set(lines))                     # 重複なし
    c3 = FakeClient({})
    assert backfill.run_jobs(c3, jobs, tmp_path, sleep=lambda s: None)["ok"] == 0 and not c3.calls   # 再実行で何も取らない


def test_backfill_failure_is_not_checkpointed_and_retried(tmp_path):
    jobs = jobs3()
    bad = ("/v2/equities/bars/daily", "2024-01-04")
    c = FakeClient({bad: [(500, [], 0), (200, [{"x": 1}], 1)]})
    st = backfill.run_jobs(c, jobs, tmp_path, sleep=lambda s: None)
    assert not st["fail"] and st["ok"] == len(jobs)                        # 次の周回で成功
    c = FakeClient({bad: [(500, [], 0)]})
    tmp2 = tmp_path / "b"
    st = backfill.run_jobs(c, jobs, tmp2, sleep=lambda s: None)
    assert st["fail"] and any("2024-01-04" in x for x in st["failed_jobs"])
    assert backfill.jkey(*bad[:1], {"date": bad[1]}) not in backfill.load_checkpoint(tmp2)


def test_backfill_zero_rows_rules(tmp_path):
    jobs = jobs3()
    c = FakeClient({("/v2/equities/bars/daily", "2024-01-04"): [(200, [], 1)], ("/v2/fins/summary", "2024-01-04"): [(200, [], 1)]})
    st = backfill.run_jobs(c, jobs, tmp_path, sleep=lambda s: None)
    assert "/v2/equities/bars/daily" in st["fail"]                         # 営業日の日足が 0 行 → 失敗（正常な 0 行にしない）
    assert "/v2/fins/summary" not in st["fail"] and st["zero_rows_accepted"] == 1
    ck = backfill.load_checkpoint(tmp_path)
    assert ck[backfill.jkey("/v2/fins/summary", {"date": "2024-01-04"})]["zero_rows"] is True


def test_backfill_records_all_pages_and_stops_on_429(tmp_path):
    jobs = jobs3()
    c = FakeClient({("/v2/fins/summary", "2024-01-05"): [(200, [{"x": 1}] * 5, 3)]})
    backfill.run_jobs(c, jobs, tmp_path, sleep=lambda s: None)
    r = backfill.load_checkpoint(tmp_path)[backfill.jkey("/v2/fins/summary", {"date": "2024-01-05"})]
    assert r["pages"] == 3 and len(r["files"]) == 3 and r["rows"] == 5
    t2 = tmp_path / "c"
    c = FakeClient({("/v2/equities/master", "2024-01-04"): [(429, [], 0)]})
    st = backfill.run_jobs(c, jobs, t2, sleep=lambda s: None)
    assert "429" in st["stopped"] and len(backfill.load_checkpoint(t2)) == 2


def test_contract_check_stops_without_changing_start(monkeypatch):
    class C:
        def __init__(self, st, js): self.r = (st, js)
        def get_page(self, *a, **k): return self.r[0], self.r[1], {}
    ok = backfill.check_contract(C(400, {"message": "Your subscription covers the following dates: 2016-11-12 ~ ."}))
    assert "2016-11-12" in ok
    with pytest.raises(backfill.ContractChanged):
        backfill.check_contract(C(400, {"message": "covers the following dates: 2017-01-04 ~ ."}))      # 期間が短くなった
    with pytest.raises(backfill.ContractChanged):
        backfill.check_contract(C(200, {"data": []}))                                                  # 窓が広がった
    with pytest.raises(backfill.ContractChanged):
        backfill.check_contract(C(500, None))


def test_estimate_scales_with_days_and_includes_daily_master():
    e = backfill.estimate(2451)
    assert e["endpoints"]["/v2/equities/master"] == 2451 and 9500 < e["requests"] < 10000
    assert 100 < e["minutes"] < 140 and 6 < e["raw_gb"] < 9


def test_backfill_cannot_start_before_oldest_date():
    assert backfill.OLDEST.isoformat() == "2016-11-12"


def test_end_date_is_previous_business_day():
    from datetime import date
    assert backfill.prev_business_day(date(2026, 11, 12)) == date(2026, 11, 11)     # 木 → 水
    assert backfill.prev_business_day(date(2026, 11, 9)) == date(2026, 11, 6)       # 月 → 前の金
    assert backfill.prev_business_day(date(2026, 11, 14)) == date(2026, 11, 13)     # 土 → 金
    assert backfill.prev_business_day(date(2026, 11, 15)) == date(2026, 11, 13)     # 日 → 金


def test_unresolved_zero_row_day_is_logged_and_does_not_stop_the_rest(tmp_path):
    jobs = jobs3()
    bad = ("/v2/equities/bars/daily", "2024-01-04")
    c = FakeClient({bad: [(200, [], 1)]})
    st = backfill.run_jobs(c, jobs, tmp_path, sleep=lambda s: None)
    assert st["ok"] == len(jobs) - 1 and st["fail"] == {"/v2/equities/bars/daily": 1}
    inv = backfill.load_investigate(tmp_path)
    assert [(i["path"], i["date"], i["reason"]) for i in inv] == [(bad[0], bad[1], "unresolved_after_retries")]
    assert backfill.jkey(bad[0], {"date": bad[1]}) not in backfill.load_checkpoint(tmp_path)    # 正常な 0 行として記録しない
    import report_w3
    rep = report_w3.main(tmp_path)
    assert rep["investigate"]["count"] == 1 and rep["investigate"]["list"][0]["date"] == "2024-01-04"
    c2 = FakeClient({})                                                                       # 後で解消すれば再実行で完了し、一覧から消える
    backfill.run_jobs(c2, jobs, tmp_path, sleep=lambda s: None)
    assert report_w3.main(tmp_path)["investigate"]["count"] == 0


def test_master_date_mismatch_is_flagged(tmp_path):
    jobs = jobs3()
    wrong = ("/v2/equities/master", "2024-01-05")
    c = FakeClient({wrong: [(200, [{"Date": "2024-01-04"}, {"Date": "2024-01-05"}], 1)]})
    st = backfill.run_jobs(c, jobs, tmp_path, sleep=lambda s: None)
    r = backfill.load_checkpoint(tmp_path)[backfill.jkey(wrong[0], {"date": wrong[1]})]
    assert r["date_mismatch"] == 1 and st["date_mismatch"] == 1
    import report_w3
    lst = report_w3.main(tmp_path)["investigate"]["list"]
    assert any(x["reason"] == "date_mismatch" and x["date"] == "2024-01-05" for x in lst)


def test_build_excludes_date_mismatch_rows_but_keeps_raw(tmp_path):
    import json
    import build_processed
    root = tmp_path
    raw = root / "raw" / "v2_equities_master" / "2024-02-01"
    raw.mkdir(parents=True)
    f = raw / "a_0.json"
    row = lambda d, c: {"Date": d, "Code": c, "CoName": "n", "Mkt": "0111", "ProdCat": "011"}  # noqa: E731
    f.write_text(json.dumps({"data": [row("2024-01-05", "10000"), row("2024-01-04", "20000")]}))     # 要求日は 2024-01-05
    (root / "_meta").mkdir()
    (root / "_meta" / "checkpoint.jsonl").write_text(json.dumps(
        {"path": "/v2/equities/master", "params": {"date": "2024-01-05"}, "rows": 2, "pages": 1, "files": [str(f)], "date_mismatch": 1}) + "\n")
    build_processed.EXCLUDED.clear()
    rows = [r for _, rs in build_processed.rows_of(root, "v2_equities_master") for r in rs]
    assert [r["Code"] for r in rows] == ["10000"]
    assert build_processed.EXCLUDED == {"v2_equities_master": 1}
    assert json.loads(f.read_text())["data"][1]["Code"] == "20000"                                # 生データは残る


def test_contract_check_uses_explicit_oldest_and_window_slides_daily():
    from datetime import date
    class C:
        def get_page(self, path, params, note=""):
            return 400, {"message": "covers the following dates: 2016-11-13 ~ ."}, {}
    assert "2016-11-13" in backfill.check_contract(C(), date(2016, 11, 13))
    with pytest.raises(backfill.ContractChanged):
        backfill.check_contract(C(), date(2016, 11, 12))                      # 既定のままでは停止（自動では変えない）


def test_adjustment_pairs_and_rounding_tolerance():
    import diagnose_adjustment
    df = schema.normalize_prices(bars(factor_on=5))
    assert diagnose_adjustment.diagnose(df)["mismatch(rel>1e-6)"] == 0
    df["adj_close"] = df["adj_close"].round(0) + 0.3                 # 丸め（0.1 円）を超える差
    assert len(schema.reconcile_adjustment(df)) > 0
    assert schema.reconcile_adjustment(df, abs_tol_yen=1.0).empty     # 丸めの単位を渡せば許容される
    d2 = schema.normalize_prices(bars(factor_on=5)); d2["adj_close"] = (d2["adj_close"] * 10).round() / 10 + 0.04
    assert schema.reconcile_adjustment(d2).empty                      # 0.1 円の丸め内は一致とみなす（既定）
    rep = diagnose_adjustment.diagnose(df)
    assert rep["share_abs_err_le"]["1.0"] > 0.99 and "by_close_level" in rep


def test_diagnose_flags_breakdown():
    import diagnose_adjustment
    pr = schema.normalize_prices(bars(n=6))
    fl = schema.quality_flags(pr)
    fl.loc[2, "no_trade"] = True
    fl.loc[4, "jump_flag"] = True
    iv = schema.master_intervals(pd.concat([master(d, ["12340"]) for d in pr["date"]]), pr["date"])
    r = diagnose_adjustment.diagnose_flags(pr, fl, iv)
    assert r["no_trade_by_market"]["0111"] == {"rows": 6, "no_trade": 1} and r["jump_flag"]["total"] == 1
    assert "limit_flag_that_day" in r["jump_flag"]


def test_universe_counts_no_trade_days_as_zero_turnover_not_missing():
    n = 80
    d = pd.bdate_range("2024-01-04", periods=n)
    t = np.full(n, 9e8)
    t[10] = np.nan                                                   # 売買なしの日
    p = pd.DataFrame({"date": d, "code": "10000", "turnover": t})
    iv = schema.master_intervals(pd.concat([master(x, ["10000"]) for x in d]), d)
    u = schema.universe(p, iv)
    assert len(u) > 0 and u["date"].min() == d[59]                   # 欠損のまま平均すると 70 日目まで対象外になる


def test_auto_oldest_is_ten_years_before_same_month_day():
    from datetime import date
    assert backfill.auto_oldest(date(2026, 11, 12)) == date(2016, 11, 12)
    assert backfill.auto_oldest(date(2026, 11, 13)) == date(2016, 11, 13)       # W3 の実測と一致
    assert backfill.auto_oldest(date(2036, 2, 29)) == date(2026, 2, 28)         # 10 年前に同日がない場合


def test_standard_extra_normalizers_use_next_trading_day_after_publication():
    days = pd.bdate_range("2026-11-02", "2026-11-30")
    m = schema.normalize_margin([{"PubDate": "2026-11-09", "Date": "2026-11-06", "Code": "72030", "IssType": "1", "ShrtVol": "10", "LongVol": "100",
                                  "ShrtNegVol": "5", "LongNegVol": "50", "ShrtStdVol": "5", "LongStdVol": "50", "ShrtVal": "1", "LongVal": "2",
                                  "ShrtNegVal": "1", "LongNegVal": "1", "ShrtStdVal": "0", "LongStdVal": "1"}] * 2, days)
    assert len(m) == 1 and m["usable_from"].iloc[0] == pd.Timestamp("2026-11-10") and m["code"].iloc[0] == "72030"      # 重複は 1 行、公表日の翌営業日
    s = schema.normalize_short_ratio([{"Date": "2026-11-06", "S33": "3700", "SellExShortVa": "800", "ShrtWithResVa": "100", "ShrtNoResVa": "100"}], days)
    assert abs(s["short_ratio"].iloc[0] - 0.2) < 1e-12 and s["usable_from"].iloc[0] == pd.Timestamp("2026-11-09")
    i = schema.normalize_investor_types([{"PubDate": "2026-11-12", "StDate": "2026-11-02", "EnDate": "2026-11-06", "Section": "TSEPrime", "FrgnBal": "5"}], days)
    assert i["usable_from"].iloc[0] == pd.Timestamp("2026-11-13")
    assert schema.normalize_margin([], days).empty


def test_backfill_extra_plan_and_resume(tmp_path):
    import backfill_extra
    from datetime import date
    days = [date(2026, 11, 2), date(2026, 11, 4), date(2026, 11, 5)]
    jobs = backfill_extra.plan_extra(days, ["3700", "5250"])
    assert [j[0] for j in jobs].count("/v2/markets/margin-interest") == 3 and [j[0] for j in jobs].count("/v2/markets/short-ratio") == 2 and len(jobs) == 6
    assert jobs[3][1] == {"s33": "3700", "from": "2026-11-02", "to": "2026-11-05"}
    c = FakeClient({})
    st = backfill.run_jobs(c, jobs, tmp_path, sleep=lambda s: None)
    assert not st["fail"] and len(backfill.load_checkpoint(tmp_path)) == 6
    assert backfill.run_jobs(FakeClient({}), jobs, tmp_path, sleep=lambda s: None)["ok"] == 0       # 再実行で何も取らない
    c2 = FakeClient({("/v2/markets/margin-interest", None): [(200, [], 1)]})                         # 公表のない日は 0 行で正常（失敗にしない）
    st2 = backfill.run_jobs(c2, jobs, tmp_path / "z", sleep=lambda s: None)
    assert not st2["fail"] and st2["zero_rows_accepted"] == 3
