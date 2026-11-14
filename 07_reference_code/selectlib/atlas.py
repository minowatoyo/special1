"""パターン図鑑: 条件（特徴量）の組み合わせを網羅し、「どういう銘柄が、どういう状態のとき、どう動いたか」を具体的に見る。
仕様は docs/w5_protocol.md「パターン図鑑」。出力は集計のみ（個別の銘柄名は出さない）。
"""
from __future__ import annotations

import itertools
import math
import warnings

import numpy as np
import pandas as pd

from forecastlib import stats as st

from . import features as feat
from . import margin as mg_mod
from . import rules

MISSING = "なし"
MIN_PER_PERIOD = 5
MIN_OBS = 1500
MIN_PERIODS = 20
MAX_ORDER = 3
ROUND_TRIP_A = 0.003

LABELS = {
    "liquidity": ["A(5億円以上)", "B(5,000万〜5億円)", "C(5,000万円未満)"],
    "price": ["株価<300円", "300〜1,000円", "1,000〜3,000円", "3,000円以上"],
    "drawdown": ["52週高値から−10%以内", "高値から−10〜−30%", "高値から−30〜−50%", "高値から−50%超"],
    "ret21": ["21日で−15%以下", "21日で−15〜−5%", "21日で−5〜+5%", "21日で+5〜+15%", "21日で+15%超"],
    "ret126": ["126日で−25%以下", "126日で−25〜0%", "126日で0〜+25%", "126日で+25%超"],
    "vol": ["低ボラ", "中ボラ", "高ボラ"],
    "value": ["予想益利回り低", "予想益利回り中", "予想益利回り高", f"予想益利回り{MISSING}"],
    "revision": ["純利益予想を上方修正", "下方修正", "修正なし"],
    "roe": ["ROE低", "ROE中", "ROE高", f"ROE{MISSING}"],
    "margin": ["信用買い残が軽い", "買い残が中程度", "買い残が重い", f"信用残{MISSING}"],
    "trend": ["75日線の上", "75日線の下"],
    "market": ["主力市場(旧東証一部・プライム)", "中位市場(旧東証二部・スタンダード・旧JASDAQ S)", "新興市場(旧マザーズ・グロース・旧JASDAQ G)", "その他の市場"],
    "month": [f"{m}月" for m in range(1, 13)],
}
MARKET_CODE = {"0101": 0, "0111": 0, "0102": 1, "0112": 1, "0106": 1, "0104": 2, "0113": 2, "0107": 2}   # v2: 新旧をまたぐ 3 区分。それ以外は 3
SECTOR_LABEL = "業種"


def _digitize(x: np.ndarray, edges: list) -> np.ndarray:
    return np.searchsorted(np.asarray(edges), x, side="right").astype(np.int8)


def _tertile(x: np.ndarray, mask: np.ndarray, missing: bool) -> np.ndarray:
    """その日の対象銘柄の 3 分位（0 低・1 中・2 高）。欠損は 3。"""
    out = np.full(x.shape, 3 if missing else 0, dtype=np.int8)
    m = mask & np.isfinite(x)
    if m.sum() >= 30:
        q1, q2 = np.percentile(x[m], [33.3, 66.7])
        out[m] = np.where(x[m] <= q1, 0, np.where(x[m] <= q2, 1, 2))
    return out


def interval_attr(P, iv: pd.DataFrame, t_idx: list, col: str) -> np.ndarray:
    """判断日 T における、銘柄の上場銘柄表の属性（区間 valid_from ≤ T ≤ valid_to）。無ければ None。"""
    ci = {c: i for i, c in enumerate(P.codes)}
    d = iv[["code", col, "valid_from", "valid_to"]].copy()
    d["j"] = d["code"].map(ci)
    d = d.dropna(subset=["j"]).astype({"j": int})
    n_j = len(P.codes)
    td = pd.DataFrame({"date": np.repeat(P.dates[t_idx].values, n_j), "j": np.tile(np.arange(n_j), len(t_idx)), "ti": np.repeat(np.arange(len(t_idx)), n_j)}).sort_values("date")
    m = pd.merge_asof(td, d.sort_values("valid_from")[["j", col, "valid_from", "valid_to"]], left_on="date", right_on="valid_from", by="j", direction="backward")
    out = np.full((len(t_idx), n_j), None, dtype=object)
    ok = (m["valid_to"] >= m["date"]).to_numpy()
    out[m["ti"].to_numpy()[ok], m["j"].to_numpy()[ok]] = m[col].to_numpy()[ok]
    return out


def build_obs(P, elig: np.ndarray, iv: pd.DataFrame, fins: pd.DataFrame, mg: pd.DataFrame | None, t_idx: list, h: int = 21) -> dict:
    """判断日 × 銘柄の観測表（1 次元の配列にした）。条件は整数の符号。"""
    F = rules.forward_returns(P, h)
    ex = rules.executable(P)
    n_t = len(P.dates)
    t_idx = [T for T in t_idx if T + 1 + h < n_t]
    ok = elig & ex
    chart = feat.chart_features(P, t_idx)
    fins_f = feat.fins_features(P, fins, t_idx)
    c = pd.DataFrame(P.adj_close)
    sma75 = c.rolling(75, min_periods=60).mean().to_numpy()[t_idx]
    va = P.va60()[t_idx]
    price = P.raw_close[t_idx]
    marg = None
    if mg is not None and len(mg):
        mv = mg_mod.margin_values(P, mg)
        to20 = pd.DataFrame(P.turnover).fillna(0.0).rolling(20, min_periods=15).mean().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            marg = (mv["long_vol"] * P.raw_close / np.where(to20 > 0, to20, np.nan))[t_idx]
    mkt = interval_attr(P, iv, t_idx, "market")
    s17 = interval_attr(P, iv, t_idx, "s17")
    sec_codes = {s: i for i, s in enumerate(sorted({x for x in np.unique(s17[s17 != None]) if x is not None}))}  # noqa: E711
    cols = {k: [] for k in ["liquidity", "price", "drawdown", "ret21", "ret126", "vol", "value", "revision", "roe", "margin", "trend", "sector", "market", "month"]}
    y_all, per, tt = [], [], []
    for i, T in enumerate(t_idx):
        y = F[T]
        m = ok[T] & np.isfinite(y)
        if m.sum() < 50:
            continue
        y = y - y[m].mean()
        j = np.flatnonzero(m)
        cols["liquidity"].append(np.where(va[i][j] >= 5e8, 0, np.where(va[i][j] >= 5e7, 1, 2)).astype(np.int8))
        cols["price"].append(_digitize(price[i][j], [300, 1000, 3000]))
        cols["drawdown"].append(3 - _digitize(chart["near_high"][i][j] - 1, [-0.5, -0.3, -0.1]))
        cols["ret21"].append(_digitize(chart["ret21"][i][j], [-0.15, -0.05, 0.05, 0.15]))
        cols["ret126"].append(_digitize(chart["ret126"][i][j], [-0.25, 0.0, 0.25]))
        cols["vol"].append(_tertile(chart["vol60"][i], m, False)[j])
        cols["value"].append(_tertile(fins_f["earn_yield"][i], m, True)[j])
        rv = np.nan_to_num(fins_f["rev_np"][i][j])
        cols["revision"].append(np.where(rv > 0, 0, np.where(rv < 0, 1, 2)).astype(np.int8))
        cols["roe"].append(_tertile(fins_f["roe"][i], m, True)[j])
        cols["margin"].append(_tertile(marg[i], m, True)[j] if marg is not None else np.full(len(j), 3, np.int8))
        cols["trend"].append(np.where(P.adj_close[T][j] > sma75[i][j], 0, 1).astype(np.int8))
        cols["sector"].append(np.array([sec_codes.get(s17[i][jj], -1) for jj in j], dtype=np.int8))
        cols["market"].append(np.array([MARKET_CODE.get(mkt[i][jj], 3) for jj in j], dtype=np.int8))
        cols["month"].append(np.full(len(j), P.dates[T + 1].month - 1, dtype=np.int8))
        y_all.append(y[j])
        per.append(np.full(len(j), len(tt)))
        tt.append(T)
    out = {k: np.concatenate(v) for k, v in cols.items()}
    out["sector"] = np.where(out["sector"] < 0, len(sec_codes), out["sector"]).astype(np.int8)       # 業種不明は最後の番号
    out["y"], out["period"] = np.concatenate(y_all), np.concatenate(per)
    out["T"] = np.array(tt)
    out["buy_date"] = P.dates[np.array(tt) + 1]
    out["sell_date"] = P.dates[np.array(tt) + 1 + h]
    out["sector_labels"] = sorted(sec_codes, key=sec_codes.get) + ["不明"]
    return out


def sizes(obs: dict) -> dict:
    s = {k: len(v) for k, v in LABELS.items()}
    s["sector"] = len(obs["sector_labels"])
    return s


def split(obs: dict, boundary: pd.Timestamp) -> tuple:
    """観測を、発見期間（売りが境界より前）と確認期間（買いが境界以降）に分ける。またぐ観測は使わない。"""
    d = obs["sell_date"][obs["period"]] < boundary
    c = obs["buy_date"][obs["period"]] >= boundary
    return d, c


def _period_year(obs: dict) -> np.ndarray:
    return np.asarray(obs["buy_date"].year)


def mine(obs: dict, mask: np.ndarray, features: list | None = None, max_order: int = MAX_ORDER, min_obs: int = MIN_OBS, min_periods: int = MIN_PERIODS) -> list:
    """条件を 1〜max_order 個組み合わせたすべての、判断日ごとの平均超過の統計。戻り値は辞書のリスト（符号化された条件つき）。"""
    sz = sizes(obs)
    feats = features or list(sz)
    per_all = obs["period"][mask]
    uniq = np.unique(per_all)
    remap = {p: i for i, p in enumerate(uniq)}
    per = np.array([remap[p] for p in per_all])
    n_p = len(uniq)
    yr = _period_year(obs)[uniq]
    years = sorted(set(yr))
    y = obs["y"][mask]
    codes = {k: obs[k][mask].astype(np.int64) for k in feats}
    warnings.filterwarnings("ignore", message="Mean of empty slice")
    res = []
    for order in range(1, max_order + 1):
        for sub in itertools.combinations(feats, order):
            key = np.zeros(len(y), dtype=np.int64)
            mult = 1
            dims = []
            for f in sub:
                key = key + codes[f] * mult
                dims.append((f, mult, sz[f]))
                mult *= sz[f]
            n_keys = mult
            flat = key * n_p + per
            cnt = np.bincount(flat, minlength=n_keys * n_p).reshape(n_keys, n_p).astype(float)
            sm = np.bincount(flat, weights=y, minlength=n_keys * n_p).reshape(n_keys, n_p)
            valid = cnt >= MIN_PER_PERIOD
            n_valid = valid.sum(axis=1)
            tot = cnt.sum(axis=1)
            cand = np.flatnonzero((n_valid >= min_periods) & (tot >= min_obs))
            if len(cand) == 0:
                continue
            pm = np.where(valid[cand], sm[cand] / np.where(cnt[cand] > 0, cnt[cand], 1), np.nan)
            mean = np.nanmean(pm, axis=1)
            sd = np.nanstd(pm, axis=1, ddof=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                t = mean / (sd / np.sqrt(n_valid[cand]))
            ym = np.full((len(cand), len(years)), np.nan)
            for k, yv in enumerate(years):
                sel = yr == yv
                if sel.sum() >= 2:
                    with np.errstate(invalid="ignore"):
                        ym[:, k] = np.nanmean(pm[:, sel], axis=1)
            for r, kk in enumerate(cand):
                if not np.isfinite(t[r]):
                    continue
                res.append({"sub": sub, "key": int(kk), "mean": float(mean[r]), "t": float(t[r]), "obs": int(tot[kk]), "periods": int(n_valid[kk]),
                            "year_means": ym[r].copy(), "years": years, "dims": dims})
    for r in res:
        r["p"] = float(2 * st.t_sf(abs(r["t"]), r["periods"] - 1))
    return res


def describe(obs: dict, r: dict) -> str:
    parts = []
    for f, mult, size in r["dims"]:
        v = (r["key"] // mult) % size
        label = obs["sector_labels"][v] if f == "sector" else LABELS[f][v]
        parts.append(f"業種:{label}" if f == "sector" else label)
    return " ＆ ".join(parts)


def year_summary(r: dict) -> dict:
    ym, years = r["year_means"], r["years"]
    ok = np.isfinite(ym)
    sign = np.sign(r["mean"])
    same = int((np.sign(ym[ok]) == sign).sum())
    return {"years_with_data": int(ok.sum()), "same_sign_years": same, "by_year": {int(y): round(float(v), 4) for y, v in zip(years, ym) if np.isfinite(v)}}


def evaluate(obs: dict, mask: np.ndarray, sub: tuple, key: int, dims: list) -> dict:
    """1 つの組み合わせを、別の期間（確認期間）の観測で評価する。"""
    sel = mask.copy()
    for f, mult, size in dims:
        v = (key // mult) % size
        sel &= obs[f] == v
    per = obs["period"][sel]
    y = obs["y"][sel]
    if len(per) == 0:
        return {"obs": 0, "periods": 0, "mean": float("nan"), "t": float("nan"), "p": float("nan"), "same_sign_years": 0, "years_with_data": 0}
    s = pd.DataFrame({"p": per, "y": y}).groupby("p")["y"].agg(["mean", "count"])
    s = s[s["count"] >= MIN_PER_PERIOD]
    n = len(s)
    out = {"obs": int(len(y)), "periods": int(n), "mean": float(s["mean"].mean()) if n else float("nan")}
    if n >= 8 and s["mean"].std(ddof=1) > 0:
        t = float(s["mean"].mean() / (s["mean"].std(ddof=1) / math.sqrt(n)))
        out.update({"t": t, "p": float(2 * st.t_sf(abs(t), n - 1))})
    else:
        out.update({"t": float("nan"), "p": float("nan")})
    yrs = obs["buy_date"].year[s.index.to_numpy()]
    ym = s["mean"].groupby(yrs).mean()
    out["years_with_data"] = int(len(ym))
    out["same_sign_years"] = int(len(ym))              # 呼び出し側で、発見期間の符号と比べる
    out["year_means"] = {int(k): round(float(v), 4) for k, v in ym.items()}
    return out


def pattern_mask(obs: dict, base: np.ndarray, dims: list, key: int) -> np.ndarray:
    sel = base.copy()
    for f, mult, size in dims:
        sel &= obs[f] == (key // mult) % size
    return sel


def dedupe(obs: dict, base: np.ndarray, ordered: list, keep: int, overlap: float = 0.9, scan: int = 600) -> list:
    """t 値の順に並べた候補から、すでに選んだ候補と観測の重なり（共通 ÷ 和集合）が overlap 以上のものを飛ばして、keep 個を選ぶ。"""
    chosen, masks = [], []
    for r in ordered[:scan]:
        m = pattern_mask(obs, base, r["dims"], r["key"])
        dup = False
        for k in masks:
            inter = np.count_nonzero(m & k)
            if inter and inter / (np.count_nonzero(m) + np.count_nonzero(k) - inter) >= overlap:
                dup = True
                break
        if not dup:
            chosen.append(r)
            masks.append(m)
            if len(chosen) >= keep:
                break
    return chosen
