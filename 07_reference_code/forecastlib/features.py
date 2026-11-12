"""予測に使う特徴量（連続値）とチャートシグナル（真偽値）。すべて先読みなし。

  * 特徴量は「σ（ボラティリティ）単位」に直してから、その時点までの平均・標準偏差で標準化する
    （銘柄や時期で値動きの大きさが違っても比べられるようにするため）。
  * シグナルは資料集の手法（移動平均、一目均衡表、オシレーター、出来高、ローソク足、急変）を
    機械的な規則に落としたもの。規則としきい値は事前登録（09_forecasting/02_protocol.md）。
指標の計算は chartlib（TA-Lib と照合済みの参考実装）を使う。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from chartlib import candles as cn
from chartlib import indicators as ind

from .vol import ewma_variance, log_returns

__all__ = ["feature_frame", "standardize_expanding", "signal_frame", "FEATURE_SETS", "KNN_FEATURES",
           "align_aux", "SIGNAL_LABELS"]

FEATURE_SETS = {
    "T1": ["mom63", "mom126", "mom252"],                       # 3〜12 か月のトレンド
    "T2": ["ret5", "ret21"],                                   # 1 週間・1 か月の値動き（短期リバーサルの候補）
    "T3": ["mom63", "mom126", "mom252", "ret5", "ret21", "kairi25", "kairi200", "rsi14c", "macdh",
           "adx_dir", "dd252", "volr_signed", "vol_trend", "gap", "ichi_pos"],
}
KNN_FEATURES = ["ret1", "ret5", "ret21", "mom126", "dd252", "volstate", "vol_trend"]


def _sd(r: pd.Series, n: int) -> pd.Series:
    return r.rolling(n).std(ddof=1)


def align_aux(index: pd.DatetimeIndex, aux_close: pd.Series, lag: int = 1) -> pd.Series:
    """補助系列（指数・為替など）を銘柄の日付に合わせる。

    lag=0: 同じ日付までの値を使う（同じ取引時間の系列。日経平均・TOPIX など）。
    lag=1: 前の日付までの値だけを使う（東京の大引けより後に終わる系列。ドル円の NY 終値、米国指数など）。
    先読みを避けるため、既定は lag=1。
    """
    a = aux_close.dropna().sort_index()
    left = pd.DataFrame({"date": index})
    right = pd.DataFrame({"date": a.index, "v": a.to_numpy(dtype=float)})
    m = pd.merge_asof(left, right, on="date", allow_exact_matches=(lag == 0))
    return pd.Series(m["v"].to_numpy(), index=index)


def feature_frame(df: pd.DataFrame, aux: dict | None = None) -> pd.DataFrame:
    """連続特徴量（標準化前）。aux = {名前: (終値の Series, lag)} を渡すと補助系列の特徴量を足す。"""
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    r = log_returns(c)
    s1 = np.sqrt(ewma_variance(r))
    lc = np.log(c)
    f = pd.DataFrame(index=df.index)
    f["ret1"] = r / s1.shift(1)
    f["ret5"] = (lc - lc.shift(5)) / (s1.shift(5) * np.sqrt(5))
    f["ret21"] = (lc - lc.shift(21)) / (s1.shift(21) * np.sqrt(21))
    for n in (63, 126, 252):
        f[f"mom{n}"] = (lc - lc.shift(n)) / (_sd(r, n) * np.sqrt(n))
    sd252 = _sd(r, 252)
    f["kairi25"] = (c / ind.sma(c, 25) - 1.0) / (s1 * np.sqrt(25 / 3))
    f["kairi200"] = (c / ind.sma(c, 200) - 1.0) / (sd252 * np.sqrt(200 / 3))
    f["rsi14c"] = (ind.rsi(c, 14) - 50.0) / 20.0
    f["macdh"] = ind.macd(c)["hist"] / (c * s1)
    dmi = ind.dmi_adx(h, l, c, 14)
    f["adx_dir"] = dmi["adx"] / 25.0 * np.sign(dmi["plus_di"] - dmi["minus_di"])
    f["dd252"] = np.log(c / c.rolling(252).max()) / (sd252 * np.sqrt(63))
    if v.notna().sum() > 300 and (v > 0).sum() > 300:
        vv = v.where(v > 0)
        f["volr_signed"] = np.log(vv / ind.sma(vv, 20).shift(1)) * np.sign(r)
        f["vol_trend"] = np.log(ind.sma(vv, 5) / ind.sma(vv, 60))
    else:
        f["volr_signed"] = np.nan
        f["vol_trend"] = np.nan
    f["gap"] = np.log(o / c.shift(1)) / s1.shift(1)
    ich = ind.ichimoku(h, l, c)
    top = ich[["senkou_a", "senkou_b"]].max(axis=1, skipna=False)
    bot = ich[["senkou_a", "senkou_b"]].min(axis=1, skipna=False)
    pos = pd.Series(0.0, index=df.index).where(top.notna())
    pos = pos.mask(c > top, 1.0).mask(c < bot, -1.0)
    f["ichi_pos"] = pos
    f["volstate"] = np.log(s1 / sd252)
    for name, (aclose, lag) in (aux or {}).items():
        a = align_aux(df.index, aclose, lag)
        la = np.log(a)
        ra = la.diff()
        sa = np.sqrt(ewma_variance(ra))
        f[f"{name}_ret5"] = (la - la.shift(5)) / (sa.shift(5) * np.sqrt(5))
        f[f"{name}_ret21"] = (la - la.shift(21)) / (sa.shift(21) * np.sqrt(21))
        rel = r - ra
        f[f"{name}_rel63"] = ((lc - lc.shift(63)) - (la - la.shift(63))) / (_sd(rel, 63) * np.sqrt(63))
    return f.replace([np.inf, -np.inf], np.nan)


def standardize_expanding(f: pd.DataFrame, min_obs: int = 250, clip: float = 5.0) -> pd.DataFrame:
    """その時点までの平均・標準偏差で標準化する（先読みなし）。±clip で打ち切る。"""
    m = f.expanding(min_periods=min_obs).mean()
    s = f.expanding(min_periods=min_obs).std(ddof=1)
    z = (f - m) / s.where(s > 0)
    return z.clip(-clip, clip)


SIGNAL_LABELS = {
    "above_sma25": "終値が25日線より上", "above_sma75": "終値が75日線より上", "above_sma200": "終値が200日線より上",
    "sma25_gt_sma75": "25日線が75日線より上", "perfect_order_up": "パーフェクトオーダー（5>25>75）",
    "perfect_order_down": "逆パーフェクトオーダー（5<25<75）", "adx_up": "ADX>25 かつ +DI>-DI",
    "adx_down": "ADX>25 かつ -DI>+DI", "ichi_above_cloud": "一目: 雲の上", "ichi_below_cloud": "一目: 雲の下",
    "sanyaku_kouten": "一目: 三役好転", "sanyaku_gyakuten": "一目: 三役逆転", "macd_pos": "MACD ヒストグラムが正",
    "golden_cross_25_75": "ゴールデンクロス（25/75、当日）", "dead_cross_25_75": "デッドクロス（25/75、当日）",
    "new_high_252": "終値が52週高値", "new_low_252": "終値が52週安値",
    "donchian20_up": "20日高値を終値で上抜け", "donchian20_down": "20日安値を終値で下抜け",
    "rsi_lt30": "RSI(14)<30", "rsi_lt20": "RSI(14)<20", "rsi_gt70": "RSI(14)>70",
    "bb_below_lower": "終値がボリンジャー−2σ未満", "bb_above_upper": "終値がボリンジャー+2σ超",
    "kairi25_lt_m10": "25日線乖離率<−10%", "kairi25_gt_p10": "25日線乖離率>+10%",
    "stoch_lt20": "ストキャスティクス Slow%K<20", "stoch_gt80": "ストキャスティクス Slow%K>80",
    "vol_spike_up": "出来高が20日平均の2倍超で上昇", "vol_spike_down": "出来高が20日平均の2倍超で下落",
    "bullish_engulfing": "陽の包み足（下降後）", "bearish_engulfing": "陰の包み足（上昇後）",
    "hammer": "ハンマー（下降後）", "shooting_star": "流れ星（上昇後）",
    "shock_up_5d": "直近5日に+3σ以上の急騰日", "shock_down_5d": "直近5日に−3σ以下の急落日",
    "surge_5d": "5日間で+3σ以上の上昇", "crash_5d": "5日間で−3σ以下の下落",
    "drawdown_40": "52週高値（終値）から40%以上の下落", "gap_up_2s": "始値の窓上げが+2σ以上", "gap_down_2s": "始値の窓下げが−2σ以下",
}


def signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    """チャートシグナル（事前登録の規則）。その日の終値で確定する真偽値。未定義の期間は False。"""
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    r = log_returns(c)
    s1 = np.sqrt(ewma_variance(r))
    lc = np.log(c)
    sma5, sma25, sma75, sma200 = (ind.sma(c, n) for n in (5, 25, 75, 200))
    dmi = ind.dmi_adx(h, l, c, 14)
    ich = ind.ichimoku(h, l, c)
    top = ich[["senkou_a", "senkou_b"]].max(axis=1, skipna=False)
    bot = ich[["senkou_a", "senkou_b"]].min(axis=1, skipna=False)
    rsi = ind.rsi(c, 14)
    bb = ind.bollinger(c, 20, 2.0)
    st = ind.stochastic(h, l, c)["slow_k"]
    hist = ind.macd(c)["hist"]
    kairi = c / sma25 - 1.0
    z1 = r / s1.shift(1)
    ret5 = (lc - lc.shift(5)) / (s1.shift(5) * np.sqrt(5))
    gap = np.log(o / c.shift(1)) / s1.shift(1)
    vv = v.where(v > 0)
    vavg = ind.sma(vv, 20).shift(1)
    s = pd.DataFrame(index=df.index)
    s["above_sma25"] = c > sma25
    s["above_sma75"] = c > sma75
    s["above_sma200"] = c > sma200
    s["sma25_gt_sma75"] = sma25 > sma75
    s["perfect_order_up"] = (sma5 > sma25) & (sma25 > sma75)
    s["perfect_order_down"] = (sma5 < sma25) & (sma25 < sma75)
    s["adx_up"] = (dmi["adx"] > 25) & (dmi["plus_di"] > dmi["minus_di"])
    s["adx_down"] = (dmi["adx"] > 25) & (dmi["minus_di"] > dmi["plus_di"])
    s["ichi_above_cloud"] = c > top
    s["ichi_below_cloud"] = c < bot
    s["sanyaku_kouten"] = (ich["tenkan"] > ich["kijun"]) & (c > top) & (c > c.shift(26))
    s["sanyaku_gyakuten"] = (ich["tenkan"] < ich["kijun"]) & (c < bot) & (c < c.shift(26))
    s["macd_pos"] = hist > 0
    up = sma25 > sma75
    s["golden_cross_25_75"] = up & (sma25.shift(1) <= sma75.shift(1))
    s["dead_cross_25_75"] = (sma25 < sma75) & (sma25.shift(1) >= sma75.shift(1))
    s["new_high_252"] = c >= c.rolling(252).max()
    s["new_low_252"] = c <= c.rolling(252).min()
    s["donchian20_up"] = c > h.rolling(20).max().shift(1)
    s["donchian20_down"] = c < l.rolling(20).min().shift(1)
    s["rsi_lt30"] = rsi < 30
    s["rsi_lt20"] = rsi < 20
    s["rsi_gt70"] = rsi > 70
    s["bb_below_lower"] = c < bb["lower"]
    s["bb_above_upper"] = c > bb["upper"]
    s["kairi25_lt_m10"] = kairi < -0.10
    s["kairi25_gt_p10"] = kairi > 0.10
    s["stoch_lt20"] = st < 20
    s["stoch_gt80"] = st > 80
    s["vol_spike_up"] = (vv > 2.0 * vavg) & (r > 0)
    s["vol_spike_down"] = (vv > 2.0 * vavg) & (r < 0)
    pt = cn.prior_trend(c, 5)
    s["bullish_engulfing"] = cn.bullish_engulfing(o, h, l, c) & (pt.shift(1) < 0)
    s["bearish_engulfing"] = cn.bearish_engulfing(o, h, l, c) & (pt.shift(1) > 0)
    s["hammer"] = cn.hammer_shape(o, h, l, c) & (pt < 0)
    s["shooting_star"] = cn.shooting_star_shape(o, h, l, c) & (pt > 0)
    s["shock_up_5d"] = z1.rolling(5).max() >= 3.0
    s["shock_down_5d"] = z1.rolling(5).min() <= -3.0
    s["surge_5d"] = ret5 >= 3.0
    s["crash_5d"] = ret5 <= -3.0
    s["drawdown_40"] = c <= 0.6 * c.rolling(252).max()
    s["gap_up_2s"] = gap >= 2.0
    s["gap_down_2s"] = gap <= -2.0
    return s.fillna(False).astype(bool)
