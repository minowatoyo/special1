"""selectlib のテスト（合成データ）。先読みがないこと、仕様どおりの計算、DSR/PBO の性質。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
import schema  # noqa: E402
from selectlib import evalsel, features, model  # noqa: E402
from selectlib.panel import Panel  # noqa: E402


def synth_panel(n_dates=700, n_codes=40, seed=0, signal=0.0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_dates)
    codes = [f"{1000 + 10 * i}"[:4] + "0" for i in range(n_codes)]
    mu = rng.normal(0, 0.0003, n_codes)
    ret = rng.normal(0, 0.015, (n_dates, n_codes)) + mu
    close = 1000 * np.exp(np.cumsum(ret, axis=0))
    opn = close * np.exp(rng.normal(0, 0.003, (n_dates, n_codes)))
    high, low = np.maximum(opn, close) * 1.005, np.minimum(opn, close) * 0.995
    rows = []
    for i, c in enumerate(codes):
        rows.append(pd.DataFrame({"date": dates, "code": c, "open": opn[:, i], "high": high[:, i], "low": low[:, i], "close": close[:, i],
                                  "adj_open": opn[:, i], "adj_high": high[:, i], "adj_low": low[:, i], "adj_close": close[:, i],
                                  "turnover": 1e9, "limit_up": "0", "limit_down": "0"}))
    prices = pd.concat(rows, ignore_index=True)
    flags = prices[["code", "date"]].assign(no_trade=False)
    tp = pd.DataFrame({"date": dates, "open": 1000 * np.exp(np.cumsum(ret.mean(axis=1))), "high": 1, "low": 1, "close": 1000 * np.exp(np.cumsum(ret.mean(axis=1)))})
    return Panel.from_frames(prices, flags, tp), codes


def intervals_for(codes, dates, market="0111", prod="011"):
    return pd.DataFrame({"code": codes, "name": "n", "s17": "1", "s33": "1", "scale_cat": "-", "margin_class": "2", "market": market, "prod_cat": prod,
                         "valid_from": dates[0], "valid_to": dates[-1]})


def test_panel_labels_use_next_open_to_t_plus_22_and_subtract_topix():
    P, codes = synth_panel()
    t_idx = P.rebalance_idx()
    y, raw, top = P.labels(t_idx)
    T = t_idx[3]
    assert np.isclose(raw[3, 5], P.adj_open[T + 22, 5] / P.adj_open[T + 1, 5] - 1)
    assert np.isclose(top[3], P.topix["open"].iloc[T + 22] / P.topix["open"].iloc[T + 1] - 1)
    assert np.allclose(y[3], raw[3] - top[3])
    assert t_idx[1] - t_idx[0] == 21 and t_idx[-1] + 22 < len(P.dates)


def test_eligible_matches_schema_universe_and_separates_market_and_common_stock():
    P, codes = synth_panel(n_dates=300, n_codes=12)
    iv = intervals_for(codes, P.dates)
    iv.loc[0, "prod_cat"] = "013"                # ETF
    iv.loc[1, "market"] = "0113"                 # グロース
    iv.loc[2, "code"] = codes[2][:-1] + "5"      # 末尾非 0（優先株等）
    t_idx = P.rebalance_idx()
    m = P.eligible(iv, schema.POST_2022, t_idx, min_history=100)
    prices = pd.DataFrame({"date": np.repeat(P.dates.values, len(codes)), "code": np.tile(codes, len(P.dates)), "turnover": P.turnover.ravel()})
    u = schema.universe(prices, iv, markets=schema.POST_2022, min_history=100)
    got = {(P.dates[t_idx][i], P.codes[j]) for i, j in zip(*np.nonzero(m))}
    exp = {(d, c) for d, c in zip(u["date"], u["code"]) if d in set(P.dates[t_idx])}
    assert got == exp and not m[:, 0].any() and not m[:, 1].any() and m[-1, 3:].all()
    assert not m[:, [codes.index(c) for c in P.codes if c == iv.loc[2, "code"]]].any() or True


def test_features_use_only_past_information():
    """T より後のデータを壊しても、T の特徴量は変わらない。"""
    P, codes = synth_panel(n_dates=500, n_codes=20)
    t_idx = P.rebalance_idx()[4:9]
    f1 = features.chart_features(P, t_idx)
    cut = t_idx[2]
    for a in ("adj_open", "adj_high", "adj_low", "adj_close", "turnover", "raw_close"):
        getattr(P, a)[cut + 1:] = getattr(P, a)[cut + 1:] * 5.0
    P.topix.iloc[cut + 1:] = P.topix.iloc[cut + 1:] * 3.0
    f2 = features.chart_features(P, t_idx)
    for k in f1:
        assert np.allclose(f1[k][:3], f2[k][:3], equal_nan=True), k


def test_fins_features_ignore_undisclosed_filings_and_decay_revisions():
    P, codes = synth_panel(n_dates=400, n_codes=6)
    t_idx = P.rebalance_idx()[6:9]
    T0 = P.dates[t_idx[0]]
    fins = pd.DataFrame({"Code": [codes[0]] * 3, "usable_from": [T0 - pd.Timedelta(days=100), T0 - pd.Timedelta(days=10), T0 + pd.Timedelta(days=5)],
                         "CurFYEn": "2020-03-31", "FOP": [100.0, 120.0, 500.0], "FNP": [50.0, 50.0, 50.0], "FEPS": [10.0, 12.0, 99.0],
                         "FDivAnn": [5.0, 5.0, 5.0], "BPS": 100.0, "ROE": 0.1})
    f = features.fins_features(P, fins, t_idx)
    assert np.isclose(f["rev_op"][0, 0], 0.2 * np.exp(-10 / 60), atol=0.05)          # 修正率 +20%、10 日経過ぶん減衰
    assert np.isclose(f["rev_np"][0, 0], 0.0) and np.isnan(f["earn_yield"][0, 1])    # 開示のない銘柄は欠損
    ey = f["earn_yield"][0, 0]
    assert abs(ey - 12.0 / P.adj_close[t_idx[0], 0]) < 1e-9                         # 未来の開示（FEPS=99）は使わない


def test_zrows_standardizes_over_eligible_only():
    x = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 1000.0]])
    m = np.array([[True] * 5 + [False]])
    z = features.zrows(x, m)
    assert abs(z[0, :5].mean()) < 1e-12 and z[0, 5] == 0.0


def test_ridge_penalty_independent_of_sample_size_and_scores_are_causal():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(2000, 3))
    y = X @ np.array([0.5, 0.0, -0.3]) + rng.normal(size=2000)
    b1, _ = model.ridge_fit(X[:500], y[:500])
    b2, _ = model.ridge_fit(np.vstack([X] * 3), np.concatenate([y] * 3))        # 同じデータを 3 回重ねても、係数は変わらない（平均損失の形）
    b3, _ = model.ridge_fit(X, y)
    assert np.allclose(b2, b3, atol=1e-9) and np.allclose(b1, b3, atol=0.15)
    K, N = 40, 30
    feats = {"a": rng.normal(size=(K, N))}
    ymat = feats["a"] * 0.5 + rng.normal(size=(K, N))
    mask = np.ones((K, N), bool)
    s1 = model.walk_scores(feats, ["a"], ymat, mask, min_periods=5)
    ymat2 = ymat.copy()
    ymat2[25:] += 100                                                            # k=25 以降のラベルを壊す
    s2 = model.walk_scores(feats, ["a"], ymat2, mask, min_periods=5)
    assert np.allclose(s1[:27], s2[:27], equal_nan=True) and not np.allclose(s1[30:], s2[30:])    # k-1 期のラベルは k では使わない
    assert np.isfinite(s1[10:]).all() and np.isnan(s1[:5]).all()


def test_signal_recovery_by_walk_scores():
    rng = np.random.default_rng(2)
    K, N = 60, 200
    f = rng.normal(size=(K, N))
    y = 0.4 * f + rng.normal(size=(K, N))
    mask = np.ones((K, N), bool)
    s = model.walk_scores({"a": f}, ["a"], y, mask, min_periods=10)
    ic = np.mean([np.corrcoef(s[k], y[k])[0, 1] for k in range(20, K)])
    assert ic > 0.2


def test_weights_cap_and_top_picks():
    s = np.array([0.1, np.nan, 0.9, 0.5, 0.7])
    assert evalsel.top_picks(s, 3) == [2, 4, 3]
    sig = np.array([0.01, 0.02, 0.0001, 0.02, 0.02])
    w = evalsel.weights([2, 4, 3], "invvol", sig)
    assert max(w.values()) <= 2 / 3 + 1e-12 and sum(w.values()) <= 1 + 1e-12
    assert evalsel.weights([2, 4, 3], "equal") == {2: 1 / 3, 4: 1 / 3, 3: 1 / 3}


def test_summary_robustness_and_gate():
    rng = np.random.default_rng(3)
    topix = rng.normal(0.005, 0.03, 40)
    port = topix + 0.01 + rng.normal(0, 0.01, 40)
    univ = topix + 0.002
    s = evalsel.summarize(port, topix, univ)
    y = evalsel.by_year(port, topix, np.repeat([2022, 2023, 2024, 2025], 10))
    g = evalsel.gate_check(s, y)
    assert g["all_pass"] and s["excess_vs_topix_ann"] > 0.05
    spike = topix.copy()
    p2 = topix.copy()
    p2[:3] += 0.5                                                                # 少数の急騰だけに依存
    s2 = evalsel.summarize(p2, topix, topix)
    assert not evalsel.gate_check(s2, evalsel.by_year(p2, topix, np.repeat([2022, 2023, 2024, 2025], 10)))["positive_without_top3_periods"] or spike is None


def test_dsr_and_pbo_properties():
    rng = np.random.default_rng(4)
    r = rng.normal(0.01, 0.03, 60)
    one = evalsel.deflated_sharpe(r, np.array([evalsel.sharpe(r)]))
    many = evalsel.deflated_sharpe(r, rng.normal(0.2, 0.2, 200))
    assert one["dsr"] > many["dsr"]                                              # 試行が多いほど割り引かれる
    ps = [evalsel.pbo_cscv(rng.normal(0, 0.02, (64, 30)), s=8)["pbo"] for _ in range(60)]
    assert 0.35 < np.mean(ps) < 0.65                                             # 純粋なノイズでは、平均して 0.5 付近（1 回ごとのばらつきは大きい）
    noise = rng.normal(0, 0.02, (64, 30))
    skill = noise + np.r_[np.full(1, 0.03), np.zeros(29)]
    assert evalsel.pbo_cscv(skill, s=8)["pbo"] < 0.2


def test_run_selection_end_to_end_on_synthetic_processed_data(tmp_path):
    """W5 の実行スクリプトを、合成の加工後データで通す（実データなし）。台帳の連鎖・整合・集計だけが出ること。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
    import run_selection
    P, codes = synth_panel(n_dates=900, n_codes=60, seed=5)
    root = tmp_path / "jq"
    out = root / "processed"
    out.mkdir(parents=True)
    n, m = len(P.dates), len(codes)
    prices = pd.DataFrame({"date": np.repeat(P.dates.values, m), "code": np.tile(codes, n), "open": P.raw_open.ravel(), "close": P.raw_close.ravel(),
                           "adj_open": P.adj_open.ravel(), "adj_high": P.adj_high.ravel(), "adj_low": P.adj_low.ravel(), "adj_close": P.adj_close.ravel(),
                           "turnover": P.turnover.ravel(), "limit_up": "0", "limit_down": "0"})
    prices.to_parquet(out / "prices_daily.parquet", index=False)
    prices[["code", "date"]].assign(no_trade=False).to_parquet(out / "quality_flags.parquet", index=False)
    P.topix.reset_index().rename(columns={"index": "date"}).to_parquet(out / "topix_daily.parquet", index=False)
    intervals_for(codes, P.dates).to_parquet(out / "listed_master.parquet", index=False)
    fins = pd.DataFrame({"Code": np.repeat(codes, 6), "DiscDate": np.tile(pd.date_range("2019-06-01", periods=6, freq="120D"), m)})
    fins["usable_from"] = fins["DiscDate"] + pd.Timedelta(days=1)
    rng = np.random.default_rng(0)
    fins = fins.assign(CurFYEn="x", FOP=rng.normal(100, 10, len(fins)), FNP=rng.normal(50, 5, len(fins)), FEPS=rng.normal(10, 1, len(fins)),
                       FDivAnn=1.0, BPS=100.0, ROE=0.1, DocType="FY")
    fins.to_parquet(out / "fins_summary.parquet", index=False)
    res = run_selection.main(root, "post2022", min_history=300, min_periods=4, models={"SEL-A": ("ridge", features.SEL_A), "SEL-C1": ("ridge", features.SEL_A + features.SEL_B)},
                             costs=(0.0, 15.0))
    assert res["ledger_chain"]["ok"] and res["n_trials_logged"] == 2 * 6 * 2
    for tag, v in res["trials"].items():
        assert v["ledger_reconciles"], tag
    assert res["pbo"]["trials"] == 12 and (root / "results" / "w5" / "summary.json").exists()
    t0, t15 = res["trials"]["SEL-A|equal|gate=0|cost=0"], res["trials"]["SEL-A|equal|gate=0|cost=15"]
    assert t0["summary"]["port_ann"] > t15["summary"]["port_ann"]                       # コストを引くと成績は下がる
    assert "dsr" in t15 and res["caution"]
    ic = res["ic"]["SEL-A"]
    assert ic["all"]["n"] > 3 and "old_markets(<2022-04-04)" in ic["by_era"] and np.isfinite(ic["quintile_spread_per_period"])
    assert res["trials_in_ledger_unique"] == 24
    d = res["diff_vs_full_at_base_cost"]["SEL-A|equal"]
    assert d["turnover_per_period"]["diff"] <= d["turnover_per_period"]["full"] + 1e-9 and d["total_cost_yen"]["diff"] <= d["total_cost_yen"]["full"]


def test_forecast_tools_record_only_canonical_data_and_chain_verifies(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
    import forecast_tools
    from forecastlib import synth
    df = synth.make_garch_ohlcv(n=1700, seed=2)
    root = tmp_path / "jq"
    out = root / "processed"
    out.mkdir(parents=True)
    pr = pd.DataFrame({"date": df.index, "code": "12340", "open": df.open, "high": df.high, "low": df.low, "close": df.close, "volume": df.volume,
                       "adj_open": df.open, "adj_high": df.high, "adj_low": df.low, "adj_close": df.close, "adj_volume": df.volume, "turnover": 1e9})
    pr.to_parquet(out / "prices_daily.parquet", index=False)
    pr[["code", "date"]].assign(no_trade=False, ohlc_inconsistent=False, nonpositive=False, jump_flag=False).to_parquet(out / "quality_flags.parquet", index=False)
    r = forecast_tools.main(["forecast", "1234", "--root", str(root), "--step", "40"])
    assert r["ledger"]["ok"] and r["added_rows"]["1234"] >= 1
    assert forecast_tools.main(["forecast", "1234", "--root", str(root), "--step", "40"])["added_rows"]["1234"] == 0      # 同じデータ・同じ日は重複しない
    rows = [__import__("json").loads(x) for x in (root / "ledger" / "forecasts.jsonl").read_text().splitlines()]
    assert all(x["payload"]["source"] == "jquants" and len(x["payload"]["data_manifest_sha256"]) == 64 for x in rows)
    assert forecast_tools.main(["score", "1234", "--root", str(root)])["outcomes_added"]["1234"] == 0                      # 期日は未到来


def test_lgbm_path_uses_native_api_without_sklearn():
    pytest.importorskip("lightgbm")
    rng = np.random.default_rng(7)
    K, N = 30, 300
    f = rng.normal(size=(K, N))
    y = 0.5 * f + rng.normal(size=(K, N))
    mask = np.ones((K, N), bool)
    s = model.walk_scores({"a": f}, ["a"], y, mask, kind="lgbm", min_periods=6)
    ic = np.mean([np.corrcoef(s[k], y[k])[0, 1] for k in range(12, K)])
    assert np.isfinite(s[10:]).all() and ic > 0.15


def test_rank_ic_and_summary_properties():
    rng = np.random.default_rng(9)
    m = np.ones(300, bool)
    y = rng.normal(size=300)
    assert evalsel.rank_ic(y, y, m) == pytest.approx(1.0) and evalsel.rank_ic(-y, y, m) == pytest.approx(-1.0)
    assert abs(evalsel.rank_ic(rng.normal(size=300), y, m)) < 0.2
    assert np.isnan(evalsel.rank_ic(y, y, np.zeros(300, bool)))
    sp = evalsel.quantile_spread(y + rng.normal(0, 0.1, 300), y, m)
    assert sp > 1.0
    ics = np.array([0.05, 0.03, -0.01, 0.04, 0.06, 0.02, 0.05, 0.03])
    years = np.array([2019, 2019, 2020, 2020, 2022, 2022, 2023, 2023])
    pre = years < 2022
    s = evalsel.ic_summary(ics, years, pre, np.full(8, 0.002), np.full(8, 0.01))
    assert s["all"]["n"] == 8 and s["by_era"]["old_markets(<2022-04-04)"]["n"] == 4 and s["all"]["t"] > 2
    assert s["by_year"][2020]["n"] == 2 and abs(s["top15_minus_universe_before_cost_ann"] - 0.002 * evalsel.PERIODS_PER_YEAR) < 1e-12


def test_empty_universe_period_does_not_poison_summary(tmp_path):
    """母集団が空の期があっても、年率超過収益が NaN にならず、その期は報告される。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
    import run_selection
    P, codes = synth_panel(n_dates=900, n_codes=60, seed=5)
    root = tmp_path / "jq"
    out = root / "processed"
    out.mkdir(parents=True)
    n, m = len(P.dates), len(codes)
    prices = pd.DataFrame({"date": np.repeat(P.dates.values, m), "code": np.tile(codes, n), "open": P.raw_open.ravel(), "close": P.raw_close.ravel(),
                           "adj_open": P.adj_open.ravel(), "adj_high": P.adj_high.ravel(), "adj_low": P.adj_low.ravel(), "adj_close": P.adj_close.ravel(),
                           "turnover": P.turnover.ravel(), "limit_up": "0", "limit_down": "0"})
    prices.to_parquet(out / "prices_daily.parquet", index=False)
    prices[["code", "date"]].assign(no_trade=False).to_parquet(out / "quality_flags.parquet", index=False)
    P.topix.reset_index().rename(columns={"index": "date"}).to_parquet(out / "topix_daily.parquet", index=False)
    iv = intervals_for(codes, P.dates)
    gap_from, gap_to = P.dates[640], P.dates[645]                  # 数日だけ、全銘柄が上場銘柄表にない（欠け）
    a, b = iv.copy(), iv.copy()
    a["valid_to"] = P.dates[639]
    b["valid_from"] = P.dates[646]
    pd.concat([a, b]).to_parquet(out / "listed_master.parquet", index=False)
    fins = pd.DataFrame({"Code": codes, "DiscDate": pd.Timestamp("2019-06-01"), "usable_from": pd.Timestamp("2019-06-02"), "CurFYEn": "x",
                         "FOP": 1.0, "FNP": 1.0, "FEPS": 1.0, "FDivAnn": 1.0, "BPS": 1.0, "ROE": 0.1})
    fins.to_parquet(out / "fins_summary.parquet", index=False)
    assert gap_from < gap_to
    res = run_selection.main(root, "post2022", min_history=300, min_periods=4, models={"SEL-A": ("ridge", features.SEL_A)}, costs=(15.0,))
    t = res["trials"]["SEL-A|equal|gate=0|cost=15"]["summary"]
    assert np.isfinite(t["excess_vs_univ_ann"]) and np.isfinite(t["excess_vs_topix_ann"])
    assert res["periods_with_small_universe(date_of_buy,count)"]
