"""forecastlib に先読みがないことの検証。

系列を時点 k で打ち切って計算した結果が、全期間で計算した結果の同じ時点の値と一致すること
（未来のデータが過去の値に影響しない）。ボラティリティ予測、特徴量、シグナル、
ウォークフォワードの予測分布のすべてで確認する。
"""
import numpy as np
import pandas as pd
import pytest

from forecastlib import Config, features, prepare_asset, synth, vol, walk_forward

N = 1700
CUTS = (900, 1300)


@pytest.fixture(scope="module")
def df():
    return synth.make_garch_ohlcv(n=N, seed=11)


def _same_prefix(full, part, k):
    a = np.asarray(full)[:k]
    b = np.asarray(part)
    assert a.shape == b.shape
    both_nan = np.isnan(a.astype(float)) & np.isnan(b.astype(float))
    assert np.allclose(np.where(both_nan, 0.0, a.astype(float)), np.where(both_nan, 0.0, b.astype(float)), rtol=1e-9, atol=1e-12)


@pytest.mark.parametrize("k", CUTS)
def test_sigma_forecasts_are_causal(df, k):
    full = vol.sigma_forecasts(df, (5, 21, 63), min_train=300)
    part = vol.sigma_forecasts(df.iloc[:k], (5, 21, 63), min_train=300)
    for h in (5, 21, 63):
        for m in vol.SIGMA_MODELS:
            _same_prefix(full[h][m], part[h][m], k)
        assert np.isfinite(part[h]["S3"].iloc[-1])                # 最終日（結果が未確定の時点）にも予測が出ている


@pytest.mark.parametrize("k", CUTS)
def test_features_and_signals_are_causal(df, k):
    aux = {"mkt": (synth.make_garch_ohlcv(n=N, seed=12)["close"], 0), "fx": (synth.make_garch_ohlcv(n=N, seed=13)["close"], 1)}
    f_full = features.standardize_expanding(features.feature_frame(df, aux))
    f_part = features.standardize_expanding(features.feature_frame(df.iloc[:k], aux))
    for c in f_full.columns:
        _same_prefix(f_full[c], f_part[c], k)
    s_full, s_part = features.signal_frame(df), features.signal_frame(df.iloc[:k])
    assert (s_full.iloc[:k].to_numpy() == s_part.to_numpy()).all()
    assert s_full.dtypes.eq(bool).all()


def test_aux_lag_one_never_uses_same_day_value():
    idx = pd.bdate_range("2020-01-01", periods=10)
    a = pd.Series(np.arange(10, dtype=float) + 100.0, index=idx)
    lag0 = features.align_aux(idx, a, lag=0)
    lag1 = features.align_aux(idx, a, lag=1)
    assert (lag0.to_numpy() == a.to_numpy()).all()
    assert np.isnan(lag1.iloc[0]) and (lag1.iloc[1:].to_numpy() == a.iloc[:-1].to_numpy()).all()


def test_walk_forward_distributions_are_causal(df):
    """全期間の実行で時点 k-1 に作った分位点格子が、k で打ち切ったデータの最終予測と一致する（全モデル）。"""
    k = 1400
    cfg_full = Config(burn=700, har_min_train=300, min_fit=300, knn_min=300, knn_k=80, step=7, record_at=(k - 1,))
    cfg_part = Config(burn=700, har_min_train=300, min_fit=300, knn_min=300, knn_k=80, step=7)
    panel_df = synth.make_garch_ohlcv(n=N, seed=21)
    full = walk_forward(prepare_asset(df, "A", cfg_full), cfg_full, (prepare_asset(panel_df, "P", cfg_full),))
    part = walk_forward(prepare_asset(df.iloc[:k], "A", cfg_part), cfg_part, (prepare_asset(panel_df, "P", cfg_part),))
    checked = 0
    for h in cfg_full.horizons:
        rec, fin = full[h]["recorded"][k - 1], part[h]["final"]["grids"]
        assert set(rec) == set(fin)
        for m in rec:
            assert np.isfinite(rec[m]).all(), (h, m)
            assert np.allclose(rec[m], fin[m], rtol=1e-8, atol=1e-10), (h, m)
            checked += 1
    assert checked == 3 * 9


def test_future_shock_does_not_change_past_forecasts(df):
    """将来の価格を大きく書き換えても、それより前の時点の予測分布と採点対象外の値は変わらない。"""
    k = 1300
    cfg = Config(burn=700, har_min_train=300, min_fit=300, knn_min=300, knn_k=80, step=7, record_at=(k - 1,))
    shocked = df.copy()
    shocked.iloc[k:, :4] *= 1.8
    a = walk_forward(prepare_asset(df, "A", cfg), cfg)
    b = walk_forward(prepare_asset(shocked, "A", cfg), cfg)
    for h in cfg.horizons:
        for m in a[h]["recorded"][k - 1]:
            assert np.allclose(a[h]["recorded"][k - 1][m], b[h]["recorded"][k - 1][m], rtol=1e-8, atol=1e-10)


def test_panel_future_does_not_leak_into_target_forecasts(df):
    """プール推定に使う他銘柄の「将来の価格」を書き換えても、それより前の時点の予測分布は変わらない。"""
    k = 1300
    cfg = Config(burn=700, har_min_train=300, min_fit=300, knn_min=300, knn_k=80, step=7, record_at=(k - 1,))
    panel_df = synth.make_garch_ohlcv(n=N, seed=21)
    shocked = panel_df.copy()
    shocked.iloc[k:, :4] *= 1.8
    target = prepare_asset(df, "A", cfg)
    a = walk_forward(target, cfg, (prepare_asset(panel_df, "P", cfg),))
    b = walk_forward(target, cfg, (prepare_asset(shocked, "P", cfg),))
    solo = walk_forward(target, cfg)
    differs_from_solo = False
    for h in cfg.horizons:
        for m in ("T1", "T2", "T3", "E1"):
            ga, gb = a[h]["recorded"][k - 1][m], b[h]["recorded"][k - 1][m]
            assert np.allclose(ga, gb, rtol=1e-8, atol=1e-10), (h, m)
            differs_from_solo |= not np.allclose(ga, solo[h]["recorded"][k - 1][m], rtol=1e-6, atol=1e-9)
    assert differs_from_solo                      # プールが実際に効いている（他銘柄の行が推定に入っている）
