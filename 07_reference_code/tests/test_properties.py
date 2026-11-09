"""手計算の例・定義どおりの愚直実装・数学的性質による検証（TA-Lib に対応物がない指標を含む）。"""
import numpy as np
import pandas as pd
import pytest

from chartlib import candles as cn
from chartlib import indicators as ind
from chartlib import swings


def S(values):
    return pd.Series(values, dtype=float)


# ------------------------------------------------------------------ 平滑化・基本
def test_wilder_smooth_recursion_and_seed():
    x = S(np.arange(1.0, 21.0))
    w = ind.wilder_smooth(x, 5)
    assert w.iloc[:4].isna().all()
    assert w.iloc[4] == pytest.approx(3.0)                       # 最初の5個の平均
    assert w.iloc[5] == pytest.approx((3.0 * 4 + 6.0) / 5)       # (前値*(n-1)+今値)/n


def test_ema_sma_seed_and_recursion():
    x = S([1, 2, 3, 4, 5, 6.0])
    e = ind.ema(x, 3)
    assert e.iloc[:2].isna().all()
    assert e.iloc[2] == pytest.approx(2.0)                       # 最初の3個の平均
    assert e.iloc[3] == pytest.approx(0.5 * 4 + 0.5 * 2.0)       # alpha = 2/(3+1) = 0.5


def test_ema_handles_leading_nan_like_ema_of_ema():
    x = S([np.nan, np.nan, 1, 2, 3, 4, 5.0])
    e = ind.ema(x, 3)
    assert e.iloc[:4].isna().all() and e.iloc[4] == pytest.approx(2.0)


def test_hma_constant_series_is_constant():
    x = S(np.full(80, 50.0))
    assert ind.hma(x, 16).dropna().eq(50.0).all()


# ------------------------------------------------------------------ RSI / ストキャス
def test_rsi_extremes_and_range(ohlcv):
    up = S(np.arange(1.0, 60.0))
    assert ind.rsi(up, 14).dropna().eq(100.0).all()
    assert ind.rsi(up[::-1].reset_index(drop=True), 14).dropna().eq(0.0).all()
    r = ind.rsi(ohlcv.close, 14).dropna()
    assert r.between(0, 100).all()


def test_rsi_cutler_differs_from_wilder(ohlcv):
    a, b = ind.rsi(ohlcv.close, 14), ind.rsi(ohlcv.close, 14, method="cutler")
    assert (a - b).abs().dropna().max() > 1.0                    # 実装差が実際に現れる


def test_stochastic_range_and_japanese_mapping(ohlcv):
    st = ind.stochastic(ohlcv.high, ohlcv.low, ohlcv.close, 14, 3, 3)
    assert st["fast_k"].dropna().between(0, 100).all()
    # 日本のスロー: (SMA3(fast_k), SMA3(SMA3(fast_k))) = 欧米の (slow_k, slow_d)
    pd.testing.assert_series_equal(st["slow_k"], st["fast_k"].rolling(3).mean(), check_names=False)
    pd.testing.assert_series_equal(st["slow_d"], st["slow_k"].rolling(3).mean(), check_names=False)


# ------------------------------------------------------------------ ボラティリティ
def test_bollinger_properties(ohlcv):
    b0 = ind.bollinger(ohlcv.close, 20, 2.0, ddof=0)
    b1 = ind.bollinger(ohlcv.close, 20, 2.0, ddof=1)
    half0, half1 = (b0.upper - b0.middle), (b1.upper - b1.middle)
    ratio = (half1 / half0).dropna()
    assert ratio.sub(np.sqrt(20 / 19)).abs().max() < 1e-12      # 標本標準偏差は母集団の sqrt(n/(n-1)) 倍
    flat = ind.bollinger(S(np.full(40, 10.0)))
    assert flat["bandwidth"].dropna().eq(0.0).all()
    assert (b0.percent_b.dropna().between(-1, 2)).all()


def test_true_range_and_atr_constant_range():
    h, l, c = S([12, 12, 12, 12, 12, 12.0]), S([10, 10, 10, 10, 10, 10.0]), S([11, 11, 11, 11, 11, 11.0])
    tr = ind.true_range(h, l, c)
    assert np.isnan(tr.iloc[0]) and tr.iloc[1:].eq(2.0).all()
    assert ind.atr(h, l, c, 3).dropna().eq(2.0).all()


def test_donchian_exclude_current_is_previous_window(ohlcv):
    d = ohlcv
    inc = ind.donchian(d.high, d.low, 20)
    exc = ind.donchian(d.high, d.low, 20, exclude_current=True)
    t = 500
    assert exc["upper"].iloc[t] == d.high.iloc[t - 20:t].max()
    assert inc["upper"].iloc[t] == d.high.iloc[t - 19:t + 1].max()


def test_parabolic_sar_is_below_lows_in_uptrend_and_above_highs_in_downtrend():
    # 単調上昇 → SAR は常に安値より下
    n = 60
    base = np.linspace(100, 160, n)
    h, l = S(base + 1), S(base - 1)
    sar = ind.parabolic_sar(h, l)
    assert (sar.dropna() < l.loc[sar.dropna().index]).all()
    # 単調下降 → SAR は常に高値より上
    base = np.linspace(160, 100, n)
    h, l = S(base + 1), S(base - 1)
    sar = ind.parabolic_sar(h, l)
    assert (sar.dropna() > h.loc[sar.dropna().index]).all()


def test_aroon_extremes():
    up = S(np.arange(1.0, 40.0))
    a = ind.aroon(up + 1, up - 1, 14)
    assert a["aroon_up"].dropna().eq(100.0).all() and a["aroon_down"].dropna().eq(0.0).all()


# ------------------------------------------------------------------ 出来高
def test_obv_hand_example():
    close, vol = S([10, 11, 10, 10, 12.0]), S([100, 200, 300, 400, 500.0])
    assert ind.obv(close, vol).tolist() == [100.0, 300.0, 0.0, 0.0, 500.0]


def test_ad_line_clv_edges():
    # 終値=高値 → CLV=+1、終値=安値 → CLV=-1、H=L → 0
    h, l, c, v = S([10, 10, 10.0]), S([8, 8, 10.0]), S([10, 8, 10.0]), S([100, 100, 100.0])
    assert ind.ad_line(h, l, c, v).tolist() == [100.0, 0.0, 0.0]


def test_vwap_anchor_resets():
    h = l = c = S([10, 20, 30, 40.0])
    v = S([1, 1, 1, 3.0])
    cum = ind.vwap(h, l, c, v)
    assert cum.iloc[-1] == pytest.approx((10 + 20 + 30 + 120) / 6)
    anchored = ind.vwap(h, l, c, v, anchor=pd.Series(["a", "a", "b", "b"]))
    assert anchored.tolist() == pytest.approx([10.0, 15.0, 30.0, (30 + 120) / 4])


# ------------------------------------------------------------------ 一目均衡表・平均足・ピボット・窓
def test_ichimoku_matches_literal_definition():
    high = S([10, 12, 11, 13, 15, 14, 16, 18, 17, 19])
    low = S([8, 9, 9, 10, 12, 12, 13, 15, 14, 16])
    close = S([9, 11, 10, 12, 14, 13, 15, 17, 16, 18])
    tn, kj, sb, disp = 2, 3, 4, 2
    r = ind.ichimoku(high, low, close, tn, kj, sb, disp)
    n = len(high)

    def mid(width, t):
        if t < width - 1:
            return np.nan
        return (high[t - width + 1:t + 1].max() + low[t - width + 1:t + 1].min()) / 2.0

    tk = [mid(tn, t) for t in range(n)]
    ki = [mid(kj, t) for t in range(n)]
    sa_raw = [(a + b) / 2.0 for a, b in zip(tk, ki)]
    sb_raw = [mid(sb, t) for t in range(n)]
    shifted = lambda arr, t: arr[t - disp] if t - disp >= 0 else np.nan  # noqa: E731
    np.testing.assert_allclose(r["tenkan"], tk, equal_nan=True)
    np.testing.assert_allclose(r["kijun"], ki, equal_nan=True)
    np.testing.assert_allclose(r["senkou_a"], [shifted(sa_raw, t) for t in range(n)], equal_nan=True)
    np.testing.assert_allclose(r["senkou_b"], [shifted(sb_raw, t) for t in range(n)], equal_nan=True)
    np.testing.assert_allclose(r["chikou"], [close[t + disp] if t + disp < n else np.nan for t in range(n)],
                               equal_nan=True)


def test_ichimoku_default_periods_lookback():
    n = 120
    base = S(np.linspace(100, 200, n))
    r = ind.ichimoku(base + 1, base - 1, base)
    assert r["tenkan"].first_valid_index() == 8                  # 9本目
    assert r["kijun"].first_valid_index() == 25                  # 26本目
    assert r["senkou_a"].first_valid_index() == 25 + 26          # 基準線が出た日 + 26 本後に描かれる
    assert r["senkou_b"].first_valid_index() == 51 + 26          # 52本目 + 26


def test_heikin_ashi_hand_example_and_invariants(ohlcv):
    o, h, l, c = S([10, 11.0]), S([12, 13.0]), S([9, 10.0]), S([11, 12.0])
    ha = ind.heikin_ashi(o, h, l, c)
    assert ha["close"].tolist() == [10.5, 11.5]
    assert ha["open"].tolist() == [10.5, 10.5]
    assert ha["high"].tolist() == [12.0, 13.0] and ha["low"].tolist() == [9.0, 10.0]
    d = ind.heikin_ashi(ohlcv.open, ohlcv.high, ohlcv.low, ohlcv.close)
    assert (d["high"] >= d[["open", "close"]].max(axis=1) - 1e-12).all()
    assert (d["low"] <= d[["open", "close"]].min(axis=1) + 1e-12).all()


def test_pivot_points_hand_example():
    h, l, c = S([110, 0.0]), S([90, 0.0]), S([100, 0.0])        # 2本目の足は何でもよい。参照するのは1本目
    p = ind.pivot_points(h, l, c, "classic").iloc[1]
    assert (p.p, p.r1, p.s1, p.r2, p.s2, p.r3, p.s3) == pytest.approx((100, 110, 90, 120, 80, 130, 70))
    f = ind.pivot_points(h, l, c, "fibonacci").iloc[1]
    assert (f.r1, f.r2, f.r3) == pytest.approx((107.64, 112.36, 120.0))
    w = ind.pivot_points(h, l, c, "woodie").iloc[1]
    assert w.p == pytest.approx(100.0)
    cam = ind.pivot_points(h, l, c, "camarilla").iloc[1]
    assert cam.r4 == pytest.approx(100 + 20 * 1.1 / 2) and cam.s1 == pytest.approx(100 - 20 * 1.1 / 12)
    assert ind.pivot_points(h, l, c).iloc[0].isna().all()        # 前の足がない最初の1本は NaN


def test_gaps_hand_example():
    # 手計算: t=1 は 安値11 > 前日高値10 → 窓上げ(幅1)。t=2 は 安値12 = 前日高値12 → 窓なし。
    #         t=3 は 高値9 < 前日安値12 → 窓下げ(幅-3)。t=4 は 安値10 > 前日高値9 → 窓上げ(幅1)。
    h = S([10, 12, 13, 9, 11.0])
    l = S([8, 11, 12, 7, 10.0])
    g = ind.gaps(h, l)
    assert g["gap_up"].tolist() == [False, True, False, False, True]
    assert g["gap_down"].tolist() == [False, False, False, True, False]
    assert np.isnan(g["gap_size"].iloc[0])
    assert g["gap_size"].iloc[1:].tolist() == [1.0, 0.0, -3.0, 1.0]


# ------------------------------------------------------------------ 追加: 解析的に期待値が分かる例
def test_cmf_extremes():
    low = S(np.arange(10.0, 60.0))
    high = low + 1.0
    vol = S(np.full(50, 100.0))
    assert ind.chaikin_money_flow(high, low, high, vol, 20).dropna().eq(1.0).all()    # 終値=高値 → +1
    assert ind.chaikin_money_flow(high, low, low, vol, 20).dropna().eq(-1.0).all()    # 終値=安値 → -1


def test_keltner_bands_on_linear_series():
    c = S(np.arange(100.0, 160.0))
    h, l = c + 1.0, c - 1.0                                       # TR は常に 2 → ATR = 2
    k = ind.keltner(h, l, c, n_ema=20, n_atr=10, mult=2.5)
    d = (k["upper"] - k["middle"]).dropna()
    assert d.sub(5.0).abs().max() < 1e-12
    assert (k["middle"] - k["lower"]).dropna().sub(5.0).abs().max() < 1e-12


def test_force_index_with_n1_is_raw_force():
    c, v = S([10, 11, 10.5, 12.0]), S([100, 200, 300, 400.0])
    f = ind.force_index(c, v, 1)
    assert np.isnan(f.iloc[0])
    assert f.iloc[1:].tolist() == pytest.approx([200.0, -150.0, 600.0])


def test_hma_on_linear_series_has_small_lag():
    # 直線 x_t = t では WMA(n) = t-(n-1)/3。HMA(16) は t - 2/3（SMA(16) の遅れ 7.5 本に比べ著しく小さい）
    x = S(np.arange(0.0, 100.0))
    h = ind.hma(x, 16).dropna()
    assert h.sub(x.loc[h.index] - 2.0 / 3.0).abs().max() < 1e-9
