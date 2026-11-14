"""型破りの探索（合成データ）。出来事の検出、植えた効果の検出、通過しない検定は確認期間を読まないこと、先読みがないこと。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_rules import _write_processed
from test_seasonal import _fins, seasonal_panel

from selectlib import events, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def _iv(P, codes, changes):
    """changes: {code: (位置, 旧市場, 新市場, 旧信用区分, 新信用区分)}。それ以外は、新旧の一斉変更（2022-04-04）だけ。"""
    rows = []
    base = {"name": "n", "s17": "1", "s33": "1", "scale_cat": "-", "prod_cat": "011"}
    reorg = int(np.searchsorted(P.dates.values, events.REORG.to_datetime64()))
    for c in codes:
        if c in changes:
            k, m0, m1, g0, g1 = changes[c]
            rows.append({**base, "code": c, "market": m0, "margin_class": g0, "valid_from": P.dates[0], "valid_to": P.dates[k - 1]})
            rows.append({**base, "code": c, "market": m1, "margin_class": g1, "valid_from": P.dates[k], "valid_to": P.dates[-1]})
        else:
            rows.append({**base, "code": c, "market": "0101", "margin_class": "2", "valid_from": P.dates[0], "valid_to": P.dates[reorg - 1]})
            rows.append({**base, "code": c, "market": "0111", "margin_class": "2", "valid_from": P.dates[reorg], "valid_to": P.dates[-1]})
    return pd.DataFrame(rows)


def test_event_detection_market_loan_split_limit():
    P, codes, _ = seasonal_panel(n_codes=30, seed=2)
    reorg = int(np.searchsorted(P.dates.values, events.REORG.to_datetime64()))
    iv = _iv(P, codes, {codes[0]: (400, "0102", "0101", "1", "1"), codes[1]: (1600, "0112", "0111", "1", "2"), codes[2]: (500, "0101", "0102", "2", "1"),
                        codes[3]: (reorg, "0102", "0112", "1", "1")})
    t, j = events.market_upgrades(P, iv)
    assert sorted(zip(t.tolist(), j.tolist())) == [(400, 0), (1600, 1)]            # 降格と、2022-04-04 の一斉変更は数えない
    t, j = events.loan_designations(P, iv)
    assert list(zip(t.tolist(), j.tolist())) == [(1600, 1)]
    # 分割: 位置 700 で 2 分割（それより前の調整後の値が半分）。併合は数えない
    P.adj_close[:700, 5] /= 2
    P.adj_close[:900, 6] *= 5
    t, j = events.splits(P)
    assert list(zip(t.tolist(), j.tolist())) == [(700, 5)]
    # ストップ高で引けた日: フラグがあり、終値 = 高値
    P.limit_up[800, 7] = True
    P.adj_high[800, 7] = P.adj_close[800, 7]
    P.limit_up[801, 8] = True
    P.adj_high[801, 8] = P.adj_close[801, 8] * 1.02                                   # 引けでは離れた
    (ut, uj), (dt, dj) = events.limit_closes(P)
    assert list(zip(ut.tolist(), uj.tolist())) == [(800, 7)] and len(dt) == 0


def test_progress_and_buyback_use_only_disclosed_history():
    P, codes, _ = seasonal_panel(n_codes=6, seed=3)
    f = _fins(P, codes)
    f["FOP"] = 100.0
    f["OP"] = f["CurPerType"].map({"1Q": 20.0, "2Q": 45.0, "3Q": 70.0, "FY": 100.0})
    f["ShOutFY"], f["TrShFY"] = 1_000_000.0, 0.0
    last = f["CurFYEn"] == f["CurFYEn"].max()
    # 銘柄 0: 最新の決算期だけ、2Q の進捗が 45% → 60%（予想は据え置き）。銘柄 1: 同じく進捗が早いが、予想を上げた
    f.loc[last & (f["Code"] == codes[0]) & (f["CurPerType"] == "2Q"), "OP"] = 60.0
    m1 = last & (f["Code"] == codes[1]) & (f["CurPerType"] == "2Q")
    f.loc[m1, ["OP", "FOP"]] = [72.0, 120.0]
    f.loc[last & (f["Code"] == codes[2]) & (f["CurPerType"] == "1Q"), "OP"] = 8.0      # 遅れ（20% → 8%）
    f.loc[(f["Code"] == codes[3]) & (f["CurFYEn"] >= "2023"), "TrShFY"] = 50_000.0     # 自己株式が 5% 増える（純減 5%）
    pe = events.progress_events(P, f)
    ci = {c: i for i, c in enumerate(P.codes)}
    assert set(pe["ahead"][1].tolist()) == {ci[codes[0]]} and len(pe["ahead"][0]) == 1
    assert set(pe["behind"][1].tolist()) == {ci[codes[2]]}
    bb = events.buyback_events(P, f)["buyback"]
    assert set(bb[1].tolist()) == {ci[codes[3]]} and len(bb[0]) == 4                    # 1 年前との比較で、4 四半期だけ点灯
    # 列がなければ、理由を返す
    assert "missing" in events.progress_events(P, f.drop(columns=["OP"])) and "missing" in events.buyback_events(P, f.drop(columns=["ShOutFY"]))


def _world(tmp, seed=5, effect=0.0):
    P, codes, _ = seasonal_panel(n_codes=160, seed=seed, turnover=1e8)
    fins = _fins(P, codes)
    rng = np.random.default_rng(seed)
    changes, n = {}, len(P.dates)
    reorg = int(np.searchsorted(P.dates.values, events.REORG.to_datetime64()))
    for i, c in enumerate(codes[:120]):                                              # 市場の昇格を、全期間にばらまく
        k = int(rng.integers(300, n - 60))
        if abs(k - reorg) < 3:
            k += 5
        changes[c] = (k, "0102", "0101", "1", "1") if k < reorg else (k, "0112", "0111", "1", "1")
        if effect:
            P.adj_open[k + 1:, i] *= np.exp(np.minimum(np.arange(n - k - 1), 5) * effect / 5)      # 翌営業日の始値から 5 日で effect だけ上がる
    root = tmp / "jq"
    _write_processed(root, P, codes)
    _iv(P, codes, changes).to_parquet(root / "processed" / "listed_master.parquet", index=False)
    fins.to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    return P, codes, root, changes, fins


def test_study_finds_planted_upgrade_effect_and_reads_confirmation_only_for_passers(tmp_path):
    import unconventional_study as us
    P, codes, root, changes, fins = _world(tmp_path, effect=0.05)
    res = us.main(root)
    by = {r["test"]: r for r in res["results"]}
    e1 = by["E1_market_upgrade|h=5"]
    assert e1["discovery"]["mean"] > 0.03 and e1["discovery"]["q"] < 0.10 and e1["law_candidate"] and e1["confirmation"]["mean"] > 0.03
    assert "E1_market_upgrade|h=5" in res["passed_discovery"] and res["ledger_chain"]["ok"]
    assert set(res["diagnostic_corrected_executability"]) == {"E4a_limit_up_close", "E4b_limit_down_close"}
    for r in res["results"]:                                                         # 通過していない検定は、確認期間を読まない
        if "skipped" not in r and r["test"] not in res["passed_discovery"]:
            assert isinstance(r["confirmation"], str)
    assert by["E6a_ahead_no_raise|h=63"].get("skipped") and by["E7_buyback|h=63"].get("skipped")   # 合成の決算には OP・株式数の列がない
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = tmp_path / "b"
    _write_processed(root2, P, codes)
    _iv(P, codes, changes).to_parquet(root2 / "processed" / "listed_master.parquet", index=False)
    fins.to_parquet(root2 / "processed" / "fins_summary.parquet", index=False)
    res2 = us.main(root2)
    d = lambda r: {x["test"]: x.get("discovery") for x in r["results"]}  # noqa: E731
    assert d(res) == d(res2)


def test_null_world_has_no_law_candidates(tmp_path):
    import unconventional_study as us
    _, _, root, _, _ = _world(tmp_path, seed=9, effect=0.0)
    res = us.main(root)
    assert res["law_candidates"] == [] and res["tests_run"] >= 2


def test_executable_at_open_keeps_stocks_that_hit_the_limit_after_the_open():
    P, codes, _ = seasonal_panel(n_codes=5, seed=1)
    P.limit_up[501, 0] = True                                   # 寄り付いた後にストップ高（始値 < 高値）
    P.adj_high[501, 0] = P.adj_open[501, 0] * 1.1
    P.limit_up[501, 1] = True                                   # ストップ高で寄った（始値 = 高値）
    P.adj_high[501, 1] = P.adj_open[501, 1]
    ex = events.executable_at_open(P)
    assert ex[500, 0] and not ex[500, 1] and not rules.executable(P)[500, 0]
    g = events.overnight_gap(P, np.array([500]), np.array([0]))
    assert abs(g[0] - (P.adj_open[501, 0] / P.adj_close[500, 0] - 1)) < 1e-12


def test_exec_switch_changes_only_the_limit_up_after_open_case(monkeypatch):
    P, codes, _ = seasonal_panel(n_codes=5, seed=1)
    P.limit_up[501, 0] = True; P.adj_high[501, 0] = P.adj_open[501, 0] * 1.1       # 寄り付いた後にストップ高  # noqa: E702
    P.limit_up[501, 1] = True; P.adj_high[501, 1] = P.adj_open[501, 1]              # ストップ高で寄った  # noqa: E702
    monkeypatch.delenv("JQ_EXEC", raising=False)
    legacy = rules.executable(P)
    assert rules.exec_tag() == "" and not legacy[500, 0] and not legacy[500, 1]
    monkeypatch.setenv("JQ_EXEC", "open")
    fixed = rules.executable(P)
    assert rules.exec_tag() == "_execopen" and fixed[500, 0] and not fixed[500, 1]
    diff = fixed != legacy
    assert diff.sum() == 1 and diff[500, 0]                                         # 他の場所は同じ
