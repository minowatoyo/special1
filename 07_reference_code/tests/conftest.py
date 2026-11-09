"""テスト用の合成 OHLCV（固定シード）。実市場データではない。"""
import numpy as np
import pandas as pd
import pytest


def make_ohlcv(n: int = 1500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0003, 0.015, n)
    close = 100.0 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]] * np.exp(rng.normal(0.0, 0.003, n))
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, 0.006, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, 0.006, n)))
    volume = rng.integers(100_000, 2_000_000, n).astype(float)
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx
    )


@pytest.fixture(scope="session")
def ohlcv() -> pd.DataFrame:
    return make_ohlcv()
