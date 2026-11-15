"""気になった銘柄の診断（弾力性・今の下げ・直近の開示）。仕様は docs/w5_protocol.md「気になった銘柄の診断と、指定の前向きの記録」。
ローカル PC で実行。画面には集計だけを出す。1 件ごとの出来事の表は、手元のファイル（results/profile/<コード>.json）にだけ保存する。

  python scripts/w5/stock_profile.py --code 7203
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import forward_s2 as fs2  # noqa: E402
import schema  # noqa: E402
from selectlib import elastic  # noqa: E402

FLOOR_VA = 5e7


def norm_code(code: str) -> str:
    c = str(code).strip()
    return c + "0" if len(c) == 4 else c


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _pct_rank(vec: np.ndarray, floor_row: np.ndarray, j: int) -> float | None:
    """母集団（その日の floor で、弾力性が計算できる銘柄）のうち、この銘柄より弾力性が高い銘柄の割合（％。小さいほど弾力的）。"""
    m = floor_row & np.isfinite(vec)
    if not np.isfinite(vec[j]) or m.sum() < 30:
        return None
    return _r(100.0 * float((vec[m] > vec[j]).mean()), 1)


def disclosures(fins: pd.DataFrame, code: str, dates: pd.DatetimeIndex, n_days: int = 20) -> list:
    """直近 n_days 営業日に使えるようになった開示（日付・種類・純利益予想の修正の向きだけ）。"""
    f = fins[fins["Code"].astype(str) == code].dropna(subset=["usable_from"]).sort_values("usable_from").copy()
    if f.empty:
        return []
    f["FNP"] = pd.to_numeric(f.get("FNP"), errors="coerce")
    f["prev"] = f.groupby("CurFYEn")["FNP"].shift()
    start = dates[max(len(dates) - n_days, 0)]
    f = f[f["usable_from"] >= start]
    out = []
    for r in f.itertuples(index=False):
        d = "修正なし"
        if pd.notna(r.FNP) and pd.notna(r.prev):
            d = "上方修正" if r.FNP > r.prev * 1.0001 else "下方修正" if r.FNP < r.prev * 0.9999 else "修正なし"
        out.append({"date": str(pd.Timestamp(r.usable_from).date()), "type": str(getattr(r, "DocType", "")), "np_forecast_revision": d})
    return out


def snapshot(root: Path, code: str, asof: str | None = None) -> dict:
    P, iv, fins = fs2.load_panel(root, asof)
    code = norm_code(code)
    if code not in P.codes:
        return {"code": code, "error": "価格データにない銘柄コード"}
    j_all = P.codes.index(code)
    elig_hist = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    floor = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=FLOOR_VA)
    s = len(P.dates) - 1
    attrs = iv[(iv["code"].astype(str) == code) & (iv["valid_to"] >= P.dates[s]) & (iv["valid_from"] <= P.dates[s])]
    meta = {"name": str(attrs["name"].iloc[0]) if len(attrs) and "name" in attrs.columns else None, "market": str(attrs["market"].iloc[0]) if len(attrs) else None,
            "margin_class": str(attrs["margin_class"].iloc[0]) if len(attrs) else None, "s33": str(attrs["s33"].iloc[0]) if len(attrs) else None}
    out = {"code": code, "asof": str(P.dates[s].date()), "meta": meta, "in_decision_universe": bool(floor[s, j_all]),
           "in_history_universe": bool(elig_hist[s, j_all])}
    if not (elig_hist | floor)[:, j_all].any():
        out["note"] = "流動性（売買代金 60 日平均 2,000 万円）・履歴の条件を、一度も満たしていない。弾力性は計算しない"
        return out
    B = elastic.build(P, elig_hist, floor)
    jj = int(np.flatnonzero(B["cols"] == j_all)[0])
    Q, ev, sc = B["Q"], B["ev"], B["scores"]
    ts = np.flatnonzero(ev[:, jj])
    reb = B["ex_reb"][ts, jj]
    rec = sc["recovered"][ts, jj]
    okr, okc = np.isfinite(reb), np.isfinite(rec)
    out["past_events"] = {"count": int(len(ts)), "with_rebound_outcome": int(okr.sum()),
                          "rebound10_mean": _r(reb[okr].mean()) if okr.any() else None, "rebound10_median": _r(np.median(reb[okr])) if okr.any() else None,
                          "rebound10_share_positive": _r(float((reb[okr] > 0).mean()), 2) if okr.any() else None,
                          "recovered_half_within_21d_share": _r(float(rec[okc].mean()), 2) if okc.any() else None,
                          "days_since_last_event": int(s - ts[-1]) if len(ts) else None}
    out["elasticity"] = {d: {"score": _r(sc[d][s, jj]), "share_of_universe_more_elastic_pct": _pct_rank(sc[d][s], B["floor"][s], jj)} for d in elastic.DEFS}
    c = Q.adj_close
    ex21 = None
    if s >= 21:
        r21 = c[s] / c[s - 21] - 1
        um = np.nanmean(np.where(B["elig_hist"][s], r21, np.nan))
        ex21 = _r(r21[jj] - um)
    hi252 = np.nanmax(Q.adj_high[max(s - 251, 0):s + 1, jj]) if np.isfinite(Q.adj_high[max(s - 251, 0):s + 1, jj]).any() else np.nan
    sig = elastic.sigma_daily(c)[s, jj]
    out["current"] = {"excess_5d": _r(B["ex5"][s, jj]), "excess_21d": ex21, "from_52w_high": _r(c[s, jj] / hi252 - 1) if np.isfinite(hi252) else None,
                      "drop_event_today": bool(ev[s, jj]), "drop_threshold_5d": _r(-max(elastic.Z * sig * np.sqrt(5), elastic.FLOOR)) if np.isfinite(sig) else None}
    out["disclosures_last_20_business_days"] = disclosures(fins, code, P.dates)
    detail = [{"event_date": str(P.dates[t].date()), "excess_5d": _r(B["ex5"][t, jj]), "rebound10": _r(B["ex_reb"][t, jj]),
               "recovered_half_21d": (None if not np.isfinite(sc["recovered"][t, jj]) else bool(sc["recovered"][t, jj]))} for t in ts]
    out["_detail"] = detail
    return out


def main(root: Path, code: str, write=True) -> dict:
    res = snapshot(root, code)
    detail = res.pop("_detail", None)
    if write and detail is not None:
        d = root / "results" / "profile"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{res['code']}.json").write_text(json.dumps({**res, "events": detail}, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
        res["events_file"] = str(Path("results") / "profile" / f"{res['code']}.json") + "（1 件ごとの表。画面には出さない）"
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--code", required=True)
    a = ap.parse_args()
    print(json.dumps(main(Path(a.root), a.code), ensure_ascii=False, indent=1, default=float))
