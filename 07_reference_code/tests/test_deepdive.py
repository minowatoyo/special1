"""深掘りレポート（合成データ）。条件の符号の一致、基準率、建玉の計算、関門、レポートの一連の出力、記録との連携。"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from test_elastic import elastic_panel
from test_events import _iv, _write_limits
from test_rules import _write_processed
from test_selectlib import intervals_for

from selectlib import atlas, deepdive

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "w5"))


def _fins_default(P, codes):
    return pd.DataFrame({"Code": codes, "DiscDate": P.dates[100], "usable_from": P.dates[101], "CurFYEn": "x", "FOP": 1.0, "FNP": 1.0, "FEPS": 1.0, "FDivAnn": 1.0, "BPS": 1.0, "ROE": 0.1})


def test_codes_at_matches_build_obs_on_a_grid_date():
    P, codes, _ = elastic_panel(n_codes=80, seed=3, elastic_share=0.0, dates=("2019-01-01", "2023-12-29"))
    iv = intervals_for(codes, P.dates)
    fins = _fins_default(P, codes)
    elig = np.ones(P.adj_close.shape, bool)
    elig[:300] = False
    grid = P.rebalance_idx()
    obs = atlas.build_obs(P, elig, iv, fins, None, grid)
    k = 20
    T = int(obs["T"][k])
    sel = obs["period"] == k
    cd = atlas.codes_at(P, elig[T], iv, fins, None, T)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = P.adj_open[T + 22] / P.adj_open[T + 1] - 1
    j = np.flatnonzero(elig[T] & np.isfinite(y) & np.isfinite(P.raw_open[T + 1]))
    assert sel.sum() == len(j)
    for f in ("liquidity", "price", "drawdown", "ret21", "ret126", "revision", "trend", "market"):          # 区切りが固定の条件は、完全に一致する
        assert (obs[f][sel] == cd[f][j]).all(), f
    for f in ("vol", "value", "roe", "margin"):                                                            # 3 分位は、母集団がわずかに違うので、ほぼ一致
        assert (obs[f][sel] == cd[f][j]).mean() > 0.9, f


def test_reference_classes_position_size_and_gate():
    rng = np.random.default_rng(0)
    n = 6000
    arr = {f: rng.integers(0, 2, n).astype(np.int8) for f in atlas.CORE_FEATURES}
    arr["period"] = np.repeat(np.arange(60), 100)
    arr["y"] = rng.normal(0, 0.05, n) + np.where((arr["liquidity"] == 1) & (arr["ret21"] == 1), 0.02, 0.0)        # 植えた状態
    codes = {f: np.array([1, 0], dtype=np.int8) for f in atlas.CORE_FEATURES}
    rc = deepdive.reference_classes(arr, codes, 0)
    assert rc["chain"][0]["added"] == atlas.LABELS["liquidity"][1] and rc["chain"][1]["mean"] > 0.012 and rc["chain"][1]["t"] > 3
    assert rc["chain"][0]["obs"] > rc["chain"][1]["obs"] and any("stopped" in c for c in rc["chain"]) or len(rc["chain"]) == len(deepdive.CHAIN)
    assert abs(rc["all_observations"]["mean"] - arr["y"].mean()) < 0.002 and rc["singles"]["roe"]["obs"] > 2000
    other = deepdive.reference_classes(arr, codes, 1)
    assert abs(other["chain"][1]["mean"]) < 0.01                                                                  # 植えていない状態は、0 付近
    # 建玉: 損失の予算 10 万円、想定する下落 10%、株価 2,000 円 → 500 株（100 万円、資金の 10%）
    r = np.r_[np.full(80, -0.10), np.full(920, 0.01)]                           # 5% 点が、−10% に乗る
    ps = deepdive.position_size(2000.0, r, 1e9)
    assert ps["stress_drop_21d_p5"] == 0.10 and ps["shares"] == 500 and ps["position_yen"] == 1_000_000 and ps["loss_if_stress_yen"] == 100_000
    assert deepdive.position_size(2000.0, r, 2e7)["shares"] == 100 and deepdive.position_size(2000.0, r, 2e7)["binding_constraint"] == "liquidity_cap"   # 売買代金の 1% = 20 万円
    hi = deepdive.position_size(60000.0, r, 1e9)                                                                  # 100 株 = 600 万円 → 買えない
    assert hi["shares"] == 0 and "買えない" in hi["note"]
    assert deepdive.position_size(2000.0, np.full(1000, 0.001), 1e9)["stress_drop_21d_p5"] == 0.05               # 下限 5%
    # 関門
    assert deepdive.gate([{"event": "X4_down_10pct", "days_ago": 2}], False, 500, False)["verdict"].startswith("回避")
    assert deepdive.gate([], True, 500, False)["verdict"].startswith("回避")
    assert deepdive.gate([], False, 0, False)["verdict"].startswith("買えない")
    g = deepdive.gate([], False, 500, True)
    assert g["verdict"] == "回避条件なし" and g["cautions"]


def _world(tmp):
    P, codes, _ = elastic_panel(n_codes=90, seed=9, elastic_share=0.0)
    T = len(P.dates) - 1
    P.adj_close[T - 1:, 0] *= 0.85                                      # 銘柄 0: 2 営業日前に −15%（極端な出来事 X4）
    P.raw_close[T - 1:, 0] *= 0.85
    root = tmp / "jq"
    _write_processed(root, P, codes)
    _write_limits(root, P, codes)
    _iv(P, codes, {}).to_parquet(root / "processed" / "listed_master.parquet", index=False)
    return P, codes, root


def test_deep_dive_end_to_end_and_record_with_layers(tmp_path):
    import deep_dive as dd
    import watchlist as wl
    P, codes, root = _world(tmp_path)
    d = dd.main(root, codes[0][:4])
    assert d["verdict"].startswith("回避") and any(e["event"] == "X4_down_10pct" and e["days_ago"] == 1 for e in d["gate"]["extreme_events_last_5d"])
    assert set(d["outside_view"]) == {"h=21", "h=63"} and d["outside_view"]["h=21"]["all_observations"]["obs"] > 3000
    assert d["outside_view"]["h=21"]["chain"][0]["added"] == atlas.LABELS["liquidity"][1]                      # 売買代金 1 億円 → 段階 B
    assert d["layers"]["red_flag"] is True and d["layers"]["agents"] is None and d["layers"]["s2_candidate"] is False
    assert d["verified_buy_side"]["s2"]["candidate"] is False and d["verified_buy_side"]["sel_c1"]["in_universe"] is False
    md = (root / d["files"]["markdown"]).read_text(encoding="utf-8")
    assert "関門" in md and "基準率" in md and "建玉" in md
    assert len(list((root / "results" / "deep").glob("_obs_*_h21.npz"))) == 1
    # 関門に掛からない銘柄: 判定は「回避条件なし」。検証済みの買い材料は、なし。買いの判定は、機械的には出ない
    d2 = dd.main(root, codes[5][:4])
    assert d2["verdict"] == "回避条件なし。検証済みの買い材料: なし" and d2["position_size"]["shares"] > 0 and d2["gate"]["extreme_events_last_5d"] == []
    assert len(list((root / "results" / "deep").glob("_obs_*_h21.npz"))) == 1                                   # 観測表は、使い回す
    # 記録: 各層の値が、台帳に入る。日付・銘柄が合わないレポートは、拒む
    r = wl.add(root, codes[0][:4], "不明", "戻らない", typ="需給反発", check="次の決算", exit_="上方修正が出たら撤回", dossier=str(root / d["files"]["json"]))
    assert r["recorded"]
    rows = wl.AppendOnlyLedger(root / "ledger" / "watchlist.jsonl")._rows()
    assert rows[0]["payload"]["layers"]["red_flag"] is True and rows[0]["payload"]["layers"]["gate"].startswith("回避")
    bad = wl.add(root, codes[5][:4], "不明", "戻る", dossier=str(root / d["files"]["json"]))
    assert "error" in bad
    assert dd.main(root, "99999")["error"]
