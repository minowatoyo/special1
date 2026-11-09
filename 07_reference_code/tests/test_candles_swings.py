"""ローソク足パターン（手作りの足）とスイング検出（既知の経路）のテスト。"""
import numpy as np
import pandas as pd
import pytest

from chartlib import candles as cn
from chartlib import swings


def bars(rows):
    """rows: [(O, H, L, C), ...] → (open, high, low, close) の4つの Series"""
    df = pd.DataFrame(rows, columns=["o", "h", "l", "c"], dtype=float)
    return df.o, df.h, df.l, df.c


def last(sr):
    return bool(sr.iloc[-1])


def test_features_basic():
    o, h, l, c = bars([(10, 12, 9, 11)])
    f = cn.features(o, h, l, c)
    assert f["body"].iloc[0] == 1 and f["range"].iloc[0] == 3
    assert f["upper"].iloc[0] == 1 and f["lower"].iloc[0] == 1
    assert f["body_ratio"].iloc[0] == pytest.approx(1 / 3)
    assert f["direction"].iloc[0] == 1


def test_doji_marubozu_hammer_shooting_star():
    assert last(cn.doji(*bars([(10, 11, 9, 10.05)])))
    assert not last(cn.doji(*bars([(10, 11, 9, 10.8)])))
    assert last(cn.marubozu(*bars([(10, 12, 10, 12)])))
    assert not last(cn.marubozu(*bars([(10, 12, 9, 11)])))
    assert last(cn.hammer_shape(*bars([(10.6, 11.0, 8.0, 11.0)])))
    assert not last(cn.hammer_shape(*bars([(10, 12, 9, 11)])))
    assert last(cn.shooting_star_shape(*bars([(10.0, 13.0, 9.7, 9.7)])))
    assert not last(cn.shooting_star_shape(*bars([(10.6, 11.0, 8.0, 11.0)])))


def test_engulfing_and_harami():
    assert last(cn.bullish_engulfing(*bars([(10, 10.2, 8.8, 9), (8.9, 10.5, 8.8, 10.3)])))
    assert not last(cn.bullish_engulfing(*bars([(10, 10.2, 8.8, 9), (9.2, 9.8, 9.1, 9.7)])))   # 包んでいない
    assert last(cn.bearish_engulfing(*bars([(9, 10.2, 8.8, 10), (10.1, 10.2, 8.5, 8.7)])))
    assert last(cn.bullish_harami(*bars([(10, 10.1, 7.9, 8), (8.5, 9.3, 8.4, 9.2)])))
    assert last(cn.bearish_harami(*bars([(8, 10.1, 7.9, 10), (9.5, 9.6, 8.6, 8.8)])))
    assert not last(cn.bullish_harami(*bars([(10, 10.1, 7.9, 8), (7.5, 10.5, 7.4, 10.4)])))   # 外側（包み線）


def test_piercing_and_dark_cloud():
    assert last(cn.piercing_line(*bars([(10, 10.1, 7.9, 8), (7.8, 9.6, 7.7, 9.5)])))
    assert not last(cn.piercing_line(*bars([(10, 10.1, 7.9, 8), (7.8, 8.8, 7.7, 8.7)])))      # 中心(9)に届かない
    assert not last(cn.piercing_line(*bars([(10, 10.1, 7.9, 8), (7.8, 10.5, 7.7, 10.4)])))    # 始値超え = 包み線
    assert last(cn.dark_cloud_cover(*bars([(8, 10.1, 7.9, 10), (10.2, 10.3, 8.4, 8.5)])))


def test_morning_and_evening_star():
    ms = bars([(12, 12.1, 8.9, 9), (8.5, 8.8, 8.3, 8.6), (8.8, 11.1, 8.7, 11)])
    assert last(cn.morning_star(*ms))
    es = bars([(9, 12.1, 8.9, 12), (12.5, 12.7, 12.2, 12.4), (12.2, 12.3, 9.4, 9.5)])
    assert last(cn.evening_star(*es))
    assert not last(cn.morning_star(*es))


def test_three_soldiers_and_crows():
    tws = bars([(10, 11.05, 9.95, 11), (10.5, 12.05, 10.45, 12), (11.5, 13.05, 11.45, 13)])
    assert last(cn.three_white_soldiers(*tws))
    tbc = bars([(13, 13.05, 11.95, 12), (12.5, 12.55, 10.95, 11), (11.5, 11.55, 9.95, 10)])
    assert last(cn.three_black_crows(*tbc))
    assert not last(cn.three_white_soldiers(*tbc))


def test_pattern_outputs_are_boolean_and_complete_on_random_data(ohlcv):
    d = ohlcv
    for fn in (cn.doji, cn.marubozu, cn.hammer_shape, cn.shooting_star_shape, cn.bullish_engulfing,
               cn.bearish_engulfing, cn.bullish_harami, cn.bearish_harami, cn.piercing_line,
               cn.dark_cloud_cover, cn.morning_star, cn.evening_star, cn.three_white_soldiers,
               cn.three_black_crows):
        r = fn(d.open, d.high, d.low, d.close)
        assert r.dtype == bool and len(r) == len(d)


def test_prior_trend_sign():
    c = pd.Series(np.arange(1.0, 30.0))
    assert (cn.prior_trend(c, 5).dropna() == 1).all()
    assert (cn.prior_trend(c[::-1].reset_index(drop=True), 5).dropna() == -1).all()


# ------------------------------------------------------------------ swings
def test_swing_points_known_example():
    high = pd.Series([1, 2, 3, 2, 1, 2, 3, 4, 3, 2.0])
    low = pd.Series([0, 1, 2, 1, 0, 1, 2, 3, 2, 1.0])
    sp = swings.swing_points(high, low, left=2, right=2)
    highs = sp[sp.kind == "H"]
    lows = sp[sp.kind == "L"]
    assert highs["pos"].tolist() == [2, 7]
    assert lows["pos"].tolist() == [4]
    assert (sp["confirmed_pos"] - sp["pos"]).eq(2).all()          # 確定は右側 right 本が揃ってから


def _path_frame():
    knots_x = [0, 10, 20, 30, 40]
    knots_y = [100, 120, 105, 130, 110]
    close = np.interp(np.arange(41), knots_x, knots_y)
    idx = pd.bdate_range("2024-01-01", periods=41)
    return pd.Series(close + 0.05, index=idx), pd.Series(close - 0.05, index=idx)


def test_zigzag_known_path_and_confirmation_delay():
    high, low = _path_frame()
    thr = 0.08
    zz = swings.zigzag(high, low, thr)
    assert zz["kind"].tolist() == ["L", "H", "L", "H"]            # 最後の安値(40)は未確定なので返さない
    assert zz["pos"].tolist() == [0, 10, 20, 30]
    assert (zz["confirmed_pos"] > zz["pos"]).all()
    # 独立の愚直な確認: 高値の確定は「極値から thr 以上下げた最初の足」
    h10 = high.iloc[10]
    first_drop = next(i for i in range(11, 41) if low.iloc[i] <= h10 * (1 - thr))
    assert zz["confirmed_pos"].iloc[1] == first_drop


def test_zigzag_alternates_and_pivots_are_extremes_between_neighbours(ohlcv):
    d = ohlcv
    zz = swings.zigzag(d.high, d.low, 0.06)
    assert len(zz) > 10
    assert (zz["kind"].iloc[1:].to_numpy() != zz["kind"].iloc[:-1].to_numpy()).all()   # H/L が交互
    assert (zz["confirmed_pos"] > zz["pos"]).all()
    for (a, b) in zip(zz.itertuples(index=False), list(zz.itertuples(index=False))[1:]):
        if a.kind == "L":      # 安値 → 高値 の区間では、高値の価格が区間内の最高値
            assert b.price == pytest.approx(d.high.iloc[a.pos:b.pos + 1].max())
        else:
            assert b.price == pytest.approx(d.low.iloc[a.pos:b.pos + 1].min())


def test_zigzag_threshold_series_matches_scalar(ohlcv):
    d = ohlcv
    a = swings.zigzag(d.high, d.low, 0.05)
    b = swings.zigzag(d.high, d.low, pd.Series(0.05, index=d.index))
    pd.testing.assert_frame_equal(a, b)
