"""財務の強さ F・財務危機・簿価利回り・開示の有無（合成データ）。項目の計算、開示日より前に使わないこと、植えた効果の検出、空振り。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_elastic import elastic_panel
from test_rules import _write_processed

from selectlib import fscore, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def fy_rows(P, code, years, vals, month=5, day=10):
    """通期決算の行。vals: 年 → dict(Sales, OP, NP, TA, Eq, CFO, ShOutFY, TrShFY, BPS)。開示は、決算期末の翌 5 月 10 日。"""
    rows = []
    for y in years:
        d = pd.Timestamp(year=y, month=month, day=day)
        rows.append({"Code": code, "DiscDate": d, "usable_from": d + pd.offsets.BDay(1), "CurFYEn": f"{y}-03-31", "CurPerType": "FY",
                     "DocType": "FYFinancialStatements_Consolidated_JP", **vals[y]})
    return rows


BASE = {"Sales": 1000.0, "OP": 100.0, "NP": 60.0, "TA": 2000.0, "Eq": 1000.0, "CFO": 80.0, "ShOutFY": 1e6, "TrShFY": 0.0, "BPS": 1000.0}


def test_f_signals_distress_and_no_use_before_disclosure():
    P, codes, _ = elastic_panel(n_codes=4, seed=1)
    good = {2019: BASE, 2020: {**BASE, "OP": 130.0, "NP": 80.0, "CFO": 120.0, "Eq": 1100.0, "Sales": 1100.0}}     # 全項目が改善
    bad = {2019: BASE, 2020: {**BASE, "OP": -50.0, "NP": -80.0, "CFO": -20.0, "Eq": 300.0, "Sales": 800.0, "ShOutFY": 1.2e6}}
    f = pd.DataFrame(fy_rows(P, codes[0], (2019, 2020), good) + fy_rows(P, codes[1], (2019, 2020), bad))
    at = fscore.annual_table(P, f)
    g = at[(at["Code"] == codes[0]) & (at["fy"].dt.year == 2020)].iloc[0]
    b = at[(at["Code"] == codes[1]) & (at["fy"].dt.year == 2020)].iloc[0]
    assert g["F"] == 1.0 and g["n_signals"] == 8 and g["distress"] == 0.0
    assert b["F"] == 0.125 and b["distress"] == 1.0                              # 満たすのは「営業 CF（−20）> 純利益（−80）」の 1 項目だけ。赤字・営業 CF 赤字・自己資本比率 15%
    first = at[at["fy"].dt.year == 2019]
    assert first["n_signals"].max() == 3 and first["F"].isna().all()             # 前期がないと、変化の項目は計算できない（6 未満は対象外）
    D = fscore.daily(P, f)
    ci = {c: i for i, c in enumerate(P.codes)}
    t = int(np.searchsorted(P.dates.values, np.datetime64("2020-05-11")))        # 利用可能日（開示の翌営業日）
    assert np.isnan(D["F"][t - 1, ci[codes[0]]]) and D["F"][t, ci[codes[0]]] == 1.0
    assert D["news"][t, ci[codes[0]]] and D["news"][t + 5, ci[codes[0]]] and not D["news"][t + 6, ci[codes[0]]] and not D["news"][t - 1, ci[codes[0]]]
    assert abs(D["book_yield"][t, ci[codes[0]]] - 1000.0 / P.adj_close[t, ci[codes[0]]]) < 1e-9
    t_old = int(np.searchsorted(P.dates.values, np.datetime64("2021-07-01")))    # 400 暦日を過ぎたら、無効
    assert np.isnan(D["F"][t_old, ci[codes[0]]])
    assert fscore.availability(f)["cfo"] and not fscore.availability(f.drop(columns=["CFO"]))["cfo"]
    at2 = fscore.annual_table(P, f.drop(columns=["CFO", "TA"]))                  # 列が足りなければ、対象外になる（落ちない）
    assert at2["F"].isna().all()


def _world(tmp, seed, drift):
    P, codes, _ = elastic_panel(n_codes=150, seed=seed, elastic_share=0.0)
    rng = np.random.default_rng(seed)
    n = len(P.dates)
    cheap = rng.random(150) < 0.4
    strong = rng.random(150) < 0.5
    rows = []
    years = range(2017, 2027)
    for i, c in enumerate(codes):
        px0 = float(P.adj_close[0, i])
        vals = {}
        for k, y in enumerate(years):
            up = 1.0 + (0.05 * k if strong[i] else -0.05 * k)
            vals[y] = {**BASE, "OP": 100.0 * up, "NP": 60.0 * up, "CFO": (90.0 if strong[i] else 40.0) * up, "Eq": 1000.0 * (1 + 0.02 * k if strong[i] else 1 - 0.02 * k),
                       "Sales": 1000.0 * up, "BPS": px0 * (3.0 if cheap[i] else 0.3)}
        rows += fy_rows(P, c, years, vals)
        if drift and cheap[i] and strong[i]:
            sc = np.exp(drift * np.arange(n))
            for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
                arr[:, i] *= sc
    fins = pd.DataFrame(rows)
    fins = fins[fins["DiscDate"] <= P.dates[-1]]
    root = tmp / "jq"
    _write_processed(root, P, codes)
    fins.to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    return P, codes, root, fins


def test_study_detects_planted_mismatch_and_reads_confirmation_only_for_passers(tmp_path):
    import mismatch_study as ms
    P, codes, root, fins = _world(tmp_path, seed=3, drift=0.0006)
    res = ms.main(root)
    by = {r["test"]: r for r in res["tests"]}
    assert len(res["tests"]) == 9 and res["ledger_chain"]["ok"] and all(v for k, v in res["columns_available"].items() if k != "eqar")
    m3 = by["M3_cheap_and_Fhigh_vs_universe|h=63"]
    assert m3["discovery"]["mean"] > 0.01 and m3["discovery"]["q"] < 0.10 and m3["law_candidate"] and m3["confirmation"]["mean"] > 0.01
    assert res["coverage_last_day"]["cheap_and_F_high"] > 5
    for r in res["tests"]:
        if r["test"] not in res["passed_discovery"]:
            assert isinstance(r["confirmation"], str)
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = tmp_path / "b"
    _write_processed(root2, P, codes)
    fins.to_parquet(root2 / "processed" / "fins_summary.parquet", index=False)
    res2 = ms.main(root2)
    assert {r["test"]: r["discovery"] for r in res["tests"]} == {r["test"]: r["discovery"] for r in res2["tests"]}


def test_null_world_has_no_law_candidates(tmp_path):
    import mismatch_study as ms
    _, _, root, _ = _world(tmp_path, seed=7, drift=0.0)
    assert ms.main(root)["law_candidates"] == []
