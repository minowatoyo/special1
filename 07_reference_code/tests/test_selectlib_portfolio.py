"""執行台帳の整合（円単位）。3 ケース: 単一銘柄の買い持ち、等ウエイト保有、定期入れ替え。合成データ。"""
import numpy as np
import pytest

from selectlib import portfolio as pf


def mats(n_dates=70, prices=((1000.0, 2000.0, 500.0),), growth=(0.001,), split_at=None):
    n = len(prices[0])
    raw = np.zeros((n_dates, n))
    for j in range(n):
        raw[:, j] = prices[0][j] * (1 + growth[j % len(growth)]) ** np.arange(n_dates)
    adj = raw.copy()
    return raw, adj, np.zeros_like(raw, dtype=bool), np.zeros_like(raw, dtype=bool)


def test_single_stock_buy_and_hold_reconciles_to_one_yen():
    raw, adj, ul, ll = mats(prices=((1234.0,),), growth=(0.002,))
    r = pf.simulate(raw, adj, ul, ll, [5], {0: {0: 1.0}}, initial=10_000_000, bps=15)
    # 独立の計算
    p_buy, p_sell = raw[6, 0], raw[6 + pf.HOLD, 0]
    sh = int(10_000_000 / (p_buy * 1.0015) // 100) * 100
    notional = int(sh * p_buy + 0.5)
    cost_b = int(notional * 0.0015 + 0.5)
    proceeds = int(sh * p_buy * (p_sell / p_buy) + 0.5)
    cost_s = int(proceeds * 0.0015 + 0.5)
    expect = 10_000_000 - notional - cost_b + proceeds - cost_s
    assert r["final_cash"] == expect
    assert pf.replay_ledger(r["ledger"], 10_000_000) == r["final_cash"]
    assert abs(r["final_cash"] - expect) <= 1 and (r["ledger"]["shares"] % 100 == 0).all()


def test_equal_weight_hold_three_stocks():
    raw, adj, ul, ll = mats(prices=((1000.0, 2000.0, 500.0),), growth=(0.001, -0.002, 0.003))
    r = pf.simulate(raw, adj, ul, ll, [3], {0: {0: 1 / 3, 1: 1 / 3, 2: 1 / 3}}, initial=9_000_000, bps=10)
    led = r["ledger"]
    assert (led["side"] == "buy").sum() == 3 and (led["side"] == "sell").sum() == 3
    assert pf.replay_ledger(led, 9_000_000) == r["final_cash"]
    exp = 9_000_000
    for j in range(3):
        p0, p1 = raw[4, j], raw[4 + pf.HOLD, j]
        sh = int(3_000_000 / (p0 * 1.001) // 100) * 100
        nb = int(sh * p0 + 0.5)
        pr = int(sh * p1 + 0.5)
        exp += -nb - int(nb * 0.001 + 0.5) + pr - int(pr * 0.001 + 0.5)
    assert abs(r["final_cash"] - exp) <= 1
    assert r["final_cash"] >= 0 and all(i["skipped"] == 0 for i in r["info"])


def test_periodic_rotation_chain_of_two_periods():
    raw, adj, ul, ll = mats(n_dates=90, prices=((1000.0, 800.0),), growth=(0.002, 0.001))
    R = [2, 2 + pf.HOLD]
    r = pf.simulate(raw, adj, ul, ll, R, {0: {0: 1.0}, 1: {1: 1.0}}, initial=5_000_000, bps=15)
    assert r["periods"] == [0, 1] and len(r["equity"]) == 3
    assert pf.replay_ledger(r["ledger"], 5_000_000) == r["final_cash"]
    cash = 5_000_000
    for col, T in ((0, 2), (1, 2 + pf.HOLD)):
        p0, p1 = raw[T + 1, col], raw[T + 1 + pf.HOLD, col]
        sh = int(cash / (p0 * 1.0015) // 100) * 100
        nb = int(sh * p0 + 0.5)
        pr = int(sh * p1 + 0.5)
        cash = cash - nb - int(nb * 0.0015 + 0.5) + pr - int(pr * 0.0015 + 0.5)
    assert abs(r["final_cash"] - cash) <= 1
    assert r["equity"][1] == r["equity"][1] and r["equity"][-1] == r["final_cash"]


def test_split_between_buy_and_sell_does_not_create_phantom_gain():
    raw, adj, ul, ll = mats(prices=((1000.0,),), growth=(0.0,))
    raw[6 + 10:, 0] = 500.0                               # 10 営業日後に 2 分割（未調整は半値）
    adj[:6 + 10, 0] = 500.0                               # 調整後は全期間 500
    adj[6 + 10:, 0] = 500.0
    r = pf.simulate(raw, adj, ul, ll, [5], {0: {0: 1.0}}, initial=1_000_000, bps=0)
    assert abs(r["final_cash"] - 1_000_000) < 1000 + 1    # 100 株未満の端数ぶんの現金だけの差


def test_skip_limit_up_buy_and_delay_limit_down_sell():
    raw, adj, ul, ll = mats(prices=((1000.0, 1000.0),), growth=(0.0, 0.0))
    ul[6, 0] = True                                       # 銘柄 0 は買い日にストップ高 → 買えない
    ll[6 + pf.HOLD, 1] = True                             # 銘柄 1 は売り日にストップ安 → 1 日繰り延べ
    r = pf.simulate(raw, adj, ul, ll, [5], {0: {0: 0.5, 1: 0.5}}, initial=2_000_000, bps=0)
    assert r["info"][0]["skipped"] == 1 and r["info"][0]["bought"] == 1
    sell = r["ledger"][r["ledger"]["side"] == "sell"].iloc[0]
    assert sell["delay"] == 1 and not sell["forced"]
    assert pf.replay_ledger(r["ledger"], 2_000_000) == r["final_cash"]


def test_nan_open_on_sell_uses_forced_valuation_after_max_delay():
    raw, adj, ul, ll = mats(prices=((1000.0,),), growth=(0.0,), n_dates=80)
    adj[6 + pf.HOLD:, 0] = np.nan
    r = pf.simulate(raw, adj, ul, ll, [5], {0: {0: 1.0}}, initial=1_000_000, bps=0)
    sell = r["ledger"][r["ledger"]["side"] == "sell"].iloc[0]
    assert sell["forced"] and sell["delay"] == pf.MAX_DELAY


# ---- 差分売買 ----
def test_diff_equals_full_when_every_pick_is_replaced():
    raw, adj, ul, ll = mats(n_dates=100, prices=((1000.0, 800.0, 1500.0),), growth=(0.002, 0.001, 0.003))
    R = [2, 2 + pf.HOLD, 2 + 2 * pf.HOLD]
    picks = {0: {0: 1.0}, 1: {1: 1.0}, 2: {2: 1.0}}                       # 毎回、別の銘柄に全入れ替え
    a = pf.simulate(raw, adj, ul, ll, R, picks, initial=5_000_000, bps=15)
    b = pf.simulate_diff(raw, adj, ul, ll, R, picks, initial=5_000_000, bps=15)
    assert a["final_cash"] == b["final_cash"]
    assert pf.replay_ledger(b["ledger"], 5_000_000) == b["final_cash"]


def test_diff_trades_far_less_when_picks_repeat_and_ledger_reconciles():
    raw, adj, ul, ll = mats(n_dates=140, prices=((1000.0, 800.0, 1500.0),), growth=(0.002, -0.001, 0.003))
    R = [2 + i * pf.HOLD for i in range(5)]
    picks = {k: {0: 1 / 3, 1: 1 / 3, 2: 1 / 3} for k in range(5)}         # 毎回、同じ 3 銘柄
    full = pf.simulate(raw, adj, ul, ll, R, picks, initial=9_000_000, bps=15)
    diff = pf.simulate_diff(raw, adj, ul, ll, R, picks, initial=9_000_000, bps=15)
    assert pf.replay_ledger(diff["ledger"], 9_000_000) == diff["final_cash"] >= 0
    assert diff["ledger"]["cost"].sum() < 0.4 * full["ledger"]["cost"].sum()
    assert pf.turnover(diff["ledger"], diff["equity"]) < 0.35 < 0.9 < pf.turnover(full["ledger"], full["equity"])
    assert len(diff["equity"]) == len(diff["periods"]) + 1 == len(full["equity"])
    gross_full = full["final_cash"] + full["ledger"]["cost"].sum()
    gross_diff = diff["final_cash"] + diff["ledger"]["cost"].sum()
    assert abs(gross_full - gross_diff) < 0.02 * 9_000_000                 # コスト前の成績はほぼ同じ（ロットの端数ぶんの差）


def test_diff_holds_through_split_without_phantom_gain_and_delays_limit_down_sale():
    raw, adj, ul, ll = mats(n_dates=100, prices=((1000.0, 1000.0),), growth=(0.0, 0.0))
    raw[20:, 0] = 500.0                                                    # 保有の途中で 2 分割（未調整は半値、調整後は一定）
    R = [2, 2 + pf.HOLD]
    r = pf.simulate_diff(raw, adj, ul, ll, R, {0: {0: 1.0}, 1: {0: 1.0}}, initial=1_000_000, bps=0)
    assert abs(r["final_cash"] - 1_000_000) <= 1000                       # 端数の現金ぶんだけ
    ll2 = ll.copy()
    ll2[2 + pf.HOLD + 1, 0] = True                                         # 2 回目の買い日にストップ安の銘柄 0 を、入れ替えで売る
    r2 = pf.simulate_diff(raw, adj, ul, ll2, R, {0: {0: 1.0}, 1: {1: 1.0}}, initial=1_000_000, bps=0)
    sell = r2["ledger"][(r2["ledger"]["side"] == "sell") & (r2["ledger"]["code_col"] == 0)].iloc[0]
    assert sell["delay"] == 1 and pf.replay_ledger(r2["ledger"], 1_000_000) == r2["final_cash"]


def test_diff_never_overspends_cash_and_skips_untradable():
    raw, adj, ul, ll = mats(n_dates=100, prices=((1000.0, 1000.0),), growth=(0.0, 0.0))
    ul[3, 1] = True                                                        # 買い日にストップ高 → 銘柄 1 は買えない
    r = pf.simulate_diff(raw, adj, ul, ll, [2], {0: {0: 0.5, 1: 0.5}}, initial=2_000_000, bps=15)
    assert r["info"][0]["bought"] == 1 and r["info"][0]["skipped"] == 1 and r["final_cash"] > 0
    assert pf.replay_ledger(r["ledger"], 2_000_000) == r["final_cash"]
