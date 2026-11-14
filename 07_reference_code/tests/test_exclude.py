"""除外フィルター（合成データ）。定義、除外後の繰り上がり、植えた効果の検出、先読みがないこと、確認期間の読みの記録。"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_rules import _write_processed
from test_selectlib import synth_panel

from selectlib import exclude, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def test_flags_use_same_day_quantiles_and_missing_margin_is_never_flagged():
    K, N = 2, 100
    rng = np.random.default_rng(0)
    mask = np.ones((K, N), bool)
    sd = rng.uniform(0, 10, (K, N))
    mm = {"short_days": sd.copy(), "ratio": rng.uniform(0.5, 5, (K, N)), "long_days": rng.uniform(0, 10, (K, N))}
    mm["short_days"][1, :20] = np.nan                                  # 信用残がない銘柄
    chart = {"ret21": np.full((K, N), 0.2), "vol60": rng.uniform(0, 1, (K, N))}
    f = exclude.flags(mm, chart, mask)
    assert abs(f["X1_short_days_top"][0].mean() - 0.20) < 0.03 and abs(f["X2_ratio_bottom"][0].mean() - 0.20) < 0.03
    assert not f["X1_short_days_top"][1, :20].any()                    # 欠損は掛からない
    # X3 は、買い残が下位 1/3（その日の分位）かつ 21 日 +15% 超。X4 は 高ボラ上位 1/3 かつ 買い残下位 1/3
    light = mm["long_days"][0] <= np.percentile(mm["long_days"][0], 33.3)
    assert (f["X3_surge_light_long"][0] == light).all()
    hv = chart["vol60"][0] > np.percentile(chart["vol60"][0], 66.7)
    assert (f["X4_highvol_light_long"][0] == (light & hv)).all()
    assert (f["U12"] == (f["X1_short_days_top"] | f["X2_ratio_bottom"])).all() and (f["U1234"] >= f["U12"]).all()
    # 対象外の銘柄は掛からない
    mask2 = mask.copy()
    mask2[0, :50] = False
    assert not exclude.flags(mm, chart, mask2)["X1_short_days_top"][0, :50].any()


def test_picks_excluding_promotes_next_ranks_and_stats():
    sc = np.arange(30, dtype=float)                                    # 29 が最上位
    fl = np.zeros(30, bool)
    fl[[29, 27, 20]] = True
    p = exclude.picks_excluding(sc, fl)
    assert len(p) == 15 and not (set(p) & {29, 27, 20}) and p[0] == 28 and set(p) == {28, 26, 25, 24, 23, 22, 21} | set(range(12, 20))
    # 植えた効果: 掛かった銘柄は −1% なら、検出される。掛からなければ有意でない
    rng = np.random.default_rng(1)
    K, N = 60, 200
    mask = np.ones((K, N), bool)
    ex = rng.normal(0, 0.05, (K, N))
    flag = rng.random((K, N)) < 0.2
    ex[flag] -= 0.01
    r = exclude.effect(flag, ex, mask, list(range(K)))
    assert r["mean"] < -0.005 and r["t"] < -2.5 and abs(r["flagged_share_mean"] - 0.2) < 0.03
    null = exclude.effect(rng.random((K, N)) < 0.2, rng.normal(0, 0.05, (K, N)), mask, list(range(K)))
    assert abs(null["t"]) < 3
    d = exclude.paired(np.zeros(K), np.full(K, 0.01) + rng.normal(0, 0.002, K), list(range(K)))
    assert d["mean"] > 0.009 and d["p"] < 1e-6
    q = exclude.bh_flags({"a": 0.001, "b": 0.5, "c": None})
    assert set(q) == {"a", "b"} and q["a"] < q["b"]


def _margin(P, codes, short_level, seed=0, step=5, lag=1):
    rng = np.random.default_rng(seed)
    idx = np.arange(300, len(P.dates) - lag - 1, step)
    rows = []
    for j, c in enumerate(codes):
        rows.append(pd.DataFrame({"code": c, "date": P.dates[idx], "long_vol": 1e5 * rng.uniform(0.8, 1.2, len(idx)),
                                  "short_vol": short_level[j] * rng.uniform(0.8, 1.2, len(idx)), "usable_from": P.dates[idx + lag]}))
    return pd.concat(rows, ignore_index=True)


def _setup(tmp, drift_flagged=-0.002, seed=3):
    P, codes = synth_panel(n_dates=2000, n_codes=40, seed=seed)
    flagged = np.arange(40) % 5 == 0                                   # 8 銘柄（上位 1/5 に当たる）
    t = np.arange(len(P.dates))[:, None]
    scale = np.exp(np.where(flagged[None, :], drift_flagged, 0.0) * t)
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr *= scale
    root = tmp / "jq"
    _write_processed(root, P, codes)
    short = np.where(flagged, 3e6, 1e4)
    _margin(P, codes, short, seed=seed).to_parquet(root / "processed" / "margin_interest.parquet", index=False)
    return P, codes, root


def test_study_detects_planted_effect_and_records_one_confirmation_read(tmp_path):
    import exclusion_study
    P, codes, root = _setup(tmp_path)
    res = exclusion_study.main(root, min_history=250, min_periods=6)
    assert res["periods"]["discovery"] >= 8 and res["periods"]["confirmation"] >= 20 and res["ledger_chain"]["ok"]
    A = res["A_effect_of_flagged_stocks_21d_excess"]
    x1 = A["X1_short_days_top"]
    assert x1["discovery"]["mean"] < -0.02 and x1["confirmation"]["mean"] < -0.02 and x1["confirmation"]["p"] < 0.01 and x1["works"]
    B = res["B_top15_with_exclusion_minus_baseline_21d"]["X1_short_days_top"]
    # 順位予測がチャートの特徴量で、植えた下落をすでに避けているので、除かれる銘柄は少ない（仕組みの確認: 除かれ、悪化しない）
    assert B["confirmation"]["mean"] >= 0.0 and 0.3 < B["confirmation"]["removed_per_period_mean"] <= 15
    assert (root / "results" / "exclusion" / "summary.json").exists()
    rows = [json.loads(line) for line in (root / "ledger" / "trials.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reads = [r for r in rows if r["type"] == "confirmation_read" and r["payload"]["family"].startswith("exclusion_v1")]
    assert len(reads) == 1
    assert set(res["primary_family"]) == {"X1_short_days_top", "X2_ratio_bottom", "U12"}


def test_null_does_not_claim_usable_and_no_lookahead_into_confirmation(tmp_path):
    import exclusion_study
    P, codes, root = _setup(tmp_path / "a", drift_flagged=0.0, seed=5)
    res = exclusion_study.main(root, min_history=250, min_periods=6)
    assert not any(res["B_top15_with_exclusion_minus_baseline_21d"][n]["usable"] for n in exclusion_study.exclude.PRIMARY)
    # 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = tmp_path / "b" / "jq"
    _write_processed(root2, P, codes)
    pd.read_parquet(root / "processed" / "margin_interest.parquet").to_parquet(root2 / "processed" / "margin_interest.parquet", index=False)
    res2 = exclusion_study.main(root2, min_history=250, min_periods=6)
    for sec in ("A_effect_of_flagged_stocks_21d_excess", "B_top15_with_exclusion_minus_baseline_21d"):
        for n in exclusion_study.exclude.ALL_NAMES:
            assert res[sec][n]["discovery"] == res2[sec][n]["discovery"]
