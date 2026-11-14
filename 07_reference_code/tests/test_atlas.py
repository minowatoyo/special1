"""パターン図鑑（合成データ）。植えたパターンを検出すること、偶然の組み合わせが補正で消えること、先読みがないこと。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_selectlib import intervals_for
from test_seasonal import seasonal_panel

from selectlib import atlas, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))


def fake_obs(n_periods=60, per=400, seed=0, planted=None, effect=0.01):
    rng = np.random.default_rng(seed)
    n = n_periods * per
    sizes = {k: len(v) for k, v in atlas.LABELS.items()}
    sizes["sector"] = 18
    obs = {k: rng.integers(0, s, n).astype(np.int8) for k, s in sizes.items()}
    obs["period"] = np.repeat(np.arange(n_periods), per)
    obs["y"] = rng.normal(0, 0.08, n)
    if planted:
        m = np.ones(n, bool)
        for f, v in planted.items():
            m &= obs[f] == v
        obs["y"][m] += effect
    dates = pd.date_range("2018-01-05", periods=n_periods, freq="30D")
    obs["buy_date"] = pd.DatetimeIndex(dates)
    obs["sell_date"] = pd.DatetimeIndex(dates + pd.Timedelta(days=30))
    obs["sector_labels"] = [f"S{i}" for i in range(17)] + ["不明"]
    obs["T"] = np.arange(n_periods)
    return obs


def test_mine_finds_planted_pattern_first():
    obs = fake_obs(planted={"price": 0, "ret21": 0}, effect=0.03)
    mask = np.ones(len(obs["y"]), bool)
    res = atlas.mine(obs, mask, features=["price", "ret21", "vol", "trend", "market"], max_order=2, min_obs=300)
    top = max(res, key=lambda r: r["t"])
    assert set(top["sub"]) == {"price", "ret21"} and top["mean"] > 0.02 and top["t"] > 8
    assert atlas.describe(obs, top) == "株価<300円 ＆ 21日で−15%以下"
    assert len(res) > 100 and all(r["obs"] >= 300 and r["periods"] >= atlas.MIN_PERIODS for r in res)


def test_null_best_pattern_does_not_survive_bh_and_does_not_replicate():
    from forecastlib import stats as st
    best_q, reps = [], 0
    for seed in range(4):
        obs = fake_obs(seed=seed + 10, n_periods=80)
        d = np.arange(len(obs["y"])) < len(obs["y"]) // 2
        c = ~d
        res = atlas.mine(obs, d, features=["price", "ret21", "vol", "trend", "market", "month", "revision"], max_order=3, min_obs=300)
        q = st.bh_fdr(np.array([r["p"] for r in res]))
        best_q.append(q.min())
        top = sorted(res, key=lambda r: -r["t"])[:30]
        ev = [atlas.evaluate(obs, c, r["sub"], r["key"], r["dims"]) for r in top]
        reps += sum(1 for e in ev if np.isfinite(e["p"]) and e["p"] < 0.05 and e["mean"] > 0)
        assert max(r["t"] for r in res) > 2.5 and len(res) > 500                 # 数千の組み合わせから見える「勝者」は、帰無でも大きく見える
    assert np.mean(best_q) > 0.10                                                  # 補正すると消える
    assert reps <= 0.12 * 30 * 4 + 3                                               # 確認期間で p<0.05 になる割合は、偶然の水準（5% 前後）


def test_evaluate_matches_mine_on_same_mask_and_year_summary():
    obs = fake_obs(planted={"vol": 2, "trend": 1}, effect=0.02)
    mask = np.ones(len(obs["y"]), bool)
    res = atlas.mine(obs, mask, features=["vol", "trend", "price"], max_order=2, min_obs=300)
    r = next(x for x in res if set(x["sub"]) == {"vol", "trend"} and atlas.describe(obs, x) == "高ボラ ＆ 75日線の下")
    e = atlas.evaluate(obs, mask, r["sub"], r["key"], r["dims"])
    assert abs(e["mean"] - r["mean"]) < 1e-9 and abs(e["t"] - r["t"]) < 1e-6 and e["obs"] == r["obs"]
    ys = atlas.year_summary(r)
    assert ys["years_with_data"] >= 3 and ys["same_sign_years"] >= 3


def test_build_obs_and_study_end_to_end_without_lookahead(tmp_path):
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))
    import pattern_atlas
    from test_rules import _write_processed
    P, codes, prices = seasonal_panel(n_codes=60, seed=7, effect=0.0, turnover=3e7)
    a = tmp_path / "a"
    _write_processed(a, P, codes)
    res = pattern_atlas.main(a, min_obs=200, min_periods=10)
    assert res["combinations_tested"] > 100 and res["observations"]["discovery"] > 3000 and res["observations"]["confirmation"] > 1000
    assert len(res["long_patterns"]) <= pattern_atlas.TOP_LONG and res["ledger_chain"]["ok"]
    assert (a / "results" / "atlas" / "summary.json").exists()
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果（報告する組み合わせと平均）は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    b = tmp_path / "b"
    _write_processed(b, P, codes)
    res2 = pattern_atlas.main(b, min_obs=200, min_periods=10)
    key = lambda r: [(x["pattern"], x["mean_excess_21d"], x["obs"]) for x in r["long_patterns"] + r["avoid_patterns"]]  # noqa: E731
    assert key(res) == key(res2) and json.dumps(res["observations"]) == json.dumps(res2["observations"])
