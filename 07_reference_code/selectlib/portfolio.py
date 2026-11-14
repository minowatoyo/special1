"""売買の執行台帳（現物・買いのみ・100 株単位・全売却→再購入）。円単位で整合させる。

入力は日付×銘柄の配列。raw_open は未調整の始値（約定価格）、adj_open は分割調整済みの始値（分割をまたぐ損益の換算）。
売却代金 = 株数 × 買い日の未調整始値 × （売却日の調整後始値 ÷ 買い日の調整後始値）を円に四捨五入。コストは片道で売買代金 × bps。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

__all__ = ["simulate", "simulate_diff", "replay_ledger", "turnover", "MAX_DELAY", "HOLD"]

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


def turnover(ledger: pd.DataFrame, equity: list) -> float:
    """1 期あたりの入れ替え率 = 売買代金の合計 ÷ 2 ÷ 平均資産 ÷ 期数（全売却→再購入は約 1）。"""
    n = max(len(equity) - 1, 1)
    return float(ledger["notional"].sum() / 2 / (np.mean(equity) * n))


def simulate_diff(raw_open, adj_open, limit_up, limit_down, rebalance_idx, picks, initial=10_000_000, bps=15.0, lot=100) -> dict:
    """差分売買（docs/w5_protocol.md の「差分売買」）。上位から外れた銘柄は全売却、残りは目標株数との差だけを売買する。
    保有は (株数, 評価の基準価格, 基準日の調整後始値)。分割をまたいでも同等の価格 = 基準価格 × 調整後始値 ÷ 基準日の調整後始値 で評価する。"""
    n_dates = raw_open.shape[0]
    periods = [(k, T) for k, T in enumerate(rebalance_idx) if T + 1 + HOLD < n_dates]
    cash, rows, equity, info, held = int(initial), [], [int(initial)], [], {}
    fee = bps / 1e4

    def mark(j, t):
        sh, p_ref, a_ref, last = held[j]
        a = adj_open[t, j]
        return p_ref * a / a_ref if np.isfinite(a) else last

    def sell(j, shares, s, price):
        nonlocal cash
        proceeds = _yen(shares * price)
        cost = _yen(proceeds * fee)
        cash += proceeds - cost
        return proceeds, cost

    def drop(j, t, d_info):
        """保有 j を全売却（繰り延べあり）。"""
        sh, p_ref, a_ref, _ = held[j]
        s, d, f = _sell_index(adj_open, limit_down, j, t)
        price = p_ref * adj_open[s, j] / a_ref
        proceeds, cost = sell(j, sh, s, price)
        rows.append({"idx": s, "code_col": j, "side": "sell", "shares": sh, "price": price, "notional": proceeds, "cost": cost, "delay": d, "forced": f})
        d_info["sell_delayed"] += d > 0
        d_info["sell_forced"] += f
        del held[j]

    for n, (k, T) in enumerate(periods):
        tb = T + 1
        e_pre = cash + sum(_yen(held[j][0] * mark(j, tb)) for j in held)
        if n > 0:
            equity.append(int(e_pre))
        w = picks[k]
        di = {"k": k, "T": T, "buy_idx": tb, "bought": 0, "skipped": 0, "sold_out": 0, "trimmed": 0, "topped_up": 0, "sell_delayed": 0, "sell_forced": 0}
        for j in [j for j in held if j not in w]:
            drop(j, tb, di)
            di["sold_out"] += 1
        e_post = cash + sum(_yen(held[j][0] * mark(j, tb)) for j in held)
        targets = {}
        for j, wt in w.items():
            a = adj_open[tb, j]
            price = mark(j, tb) if j in held else raw_open[tb, j]
            if not (np.isfinite(price) and price > 0 and np.isfinite(a)):
                targets[j] = None
                continue
            targets[j] = (int(math.floor(e_post * wt / (price * (1 + fee)) / lot)) * lot, price, a)
        for j, tg in targets.items():                                      # 超過ぶんの売り
            if tg is None or j not in held:
                continue
            sh, p_ref, a_ref, _ = held[j]
            excess = sh - tg[0]
            if excess >= lot and not limit_down[tb, j]:
                proceeds, cost = sell(j, excess, tb, tg[1])
                rows.append({"idx": tb, "code_col": j, "side": "sell", "shares": excess, "price": tg[1], "notional": proceeds, "cost": cost, "delay": 0, "forced": False})
                held[j] = [sh - excess, tg[1], tg[2], tg[1]]
                di["trimmed"] += 1
        for j, tg in targets.items():                                      # 新規と買い増し
            if tg is None or limit_up[tb, j]:
                di["skipped"] += 1
                continue
            cur = held[j][0] if j in held else 0
            add = tg[0] - cur
            if add < lot:
                if j in held:
                    held[j] = [held[j][0], tg[1], tg[2], tg[1]]
                continue
            notional = _yen(add * tg[1])
            cost = _yen(notional * fee)
            if notional + cost > cash:
                di["skipped"] += 1
                continue
            cash -= notional + cost
            held[j] = [cur + add, tg[1], tg[2], tg[1]]
            rows.append({"idx": tb, "code_col": j, "side": "buy", "shares": add, "price": tg[1], "notional": notional, "cost": cost, "delay": 0, "forced": False})
            di["topped_up" if cur else "bought"] += 1
        info.append(di)
    if held:
        T = periods[-1][1]
        di = info[-1]
        for j in list(held):
            drop(j, T + 1 + HOLD, di)
        equity.append(cash)
    led = pd.DataFrame(rows, columns=["idx", "code_col", "side", "shares", "price", "notional", "cost", "delay", "forced"])
    return {"ledger": led, "equity": equity, "final_cash": cash, "info": info, "periods": [k for k, _ in periods]}
