"""J-Quants 生データ → 加工後テーブルのスキーマと正規化（純関数。実データを含まない）。

加工後は data/jquants/processed/<テーブル>.parquet に置く。モデル側は forecastlib.jquants_adapter 経由でだけ読む。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 本物の応答の列名 → 加工後の列名
PRICES_MAP = {"Date": "date", "Code": "code", "O": "open", "H": "high", "L": "low", "C": "close",
              "UL": "limit_up", "LL": "limit_down", "Vo": "volume", "Va": "turnover", "AdjFactor": "adj_factor",
              "AdjO": "adj_open", "AdjH": "adj_high", "AdjL": "adj_low", "AdjC": "adj_close", "AdjVo": "adj_volume",
              "MktCap": "mktcap_mjpy", "ExRT": "ex_rights"}
MASTER_MAP = {"Date": "asof", "Code": "code", "CoName": "name", "CoNameEn": "name_en", "S17": "s17", "S17Nm": "s17_name",
              "S33": "s33", "S33Nm": "s33_name", "ScaleCat": "scale_cat", "Mkt": "market", "MktNm": "market_name",
              "Mrgn": "margin_class", "MrgnNm": "margin_name", "ProdCat": "prod_cat"}
INDEX_MAP = {"Date": "date", "Code": "index_code", "O": "open", "H": "high", "L": "low", "C": "close"}
CALENDAR_MAP = {"Date": "ann_date", "Code": "code", "CoName": "name", "FY": "fiscal_year", "SectorNm": "sector",
                "FQ": "fiscal_quarter", "Section": "section"}

# 値を保存するだけで、モデル入力にはしない（Standard 固有。事前登録した除去実験を通すまで使わない）
EMPTY_SLOTS = {
    "margin_interest": ["date", "code", "long_balance", "short_balance"],
    "short_ratio": ["date", "s33", "short_ratio"],
    "investor_types": ["start", "end", "section", "investor", "buy", "sell"],
    "sector_indices": ["date", "index_code", "open", "high", "low", "close"],
}

PRIME, STANDARD = "0111", "0112"          # 2022-04-04 以降の市場区分
OLD_FIRST, OLD_SECOND, OLD_JASDAQ_STD = "0101", "0102", "0106"   # 旧東証一部・二部・JASDAQ スタンダード（2022-04-01 まで。案。未確定）
POST_2022 = (PRIME, STANDARD)
PRE_2022_PROPOSAL = (OLD_FIRST, OLD_SECOND, OLD_JASDAQ_STD)
DOMESTIC_STOCK = "011"                    # 公式仕様: 内国株券（優先株式等を含む）
CUTOFF = "15:30"
VA_MIN = 5e8                  # 60 営業日平均売買代金 ≥ 5 億円
VA_WINDOW = 60
IMPOSSIBLE_MOVE = 0.31
MAX_GAP_DAYS = 7              # 連続営業日とみなす暦日の間隔の上限（年末年始・連休を含む）


def _rename(rows: list[dict], mp: dict) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=list(mp.values()))
    return df[[c for c in mp if c in df.columns]].rename(columns=mp)


def normalize_prices(rows: list[dict]) -> pd.DataFrame:
    """日足。未調整 OHLC・調整係数・調整後 OHLC・出来高・売買代金を別の列で保持する。"""
    df = _rename(rows, PRICES_MAP)
    df["date"] = pd.to_datetime(df["date"])
    num = [c for c in df.columns if c not in ("date", "code", "limit_up", "limit_down", "ex_rights")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    return df.drop_duplicates(["code", "date"], keep="last").sort_values(["code", "date"]).reset_index(drop=True)


def is_domestic_common(prod_cat, code) -> pd.Series:
    """内国普通株の判定（市場区分の判定とは別）。ProdCat=="011"（内国株券。優先株式等を含む）かつ 5 文字コードで末尾が "0"
    （公式 FAQ: 末尾 0 が普通株）。欠損・不正なコード、ETF・REIT（別の ProdCat）、末尾が 0 でない優先株等は除く。コードは文字列のまま扱う。"""
    pc = pd.Series(prod_cat).astype("string")
    cd = pd.Series(code, index=pc.index).astype("string")
    return ((pc == DOMESTIC_STOCK) & (cd.str.len() == 5) & (cd.str.endswith("0")) & cd.str.fullmatch(r"[0-9A-Z]{5}")).fillna(False).astype(bool)


def market_in(market, allowed) -> pd.Series:
    """市場区分の判定（普通株の判定とは別）。allowed は市場区分コードの集合。"""
    return pd.Series(market).astype("string").isin(list(allowed)).fillna(False).astype(bool)


def normalize_master(rows: list[dict]) -> pd.DataFrame:
    df = _rename(rows, MASTER_MAP)
    df["code"] = df["code"].astype(str)
    df["asof"] = pd.to_datetime(df["asof"])
    return df.drop_duplicates(["asof", "code"], keep="last").sort_values(["asof", "code"]).reset_index(drop=True)


def normalize_index(rows: list[dict], code: str = "TOPIX") -> pd.DataFrame:
    df = _rename(rows, INDEX_MAP)
    if "index_code" not in df.columns:
        df["index_code"] = code
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop_duplicates(["index_code", "date"], keep="last").sort_values(["index_code", "date"]).reset_index(drop=True)


def normalize_calendar(rows: list[dict], fetched: str) -> pd.DataFrame:
    """決算発表予定。予定は改訂されるので、取得日（version）付きで追記する。"""
    df = _rename(rows, CALENDAR_MAP)
    df["ann_date"] = pd.to_datetime(df["ann_date"])
    df["version"] = pd.to_datetime(fetched)
    return df


def normalize_fins(rows: list[dict], trading_days) -> pd.DataFrame:
    """財務サマリー。開示日時と、モデルが使える最初の日（usable_from）を付ける。"""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["DiscDate"] = pd.to_datetime(df["DiscDate"])
    df["usable_from"] = [usable_from(d, t, trading_days) for d, t in zip(df["DiscDate"], df.get("DiscTime", [None] * len(df)))]
    return df.sort_values(["Code", "DiscDate", "DiscNo"] if "DiscNo" in df.columns else ["Code", "DiscDate"]).reset_index(drop=True)


def usable_from(disc_date, disc_time, trading_days) -> pd.Timestamp:
    """開示情報を、引け後シグナルに使える最初の営業日（その日の引け後に使える）。

    15:30 より前の開示は、その日が営業日ならその日の引け後から。15:30 以降・時刻不明・非営業日の開示は、翌営業日の引け後から。
    （Standard の約定は、さらにその翌営業日の始値になる。）
    """
    days = pd.DatetimeIndex(trading_days)
    d = pd.Timestamp(disc_date).normalize()
    known = disc_time is not None and not (isinstance(disc_time, float) and np.isnan(disc_time)) and str(disc_time).strip() != ""
    before = known and str(disc_time).strip()[:5].zfill(5) < CUTOFF
    if before and d in days:
        return d
    nxt = days[days > d]
    return nxt[0] if len(nxt) else pd.NaT


def reconcile_adjustment(prices: pd.DataFrame, tol: float = 1e-6) -> pd.DataFrame:
    """調整係数の突合: 連続する営業日の組で、(AdjC/C)_t ÷ (AdjC/C)_{t+1} が AdjFactor_{t+1} に一致するか。
    営業日は、取得済みの全日付の和集合（カレンダー）で数え、暦日の間隔が 7 日を超える組（取得していない日に分割があり得る）は検査しない。
    銘柄ごとの不一致日を返す（空なら全部一致）。窓の端の影響を受けない局所的な検査。"""
    cal = {d: i for i, d in enumerate(sorted(prices["date"].unique()))}
    out = []
    for code, g in prices.sort_values("date").groupby("code"):
        g = g.dropna(subset=["close", "adj_close"])
        g = g[g["close"] > 0]
        if len(g) < 2:
            continue
        idx = g["date"].map(cal).to_numpy()
        r = (g["adj_close"] / g["close"]).to_numpy()
        f = g["adj_factor"].to_numpy()
        exp = r[1:] * f[1:]            # r_t = r_{t+1} × f_{t+1}
        gap_days = (g["date"].iloc[1:].to_numpy() - g["date"].iloc[:-1].to_numpy()).astype("timedelta64[D]").astype(int)
        adjacent = ((idx[1:] - idx[:-1]) == 1) & (gap_days <= MAX_GAP_DAYS)
        bad = adjacent & (np.abs(r[:-1] - exp) > tol * np.maximum(1.0, np.abs(r[:-1])))
        for i in np.where(bad)[0]:
            out.append({"code": code, "date": g["date"].iloc[i], "ratio": r[i], "expected": exp[i]})
    return pd.DataFrame(out, columns=["code", "date", "ratio", "expected"])


def quality_flags(prices: pd.DataFrame) -> pd.DataFrame:
    """原因別の隔離フラグ（通さない・代用しない）。

    ohlc_inconsistent: 高値 < max(始値,終値,安値) または 安値 > min(...)（未調整・調整後それぞれ）
    no_trade: 始値〜終値がすべて欠損で出来高なし（売買のなかった日。銘柄別の取引可能日から外す）
    nonpositive: 売買があったのに価格が 0 以下または欠損
    jump_flag: 調整後終値の日次変化が ±31% 超（調査フラグ。値幅制限の拡大などもありうる）
    """
    p = prices.sort_values(["code", "date"]).copy()
    def inc(o, h, l, c):
        hi = np.fmax.reduce([p[o], p[l], p[c]]); lo = np.fmin.reduce([p[o], p[h], p[c]])
        return ((p[h] < hi) | (p[l] > lo)).fillna(False)
    p["ohlc_inconsistent"] = inc("open", "high", "low", "close") | inc("adj_open", "adj_high", "adj_low", "adj_close")
    ohlc_null = p[["open", "high", "low", "close"]].isna().all(axis=1)
    p["no_trade"] = ohlc_null & (p["volume"].fillna(0) == 0)          # 売買のなかった日（停止など）。市場の営業日とは別に持つ
    p["nonpositive"] = ~p["no_trade"] & ~((p[["open", "high", "low", "close"]] > 0).all(axis=1))
    ret = p.groupby("code")["adj_close"].pct_change()
    gap = p.groupby("code")["date"].diff().dt.days
    p["jump_flag"] = ((ret.abs() > IMPOSSIBLE_MOVE) & (gap <= MAX_GAP_DAYS)).fillna(False)   # 取得の飛び（間が空いた組）は対象外
    return p[["code", "date", "ohlc_inconsistent", "nonpositive", "no_trade", "jump_flag"]]


MASTER_ATTRS = ["name", "s17", "s33", "scale_cat", "market", "margin_class", "prod_cat"]


def master_intervals(master_daily: pd.DataFrame, calendar) -> pd.DataFrame:
    """日次の上場銘柄表 → 銘柄ごとの有効区間（valid_from, valid_to）。属性が変わるか、営業日が欠けたら新しい区間。
    月中の新規上場・上場廃止・市場変更が区間の端に現れる。calendar は営業日（日次の取得に欠けがないかの判定に使う）。"""
    pos = {d: i for i, d in enumerate(sorted(pd.DatetimeIndex(calendar).unique()))}
    m = master_daily.copy()
    m = m[m["asof"].isin(pos)].sort_values(["code", "asof"])
    m["_i"] = m["asof"].map(pos)
    attrs = [c for c in MASTER_ATTRS if c in m.columns]
    key = m[attrs].astype("string").fillna("").agg("|".join, axis=1) if attrs else pd.Series("", index=m.index)
    m["_chg"] = (key != key.groupby(m["code"]).shift()) | (m["_i"] - m.groupby("code")["_i"].shift() != 1)
    m["_run"] = m.groupby("code")["_chg"].cumsum()
    g = m.groupby(["code", "_run"])
    out = g[attrs].first()
    out["valid_from"] = g["asof"].min()
    out["valid_to"] = g["asof"].max()
    return out.reset_index().drop(columns="_run").sort_values(["code", "valid_from"]).reset_index(drop=True)


def universe(prices: pd.DataFrame, intervals: pd.DataFrame, markets=POST_2022, min_history: int = 0) -> pd.DataFrame:
    """日付ごとの対象銘柄。フィルタは、取得とは別にここで適用する（原データは捨てない）。
    条件: その日に上場（有効区間に含まれる）／内国普通株（is_domestic_common）／市場区分が markets のいずれか（別判定）／
    売買代金 Va の 60 営業日平均 ≥ 5 億円／履歴 ≥ max(min_history, 60) 営業日。
    markets は既定で 2022-04-04 以降の区分。それ以前の母集団は PRE_2022_PROPOSAL（案。未確定）を明示して渡す。"""
    p = prices.sort_values(["code", "date"]).copy()
    p["va60"] = p.groupby("code")["turnover"].transform(lambda s: s.rolling(VA_WINDOW, min_periods=VA_WINDOW).mean())
    p["hist"] = p.groupby("code").cumcount() + 1
    iv = intervals.copy()
    iv["common"] = is_domestic_common(iv["prod_cat"], iv["code"]).to_numpy()
    iv["mkt_ok"] = market_in(iv["market"], markets).to_numpy()
    p = p.sort_values("date")
    j = pd.merge_asof(p, iv.sort_values("valid_from")[["code", "valid_from", "valid_to", "common", "mkt_ok"]],
                      left_on="date", right_on="valid_from", by="code", direction="backward")
    ok = (j["valid_to"] >= j["date"]) & j["common"].fillna(False) & j["mkt_ok"].fillna(False) \
        & (j["va60"] >= VA_MIN) & (j["hist"] >= max(min_history, VA_WINDOW))
    return j.loc[ok, ["date", "code"]].sort_values(["date", "code"]).reset_index(drop=True)


def benchmark_excess(adj_open: pd.Series, topix_open: pd.Series, t1, t22) -> float:
    """初版の超過収益: 分割調整済み始値の T+1→T+22 リターン − 同期間の TOPIX 価格リターン。"""
    return float(adj_open.loc[t22] / adj_open.loc[t1] - 1 - (topix_open.loc[t22] / topix_open.loc[t1] - 1))
