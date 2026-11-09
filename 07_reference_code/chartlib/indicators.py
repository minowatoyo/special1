"""主要テクニカル指標の参考実装（pandas / numpy）。

目的:
  * 文書（01_techniques/）に書かれた数式を「動くコード」で確認する。
  * TA-Lib と数値照合し、平滑化・初期値・ルックバックの流儀を明確にする。
本番の売買システム用ではない。入力は同一 index の pandas Series。
出力は入力と同じ index に揃え、計算に必要な期間（ルックバック）は NaN とする。
未来のデータは一切使わない（tests/test_causality.py で確認）。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

__all__ = [
    "sma", "ema", "wma", "vwma", "dema", "tema", "hma", "kama", "wilder_smooth",
    "rsi", "stochastic", "stochastic_jp", "macd", "cci", "williams_r", "roc", "momentum",
    "ultimate_oscillator", "mfi", "trix",
    "bollinger", "true_range", "atr", "natr", "dmi_adx", "parabolic_sar",
    "donchian", "keltner", "aroon",
    "obv", "ad_line", "chaikin_money_flow", "vwap", "force_index",
    "ichimoku", "heikin_ashi", "pivot_points", "gaps",
]


# --------------------------------------------------------------------------
# 内部ヘルパー
# --------------------------------------------------------------------------
def _first_valid(a: np.ndarray) -> int:
    nz = np.flatnonzero(~np.isnan(a))
    return int(nz[0]) if len(nz) else -1


def _like(x: pd.Series, values: np.ndarray) -> pd.Series:
    return pd.Series(values, index=x.index, name=x.name)


# --------------------------------------------------------------------------
# 移動平均
# --------------------------------------------------------------------------
def sma(x: pd.Series, n: int) -> pd.Series:
    """単純移動平均。最初の n-1 本は NaN。"""
    return x.rolling(n).mean()


def ema(x: pd.Series, n: int, seed: str = "sma") -> pd.Series:
    """指数移動平均。alpha = 2 / (n + 1)。

    seed="sma"  : 最初の n 個の単純平均で初期化（TA-Lib / 多くの教科書の流儀）。
                  最初の有効値は先頭から数えて n 本目。
    seed="first": 最初の値で初期化（pandas ewm(adjust=False) の流儀）。
    先頭が NaN の系列（EMA の EMA など）は、最初の有効値から数える。
    """
    v = x.to_numpy(dtype=float)
    out = np.full(v.shape, np.nan)
    s = _first_valid(v)
    if s < 0:
        return _like(x, out)
    a = 2.0 / (n + 1.0)
    if seed == "sma":
        start = s + n - 1
        if start >= len(v):
            return _like(x, out)
        out[start] = v[s:start + 1].mean()
    elif seed == "first":
        start = s
        out[start] = v[s]
    else:
        raise ValueError("seed must be 'sma' or 'first'")
    for i in range(start + 1, len(v)):
        out[i] = a * v[i] + (1.0 - a) * out[i - 1]
    return _like(x, out)


def wilder_smooth(x: pd.Series, n: int) -> pd.Series:
    """ワイルダー平滑（RMA / SMMA）。最初の n 個の単純平均で初期化し、
    以後 out[t] = (out[t-1] * (n-1) + x[t]) / n。 EMA(alpha=1/n) に相当。
    RSI・ATR・ADX が使う。先頭が NaN の系列は最初の有効値から数える。
    """
    v = x.to_numpy(dtype=float)
    out = np.full(v.shape, np.nan)
    s = _first_valid(v)
    if s < 0:
        return _like(x, out)
    start = s + n - 1
    if start >= len(v):
        return _like(x, out)
    out[start] = v[s:start + 1].mean()
    for i in range(start + 1, len(v)):
        out[i] = (out[i - 1] * (n - 1) + v[i]) / n
    return _like(x, out)


def wma(x: pd.Series, n: int) -> pd.Series:
    """加重移動平均。重みは 1..n（最新が n）。"""
    w = np.arange(1, n + 1, dtype=float)
    return x.rolling(n).apply(lambda a: float(np.dot(a, w) / w.sum()), raw=True)


def vwma(close: pd.Series, volume: pd.Series, n: int = 20) -> pd.Series:
    """出来高加重移動平均 = Σ(終値×出来高, n) / Σ(出来高, n)。"""
    return (close * volume).rolling(n).sum() / volume.rolling(n).sum()


def dema(x: pd.Series, n: int) -> pd.Series:
    """DEMA = 2*EMA - EMA(EMA)。"""
    e1 = ema(x, n)
    return 2.0 * e1 - ema(e1, n)


def tema(x: pd.Series, n: int) -> pd.Series:
    """TEMA = 3*EMA1 - 3*EMA2 + EMA3。"""
    e1 = ema(x, n)
    e2 = ema(e1, n)
    e3 = ema(e2, n)
    return 3.0 * e1 - 3.0 * e2 + e3


def hma(x: pd.Series, n: int) -> pd.Series:
    """ハル移動平均 = WMA( 2*WMA(n/2) - WMA(n), sqrt(n) )。
    n/2 と sqrt(n) はともに切り捨て（TA-Lib 0.8.3 の HMA と一致。sqrt を四捨五入する実装もあり、
    n=14, 21 などでは結果が変わる。tests/test_vs_talib.py で確認）。
    """
    half = max(1, n // 2)
    root = max(1, int(math.sqrt(n)))
    return wma(2.0 * wma(x, half) - wma(x, n), root)


def kama(x: pd.Series, n: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    """カウフマン適応型移動平均。ER = |変化| / 値動きの合計、
    SC = (ER*(2/(fast+1) - 2/(slow+1)) + 2/(slow+1))^2、KAMA += SC*(価格 - KAMA)。
    初期値は index n-1 の価格（TA-Lib と同じ。出力は index n から）。
    """
    v = x.to_numpy(dtype=float)
    out = np.full(v.shape, np.nan)
    if len(v) <= n:
        return _like(x, out)
    fsc, ssc = 2.0 / (fast + 1.0), 2.0 / (slow + 1.0)
    prev = v[n - 1]
    for i in range(n, len(v)):
        change = abs(v[i] - v[i - n])
        vol = np.abs(np.diff(v[i - n:i + 1])).sum()
        er = change / vol if vol != 0 else 0.0
        sc = (er * (fsc - ssc) + ssc) ** 2
        prev = prev + sc * (v[i] - prev)
        out[i] = prev
    return _like(x, out)


# --------------------------------------------------------------------------
# モメンタム系
# --------------------------------------------------------------------------
def rsi(close: pd.Series, n: int = 14, method: str = "wilder") -> pd.Series:
    """RSI = 100 * 平均上昇幅 / (平均上昇幅 + 平均下落幅)。

    method="wilder": ワイルダー平滑（原典。TA-Lib・多くの海外ツール）。
    method="cutler": 単純移動平均（Cutler の RSI。証券会社によってはこちら）。
    全期間が横ばい（分母 0）のときは未定義として NaN を返す。
    """
    d = close.diff()
    gain = d.clip(lower=0.0)
    loss = (-d).clip(lower=0.0)
    if method == "wilder":
        ag, al = wilder_smooth(gain, n), wilder_smooth(loss, n)
    elif method == "cutler":
        ag, al = gain.rolling(n).mean(), loss.rolling(n).mean()
    else:
        raise ValueError("method must be 'wilder' or 'cutler'")
    tot = ag + al
    return 100.0 * ag / tot.where(tot != 0)


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, k_smooth: int = 3, d_period: int = 3) -> pd.DataFrame:
    """ストキャスティクス（欧米式）。
    fast_k = 100*(C - 期間最安値)/(期間最高値 - 期間最安値)
    slow_k = SMA(fast_k, k_smooth)          （欧米の Slow %K。k_smooth=d_period=3 なら Fast %D と同じ）
    slow_d = SMA(slow_k, d_period)          （欧米の Slow %D）
    注意: 日本の証券会社に多い定義（野村證券など）の %D は「分子・分母を別々に m 日合計してから割る」形で、
    欧米の Slow %K（%K の単純平均）とは近いが別物。日本式は stochastic_jp() を使う。
    """
    hh = high.rolling(k_period).max()
    ll = low.rolling(k_period).min()
    rng = (hh - ll).where((hh - ll) != 0)
    fast_k = 100.0 * (close - ll) / rng
    slow_k = fast_k.rolling(k_smooth).mean()
    slow_d = slow_k.rolling(d_period).mean()
    return pd.DataFrame({"fast_k": fast_k, "slow_k": slow_k, "slow_d": slow_d})


def stochastic_jp(high: pd.Series, low: pd.Series, close: pd.Series,
                  n: int = 9, m: int = 3, y: int = 3) -> pd.DataFrame:
    """日本の証券会社で多いストキャスティクス（野村證券の用語集などの定義。n=5 や 9、m=y=3 が多い）。
    %K = 100*(C - n日最安値)/(n日最高値 - n日最安値)
    %D = 100*Σ_m(C - n日最安値) / Σ_m(n日最高値 - n日最安値)   ← 分子・分母を m 日ずつ合計してから割る
    SD = SMA(%D, y)                                             （スロー%D）
    レンジ（分母）が日々変わるため、欧米の Slow %K = SMA(%K, m) とは一致しない。
    """
    hh, ll = high.rolling(n).max(), low.rolling(n).min()
    num, den = close - ll, hh - ll
    k = 100.0 * num / den.where(den != 0)
    den_sum = den.rolling(m).sum()
    d = 100.0 * num.rolling(m).sum() / den_sum.where(den_sum != 0)
    return pd.DataFrame({"k": k, "d": d, "sd": d.rolling(y).mean()})


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD = EMA(fast) - EMA(slow)、シグナル = EMA(MACD, signal)、ヒストグラム = MACD - シグナル。
    EMA は SMA で初期化（seed="sma"）。
    """
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def cci(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 20) -> pd.Series:
    """CCI = (TP - SMA(TP)) / (0.015 * 平均偏差)。TP=(H+L+C)/3、平均偏差=|TP-SMA(TP)|の単純平均。"""
    tp = (high + low + close) / 3.0
    ma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda a: float(np.abs(a - a.mean()).mean()), raw=True)
    return (tp - ma) / (0.015 * md)


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """ウィリアムズ%R = -100 * (期間最高値 - C) / (期間最高値 - 期間最安値)。範囲 -100〜0。"""
    hh, ll = high.rolling(n).max(), low.rolling(n).min()
    return -100.0 * (hh - close) / (hh - ll).where((hh - ll) != 0)


def roc(close: pd.Series, n: int = 10) -> pd.Series:
    """変化率 ROC = (C / C[n本前] - 1) * 100。"""
    return (close / close.shift(n) - 1.0) * 100.0


def momentum(close: pd.Series, n: int = 10) -> pd.Series:
    """モメンタム = C - C[n本前]。"""
    return close - close.shift(n)


def ultimate_oscillator(high: pd.Series, low: pd.Series, close: pd.Series,
                        p1: int = 7, p2: int = 14, p3: int = 28) -> pd.Series:
    """アルティメット・オシレーター。BP=C-min(L,前C)、TR=max(H,前C)-min(L,前C)、
    avg_k = ΣBP/ΣTR (k=p1,p2,p3)、UO = 100*(4*avg1 + 2*avg2 + avg3)/7。
    """
    pc = close.shift(1)
    lo = pd.concat([low, pc], axis=1).min(axis=1, skipna=False)
    hi = pd.concat([high, pc], axis=1).max(axis=1, skipna=False)
    bp, tr = close - lo, hi - lo
    avg = lambda k: bp.rolling(k).sum() / tr.rolling(k).sum()  # noqa: E731
    return 100.0 * (4.0 * avg(p1) + 2.0 * avg(p2) + avg(p3)) / 7.0


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, n: int = 14) -> pd.Series:
    """マネーフロー・インデックス。TP=(H+L+C)/3、資金フロー=TP*出来高。
    TP が前日より上なら正、下なら負のフロー。MFI = 100*Σ正/(Σ正+Σ負)（n本の単純和）。
    """
    tp = (high + low + close) / 3.0
    flow = tp * volume
    d = tp.diff()
    pos = flow.where(d > 0, 0.0).where(d.notna())
    neg = flow.where(d < 0, 0.0).where(d.notna())
    ps, ns = pos.rolling(n).sum(), neg.rolling(n).sum()
    return 100.0 * ps / (ps + ns).where((ps + ns) != 0)


def trix(close: pd.Series, n: int = 30) -> pd.Series:
    """TRIX = 三重平滑 EMA の1本前比変化率（%）。"""
    e3 = ema(ema(ema(close, n), n), n)
    return (e3 / e3.shift(1) - 1.0) * 100.0


# --------------------------------------------------------------------------
# ボラティリティ・トレンド強度
# --------------------------------------------------------------------------
def bollinger(close: pd.Series, n: int = 20, k: float = 2.0, ddof: int = 0) -> pd.DataFrame:
    """ボリンジャーバンド。中心=SMA(n)、上下=中心±k*標準偏差。
    標準偏差は母集団（ddof=0）が原典・TA-Lib の流儀。ddof=1（標本）にする実装もある。
    percent_b=(C-下)/(上-下)、bandwidth=(上-下)/中心。
    """
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=ddof)
    up, lo = mid + k * sd, mid - k * sd
    return pd.DataFrame({
        "upper": up, "middle": mid, "lower": lo,
        "percent_b": (close - lo) / (up - lo).where((up - lo) != 0),
        "bandwidth": (up - lo) / mid,
    })


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """TR = max(H-L, |H-前C|, |L-前C|)。最初の1本は前日終値がないため NaN。"""
    pc = close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1, skipna=False)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """ATR = TR のワイルダー平滑（最初の n 個の TR の単純平均で初期化）。"""
    return wilder_smooth(true_range(high, low, close), n)


def natr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """正規化 ATR = 100 * ATR / 終値。"""
    return 100.0 * atr(high, low, close, n) / close


def _wilder_sums(x: pd.Series, n: int, variant: str) -> pd.Series:
    """ワイルダーの「合計型」平滑: S[t] = S[t-1] - S[t-1]/n + x[t]。初期値の取り方に2流儀ある。
    variant="wilder": 最初の n 個の合計を S とする（ワイルダー原典・教科書。SMA 初期化の RMA と比が同じ）。
    variant="talib" : 最初の n-1 個の合計 A から S = A - A/n + x[n 個目] とする（TA-Lib の実装）。
    どちらも以後は同じ漸化式なので、差は指数的に減衰する（係数 (1-1/n)^k）。
    """
    v = x.to_numpy(dtype=float)
    out = np.full(v.shape, np.nan)
    s = _first_valid(v)
    if s < 0:
        return _like(x, out)
    start = s + n - 1
    if start >= len(v):
        return _like(x, out)
    if variant == "wilder":
        out[start] = v[s:start + 1].sum()
    elif variant == "talib":
        a = v[s:start].sum()
        out[start] = a - a / n + v[start]
    else:
        raise ValueError("variant must be 'wilder' or 'talib'")
    for i in range(start + 1, len(v)):
        out[i] = out[i - 1] - out[i - 1] / n + v[i]
    return _like(x, out)


def dmi_adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14,
            variant: str = "wilder") -> pd.DataFrame:
    """DMI / ADX（ワイルダー）。
    +DM = H-前H（>(前L-L) かつ >0 のとき、そうでなければ0）、-DM = 前L-L（>(H-前H) かつ >0 のとき）。
    平滑(TR)・平滑(+DM)・平滑(-DM) は合計型のワイルダー平滑（初期化は variant、_wilder_sums 参照）。
    +DI = 100*平滑(+DM)/平滑(TR)、-DI も同様。DX = 100*|+DI - -DI|/(+DI + -DI)。
    ADX = DX のワイルダー平滑（最初の n 個の DX の単純平均で初期化。出力は index 2n-1 から）。
    """
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0).where(up.notna())
    minus_dm = down.where((down > up) & (down > 0), 0.0).where(down.notna())
    tr = true_range(high, low, close)
    s_tr = _wilder_sums(tr, n, variant)
    s_p, s_m = _wilder_sums(plus_dm, n, variant), _wilder_sums(minus_dm, n, variant)
    plus_di, minus_di = 100.0 * s_p / s_tr, 100.0 * s_m / s_tr
    den = (plus_di + minus_di).where((plus_di + minus_di) != 0)
    dx = 100.0 * (plus_di - minus_di).abs() / den
    return pd.DataFrame({"plus_di": plus_di, "minus_di": minus_di, "dx": dx, "adx": wilder_smooth(dx, n)})


def parabolic_sar(high: pd.Series, low: pd.Series, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    """パラボリック SAR（ワイルダー）。TA-Lib SAR と同じ初期化を移植:
    最初の足の -DM > 0 なら下降（ショート）、そうでなければ上昇（ロング）で開始。
    初期 SAR はロングなら前の足の安値、ショートなら前の足の高値。EP は当足の高値/安値。
    AF は EP 更新ごとに af_step 加算（上限 af_max）、反転時に af_step へ戻す。
    """
    h, l = high.to_numpy(dtype=float), low.to_numpy(dtype=float)
    n = len(h)
    out = np.full(n, np.nan)
    if n < 2:
        return _like(high, out)
    diff_p, diff_m = h[1] - h[0], l[0] - l[1]
    minus_dm = diff_m if (diff_m > 0 and diff_p < diff_m) else 0.0
    is_long = not (minus_dm > 0)
    af = af_step
    if is_long:
        ep, sar = h[1], l[0]
    else:
        ep, sar = l[1], h[0]
    new_low, new_high = l[1], h[1]
    for t in range(1, n):
        prev_low, prev_high = new_low, new_high
        new_low, new_high = l[t], h[t]
        if is_long:
            if new_low <= sar:                      # 反転: ショートへ
                is_long = False
                sar = max(ep, prev_high, new_high)
                out[t] = sar
                af, ep = af_step, new_low
                sar = sar + af * (ep - sar)
                sar = max(sar, prev_high, new_high)
            else:
                out[t] = sar
                if new_high > ep:
                    ep = new_high
                    af = min(af + af_step, af_max)
                sar = sar + af * (ep - sar)
                sar = min(sar, prev_low, new_low)
        else:
            if new_high >= sar:                     # 反転: ロングへ
                is_long = True
                sar = min(ep, prev_low, new_low)
                out[t] = sar
                af, ep = af_step, new_high
                sar = sar + af * (ep - sar)
                sar = min(sar, prev_low, new_low)
            else:
                out[t] = sar
                if new_low < ep:
                    ep = new_low
                    af = min(af + af_step, af_max)
                sar = sar + af * (ep - sar)
                sar = max(sar, prev_high, new_high)
    return _like(high, out)


def donchian(high: pd.Series, low: pd.Series, n: int = 20, exclude_current: bool = False) -> pd.DataFrame:
    """ドンチャン・チャネル。上=n本の最高値、下=n本の最安値、中=その平均。
    exclude_current=True なら「当足を含まない過去 n 本」（タートルのブレイクアウト判定に使う形）。
    """
    up, lo = high.rolling(n).max(), low.rolling(n).min()
    if exclude_current:
        up, lo = up.shift(1), lo.shift(1)
    return pd.DataFrame({"upper": up, "middle": (up + lo) / 2.0, "lower": lo})


def keltner(high: pd.Series, low: pd.Series, close: pd.Series,
            n_ema: int = 20, n_atr: int = 10, mult: float = 2.0) -> pd.DataFrame:
    """ケルトナー・チャネル（現代的な形）: 中心=EMA(終値, n_ema)、上下=中心±mult*ATR(n_atr)。
    原典（Chester Keltner）は典型価格の10日SMA±10日平均レンジで、流派差がある。
    """
    mid = ema(close, n_ema)
    a = atr(high, low, close, n_atr)
    return pd.DataFrame({"upper": mid + mult * a, "middle": mid, "lower": mid - mult * a})


def aroon(high: pd.Series, low: pd.Series, n: int = 14) -> pd.DataFrame:
    """アルーン。直近 n+1 本の窓で、最高値/最安値からの経過本数 k に対し 100*(n-k)/n（TA-Lib 流）。"""
    up = high.rolling(n + 1).apply(lambda a: 100.0 * float(np.argmax(a)) / n, raw=True)
    dn = low.rolling(n + 1).apply(lambda a: 100.0 * float(np.argmin(a)) / n, raw=True)
    return pd.DataFrame({"aroon_up": up, "aroon_down": dn, "oscillator": up - dn})


# --------------------------------------------------------------------------
# 出来高系
# --------------------------------------------------------------------------
def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """OBV。最初の値は出来高、以後 終値が上がれば +出来高、下がれば -出来高、同値なら変化なし。"""
    sign = np.sign(close.diff()).fillna(0.0)
    sign.iloc[0] = 1.0  # 最初の足は出来高をそのまま採用（TA-Lib と同じ）
    return (sign * volume).cumsum()


def _clv(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    rng = high - low
    clv = ((close - low) - (high - close)) / rng.where(rng != 0)
    return clv.fillna(0.0)


def ad_line(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """チャイキンの A/D ライン = Σ[ CLV × 出来高 ]、CLV=((C-L)-(H-C))/(H-L)（H=L のとき 0）。"""
    return (_clv(high, low, close) * volume).cumsum()


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
                       n: int = 20) -> pd.Series:
    """CMF = Σ(CLV×出来高, n) / Σ(出来高, n)。"""
    return (_clv(high, low, close) * volume).rolling(n).sum() / volume.rolling(n).sum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
         anchor: pd.Series | None = None) -> pd.Series:
    """VWAP = Σ(典型価格×出来高)/Σ出来高。anchor（例: 日付）が変わるたびにリセット。
    None なら先頭からの累積（アンカード VWAP の起点を先頭にした形）。
    """
    tp = (high + low + close) / 3.0
    pv = tp * volume
    if anchor is None:
        return pv.cumsum() / volume.cumsum()
    g = anchor.to_numpy()
    return pv.groupby(g).cumsum() / volume.groupby(g).cumsum()


def force_index(close: pd.Series, volume: pd.Series, n: int = 13) -> pd.Series:
    """エルダーのフォース・インデックス = EMA( (C - 前C) × 出来高, n )。"""
    return ema((close.diff() * volume), n)


# --------------------------------------------------------------------------
# 一目均衡表・平均足・ピボット・窓
# --------------------------------------------------------------------------
def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan: int = 9, kijun: int = 26, senkou_b: int = 52,
             displacement: int = 26) -> pd.DataFrame:
    """一目均衡表。
    転換線 = (n=tenkan の最高値 + 最安値)/2、基準線 = (n=kijun の最高値 + 最安値)/2
    先行スパン1 = (転換線 + 基準線)/2 を displacement 本「先」に描く
    先行スパン2 = (n=senkou_b の最高値 + 最安値)/2 を displacement 本「先」に描く
    遅行スパン = 当日終値を displacement 本「前」に描く

    返す senkou_a / senkou_b は「その日に描かれている雲」（= displacement 本前に計算した値）で、
    先読みを含まない。 chikou は「その日の位置に描かれる遅行スパン」= 将来の終値であり、
    シグナル判定に使うと先読みになる（判定には close と close.shift(displacement) を比べる）。
    未来側の雲（最新日より先）は返さない。

    シフト本数の流儀差: displacement=26 は MT4/MT5 流（計算日の26本先／26本前に描く）。
    日本の数え方（「本日を含めて26日」＝計算日の25本先／25本前、楽天証券の説明など）や、
    TradingView（offset=displacement-1）に合わせるには displacement=25 を指定する。
    詳細と出典は ../02_japan/02_ichimoku_kinko_hyo.md の 3.1 節。
    """
    tk = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2.0
    kj = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2.0
    sa_raw = (tk + kj) / 2.0
    sb_raw = (high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2.0
    return pd.DataFrame({
        "tenkan": tk, "kijun": kj,
        "senkou_a": sa_raw.shift(displacement),
        "senkou_b": sb_raw.shift(displacement),
        "chikou": close.shift(-displacement),
    })


def heikin_ashi(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    """平均足。HA終値=(O+H+L+C)/4、HA始値=(前HA始値+前HA終値)/2（初回は(O+C)/2）、
    HA高値=max(H, HA始値, HA終値)、HA安値=min(L, HA始値, HA終値)。
    """
    ha_c = (open_ + high + low + close) / 4.0
    o = np.empty(len(ha_c))
    c = ha_c.to_numpy(dtype=float)
    o[0] = (open_.iloc[0] + close.iloc[0]) / 2.0
    for i in range(1, len(o)):
        o[i] = (o[i - 1] + c[i - 1]) / 2.0
    ha_o = pd.Series(o, index=ha_c.index)
    return pd.DataFrame({
        "open": ha_o, "high": pd.concat([high, ha_o, ha_c], axis=1).max(axis=1),
        "low": pd.concat([low, ha_o, ha_c], axis=1).min(axis=1), "close": ha_c,
    })


def pivot_points(high: pd.Series, low: pd.Series, close: pd.Series, kind: str = "classic") -> pd.DataFrame:
    """ピボットポイント。前の足（日/週/月）の H/L/C から「次の足」の水準を出すので shift(1) 済みで返す。
    kind: classic / fibonacci / woodie / camarilla（定義には流派差がある）。
    """
    h, l, c = high.shift(1), low.shift(1), close.shift(1)
    r = h - l
    if kind == "classic":
        p = (h + l + c) / 3.0
        return pd.DataFrame({
            "p": p, "r1": 2 * p - l, "s1": 2 * p - h, "r2": p + r, "s2": p - r,
            "r3": h + 2 * (p - l), "s3": l - 2 * (h - p)})
    if kind == "fibonacci":
        p = (h + l + c) / 3.0
        return pd.DataFrame({
            "p": p, "r1": p + 0.382 * r, "r2": p + 0.618 * r, "r3": p + r,
            "s1": p - 0.382 * r, "s2": p - 0.618 * r, "s3": p - r})
    if kind == "woodie":
        p = (h + l + 2 * c) / 4.0
        return pd.DataFrame({"p": p, "r1": 2 * p - l, "s1": 2 * p - h, "r2": p + r, "s2": p - r})
    if kind == "camarilla":
        return pd.DataFrame({
            "r1": c + r * 1.1 / 12, "r2": c + r * 1.1 / 6, "r3": c + r * 1.1 / 4, "r4": c + r * 1.1 / 2,
            "s1": c - r * 1.1 / 12, "s2": c - r * 1.1 / 6, "s3": c - r * 1.1 / 4, "s4": c - r * 1.1 / 2})
    raise ValueError("kind must be classic / fibonacci / woodie / camarilla")


def gaps(high: pd.Series, low: pd.Series) -> pd.DataFrame:
    """窓（ギャップ）。窓上げ: 当日安値 > 前日高値、窓下げ: 当日高値 < 前日安値。
    gap_size は窓の幅（上は正、下は負、なければ0）。
    """
    up = low > high.shift(1)
    down = high < low.shift(1)
    size = (low - high.shift(1)).where(up, 0.0) + (high - low.shift(1)).where(down, 0.0)
    size = size.where(high.shift(1).notna())
    return pd.DataFrame({"gap_up": up, "gap_down": down, "gap_size": size})
