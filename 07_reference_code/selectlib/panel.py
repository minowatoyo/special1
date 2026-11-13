"""日付×銘柄のパネル（J-Quants 加工後データから）。リバランス日・ラベル・対象銘柄のマスク。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
import schema  # noqa: E402

HOLD = 21
MIN_HISTORY = 500


class Panel:
    """dates: TOPIX の営業日。各行列は [日付, 銘柄]。未調整始値 raw_open が約定価格、adj_* は分割調整済み。"""

    def __init__(self, dates, codes, arrays: dict, topix: pd.DataFrame):
        self.dates = pd.DatetimeIndex(dates)
        self.codes = list(codes)
        self.__dict__.update(arrays)
        self.topix = topix.reindex(self.dates)

    @classmethod
    def from_frames(cls, prices: pd.DataFrame, flags: pd.DataFrame, topix: pd.DataFrame):
        topix = topix.sort_values("date").set_index("date")
        dates = topix.index
        p = prices.merge(flags[["code", "date", "no_trade"]], on=["code", "date"], how="left")
        codes = sorted(p["code"].unique())
        ci = {c: i for i, c in enumerate(codes)}
        di = {d: i for i, d in enumerate(dates)}
        p = p[p["date"].isin(di)]
        r = p["date"].map(di).to_numpy()
        c = p["code"].map(ci).to_numpy()
        def mat(col, fill=np.nan, dtype=float):
            m = np.full((len(dates), len(codes)), fill, dtype=dtype)
            m[r, c] = p[col].to_numpy(dtype=dtype)
            return m
        arrays = {"raw_open": mat("open"), "raw_close": mat("close"), "adj_open": mat("adj_open"), "adj_high": mat("adj_high"),
                  "adj_low": mat("adj_low"), "adj_close": mat("adj_close"), "turnover": mat("turnover")}
        for col in ("limit_up", "limit_down"):
            m = np.zeros((len(dates), len(codes)), dtype=bool)
            m[r, c] = (p[col].astype(str) == "1").to_numpy()
            arrays[col] = m
        return cls(dates, codes, arrays, topix[["open", "high", "low", "close"]])

    def rebalance_idx(self, start: int = 0) -> list:
        """T の位置: start から 21 営業日ごと。売却（T+22）の日付がない T は、売買側で除かれる。"""
        return list(range(start, len(self.dates) - HOLD - 1, HOLD))

    def eligible(self, intervals: pd.DataFrame, markets, t_idx: list, min_history: int = MIN_HISTORY) -> np.ndarray:
        """リバランス日ごとの対象銘柄のマスク [len(t_idx), 銘柄]。schema.universe と同じ条件（内国普通株・市場区分・
        売買代金 60 営業日平均 ≥ 5 億円・履歴）。市場区分と普通株の判定は別々に適用する。"""
        to = pd.DataFrame(self.turnover).fillna(0.0)
        va60 = to.rolling(schema.VA_WINDOW, min_periods=schema.VA_WINDOW).mean().to_numpy()
        hist = np.cumsum(np.isfinite(self.adj_close), axis=0)
        iv = intervals.copy()
        iv["ok"] = (schema.is_domestic_common(iv["prod_cat"], iv["code"]) & schema.market_in(iv["market"], markets)).to_numpy()
        ci = {c: i for i, c in enumerate(self.codes)}
        iv["col"] = iv["code"].map(ci)
        iv = iv[iv["col"].notna()].astype({"col": int})
        td = pd.DataFrame({"date": np.repeat(self.dates[t_idx].values, len(self.codes)), "col": np.tile(np.arange(len(self.codes)), len(t_idx)),
                           "ti": np.repeat(np.arange(len(t_idx)), len(self.codes))}).sort_values("date")
        j = pd.merge_asof(td, iv.sort_values("valid_from")[["col", "valid_from", "valid_to", "ok"]], left_on="date", right_on="valid_from",
                          by="col", direction="backward")
        listed = ((j["valid_to"] >= j["date"]) & j["ok"].fillna(False).astype(bool)).to_numpy()
        mask = np.zeros((len(t_idx), len(self.codes)), dtype=bool)
        ti, col = j["ti"].to_numpy(), j["col"].to_numpy()
        T = np.array(t_idx)[ti]
        good = listed & (va60[T, col] >= schema.VA_MIN) & (hist[T, col] >= max(min_history, schema.VA_WINDOW))
        mask[ti[good], col[good]] = True
        return mask

    def labels(self, t_idx: list) -> tuple:
        """ラベル（超過）と、株式の素のリターン・TOPIX リターン。買い T+1 始値 → 売り T+22 始値（調整後）。"""
        raw, top = [], []
        for T in t_idx:
            b, s = T + 1, T + 1 + HOLD
            raw.append(self.adj_open[s] / self.adj_open[b] - 1.0)
            top.append(self.topix["open"].iloc[s] / self.topix["open"].iloc[b] - 1.0)
        raw, top = np.array(raw), np.array(top)
        return raw - top[:, None], raw, top
