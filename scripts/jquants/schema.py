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
    "sector_indices": ["date", "index_code", "open", "high", "low", "close"],
}
MARGIN_MAP = {"PubDate": "pub_date", "Date": "date", "Code": "code", "IssType": "iss_type", "ShrtVol": "short_vol", "LongVol": "long_vol",
              "ShrtNegVol": "short_neg_vol", "LongNegVol": "long_neg_vol", "ShrtStdVol": "short_std_vol", "LongStdVol": "long_std_vol",
              "ShrtVal": "short_val", "LongVal": "long_val", "ShrtNegVal": "short_neg_val", "LongNegVal": "long_neg_val",
              "ShrtStdVal": "short_std_val", "LongStdVal": "long_std_val"}
SHORT_RATIO_MAP = {"Date": "date", "S33": "s33", "SellExShortVa": "sell_ex_short_va", "ShrtWithResVa": "short_with_restriction_va",
                   "ShrtNoResVa": "short_no_restriction_va"}

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


def _next_day(dates: pd.Series, trading_days) -> pd.Series:
    days = pd.DatetimeIndex(trading_days)
    return pd.Series([days[days > d][0] if (days > d).any() else pd.NaT for d in dates], index=dates.index)


def normalize_margin(rows: list[dict], trading_days) -> pd.DataFrame:
    """信用取引週末残高（週次・銘柄別）。usable_from ＝ 公表日の次の営業日の引け後（公表日の当日の使用は避ける）。"""
    df = _rename(rows, MARGIN_MAP)
    if df.empty:
        return df
    df["code"] = df["code"].astype(str)
    for c in ("pub_date", "date"):
        df[c] = pd.to_datetime(df[c])
    num = [c for c in df.columns if c not in ("pub_date", "date", "code", "iss_type")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    df["usable_from"] = _next_day(df["pub_date"], trading_days)
    return df.drop_duplicates(["code", "date", "pub_date"], keep="last").sort_values(["code", "date"]).reset_index(drop=True)


def normalize_short_ratio(rows: list[dict], trading_days) -> pd.DataFrame:
    """業種別空売り比率（日次）。usable_from ＝ 翌営業日（公表時刻が不明なので保守的に）。"""
    df = _rename(rows, SHORT_RATIO_MAP)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    num = [c for c in df.columns if c not in ("date", "s33")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    tot = df["sell_ex_short_va"] + df["short_with_restriction_va"] + df["short_no_restriction_va"]
    df["short_ratio"] = (df["short_with_restriction_va"] + df["short_no_restriction_va"]) / tot.replace(0, np.nan)
    df["usable_from"] = _next_day(df["date"], trading_days)
    return df.drop_duplicates(["s33", "date"], keep="last").sort_values(["s33", "date"]).reset_index(drop=True)


def normalize_investor_types(rows: list[dict], trading_days) -> pd.DataFrame:
    """投資部門別売買状況（週次）。列は元のまま、日付と usable_from（公表日の次の営業日）を付ける。"""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ("PubDate", "StDate", "EnDate"):
        df[c] = pd.to_datetime(df[c])
    df["usable_from"] = _next_day(df["PubDate"], trading_days)
    return df.drop_duplicates(["Section", "StDate", "PubDate"], keep="last").sort_values(["Section", "StDate"]).reset_index(drop=True)


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


def adjustment_pairs(prices: pd.DataFrame) -> pd.DataFrame:
    """連続する営業日の組ごとの突合結果。営業日は、取得済みの全日付の和集合（カレンダー）で数え、暦日の間隔が 7 日を超える組
    （取得していない日に分割があり得る）は含めない。(AdjC/C)_t が (AdjC/C)_{t+1} × AdjFactor_{t+1} に一致するはず。
    列: code, date, close, adj_close, f_next, err_abs（調整後終値での差。円）, err_rel。"""
    cal = {d: i for i, d in enumerate(sorted(prices["date"].unique()))}
    parts = []
    for code, g in prices.sort_values("date").groupby("code"):
        g = g.dropna(subset=["close", "adj_close"])
        g = g[g["close"] > 0]
        if len(g) < 2:
            continue
        idx = g["date"].map(cal).to_numpy()
        r = (g["adj_close"] / g["close"]).to_numpy()
        f = g["adj_factor"].to_numpy()
        gap_days = (g["date"].iloc[1:].to_numpy() - g["date"].iloc[:-1].to_numpy()).astype("timedelta64[D]").astype(int)
        ok = ((idx[1:] - idx[:-1]) == 1) & (gap_days <= MAX_GAP_DAYS)
        exp = r[1:] * f[1:]
        c = g["close"].to_numpy()[:-1]
        err_abs = np.abs(g["adj_close"].to_numpy()[:-1] - c * exp)
        parts.append(pd.DataFrame({"code": code, "date": g["date"].iloc[:-1].to_numpy(), "close": c,
                                   "adj_close": g["adj_close"].to_numpy()[:-1], "f_next": f[1:], "err_abs": err_abs,
                                   "err_rel": np.abs(r[:-1] - exp) / np.maximum(1.0, np.abs(r[:-1]))})[ok])
    cols = ["code", "date", "close", "adj_close", "f_next", "err_abs", "err_rel"]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


ADJ_ROUND_YEN = 0.1           # 調整後価格は 0.1 円単位に丸められている（W3 の実測: 不一致 455,521 件すべてが差 0.1 円以内）
ADJ_SLACK = 1e-4


def reconcile_adjustment(prices: pd.DataFrame, tol: float = 1e-6, abs_tol_yen: float = ADJ_ROUND_YEN) -> pd.DataFrame:
    """調整係数の突合の不一致（空なら全部一致）。相対誤差が tol を超え、かつ調整後終値の差が abs_tol_yen（丸めの単位）を
    超える組だけを不一致とする。丸めの範囲を超える差（分割の取りこぼしなど）は検出する。検出の分解能は abs_tol_yen 円。"""
    pr = adjustment_pairs(prices)
    if pr.empty:
        return pd.DataFrame(columns=["code", "date", "ratio", "expected"])
    bad = pr[(pr["err_rel"] > tol) & (pr["err_abs"] > abs_tol_yen + ADJ_SLACK)]
    return bad.assign(ratio=bad["adj_close"] / bad["close"], expected=bad["adj_close"] / bad["close"] * (1 + bad["err_rel"]))[["code", "date", "ratio", "expected"]]


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
    p["turnover"] = p["turnover"].fillna(0.0)                  # 売買のなかった日は売買代金 0（欠損のまま平均に入れない）
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
