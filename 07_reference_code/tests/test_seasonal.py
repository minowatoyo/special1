"""季節性の検証（合成データ）。植えた季節性を検出すること、先読みがないこと、権利付き最終日の位置。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_selectlib import intervals_for

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
import schema  # noqa: E402
from selectlib import rules, seasonal  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def seasonal_panel(n_codes=150, seed=0, effect=0.0, start="2016-11-14", end="2026-11-12", turnover=1e9):
    """effect>0 なら、銘柄 j は毎年、暦月 (j % 12)+1 に、月の最初の営業日に effect だけ上がる。"""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    n = len(dates)
    ret = rng.normal(0, 0.012, (n, n_codes))
    first_of_month = np.r_[True, dates.month[1:] != dates.month[:-1]]
    idx1 = np.flatnonzero(first_of_month)
    for j in range(n_codes):
        m = (j % 12) + 1
        for i in idx1:
            if dates[i].month == m and i + 3 < n:
                ret[i + 3, j] += effect                        # 月の 4 営業日目に上がる（月初の始値で買った後）
    close = 1000 * np.exp(np.cumsum(ret, axis=0))
    opn = np.vstack([close[:1], close[:-1]])                   # 始値 = 前日終値
    codes = [f"{10000 + 10 * i}"[:4] + "0" for i in range(n_codes)]
    rows = [pd.DataFrame({"date": dates, "code": c, "open": opn[:, i], "close": close[:, i], "adj_open": opn[:, i], "adj_high": np.maximum(opn[:, i], close[:, i]),
                          "adj_low": np.minimum(opn[:, i], close[:, i]), "adj_close": close[:, i], "adj_volume": 1e6, "turnover": turnover,
                          "limit_up": "0", "limit_down": "0"}) for i, c in enumerate(codes)]
    prices = pd.concat(rows, ignore_index=True)
    tp = pd.DataFrame({"date": dates, "open": 1000.0, "high": 1000.0, "low": 1000.0, "close": 1000.0})
    P = Panel.from_frames(prices, prices[["code", "date"]].assign(no_trade=False), tp)
    return P, codes, prices


def test_months_and_rights_last_day_position():
    P, _, _ = seasonal_panel(n_codes=3)
    mo = seasonal.months(P)
    assert (np.diff(mo["first"]) > 0).all() and (mo["last"] >= mo["first"]).all()
    m = list(mo["period"].astype(str)).index("2021-03")
    assert P.dates[mo["last"][m]] == pd.Timestamp("2021-03-31") and P.dates[mo["last"][m] - 2] == pd.Timestamp("2021-03-29")   # 権利付き最終日
    assert seasonal.tiers(np.array([6e8, 1e8, 3e7])).tolist() == [0, 1, 2]


def test_s1_detects_planted_seasonality_and_null_is_flat():
    P, codes, _ = seasonal_panel(effect=0.04, seed=1)
    elig = np.ones(P.adj_close.shape, bool)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64()))
    rows = seasonal.s1_same_month(P, elig, P.va60(), b)["rows"]
    ic = np.array([r["ic"] for r in rows])
    top = np.array([r["top"] for r in rows])
    assert len(rows) > 60 and ic.mean() > 0.04 and seasonal.tstat(ic)["t"] > 5 and top.mean() > 0.01   # 季節性を持つのは毎月 1/12 の銘柄だけ
    assert {r["period"] for r in rows} >= {"discovery", "confirmation"}
    assert min(r["years"] for r in rows) >= seasonal.MIN_YEARS                     # 過去 3 年以上の同じ月だけを使う
    P0, _, _ = seasonal_panel(effect=0.0, seed=2)
    r0 = seasonal.s1_same_month(P0, elig, P0.va60(), b)["rows"]
    assert abs(np.mean([r["ic"] for r in r0])) < 0.03


def test_s1_uses_only_past_months():
    """ある月より後のデータを壊しても、その月までの結果は変わらない。"""
    P, _, _ = seasonal_panel(effect=0.02, seed=3, n_codes=120)
    elig = np.ones(P.adj_close.shape, bool)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64()))
    r1 = seasonal.s1_same_month(P, elig, P.va60(), b)["rows"]
    cut = int(np.searchsorted(P.dates.values, np.datetime64("2023-01-10")))
    P.adj_open[cut:] *= np.linspace(1, 3, P.adj_open.shape[1])
    r2 = seasonal.s1_same_month(P, elig, P.va60(), b)["rows"]
    k = sum(1 for r in r1 if r["period"] == "discovery")
    assert k > 10 and [(r["ic"], r["top"]) for r in r1[:k]] == [(r["ic"], r["top"]) for r in r2[:k]]


def _fins(P, codes, fy_month=3, div=30.0):
    rows = []
    for i, c in enumerate(codes):
        for y in range(2017, 2027):
            for q, (mm, dd) in zip(("1Q", "2Q", "3Q", "FY"), ((8, 5), (11, 5), (2, 5), (5, 10))):
                d = pd.Timestamp(year=y, month=mm, day=dd) + pd.offsets.BDay(i % 15)     # 発表日は銘柄ごとにずれる
                rows.append({"Code": c, "DiscDate": d, "usable_from": d + pd.offsets.BDay(1), "CurFYEn": f"{y if mm <= fy_month else y + 1}-{fy_month:02d}-31",
                             "CurPerType": q, "DocType": f"{q}FinancialStatements_Consolidated_JP", "FDivAnn": div, "NxFDivAnn": np.nan, "DivAnn": np.nan})
    f = pd.DataFrame(rows)
    return f[f["DiscDate"] <= P.dates[-1]]


def test_s2_group_is_rights_month_and_s3_runs():
    P, codes, _ = seasonal_panel(n_codes=80, seed=4)
    elig = np.ones(P.adj_close.shape, bool)
    b = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64()))
    fins = _fins(P, codes)
    rng = np.random.default_rng(0)
    fins["FDivAnn"] = fins["Code"].map({c: v for c, v in zip(codes, rng.uniform(5, 60, len(codes)))})
    rows = seasonal.s2_dividend_runup(P, elig, P.va60(), fins, b)["rows"]
    assert rows and {r["month"] for r in rows} == {3, 9}                           # 決算期末の月と、その 6 か月後だけ
    assert all(r["group"] >= seasonal.MIN_GROUP for r in rows)
    acc = seasonal.s3_pre_earnings(P, elig, P.va60(), fins, b)
    s = seasonal.s3_stats(acc, P.dates, b, "discovery")
    assert s["entries"] > 500 and np.isfinite(s["mean"]) and abs(s["mean"]) < 0.01     # ランダムなデータでは 0 付近


def test_seasonal_study_end_to_end_with_wide_universe(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
    import seasonal_study
    P, codes, prices = seasonal_panel(n_codes=130, seed=5, effect=0.03, turnover=3e7)      # 売買代金 3,000 万円: 従来の 5 億円では対象外、広い母集団では対象
    root = tmp_path / "jq"
    out = root / "processed"
    out.mkdir(parents=True)
    prices.to_parquet(out / "prices_daily.parquet", index=False)
    prices[["code", "date"]].assign(no_trade=False).to_parquet(out / "quality_flags.parquet", index=False)
    P.topix.reset_index().rename(columns={"index": "date"}).to_parquet(out / "topix_daily.parquet", index=False)
    iv = intervals_for(codes, P.dates, market="0113")                                       # グロース（従来の母集団には入らない区分）
    iv.to_parquet(out / "listed_master.parquet", index=False)
    _fins(P, codes).to_parquet(out / "fins_summary.parquet", index=False)
    res = seasonal_study.main(root)
    assert res["universe"]["eligible_median_per_day"] == 130 and res["universe"]["tier_counts_at_end_of_discovery(A,B,C)"] == [0, 0, 130]
    r = {x["test"]: x for x in res["results"]}
    assert r["S1_same_month:ic"]["discovery"]["mean"] > 0.03 and r["S1_same_month:ic"]["q"] < 0.10
    assert "confirmation" in r["S1_same_month:ic"] and r["S1_same_month:ic"]["law_candidate"] is True
    assert res["ledger_chain"]["ok"] and (root / "results" / "seasonal" / "summary.json").exists()
    assert schema.WIDE_VA_MIN == 2e7 and "0113" in schema.WIDE_MARKETS and "0105" not in schema.WIDE_MARKETS
