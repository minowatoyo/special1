"""J-Quants 加工後データ（data/jquants/processed）の読み取り専用アダプタ。

モデル側（forecastlib）と J-Quants のデータ置き場の唯一の接点。書き込まず、生データには触れない。
返す表は forecastlib の日足形式（日付昇順の index、列 open/high/low/close/volume）。
データの置き場は引数 root か環境変数 JQUANTS_DATA_DIR（既定 data/jquants）。解約時は scripts/jquants/purge.sh --yes で全消去。
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

__all__ = ["processed_dir", "load_ohlcv", "load_topix", "load_flags", "universe_on", "fins_usable"]


def processed_dir(root: str | Path | None = None) -> Path:
    return Path(root or os.environ.get("JQUANTS_DATA_DIR", "data/jquants")) / "processed"


def _read(name: str, root) -> pd.DataFrame:
    p = processed_dir(root) / f"{name}.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} がありません（scripts/jquants/build_processed.py を実行してください）")
    return pd.read_parquet(p)


def _code5(code: str | int) -> str:
    c = str(code)
    return c if len(c) == 5 else c + "0"


def load_ohlcv(code: str | int, root=None, adjusted: bool = True, drop_no_trade: bool = True) -> pd.DataFrame:
    """1 銘柄の日足。adjusted=True は分割調整済み（AdjO/H/L/C/Vo）、False は未調整。売買のなかった日は既定で除く。"""
    c = _code5(code)
    p = _read("prices_daily", root)
    p = p[p["code"] == c].sort_values("date")
    if drop_no_trade:
        f = _read("quality_flags", root)
        bad = set(f.loc[(f["code"] == c) & f["no_trade"], "date"])
        p = p[~p["date"].isin(bad)]
    cols = (["adj_open", "adj_high", "adj_low", "adj_close", "adj_volume"] if adjusted
            else ["open", "high", "low", "close", "volume"])
    out = p.set_index("date")[cols]
    out.columns = ["open", "high", "low", "close", "volume"]
    out.index.name = "date"
    return out


def load_topix(root=None) -> pd.DataFrame:
    t = _read("topix_daily", root).sort_values("date").set_index("date")
    return t[["open", "high", "low", "close"]]


def load_flags(code: str | int, root=None) -> pd.DataFrame:
    """銘柄の品質フラグ（OHLC の矛盾・価格異常・売買なし・±31% 超の跳び）。"""
    f = _read("quality_flags", root)
    return f[f["code"] == _code5(code)].sort_values("date").set_index("date").drop(columns="code")


def universe_on(date, root=None) -> list[str]:
    """date の引け後に使える対象銘柄（プライム＋スタンダードの普通株、60 営業日平均売買代金 ≥ 5 億円）。"""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
    import schema
    u = schema.universe(_read("prices_daily", root), _read("listed_master", root))
    return sorted(u.loc[u["date"] == pd.Timestamp(date), "code"])


def fins_usable(code: str | int, date, root=None) -> pd.DataFrame:
    """date の引け後のシグナルに使ってよい財務サマリー（usable_from <= date）。未来の開示は返さない。"""
    f = _read("fins_summary", root)
    return f[(f["Code"] == _code5(code)) & (f["usable_from"] <= pd.Timestamp(date))].sort_values(["DiscDate"])
