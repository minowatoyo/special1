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
    return pd.DataFrame({"asof": pd.Timestamp(asof), "code": codes, "market": market, "prod_cat": prod})


def test_universe_filters_market_product_liquidity_and_delisting():
    n = 80
    d = pd.bdate_range("2024-01-04", periods=n)
    p = pd.concat([
        pd.DataFrame({"date": d, "code": "10000", "turnover": 6e8}),                 # 流動性あり
        pd.DataFrame({"date": d, "code": "20000", "turnover": 4e8}),                 # 流動性不足
        pd.DataFrame({"date": d, "code": "30000", "turnover": 9e8}),                 # グロース
        pd.DataFrame({"date": d, "code": "40000", "turnover": 9e8}),                 # ETF など
        pd.DataFrame({"date": d[:70], "code": "50000", "turnover": 9e8}),            # 途中で上場廃止
    ])
    m = pd.concat([
        master("2024-01-04", ["10000", "20000", "50000"]),
        master("2024-01-04", ["30000"], market="0113"),
        master("2024-01-04", ["40000"], prod="013"),
        master("2024-04-22", ["10000", "20000"]),                                    # 後の時点では 50000 はない
    ])
    u = schema.universe(p, m)
    assert u["date"].min() == d[59]                                                  # 60 営業日そろってから
    assert set(u["code"]) == {"10000", "50000"}
    assert u.loc[u["code"] == "50000", "date"].max() <= d[69]
    assert (u["code"] == "10000").sum() == n - 59


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
