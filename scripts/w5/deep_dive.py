"""深掘りレポート: 指定した 1 銘柄について、関門・検証済みの買い材料・基準率・中身・建玉・内側の見方を、1 つにまとめる。
仕様は docs/w5_protocol.md「深掘りレポート」（事前固定）。ローカル PC で実行。出力は、その銘柄の集計と区分だけ。

  python scripts/w5/deep_dive.py --code 7203          # 初回は、基準率の観測表を作るので 10 分ほど。2 回目からは数分
結果: results/deep/<コード>_<日付>.json と .md。記録は: python scripts/w5/watchlist.py add --code ... --dossier <json> --cause ... --view ... --type ... --check ... --exit ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_reference_code"))
sys.path.insert(0, str(ROOT / "scripts" / "jquants"))
sys.path.insert(0, str(Path(__file__).parent))
import forward_s2 as fs2  # noqa: E402
import run_selection as rs  # noqa: E402
import schema  # noqa: E402
import stock_profile as sp  # noqa: E402
from forecastlib.ledger import AppendOnlyLedger  # noqa: E402
from selectlib import atlas, deepdive, events, exclude, extremes  # noqa: E402

HS = (21, 63)
RECENT_DAYS = 7
BULL = ("buy", "overweight")
BEAR = ("sell", "underweight")


def _r(x, n=4):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


def _fmt(d):
    if isinstance(d, dict):
        return {k: _fmt(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_fmt(v) for v in d]
    if isinstance(d, float):
        return _r(d)
    return d


def obs_for(root: Path, P, iv, fins, mg, h: int, sha: str) -> dict:
    """基準率の観測表（広い母集団、21 営業日ごとの判断日）。データの指紋ごとに、手元に保存して、使い回す。"""
    d = root / "results" / "deep"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"_obs_{sha[:16]}_h{h}.npz"
    if f.exists():
        z = np.load(f)
        return {k: z[k] for k in z.files}
    elig = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=250, va_min=schema.WIDE_VA_MIN)
    prev = os.environ.get("JQ_EXEC")
    os.environ["JQ_EXEC"] = "open"                                   # 買える日の判定は、修正版（寄り付きの時点の情報だけ）
    try:
        arr = deepdive.obs_arrays(atlas.build_obs(P, elig, iv, fins, mg, P.rebalance_idx(), h))
    finally:
        if prev is None:
            os.environ.pop("JQ_EXEC", None)
        else:
            os.environ["JQ_EXEC"] = prev
    for old in d.glob(f"_obs_*_h{h}.npz"):
        old.unlink()
    np.savez_compressed(f, **arr)
    return arr


def s2_status(root: Path, code: str) -> dict:
    rows = [r["payload"] for r in AppendOnlyLedger(root / "ledger" / "forward_s2.jsonl")._rows() if r["type"] == "s2_record"]
    if not rows:
        return {"candidate": False, "note": "S2 の前向きの記録が、まだない"}
    last = max(r["asof"] for r in rows)
    out = {"candidate": False, "record_asof": last}
    for r in [r for r in rows if r["asof"] == last]:
        g = {c: (y, t) for c, y, t in r["group"]}
        if code in g:
            ys = np.array([y for _, y, _ in r["group"]])
            rank = float((ys < g[code][0]).mean())
            out.update({"in_rights_month": r["rights_month"], "est_entry_day": r["est_entry_day"], "forecast_div_yield": _r(g[code][0]), "yield_rank_in_group": _r(rank, 2),
                        "tier": "ABC"[g[code][1]], "candidate": bool(rank >= 0.8),
                        "note": "確認期間で残ったのは、段階 B。買いは、権利付き最終日の 40 営業日前の始値、売りは、最終日の始値"})
            break
    return out


def sel_status(root: Path, code: str) -> dict:
    rows = [r["payload"] for r in AppendOnlyLedger(root / "ledger" / "forward.jsonl")._rows() if r["type"] == "selection" and r["payload"]["model"] == "SEL-C1"]
    if not rows:
        return {"in_universe": False, "note": "順位予測の前向きの記録が、まだない"}
    r = max(rows, key=lambda x: x["asof"])
    order = [c for c, _ in sorted(r["scores"], key=lambda x: -x[1])]
    if code not in order:
        return {"in_universe": False, "record_asof": r["asof"], "note": "順位予測の母集団（売買代金 5 億円以上など）に、入っていない"}
    k = order.index(code) + 1
    return {"in_universe": True, "record_asof": r["asof"], "rank": k, "of": len(order), "top15": bool(k <= 15),
            "note": "順位を当てる力はある（順位相関 0.04〜0.06）が、100 株単位とコストで、売買では、ほぼ消える"}


def inside_view(root: Path, code: str, asof: pd.Timestamp) -> dict:
    import lens_log
    out = {"lens": {}, "agents": None}
    lo = asof - timedelta(days=RECENT_DAYS)
    for r in AppendOnlyLedger(root / "ledger" / "lens.jsonl")._rows():
        p = r["payload"]
        if r["type"] != "lens_signal" or p.get("jq_code") != code:
            continue
        d = lens_log.jst_date(p["time"])
        if d is None or d < lo:
            continue
        cls = lens_log.tf_class(p["timeframe"])
        if cls not in out["lens"] or str(p["time"]) > str(out["lens"][cls]["time"]):
            out["lens"][cls] = {"decision": p["decision"], "confidence": p.get("confidence"), "timeframe": p["timeframe"], "time": p["time"], "check": p.get("check")}
    runs = [r["payload"] for r in AppendOnlyLedger(root / "ledger" / "agents.jsonl")._rows() if r["type"] == "agents_run" and r["payload"].get("jq_code") == code
            and pd.Timestamp(r["payload"]["trade_date"]) >= lo]
    if runs:
        a = max(runs, key=lambda x: x["trade_date"])
        out["agents"] = {"rating": a["rating"], "group": a["group"], "trade_date": a["trade_date"], "backfill": a["backfill"], "excerpt": (a.get("decision_excerpt") or "")[:300]}
    return out


def disagreements(gate: dict, outside: dict, inside: dict, s2: dict) -> list:
    out = []
    bull_agents = bool(inside["agents"]) and inside["agents"]["group"] == "bullish"
    bear_agents = bool(inside["agents"]) and inside["agents"]["group"] == "bearish"
    lens_long = [k for k, v in inside["lens"].items() if v["decision"] == "LONG"]
    if gate["verdict"].startswith("回避") and (bull_agents or lens_long):
        out.append("関門は「回避」だが、" + ("エージェントは強気" if bull_agents else "") + ("・" if bull_agents and lens_long else "") + ("Lens は LONG" if lens_long else "") + "。関門を優先する")
    if gate["verdict"].startswith("回避") and s2.get("candidate"):
        out.append("S2 の候補だが、関門は「回避」。買いの日（権利付き最終日の 40 営業日前）までに、極端な動きから 5 営業日以上あくかを見る")
    ch = [c for c in outside["h=21"]["chain"] if c.get("mean") is not None]
    if ch and ch[-1]["mean"] < 0 and (bull_agents or lens_long):
        out.append(f"基準率（同じ状態の観測の、その後 21 日）は {ch[-1]['mean']:+.2%} で負だが、内側の見方は強気")
    if ch and ch[-1]["mean"] > 0 and bear_agents:
        out.append(f"基準率は {ch[-1]['mean']:+.2%} で正だが、エージェントは弱気")
    if bull_agents and any(v["decision"] == "SKIP" for v in inside["lens"].values()):
        out.append("エージェントは強気だが、Lens は SKIP")
    if len({v["decision"] for v in inside["lens"].values()}) > 1:
        out.append("Lens の日足と分足で、意見が違う（" + "、".join(f"{k}: {v['decision']}" for k, v in inside["lens"].items()) + "）")
    return out


RESEARCH = ["直近の値動きの原因は何か（適時開示・決算説明・ニュース）。一過性／構造的／需給／連想／不明 の、どれか",
            "市場が置いている悲観（または楽観）は何か。それと整合しない、確認できる事実はあるか（会社の説明以外で）",
            "回復（または継続）までの資金繰りは持つか。借入の返済・増資の可能性",
            "次に、何を、いつ確認するか（次の決算日など）。何が出たら、仮説を撤回するか"]


def layers_of(dossier: dict) -> dict:
    """記録用の、各層の値（後から、層ごとに採点する）。"""
    ch = [c for c in dossier["outside_view"]["h=21"]["chain"] if c.get("mean") is not None]
    iv = dossier["inside_view"]
    return {"gate": dossier["gate"]["verdict"], "red_flag": dossier["gate"]["verdict"].startswith("回避"), "distress": bool(dossier["gate"]["cautions"]),
            "outside_21d_sign": (None if not ch else "正" if ch[-1]["mean"] > 0 else "負"), "outside_21d_mean": (None if not ch else _r(ch[-1]["mean"])),
            "lens_daily": (iv["lens"].get("daily") or {}).get("decision"), "lens_intraday": (iv["lens"].get("intraday") or {}).get("decision"),
            "agents": (iv["agents"] or {}).get("group"), "s2_candidate": bool(dossier["verified_buy_side"]["s2"].get("candidate")),
            "sel_top15": bool(dossier["verified_buy_side"]["sel_c1"].get("top15")), "position_shares": dossier["position_size"].get("shares")}


def to_markdown(d: dict) -> str:
    g, vb, ps = d["gate"], d["verified_buy_side"], d["position_size"]
    L = [f"# 深掘りレポート: {d['code']} {d['meta'].get('name') or ''}（{d['asof']}）", "", f"**判定: {d['verdict']}**", ""]
    L += ["## 1. 関門（検証済みの回避条件）", f"- {g['verdict']}"] + [f"  - {x}" for x in g["reasons"]] + [f"  - 注意: {x}" for x in g["cautions"]]
    L += ["", "## 2. 検証済みの買い側の材料", f"- S2（配当の権利取り）: {'候補' if vb['s2'].get('candidate') else '候補でない'} {json.dumps({k: v for k, v in vb['s2'].items() if k not in ('note', 'candidate')}, ensure_ascii=False)}",
          f"- 順位予測 SEL-C1: {json.dumps({k: v for k, v in vb['sel_c1'].items() if k != 'note'}, ensure_ascii=False)}"]
    L += ["", "## 3. 外から見た基準率（同じ状態だった観測の、その後の超過）"]
    for h in ("h=21", "h=63"):
        ov = d["outside_view"][h]
        L += [f"### {h}（全観測の平均 {ov['all_observations']['mean']:+.2%}）", "| 重ねた条件 | 観測 | 判断日 | 平均超過 | t | 正の割合 |", "|---|---|---|---|---|---|"]
        for c in ov["chain"]:
            if "stopped" in c:
                L.append(f"| ＋{c['added']} | {c['stopped']} | | | | |")
            else:
                L.append(f"| ＋{c['added']} | {c['obs']} | {c['periods']} | {c['mean']:+.2%} | {'' if c['t'] is None else f'{c['t']:.2f}'} | {c['share_positive']:.0%} |")
    L += ["", "パターン図鑑では、補正後に有意な組み合わせはなかった。基準率は、「特別なことは、ない」ことの確認に使う。", "", "## 4. 銘柄の中身",
          f"- 今: {json.dumps(d['profile'].get('current'), ensure_ascii=False)}", f"- 財務: {json.dumps(d['profile'].get('fundamentals'), ensure_ascii=False)}",
          f"- 過去の個別の下げ: {json.dumps(d['profile'].get('past_events'), ensure_ascii=False)}", f"- 売り残・貸借: {json.dumps(d['short_balance'], ensure_ascii=False)}",
          f"- 直近の開示: {json.dumps(d['profile'].get('disclosures_last_20_business_days'), ensure_ascii=False)}",
          "", "## 5. 建玉の計算", f"- {json.dumps(ps, ensure_ascii=False)}", "", "## 6. 内側の見方（記録済みのもの）", f"- Lens: {json.dumps(d['inside_view']['lens'], ensure_ascii=False)}",
          f"- TradingAgents: {json.dumps(d['inside_view']['agents'], ensure_ascii=False)}", "", "## 食い違い"] + ([f"- {x}" for x in d["disagreements"]] or ["- なし"])
    L += ["", "## 7. 調べること（日本の一次情報）"] + [f"- {x}" for x in d["to_research"]] + ["", "## 記録", f"`{d['record_command']}`", ""]
    return "\n".join(L)


def main(root: Path, code: str, capital: float = 10_000_000, write=True) -> dict:
    P, iv, fins = fs2.load_panel(root, None)
    code = sp.norm_code(code)
    if code not in P.codes:
        return {"code": code, "error": "価格データにない銘柄コード"}
    snap = sp.snapshot(root, code, loaded=(P, iv, fins))
    snap.pop("_detail", None)
    T, j = len(P.dates) - 1, P.codes.index(code)
    sha = rs.manifest_sha(root)
    mgf = root / "processed" / "margin_interest.parquet"
    mg = pd.read_parquet(mgf) if mgf.exists() else None
    if mg is not None and (mg.empty or "usable_from" not in mg.columns):
        mg = None
    wide = P.eligible_daily(iv, schema.WIDE_MARKETS, min_history=extremes.HIST_MIN, va_min=extremes.VA_MIN)
    ev = deepdive.recent_extremes(P, wide, j)
    lim_up = bool(P.limit_up[T, j] and np.isfinite(P.adj_close[T, j]) and P.adj_close[T, j] >= P.adj_high[T, j] * (1 - 1e-9))
    elig_T = P.eligible(iv, schema.WIDE_MARKETS, [T], min_history=250, va_min=schema.WIDE_VA_MIN)[0]
    codes = atlas.codes_at(P, elig_T, iv, fins, mg, T)
    outside = {f"h={h}": deepdive.reference_classes(obs_for(root, P, iv, fins, mg, h, sha), codes, j) for h in HS}
    c = P.adj_close[max(T - 771, 0):T + 1, j]
    r21 = c[21:] / c[:-21] - 1.0 if len(c) > 21 else np.array([])
    va = float(P.va60()[T, j])
    pos = deepdive.position_size(float(P.raw_close[T, j]), r21, va, capital=capital)
    sb = {"loan(貸借)": None, "short_balance_class": "unknown"}
    cls = events.attr_at(P, iv, np.array([T]), np.array([j]), "margin_class")[0]
    sb["loan(貸借)"] = (None if cls is None else str(cls) == events.LOAN_CLASS)
    if mg is not None:
        row = exclude.margin_matrices(P, mg, [T])["short_days"][0]
        m = elig_T & np.isfinite(row)
        if m.sum() >= 30 and np.isfinite(row[j]):
            q1, q2 = np.percentile(row[m], [100 / 3, 200 / 3])
            sb["short_balance_class"] = "light" if row[j] <= q1 else "mid" if row[j] <= q2 else "heavy"
            sb["short_days"] = _r(float(row[j]), 2)
    distress = (snap.get("fundamentals") or {}).get("distress")
    gate = deepdive.gate(ev, lim_up, pos.get("shares", 0), distress)
    vb = {"s2": s2_status(root, code), "sel_c1": sel_status(root, code)}
    inside = inside_view(root, code, P.dates[T])
    has_buy = vb["s2"].get("candidate") or vb["sel_c1"].get("top15")
    verdict = gate["verdict"] if gate["verdict"] != "回避条件なし" else "回避条件なし。検証済みの買い材料: " + ("あり（" + "・".join(x for x, ok in (("S2", vb["s2"].get("candidate")), ("SEL 上位 15", vb["sel_c1"].get("top15"))) if ok) + "）" if has_buy else "なし")
    d = {"code": code, "asof": str(P.dates[T].date()), "meta": snap.get("meta", {}), "verdict": verdict, "gate": {**gate, "extreme_events_last_5d": ev, "limit_up_close_today": lim_up},
         "verified_buy_side": vb, "outside_view": outside, "profile": {k: snap.get(k) for k in ("in_decision_universe", "current", "fundamentals", "past_events", "elasticity", "disclosures_last_20_business_days")},
         "short_balance": sb, "position_size": pos, "inside_view": inside, "to_research": RESEARCH, "data_manifest_sha256": sha}
    d["disagreements"] = disagreements(gate, outside, inside, vb["s2"])
    d = _fmt(d)
    d["layers"] = layers_of(d)
    out_json = Path("results") / "deep" / f"{code}_{d['asof']}.json"
    d["record_command"] = f"python scripts/w5/watchlist.py add --code {code[:4]} --dossier data/jquants/{out_json.as_posix()} --cause <一過性|構造的|需給|連想|不明> --view <戻る|戻らない> --type <需給反発|業績回復|期待修正|経営改革> --check \"<確認時期>\" --exit \"<反証条件>\""
    if write:
        (root / out_json).parent.mkdir(parents=True, exist_ok=True)
        (root / out_json).write_text(json.dumps(d, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
        (root / out_json).with_suffix(".md").write_text(to_markdown(d), encoding="utf-8")
        d["files"] = {"json": str(out_json), "markdown": str(out_json.with_suffix(".md"))}
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/jquants")
    ap.add_argument("--code", required=True)
    ap.add_argument("--capital", type=float, default=10_000_000)
    a = ap.parse_args()
    print(json.dumps(main(Path(a.root), a.code, a.capital), ensure_ascii=False, indent=1, default=float))
