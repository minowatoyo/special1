"""W2 のゲート手前の小規模確認。出力は件数・列名・日付の範囲・HTTP 状態・集計だけ（生データの行は出さない）。"""
import json, sys, time
sys.path.insert(0, "scripts/jquants")
from client import Client, AuthError

c = Client(per_min=60)
def cols(rows): return sorted({k for r in rows for k in r}) if rows else []
def probe(label, path, params):
    st, js, hd = c.get_page(path, params, note=f"probe:{label}")
    n = None; cl = []
    if js:
        for k, v in js.items():
            if isinstance(v, list): n = len(v); cl = cols(v)
        msg = js.get("message") if st != 200 else None
    else:
        msg = None
    print(f"[{label}] {path} {params} -> HTTP {st}, 件数 {n}, 列 {cl}" + (f", message={msg}" if msg else ""))
    return st, js, hd

# 1. 1 銘柄・1 か月（トヨタ 2026-10）
st, js, hd = probe("bars_1m", "/v2/equities/bars/daily", {"code": "72030", "from": "2026-10-01", "to": "2026-10-31"})
print("  応答ヘッダー（レート関連のみ）:", {k: v for k, v in hd.items() if "limit" in k.lower() or "rate" in k.lower() or "retry" in k.lower()})
if js:
    d = js["data"]; print("  AdjFactor の種類:", sorted({x["AdjFactor"] for x in d}), "日付", d[0]["Date"], "〜", d[-1]["Date"])
# 2. 10 年窓の最古日（範囲外を要求して、プランの対象期間の案内文を読む）
for fr in ("2016-01-04", "2016-10-03", "2016-11-14", "2016-11-11"):
    probe(f"oldest_{fr}", "/v2/equities/bars/daily", {"code": "72030", "from": fr, "to": fr})
# 3. 上場廃止銘柄（東芝 6502：2023-12 に上場廃止）の価格が、廃止後の取得で取れるか
probe("delisted_bars_2023-06", "/v2/equities/bars/daily", {"code": "65020", "from": "2023-06-01", "to": "2023-06-30"})
probe("delisted_bars_after", "/v2/equities/bars/daily", {"code": "65020", "from": "2024-01-04", "to": "2024-01-12"})
# 4. 銘柄マスタ（日付指定）
for dt in ("2023-06-01", "2026-11-11"):
    st, js, hd = probe(f"master_{dt}", "/v2/equities/master", {"date": dt})
    if js:
        rows = [v for v in js.values() if isinstance(v, list)][0]
        codes = {r.get("Code") for r in rows}
        print(f"  6502(65020) が含まれるか: {'65020' in codes}, 全体 {len(rows)} 件")
# 5. 日付指定の全銘柄日足（廃止銘柄を含むか）
st, js, hd = probe("bars_by_date_2023-06-01", "/v2/equities/bars/daily", {"date": "2023-06-01"})
if js:
    rows = [v for v in js.values() if isinstance(v, list)][0]
    print("  日付指定の全銘柄: 件数", len(rows), ", 65020 を含む:", any(r.get("Code") == "65020" for r in rows), ", ページ続き:", bool(js.get("pagination_key")))
# 6. 財務・決算予定日・TOPIX・指数
st, js, hd = probe("fins_summary", "/v2/fins/summary", {"code": "72030"})
if js:
    rows = [v for v in js.values() if isinstance(v, list)][0]
    print("  開示日・開示時刻の列:", [k for k in cols(rows) if "Disc" in k or "Date" in k or "Time" in k][:8])
probe("earnings_calendar", "/v2/equities/earnings-calendar", {})
probe("topix", "/v2/indices/bars/daily/topix", {"from": "2026-11-05", "to": "2026-11-12"})
probe("indices", "/v2/indices/bars/daily", {"date": "2026-11-11"})
try:
    probe("dividend(Premium限定のはず)", "/v2/fins/dividend", {"code": "72030"})
except AuthError as e:                       # 403 は想定どおり（Standard では使えない）
    print("dividend: 利用不可（403）", str(e)[:60])
