"""レート制限の確認。公表の上限（日足系 120 回/分、財務サマリー 60 回/分）を超えない範囲で、429 が出ないか見る。"""
import sys, time, collections
sys.path.insert(0, "scripts/jquants")
from client import Client
def run(label, path, params_list, per_min):
    c = Client(per_min=per_min)
    cnt = collections.Counter(); t0 = time.monotonic()
    for p in params_list:
        st, js, hd = c.get_page(path, p, note=f"rate:{label}")
        cnt[st] += 1
    dt = time.monotonic() - t0
    print(f"[{label}] {len(params_list)} 回 / {dt:.0f} 秒 = {len(params_list) / dt * 60:.0f} 回/分, HTTP 状態の内訳 {dict(cnt)}")
dates = ["2026-11-02", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"]
run("bars", "/v2/indices/bars/daily/topix", [{"from": dates[i % 8], "to": dates[i % 8]} for i in range(60)], per_min=110)
run("fins", "/v2/fins/summary", [{"code": f"{c}0"} for c in ("7203", "5802", "5801", "6758", "6902") * 6], per_min=55)
