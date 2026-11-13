"""調整係数の突合の不一致を、原因別に集計する（件数・分位点のみ。生の表は出さない）。

使い方: python scripts/jquants/diagnose_adjustment.py [--root data/jquants]   （先に build_processed.py）
見るもの: 不一致の大半が (a) 丸め誤差（円単位の差が小さい）か、(b) 係数が 1 でない日（分割・併合）の前後か、(c) それ以外か。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import schema  # noqa: E402


def diagnose(pr: pd.DataFrame) -> dict:
    pairs = schema.adjustment_pairs(pr)
    bad = pairs[pairs["err_rel"] > 1e-6]
    q = lambda s: {k: float(f"{v:.3g}") for k, v in s.quantile([0.5, 0.9, 0.99, 1.0]).items()}  # noqa: E731
    rep = {"pairs_checked": len(pairs), "mismatch(rel>1e-6)": len(bad)}
    if bad.empty:
        return rep
    rep["abs_err_yen_quantiles"] = q(bad["err_abs"])
    rep["rel_err_quantiles"] = q(bad["err_rel"])
    rep["share_abs_err_le"] = {str(t): round(float((bad["err_abs"] <= t).mean()), 4) for t in (0.001, 0.01, 0.05, 0.1, 0.5, 1.0)}
    rep["factor_next_is_1"] = {"yes": int((bad["f_next"] == 1).sum()), "no": int((bad["f_next"] != 1).sum())}
    corp = pairs[pairs["f_next"] != 1]
    rep["pairs_with_factor_not_1"] = {"total": len(corp), "mismatch": int((corp["err_rel"] > 1e-6).sum())}
    rep["by_close_level"] = {}
    for lo, hi in ((0, 100), (100, 1000), (1000, 10000), (10000, 1e9)):
        m = (pairs["close"] >= lo) & (pairs["close"] < hi)
        rep["by_close_level"][f"{lo}-{int(hi)}"] = {"pairs": int(m.sum()), "mismatch": int((m & (pairs["err_rel"] > 1e-6)).sum())}
    y = pairs.assign(y=pairs["date"].dt.year)
    rep["mismatch_by_year"] = {int(k): int(v) for k, v in y[y["err_rel"] > 1e-6].groupby("y").size().items()}
    big = pairs[(pairs["err_rel"] > 1e-3)]
    rep["mismatch_rel_gt_1e-3"] = {"pairs": len(big), "codes": int(big["code"].nunique()), "factor_not_1": int((big["f_next"] != 1).sum())}
    return rep


def diagnose_flags(pr: pd.DataFrame, fl: pd.DataFrame, iv: pd.DataFrame) -> dict:
    """売買なし（no_trade）と ±31% 超の跳び（jump_flag）の内訳。市場区分・年・分割との関係（件数のみ）。"""
    m = pr[["code", "date", "adj_factor"]].merge(fl, on=["code", "date"]).sort_values("date")
    j = pd.merge_asof(m, iv.sort_values("valid_from")[["code", "valid_from", "valid_to", "market"]],
                      left_on="date", right_on="valid_from", by="code", direction="backward")
    j["market"] = j["market"].where(j["valid_to"] >= j["date"], "不明")
    out = {"no_trade_by_market": {}}
    for mk, g in j.groupby(j["market"].fillna("不明")):
        out["no_trade_by_market"][str(mk)] = {"rows": len(g), "no_trade": int(g["no_trade"].sum())}
    jf = j[j["jump_flag"]]
    out["jump_flag"] = {"total": len(jf), "by_year": {int(k): int(v) for k, v in jf.groupby(jf["date"].dt.year).size().items()},
                        "adj_factor_not_1_that_day": int((jf["adj_factor"] != 1).sum()),
                        "by_market": {str(k): int(v) for k, v in jf.groupby(jf["market"].fillna("不明")).size().items()}}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    out = Path(ap.parse_args().root) / "processed"
    pr = pd.read_parquet(out / "prices_daily.parquet")
    rep = diagnose(pr)
    rep.update(diagnose_flags(pr, pd.read_parquet(out / "quality_flags.parquet"), pd.read_parquet(out / "listed_master.parquet")))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
