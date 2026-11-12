"""日足 CSV の読み込み・検査・分割調整。

対応する形式（列名は大文字小文字・前後の空白を無視）:
  * Stooq:  Date,Open,High,Low,Close,Volume
  * Yahoo:  Date,Open,High,Low,Close,Adj Close,Volume
  * 日本語: 日付,始値,高値,安値,終値,出来高
区切りはカンマ・タブ・セミコロン、文字コードは UTF-8（BOM 可）と CP932 を試す。
日付は昇順に並べ直し、重複日は最後の行を残す。

検査の考え方: 予測の前に「データそのものの誤り」を見つける。特に、分割が未調整の系列は
ボラティリティ推定を壊すので、東証の値幅制限では起こりえない日次変化（±31% 超）を拾って候補を示す。
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["load_ohlcv", "validate_ohlcv", "suggest_split_factor", "adjust_splits", "COLUMNS"]

COLUMNS = ["open", "high", "low", "close", "volume"]

_ALIASES = {
    "date": ["date", "日付", "年月日", "time", "timestamp", "<date>", "data", "日時", "datetime"],
    "open": ["open", "始値", "<open>", "otwarcie"],
    "high": ["high", "高値", "<high>", "najwyzszy"],
    "low": ["low", "安値", "<low>", "najnizszy"],
    "close": ["close", "終値", "<close>", "zamkniecie"],
    "adj_close": ["adj close", "adjclose", "adj_close", "調整後終値", "終値調整", "終値調整値", "調整後終値*"],
    "volume": ["volume", "出来高", "<vol>", "vol", "wolumen", "売買高"],
}

# 東証の制限値幅（基準値段 500 円以上では最大でも 30%）を超える日次変化は、分割未調整かデータ誤りを疑う。
IMPOSSIBLE_DAILY_MOVE = 0.31
_SPLIT_FACTORS = [1.5, 2.0, 3.0, 4.0, 5.0, 10.0, 20.0, 25.0, 50.0, 100.0, 0.5, 0.2, 0.1]


def _read_text(path: Path, encoding: str | None) -> str:
    raw = Path(path).read_bytes()
    for enc in ([encoding] if encoding else []) + ["utf-8-sig", "cp932", "latin-1"]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"文字コードを判定できない: {path}")


def _sniff_delimiter(text: str) -> str:
    head = "\n".join(text.splitlines()[:5])
    counts = {d: head.count(d) for d in [",", "\t", ";"]}
    return max(counts, key=counts.get)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _parse_dates(s: pd.Series) -> pd.DatetimeIndex:
    t = s.astype(str).str.strip()
    t = t.str.replace(r"(\d{4})年(\d{1,2})月(\d{1,2})日", r"\1-\2-\3", regex=True)
    if t.str.fullmatch(r"\d{8}").all():
        return pd.DatetimeIndex(pd.to_datetime(t, format="%Y%m%d"))
    t = t.str.replace("/", "-", regex=False).str.replace(".", "-", regex=False)
    return pd.DatetimeIndex(pd.to_datetime(t, errors="coerce"))


def _to_float(s: pd.Series) -> pd.Series:
    if s.dtype.kind in "fiu":
        return s.astype(float)
    t = s.astype(str).str.replace(",", "", regex=False).str.strip()
    t = t.replace({"-": np.nan, "--": np.nan, "": np.nan, "nan": np.nan, "None": np.nan})
    return pd.to_numeric(t, errors="coerce")


def load_ohlcv(path, encoding: str | None = None) -> pd.DataFrame:
    """CSV を読み、index=日付（昇順）、列 open/high/low/close/volume（float）の DataFrame を返す。

    df.attrs に読み込みの記録（元の列名、重複日の数、adj_close の有無など）を残す。
    出来高の列がなければ NaN の列を作る（出来高を使う特徴量は計算されない）。
    """
    text = _read_text(Path(path), encoding)
    if "<html" in text[:2000].lower() or "<!doctype" in text[:2000].lower():
        raise ValueError("CSV ではなく HTML が保存されている（ブラウザ検証ページなど）。CSV を取り直すこと。")
    sep = _sniff_delimiter(text)
    raw = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, skip_blank_lines=True)
    raw = raw.dropna(how="all")
    colmap: dict[str, str] = {}
    for col in raw.columns:
        key = _norm(col)
        for std, names in _ALIASES.items():
            if key in names and std not in colmap:
                colmap[std] = col
    missing = [c for c in ["date", "open", "high", "low", "close"] if c not in colmap]
    if missing:
        raise ValueError(f"必要な列が見つからない: {missing}（列名: {list(raw.columns)}）")
    df = pd.DataFrame({c: _to_float(raw[colmap[c]]) for c in ["open", "high", "low", "close"]})
    df["volume"] = _to_float(raw[colmap["volume"]]) if "volume" in colmap else np.nan
    if "adj_close" in colmap:
        df["adj_close"] = _to_float(raw[colmap["adj_close"]])
    idx = _parse_dates(raw[colmap["date"]])
    bad_dates = int(pd.isna(idx).sum())
    df.index = idx
    df = df[~pd.isna(df.index)]
    n_before = len(df)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "date"
    df.attrs.update({
        "source": str(path), "columns_in_file": list(raw.columns), "delimiter": sep,
        "duplicate_dates_removed": n_before - len(df), "unparsed_dates": bad_dates,
        "has_volume": "volume" in colmap, "has_adj_close": "adj_close" in colmap,
    })
    return df


def suggest_split_factor(ratio: float, tol: float = 0.15) -> float | None:
    """前日比（当日終値/前日終値）から、未調整の分割・併合の倍率（1 株 → f 株）を推定する。合わなければ None。"""
    if not (ratio > 0) or not math.isfinite(ratio):
        return None
    best, err = None, tol
    for f in _SPLIT_FACTORS:
        e = abs(math.log(ratio * f))
        if e < err:
            best, err = f, e
    return best


def adjust_splits(df: pd.DataFrame, splits: dict) -> pd.DataFrame:
    """未調整の分割を調整する。splits = {権利落ち日: 倍率 f（1 株が f 株になる）}。
    権利落ち日より前の価格を f で割り、出来高に f を掛ける。
    """
    out = df.copy()
    for day, f in sorted(splits.items(), key=lambda kv: pd.Timestamp(kv[0])):
        before = out.index < pd.Timestamp(day)
        for c in ["open", "high", "low", "close"] + (["adj_close"] if "adj_close" in out.columns else []):
            out.loc[before, c] = out.loc[before, c] / float(f)
        out.loc[before, "volume"] = out.loc[before, "volume"] * float(f)
    out.attrs = dict(df.attrs)
    out.attrs["splits_applied"] = {str(pd.Timestamp(k).date()): float(v) for k, v in splits.items()}
    return out


def validate_ohlcv(df: pd.DataFrame, today=None) -> dict:
    """データの検査。errors（予測に進めない）、warnings（注意）、info、suspect_splits を返す。"""
    rep: dict = {"errors": [], "warnings": [], "info": [], "suspect_splits": []}
    n = len(df)
    if n == 0:
        rep["errors"].append("行がない")
        return rep
    rep["info"].append(f"行数 {n}、期間 {df.index[0].date()}〜{df.index[-1].date()}")
    a = df.attrs
    if a.get("duplicate_dates_removed"):
        rep["warnings"].append(f"重複した日付 {a['duplicate_dates_removed']} 行を除いた（後の行を採用）")
    if a.get("unparsed_dates"):
        rep["warnings"].append(f"日付として読めない行 {a['unparsed_dates']} 行を除いた")
    px = df[["open", "high", "low", "close"]]
    nan_rows = int(px.isna().any(axis=1).sum())
    if nan_rows:
        rep["warnings"].append(f"四本値に欠損のある行 {nan_rows} 行")
    if (px <= 0).any().any():
        rep["errors"].append("0 以下の価格がある")
    tol = 1e-9
    hi_bad = int((df["high"] < px[["open", "close"]].max(axis=1) - tol).sum())
    lo_bad = int((df["low"] > px[["open", "close"]].min(axis=1) + tol).sum())
    if hi_bad or lo_bad:
        rep["warnings"].append(f"高値・安値が始値／終値と矛盾する行: 高値 {hi_bad} 行、安値 {lo_bad} 行"
                               "（調整後終値と未調整の高安が混在している可能性）")
    if "volume" in df and a.get("has_volume", True):
        zero_vol = int(((df["volume"] == 0) | df["volume"].isna()).sum())
        if zero_vol:
            rep["warnings"].append(f"出来高が 0 または欠損の日 {zero_vol} 日")
    else:
        rep["warnings"].append("出来高の列がない（出来高を使う特徴量とシグナルは計算しない）")
    wk = int((df.index.day_of_week >= 5).sum())
    if wk:
        rep["warnings"].append(f"土日の日付 {wk} 行（日付のずれの可能性）")
    gap_days = pd.Series(df.index[1:] - df.index[:-1], index=df.index[1:]).dt.days
    long_gaps = gap_days[gap_days > 10]
    if len(long_gaps):
        ex = "、".join(f"{d.date()}（{int(g)}日）" for d, g in long_gaps.head(5).items())
        rep["warnings"].append(f"10 日を超える空白が {len(long_gaps)} か所: {ex}")
    if n < 1500:
        rep["warnings"].append(f"履歴が短い（{n} 行）。検証に使える独立な標本が少なく、結論の不確かさが大きい")
    ratio = (df["close"] / df["close"].shift(1)).dropna()
    big = ratio[(ratio - 1.0).abs() > IMPOSSIBLE_DAILY_MOVE]
    for day, rt in big.items():
        f = suggest_split_factor(float(rt))
        rep["suspect_splits"].append({"date": str(day.date()), "ratio": float(rt), "factor": f})
    if len(big):
        rep["warnings"].append(
            f"値幅制限では起こりにくい日次変化（±{int(IMPOSSIBLE_DAILY_MOVE * 100)}% 超）が {len(big)} 日ある。"
            "分割の未調整かデータ誤りを確認すること")
    same = (df["close"].diff() == 0)
    run = same.groupby((~same).cumsum()).cumsum()
    if int(run.max() or 0) >= 5:
        rep["warnings"].append(f"終値が {int(run.max()) + 1} 日続けて同じ箇所がある（売買停止か欠損の埋め合わせの可能性）")
    if today is not None:
        lag = (pd.Timestamp(today).normalize() - df.index[-1].normalize()).days
        rep["info"].append(f"最終日は {df.index[-1].date()}（基準日 {pd.Timestamp(today).date()} の {lag} 日前）")
        if lag > 7:
            rep["warnings"].append(f"データが古い（最終日が {lag} 日前）")
    return rep
