"""S2 の口座での売買の模擬（合成データ）。現金の保存、100 株単位・銘柄数・段階の制約、植えた上昇の回収、先読みがないこと。"""
import sys
from pathlib import Path

import numpy as np
from test_rules import _write_processed
from test_seasonal import _fins, seasonal_panel

from selectlib import rules, s2port, seasonal

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def _planted(turnover=1e8, seed=11, bump_max=0.06):
    P, codes, _ = seasonal_panel(n_codes=140, seed=seed, turnover=turnover)
    fins = _fins(P, codes)
    rng = np.random.default_rng(1)
    divs = dict(zip(codes, rng.uniform(5, 60, len(codes))))
    fins["FDivAnn"] = fins["Code"].map(divs)
    mo = seasonal.months(P)
    for m in range(len(mo["last"])):
        if mo["cal"][m] not in (3, 9):
            continue
        L = mo["last"][m] - (2 if P.dates[mo["last"][m]] >= seasonal.T2_START else 3)
        e = L - 40
        if e < 5:
            continue
        for j, c in enumerate(codes):
            bump = bump_max * (divs[c] - 5) / 55
            P.adj_open[e:L + 1, j] *= np.linspace(1.0, 1.0 + bump, L - e + 1)
            P.adj_open[L + 1:, j] *= 1.0 + bump
            P.adj_close[e:L, j] *= np.linspace(1.0, 1.0 + bump, L - e + 1)[:-1]
            P.adj_close[L:, j] *= 1.0 + bump
    return P, codes, fins


def test_cash_is_conserved_and_constraints_hold():
    P, codes, fins = _planted()
    elig = np.ones(P.adj_close.shape, bool)
    va = P.va60()
    cands = s2port.candidates(P, elig, va, fins)
    assert cands and all(c["e"] == c["L"] - 40 and c["s"] == c["e"] - 1 for c in cands)
    sim = s2port.simulate(P, cands, va, (1,))
    ws = sim["windows"]
    assert ws and all(0 < w["n"] <= s2port.N_MAX for w in ws)
    # 現金の保存: 期末の現金 = 初期 + 売りの入金 − 買いの出金
    assert abs(sim["cash"][-1] - (10_000_000 + sum(w["proceeds"] for w in ws) - sum(w["invested"] for w in ws))) < 1.0
    # 窓の資金は、総資産の 1/2 以下。1 銘柄は、売買代金の 1% 以下（1 億円 × 1% = 100 万円）
    for w in ws:
        assert w["invested"] <= 0.5 * np.nanmax(sim["equity"]) + 1 and w["invested"] / w["n"] <= 1e6 * 1.004
    assert np.isfinite(sim["equity"]).all() and (sim["cash"] >= -1e-6).all()
    # 段階の制約: 全銘柄が段階 B のとき、段階 A のみの試行は 1 つも買わない
    none = s2port.simulate(P, cands, va, (0,))
    assert all(w["n"] == 0 for w in none["windows"]) and abs(none["equity"][-1] - 10_000_000) < 1e-6


def test_planted_runup_is_captured_net_of_costs_and_no_lookahead(tmp_path):
    import s2_portfolio
    P, codes, fins = _planted(bump_max=0.12)                 # 利回りの順位は株価にも左右されるので、効果は大きめに植える
    root = tmp_path / "jq"
    _write_processed(root, P, codes)
    fins.to_parquet(root / "processed" / "fins_summary.parquet", index=False)
    res = s2_portfolio.main(root)
    pri = res["trials"]["primary_tier_B_only"]
    c = pri["confirmation"]
    assert c["window_net_excess_vs_universe"]["mean"] > 0.01 and c["windows_traded"] >= 5 and c["cost_total_yen"] > 0
    # 合成データは権利月が年 2 回だけで、口座の大半が現金。母集団（常に全額投資）との年率の比較は、ここでは判定しない
    assert c["account_return_ann"] > 0 and isinstance(pri["feasible"], bool) and res["ledger_chain"]["ok"]
    assert 0 < c["stocks_per_window_mean"] <= 10 and 0 <= c["cash_share_mean"] <= 1
    assert (root / "results" / "s2_portfolio" / "summary.json").exists()
    # 先読みなし: 確認期間のデータを壊しても、発見期間の結果は変わらない
    cut = int(np.searchsorted(P.dates.values, rules.SPLIT.to_datetime64())) + 5
    for arr in (P.adj_open, P.adj_high, P.adj_low, P.adj_close, P.raw_open, P.raw_close):
        arr[cut:] *= np.linspace(0.5, 2.0, arr.shape[1])
    root2 = tmp_path / "b"
    _write_processed(root2, P, codes)
    fins.to_parquet(root2 / "processed" / "fins_summary.parquet", index=False)
    res2 = s2_portfolio.main(root2)
    assert res["trials"]["primary_tier_B_only"]["discovery"] == res2["trials"]["primary_tier_B_only"]["discovery"]


def test_no_effect_loses_roughly_the_costs():
    P, codes, fins = _planted(bump_max=0.0, seed=4)
    elig = np.ones(P.adj_close.shape, bool)
    sim = s2port.simulate(P, s2port.candidates(P, elig, P.va60(), fins), P.va60(), (1,))
    ws = [w for w in sim["windows"] if w["n"] and w["open"] == 0 and np.isfinite(w["univ"])]
    ex = np.array([w["proceeds"] / w["invested"] - 1 - w["univ"] for w in ws])
    assert -0.02 < ex.mean() < 0.006                         # 効果がなければ、往復コスト（0.6%）の分だけ負の側
