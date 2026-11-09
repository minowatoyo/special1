"""ローソク足パターンの参考実装（説明用・しきい値はすべて引数）。

注意:
  * 判定規則は本資料集の定義（01_techniques/03_candlesticks.md）を単純化したもの。
    TA-Lib の CDL* 関数は「直近の平均的な実体・影の長さ」に対する相対判定を使うため、
    結果は一致しない（一致を主張しない）。
  * 各関数の戻り値は「パターンが完成した足」で True になる bool の Series。未来は参照しない。
  * 反転パターンは先行トレンド（prior_trend）と組み合わせて使う。 例:
        bull = bullish_engulfing(o, h, l, c) & (prior_trend(c, 5) < 0)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "features", "prior_trend", "doji", "marubozu", "hammer_shape", "shooting_star_shape",
    "bullish_engulfing", "bearish_engulfing", "bullish_harami", "bearish_harami",
    "piercing_line", "dark_cloud_cover", "morning_star", "evening_star",
    "three_white_soldiers", "three_black_crows",
]


def features(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    """ローソク足の基本量。body=|C-O|、range=H-L、upper/lower=上下ヒゲ、*_ratio=range に対する比。"""
    body = (close - open_).abs()
    rng = high - low
    upper = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower = pd.concat([open_, close], axis=1).min(axis=1) - low
    safe = rng.where(rng > 0)
    return pd.DataFrame({
        "body": body, "range": rng, "upper": upper, "lower": lower,
        "body_ratio": body / safe, "upper_ratio": upper / safe, "lower_ratio": lower / safe,
        "direction": np.sign(close - open_),
    })


def prior_trend(close: pd.Series, n: int = 5) -> pd.Series:
    """先行トレンドの符号: sign(前日終値 - n+1 本前の終値)。+1 上昇、-1 下降、0 横ばい。
    複数足パターンでは、パターンの最初の足より前で測るよう shift を追加すること。
    """
    return np.sign(close.shift(1) - close.shift(1 + n))


def _b(s: pd.Series) -> pd.Series:
    return s.fillna(False).astype(bool)


def doji(open_, high, low, close, max_body_ratio: float = 0.1) -> pd.Series:
    """十字線: 実体がレンジの max_body_ratio 以下。"""
    f = features(open_, high, low, close)
    return _b(f["body_ratio"] <= max_body_ratio)


def marubozu(open_, high, low, close, min_body_ratio: float = 0.9) -> pd.Series:
    """丸坊主（ほぼヒゲなし）: 実体がレンジの min_body_ratio 以上。"""
    f = features(open_, high, low, close)
    return _b(f["body_ratio"] >= min_body_ratio)


def hammer_shape(open_, high, low, close, shadow_to_body: float = 2.0,
                 max_upper_ratio: float = 0.1, min_lower_ratio: float = 0.5) -> pd.Series:
    """ハンマー／首吊りの形（下ヒゲが実体の shadow_to_body 倍以上でレンジの半分以上、上ヒゲ僅少）。
    下降後ならハンマー、上昇後なら首吊り線。形だけで文脈は判定しない。
    """
    f = features(open_, high, low, close)
    return _b((f["lower"] >= shadow_to_body * f["body"]) & (f["lower_ratio"] >= min_lower_ratio)
              & (f["upper_ratio"] <= max_upper_ratio))


def shooting_star_shape(open_, high, low, close, shadow_to_body: float = 2.0,
                        max_lower_ratio: float = 0.1, min_upper_ratio: float = 0.5) -> pd.Series:
    """流れ星／逆ハンマーの形（上ヒゲが長く下ヒゲ僅少）。上昇後なら流れ星、下降後なら逆ハンマー。"""
    f = features(open_, high, low, close)
    return _b((f["upper"] >= shadow_to_body * f["body"]) & (f["upper_ratio"] >= min_upper_ratio)
              & (f["lower_ratio"] <= max_lower_ratio))


def bullish_engulfing(open_, high, low, close) -> pd.Series:
    """陽線の包み線: 前日が陰線、当日が陽線で、当日の実体が前日の実体を包む。"""
    po, pc = open_.shift(1), close.shift(1)
    return _b((pc < po) & (close > open_) & (open_ <= pc) & (close >= po) & ((open_ < pc) | (close > po)))


def bearish_engulfing(open_, high, low, close) -> pd.Series:
    """陰線の包み線（弱気の包み足）。"""
    po, pc = open_.shift(1), close.shift(1)
    return _b((pc > po) & (close < open_) & (open_ >= pc) & (close <= po) & ((open_ > pc) | (close < po)))


def bullish_harami(open_, high, low, close, min_prev_body_ratio: float = 0.5) -> pd.Series:
    """陽のはらみ線: 前日が長い陰線、当日の小さな陽線の実体が前日の実体の内側。"""
    f = features(open_, high, low, close)
    po, pc = open_.shift(1), close.shift(1)
    inside = (open_ >= pc) & (close <= po) & (f["body"] < (po - pc).abs())
    return _b((pc < po) & (f["body_ratio"].shift(1) >= min_prev_body_ratio) & (close > open_) & inside)


def bearish_harami(open_, high, low, close, min_prev_body_ratio: float = 0.5) -> pd.Series:
    """陰のはらみ線。"""
    f = features(open_, high, low, close)
    po, pc = open_.shift(1), close.shift(1)
    inside = (open_ <= pc) & (close >= po) & (f["body"] < (pc - po).abs())
    return _b((pc > po) & (f["body_ratio"].shift(1) >= min_prev_body_ratio) & (close < open_) & inside)


def piercing_line(open_, high, low, close, min_prev_body_ratio: float = 0.5,
                  open_below_prev_low: bool = False) -> pd.Series:
    """切り込み線: 前日が長い陰線、当日は前日終値より下で始まり、前日の実体の中心より上で引ける（始値超えはしない）。
    open_below_prev_low=True なら始値が前日安値を下回ることを要求（より厳格な欧米流）。
    """
    f = features(open_, high, low, close)
    po, pc = open_.shift(1), close.shift(1)
    start = (open_ < low.shift(1)) if open_below_prev_low else (open_ < pc)
    return _b((pc < po) & (f["body_ratio"].shift(1) >= min_prev_body_ratio) & (close > open_)
              & start & (close > (po + pc) / 2.0) & (close < po))


def dark_cloud_cover(open_, high, low, close, min_prev_body_ratio: float = 0.5,
                     open_above_prev_high: bool = False) -> pd.Series:
    """かぶせ線: 前日が長い陽線、当日は前日終値より上で始まり、前日の実体の中心より下で引ける。"""
    f = features(open_, high, low, close)
    po, pc = open_.shift(1), close.shift(1)
    start = (open_ > high.shift(1)) if open_above_prev_high else (open_ > pc)
    return _b((pc > po) & (f["body_ratio"].shift(1) >= min_prev_body_ratio) & (close < open_)
              & start & (close < (po + pc) / 2.0) & (close > po))


def morning_star(open_, high, low, close, min_long_body_ratio: float = 0.5,
                 max_star_body_ratio: float = 0.3) -> pd.Series:
    """明けの明星: ①長い陰線 ②実体が小さく、実体が①の実体より下（窓）③陽線で①の実体の中心を上回って引ける。"""
    f = features(open_, high, low, close)
    o1, c1 = open_.shift(2), close.shift(2)
    o2, c2 = open_.shift(1), close.shift(1)
    first = (c1 < o1) & (f["body_ratio"].shift(2) >= min_long_body_ratio)
    star = (f["body_ratio"].shift(1) <= max_star_body_ratio) & (pd.concat([o2, c2], axis=1).max(axis=1) < c1)
    third = (close > open_) & (close > (o1 + c1) / 2.0)
    return _b(first & star & third)


def evening_star(open_, high, low, close, min_long_body_ratio: float = 0.5,
                 max_star_body_ratio: float = 0.3) -> pd.Series:
    """宵の明星: ①長い陽線 ②実体が小さく、実体が①の実体より上（窓）③陰線で①の実体の中心を下回って引ける。"""
    f = features(open_, high, low, close)
    o1, c1 = open_.shift(2), close.shift(2)
    o2, c2 = open_.shift(1), close.shift(1)
    first = (c1 > o1) & (f["body_ratio"].shift(2) >= min_long_body_ratio)
    star = (f["body_ratio"].shift(1) <= max_star_body_ratio) & (pd.concat([o2, c2], axis=1).min(axis=1) > c1)
    third = (close < open_) & (close < (o1 + c1) / 2.0)
    return _b(first & star & third)


def three_white_soldiers(open_, high, low, close, min_body_ratio: float = 0.5,
                         max_upper_ratio: float = 0.2) -> pd.Series:
    """赤三兵（三兵）: 3本連続の陽線。終値は切り上がり、各始値は前の実体の内側、上ヒゲは短い。"""
    f = features(open_, high, low, close)
    ok = pd.Series(True, index=close.index)
    for k in (0, 1, 2):
        ok &= (close.shift(k) > open_.shift(k)) & (f["body_ratio"].shift(k) >= min_body_ratio) \
              & (f["upper_ratio"].shift(k) <= max_upper_ratio)
    for k in (0, 1):
        ok &= (close.shift(k) > close.shift(k + 1)) & (open_.shift(k) > open_.shift(k + 1)) \
              & (open_.shift(k) < close.shift(k + 1))
    return _b(ok)


def three_black_crows(open_, high, low, close, min_body_ratio: float = 0.5,
                      max_lower_ratio: float = 0.2) -> pd.Series:
    """黒三兵（三羽烏）: 3本連続の陰線。終値は切り下がり、各始値は前の実体の内側、下ヒゲは短い。"""
    f = features(open_, high, low, close)
    ok = pd.Series(True, index=close.index)
    for k in (0, 1, 2):
        ok &= (close.shift(k) < open_.shift(k)) & (f["body_ratio"].shift(k) >= min_body_ratio) \
              & (f["lower_ratio"].shift(k) <= max_lower_ratio)
    for k in (0, 1):
        ok &= (close.shift(k) < close.shift(k + 1)) & (open_.shift(k) < open_.shift(k + 1)) \
              & (open_.shift(k) > close.shift(k + 1))
    return _b(ok)
