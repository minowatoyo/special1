"""極端な動きの回避フィルター（合成データ）。フラグの定義、除外後の繰り上がり、植えた効果の検出、先読みがないこと、確認期間の読みの記録。"""
import json
import sys
from pathlib import Path

import numpy as np
from test_events import _iv, _write_limits
from test_rules import _write_processed
from test_vol_matched import vol_panel

from selectlib import extremes, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def test_recent_window_includes_today_and_covers_five_sessions():
    ev = np.zeros((12, 1), bool)
    ev[3, 0] = True
    r = extremes.recent(ev, 5)[:, 0]
    assert np.flatnonzero(r).tolist() == [3, 4, 5, 6, 7]                        # 当日を含み、5 営業日
    assert set(extremes.UP_EVENTS) | set(extremes.DOWN_EVENTS) == {"X1_limit_up_close", "X2_limit_down_close", "X3_up_10pct", "X4_down_10pct", "V1_volume_spike_up", "V2_volume_spike_down"}


def _write(tmp, P, codes):
    root = tmp / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    _iv(P, codes, {}).to_parquet(root / "processed" / "listed_master.parquet", index=False)
    return root


def test_filter_study_flags_planted_drop_after_extreme_events_and_records_one_read(tmp_path):
    import extreme_filter_study as ef
    P, codes, hi = vol_panel(seed=6, n_codes=120, hi_share=0.5, hi_drift=0.0, event_effect=-0.20, events_per_stock=90, turnover=1e9)
    root = _write(tmp_path, P, codes)
    res = ef.main(root, min_history=250, min_periods=6)
    assert res["periods"]["discovery"] >= 5 and res["periods"]["confirmation"] >= 20 and res["ledger_chain"]["ok"]
    a = res["A_effect_of_flagged_stocks_21d_excess"]["N2_up_extreme_5d"]
    assert a["confirmation"]["mean"] < -0.02 and a["confirmation"]["p"] < 0.05                     # 植えた効果（ストップ高の後の下落）
    b = res["B_top15_with_exclusion_minus_baseline_21d"]["N2_up_extreme_5d"]
    assert b["confirmation"]["removed_per_period_mean"] >= 0 and b["confirmation"]["mean"] >= 0
    assert set(res["filters"]) == set(ef.NAMES) and (root / "results" / "extreme_filter" / "summary.json").exists()
    rows = [json.loads(x) for x in (root / "ledger" / "trials.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len([r for r in rows if r["type"] == "confirmation_read" and r["payload"]["family"].startswith("extreme_filter_v1")]) == 1
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = _write(tmp_path / "b", P, codes)
    res2 = ef.main(root2, min_history=250, min_periods=6)
    for sec in ("A_effect_of_flagged_stocks_21d_excess", "B_top15_with_exclusion_minus_baseline_21d"):
        for n in ef.NAMES:
            assert res[sec][n]["discovery"] == res2[sec][n]["discovery"]


def test_null_world_is_not_usable(tmp_path):
    import extreme_filter_study as ef
    P, codes, hi = vol_panel(seed=8, n_codes=120, hi_share=0.5, hi_drift=0.0, event_effect=0.0, events_per_stock=90, turnover=1e9)
    res = ef.main(_write(tmp_path, P, codes), min_history=250, min_periods=6)
    assert not any(res["B_top15_with_exclusion_minus_baseline_21d"][n]["usable"] for n in ef.NAMES)
