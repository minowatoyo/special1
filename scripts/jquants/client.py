"""J-Quants API V2 の最小クライアント（取得・生データ保存・取得ログ・レート制限）。

  * 鍵: 環境変数 JQUANTS_API_KEY（ローカル PC では実際のキー）。クラウドのセッションでは、プロキシが保存済みのキーに
    置き換えるので、未設定なら仮の値 "proxy-injected" を送る。
  * 生の応答は data/jquants/raw/<エンドポイント>/<取得日>/<パラメータのハッシュ>.json に、そのまま保存する（ページごと）。
  * 取得ログ data/jquants/_meta/fetch_log.csv に、URL・UTC 時刻・HTTP 状態・バイト数・sha256 を追記する（鍵は記録しない）。
  * 再試行は同じ URL につき最大 2 回（429・5xx のみ）。401/403 は再試行せず例外にする（回避しない）。
  * 生データは、会話・レポートに出さない（出すのは件数・列名・集計・ハッシュ）。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.jquants.com"
ROOT = Path(os.environ.get("JQUANTS_DATA_DIR", "data/jquants"))
UA = "research-fetch/1.0"


class AuthError(RuntimeError):
    """401/403。再試行しない。"""


class RateLimiter:
    def __init__(self, per_min: float):
        self.gap = 60.0 / per_min
        self.last = 0.0

    def wait(self) -> None:
        d = self.gap - (time.monotonic() - self.last)
        if d > 0:
            time.sleep(d)
        self.last = time.monotonic()


class Client:
    def __init__(self, root: Path | None = None, per_min: float = 60.0, key: str | None = None):
        self.root = Path(root) if root else ROOT
        self.limiter = RateLimiter(per_min)
        self.last_raw = ""
        self.last_files: list = []
        self.last_pages = 0
        self.key = key or os.environ.get("JQUANTS_API_KEY") or "proxy-injected"
        (self.root / "_meta").mkdir(parents=True, exist_ok=True)

    def _log(self, row: list) -> None:
        p = self.root / "_meta" / "fetch_log.csv"
        new = not p.exists()
        with open(p, "a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            if new:
                w.writerow(["utc", "path", "params", "http", "bytes", "sha256", "raw_file", "note"])
            w.writerow(row)

    def get_page(self, path: str, params: dict | None = None, note: str = "") -> tuple[int, dict | None, dict]:
        """1 ページ取得。戻り値 (HTTP 状態, JSON または None, 応答ヘッダー)。"""
        params = {k: v for k, v in (params or {}).items() if v is not None}
        url = BASE + path + ("?" + urllib.parse.urlencode(sorted(params.items())) if params else "")
        status, body, headers = 0, b"", {}
        for attempt in range(3):
            self.limiter.wait()
            req = urllib.request.Request(url, headers={"x-api-key": self.key, "User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    status, body, headers = r.status, r.read(), dict(r.headers)
            except urllib.error.HTTPError as e:
                status, body, headers = e.code, e.read(), dict(e.headers)
            except Exception as e:                      # 接続の失敗など
                status, body = 0, str(e).encode()
            if status in (401, 403):
                self._record(path, params, status, body, note + " AUTH")
                raise AuthError(f"{status} {path}: {body[:120]!r}")
            if status in (429,) or status >= 500 or status == 0:
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
            break
        self.last_raw = self._record(path, params, status, body, note)
        try:
            js = json.loads(body) if body else None
        except ValueError:
            js = None
        return status, js, headers

    def _record(self, path: str, params: dict, status: int, body: bytes, note: str) -> str:
        sha = hashlib.sha256(body).hexdigest()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = path.strip("/").replace("/", "_")
        h = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
        n = 0
        d = self.root / "raw" / slug / day
        d.mkdir(parents=True, exist_ok=True)
        while (d / f"{h}_{n}.json").exists():
            n += 1
        f = d / f"{h}_{n}.json"
        f.write_bytes(body)
        self._log([datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), path, json.dumps(params, sort_keys=True), status, len(body), sha, str(f), note])
        return str(f)

    def get_all(self, path: str, params: dict | None = None, note: str = "") -> tuple[int, list]:
        """pagination_key をたどって全ページを取得し、data 配列を連結して返す。

        200 以外、または 200 でも本文が JSON として読めないページがあれば、その時点の状態を返す（呼び出し側は失敗として扱う。
        正常な 0 行とは区別される）。取得できたページの生データの場所は self.last_files に残る。"""
        rows, pk, status = [], None, 0
        self.last_files = []
        self.last_pages = 0
        while True:
            q = dict(params or {})
            if pk:
                q["pagination_key"] = pk
            status, js, _ = self.get_page(path, q, note)
            self.last_files.append(self.last_raw)
            if status == 200 and not isinstance(js, dict):
                status = -1                      # 本文が壊れている
            if status != 200:
                break
            self.last_pages += 1
            for v in js.values():
                if isinstance(v, list):
                    rows.extend(v)
            pk = js.get("pagination_key")
            if not pk:
                break
        return status, rows
