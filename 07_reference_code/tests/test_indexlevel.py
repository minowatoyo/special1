"""指数レベルの逆張り（合成データ）。点灯の定義、先読みがないこと、植えた反発・反転の検出、効果がないときの空振り。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from selectlib import indexlevel, rules

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def make_world(tmp, seed=0, rebound=0.0, sector_reversal=0.0, n_sec=33):
    """TOPIX: ランダムウォークに、急落のたびの反発（rebound）を植える。業種: 5 日の相対リターンが低いほど、次の 5 日で上がる（sector_reversal）。"""
    rng = np.random.default_rng(seed)
    d = pd.bdate_range("2016-11-14", "2026-11-12")
    n = len(d)
    r = rng.normal(0.0003, 0.009, n)
    close = np.exp(np.cumsum(r)) * 1000
    # 急落（5 日で −3%）の翌日から 5 日間、合計 rebound だけ上がる
    for t in range(10, n - 10):
        if close[t] / close[t - 5] - 1 <= -0.03 and rebound:
            r[t + 2:t + 7] += rebound / 5
    close = np.exp(np.cumsum(r)) * 1000
    opn = np.r_[close[0], close[:-1]]
    tp = pd.DataFrame({"open": opn, "high": close, "low": close, "close": close}, index=d)
    tp.index.name = "date"
    secs = {}
    for k in range(n_sec):
        e = rng.normal(0, 0.008, n)
        s = np.exp(np.cumsum(r + e)) * 100
        secs[f"{40 + k // 2:04d}" + ("A" if k % 2 else "")] = s       # 実データと同じ抽出（"0040"〜"0060" の文字列の範囲）で、33 本になる
    if sector_reversal:
        for k in secs:
            s = secs[k]
            rel5 = np.full(n, np.nan)
            rel5[5:] = (s[5:] / s[:-5]) / (close[5:] / close[:-5]) - 1
        # 相対が低い業種ほど、次の 5 日で上げる: 業種 k の日次リターンに、直前 5 日の相対リターンの −係数を足す
        arr = np.column_stack([secs[k] for k in secs])
        ret = np.vstack([np.zeros((1, n_sec)), arr[1:] / arr[:-1] - 1])
        for t in range(10, n - 1):
            rel = (arr[t] / arr[t - 5]) / (close[t] / close[t - 5]) - 1
            ret[t + 1] += -sector_reversal * (rel - rel.mean())
        arr = 100 * np.cumprod(1 + ret, axis=0)
        secs = {k: arr[:, i] for i, k in enumerate(secs)}
    rows = []
    for k, s in secs.items():
        rows.append(pd.DataFrame({"date": d, "index_code": k, "open": np.r_[s[0], s[:-1]], "high": s, "low": s, "close": s}))
    ix = pd.concat(rows, ignore_index=True)
    root = tmp / "jq"
    (root / "processed").mkdir(parents=True)
    tp.reset_index().to_parquet(root / "processed" / "topix_daily.parquet", index=False)
    ix.to_parquet(root / "processed" / "indices_daily.parquet", index=False)
    (root / "processed" / "prices_daily.parquet").write_bytes(b"")           # manifest 用の空ファイル（rs.manifest_sha が読むだけ）
    return tp, root


def test_flags_use_only_the_past_and_fwd_open_timing():
    d = pd.bdate_range("2020-01-01", periods=400)
    c = pd.Series(np.linspace(100, 200, 400), index=d)
    c.iloc[350:] = c.iloc[350:] * 0.8                                         # 急落
    tp = pd.DataFrame({"open": c, "high": c, "low": c, "close": c})
    f = indexlevel.flags(tp)
    assert f[indexlevel.NAMES[2]].iloc[350] and f[indexlevel.NAMES[1]].iloc[350] and not f[list(indexlevel.NAMES[1:])].iloc[349].any()
    # 未来を壊しても、過去の点灯は変わらない
    tp2 = tp.copy()
    tp2.iloc[360:] = 1.0
    assert (indexlevel.flags(tp2).iloc[:360] == f.iloc[:360]).all().all()
    o = np.arange(1.0, 21.0)
    F = indexlevel.fwd_open(o, 5)
    assert abs(F[0] - (o[6] / o[1] - 1)) < 1e-12 and np.isnan(F[-1]) and np.isnan(F[-6])


def test_sector_test_detects_planted_reversal_and_market_test_a_planted_rebound(tmp_path):
    import index_contrarian as ic
    tp, root = make_world(tmp_path, seed=1, rebound=0.04, sector_reversal=0.5)
    res = ic.main(root)
    by = {r["test"]: r for r in res["tests"]}
    assert len(res["tests"]) == 10 and res["tests_run"] >= 5 and res["sectors"] == 33 and res["ledger_chain"]["ok"]
    m = by["I1_5d_return_bottom5pct|h=5"]
    assert m["discovery"]["mean"] > 0.01 and m["discovery"]["q"] < 0.10 and m["law_candidate"] and m["confirmation"]["mean"] > 0.01
    s = by["S1_rel5d_bottom5|h=5"]
    assert s["discovery"]["mean"] > 0.002 and s["discovery"]["q"] < 0.10 and s["law_candidate"]
    for r in res["tests"]:                                                    # 通っていない検定は、確認期間を読まない
        if r["test"] not in res["passed_discovery"]:
            assert isinstance(r["confirmation"], str)


def test_null_world_has_no_law_candidates_and_no_lookahead(tmp_path):
    import index_contrarian as ic
    tp, root = make_world(tmp_path, seed=2)
    res = ic.main(root)
    assert res["law_candidates"] == []
    # 先読みなし: 確認期間の価格を壊しても、発見期間の結果は変わらない
    b = int(np.searchsorted(tp.index.values, rules.SPLIT.to_datetime64()))
    tp2 = tp.copy()
    tp2.iloc[b + 5:, :] = tp2.iloc[b + 5:, :] * np.linspace(0.5, 2.0, len(tp2) - b - 5)[:, None]
    root2 = tmp_path / "b"
    (root2 / "processed").mkdir(parents=True)
    tp2.reset_index().to_parquet(root2 / "processed" / "topix_daily.parquet", index=False)
    pd.read_parquet(root / "processed" / "indices_daily.parquet").to_parquet(root2 / "processed" / "indices_daily.parquet", index=False)
    (root2 / "processed" / "prices_daily.parquet").write_bytes(b"")
    res2 = ic.main(root2)
    assert {r["test"]: r["discovery"] for r in res["tests"] if "S" not in r["test"][:1]} == {r["test"]: r["discovery"] for r in res2["tests"] if "S" not in r["test"][:1]}
