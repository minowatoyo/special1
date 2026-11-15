"""ボラを合わせた比較（合成データ）。高ボラ株の低リターンだけが原因なら説明される、出来事そのものの効果なら説明できない。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_events import _iv, _write_limits
from test_rules import _write_processed

from selectlib import extremes
from selectlib.panel import Panel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def vol_panel(seed=0, n_codes=150, hi_share=0.3, hi_drift=-0.0008, event_effect=0.0, events_per_stock=40, dates=("2016-11-14", "2026-11-12"), turnover=1e8):
    """前の hi_share の銘柄は、高ボラ（日次 3.2%）で、平均が低い（hi_drift）。出来事（ストップ高引け）は、高ボラ銘柄にだけ付ける。
    event_effect != 0 なら、出来事の翌朝から 5 日で、さらにその分だけ下がる。"""
    rng = np.random.default_rng(seed)
    d = pd.bdate_range(*dates)
    n = len(d)
    mkt = rng.normal(0, 0.006, n)
    hi = np.arange(n_codes) < int(n_codes * hi_share)
    sd = np.where(hi, 0.032, 0.012)
    ret = rng.normal(0, 1, (n, n_codes)) * sd + np.where(hi, hi_drift, 0.0) + mkt[:, None]
    ev_pos = {}
    for j in np.flatnonzero(hi):
        ev_pos[j] = rng.choice(np.arange(300, n - 30), events_per_stock, replace=False)
        for t in ev_pos[j]:
            ret[t + 2:t + 7, j] += event_effect / 5.0
    close = 1000 * np.exp(np.cumsum(ret, axis=0))
    opn = np.vstack([close[:1], close[:-1]])
    codes = [f"{10000 + 10 * i}"[:4] + "0" for i in range(n_codes)]
    rows = [pd.DataFrame({"date": d, "code": c, "open": opn[:, i], "close": close[:, i], "adj_open": opn[:, i], "adj_high": np.maximum(opn[:, i], close[:, i]),
                          "adj_low": np.minimum(opn[:, i], close[:, i]), "adj_close": close[:, i], "adj_volume": 1e6, "turnover": turnover, "limit_up": "0", "limit_down": "0"})
            for i, c in enumerate(codes)]
    prices = pd.concat(rows, ignore_index=True)
    tp = pd.DataFrame({"date": d, "open": 1000.0, "high": 1000.0, "low": 1000.0, "close": 1000.0})
    P = Panel.from_frames(prices, prices[["code", "date"]].assign(no_trade=False), tp)
    for j, ts in ev_pos.items():
        for t in ts:
            P.limit_up[t, j] = True
            P.adj_high[t, j] = P.adj_close[t, j]
    return P, codes, hi


def test_helpers_vol_quintiles_and_control_means():
    rng = np.random.default_rng(0)
    T, N = 5, 300
    sig = rng.uniform(0.01, 0.05, (T, N))
    tier = np.tile(np.arange(N) % 3, (T, 1)).astype(np.int8)
    q = extremes.vol_quintiles(sig, tier)
    assert q.min() == 0 and q.max() == 4 and abs((q[0][tier[0] == 1] == 2).mean() - 0.2) < 0.03
    ex = rng.normal(0, 0.01, (T, N)) + 0.005 * q                           # 分位が高いほど、超過が大きい
    clean = np.ones((T, N), bool)
    CM = extremes.control_means(ex, clean, tier, q)
    assert CM.shape == (T, 3, 5) and (CM[:, :, 4] > CM[:, :, 0]).mean() > 0.9
    M = extremes.matched_excess(ex, tier, q, CM)
    assert abs(np.nanmean(M)) < 0.002                                      # 対照を引くと、分位による差が消える
    rec = extremes.recent(np.eye(6, dtype=bool)[:, :1].T.repeat(1, 0).reshape(1, 6).T.astype(bool)[:6], 3)
    assert rec.shape == (6, 1)


def _write(tmp, P, codes):
    root = tmp / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    _iv(P, codes, {}).to_parquet(root / "processed" / "listed_master.parquet", index=False)
    return root


def test_vol_explained_when_only_high_vol_drift(tmp_path):
    import vol_matched_study as vm
    P, codes, hi = vol_panel(seed=3, event_effect=0.0)
    res = vm.main(_write(tmp_path, P, codes))
    cell = [c for c in res["cells"] if c["cell"] == "X1_limit_up_close|T2_50M_500M|h=21"]
    assert cell
    c = cell[0]
    raw, m = c["confirmation"]["raw"], c["confirmation"]["matched"]
    assert raw["mean"] < -0.008                                             # 元の出来事の後は、弱い（高ボラ株の低リターンのせい）
    assert abs(m["mean"]) < 0.5 * abs(raw["mean"]) or m["p"] > 0.05         # ボラを合わせると、縮むか、有意でなくなる
    assert c["verdict"] in ("ボラで説明される", "一部")


def test_vol_cannot_explain_a_real_event_effect(tmp_path):
    import vol_matched_study as vm
    P, codes, hi = vol_panel(seed=4, event_effect=-0.08)
    res = vm.main(_write(tmp_path, P, codes))
    c = [c for c in res["cells"] if c["cell"] == "X1_limit_up_close|T2_50M_500M|h=5"][0]
    assert c["discovery"]["matched"]["mean"] < -0.04 and c["confirmation"]["matched"]["mean"] < -0.04
    assert c["verdict"] == "ボラでは説明できない"
    assert set(res["vol_effect_clean_tierT2_by_quintile"]["h=5"]) == {"discovery", "confirmation"}
