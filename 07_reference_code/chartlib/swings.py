"""スイング（転換点）検出の参考実装。

チャートパターン（ダブルトップ、ヘッド＆ショルダーズ等）を機械的に扱う前提となる「高値・安値の確定」を、
先読みなしで行う。重要な性質: 転換点は「確定した足」より前の足にあるので、
確定足（confirmed_pos）より前にその転換点を使うと先読みになる。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["swing_points", "zigzag"]

_COLS = ["pos", "time", "kind", "price", "confirmed_pos", "confirmed_time"]


def _frame(rows, index) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["pos", "kind", "price", "confirmed_pos"])
    if df.empty:
        return pd.DataFrame(columns=_COLS)
    df["time"] = index[df["pos"].to_numpy()]
    df["confirmed_time"] = index[df["confirmed_pos"].to_numpy()]
    return df[_COLS]


def swing_points(high: pd.Series, low: pd.Series, left: int = 2, right: int = 2) -> pd.DataFrame:
    """フラクタル型スイング。
    スイング高値: 高値[i] が 左 left 本の高値より厳密に高く、右 right 本の高値以上。
    スイング安値: 安値[i] が 左 left 本の安値より厳密に低く、右 right 本の安値以下。
    確定は i + right 本目（右側の本数が揃うまで分からない）。 confirmed_pos がその位置。
    """
    h, l = high.to_numpy(dtype=float), low.to_numpy(dtype=float)
    n = len(h)
    rows = []
    for i in range(left, n - right):
        if h[i] > h[i - left:i].max() and h[i] >= h[i + 1:i + right + 1].max():
            rows.append((i, "H", h[i], i + right))
        if l[i] < l[i - left:i].min() and l[i] <= l[i + 1:i + right + 1].min():
            rows.append((i, "L", l[i], i + right))
    rows.sort(key=lambda r: (r[0], r[1]))
    return _frame(rows, high.index)


def zigzag(high: pd.Series, low: pd.Series, threshold) -> pd.DataFrame:
    """ジグザグ（しきい値型）。直近の極値から threshold（割合。例 0.05 = 5%、または足ごとの Series）
    以上逆行した足で、その極値が転換点として確定する。確定前の最新の極値は返さない。
    threshold に ATR 倍率/終値 などの Series を渡せば、ボラティリティ適応型になる。
    同じ足で「新高値の更新」と「反転条件の成立」が同時に起きた場合は、足内の順序が不明なので反転させない。
    """
    h, l = high.to_numpy(dtype=float), low.to_numpy(dtype=float)
    n = len(h)
    if isinstance(threshold, pd.Series):
        thr = threshold.to_numpy(dtype=float)
    else:
        thr = np.full(n, float(threshold))
    rows = []
    direction = 0
    hi_pos, hi = 0, h[0]
    lo_pos, lo = 0, l[0]
    for i in range(1, n):
        t = thr[i]
        if np.isnan(t):
            continue
        if direction == 0:
            if h[i] > hi:
                hi_pos, hi = i, h[i]
            if l[i] < lo:
                lo_pos, lo = i, l[i]
            up_ok = lo_pos < i and h[i] >= lo * (1.0 + t)
            dn_ok = hi_pos < i and l[i] <= hi * (1.0 - t)
            if up_ok and dn_ok:
                up_ok, dn_ok = (lo_pos > hi_pos), (lo_pos <= hi_pos)
            if up_ok:
                rows.append((lo_pos, "L", lo, i))
                direction, hi_pos, hi = 1, i, h[i]
            elif dn_ok:
                rows.append((hi_pos, "H", hi, i))
                direction, lo_pos, lo = -1, i, l[i]
        elif direction == 1:
            if h[i] > hi:
                hi_pos, hi = i, h[i]
            elif l[i] <= hi * (1.0 - t):
                rows.append((hi_pos, "H", hi, i))
                direction, lo_pos, lo = -1, i, l[i]
        else:
            if l[i] < lo:
                lo_pos, lo = i, l[i]
            elif h[i] >= lo * (1.0 + t):
                rows.append((lo_pos, "L", lo, i))
                direction, hi_pos, hi = 1, i, h[i]
    return _frame(rows, high.index)
