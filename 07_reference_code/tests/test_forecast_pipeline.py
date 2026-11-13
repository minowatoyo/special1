"""forecastlib の判定・予測出力・台帳・レポートのテスト（合成データ。実市場データではない）。"""
import json
import math

import numpy as np
import pandas as pd
import pytest

from forecastlib import (Config, evaluate, eventstudy, features, forecast, ledger, prepare_asset, report, stats as st,
                         synth, walk_forward)
from forecastlib.walkforward import SortedBuf

FAST = dict(step=5, boot_b=300)


def test_sortedbuf_matches_sort():
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    b = SortedBuf(600)
    b.bulk(x[:200])
    for v in x[200:]:
        b.add(v)
    b.add(float("nan"))
    assert np.array_equal(b.view(), np.sort(x))
    assert abs(b.frac_ge(0.0) - (x >= 0).mean()) < 1e-12 and abs(b.frac_le(0.0) - (x <= 0).mean()) < 1e-12


def test_predictive_taus_widen_tails_and_vanish_for_large_n():
    taus = st.tau_grid(100)
    small, large = st.predictive_taus(taus, 20), st.predictive_taus(taus, 1e6)
    assert np.all(small[:50] < taus[:50]) and np.all(small[50:] > taus[50:])
    assert np.allclose(large, taus, atol=1e-6)
    assert small.min() >= 0 and small.max() <= 1 and np.all(np.diff(small) >= 0)   # 端は 0・1 で打ち切り


@pytest.fixture(scope="module")
def null_run():
    cfg = Config(**FAST)
    df = synth.make_garch_ohlcv(n=3200, seed=5003)
    a = prepare_asset(df, "NULL", cfg)
    wf = walk_forward(a, cfg)
    return cfg, df, a, wf


def test_null_series_adopts_no_tilt_and_intervals_are_calibrated(null_run):
    cfg, df, a, wf = null_run
    dec, sm = evaluate.decide(wf, cfg), evaluate.summarize(wf, cfg)
    for h in cfg.horizons:
        assert dec[h]["adopted_tilt"] is None, dec[h]
        assert dec[h]["final_model"] in ("V3", "B1", "B0")
        for m in ("B1", "V3"):
            assert 0.70 <= sm[h].loc[m, "cov80"] <= 0.90, (h, m, sm[h].loc[m, "cov80"])
        assert sm[h].loc["B1", "skill_vs_B1"] == 0.0
    # ボラティリティで伸縮する方式は、伸縮しない基準より 1 週間の予測で良い（ボラティリティの持続を埋め込んである）
    assert sm[5].loc["B1", "crps"] < sm[5].loc["B0", "crps"]


def test_strong_planted_momentum_is_detected():
    cfg = Config(step=3, boot_b=300)
    df = synth.make_garch_ohlcv(n=4000, seed=1, signal={"type": "momentum", "coef": 0.10, "window": 63})
    wf = walk_forward(prepare_asset(df, "MOM", cfg), cfg)
    dec = evaluate.decide(wf, cfg)
    for h in (5, 21):
        assert dec[h]["adopted_tilt"] in ("T1", "T3", "E1"), dec[h]
        assert wf[h]["final"]["beta"]["T1"][1] > 0.03          # mom63 の係数が正（縮小後）
        assert dec[h]["best_skill"] > 0.01


def test_pooled_panel_estimates_larger_coefficient_and_panel_decision_detects():
    """中程度の成分は 1 銘柄では見分けにくいが、同じ成分を持つ銘柄をまとめると係数の縮小が弱まり、判定も通る。"""
    cfg = Config(**FAST)
    sig = {"type": "momentum", "coef": 0.06, "window": 63}
    assets = [prepare_asset(synth.make_garch_ohlcv(n=3200, seed=300 + j, signal=sig), f"A{j}", cfg) for j in range(6)]
    single = walk_forward(assets[0], cfg)
    wfs = {a.name: walk_forward(a, cfg, tuple(b for b in assets if b is not a)) for a in assets}
    b_single = single[21]["final"]["beta"]["T1"][1]
    b_pooled = wfs["A0"][21]["final"]["beta"]["T1"][1]
    assert b_pooled > b_single > 0
    dec = evaluate.decide_panel(wfs, cfg)
    assert dec[21]["n_assets"] == 6
    assert dec[5]["adopted_tilt"] is not None or dec[21]["adopted_tilt"] is not None, (dec[5], dec[21])


def test_final_forecast_is_internally_consistent(null_run):
    cfg, df, a, wf = null_run
    dec = evaluate.decide(wf, cfg)
    c0 = float(df["close"].iloc[-1])
    levels = [{"name": "上1", "price": c0 * 1.03}, {"name": "上2", "price": c0 * 1.08},
              {"name": "下1", "price": c0 * 0.97}, {"name": "下2", "price": c0 * 0.92}]
    fc = forecast.final_forecast(a, wf, dec, cfg, levels)
    assert fc["asof"] == str(df.index[-1].date()) and fc["last_close"] == c0
    widths = []
    for h in cfg.horizons:
        hz = fc["horizons"][h]
        prices = [q["price"] for q in hz["quantiles"]]
        assert all(np.diff(prices) > 0)
        assert 0.30 < hz["p_up"] < 0.75                    # 過去平均の傾き（合成データは正のドリフト）ぶんだけ 50% から離れる
        lv = {r["name"]: r for r in hz["levels"]}
        assert lv["上1"]["p_touch"] >= lv["上2"]["p_touch"] and lv["下1"]["p_touch"] >= lv["下2"]["p_touch"]
        assert lv["上1"]["p_touch"] >= lv["上1"]["p_close_above"] - 1e-9          # 届く確率 >= 終値が上にある確率
        assert lv["下1"]["p_touch"] >= (1.0 - lv["下1"]["p_close_above"]) - 1e-9
        assert lv["上1"]["p_close_above"] > lv["上2"]["p_close_above"]
        widths.append(prices[-1] / prices[0])
        scen = [{"h": h, "name": "弱気", "lo": None, "hi": c0 * 0.97}, {"h": h, "name": "基本", "lo": c0 * 0.97, "hi": c0 * 1.03},
                {"h": h, "name": "強気", "lo": c0 * 1.03, "hi": None}]
        probs = forecast.scenario_probabilities(fc, scen)
        assert abs(sum(p["prob"] for p in probs) - 1.0) < 1e-9
    assert widths[0] < widths[1] < widths[2]                                     # 期間が長いほど区間は広い
    assert len(fc["analogs"]) > 0 and all(k in fc["analogs"][0] for k in ("date", "ret_5", "scaled_63"))
    json.dumps(fc, default=float)                                                # JSON にできる


def test_auto_levels_are_sorted_and_near_price(null_run):
    _, df, _, _ = null_run
    lv = forecast.auto_levels(df)
    prices = [d["price"] for d in lv]
    c0 = float(df["close"].iloc[-1])
    assert prices == sorted(prices) and len(lv) >= 5
    assert all(abs(p / c0 - 1) <= 0.35 for p in prices)


def test_ledger_append_is_idempotent_and_scoring_works(tmp_path, null_run):
    cfg, df, a, wf = null_run
    k = len(df) - 80
    cfg2 = Config(**FAST)
    part = df.iloc[:k]
    a2 = prepare_asset(part, "NULL", cfg2)
    wf2 = walk_forward(a2, cfg2)
    fc = forecast.final_forecast(a2, wf2, evaluate.decide(wf2, cfg2), cfg2, [])
    path = tmp_path / "ledger.csv"
    meta = {"data_sha256": "abc", "code_version": "test"}
    assert ledger.append_forecast(path, fc, meta) == 3
    assert ledger.append_forecast(path, fc, meta) == 0                            # 同じ予測は二重に記録しない
    early = ledger.score_ledger(path, part, "NULL")
    assert early["realized"].isna().all()                                        # 期日前は採点しない
    scored = ledger.score_ledger(path, df, "NULL").set_index("h")
    for h in (5, 21, 63):
        r = scored.loc[h]
        assert r["realized"] == pytest.approx(float(df["close"].iloc[k - 1 + h]))
        assert r["target_date"] == str(df.index[k - 1 + h].date())
        assert r["pinball"] > 0 and r["in90"] in (0.0, 1.0) and 0 <= r["brier_up"] <= 1


def test_event_study_columns_and_null_behaviour(null_run):
    cfg, df, a, _ = null_run
    sig = features.signal_frame(df)
    assert sig.shape[1] == len(features.SIGNAL_LABELS) == 41
    ev = eventstudy.event_study(a, sig, cfg)
    assert set(["signal", "h", "n_days", "episodes", "b", "t_b", "q_b", "var_ratio", "q_c", "now"]).issubset(ev.columns)
    tested = ev[np.isfinite(ev["p_b"])]
    assert len(tested) > 40 and (tested["q_b"] >= tested["p_b"] - 1e-12).all()
    assert (ev["q_b"] < 0.10).sum() <= 2                                         # 成分のないデータでは、補正後に残るものはほぼない


def test_event_study_finds_a_planted_state_effect():
    """「終値がボリンジャー−2σ を割った翌日は上がりやすい」という成分を埋め込むと、そのシグナルが補正後も残る。"""
    cfg = Config(**FAST)
    base = synth.make_garch_ohlcv(n=4500, seed=77)
    c = base["close"].to_numpy()
    shift = np.zeros(len(c))                       # 累積の上乗せ（対数）
    mod = np.zeros(len(c))
    state_prev = False
    for t in range(len(c)):
        shift[t] = (shift[t - 1] if t else 0.0) + (0.02 if state_prev else 0.0)
        mod[t] = c[t] * math.exp(shift[t])
        if t >= 19:
            w = mod[t - 19: t + 1]
            state_prev = bool(mod[t] < w.mean() - 2.0 * w.std())
    df = base.copy()
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].to_numpy() * np.exp(shift)
    a = prepare_asset(df, "PLANT", cfg)
    ev = eventstudy.event_study(a, features.signal_frame(df), cfg)
    row = ev[(ev["signal"] == "bb_below_lower") & (ev["h"] == 5)].iloc[0]
    assert row["n_days"] > 60 and row["b"] > 0.2 and row["q_b"] < 0.10, row.to_dict()


def test_report_builds_with_all_sections(tmp_path, null_run):
    cfg, df, a, wf = null_run
    sm, dec, tc = evaluate.summarize(wf, cfg), evaluate.decide(wf, cfg), evaluate.touch_summary(wf, cfg)
    ev = eventstudy.event_study(a, features.signal_frame(df), cfg)
    fc = forecast.final_forecast(a, wf, dec, cfg)
    c0 = fc["last_close"]
    scen = forecast.scenario_probabilities(fc, [{"h": 5, "name": "基本", "lo": c0 * 0.97, "hi": c0 * 1.03, "weight": 0.5}])
    md = report.build_report("合成", a, {"errors": [], "warnings": ["w"], "info": ["i"], "suspect_splits": []}, wf, sm, dec, tc, ev, fc, cfg,
                             {"データ": "x"}, scen, {"図": "fan.png"})
    for head in ("## 1. 結論", "## 2. データの検査", "## 3. 予測分布", "## 4. シナリオ区間に入る確率", "## 5. 検証", "## 6. チャートシグナル", "## 7. 過去の似た局面", "## 限界"):
        assert head in md
    assert "nan" not in md.lower().replace("nanosecond", "")
    report.plot_fan(a, fc, tmp_path / "fan.png")
    report.plot_calibration(wf, dec, tmp_path / "cal.png")
    assert (tmp_path / "fan.png").stat().st_size > 10000 and (tmp_path / "cal.png").stat().st_size > 5000


# ---- 改訂仕様 v0.2 FIX-01/02/09 ----
def test_features_ret5_ret21_use_daily_sigma_without_double_sqrt_h():
    """FIX-09(1): ret5/ret21 は日次 σ1 で割り √n で規格化する。一定ボラの iid なら標準偏差はほぼ 1。"""
    rng = np.random.default_rng(1)
    n = 6000
    r = rng.normal(0, 0.012, n)
    c = 100 * np.exp(np.cumsum(r))
    df = pd.DataFrame({"open": c, "high": c * 1.002, "low": c * 0.998, "close": c, "volume": 1e6}, index=pd.bdate_range("2000-01-03", periods=n))
    f = features.feature_frame(df)
    for col in ("ret5", "ret21"):
        assert 0.9 < f[col].iloc[1000:].std() < 1.1


def test_loc_mode_default_unchanged_and_modes_run():
    """FIX-01/02: 既定は縮小なしの過去平均（d=h·m）。centered はドリフトを変えず、centered_shrink は 0.5 倍にする。"""
    df = synth.make_garch_ohlcv(n=1800, seed=3)
    out = {}
    for mode in ("raw", "centered", "centered_shrink"):
        cfg = Config(step=40, boot_b=50, loc_mode=mode)
        a = prepare_asset(df, "x", cfg)
        out[mode] = (a.drift_scale, walk_forward(a, cfg))
    assert Config().loc_mode == "raw" and out["raw"][0] == 1.0 and out["centered"][0] == 1.0 and out["centered_shrink"][0] == 0.5
    h = 21
    d_raw, d_cen, d_shr = (out[m][1][h]["diag"]["drift"] for m in ("raw", "centered", "centered_shrink"))
    ok = np.isfinite(d_raw)
    assert np.allclose(d_raw[ok], d_cen[ok]) and np.allclose(d_shr[ok], 0.5 * d_raw[ok])
    for m in out:
        dg = out[m][1][h]["diag"]
        assert {"drift", "z_mean", "z_median", "v3_mean", "v3_median", "t3_mean", "t3_median"} <= set(dg)


def test_ridge_scale_by_assets_flag_changes_penalty_only_when_set():
    """FIX-09(3): 既定はパネルの銘柄数で罰則を変えない。フラグを立てると銘柄数に比例して強くなる（単独銘柄なら同一）。"""
    df = synth.make_garch_ohlcv(n=1500, seed=5)
    cfg0 = Config(step=60, boot_b=30)
    cfg1 = Config(step=60, boot_b=30, ridge_scale_by_assets=True)
    a0, a1 = prepare_asset(df, "x", cfg0), prepare_asset(df, "x", cfg1)
    r0, r1 = walk_forward(a0, cfg0), walk_forward(a1, cfg1)
    assert np.allclose(np.nan_to_num(r0[21]["scale"]), np.nan_to_num(r1[21]["scale"]))


def test_outer_evaluation_selects_only_from_past_and_reports_optimism():
    """FIX-05: 外側の評価は、各ブロックの前に確定した損失だけで採用モデルを選ぶ。"""
    from forecastlib import outer
    df = synth.make_garch_ohlcv(n=3000, seed=11)
    cfg = Config(step=5, boot_b=60, horizons=(5, 21))
    wf = walk_forward(prepare_asset(df, "x", cfg), cfg)
    r = outer.outer_evaluate(wf, cfg, n_blocks=5)
    o = r[21]
    assert o["n_outer"] > 100 and np.isfinite(o["crps_outer"]) and len(o["blocks"]) == 5
    for b in o["blocks"]:
        assert b["train_n"] > 0 and b["selected"] in wf[21]["models"]
    assert all(o["blocks"][i]["train_n"] <= o["blocks"][i + 1]["train_n"] for i in range(4))   # 学習は時間とともに延びる（先読みなし）
    # 外側の損失は、選ばれたモデルの損失の連結に一致する
    assert "optimism(insample_skill - outer_skill)" in o


def _fake_fc(asof="2024-01-04", h=21):
    qs = [{"p": p, "price": 100 * math.exp(0.1 * (p - 0.5))} for p in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)]
    return {"asset": "7203", "asof": asof, "last_close": 100.0, "horizons": {h: {"model": "V3", "quantiles": qs, "p_up": 0.52, "sigma_h": 0.06}}}


META = {"source": "jquants", "data_manifest_sha256": "a" * 64, "code_version": "abc123", "config_sha256": "b" * 64}


def test_append_only_ledger_chain_detects_tampering_and_rejects_provisional(tmp_path):
    from forecastlib.ledger import AppendOnlyLedger, LedgerError
    L = AppendOnlyLedger(tmp_path / "ledger" / "f.jsonl")
    assert len(L.append_forecast(_fake_fc(), META)) == 1
    assert L.append_forecast(_fake_fc(), META) == []                            # 同じ予測は重複させない
    assert len(L.append_forecast(_fake_fc("2024-01-05"), META)) == 1
    assert L.verify() == {"ok": True, "rows": 2, "first_bad": None}
    with pytest.raises(LedgerError):
        L.append_forecast(_fake_fc("2024-01-08"), {**META, "source": "mixed"})   # 暫定データは記録しない
    with pytest.raises(LedgerError):
        L.append_forecast(_fake_fc("2024-01-08"), {**META, "config_sha256": ""})
    lines = L.path.read_text(encoding="utf-8").splitlines()
    L.path.write_text("\n".join([lines[0].replace('"p_up":0.52', '"p_up":0.99'), lines[1]]) + "\n", encoding="utf-8")   # 書き換え
    assert L.verify()["ok"] is False and L.verify()["first_bad"] == 0
    with pytest.raises(LedgerError):
        L.append_forecast(_fake_fc("2024-01-09"), META)                          # 壊れた台帳には追記しない


def test_ledger_scoring_appends_outcomes_without_touching_forecasts(tmp_path):
    from forecastlib.ledger import AppendOnlyLedger
    idx = pd.bdate_range("2024-01-01", periods=60)
    df = pd.DataFrame({"close": 100.0 * np.exp(np.linspace(0, 0.1, 60))}, index=idx)
    L = AppendOnlyLedger(tmp_path / "f.jsonl")
    L.append_forecast(_fake_fc(str(idx[3].date()), 21), META)
    L.append_forecast(_fake_fc(str(idx[55].date()), 21), META)                   # 期日が来ていない
    before = L.path.read_text(encoding="utf-8").splitlines()
    out = L.score(df, "7203")
    assert len(out) == 1 and out[0]["payload"]["target_date"] == str(idx[24].date())
    assert L.score(df, "7203") == []                                              # 二重に採点しない
    after = L.path.read_text(encoding="utf-8").splitlines()
    assert after[:2] == before and len(after) == 3 and L.verify()["ok"]
