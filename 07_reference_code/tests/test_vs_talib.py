"""chartlib.indicators と TA-Lib の数値照合。

assert_same は (1) NaN の位置（= ルックバック期間）が完全一致、(2) 値が許容誤差内で一致、を確認する。
EMA の初期値の取り方が TA-Lib と異なる指標（MACD の速い EMA など）は、初期の影響が指数的に消えた
warmup 以降のみ比較する（指数平滑の初期差は (1-alpha)^k で減衰する）。
"""
import numpy as np
import pandas as pd
import pytest

talib = pytest.importorskip("talib")

from chartlib import indicators as ind  # noqa: E402


def arr(s):
    return s.to_numpy(dtype=float)


def as_list(x):
    if isinstance(x, pd.DataFrame):
        return [x[c].to_numpy(dtype=float) for c in x.columns]
    if isinstance(x, pd.Series):
        return [x.to_numpy(dtype=float)]
    if isinstance(x, (tuple, list)):
        return [np.asarray(a, dtype=float) for a in x]
    return [np.asarray(x, dtype=float)]


def assert_same(mine, ref, warmup=0, rtol=1e-9, atol=1e-9, lenient_prefix=False):
    """lenient_prefix=True: TA-Lib が複数出力を「最後に有効化する系列の開始位置」へ揃えて返す場合
    （STOCH / STOCHF / MACD）に使う。自前の方が早く有効になるのは許容し、TA-Lib が値を返す位置で比較する。"""
    ms, rs = as_list(mine), as_list(ref)
    assert len(ms) == len(rs)
    for m, r in zip(ms, rs):
        if lenient_prefix:
            valid = ~np.isnan(r)
            assert not np.isnan(m[valid]).any(), "TA-Lib が値を返す位置で自前が NaN"
            keep = valid.copy()
            keep[:warmup] = False
            np.testing.assert_allclose(m[keep], r[keep], rtol=rtol, atol=atol)
        else:
            assert np.array_equal(np.isnan(m), np.isnan(r)), "NaN位置（ルックバック）が TA-Lib と異なる"
            np.testing.assert_allclose(m[warmup:], r[warmup:], rtol=rtol, atol=atol, equal_nan=True)


# 名前: (自前の計算, TA-Lib の計算, warmup)  — warmup=0 は先頭から完全一致を要求
CASES = {
    "SMA(20)": (lambda d: ind.sma(d.close, 20), lambda d: talib.SMA(arr(d.close), 20), 0),
    "EMA(20)": (lambda d: ind.ema(d.close, 20), lambda d: talib.EMA(arr(d.close), 20), 0),
    "WMA(20)": (lambda d: ind.wma(d.close, 20), lambda d: talib.WMA(arr(d.close), 20), 0),
    "DEMA(20)": (lambda d: ind.dema(d.close, 20), lambda d: talib.DEMA(arr(d.close), 20), 0),
    "TEMA(20)": (lambda d: ind.tema(d.close, 20), lambda d: talib.TEMA(arr(d.close), 20), 0),
    "KAMA(10)": (lambda d: ind.kama(d.close, 10), lambda d: talib.KAMA(arr(d.close), 10), 0),
    "RSI(14) Wilder": (lambda d: ind.rsi(d.close, 14), lambda d: talib.RSI(arr(d.close), 14), 0),
    "STOCH(14,3,3)": (
        lambda d: ind.stochastic(d.high, d.low, d.close, 14, 3, 3)[["slow_k", "slow_d"]],
        lambda d: talib.STOCH(arr(d.high), arr(d.low), arr(d.close), fastk_period=14,
                              slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0), 0),
    "STOCHF(14,3)": (
        lambda d: pd.DataFrame({
            "fastk": ind.stochastic(d.high, d.low, d.close, 14, 1, 1)["fast_k"],
            "fastd": ind.stochastic(d.high, d.low, d.close, 14, 1, 1)["fast_k"].rolling(3).mean()}),
        lambda d: talib.STOCHF(arr(d.high), arr(d.low), arr(d.close), fastk_period=14,
                               fastd_period=3, fastd_matype=0), 0),
    "CCI(20)": (lambda d: ind.cci(d.high, d.low, d.close, 20),
                lambda d: talib.CCI(arr(d.high), arr(d.low), arr(d.close), 20), 0),
    "WILLR(14)": (lambda d: ind.williams_r(d.high, d.low, d.close, 14),
                  lambda d: talib.WILLR(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "ROC(10)": (lambda d: ind.roc(d.close, 10), lambda d: talib.ROC(arr(d.close), 10), 0),
    "MOM(10)": (lambda d: ind.momentum(d.close, 10), lambda d: talib.MOM(arr(d.close), 10), 0),
    "ULTOSC(7,14,28)": (lambda d: ind.ultimate_oscillator(d.high, d.low, d.close, 7, 14, 28),
                        lambda d: talib.ULTOSC(arr(d.high), arr(d.low), arr(d.close), 7, 14, 28), 0),
    "MFI(14)": (lambda d: ind.mfi(d.high, d.low, d.close, d.volume, 14),
                lambda d: talib.MFI(arr(d.high), arr(d.low), arr(d.close), arr(d.volume), 14), 0),
    "BBANDS(20,2) ddof=0": (
        lambda d: ind.bollinger(d.close, 20, 2.0, ddof=0)[["upper", "middle", "lower"]],
        lambda d: talib.BBANDS(arr(d.close), timeperiod=20, nbdevup=2, nbdevdn=2, matype=0), 0),
    "TRANGE": (lambda d: ind.true_range(d.high, d.low, d.close),
               lambda d: talib.TRANGE(arr(d.high), arr(d.low), arr(d.close)), 0),
    "ATR(14)": (lambda d: ind.atr(d.high, d.low, d.close, 14),
                lambda d: talib.ATR(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "NATR(14)": (lambda d: ind.natr(d.high, d.low, d.close, 14),
                 lambda d: talib.NATR(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "+DI(14)": (lambda d: ind.dmi_adx(d.high, d.low, d.close, 14, variant="talib")["plus_di"],
                lambda d: talib.PLUS_DI(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "-DI(14)": (lambda d: ind.dmi_adx(d.high, d.low, d.close, 14, variant="talib")["minus_di"],
                lambda d: talib.MINUS_DI(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "DX(14)": (lambda d: ind.dmi_adx(d.high, d.low, d.close, 14, variant="talib")["dx"],
               lambda d: talib.DX(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "ADX(14)": (lambda d: ind.dmi_adx(d.high, d.low, d.close, 14, variant="talib")["adx"],
                lambda d: talib.ADX(arr(d.high), arr(d.low), arr(d.close), 14), 0),
    "SAR(0.02,0.2)": (lambda d: ind.parabolic_sar(d.high, d.low, 0.02, 0.2),
                      lambda d: talib.SAR(arr(d.high), arr(d.low), acceleration=0.02, maximum=0.2), 0),
    "AROON(14)": (lambda d: ind.aroon(d.high, d.low, 14)[["aroon_down", "aroon_up"]],
                  lambda d: talib.AROON(arr(d.high), arr(d.low), 14), 0),
    "OBV": (lambda d: ind.obv(d.close, d.volume), lambda d: talib.OBV(arr(d.close), arr(d.volume)), 0),
    "AD": (lambda d: ind.ad_line(d.high, d.low, d.close, d.volume),
           lambda d: talib.AD(arr(d.high), arr(d.low), arr(d.close), arr(d.volume)), 0),
    # EMA の初期値が TA-Lib と異なる指標: 初期の影響が消えた後（warmup 以降）を比較
    "MACD(12,26,9)": (lambda d: ind.macd(d.close, 12, 26, 9),
                      lambda d: talib.MACD(arr(d.close), 12, 26, 9), 400),
    "TRIX(30)": (lambda d: ind.trix(d.close, 30), lambda d: talib.TRIX(arr(d.close), 30), 600),
}


LENIENT = {"STOCH(14,3,3)", "STOCHF(14,3)", "MACD(12,26,9)"}


@pytest.mark.parametrize("name", list(CASES))
def test_matches_talib(ohlcv, name):
    mine_fn, ref_fn, warmup = CASES[name]
    assert_same(mine_fn(ohlcv), ref_fn(ohlcv), warmup=warmup, lenient_prefix=name in LENIENT)


def test_adosc_matches_talib_with_first_value_seed(ohlcv):
    """TA-Lib の ADOSC は EMA を最初の値で初期化する（SMA 初期化ではない）。"""
    d = ohlcv
    ad = ind.ad_line(d.high, d.low, d.close, d.volume)
    mine = ind.ema(ad, 3, seed="first") - ind.ema(ad, 10, seed="first")
    ref = talib.ADOSC(arr(d.high), arr(d.low), arr(d.close), arr(d.volume), 3, 10)
    m = mine.to_numpy()
    mask = ~np.isnan(ref)
    np.testing.assert_allclose(m[mask], ref[mask], rtol=1e-8, atol=1e-6)


def test_ema_seed_first_equals_pandas_ewm(ohlcv):
    x = ohlcv.close
    pd.testing.assert_series_equal(
        ind.ema(x, 20, seed="first"), x.ewm(span=20, adjust=False).mean(), check_names=False, rtol=1e-12)


def test_rsi_flat_series_is_nan():
    flat = pd.Series(np.full(50, 100.0))
    assert ind.rsi(flat, 14).isna().all()


def test_dmi_textbook_wilder_converges_to_talib(ohlcv):
    """ワイルダー原典の初期化（最初のn個の合計）と TA-Lib の初期化は、初期差が指数的に減衰して一致に向かう。"""
    d = ohlcv
    a = ind.dmi_adx(d.high, d.low, d.close, 14, variant="wilder")
    b = ind.dmi_adx(d.high, d.low, d.close, 14, variant="talib")
    early = (a["plus_di"] - b["plus_di"]).abs().iloc[14:20].max()
    late = (a - b).abs().iloc[400:].max().max()
    assert early > 1e-3, "初期にははっきり差があるはず"
    assert late < 1e-7, "400本後には事実上一致するはず"
