"""検証用の合成データ（実市場データではない）。

GARCH(1,1) 型のボラティリティ変動と裾の厚い誤差を持つ日足を作る。予測できる成分は、
指定したとき（signal）だけ入れる。道具の検査に使う:
  * 予測できる成分がないデータで、傾きモデルを誤って採用しないか（偽陽性）
  * 成分を埋め込んだデータで、それを見つけられるか（検出力）
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

__all__ = ["make_garch_ohlcv"]


def make_garch_ohlcv(n: int = 4000, seed: int = 0, vol: float = 0.016, alpha: float = 0.08, beta: float = 0.90,
                     nu: float = 6.0, mu: float = 0.0002, signal: dict | None = None, intraday: int = 16,
                     overnight_share: float = 0.25, start: str = "2001-01-04", price0: float = 1000.0) -> pd.DataFrame:
    """合成の日足 OHLCV。

    signal={"type": "momentum", "coef": k, "window": 63}: 日次の期待リターンに k·σ_t·M_t を足す
        （M_t は過去 window 日のリターンを σ√window で割ったもの。トレンドが続く成分）。
    signal={"type": "reversal", "coef": k, "window": 5}: 同じ形で符号を逆にする（短期の反転成分）。
    """
    rng = np.random.default_rng(seed)
    omega = (1.0 - alpha - beta) * vol * vol
    scale = math.sqrt((nu - 2.0) / nu)                       # t 分布を分散 1 にそろえる
    var = vol * vol
    logp = math.log(price0)
    win = int((signal or {}).get("window", 63))
    coef = float((signal or {}).get("coef", 0.0))
    sign = -1.0 if (signal or {}).get("type") == "reversal" else 1.0
    past_r: list = []
    past_s: list = []
    rows = []
    for _ in range(n):
        sd = math.sqrt(var)
        drift = mu
        if coef and len(past_r) >= win:
            m = sum(past_r[-win:]) / (max(np.mean(past_s[-win:]), 1e-6) * math.sqrt(win))
            drift += sign * coef * sd * float(np.clip(m, -3, 3))
        e_on = rng.standard_t(nu) * scale
        e_in = rng.standard_t(nu, size=intraday) * scale
        r_on = math.sqrt(overnight_share) * sd * e_on + drift * overnight_share
        steps = math.sqrt((1.0 - overnight_share) / intraday) * sd * e_in + drift * (1.0 - overnight_share) / intraday
        path = logp + r_on + np.cumsum(steps)
        o = logp + r_on
        c = float(path[-1])
        hi, lo = max(o, float(path.max())), min(o, float(path.min()))
        r = c - logp
        volu = math.exp(13.0 + 0.6 * abs(r) / vol + 0.3 * rng.standard_normal())
        rows.append((math.exp(o), math.exp(hi), math.exp(lo), math.exp(c), volu))
        past_r.append(r)
        past_s.append(sd)
        var = omega + alpha * r * r + beta * var
        logp = c
    idx = pd.bdate_range(start, periods=n)
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx)
    df.index.name = "date"
    return df
