"""全銘柄での極端な出来事の漂流（合成データ）。段階・出来事の定義、植えた効果の検出、通過しないセルは確認期間を読まないこと、先読みがないこと。"""
import sys
from pathlib import Path

import numpy as np
from test_elastic import elastic_panel
from test_events import _iv, _write_limits
from test_rules import _write_processed

from selectlib import extremes, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def test_tiers_and_event_definitions():
    va = np.array([[6e8, 5e8, 4e8, 5e7, 4e7, 2e7, 1.5e7, 1e7, 7e6, 5e6, 4e6]])
    assert extremes.tier_matrix(va).tolist() == [[0, 0, 1, 1, 2, 2, 3, 3, 4, 4, -1]]
    P, codes, _ = elastic_panel(n_codes=40, seed=3, elastic_share=0.0, dates=("2022-01-03", "2023-12-29"))
    P.limit_up[300, 0] = True
    P.adj_high[300, 0] = P.adj_close[300, 0]                              # X1
    P.limit_up[301, 1] = True
    P.adj_high[301, 1] = P.adj_close[301, 1] * 1.05                       # 引けは高値でない → X1 ではない
    P.adj_close[302, 2] = P.adj_close[301, 2] * 1.2                       # +20%（ストップ高フラグなし）→ X3
    P.adj_close[303, 3] = P.adj_close[302, 3] * 0.8                       # −20% → X4
    P.turnover[304, 4] = 1e9                                              # 売買代金が 10 倍（平均 1 億円）
    P.adj_close[304, 4] = P.adj_close[303, 4] * 1.06                      # +6% → V1
    P.turnover[305, 5] = 1e9
    P.adj_close[305, 5] = P.adj_close[304, 5] * 0.94                      # −6% → V2
    ev = extremes.event_matrices(P, np.ones(P.adj_close.shape, bool))
    assert ev["X1_limit_up_close"][300, 0] and not ev["X1_limit_up_close"][301, 1] and ev["X3_up_10pct"][302, 2] and ev["X4_down_10pct"][303, 3]
    assert ev["V1_volume_spike_up"][304, 4] and ev["V2_volume_spike_down"][305, 5] and not ev["X3_up_10pct"][300, 0]
    assert extremes.net_after_cost(0.02, 1, 5)["net"] == 0.02 - 0.006
    s = extremes.net_after_cost(-0.04, 2, 21)
    assert s["side"].startswith("sell") and abs(s["net"] - (0.04 - 0.009 - 0.0115 * 21 / 252)) < 1e-12


def _world(tmp, seed, plant):
    P, codes, _ = elastic_panel(n_codes=120, seed=seed, elastic_share=0.0)
    rng = np.random.default_rng(seed)
    n = len(P.dates)
    if plant:
        for j in range(120):
            for t in rng.choice(np.arange(300, n - 30), 8, replace=False):
                P.limit_up[t, j] = True
                P.adj_high[t, j] = P.adj_close[t, j]
                P.adj_open[t + 6:, j] *= 0.95                              # 翌朝の始値から 5 営業日後の始値が 5% 下がる
    root = tmp / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    _iv(P, codes, {}).to_parquet(root / "processed" / "listed_master.parquet", index=False)
    return P, codes, root


def test_study_detects_planted_limit_up_reversal_and_reads_confirmation_only_for_passers(tmp_path):
    import extreme_events as ee
    P, codes, root = _world(tmp_path, seed=5, plant=True)
    res = ee.main(root)
    assert res["ledger_chain"]["ok"] and res["tests_run"] >= 2
    cell = [c for c in res["passed_cells"] if c["cell"] == "X1_limit_up_close|T2_50M_500M|h=5"]
    assert cell, res["not_passed_cells_discovery_only"][:5]
    c = cell[0]
    assert c["discovery"]["mean"] < -0.03 and c["discovery"]["q"] < 0.10 and c["law_candidate"] and c["confirmation"]["mean"] < -0.03
    assert c["after_cost_confirmation"]["side"].startswith("sell") and c["after_cost_confirmation"]["net"] > 0.01
    assert res["loan_share_discovery"]["X1_limit_up_close"][1] > 0.9      # 合成の銘柄表は、全銘柄が貸借（信用区分 2）
    for x in res["not_passed_cells_discovery_only"]:                       # 通過しないセルは、確認期間を読まない
        assert "confirmation" not in x
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = tmp_path / "b"
    _write_processed(root2, P, codes)
    _write_limits(root2, P, codes)
    _iv(P, codes, {}).to_parquet(root2 / "processed" / "listed_master.parquet", index=False)
    res2 = ee.main(root2)
    import json
    cells = lambda rt: {c["cell"]: c["discovery"] for c in json.loads((rt / "results" / "extremes" / "summary.json").read_text(encoding="utf-8"))["all_cells"]}  # noqa: E731
    assert cells(root) == cells(root2)


def test_null_world_has_no_law_candidates(tmp_path):
    import extreme_events as ee
    _, _, root = _world(tmp_path, seed=9, plant=False)
    res = ee.main(root)
    assert res["law_candidates"] == [] and res["passed_discovery"] == []
