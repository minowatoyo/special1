"""外側のウォークフォワード評価（改訂仕様 FIX-05）。

現行の採否ルール（evaluate.decide）は、モデルの選択と評価に同じ全期間の損失を使うので、選択後の成績は楽観的になる。
ここでは「内側で選択 → 固定 → 外側で評価」を、時間順に繰り返す。
  各ブロック k（外側）について、そのブロックの開始より前に結果が確定している時点（h 日ぶんの余白を空ける）の損失だけで
  evaluate._decide_from_losses を適用し、採用モデルを決める。そのモデルの、ブロック内の損失を外側の損失として並べる。
比較: 基準 B1・B0・（内側のルールを使わずに）全期間で選んだ場合の成績（楽観の大きさ）。
"""
from __future__ import annotations

import math

import numpy as np

from . import evaluate as ev
from . import stats as st

__all__ = ["outer_evaluate"]


def outer_evaluate(wf: dict, cfg, n_blocks: int = 8, min_train_frac: float = 0.4) -> dict:
    out = {}
    for h, res in wf.items():
        models = res["models"]
        ok = ev._common(res, models)
        n = int(ok.sum())
        if n < 200:
            out[h] = {"n": n, "note": "評価できる時点が少ない（200 未満）"}
            continue
        c = {m: res["crps"][m][ok] for m in models}
        scale = res["scale"][ok]
        step = res["step"]
        gap = math.ceil(h / step)                         # 結果が確定するまでの時点数（余白）
        start = max(60 + gap, int(min_train_frac * n))
        edges = np.linspace(start, n, n_blocks + 1).astype(int)
        sel_loss, base_b1, base_b0, labels = [], [], [], []
        for k in range(n_blocks):
            s, e = int(edges[k]), int(edges[k + 1])
            if e <= s:
                continue
            tr = slice(0, s - gap)
            ctr = {m: c[m][tr] for m in models}
            d = ev._decide_from_losses(ctr, models, h, step, ev._block(res), cfg, scale[tr])
            sel_loss.append(c[d["final_model"]][s:e])
            base_b1.append(c["B1"][s:e])
            base_b0.append(c["B0"][s:e])
            labels.append({"block": k, "train_n": s - gap, "test_n": e - s, "selected": d["final_model"], "sigma_model": d["sigma_model"],
                           "tilt": d["adopted_tilt"]})
        a, b1, b0 = (np.concatenate(x) for x in (sel_loss, base_b1, base_b0))
        full = ev._decide_from_losses(c, models, h, step, ev._block(res), cfg, scale)     # 同じデータで選んで評価（楽観）
        ins = c[full["final_model"]][int(edges[0]):]
        dm = st.dm_test(a, b1, h, step)
        out[h] = {"n_outer": int(len(a)), "crps_outer": float(a.mean()), "crps_B1": float(b1.mean()), "crps_B0": float(b0.mean()),
                  "skill_vs_B1": float(1 - a.mean() / b1.mean()), "skill_vs_B0": float(1 - a.mean() / b0.mean()),
                  "dm_p_vs_B1": float(dm["p"]), "insample_selected": full["final_model"],
                  "optimism(insample_skill - outer_skill)": float((1 - ins.mean() / b1.mean()) - (1 - a.mean() / b1.mean())),
                  "blocks": labels}
    return out
