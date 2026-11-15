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


def _write_limits(root, P, codes):
    """_write_processed は limit_up を "0" 固定で書く。パネルのストップ高を、価格表に書き込む。"""
    f = root / "processed" / "prices_daily.parquet"
    d = pd.read_parquet(f)
    d["limit_up"] = np.where(P.limit_up.ravel(), "1", "0")
    d.to_parquet(f, index=False)


def test_short_feasibility_counts_only_loan_stocks_and_applies_costs(tmp_path):
    import short_feasibility as sf
    P, codes, _ = seasonal_panel(n_codes=80, seed=21, turnover=1e8)
    fins = _fins(P, codes)
    rng = np.random.default_rng(2)
    n = len(P.dates)
    for j in range(60):
        for t in rng.choice(np.arange(300, n - 20), 6, replace=False):
            P.limit_up[t, j] = True
            P.adj_high[t, j] = P.adj_close[t, j]                      # ストップ高で引けた
            P.adj_open[t + 6:, j] *= 0.94                              # 5 営業日後の始値が 6% 下がる（植えた）
    iv = _iv(P, codes, {})
    iv.loc[iv["code"].isin(codes[30:]), "margin_class"] = "1"          # 後半の銘柄は貸借でない
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    iv.to_parquet(root / "processed" / "listed_master.parquet", index=False)
    fins.to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    res = sf.main(root)
    c = res["periods"]["confirmation"]
    assert 0.4 < res["loan_share"] < 0.6 and c["loan_events"] > 0 and c["loan_events"] < c["events"]
    gross = c["market_neutral_before_cost"]["month_mean"]
    net = c["market_neutral_after_cost"]["month_mean"]
    assert gross > 0.03 and 0.003 < gross - net < 0.006                # コスト（0.4% ＋ 貸株料）が引かれる
    assert res["viable_candidate"] and c["distribution_unhedged_per_trade"]["p50"] > 0.03
    assert (root / "results" / "short_feasibility" / "summary.json").exists()
    # 先読みなし: 結果は t+6 までの価格だけに依存する。効果がなければ候補にならない
    P2, codes2, _ = seasonal_panel(n_codes=80, seed=22, turnover=1e8)
    for j in range(60):
        for t in rng.choice(np.arange(300, n - 20), 6, replace=False):
            P2.limit_up[t, j] = True
            P2.adj_high[t, j] = P2.adj_close[t, j]
    root2 = tmp_path / "n"
    _write_processed(root2, P2, codes2)
    _write_limits(root2, P2, codes2)
    _iv(P2, codes2, {}).to_parquet(root2 / "processed" / "listed_master.parquet", index=False)
    _fins(P2, codes2).to_parquet(root2 / "processed" / "fins_summary.parquet", index=False)
    assert not sf.main(root2)["viable_candidate"]


def test_attr_at_matches_interval_at_the_date():
    P, codes, _ = seasonal_panel(n_codes=3, seed=1)
    iv = _iv(P, codes, {codes[0]: (400, "0102", "0101", "1", "2")})
    a = events.attr_at(P, iv, np.array([399, 400, 401, 500]), np.array([0, 0, 0, 1]), "margin_class")
    assert list(a) == ["1", "2", "2", "2"]


def test_short_refinement_splits_by_short_balance_and_gyaku_hibu(tmp_path):
    import short_feasibility as sf
    P, codes, _ = seasonal_panel(n_codes=90, seed=31, turnover=1e8)
    fins = _fins(P, codes)
    rng = np.random.default_rng(3)
    n = len(P.dates)
    heavy = np.arange(90) < 30                                           # 売り残が重い銘柄: ストップ高の後、5 日で下がらず、むしろ上がる（植えた）
    for j in range(90):
        for t in rng.choice(np.arange(300, n - 20), 6, replace=False):
            P.limit_up[t, j] = True
            P.adj_high[t, j] = P.adj_close[t, j]
            P.adj_open[t + 6:, j] *= 1.04 if heavy[j] else 0.94
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    _iv(P, codes, {}).to_parquet(root / "processed" / "listed_master.parquet", index=False)
    fins.to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    idx = np.arange(300, n - 6, 5)
    rows = [pd.DataFrame({"code": c, "date": P.dates[idx], "long_vol": 1e5, "short_vol": 3e6 if heavy[i] else 1e4, "usable_from": P.dates[idx + 1]}) for i, c in enumerate(codes)]
    pd.concat(rows, ignore_index=True).to_parquet(root / "processed" / "margin_interest.parquet", index=False)
    res = sf.main(root)
    c = res["refinement"]["by_period"]["confirmation"]
    sb = c["by_short_balance"]
    assert sb["light"]["events"] > 20 and sb["heavy"]["events"] > 20
    assert sb["light"]["net_event_weighted_mean"] > 0.03 and sb["heavy"]["net_event_weighted_mean"] < -0.03        # 軽い群は売りで勝ち、重い群は負ける
    assert abs(sb["light"]["after_gyaku_hibu_per_5d"]["1.0%"] - (sb["light"]["net_event_weighted_mean"] - 0.01)) < 1e-9
    assert "all_loan" in c["sizing"] and "short_balance_light" in c["sizing"]
    sz = c["sizing"]["short_balance_light"]["per_position_pct_of_equity"]["2%"]
    assert sz["annual_contribution"] > 0 and sz["worst_single_loss"] < 0
    # 売り残のデータがなければ、すべて「不明」に入り、落ちない
    (root / "processed" / "margin_interest.parquet").unlink()
    res2 = sf.main(root)
    assert res2["refinement"]["by_period"]["confirmation"]["by_short_balance"]["unknown"]["events"] > 0


def test_forward_events_record_score_summary_with_forward_validity(tmp_path):
    import forward_events as fe
    P, codes, _ = seasonal_panel(n_codes=90, seed=41, turnover=1e8)
    fins = _fins(P, codes)
    n = len(P.dates)
    t0 = n - 40                                                         # 記録する日
    light = np.arange(90) < 28                                          # 売り残が軽い銘柄は、下位 1/3 に入る 28 銘柄。ほかは重い
    for j in (0, 1, 50):                                                # 0・1: 軽い（候補）。50: 重い（候補外）
        P.limit_up[t0, j] = True
        P.adj_high[t0, j] = P.adj_close[t0, j]
        P.adj_open[t0 + 6:, j] *= 0.94                                  # 5 日後に 6% 下がる
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    iv = _iv(P, codes, {})
    iv.loc[iv["code"] == codes[1], "margin_class"] = "1"               # 1 は貸借でない → 候補外
    iv.to_parquet(root / "processed" / "listed_master.parquet", index=False)
    fins.to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    idx = np.arange(300, n - 2, 5)
    rows = [pd.DataFrame({"code": c, "date": P.dates[idx], "long_vol": 1e5, "short_vol": 1e4 if light[i] else 3e6, "usable_from": P.dates[idx + 1]}) for i, c in enumerate(codes)]
    pd.concat(rows, ignore_index=True).to_parquet(root / "processed" / "margin_interest.parquet", index=False)
    asof = str(P.dates[t0].date())
    r = fe.record(root, asof)
    assert r["status"] == "recorded" and r["limit_up_closes"] == 3 and r["candidates"] == 1                    # コード 0 だけ
    assert fe.record(root, asof)["status"] == "already_recorded"                                                # 同じ日は、二重に記録しない
    s0 = fe.summary(root)
    assert s0["short_candidates"]["scored_ok"] == 0 and "結論を出さない" in s0["short_candidates"]["conclusion"]
    sc = fe.score(root)
    assert sc["scored_candidate_days"] == 1 and sc["scored_index_days"] == 1
    assert fe.score(root)["scored_candidate_days"] == 0                                                          # 二重に採点しない
    s = fe.summary(root)
    assert s["short_candidates"]["scored_ok"] == 1 and s["short_candidates"]["mean_net_after_cost"] > 0.02
    # 前向きの条件: 記録の後に、価格が壊れても、記録は変わらない
    rec = [r for r in fe.AppendOnlyLedger(root / "ledger" / "forward_events.jsonl")._rows() if r["type"] == "fe_record"][0]["payload"]
    assert [c["code"] for c in rec["candidates"]] == [codes[0]] and rec["asof"] == asof
