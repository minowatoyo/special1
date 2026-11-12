"""ウォークフォワードの結果の集計と、事前登録した採否ルールの適用。

採否ルール（09_forecasting/02_protocol.md の 5 節）:
  1. 幅（σ）の段: B0（伸縮なし）・B1（EWMA）・V2（HAR 型）・V3（結合）のうち、平均 CRPS が最小のもの。
     同じなら単純なほう（B0 → B1 → V2 → V3 の順）を選ぶ。
  2. 傾き・類似局面の段: 候補（T1・T2・T3・X1・K1・E1）のうち平均 CRPS が最小のものを 1 つ選び、
     次のすべてを満たすときだけ採用する。満たさなければ 1 の結果のまま。
       (a) Reality Check の p < 0.05（候補を複数試したことの補正）
       (b) 1 の結果に対する DM 検定の片側 p < 0.05 かつ定常ブートストラップの p < 0.05
       (c) 評価期間の前半・後半のどちらでも CRPS が改善
       (d) 尺度で割った CRPS（各時点の CRPS ÷ その時点の EWMA の σ）でも改善
           （平均 CRPS は値動きの荒い時期の成績で決まりやすいため、静かな時期を含めた確認）
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import stats as st

__all__ = ["summarize", "decide", "decide_panel", "vol_summary", "touch_summary", "TILT_FAMILY", "ADOPT_P"]

TILT_FAMILY = ("T1", "T2", "T3", "X1", "K1", "E1")
ADOPT_P = 0.05


def _common(res: dict, models) -> np.ndarray:
    ok = np.ones(len(res["R"]), dtype=bool)
    for m in models:
        ok &= np.isfinite(res["crps"][m])
    return ok


def _block(res: dict) -> float:
    return max(2.0 * res["h"] / res["step"], 10.0)


def summarize(wf: dict, cfg) -> dict:
    """期間ごとの成績表。全モデルが予測を出せた時点（共通の標本）で比べる。"""
    out = {}
    for h, res in wf.items():
        models = res["models"]
        ok = _common(res, models)
        n = int(ok.sum())
        rows = []
        if n == 0:
            out[h] = pd.DataFrame()
            continue
        y = res["R"][ok]
        up = (y > 0).astype(float)
        base_b1 = res["crps"]["B1"][ok]
        base_b0 = res["crps"]["B0"][ok]
        scale = res["scale"][ok]
        half = n // 2
        for m in models:
            c = res["crps"][m][ok]
            p = res["pit"][m][ok]
            pu = res["pup"][m][ok]
            dm = st.dm_test(c, base_b1, h, res["step"]) if m != "B1" else {"p": np.nan}
            rows.append({
                "model": m, "n": n, "crps": float(c.mean()),
                "skill_vs_B1": float(1.0 - c.mean() / base_b1.mean()),
                "sskill_vs_B1": float(1.0 - (c / scale).mean() / (base_b1 / scale).mean()),
                "skill_vs_B0": float(1.0 - c.mean() / base_b0.mean()),
                "dm_p_vs_B1": float(dm["p"]),
                "cov50": float(((p >= 0.25) & (p <= 0.75)).mean()),
                "cov80": float(((p >= 0.10) & (p <= 0.90)).mean()),
                "cov90": float(((p >= 0.05) & (p <= 0.95)).mean()),
                "brier_up": float(((pu - up) ** 2).mean()),
                "hit_up": float(((pu > 0.5) == (up > 0.5)).mean()),
                "skill_h1": float(1.0 - c[:half].mean() / base_b1[:half].mean()),
                "skill_h2": float(1.0 - c[half:].mean() / base_b1[half:].mean()),
            })
        df = pd.DataFrame(rows).set_index("model")
        df.attrs["first"] = str(pd.Timestamp(res["dates"][np.flatnonzero(ok)[0]]).date())
        df.attrs["last"] = str(pd.Timestamp(res["dates"][np.flatnonzero(ok)[-1]]).date())
        df.attrs["up_rate"] = float(up.mean())
        out[h] = df
    return out


def _decide_from_losses(c: dict, models: list, h: int, step: int, block: float, cfg, scale=None) -> dict:
    """損失の系列（モデル名 → 配列。時点は共通）から、事前登録の採否ルールを適用する。"""
    n = len(c["B1"])
    d = {"h": h, "n": int(n), "sigma_model": "B1", "final_model": "B1", "adopted_tilt": None}
    if n < 60:
        d["reason"] = "評価できる時点が少ない（60 未満）。基準 B1 を使う"
        return d
    order = ("B0", "B1", "V2", "V3")
    sigma_model = min(order, key=lambda m: (round(float(c[m].mean()), 12), order.index(m)))
    d["sigma_model"] = sigma_model
    d["sigma_dm_p"] = float(st.dm_test(c["V3"], c["B1"], h, step)["p"])
    d["sigma_skill"] = float(1.0 - c["V3"].mean() / c["B1"].mean())
    best_scaled = min(("B1", "V2", "V3"), key=lambda m: float(c[m].mean()))
    d["scaling_skill"] = float(1.0 - c[best_scaled].mean() / c["B0"].mean())
    d["scaling_dm_p"] = float(st.dm_test(c[best_scaled], c["B0"], h, step)["p"])
    cands = [m for m in TILT_FAMILY if m in models]
    d["final_model"] = sigma_model
    if cands:
        bench = c[sigma_model]
        diffs = np.column_stack([bench - c[m] for m in cands])
        rc = st.reality_check(diffs, block, cfg.boot_b, cfg.seed + h)
        means = diffs.mean(axis=0)
        best = cands[int(means.argmax())]
        bd = bench - c[best]
        dm = st.dm_test(c[best], bench, h, step)
        bt = st.boot_mean_pvalue(bd, block, cfg.boot_b, cfg.seed + 7 * h)
        half = len(bd) // 2
        h1, h2 = float(bd[:half].mean()), float(bd[half:].mean())
        scaled_gain = float(np.mean(bd / scale)) if scale is not None else float("nan")
        scaled_ok = (scale is None) or scaled_gain > 0
        passed = (rc["p"] < ADOPT_P and dm["p"] < ADOPT_P and bt["p"] < ADOPT_P and h1 > 0 and h2 > 0 and scaled_ok)
        d.update({"best_candidate": best, "best_skill": float(1.0 - c[best].mean() / bench.mean()), "scaled_gain": scaled_gain,
                  "rc_p": float(rc["p"]), "dm_p": float(dm["p"]), "boot_p": float(bt["p"]),
                  "half1_gain": h1, "half2_gain": h2, "n_candidates": len(cands)})
        if passed:
            d["final_model"] = best
            d["adopted_tilt"] = best
            d["reason"] = f"{best} が採用基準をすべて満たした"
        else:
            fails = []
            if not rc["p"] < ADOPT_P:
                fails.append(f"Reality Check p={rc['p']:.2f}")
            if not dm["p"] < ADOPT_P:
                fails.append(f"DM p={dm['p']:.2f}")
            if not bt["p"] < ADOPT_P:
                fails.append(f"ブートストラップ p={bt['p']:.2f}")
            if not (h1 > 0 and h2 > 0):
                fails.append("前半・後半の片方で改善なし")
            if not scaled_ok:
                fails.append("尺度で割った CRPS では改善なし")
            d["reason"] = f"最良の候補 {best} は採用基準を満たさない（" + "、".join(fails) + "）"
    return d


def decide(wf: dict, cfg) -> dict:
    """事前登録の採否ルールを、1 銘柄の検証結果に適用する。"""
    out = {}
    for h, res in wf.items():
        models = res["models"]
        ok = _common(res, models)
        c = {m: res["crps"][m][ok] for m in models}
        out[h] = _decide_from_losses(c, models, h, res["step"], _block(res), cfg, res["scale"][ok])
    return out


def decide_panel(wfs: dict, cfg) -> dict:
    """複数銘柄の検証結果をまとめて採否を決める。

    1 銘柄の履歴だけでは、方向の手がかりを見分ける力（検出力）が弱い。同じ手順を多くの銘柄に当て、
    日付ごとに銘柄平均した損失で同じ採否ルールを適用する（「この種の銘柄一般で効くか」を問う）。
    wfs = {銘柄名: walk_forward の結果}。戻り値の各期間の辞書に n_assets を足す。
    """
    out = {}
    hs = sorted(set.intersection(*[set(w.keys()) for w in wfs.values()])) if wfs else []
    for h in hs:
        models = [m for m in next(iter(wfs.values()))[h]["models"] if all(m in w[h]["models"] for w in wfs.values())]
        frames = []
        for w in wfs.values():
            res = w[h]
            ok = _common(res, models)
            if ok.sum():
                # 銘柄ごとに、その時点の EWMA の σ で割ってから平均する（値動きの大きい銘柄だけで決まらないように）
                frames.append(pd.DataFrame({m: res["crps"][m][ok] / res["scale"][ok] for m in models},
                                           index=pd.DatetimeIndex(res["dates"][ok])))
        if not frames:
            continue
        avg = pd.concat(frames).groupby(level=0).mean().sort_index()
        c = {m: avg[m].to_numpy() for m in models}
        d = _decide_from_losses(c, models, h, 1, max(2.0 * h, 10.0), cfg)
        d["n_assets"] = len(frames)
        d["n_dates"] = int(len(avg))
        out[h] = d
    return out


def vol_summary(asset, cfg) -> pd.DataFrame:
    """ボラティリティ予測そのものの採点（QLIKE。小さいほど良い）。

    QLIKE = RV/σ̂² − ln(RV/σ̂²) − 1（RV は先 h 日の実現分散）。誤差の大きい代理変数（実現分散）でも
    予測の順位づけが狂いにくい損失として知られる。「長期平均」は、その時点までの日次リターン二乗の平均を
    そのまま使う予測（ボラティリティは変わらないとみなす基準）。
    """
    r = np.log(asset.df["close"] / asset.df["close"].shift(1))
    r2 = (r ** 2)
    naive_daily = r2.expanding(min_periods=250).mean().to_numpy(dtype=float)
    rows = []
    for h in cfg.horizons:
        rv = r2.rolling(h).sum().shift(-h).to_numpy(dtype=float)
        f = {"長期平均": h * naive_daily, **{m: asset.sig[h][m] ** 2 for m in ("S1", "S2", "S3")}}
        ok = np.isfinite(rv) & (rv > 0)
        ok[: cfg.burn] = False
        for v in f.values():
            ok &= np.isfinite(v) & (v > 0)
        if ok.sum() < 100:
            continue
        row = {"h": h, "n": int(ok.sum())}
        for m, v in f.items():
            x = rv[ok] / v[ok]
            row[m] = float(np.mean(x - np.log(x) - 1.0))
        rows.append(row)
    return pd.DataFrame(rows)


def touch_summary(wf: dict, cfg) -> pd.DataFrame:
    """水準到達確率（期間中に高値・安値が b×σ に届く確率）の検証。Brier と実際の到達率。"""
    rows = []
    for h, res in wf.items():
        t = res["touch"]
        for b in cfg.touch_b:
            for side in ("up", "dn"):
                p, p0, hit = t[(side, b)], t[(side + "0", b)], t[(side + "_hit", b)]
                ok = np.isfinite(p) & np.isfinite(p0) & np.isfinite(hit)
                if ok.sum() < 30:
                    continue
                bs, bs0 = ((p[ok] - hit[ok]) ** 2).mean(), ((p0[ok] - hit[ok]) ** 2).mean()
                rows.append({"h": h, "side": side, "b": b, "n": int(ok.sum()), "mean_prob": float(p[ok].mean()),
                             "hit_rate": float(hit[ok].mean()), "brier": float(bs), "brier_base": float(bs0),
                             "brier_skill": float(1.0 - bs / bs0) if bs0 > 0 else np.nan})
    return pd.DataFrame(rows)
