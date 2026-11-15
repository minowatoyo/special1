# 前向きの記録の更新（月に 1 回ほど、PowerShell で実行）。
#   powershell -ExecutionPolicy Bypass -File scripts\update_and_record.ps1
# 1. J-Quants の追加取得（取得済みの日は、チェックポイントで飛ばす）  2. 加工  3. 順位予測・S2 の記録  4. 採点・集計
# APIキーは、実行のたびに入力する（画面に出さない。ファイルには書かない）。チャットに貼らない。
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not $env:JQUANTS_API_KEY) {
    $sec = Read-Host "J-Quants APIキー" -AsSecureString
    $env:JQUANTS_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}
git pull
python scripts/jquants/backfill.py --execute
python scripts/jquants/build_processed.py
python scripts/w5/forward.py record
python scripts/w5/forward_s2.py record
python scripts/w5/forward_events.py record
python scripts/w5/forward.py score
python scripts/w5/forward_s2.py score
python scripts/w5/forward_events.py score
python scripts/w5/forward.py summary
python scripts/w5/forward_s2.py summary
python scripts/w5/forward_events.py summary
Remove-Item Env:JQUANTS_API_KEY
Write-Host "完了。上の summary の出力（集計のみ）を貼る。"
