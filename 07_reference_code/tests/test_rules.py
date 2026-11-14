"""チャート規則の一斉検証（合成データ）。先読みがないこと、蓄積が総当たりと一致すること、統計の性質、期間分割。"""
import numpy as np
import pandas as pd
import pytest
from test_selectlib import synth_panel

from forecastlib import synth
from selectlib import rules


def test_rule_count_names_and_no_lookahead_for_all_rules():
    df = synth.make_garch_ohlcv(n=900, seed=3)
    s = rules.rule_signals(df)
    assert s.shape[1] == 49 and len(set(s.columns)) == 49 and (s.dtypes == bool).all()
    cut = 600
    d2 = df.copy()
    d2.iloc[cut + 1:] = d2.iloc[cut + 1:].to_numpy() * 3.7                # 未来を壊す
    s2 = rules.rule_signals(d2)
    assert (s.iloc[:cut + 1].to_numpy() == s2.iloc[:cut + 1].to_numpy()).all()
    assert (rules.volume_surge(df).iloc[:cut + 1].to_numpy() == rules.volume_surge(d2).iloc[:cut + 1].to_numpy()).all()


def test_accumulation_matches_brute_force_and_tertiles_sum_to_total():
    P, codes = synth_panel(n_dates=700, n_codes=30, seed=2)
    elig = np.zeros(P.adj_close.shape, dtype=bool)
    elig[300:] = True
    builders = {"close_gt_prev": lambda x: x.sig["above_sma25"].to_numpy()}
    fins = pd.DataFrame({"Code": [], "usable_from": pd.to_datetime([])})
    acc = rules.run_pass(P, elig, builders, fins, horizons=(5,))
    F = rules.forward_returns(P, 5)
    ex = rules.executable(P)
    c = pd.DataFrame(P.adj_close).rolling(25).mean().to_numpy()
    sig = P.adj_close > c
    ok = elig & ex
    t = 450
    m = sig[t] & ok[t] & np.isfinite(F[t])
    assert acc["cnt"][0, 0, t] == m.sum() and np.isclose(acc["sum"][0, 0, t], F[t][m].sum())
    mu = ok[t] & np.isfinite(F[t])
    assert acc["ucnt"][0, t] == mu.sum() and np.isclose(acc["usum"][0, t], F[t][mu].sum())
    assert np.allclose(acc["cnt3"][0, :, 0, t].sum(), acc["cnt"][0, 0, t]) and np.isclose(acc["sum3"][0, :, 0, t].sum(), acc["sum"][0, 0, t])
    assert acc["ucnt"][0, :299].sum() == 0                                   # 対象でない期間は 0


def test_spread_stats_detects_drift_and_is_calibrated_under_null():
    rng = np.random.default_rng(0)
    n, h = 1500, 5
    pos = np.arange(n)
    d = rng.normal(0, 0.01, n)
    s_null = rules.spread_stats(d, np.ones(n, bool), h)
    s_eff = rules.spread_stats(d + 0.004, np.ones(n, bool), h)
    assert s_eff["t"] > 5 and s_eff["p"] < 1e-5 and abs(s_null["t"]) < 3.5
    ps = [rules.spread_stats(rng.normal(0, 0.01, 800), np.ones(800, bool), 21)["p"] for _ in range(200)]
    assert np.mean(np.array(ps) < 0.05) < 0.12 and pos[0] == 0                 # 帰無で p<0.05 が 5% 付近
    assert np.isnan(rules.spread_stats(d, np.zeros(n, bool), h)["t"])


def test_period_split_has_no_overlap_across_the_boundary():
    dates = pd.bdate_range("2017-01-02", "2026-11-12")
    b = int(np.searchsorted(dates.values, rules.SPLIT.to_datetime64()))
    for h in (5, 21):
        d, c = rules.period_mask(dates, h, "discovery"), rules.period_mask(dates, h, "confirmation")
        last_d, first_c = np.flatnonzero(d).max(), np.flatnonzero(c).min()
        assert not (d & c).any() and first_c == b and last_d + 1 + h < first_c + 1     # 発見期間の最後の売却日が確認期間の買い日より前
        assert dates[first_c] >= rules.SPLIT


def test_discover_and_confirm_only_reads_passed_rules():
    dates = pd.bdate_range("2017-01-02", "2026-11-12")
    n, rng = len(dates), np.random.default_rng(1)
    R, H = 3, 2
    acc = {"names": ["planted", "null", "reversed"], "horizons": [5, 21], "dates": dates,
           "cnt": np.full((H, R, n), 40.0), "sum": np.zeros((H, R, n)), "cnt3": np.full((H, 3, R, n), 13.0), "sum3": np.zeros((H, 3, R, n)),
           "ucnt": np.full((H, n), 600.0), "usum": np.zeros((H, n)), "ucnt3": np.full((H, 3, n), 200.0), "usum3": np.zeros((H, 3, n))}
    for hi in range(H):
        noise = rng.normal(0, 0.02, (R, n)) * 40
        acc["sum"][hi] = noise
        acc["sum"][hi, 0] += 0.006 * 40                                         # planted: 発見・確認の両方で正
        acc["sum"][hi, 2] += np.where(np.arange(n) < 1300, 0.006, -0.006) * 40   # 発見では正、確認で逆転
    dis = rules.discover(acc)
    names = {k[0] for k in dis["passed"]}
    assert "planted" in names and "null" not in names and dis["n_tests"] == 6
    conf = rules.confirm(acc, dis["passed"])
    assert set(k[0] for k in conf) == names
    assert conf[("planted", 5)]["t"] > 3
    if ("reversed", 5) in conf:
        assert conf[("reversed", 5)]["mean"] < 0


def test_conditional_builders_and_earnings_flags():
    assert len(rules.conditional_builders(["a", "b"])) == 12 and set(rules.conditional_builders(["a"])) == {f"a&{c}" for c in rules.COND_NAMES}
    P, codes = synth_panel(n_dates=60, n_codes=3, seed=1)
    fins = pd.DataFrame({"Code": [codes[0]], "usable_from": [P.dates[10]]})
    f = rules.earnings_flags(P, fins)
    assert f[10:15, 0].all() and not f[9, 0] and not f[15, 0] and not f[:, 1].any()
    tb = rules.type_builders()
    assert set(tb) == {"type_pullback", "type_breakout", "type_oversold_all", "type_oversold_no_earnings"}


def test_rule_study_runs_end_to_end_on_synthetic_processed_data(tmp_path):
    """実行スクリプトを合成の加工後データで通す（実データなし）。確認期間は通過規則だけ読まれ、台帳に記録される。"""
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts" / "w5"))
    import rule_study
    from test_selectlib import intervals_for
    P, codes = synth_panel(n_dates=1500, n_codes=25, seed=4)
    root = tmp_path / "jq"
    out = root / "processed"
    out.mkdir(parents=True)
    n, m = len(P.dates), len(codes)
    pd.DataFrame({"date": np.repeat(P.dates.values, m), "code": np.tile(codes, n), "open": P.raw_open.ravel(), "close": P.raw_close.ravel(),
                  "adj_open": P.adj_open.ravel(), "adj_high": P.adj_high.ravel(), "adj_low": P.adj_low.ravel(), "adj_close": P.adj_close.ravel(),
                  "adj_volume": 1e6, "turnover": P.turnover.ravel(), "limit_up": "0", "limit_down": "0"}).to_parquet(out / "prices_daily.parquet", index=False)
    pd.DataFrame({"code": np.tile(codes, n), "date": np.repeat(P.dates.values, m), "no_trade": False}).to_parquet(out / "quality_flags.parquet", index=False)
    P.topix.reset_index().rename(columns={"index": "date"}).to_parquet(out / "topix_daily.parquet", index=False)
    intervals_for(codes, P.dates).to_parquet(out / "listed_master.parquet", index=False)
    pd.DataFrame({"Code": codes, "DiscDate": P.dates[100], "usable_from": P.dates[101]}).to_parquet(out / "fins_summary.parquet", index=False)
    res = rule_study.main(root)
    assert res["ledger_chain"]["ok"] and res["stage1_rules"]["n_tests"] > 10
    reads = [r for r in __import__("forecastlib.ledger", fromlist=["AppendOnlyLedger"]).AppendOnlyLedger(root / "ledger" / "trials.jsonl")._rows() if r["type"] == "confirmation_read"]
    assert all(r["payload"]["re_read"] is False for r in reads)
    assert (root / "results" / "rules" / "summary.json").exists()


def _write_processed(root, P, codes, last=None):
    from test_selectlib import intervals_for
    out = root / "processed"
    out.mkdir(parents=True, exist_ok=True)
    nd = len(P.dates) if last is None else last
    m = len(codes)
    sl = slice(0, nd)
    pd.DataFrame({"date": np.repeat(P.dates.values[sl], m), "code": np.tile(codes, nd), "open": P.raw_open[sl].ravel(), "close": P.raw_close[sl].ravel(),
                  "adj_open": P.adj_open[sl].ravel(), "adj_high": P.adj_high[sl].ravel(), "adj_low": P.adj_low[sl].ravel(), "adj_close": P.adj_close[sl].ravel(),
                  "adj_volume": 1e6, "turnover": P.turnover[sl].ravel(), "limit_up": "0", "limit_down": "0"}).to_parquet(out / "prices_daily.parquet", index=False)
    pd.DataFrame({"code": np.tile(codes, nd), "date": np.repeat(P.dates.values[sl], m), "no_trade": False}).to_parquet(out / "quality_flags.parquet", index=False)
    P.topix.iloc[sl].reset_index().rename(columns={"index": "date"}).to_parquet(out / "topix_daily.parquet", index=False)
    intervals_for(codes, P.dates[sl]).to_parquet(out / "listed_master.parquet", index=False)
    pd.DataFrame({"Code": codes, "DiscDate": P.dates[100], "usable_from": P.dates[101], "CurFYEn": "x", "FOP": 1.0, "FNP": 1.0, "FEPS": 1.0, "FDivAnn": 1.0,
                  "BPS": 1.0, "ROE": 0.1}).to_parquet(out / "fins_summary.parquet", index=False)


def test_diagnose_runs_and_h0_decomposition_adds_up(tmp_path):
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts" / "w5"))
    import diagnose
    P, codes = synth_panel(n_dates=1500, n_codes=40, seed=6)
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    # 合成データでは履歴 500 営業日の既定を満たす期が少ないので、診断の実行そのものと、分解の恒等式を確認する
    res = diagnose.main(root)
    assert set(res["stage0_feature_ic"]) >= {"ret5", "rev_op", "_ridge_fits"}
    h = res["h0_ideal_vs_realized_equal_weight_full_rotation"]["SEL-A"]
    assert abs(h["gap_lot_and_fill_effect"] + h["gap_cost_15bps"] - h["gap_total"]) < 2e-4
    assert h["gap_cost_15bps"] > 0 and 0 <= h["idle_cash_fraction_after_buy_mean"] < 0.5


def test_forward_record_score_summary_and_no_lookahead(tmp_path):
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts" / "w5"))
    import forward
    from selectlib import features as F
    P, codes = synth_panel(n_dates=1700, n_codes=40, seed=8)
    short, full = tmp_path / "short", tmp_path / "full"
    _write_processed(short, P, codes, last=1500)
    _write_processed(full, P, codes)
    ms = {"SEL-A": ("ridge", F.SEL_A), "SEL-C1": ("ridge", F.SEL_A + F.SEL_B)}
    r1 = forward.record(short, models=ms)
    r2 = forward.record(full, asof=str(P.dates[1499].date()), models=ms)          # 先の日付までで切って記録 → 短いデータと同じスコア（先読みなし）
    assert r1["asof"] == r2["asof"] == str(P.dates[1499].date())
    a = [r for r in forward.AppendOnlyLedger(short / "ledger" / "forward.jsonl")._rows()]
    b = [r for r in forward.AppendOnlyLedger(full / "ledger" / "forward.jsonl")._rows()]
    assert [x["payload"]["top"] for x in a] == [x["payload"]["top"] for x in b] and len(a) == 2
    assert forward.record(short, models=ms)["recorded"] == []                      # 同じ日・同じデータは重複しない
    assert forward.score(short)["scored"] == 0 and forward.score(short)["pending"] == 2     # 結果はまだ
    _write_processed(short, P, codes)                                              # データが延びた（T+22 までそろう）
    s = forward.score(short)
    assert s["scored"] == 2 and s["ledger"]["ok"]
    out = [r for r in forward.AppendOnlyLedger(short / "ledger" / "forward.jsonl")._rows() if r["type"] == "outcome"]
    assert all(o["payload"]["n_scored"] > 20 and o["payload"]["top15_mean_excess"] is not None for o in out)
    sm = forward.summary(short)["models"]
    assert sm["SEL-C1"]["independent_periods"] == 1 and sm["SEL-C1"]["primary"] is True


def test_diff_table_detects_planted_difference_and_study_defines_24_tests():
    dates = pd.bdate_range("2017-01-02", "2026-11-12")
    n, rng = len(dates), np.random.default_rng(3)
    H = 2
    names = ["x&earn_no", "x&earn_yes"]
    acc = {"names": names, "horizons": [5, 21], "dates": dates, "cnt": np.full((H, 2, n), 30.0), "sum": np.zeros((H, 2, n)),
           "cnt3": np.full((H, 3, 2, n), 10.0), "sum3": np.zeros((H, 3, 2, n)), "ucnt": np.full((H, n), 600.0), "usum": np.zeros((H, n)),
           "ucnt3": np.full((H, 3, n), 200.0), "usum3": np.zeros((H, 3, n))}
    for hi in range(H):
        acc["sum"][hi] = rng.normal(0, 0.03, (2, n)) * 30
        acc["sum"][hi, 0] += 0.008 * 30                                   # earn_no だけ反発
    d = rules.diff_table(acc, "discovery", [("x:earn_no-earn_yes", "x&earn_no", "x&earn_yes")])
    assert d[("x:earn_no-earn_yes", 5)]["t"] > 3 and d[("x:earn_no-earn_yes", 5)]["mean"] > 0.006
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts" / "w5"))
    import earnings_study
    assert len(earnings_study.builders()) == 8 and len(earnings_study.pairs()) == 4
    assert len(earnings_study.builders()) * 2 + len(earnings_study.pairs()) * 2 == 24          # 16 の水準 + 8 の差


def test_earnings_study_end_to_end_synthetic(tmp_path):
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts" / "w5"))
    import earnings_study
    P, codes = synth_panel(n_dates=1500, n_codes=25, seed=12)
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    res = earnings_study.main(root)
    assert res["exploratory"] and res["ledger_chain"]["ok"] and res["n_tests"] >= 0
    assert (root / "results" / "earnings" / "summary.json").exists()
