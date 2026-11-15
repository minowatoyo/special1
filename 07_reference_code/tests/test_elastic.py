"""個別株の弾力性（合成データ）。出来事の定義、結果が確定するまで使わないこと、植えた弾力性の検出、効果がないときの空振り、先読みがないこと。"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_rules import _write_processed
from test_selectlib import intervals_for

from selectlib import elastic, rules
from selectlib.panel import Panel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def elastic_panel(n_codes=160, seed=0, elastic_share=0.5, phi=0.93, dates=("2016-11-14", "2026-11-12")):
    """前半の銘柄は、水準が平均へ戻る（OU）弾力的な銘柄、後半は、ランダムウォーク。"""
    rng = np.random.default_rng(seed)
    d = pd.bdate_range(*dates)
    n = len(d)
    mkt = rng.normal(0, 0.006, n)
    is_el = np.arange(n_codes) < int(n_codes * elastic_share)
    lp = np.zeros((n, n_codes))
    for j in range(n_codes):
        e = rng.normal(0, 0.013, n)
        if is_el[j]:
            u = np.zeros(n)
            for t in range(1, n):
                u[t] = phi * u[t - 1] + e[t]
            lp[:, j] = u + np.cumsum(mkt)
        else:
            lp[:, j] = np.cumsum(e + mkt)
    close = 1000 * np.exp(lp)
    opn = np.vstack([close[:1], close[:-1]])
    codes = [f"{10000 + 10 * i}"[:4] + "0" for i in range(n_codes)]
    rows = [pd.DataFrame({"date": d, "code": c, "open": opn[:, i], "close": close[:, i], "adj_open": opn[:, i], "adj_high": np.maximum(opn[:, i], close[:, i]),
                          "adj_low": np.minimum(opn[:, i], close[:, i]), "adj_close": close[:, i], "adj_volume": 1e6, "turnover": 1e8, "limit_up": "0", "limit_down": "0"})
            for i, c in enumerate(codes)]
    prices = pd.concat(rows, ignore_index=True)
    tp = pd.DataFrame({"date": d, "open": 1000.0, "high": 1000.0, "low": 1000.0, "close": 1000.0})
    P = Panel.from_frames(prices, prices[["code", "date"]].assign(no_trade=False), tp)
    return P, codes, is_el


def test_events_dedupe_and_scores_use_only_resolved_outcomes():
    cond = np.zeros((40, 2), bool)
    cond[[3, 5, 9, 14, 30], 0] = True                          # 3 の次の 5・9 は 10 営業日未満で捨てる。14 は 3 から 11 日後で、数える
    cond[[3], 1] = True
    ev = elastic.dedupe(cond)
    assert np.flatnonzero(ev[:, 0]).tolist() == [3, 14, 30] and np.flatnonzero(ev[:, 1]).tolist() == [3]
    # 結果の確定: 出来事 t の結果は、s ≥ t + lag から
    A = np.zeros((30, 1))
    A[5] = 1.0
    cs = elastic.shifted_cumsum(A, 12)
    assert cs[16, 0] == 0 and cs[17, 0] == 1.0 and cs[29, 0] == 1.0


def test_scores_detect_planted_elasticity_and_do_not_look_ahead():
    P, codes, is_el = elastic_panel(seed=1)
    n = len(P.dates)
    elig = np.ones(P.adj_close.shape, bool)
    elig[:250] = False
    B = elastic.build(P, elig, elig)
    d1, d2, d3 = (B["scores"][k] for k in elastic.DEFS)
    s = n - 5
    el = is_el[B["cols"]]
    for d, nm in ((d1, "D1"), (d2, "D2"), (d3, "D3")):
        assert np.nanmean(d[s][el]) > np.nanmean(d[s][~el]) + 0.0005, nm       # 弾力的な銘柄のほうが、高い
    # 先読みなし: 日 s より後の価格を壊しても、日 s までの弾力性は変わらない
    P2, _, _ = elastic_panel(seed=1)
    cut = n - 300
    for arr in (P2.adj_open, P2.adj_high, P2.adj_low, P2.adj_close, P2.raw_open, P2.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    B2 = elastic.build(P2, elig, elig)
    for k in elastic.DEFS:
        a, b2 = B["scores"][k][:cut - 25], B2["scores"][k][:cut - 25]
        assert np.allclose(a, b2, equal_nan=True), k


def _world(tmp, seed, share):
    P, codes, is_el = elastic_panel(seed=seed, elastic_share=share)
    root = tmp / "jq"
    _write_processed(root, P, codes)
    return P, codes, root


def test_study_finds_planted_elasticity_and_reads_confirmation_only_for_passers(tmp_path):
    import elasticity_study as es
    P, codes, root = _world(tmp_path, seed=4, share=0.5)
    res = es.main(root)
    assert res["events_in_decision_universe"] > 500 and res["ledger_chain"]["ok"] and len(res["tests"]) == 6
    by = {r["test"]: r for r in res["tests"]}
    assert res["passed_discovery"], res["tests"]
    first = by[res["passed_discovery"][0]]
    assert first["discovery"]["diff_mean"] > 0 and first["discovery"]["q"] < 0.10
    assert first["confirmation"]["diff_mean"] > 0 and first["law_candidate"]
    for r in res["tests"]:                                                       # 通過していない検定は、確認期間を読まない
        if r["test"] not in res["passed_discovery"]:
            assert isinstance(r["confirmation"], str)
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = tmp_path / "b"
    _write_processed(root2, P, codes)
    res2 = es.main(root2)
    assert {r["test"]: r["discovery"] for r in res["tests"]} == {r["test"]: r["discovery"] for r in res2["tests"]}


def test_null_world_has_no_law_candidates(tmp_path):
    import elasticity_study as es
    _, _, root = _world(tmp_path, seed=8, share=0.0)
    res = es.main(root)
    assert res["law_candidates"] == [] and res["events_in_decision_universe"] > 300


def test_profile_and_watchlist_roundtrip_with_forward_scoring(tmp_path):
    import stock_profile as sp
    import watchlist as wl
    from selectlib import seasonal
    from test_seasonal import _fins
    P, codes, is_el = elastic_panel(n_codes=80, seed=6, elastic_share=0.5)
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    _fins(P, codes).to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    code = codes[0]                                                              # 弾力的な銘柄
    res = sp.main(root, code[:4])                                                # 4 桁でも受け付ける
    assert res["code"] == code and res["in_history_universe"] and res["past_events"]["count"] > 5
    assert set(res["elasticity"]) == set(elastic.DEFS) and "_detail" not in res and "events" not in res           # 1 件ごとの表は、画面に出さない
    saved = json.loads((root / "results" / "profile" / f"{code}.json").read_text(encoding="utf-8"))
    assert len(saved["events"]) == res["past_events"]["count"]
    assert sp.main(root, "99999")["error"]
    # 前向きの記録: 過去の日で記録 → 全データで採点
    asof = str(P.dates[1500].date())
    r = wl.add(root, code, "一過性", "戻る", "テスト", asof=asof)
    assert r["recorded"] and r["asof"] == asof and r["ledger"]["ok"]
    wl.add(root, codes[1], "不明", "戻らない", asof=str(P.dates[len(P.dates) - 5].date()))          # 22 営業日目がまだない
    sc = wl.score(root)
    assert sc["scored"] == 1 and sc["pending"] == 1
    S = wl.summary(root)
    assert S["recorded"] == 2 and S["scored"] == 1 and S["by_cause"]["一過性"]["n"] == 1 and "12 件未満" in S["by_cause"]["一過性"]["conclusion"]
    # 検算: 採点は、翌営業日始値 → 22 営業日目の始値の、対象銘柄の平均との差
    out = [x["payload"] for x in wl_rows(root) if x["type"] == "watch_outcome"][0]
    from selectlib.panel import Panel  # noqa: F401
    y = seasonal.window_excess(P, np.ones(P.adj_close.shape, bool)[1500], 1501, 1522)
    assert abs(out["excess_21d"] - y[0]) < 0.02                                   # 母集団の定義（対象銘柄）が少し違うので、近いことだけを確かめる


def wl_rows(root):
    from forecastlib.ledger import AppendOnlyLedger
    return AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")._rows()
