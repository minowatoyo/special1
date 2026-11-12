"""forecastlib の読み込み・検査と統計関数のテスト。"""
import math

import numpy as np
import pandas as pd
import pytest

from forecastlib import data, stats as st, synth


def _write(tmp_path, name, text, encoding="utf-8"):
    p = tmp_path / name
    p.write_bytes(text.encode(encoding))
    return p


def test_load_stooq_format_sorted_and_typed(tmp_path):
    p = _write(tmp_path, "a.csv", "Date,Open,High,Low,Close,Volume\n2024-01-05,101,103,100,102,2000\n2024-01-04,100,102,99,101,1000\n")
    df = data.load_ohlcv(p)
    assert list(df.columns[:5]) == data.COLUMNS
    assert df.index.is_monotonic_increasing and df.index[0] == pd.Timestamp("2024-01-04")
    assert df["close"].tolist() == [101.0, 102.0]


def test_load_japanese_headers_cp932_and_commas(tmp_path):
    txt = "日付,始値,高値,安値,終値,出来高\n2024/01/04,\"1,000\",\"1,020\",990,\"1,010\",\"1,234,500\"\n2024/01/05,1010,1030,1000,1020,-\n"
    df = data.load_ohlcv(_write(tmp_path, "j.csv", txt, "cp932"))
    assert df["high"].iloc[0] == 1020.0 and df["volume"].iloc[0] == 1234500.0
    assert math.isnan(df["volume"].iloc[1])


def test_load_yyyymmdd_duplicates_and_yahoo_adj_close(tmp_path):
    txt = "Date,Open,High,Low,Close,Adj Close,Volume\n20240104,100,102,99,101,95,1000\n20240104,100,102,99,101.5,95.5,1100\n20240105,101,103,100,102,96,2000\n"
    df = data.load_ohlcv(_write(tmp_path, "y.csv", txt))
    assert len(df) == 2 and df.attrs["duplicate_dates_removed"] == 1
    assert df["close"].iloc[0] == 101.5 and "adj_close" in df.columns


def test_load_rejects_html_and_missing_columns(tmp_path):
    with pytest.raises(ValueError):
        data.load_ohlcv(_write(tmp_path, "h.csv", "<!DOCTYPE html><html><body>verify</body></html>"))
    with pytest.raises(ValueError):
        data.load_ohlcv(_write(tmp_path, "m.csv", "Date,Close\n2024-01-04,100\n"))


def test_unadjusted_split_is_detected_and_adjusted():
    df = synth.make_garch_ohlcv(n=800, seed=3)
    raw = df.copy()
    cut = df.index[400]
    before = raw.index < cut
    raw.loc[before, ["open", "high", "low", "close"]] *= 5.0          # 1:5 分割が未調整の系列
    raw.loc[before, "volume"] /= 5.0
    rep = data.validate_ohlcv(raw)
    assert [s["date"] for s in rep["suspect_splits"]] == [str(cut.date())]
    assert rep["suspect_splits"][0]["factor"] == 5.0
    fixed = data.adjust_splits(raw, {cut: 5.0})
    assert np.allclose(fixed["close"].to_numpy(), df["close"].to_numpy())
    assert np.allclose(fixed["volume"].to_numpy(), df["volume"].to_numpy())
    assert data.validate_ohlcv(fixed)["suspect_splits"] == []


def test_validate_flags_inconsistent_ohlc_and_stale_data():
    df = synth.make_garch_ohlcv(n=600, seed=4)
    df.iloc[10, df.columns.get_loc("high")] = df["low"].iloc[10] * 0.9
    rep = data.validate_ohlcv(df, today=df.index[-1] + pd.Timedelta(days=30))
    assert any("矛盾" in w for w in rep["warnings"])
    assert any("古い" in w for w in rep["warnings"])
    assert any("履歴が短い" in w for w in rep["warnings"])


def test_suggest_split_factor():
    assert data.suggest_split_factor(0.2) == 5.0
    assert data.suggest_split_factor(0.51) == 2.0
    assert data.suggest_split_factor(2.02) == 0.5
    assert data.suggest_split_factor(0.80) is None


# ---------------------------------------------------------------- 統計
def test_sorted_quantiles_match_numpy():
    rng = np.random.default_rng(0)
    x = np.sort(rng.normal(size=777))
    taus = st.tau_grid(100)
    assert np.allclose(st.sorted_quantiles(x, taus), np.quantile(x, taus))


def test_crps_grid_close_to_exact():
    rng = np.random.default_rng(1)
    sample = rng.standard_t(5, size=5000)
    taus = st.tau_grid(100)
    grid = np.quantile(sample, taus)
    for y in (-2.5, -0.3, 0.0, 0.8, 3.0):
        exact = st.crps_exact(y, sample)
        assert abs(st.crps_from_grid(y, grid, taus) - exact) / exact < 0.03


def test_crps_prefers_true_distribution_on_average():
    rng = np.random.default_rng(2)
    taus = st.tau_grid(100)
    true = np.quantile(rng.normal(0, 1, 20000), taus)
    wide = 2.0 * true
    shifted = true + 0.7
    ys = rng.normal(0, 1, 3000)
    f = lambda g: np.mean([st.crps_from_grid(y, g, taus) for y in ys])  # noqa: E731
    assert f(true) < f(wide) and f(true) < f(shifted)


def test_cdf_and_quantile_from_grid_are_inverse():
    taus = st.tau_grid(100)
    grid = np.quantile(np.random.default_rng(3).normal(size=10000), taus)
    for p in (0.05, 0.25, 0.5, 0.9):
        assert abs(st.cdf_from_grid(st.quantile_from_grid(p, grid, taus), grid, taus) - p) < 1e-9
    assert st.cdf_from_grid(-99.0, grid, taus) < 0.005 and st.cdf_from_grid(99.0, grid, taus) > 0.995


def test_stationary_bootstrap_indices():
    rng = np.random.default_rng(4)
    idx = st.stationary_bootstrap_indices(500, 20.0, 200, rng)
    assert idx.shape == (200, 500) and idx.min() >= 0 and idx.max() < 500
    cont = (np.diff(idx, axis=1) % 500 == 1).mean()                 # 続きの添字の割合 ≒ 1 − 1/ブロック長
    assert 0.93 < cont < 0.97


def test_bh_fdr_known_values():
    q = st.bh_fdr(np.array([0.01, 0.04, 0.03, 0.20, np.nan]))
    assert np.allclose(q[:4], [0.04, 0.0533333, 0.0533333, 0.20], atol=1e-6) and math.isnan(q[4])


def test_dm_and_reality_check_detect_real_difference_only():
    rng = np.random.default_rng(5)
    n = 1500
    base = rng.gamma(2.0, 1.0, n)
    same = base + rng.normal(0, 0.5, n)
    better = base - 0.15 + rng.normal(0, 0.5, n)
    assert st.dm_test(better, base, h=5)["p"] < 0.01
    assert st.dm_test(same, base, h=5)["p"] > 0.05
    null_family = np.column_stack([base - (base + rng.normal(0, 0.5, n)) for _ in range(6)])
    assert st.reality_check(null_family, 10.0, 500, 1)["p"] > 0.10
    real_family = np.column_stack([null_family[:, :5], base - better])
    rc = st.reality_check(real_family, 10.0, 500, 1)
    assert rc["p"] < 0.01 and rc["best"] == 5


def test_reality_check_size_under_null():
    """候補が 6 個すべて無意味なとき、p<0.10 になる割合が名目に近いこと（多重比較の補正の確認）。"""
    rej_rc = rej_naive = 0
    for s in range(120):
        rng = np.random.default_rng(1000 + s)
        d = rng.normal(0, 1, (400, 6))
        rej_rc += st.reality_check(d, 5.0, 300, s)["p"] < 0.10
        best = d.mean(axis=0).argmax()
        rej_naive += st.dm_test(-d[:, best], np.zeros(400), h=1)["p"] < 0.10
    assert rej_rc / 120 < 0.18                       # 名目 10% の近く
    assert rej_naive / 120 > 0.30                    # 補正しないと偽陽性が大きく増える


def test_nw_ols_recovers_coefficients_and_widens_se_for_autocorrelation():
    rng = np.random.default_rng(6)
    n = 3000
    x = rng.normal(size=n)
    e = np.convolve(rng.normal(size=n + 20), np.ones(21) / math.sqrt(21), mode="valid")   # MA(20)
    xs = np.convolve(rng.normal(size=n + 20), np.ones(21) / math.sqrt(21), mode="valid")
    y = 1.0 + 0.5 * xs + e
    X = np.column_stack([np.ones(n), xs])
    r0, r1 = st.nw_ols(y, X, 0), st.nw_ols(y, X, 30)
    assert abs(r1["beta"][1] - 0.5) < 0.15
    assert r1["se"][1] > 1.5 * r0["se"][1]
    assert x.shape == (n,)
