"""ウォークフォワード（時点を 1 日ずつ進めながら、その時点までの情報だけで予測分布を作って採点する）。

候補モデル（事前登録。記号は 09_forecasting/02_protocol.md と同じ）:
  B0  過去の h 日リターンの経験分布（ボラティリティで伸縮しない基準）
  B1  σ(S1: EWMA) × 標準化リターンの経験分布
  V2  σ(S2: HAR 型。レンジ・下落・出来高) × 同上
  V3  σ(S3: S1 と S2 の結合) × 同上
  T1  V3 ＋ 傾き（トレンド特徴量のリッジ回帰）
  T2  V3 ＋ 傾き（短期リターン）
  T3  V3 ＋ 傾き（全特徴量）
  X1  V3 ＋ 傾き（全特徴量＋補助系列。補助系列があるときだけ）
  K1  V3 ＋ 類似局面（k 近傍）の標準化リターン分布との分位点平均
  E1  V3・T3・K1 の分位点平均

予測分布は分位点の格子（既定 100 点）で表す。標準化リターン z_t = (R_t^(h) − h·m_t) / σ̂_t^(h) は、
結果が確定した行（t + h <= 現在）だけを使う。m_t はその時点までの日次対数リターンの平均（過去平均）で、
予測は h·m_T + σ̂_T × （z の経験分位点）とする。平均を「リターンの単位で一定」と置くので、ボラティリティが
高い局面ほど上昇確率は 50% に近づく（平均を σ に比例させると、荒い局面で傾きを過大に見積もる）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import stats as st
from .features import FEATURE_SETS, KNN_FEATURES, feature_frame, standardize_expanding
from .vol import sigma_forecasts

__all__ = ["Config", "Asset", "prepare_asset", "walk_forward", "SortedBuf", "MODEL_LABELS"]

MODEL_LABELS = {
    "B0": "過去リターンの経験分布（伸縮なし）", "B1": "EWMA で伸縮", "V2": "HAR 型（レンジ・下落・出来高）で伸縮",
    "V3": "EWMA と HAR の結合で伸縮", "T1": "V3＋傾き（トレンド）", "T2": "V3＋傾き（短期リターン）",
    "T3": "V3＋傾き（全特徴量）", "X1": "V3＋傾き（全特徴量＋補助系列）", "K1": "V3＋類似局面",
    "E1": "V3・T3・K1 の平均",
}


@dataclass
class Config:
    horizons: tuple = (5, 21, 63)
    burn: int = 1250            # 最初の約 5 年は学習のみ
    refit: int = 21             # 回帰の推定し直し間隔（営業日）
    q: int = 100                # 分位点格子の点数
    tau0: float = 0.05          # 標準化係数の事前標準偏差。リッジの強さは λ = h / tau0²
    knn_k: int = 150
    knn_min: int = 600
    knn_blend: float = 0.5
    step: int = 1               # 採点する時点の間隔
    lam: float = 0.94
    har_min_train: int = 500
    min_fit: int = 500
    touch_b: tuple = (0.5, 1.0, 1.5)
    boot_b: int = 2000
    seed: int = 20261111
    finite_sample: bool = True  # 分位点の有限標本補正（stats.predictive_taus）
    overlap_eff: float = 1.5    # 重なりのある標本の有効な数 = overlap_eff × 標本数 ÷ h
    record_at: tuple = ()       # 分位点格子を保存する時点（検査用）


@dataclass
class Asset:
    name: str
    df: pd.DataFrame
    dates: np.ndarray
    close: np.ndarray
    sig: dict
    R: dict
    MH: dict
    ML: dict
    Fraw: pd.DataFrame
    F: pd.DataFrame
    sets: dict
    knn_cols: list
    aux_names: list = field(default_factory=list)
    mbar: np.ndarray | None = None      # その時点までの日次対数リターンの平均（過去平均）


class SortedBuf:
    """昇順を保ったまま 1 件ずつ足せる配列（経験分布の分位点を速く求めるため）。"""

    def __init__(self, cap: int):
        self.a = np.empty(cap + 1)
        self.n = 0

    def bulk(self, vals) -> None:
        v = np.asarray(vals, dtype=float)
        v = np.sort(v[np.isfinite(v)])
        self.n = len(v)
        self.a[: self.n] = v

    def add(self, x: float) -> None:
        if not np.isfinite(x):
            return
        pos = int(np.searchsorted(self.a[: self.n], x))
        self.a[pos + 1: self.n + 1] = self.a[pos: self.n]
        self.a[pos] = x
        self.n += 1

    def view(self) -> np.ndarray:
        return self.a[: self.n]

    def frac_ge(self, x: float) -> float:
        return float("nan") if self.n == 0 else 1.0 - float(np.searchsorted(self.a[: self.n], x, side="left")) / self.n

    def frac_le(self, x: float) -> float:
        return float("nan") if self.n == 0 else float(np.searchsorted(self.a[: self.n], x, side="right")) / self.n


def prepare_asset(df: pd.DataFrame, name: str, cfg: Config, aux: dict | None = None) -> Asset:
    """1 銘柄ぶんの前計算（σ の予測、先 h 日のリターンと高値・安値、特徴量）。"""
    c = df["close"]
    lc = np.log(c)
    sig = {h: {m: s[m].to_numpy(dtype=float) for m in s.columns}
           for h, s in sigma_forecasts(df, cfg.horizons, cfg.lam, cfg.refit, cfg.har_min_train).items()}
    R, MH, ML = {}, {}, {}
    for h in cfg.horizons:
        R[h] = (lc.shift(-h) - lc).to_numpy(dtype=float)
        MH[h] = (np.log(df["high"].rolling(h).max().shift(-h)) - lc).to_numpy(dtype=float)
        ML[h] = (np.log(df["low"].rolling(h).min().shift(-h)) - lc).to_numpy(dtype=float)
    mbar = lc.diff().expanding(min_periods=250).mean().to_numpy(dtype=float)
    fraw = feature_frame(df, aux)
    f = standardize_expanding(fraw)
    usable = [col for col in f.columns if f[col].notna().sum() > 300]
    sets = {k: [x for x in v if x in usable] for k, v in FEATURE_SETS.items()}
    aux_names = list((aux or {}).keys())
    if aux_names:
        extra = [col for col in usable if any(col.startswith(a + "_") for a in aux_names)]
        sets["X1"] = sets["T3"] + extra
    knn_cols = [x for x in KNN_FEATURES if x in usable]
    return Asset(name=name, df=df, dates=df.index.to_numpy(), close=c.to_numpy(dtype=float), sig=sig,
                 R=R, MH=MH, ML=ML, Fraw=fraw, F=f, sets=sets, knn_cols=knn_cols, aux_names=aux_names, mbar=mbar)


def _cum_normal_eq(x: np.ndarray, y: np.ndarray, ok: np.ndarray):
    xz = np.where(ok[:, None], x, 0.0)
    yz = np.where(ok, y, 0.0)
    cxx = np.cumsum(xz[:, :, None] * xz[:, None, :], axis=0)
    cxy = np.cumsum(xz * yz[:, None], axis=0)
    return cxx, cxy, np.cumsum(ok)


def _design(asset: Asset, cols: list, h: int):
    """定数項つきの計画行列、目的変数（S3 で標準化した先 h 日リターン）、有効行。"""
    n = len(asset.close)
    x = np.column_stack([np.ones(n)] + [asset.F[c].to_numpy(dtype=float) for c in cols]) if cols else np.ones((n, 1))
    y = (asset.R[h] - h * asset.mbar) / asset.sig[h]["S3"]
    ok = np.isfinite(x).all(axis=1) & np.isfinite(y)
    return x, y, ok


def walk_forward(asset: Asset, cfg: Config, panel: tuple = ()) -> dict:
    """ウォークフォワードの実行。戻り値 {h: 結果の辞書}。

    panel に他銘柄の Asset を渡すと、傾き（T1〜T3）の回帰をプールして推定する
    （各銘柄の行は、結果の確定日が現在の日付以前のものだけを使う）。
    """
    taus = st.tau_grid(cfg.q)
    n = len(asset.close)
    out = {}
    tilt_names = [m for m in ("T1", "T2", "T3", "X1") if asset.sets.get(m)]
    sup_cols = list(dict.fromkeys(sum((asset.sets[m] for m in tilt_names), [])))
    pool_cols = [c for c in sup_cols if not any(c.startswith(a + "_") for a in asset.aux_names)]
    for h in cfg.horizons:
        R = asset.R[h]
        s = asset.sig[h]
        drift = h * asset.mbar                                  # 過去平均による h 日ぶんの傾き（時点 t で確定）
        z = {m: (R - drift) / s[m] for m in ("S1", "S2", "S3")}
        s3 = s["S3"]
        fin = np.flatnonzero(np.isfinite(s3) & np.isfinite(s["S1"]))
        if len(fin) == 0 or fin[0] + h >= n:
            continue
        start = max(cfg.burn, int(fin[0]) + h + 50)
        if start >= n:
            continue
        # --- 傾き用の正規方程式（累積） ---
        x_sup, y3, ok_sup = _design(asset, sup_cols, h)
        cxx, cxy, cnt = _cum_normal_eq(x_sup, y3, ok_sup)
        col_idx = {m: [0] + [1 + sup_cols.index(c) for c in asset.sets[m]] for m in tilt_names}
        pool_idx = [0] + [1 + sup_cols.index(c) for c in pool_cols]
        pan = []
        for a in panel:
            if not all(c in a.F.columns for c in pool_cols):
                continue
            xa, ya, oka = _design(a, pool_cols, h)
            cxa, cya, _ = _cum_normal_eq(xa, ya, oka)
            known = a.dates[h:]                      # 行 t の結果が確定する日付（t = 0..n_a-h-1）
            pan.append((cxa, cya, known))
        lam = h / (cfg.tau0 ** 2)
        # --- 類似局面用 ---
        kx = asset.F[asset.knn_cols].to_numpy(dtype=float) if asset.knn_cols else np.empty((n, 0))
        ok_k = np.isfinite(kx).all(axis=1) & np.isfinite(z["S3"]) if asset.knn_cols else np.zeros(n, bool)
        k_rows = np.flatnonzero(ok_k)
        kx_c, kz_c = kx[k_rows], z["S3"][k_rows]
        # --- 経験分布のバッファ ---
        bufs = {"B0": SortedBuf(n), "B1": SortedBuf(n), "V2": SortedBuf(n), "V3": SortedBuf(n)}
        src = {"B0": R, "B1": z["S1"], "V2": z["S2"], "V3": z["S3"]}
        mhz, mlz = asset.MH[h] / s3, asset.ML[h] / s3
        tb = {"MHz": SortedBuf(n), "MLz": SortedBuf(n), "MH": SortedBuf(n), "ML": SortedBuf(n)}
        tsrc = {"MHz": mhz, "MLz": mlz, "MH": asset.MH[h], "ML": asset.ML[h]}
        tilt = {m: {"beta": None, "buf": SortedBuf(n)} for m in tilt_names}
        models = ["B0", "B1", "V2", "V3"] + tilt_names + (["K1"] if asset.knn_cols else [])
        if "T3" in tilt_names and asset.knn_cols:
            models.append("E1")
        crps = {m: np.full(n, np.nan) for m in models}
        pit = {m: np.full(n, np.nan) for m in models}
        pup = {m: np.full(n, np.nan) for m in models}
        mu_rec = {m: np.full(n, np.nan) for m in tilt_names}
        knn_dist = np.full(n, np.nan)
        touch = {(k, b): np.full(n, np.nan) for k in ("up", "dn", "up0", "dn0", "up_hit", "dn_hit") for b in cfg.touch_b}
        recorded = {}
        final = {}
        elig0 = start - h
        for k in bufs:
            bufs[k].bulk(src[k][: elig0 + 1])
        for k in tb:
            tb[k].bulk(tsrc[k][: elig0 + 1])
        for T in range(start, n):
            last = T - h
            if T > start:
                for k in bufs:
                    bufs[k].add(src[k][last])
                for k in tb:
                    tb[k].add(tsrc[k][last])
                for m in tilt_names:
                    b = tilt[m]["beta"]
                    if b is not None and ok_sup[last]:
                        tilt[m]["buf"].add(y3[last] - float(x_sup[last, col_idx[m]] @ b))
            if (T - start) % cfg.refit == 0 and cnt[last] >= cfg.min_fit:
                for m in tilt_names:
                    ci = col_idx[m]
                    axx = cxx[last][np.ix_(ci, ci)].copy()
                    axy = cxy[last][ci].copy()
                    if m != "X1":
                        for cxa, cya, known in pan:
                            j = int(np.searchsorted(known, asset.dates[T], side="right")) - 1
                            if j >= 0:
                                pi = [pool_idx.index(i) for i in ci]
                                axx += cxa[j][np.ix_(pi, pi)]
                                axy += cya[j][pi]
                    pen = lam * np.eye(len(ci))
                    pen[0, 0] = 0.0
                    try:
                        beta = np.linalg.solve(axx + pen, axy)
                    except np.linalg.LinAlgError:
                        beta = None
                    tilt[m]["beta"] = beta
                    if beta is not None:
                        rows = ok_sup[: last + 1]
                        tilt[m]["buf"].bulk(y3[: last + 1][rows] - x_sup[: last + 1][rows][:, ci] @ beta)
            # --- 各モデルの分位点格子 ---
            grids = {}
            pt = {k: (st.predictive_taus(taus, cfg.overlap_eff * bufs[k].n / h) if cfg.finite_sample else taus) for k in bufs}
            grids["B0"] = st.sorted_quantiles(bufs["B0"].view(), pt["B0"])
            zq3 = st.sorted_quantiles(bufs["V3"].view(), pt["V3"])
            grids["B1"] = drift[T] + s["S1"][T] * st.sorted_quantiles(bufs["B1"].view(), pt["B1"])
            grids["V2"] = drift[T] + s["S2"][T] * st.sorted_quantiles(bufs["V2"].view(), pt["V2"])
            grids["V3"] = drift[T] + s3[T] * zq3
            for m in tilt_names:
                b = tilt[m]["beta"]
                xr = x_sup[T, col_idx[m]]
                if b is None or not np.isfinite(xr).all() or tilt[m]["buf"].n < cfg.min_fit:
                    grids[m] = np.full(cfg.q, np.nan)
                else:
                    mu = float(xr @ b)
                    mu_rec[m][T] = mu
                    tm = st.predictive_taus(taus, cfg.overlap_eff * tilt[m]["buf"].n / h) if cfg.finite_sample else taus
                    grids[m] = drift[T] + s3[T] * (mu + st.sorted_quantiles(tilt[m]["buf"].view(), tm))
            nb_info = None
            if asset.knn_cols:
                mcount = int(np.searchsorted(k_rows, last, side="right"))
                if mcount >= cfg.knn_min and np.isfinite(kx[T]).all() and np.isfinite(s3[T]):
                    d2 = ((kx_c[:mcount] - kx[T]) ** 2).sum(axis=1)
                    kk = min(cfg.knn_k, mcount - 1)
                    nb = np.argpartition(d2, kk)[:kk]
                    zn = np.sort(kz_c[nb])
                    knn_dist[T] = float(np.sqrt(d2[nb]).mean())
                    rows_nb = np.sort(k_rows[nb])
                    n_clu = 1 + int((np.diff(rows_nb) > h).sum())          # 時間的に離れた近傍のかたまりの数
                    tn = st.predictive_taus(taus, n_clu) if cfg.finite_sample else taus
                    grids["K1"] = drift[T] + s3[T] * (cfg.knn_blend * st.sorted_quantiles(zn, tn) + (1 - cfg.knn_blend) * zq3)
                    nb_info = (k_rows[nb], np.sqrt(d2[nb]))
                else:
                    grids["K1"] = np.full(cfg.q, np.nan)
            if "E1" in models:
                grids["E1"] = (grids["V3"] + grids["T3"] + grids["K1"]) / 3.0
            # --- 採点 ---
            if last >= 0 and T + h < n and (T - start) % cfg.step == 0 and np.isfinite(R[T]):
                y = R[T]
                for m in models:
                    g = grids[m]
                    if np.isfinite(g).all():
                        crps[m][T] = st.crps_from_grid(y, g, taus)
                        pit[m][T] = st.cdf_from_grid(y, g, taus)
                        pup[m][T] = 1.0 - st.cdf_from_grid(0.0, g, taus)
                if np.isfinite(s3[T]):
                    for b in cfg.touch_b:
                        touch[("up", b)][T] = tb["MHz"].frac_ge(b)
                        touch[("dn", b)][T] = tb["MLz"].frac_le(-b)
                        touch[("up0", b)][T] = tb["MH"].frac_ge(b * s3[T])
                        touch[("dn0", b)][T] = tb["ML"].frac_le(-b * s3[T])
                        touch[("up_hit", b)][T] = float(mhz[T] >= b)
                        touch[("dn_hit", b)][T] = float(mlz[T] <= -b)
            if T in cfg.record_at:
                recorded[T] = {m: g.copy() for m, g in grids.items()}
            if T == n - 1:
                final = {
                    "grids": {m: g.copy() for m, g in grids.items()},
                    "sigma": {m: float(s[m][T]) for m in ("S1", "S2", "S3")},
                    "drift": float(drift[T]),
                    "beta": {m: (None if tilt[m]["beta"] is None else tilt[m]["beta"].copy()) for m in tilt_names},
                    "mu": {m: float(mu_rec[m][T]) for m in tilt_names},
                    "features": {m: list(asset.sets[m]) for m in tilt_names},
                    "neighbors": nb_info,
                    "touch_sorted": {k: tb[k].view().copy() for k in tb},
                    "z_sorted": bufs["V3"].view().copy(),
                    "n_eligible": bufs["V3"].n,
                }
        out[h] = {"h": h, "start": start, "models": models, "taus": taus, "crps": crps, "pit": pit, "pup": pup,
                  "scale": s["S1"], "drift": drift,
                  "R": R, "s3": s3, "mu": mu_rec, "knn_dist": knn_dist, "touch": touch, "recorded": recorded,
                  "final": final, "dates": asset.dates, "step": cfg.step}
    return out
