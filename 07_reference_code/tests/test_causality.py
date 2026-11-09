"""先読み（look-ahead）がないことの検証。

どの指標も、系列を時点 k で打ち切って計算した結果が、全期間で計算した結果の先頭 k 本と一致するはず
（未来のデータが過去の値に影響しない）。バックテストの最も基本的な健全性チェックで、自作指標にも使える。
例外: 一目均衡表の chikou（遅行スパン）は「描画位置」の都合で未来の終値を使う列なので除外する。
"""
import numpy as np
import pandas as pd
import pytest

from chartlib import candles as cn
from chartlib import indicators as ind
from chartlib import swings

CUTS = (300, 700, 1100)

FUNCS = {
    "sma": lambda d: ind.sma(d.close, 20),
    "ema": lambda d: ind.ema(d.close, 20),
    "wma": lambda d: ind.wma(d.close, 20),
    "dema": lambda d: ind.dema(d.close, 20),
    "tema": lambda d: ind.tema(d.close, 20),
    "hma": lambda d: ind.hma(d.close, 20),
    "kama": lambda d: ind.kama(d.close, 10),
    "rsi": lambda d: ind.rsi(d.close, 14),
    "rsi_cutler": lambda d: ind.rsi(d.close, 14, method="cutler"),
    "stochastic": lambda d: ind.stochastic(d.high, d.low, d.close),
    "macd": lambda d: ind.macd(d.close),
    "cci": lambda d: ind.cci(d.high, d.low, d.close, 20),
    "williams_r": lambda d: ind.williams_r(d.high, d.low, d.close, 14),
    "roc": lambda d: ind.roc(d.close, 10),
    "ultimate": lambda d: ind.ultimate_oscillator(d.high, d.low, d.close),
    "mfi": lambda d: ind.mfi(d.high, d.low, d.close, d.volume),
    "trix": lambda d: ind.trix(d.close, 15),
    "bollinger": lambda d: ind.bollinger(d.close),
    "atr": lambda d: ind.atr(d.high, d.low, d.close),
    "dmi_adx": lambda d: ind.dmi_adx(d.high, d.low, d.close),
    "sar": lambda d: ind.parabolic_sar(d.high, d.low),
    "donchian": lambda d: ind.donchian(d.high, d.low, 20),
    "donchian_ex": lambda d: ind.donchian(d.high, d.low, 20, exclude_current=True),
    "keltner": lambda d: ind.keltner(d.high, d.low, d.close),
    "aroon": lambda d: ind.aroon(d.high, d.low, 14),
    "obv": lambda d: ind.obv(d.close, d.volume),
    "ad_line": lambda d: ind.ad_line(d.high, d.low, d.close, d.volume),
    "cmf": lambda d: ind.chaikin_money_flow(d.high, d.low, d.close, d.volume),
    "vwap": lambda d: ind.vwap(d.high, d.low, d.close, d.volume),
    "force": lambda d: ind.force_index(d.close, d.volume),
    "ichimoku_no_chikou": lambda d: ind.ichimoku(d.high, d.low, d.close).drop(columns="chikou"),
    "heikin_ashi": lambda d: ind.heikin_ashi(d.open, d.high, d.low, d.close),
    "pivot_classic": lambda d: ind.pivot_points(d.high, d.low, d.close, "classic"),
    "gaps": lambda d: ind.gaps(d.high, d.low),
    "engulfing": lambda d: cn.bullish_engulfing(d.open, d.high, d.low, d.close),
    "morning_star": lambda d: cn.morning_star(d.open, d.high, d.low, d.close),
    "three_soldiers": lambda d: cn.three_white_soldiers(d.open, d.high, d.low, d.close),
}


@pytest.mark.parametrize("name", list(FUNCS))
def test_no_lookahead(ohlcv, name):
    f = FUNCS[name]
    full = f(ohlcv)
    for k in CUTS:
        part = f(ohlcv.iloc[:k])
        got, exp = part, full.iloc[:k]
        if isinstance(got, pd.DataFrame):
            pd.testing.assert_frame_equal(got, exp, check_exact=False, rtol=1e-9, atol=1e-9)
        else:
            pd.testing.assert_series_equal(got, exp, check_exact=False, rtol=1e-9, atol=1e-9)


def test_chikou_uses_future_close_by_design(ohlcv):
    """遅行スパンの描画位置 t の値は close[t+26]。シグナル判定に使うと先読みになる。"""
    r = ind.ichimoku(ohlcv.high, ohlcv.low, ohlcv.close)
    assert r["chikou"].iloc[100] == pytest.approx(ohlcv.close.iloc[126])
    assert r["chikou"].iloc[-26:].isna().all()


@pytest.mark.parametrize("fn,kwargs", [
    (swings.swing_points, dict(left=2, right=2)),
    (swings.zigzag, dict(threshold=0.05)),
])
def test_swings_confirmed_pivots_do_not_change_with_future_data(ohlcv, fn, kwargs):
    """確定済みの転換点（confirmed_pos < k）は、k 以降のデータを足しても変わらない。"""
    full = fn(ohlcv.high, ohlcv.low, **kwargs)
    for k in CUTS:
        part = fn(ohlcv.high.iloc[:k], ohlcv.low.iloc[:k], **kwargs)
        exp = full[full["confirmed_pos"] <= k - 1].reset_index(drop=True)
        pd.testing.assert_frame_equal(part.reset_index(drop=True), exp, check_exact=False, rtol=1e-12)
