"""予測レポート（Markdown）と図の出力。図のラベルは CJK フォント非依存にするため英語。"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from chartlib import indicators as ind

from .evaluate import ADOPT_P
from .eventstudy import EVENT_Q
from .features import SIGNAL_LABELS
from .walkforward import MODEL_LABELS

__all__ = ["build_report", "plot_fan", "plot_calibration", "HORIZON_LABEL"]

HORIZON_LABEL = {5: "1週間（5営業日）", 21: "1か月（21営業日）", 63: "3か月（63営業日）"}


def _yen(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return f"{x:,.0f}" if x >= 1000 else (f"{x:,.1f}" if x >= 100 else f"{x:,.2f}")


def _pct(x: float, d: int = 1, sign: bool = False) -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return f"{100 * x:+.{d}f}%" if sign else f"{100 * x:.{d}f}%"


def _p(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return "<0.001" if x < 0.001 else f"{x:.3f}"


def _hl(h: int) -> str:
    return HORIZON_LABEL.get(h, f"{h}営業日")


def _state_lines(asset, wf) -> list:
    df = asset.df
    c = df["close"]
    c0 = float(c.iloc[-1])
    out = []
    rsi = float(ind.rsi(c, 14).iloc[-1])
    k25 = float(c0 / ind.sma(c, 25).iloc[-1] - 1.0)
    hi52 = float(c0 / c.rolling(252).max().iloc[-1] - 1.0)
    r5 = float(c0 / c.iloc[-6] - 1.0) if len(c) > 6 else float("nan")
    r21 = float(c0 / c.iloc[-22] - 1.0) if len(c) > 22 else float("nan")
    out.append(f"- 直近の値動き: 5日 {_pct(r5, 1, True)}、21日 {_pct(r21, 1, True)}。RSI(14) は {rsi:.0f}、25日線からの乖離率は {_pct(k25, 1, True)}、"
               f"52週高値（終値）からは {_pct(hi52, 1, True)}。")
    if 21 in wf and wf[21]["final"]:
        s3 = wf[21]["s3"]
        hist = s3[np.isfinite(s3)]
        now = wf[21]["final"]["sigma"]["S3"]                 # 状態の説明には、どの採用モデルでも S3（結合）を使う
        pctl = float((hist < now).mean())
        ann = now / math.sqrt(21) * math.sqrt(250)
        out.append(f"- 予測ボラティリティ（1か月先まで、年率換算）は {_pct(ann, 0)}。この銘柄の過去の予測値の中で下から {_pct(pctl, 0)} の位置（100% に近いほど荒い局面）。")
    return out


def build_report(name: str, asset, validation: dict, wf: dict, summary: dict, decisions: dict, touch: pd.DataFrame,
                 events: pd.DataFrame, fc: dict, cfg, meta: dict, scenarios: list | None = None,
                 images: dict | None = None, panel: dict | None = None, volsum: pd.DataFrame | None = None,
                 cond: dict | None = None) -> str:
    L = []
    c0 = fc["last_close"]
    L.append(f"# {name} — 日足による確率予測（基準日 {fc['asof']}）")
    L.append("")
    L.append("> 日足（始値・高値・安値・終値・出来高）だけから作った確率予測と、その作り方を同じ銘柄の過去で採点した結果である。"
             "手順は事前に固定してある（`09_forecasting/02_protocol.md`）。教育目的であり、投資助言ではない。")
    L.append("")
    L.append("## 1. 結論")
    L.append("")
    L.append(f"基準日 {fc['asof']} の終値は {_yen(c0)} 円。")
    L.append("")
    L.append("| 期間 | 中央値 | 50% 区間（25〜75%） | 80% 区間（10〜90%） | 上昇確率 | 採用モデル |")
    L.append("|---|---:|---|---|---:|---|")
    for h, hz in fc["horizons"].items():
        q = {round(x["p"], 2): x for x in hz["quantiles"]}
        L.append(f"| {_hl(h)} | {_yen(q[0.5]['price'])} | {_yen(q[0.25]['price'])}〜{_yen(q[0.75]['price'])} | "
                 f"{_yen(q[0.1]['price'])}〜{_yen(q[0.9]['price'])} | {_pct(hz['p_up'], 0)} | {hz['model']}（{MODEL_LABELS.get(hz['model'], '')}） |")
    L.append("")
    tilt_any = [h for h, d in decisions.items() if d.get("adopted_tilt")]
    if tilt_any:
        L.append("- **方向の手がかり**: " + "、".join(f"{_hl(h)}で {decisions[h]['adopted_tilt']}" for h in tilt_any)
                 + " が採用基準を満たした。上昇確率と中央値にその傾きが入っている（効果の大きさは 5 節）。")
    else:
        L.append("- **方向の手がかり**: 採用基準（多重検定の補正後も、検証期間の前半・後半の両方で改善）を満たす方向の予測材料は、"
                 "この銘柄の履歴からは見つからなかった。上昇確率は、過去の平均的な傾きだけを反映している。**この表が示すのは主に「値幅」である。**")
    for h, d in decisions.items():
        if h in summary and len(summary[h]):
            sm_ = d.get("sigma_model")
            s = summary[h].loc[sm_]
            if sm_ == "B0":
                L.append(f"- {_hl(h)}の値幅: この銘柄の履歴では、直近のボラティリティに合わせて幅を伸縮しても予測は良くならなかった。"
                         f"過去のリターンの分布をそのまま使う（検証 {int(s['n'])} 時点。80% 区間の的中率は {_pct(s['cov80'], 0)}）。")
            else:
                L.append(f"- {_hl(h)}の値幅: 直近のボラティリティに合わせて伸縮する方式（{sm_}）は、伸縮しない基準（B0）に比べて CRPS を {_pct(s['skill_vs_B0'], 1)} 改善した"
                         f"（検証 {int(s['n'])} 時点。80% 区間の的中率は {_pct(s['cov80'], 0)}）。")
    L.extend(_state_lines(asset, wf))
    for h, hz in fc["horizons"].items():
        if "analog_distance_pct" in hz and hz["analog_distance_pct"] > 0.95:
            L.append(f"- **注意**: 現在の局面は、過去に似た例が少ない（類似度の距離が検証期間の上位 {_pct(1 - hz['analog_distance_pct'], 0)}）。"
                     "過去の分布をそのまま当てはめる前提が弱く、実際の幅はここに示す区間より広い可能性がある。")
            break
    L.append("")
    L.append("## 2. データの検査")
    L.append("")
    for k, title in (("errors", "エラー"), ("warnings", "注意"), ("info", "情報")):
        for msg in validation.get(k, []):
            L.append(f"- {title}: {msg}")
    for s in validation.get("suspect_splits", []):
        f = f"分割・併合の倍率 {s['factor']:g} の未調整に近い" if s.get("factor") else "倍率は特定できない"
        L.append(f"- 要確認: {s['date']} の前日比 {s['ratio']:.3f}（{f}）")
    if meta.get("splits_applied"):
        L.append(f"- 適用した分割調整: {meta['splits_applied']}")
    L.append("")
    L.append("## 3. 予測分布")
    for h, hz in fc["horizons"].items():
        L.append("")
        L.append(f"### {_hl(h)}")
        L.append("")
        if hz["model"] == "B0":
            L.append(f"採用モデルは B0（伸縮なし）で、過去 {hz['n_eligible']:,} 時点の {h} 営業日リターンの分布をそのまま使う。"
                     f"参考: 直近のボラティリティから見た標準偏差の予測は、S1（EWMA）{_pct(hz['sigma_h_s1'], 1)}、S2（HAR 型）{_pct(hz['sigma_h_s2'], 1)}、S3（結合）{_pct(hz['sigma_h_s3'], 1)}。")
        else:
            L.append(f"予測の標準偏差は {_pct(hz['sigma_h'], 1)}（{hz['sigma_model']}）。参考: S1（EWMA）{_pct(hz['sigma_h_s1'], 1)}、S2（HAR 型）{_pct(hz['sigma_h_s2'], 1)}、S3（結合）{_pct(hz['sigma_h_s3'], 1)}。"
                     f"過去平均による傾きは {_pct(math.expm1(hz.get('drift_h', 0.0)), 2, True)}。標本は過去 {hz['n_eligible']:,} 時点。")
        L.append("")
        L.append("| 確率 | " + " | ".join(f"{int(round(100 * x['p']))}%" for x in hz["quantiles"]) + " |")
        L.append("|---|" + "---:|" * len(hz["quantiles"]))
        L.append("| 終値 | " + " | ".join(_yen(x["price"]) for x in hz["quantiles"]) + " |")
        L.append("| 変化率 | " + " | ".join(_pct(x["ret"], 1, True) for x in hz["quantiles"]) + " |")
        L.append("")
        L.append("| 終値の変化 | " + " | ".join(f"+{int(100 * t['pct'])}% 以上" for t in hz["thresholds"]) + " | "
                 + " | ".join(f"−{int(100 * t['pct'])}% 以下" for t in hz["thresholds"]) + " |")
        L.append("|---|" + "---:|" * (2 * len(hz["thresholds"])))
        L.append("| 確率 | " + " | ".join(_pct(t["p_ge"], 0) for t in hz["thresholds"]) + " | "
                 + " | ".join(_pct(t["p_le"], 0) for t in hz["thresholds"]) + " |")
        if hz.get("period_high"):
            ph = {x["p"]: x["price"] for x in hz["period_high"]}
            pl = {x["p"]: x["price"] for x in hz["period_low"]}
            L.append("")
            L.append(f"期間中の高値は中央値 {_yen(ph[0.5])} 円（25〜75%: {_yen(ph[0.25])}〜{_yen(ph[0.75])}）、"
                     f"安値は中央値 {_yen(pl[0.5])} 円（25〜75%: {_yen(pl[0.25])}〜{_yen(pl[0.75])}）。")
        if hz.get("levels"):
            L.append("")
            L.append("| 水準 | 価格 | 現値比 | 期間中に届く確率 | 期間末の終値が上にある確率 |")
            L.append("|---|---:|---:|---:|---:|")
            for r in sorted(hz["levels"], key=lambda r: -r["price"]):
                L.append(f"| {r['name']} | {_yen(r['price'])} | {_pct(r['dist'], 1, True)} | {_pct(r['p_touch'], 0)} | {_pct(r['p_close_above'], 0)} |")
    if scenarios:
        L.append("")
        L.append("## 4. シナリオ区間に入る確率")
        L.append("")
        L.append("以前に主観で付けた重みと、今回の予測分布から求めた「期間末の終値がその区間に入る確率」を並べる。"
                 "基準日が異なるため同じ条件の比較ではなく、更新である。")
        L.append("")
        L.append("| 期間 | シナリオ | 区間（円） | 以前の重み | 今回の確率 |")
        L.append("|---|---|---|---:|---:|")
        for s in scenarios:
            lo = "—" if s.get("lo") is None else _yen(s["lo"])
            hi = "—" if s.get("hi") is None else _yen(s["hi"])
            w = "—" if s.get("weight") is None else _pct(s["weight"], 0)
            L.append(f"| {_hl(s['h'])} | {s['name']} | {lo}〜{hi} | {w} | {_pct(s['prob'], 0)} |")
    L.append("")
    L.append("## 5. 検証（ウォークフォワード）")
    L.append("")
    if panel:
        L.append(f"傾きの推定と採否の判定には、次の {len(panel['names'])} 銘柄も使った（プール推定とパネル判定）: " + "、".join(panel["names"]) + "。"
                 "下の成績表はこの銘柄だけの成績で、判定は全銘柄の平均損失による。")
        L.append("")
    L.append("各時点で、その時点までの情報だけを使って予測分布を作り、実際の結果で採点した。CRPS は分布全体の当たり具合で、小さいほど良い。"
             "「B1 比」は EWMA 伸縮の基準に対する改善率、p は「B1 より良くない」を帰無仮説とする片側検定である。"
             "「尺度調整後」は、各時点の CRPS をその時点の EWMA の σ で割ってから平均したもので、値動きの荒い時期だけで成績が決まらないようにした見方である。")
    for h, t in summary.items():
        if not len(t):
            continue
        d = decisions[h]
        L.append("")
        L.append(f"### {_hl(h)}（検証 {t.attrs.get('first')}〜{t.attrs.get('last')}、{int(t['n'].iloc[0]):,} 時点、上昇した割合 {_pct(t.attrs.get('up_rate', float('nan')), 0)}）")
        L.append("")
        L.append("| モデル | CRPS | B1 比 | p | 尺度調整後の B1 比 | 50% 区間の的中率 | 80% | 90% | 上昇確率の Brier | 前半の B1 比 | 後半の B1 比 |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for m, r in t.iterrows():
            L.append(f"| {m} {MODEL_LABELS.get(m, '')} | {r['crps']:.5f} | {_pct(r['skill_vs_B1'], 2, True)} | {_p(r['dm_p_vs_B1'])} | {_pct(r['sskill_vs_B1'], 2, True)} | "
                     f"{_pct(r['cov50'], 0)} | {_pct(r['cov80'], 0)} | {_pct(r['cov90'], 0)} | {r['brier_up']:.4f} | "
                     f"{_pct(r['skill_h1'], 2, True)} | {_pct(r['skill_h2'], 2, True)} |")
        L.append("")
        who = f"判定（{d['n_assets']} 銘柄をまとめた平均損失による）" if d.get("n_assets") else "判定"
        line = f"{who}: 幅は {d['sigma_model']}、最終は **{d['final_model']}**。"
        if "best_candidate" in d:
            line += (f" 傾き・類似局面の候補 {d['n_candidates']} 個のうち最良は {d['best_candidate']}（幅のモデル比 {_pct(d['best_skill'], 2, True)}、"
                     f"Reality Check p={_p(d['rc_p'])}、DM p={_p(d['dm_p'])}、ブートストラップ p={_p(d['boot_p'])}）。")
        L.append(line + " " + d.get("reason", ""))
        if panel and h in panel.get("single", {}):
            ds = panel["single"][h]
            L.append("")
            L.append(f"参考（この銘柄だけでの判定）: 最終は {ds['final_model']}。{ds.get('reason', '')}")
    if volsum is not None and len(volsum):
        L.append("")
        L.append("### ボラティリティ予測の検証")
        L.append("")
        L.append("先 h 日の実現分散に対する QLIKE 損失（小さいほど良い）。「長期平均」は、ボラティリティが変わらないとみなす基準である。")
        L.append("")
        L.append("| 期間 | 時点数 | 長期平均 | S1（EWMA） | S2（HAR 型） | S3（結合） |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for _, r in volsum.iterrows():
            L.append(f"| {_hl(int(r['h']))} | {int(r['n']):,} | {r['長期平均']:.4f} | {r['S1']:.4f} | {r['S2']:.4f} | {r['S3']:.4f} |")
    if len(touch):
        L.append("")
        L.append("### 水準に届く確率の検証")
        L.append("")
        L.append("期間中の高値（安値）が、現値から σ の b 倍だけ上（下）に届くかを予測し、Brier スコアで採点した。基準は、σ で標準化しない過去の実績である。")
        L.append("")
        L.append("| 期間 | 向き | b | 予測確率の平均 | 実際に届いた割合 | Brier | 基準の Brier | 改善率 |")
        L.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for _, r in touch.iterrows():
            L.append(f"| {_hl(int(r['h']))} | {'上' if r['side'] == 'up' else '下'} | {r['b']:.1f} | {_pct(r['mean_prob'], 0)} | {_pct(r['hit_rate'], 0)} | "
                     f"{r['brier']:.4f} | {r['brier_base']:.4f} | {_pct(r['brier_skill'], 1, True)} |")
    L.append("")
    L.append("## 6. チャートシグナルの検証（イベントスタディ）")
    L.append("")
    L.append("資料集の手法を機械的な規則にした 41 個のシグナルについて、点灯した日の後の値動きを、この銘柄の全履歴で調べた。"
             "「平均の差」は、ボラティリティで標準化したリターンの、点灯日とそれ以外の差（σ 単位）である。q は、多数を同時に調べたことを補正した値で、"
             f"**q < {EVENT_Q:.2f} のものだけが偶然と区別できる**。全期間を使った記述統計で、将来の保証ではない。")
    if len(events):
        ev = events.copy()
        now = ev[ev["now"]]
        L.append("")
        L.append("### 現在点灯しているシグナル")
        L.append("")
        if len(now):
            L.append("| シグナル | 期間 | 点灯日数 | かたまり数 | 平均の差（σ） | 概算の変化率 | t | q | 点灯後に上昇した割合（他の日） | ばらつきの比 | q（ばらつき） |")
            L.append("|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|")
            for _, r in now.sort_values(["signal", "h"]).iterrows():
                if not np.isfinite(r["b"]):
                    L.append(f"| {r['label']} | {_hl(int(r['h']))} | {int(r['n_days'])} | {int(r['episodes'])} | 標本不足 | — | — | — | — | — | — |")
                    continue
                L.append(f"| {r['label']} | {_hl(int(r['h']))} | {int(r['n_days'])} | {int(r['episodes'])} | {r['b']:+.2f} | {r['pct']:+.1f}% | {r['t_b']:+.1f} | {_p(r['q_b'])} | "
                         f"{_pct(r['hit_sig'], 0)}（{_pct(r['hit_other'], 0)}） | {r['var_ratio']:.2f} | {_p(r['q_c'])} |")
        else:
            L.append("現在点灯しているシグナルはない。")
        sig = ev[(ev["q_b"] < EVENT_Q)]
        L.append("")
        L.append(f"### 補正後も残ったシグナル（平均への効果、q < {EVENT_Q:.2f}）")
        L.append("")
        if len(sig):
            L.append("| シグナル | 期間 | 点灯日数 | かたまり数 | 平均の差（σ） | 概算の変化率 | t | q | 現在 |")
            L.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
            for _, r in sig.sort_values("q_b").iterrows():
                L.append(f"| {r['label']} | {_hl(int(r['h']))} | {int(r['n_days'])} | {int(r['episodes'])} | {r['b']:+.2f} | {r['pct']:+.1f}% | {r['t_b']:+.1f} | {_p(r['q_b'])} | {'点灯' if r['now'] else '—'} |")
        else:
            tested = int(np.isfinite(ev["p_b"]).sum())
            L.append(f"なし（検定した {tested} 通りのうち、補正後に残ったものはない）。")
        vs = ev[(ev["q_c"] < EVENT_Q)]
        if len(vs):
            L.append("")
            L.append(f"### 点灯後に値幅の予測がずれるシグナル（ばらつきへの効果、q < {EVENT_Q:.2f}、参考）")
            L.append("")
            L.append("ばらつきの比が 1 より大きいと、点灯後は予測より値幅が広がりやすく、1 より小さいと狭くなりやすい。"
                     "この検定は、予測できる成分のない合成データでも約 4 系列に 1 系列で何かを検出した（ボラティリティ予測の近似誤差を拾うため）。"
                     "方向の手がかりではなく、値幅の予測の注意書きとして読む。")
            L.append("")
            L.append("| シグナル | 期間 | 点灯日数 | ばらつきの比 | t | q | 現在 |")
            L.append("|---|---|---:|---:|---:|---:|---|")
            for _, r in vs.sort_values("q_c").head(25).iterrows():
                L.append(f"| {r['label']} | {_hl(int(r['h']))} | {int(r['n_days'])} | {r['var_ratio']:.2f} | {r['t_c']:+.1f} | {_p(r['q_c'])} | {'点灯' if r['now'] else '—'} |")
    if cond:
        L.append("")
        L.append("### 補助系列との連動（条件つきの見方。予測ではない）")
        L.append("")
        L.append("直近 750 営業日の、重ならない 5 営業日リターンどうしの回帰。「補助系列が x% 動いたとき、この銘柄は平均して β×x% 動いた」という関係で、"
                 "同じ期間の連動であり、補助系列の動きから先を当てるものではない。")
        L.append("")
        L.append("| 補助系列 | β | 標準誤差 | R² | 標本数 | 補助系列 −5% のとき | +5% のとき |")
        L.append("|---|---:|---:|---:|---:|---:|---:|")
        for nm, c in cond.items():
            if not np.isfinite(c.get("beta", float("nan"))):
                L.append(f"| {nm} | — | — | — | {c.get('n', 0)} | — | — |")
                continue
            L.append(f"| {nm} | {c['beta']:.2f} | {c['se']:.2f} | {c['r2']:.2f} | {c['n']} | {_pct(-0.05 * c['beta'], 1, True)} | {_pct(0.05 * c['beta'], 1, True)} |")
    if fc.get("analogs"):
        L.append("")
        L.append("## 7. 過去の似た局面")
        L.append("")
        L.append("直近の値動き・52週高値からの距離・ボラティリティと出来高の状態が近かった過去の日（互いに 10 営業日以上離したもの）と、その後の変化率。"
                 "かっこ内は、当時と現在のボラティリティの違いを補正した値。例示であり、件数が少ないので、これだけで判断しない。")
        L.append("")
        hs = list(fc["horizons"].keys())
        L.append("| 日付 | 距離 | 当時の終値 | " + " | ".join(f"{_hl(h)}後" for h in hs) + " |")
        L.append("|---|---:|---:|" + "---|" * len(hs))
        for a in fc["analogs"]:
            cells = []
            for h in hs:
                r, sc = a.get(f"ret_{h}"), a.get(f"scaled_{h}")
                cells.append("—" if r is None else f"{_pct(r, 1, True)}（{_pct(sc, 1, True)}）")
            L.append(f"| {a['date']} | {a['distance']:.2f} | {_yen(a['close'])} | " + " | ".join(cells) + " |")
    if images:
        L.append("")
        L.append("## 図")
        L.append("")
        for title, path in images.items():
            L.append(f"![{title}]({path})")
            L.append("")
    L.append("")
    L.append("## 限界")
    L.append("")
    L.append("- 使ったのはこの銘柄の日足だけである。決算・為替・指数・材料は、過去の値動きに表れた分しか入っていない。次の決算などの予定された出来事は、過去の平均的な頻度でしか織り込んでいない。")
    L.append("- 予測分布は「過去の、ボラティリティで標準化した値動きの分布が今後も当てはまる」ことを前提にしている。過去に例の少ない局面では、この前提が弱い。")
    L.append("- 3か月先の検証は、重ならない期間で数えると標本が少ない（25 年で約 100 個）。差が小さいモデルの優劣は決められない。")
    L.append("- 検証は終値で取引コストを考えない採点であり、売買ルールの損益の検証ではない。")
    L.append("- 投資助言ではない。")
    L.append("")
    L.append("## 付録: 実行の記録")
    L.append("")
    for k, v in meta.items():
        L.append(f"- {k}: {v}")
    L.append(f"- 設定: 学習のみの期間 {cfg.burn} 日、推定し直し {cfg.refit} 日ごと、分位点格子 {cfg.q} 点、リッジの事前標準偏差 {cfg.tau0}、近傍 {cfg.knn_k} 件、採点の間隔 {cfg.step} 日")
    L.append("")
    return "\n".join(L)


def plot_fan(asset, fc: dict, path: Path, lookback: int = 250) -> None:
    """終値と予測区間の図（英語ラベル）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    c = asset.df["close"].iloc[-lookback:]
    x0 = len(c) - 1
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(len(c)), c.to_numpy(), color="#333333", lw=1.2, label="Close")
    hs = sorted(fc["horizons"].keys())
    xs = [x0] + [x0 + h for h in hs]
    c0 = fc["last_close"]

    def band(lo_p, hi_p, color, label):
        lo, hi = [c0], [c0]
        for h in hs:
            q = {round(v["p"], 2): v["price"] for v in fc["horizons"][h]["quantiles"]}
            lo.append(q[lo_p])
            hi.append(q[hi_p])
        ax.fill_between(xs, lo, hi, color=color, alpha=0.35, lw=0, label=label)

    band(0.05, 0.95, "#bbdefb", "5-95%")
    band(0.10, 0.90, "#90caf9", "10-90%")
    band(0.25, 0.75, "#42a5f5", "25-75%")
    med = [c0] + [{round(v["p"], 2): v["price"] for v in fc["horizons"][h]["quantiles"]}[0.5] for h in hs]
    ax.plot(xs, med, color="#0d47a1", lw=1.5, ls="--", label="Median")
    for h in hs:
        ax.axvline(x0 + h, color="#999999", lw=0.5, ls=":")
        ax.text(x0 + h, ax.get_ylim()[1], f"+{h}d", ha="center", va="bottom", fontsize=8)
    ax.set_title(f"Forecast intervals as of {fc['asof']} (trading days ahead)")
    ax.set_xlabel("Trading days (last 250 + forecast)")
    ax.set_ylabel("Price")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, ls=":", color="#cccccc")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_calibration(wf: dict, decisions: dict, path: Path) -> None:
    """PIT ヒストグラム（較正の確認。平らなら予測分布が実際の頻度と合っている）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hs = [h for h in wf if wf[h]["final"]]
    fig, axes = plt.subplots(1, len(hs), figsize=(4.2 * len(hs), 3.6), squeeze=False)
    for ax, h in zip(axes[0], hs):
        m = decisions[h]["final_model"]
        for name, color in (("B0", "#bdbdbd"), (m, "#1976d2")):
            p = wf[h]["pit"][name]
            p = p[np.isfinite(p)]
            if len(p):
                ax.hist(p, bins=10, range=(0, 1), density=True, histtype="step", color=color, lw=1.6, label=name)
        ax.axhline(1.0, color="#333333", lw=0.8, ls="--")
        ax.set_title(f"PIT histogram, h={h}d")
        ax.set_xlabel("PIT (flat = calibrated)")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
