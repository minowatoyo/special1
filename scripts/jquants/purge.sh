#!/bin/sh
# J-Quants 由来のデータ（生・加工済み・DB・取得ログ）を一括で完全に消去する。解約時に実行する。
# 使い方: scripts/jquants/purge.sh [データのディレクトリ。既定 data/jquants]  （確認のため --yes が要る）
DIR="${1:-data/jquants}"
[ "$1" = "--yes" ] && DIR="data/jquants"
case "$*" in *--yes*) ;; *) echo "消去の対象: $DIR（確認のため --yes を付けて再実行）"; exit 1;; esac
[ -n "$DIR" ] && [ "$DIR" != "/" ] && [ -d "$DIR" ] || { echo "ディレクトリが見つからない: $DIR"; exit 1; }
rm -rf -- "$DIR"
echo "消去しました: $DIR"
