Set-Location -LiteralPath "$PSScriptRoot"
& "$PSScriptRoot\emotion_env\Scripts\Activate.ps1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
python "$PSScriptRoot\app.py"
