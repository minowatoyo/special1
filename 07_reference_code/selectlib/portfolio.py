"""売買の執行台帳（現物・買いのみ・100 株単位・全売却→再購入）。円単位で整合させる。

入力は日付×銘柄の配列。raw_open は未調整の始値（約定価格）、adj_open は分割調整済みの始値（分割をまたぐ損益の換算）。
売却代金 = 株数 × 買い日の未調整始値 × （売却日の調整後始値 ÷ 買い日の調整後始値）を円に四捨五入。コストは片道で売買代金 × bps。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

__all__ = ["simulate", "replay_ledger", "MAX_DELAY", "HOLD"]

MAX_DELAY = 5     # 売却できない日の繰り延べの上限（営業日）
HOLD = 21         # 買い日から売り日までの営業日数（T+1 → T+22）


def _yen(x: float) -> int:
    return int(math.floor(x + 0.5))


def _sell_index(adj_open, limit_down, j, t):
    """売却できる日（売買があり、ストップ安でない）の位置と、繰り延べ日数、強制評価か。"""
    n = adj_open.shape[0]
    for d in range(MAX_DELAY + 1):
        s = t + d
        if s >= n:
            break
        if np.isfinite(adj_open[s, j]) and not limit_down[s, j]:
            return s, d, False
    s = min(t + MAX_DELAY, n - 1)
    while s > 0 and not np.isfinite(adj_open[s, j]):
        s -= 1
    return s, MAX_DELAY, True


def simulate(raw_open, adj_open, limit_up, limit_down, rebalance_idx, picks, initial=10_000_000, bps=15.0, lot=100) -> dict:
    """picks: リバランスごとの {銘柄の列番号: 重み}（重みの合計は 1 以下。残りは現金）。rebalance_idx は T の位置のリスト。
    各期は T+1 始値で買い、T+22 始値（次の期の買い日）で売る。最後の期は T+22 まで日付がある期だけを使う。"""
    n_dates = raw_open.shape[0]
    periods = [(k, T) for k, T in enumerate(rebalance_idx) if T + 1 + HOLD < n_dates]
    cash, rows, equity, info, held = int(initial), [], [int(initial)], [], {}
    fee = bps / 1e4

    def liquidate(t_sell_nominal):
        nonlocal cash
        forced = delayed = 0
        for j, (sh, p_buy, a_buy) in held.items():
            s, d, f = _sell_index(adj_open, limit_down, j, t_sell_nominal)
            proceeds = _yen(sh * p_buy * (adj_open[s, j] / a_buy))
            cost = _yen(proceeds * fee)
            cash += proceeds - cost
            delayed += d > 0
            forced += f
            rows.append({"idx": s, "code_col": j, "side": "sell", "shares": sh, "price": p_buy * (adj_open[s, j] / a_buy),
                         "notional": proceeds, "cost": cost, "delay": d, "forced": f})
        held.clear()
        return delayed, forced

    for n, (k, T) in enumerate(periods):
        tb = T + 1
        delayed, forced = liquidate(tb) if held else (0, 0)
        if n > 0:
            equity.append(cash)
        w = picks[k]
        bought = skipped = 0
        eq0 = cash
        for j, wt in w.items():
            p, a = raw_open[tb, j], adj_open[tb, j]
            if not (np.isfinite(p) and np.isfinite(a)) or limit_up[tb, j] or p <= 0:
                skipped += 1
                continue
            sh = int(math.floor(eq0 * wt / (p * (1 + fee)) / lot)) * lot
            if sh <= 0:
                skipped += 1
                continue
            notional = _yen(sh * p)
            cost = _yen(notional * fee)
            if notional + cost > cash:
                skipped += 1
                continue
            cash -= notional + cost
            held[j] = (sh, p, a)
            bought += 1
            rows.append({"idx": tb, "code_col": j, "side": "buy", "shares": sh, "price": p, "notional": notional, "cost": cost, "delay": 0, "forced": False})
        info.append({"k": k, "T": T, "buy_idx": tb, "bought": bought, "skipped": skipped, "sell_delayed": delayed, "sell_forced": forced})
    if held:
        T = periods[-1][1]
        delayed, forced = liquidate(T + 1 + HOLD)
        info[-1]["final_sell_delayed"], info[-1]["final_sell_forced"] = delayed, forced
        equity.append(cash)
    led = pd.DataFrame(rows, columns=["idx", "code_col", "side", "shares", "price", "notional", "cost", "delay", "forced"])
    return {"ledger": led, "equity": equity, "final_cash": cash, "info": info, "periods": [k for k, _ in periods]}


def replay_ledger(ledger: pd.DataFrame, initial: int) -> int:
    """台帳だけから現金を再計算する（整合の確認用）。"""
    buys = ledger[ledger["side"] == "buy"]
    sells = ledger[ledger["side"] == "sell"]
    return int(initial - (buys["notional"] + buys["cost"]).sum() + (sells["notional"] - sells["cost"]).sum())
