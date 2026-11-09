"""資料集（Markdown）の品質検査と出典台帳の生成。

    python tools/docs_tool.py lint    [--root ..]
    python tools/docs_tool.py sources [--root ..] [--out ../SOURCES.md]

lint が見るもの（01〜05 の本文書）:
  * 先頭の見出し・要約・最終更新、必須セクション（関連文書／この文書の限界／出典）
  * 出典表: 7 列、ID の形式と全体での一意性、検証タグ（✅S / ⚠M / ❓）、URL の形式
  * ⚠M の行に URL が付いていないこと（記憶由来の資料に URL を付けない規則）
  * 本文の引用 [XX-000] が（全文書の）出典表に存在するか、相対リンクの宛先が存在するか
  * 禁止語（AI モデル名など）、極端なサイズ
sources は、検証タグの集計・要確認一覧（⚠M / ❓）・URL のドメイン別件数をまとめた SOURCES.md を作る。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

TAGS = ("✅S", "⚠M", "❓")
SRC_HEADER = ["ID", "資料名", "著者・発行元", "年", "URL", "検証", "メモ"]
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d{2,3}$")
CITE_RE = re.compile(r"\[([A-Z][A-Z0-9]*-\d{2,3})\]")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FORBIDDEN = re.compile(r"claude|anthropic|sonnet|opus|haiku|fable", re.I)
REQUIRED_SECTIONS = ["関連文書", "この文書の限界", "出典"]
CONTENT_DIRS = ("01_techniques", "02_japan", "03_evidence", "04_learning", "05_tools_data_code")
LOW_KB, HIGH_KB = 3, 40


def content_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for d in CONTENT_DIRS:
        files += sorted((root / d).glob("*.md"))
    return files


def all_md(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if ".git" not in p.parts and ".venv" not in p.parts)


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def parse_sources(text: str) -> tuple[list[dict], list[str]]:
    """'## 出典' 以降の表を読む。返り値: (行の辞書リスト, 構文エラー)"""
    errs: list[str] = []
    m = re.search(r"^##\s+出典\s*$", text, re.M)
    if not m:
        return [], ["「## 出典」セクションがない"]
    rows: list[dict] = []
    seen_header = False
    for ln in text[m.end():].splitlines():
        if ln.startswith("## "):
            break
        if not ln.strip().startswith("|"):
            continue
        cells = split_row(ln)
        if re.fullmatch(r"[-:\s|]+", ln.strip()):
            continue
        if not seen_header:
            if cells[:len(SRC_HEADER)] != SRC_HEADER:
                errs.append(f"出典表のヘッダが規定と違う: {cells}")
            seen_header = True
            continue
        if len(cells) != len(SRC_HEADER):
            errs.append(f"出典表の列数が {len(cells)}（7 であるべき）: {ln[:80]}")
            continue
        rows.append(dict(zip(["id", "title", "author", "year", "url", "tag", "note"], cells)))
    if not seen_header:
        errs.append("出典表が見つからない")
    return rows, errs


def lint(root: Path) -> int:
    problems: list[str] = []
    warns: list[str] = []
    all_ids: dict[str, tuple[str, str, str]] = {}
    files = content_files(root)
    if not files:
        print("本文書が見つからない:", root)
        return 1
    global_ids: set[str] = set()
    for p in files:
        rows0, _ = parse_sources(p.read_text(encoding="utf-8"))
        global_ids |= {r["id"] for r in rows0}
    for p in files:
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8")
        kb = len(text.encode("utf-8")) / 1024
        if kb < LOW_KB:
            warns.append(f"{rel}: サイズが小さい ({kb:.1f} KB)")
        if kb > HIGH_KB:
            warns.append(f"{rel}: サイズが大きい ({kb:.1f} KB)")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            problems.append(f"{rel}: 1 行目が '# タイトル' でない")
        head = "\n".join(lines[:8])
        if "> 要約:" not in head:
            problems.append(f"{rel}: 冒頭に '> 要約:' がない")
        if "> 最終更新:" not in head:
            problems.append(f"{rel}: 冒頭に '> 最終更新:' がない")
        for sec in REQUIRED_SECTIONS:
            if not re.search(rf"^##\s+{sec}\s*$", text, re.M):
                problems.append(f"{rel}: セクション「{sec}」がない")
        # URL 中の追跡パラメータ（例: ?utm_source=...）は対象外。URL は改変しない方針なので除いてから検査する
        text_wo_urls = re.sub(r"https?://\S+", "", text)
        for mm in FORBIDDEN.finditer(text_wo_urls):
            ctx = text_wo_urls[max(0, mm.start() - 20):mm.end() + 20].replace("\n", " ")
            problems.append(f"{rel}: 禁止語 '{mm.group(0)}' … {ctx}")
        rows, errs = parse_sources(text)
        problems += [f"{rel}: {e}" for e in errs]
        ids_here = set()
        for r in rows:
            i = r["id"]
            if not ID_RE.match(i):
                problems.append(f"{rel}: ID の形式が不正: {i!r}")
            if i in all_ids:
                prev_rel, prev_url, prev_title = all_ids[i]
                same_url = r["url"] != "—" and r["url"] == prev_url
                same_title = r["url"] == "—" and prev_url == "—" and r["title"] == prev_title
                if not (same_url or same_title):
                    problems.append(f"{rel}: ID {i} が {prev_rel} の別の出典と衝突している（同一出典の再利用は許可）")
            else:
                all_ids[i] = (rel, r["url"], r["title"])
            ids_here.add(i)
            if r["tag"] not in TAGS:
                problems.append(f"{rel}: {i} の検証タグが不正: {r['tag']!r}")
            url = r["url"]
            if url != "—" and not re.match(r"^https?://\S+$", url):
                problems.append(f"{rel}: {i} の URL 形式が不正: {url!r}")
            if r["tag"] == "⚠M" and url != "—":
                problems.append(f"{rel}: {i} は ⚠M なのに URL がある（記憶由来に URL を付けない規則）")
            if r["tag"] == "❓" and url != "—":
                warns.append(f"{rel}: {i} は ❓ なのに URL がある")
        m_src = re.search(r"^##\s+出典\s*$", text, re.M)
        body = text[:m_src.start()] if m_src else text
        cited = set(CITE_RE.findall(body))
        for c in sorted(cited - global_ids):
            problems.append(f"{rel}: 本文の引用 [{c}] がどの出典表にもない")
        unused = ids_here - cited
        if rows and len(unused) > 0.6 * len(rows) and len(rows) > 15:
            warns.append(f"{rel}: 出典 {len(rows)} 件中 {len(unused)} 件が本文で引用されていない")
    for p in all_md(root):
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            path = target.split("#")[0]
            if path and not (p.parent / path).resolve().exists():
                problems.append(f"{rel}: リンク切れ → {target}")
    print(f"検査対象 {len(files)} ファイル / 一意な出典 {len(all_ids)} 件")
    for w in warns:
        print("WARN ", w)
    for q in problems:
        print("ERROR", q)
    print(f"結果: ERROR {len(problems)} 件, WARN {len(warns)} 件")
    return 1 if problems else 0


def build_sources(root: Path, out: Path) -> None:
    per_file: dict[str, list[dict]] = {}
    for p in content_files(root):
        rows, _ = parse_sources(p.read_text(encoding="utf-8"))
        per_file[p.relative_to(root).as_posix()] = rows
    total = Counter()
    lines = [
        "# 出典台帳（自動生成）",
        "> 要約: 各文書の「出典」表を集計した台帳。検証タグごとの件数、人手での確認が必要な資料（⚠M / ❓）の一覧、URL のドメイン別件数を示す。",
        "> 最終更新: 2026-11-09（`07_reference_code/tools/docs_tool.py sources` で再生成）",
        "",
        "## 検証タグの意味",
        "",
        "| タグ | 意味 |",
        "|---|---|",
        "| ✅S | 検索結果・論文データベース・パッケージレジストリ（PyPI/npm）の応答に現れ、書名・著者・年などの書誌情報が整合することを確認した。**全文・原ページは読んでいない**（外部サイトの直接取得がこの作業環境では遮断されていたため）。 |",
        "| ⚠M | 作成時の記憶に基づく。広く知られた古典など存在を強く確信できるものに限るが、今回の作業で再確認していない。URL は付けていない。 |",
        "| ❓ | 不確実。人手での確認が必要。 |",
        "",
        "## ファイル別の件数",
        "",
        "| ファイル | 合計 | ✅S | ⚠M | ❓ |",
        "|---|---:|---:|---:|---:|",
    ]
    domains: Counter = Counter()
    review: dict[str, list[dict]] = defaultdict(list)
    for rel, rows in per_file.items():
        c = Counter(r["tag"] for r in rows)
        total.update(c)
        lines.append(f"| `{rel}` | {len(rows)} | {c['✅S']} | {c['⚠M']} | {c['❓']} |")
        for r in rows:
            if r["tag"] in ("⚠M", "❓"):
                review[rel].append(r)
            if r["url"].startswith("http"):
                domains[urlparse(r["url"]).netloc.lower().removeprefix("www.")] += 1
    uniq = {}
    for rows in per_file.values():
        for r in rows:
            uniq.setdefault(r["id"], r["tag"])
    n = sum(total.values())
    uc = Counter(uniq.values())
    lines.append(f"| **合計（延べ）** | **{n}** | **{total['✅S']}** | **{total['⚠M']}** | **{total['❓']}** |")
    lines.append(f"| **一意な出典（ID で重複排除）** | **{len(uniq)}** | **{uc['✅S']}** | **{uc['⚠M']}** | **{uc['❓']}** |")
    lines += ["", "## 人手での確認を推奨する資料（⚠M / ❓）", ""]
    if not review:
        lines.append("（なし）")
    for rel, rows in review.items():
        lines += [f"### `{rel}`", "", "| ID | 資料名 | 著者・発行元 | 年 | タグ | メモ |", "|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['id']} | {r['title']} | {r['author']} | {r['year']} | {r['tag']} | {r['note']} |")
        lines.append("")
    lines += ["## URL のドメイン別件数", "", "| ドメイン | 件数 |", "|---|---:|"]
    for dom, cnt in domains.most_common():
        lines.append(f"| {dom} | {cnt} |")
    lines += ["", "## 関連文書", "", "- [README](README.md)", "", "## この文書の限界", "",
              "- 台帳は各文書の出典表から機械的に集計したもので、URL の到達性は確認していない（作業環境からは外部サイトに接続できなかった）。",
              "- ✅S は書誌情報の整合を確認したことを意味し、内容の正しさや全文の精読を意味しない。", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}  (延べ {n} 件 / 一意 {len(uniq)} 件: ✅S {uc['✅S']} / ⚠M {uc['⚠M']} / ❓ {uc['❓']})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lint", "sources"])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.cmd == "lint":
        return lint(root)
    build_sources(root, Path(a.out) if a.out else root / "SOURCES.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
