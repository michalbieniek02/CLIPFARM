$ErrorActionPreference = 'Stop'
$clipfarmRoot = $PSScriptRoot
$clipfarmPython = Join-Path $clipfarmRoot 'runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $clipfarmPython)) {
    throw 'Brak środowiska Python. Uruchom najpierw Install-CLIPFARM.ps1.'
}
$env:TEMP = $clipfarmRoot
$env:TMP = $clipfarmRoot
Start-Process -FilePath $clipfarmPython -ArgumentList ('"' + (Join-Path $clipfarmRoot 'app.py') + '"') -WorkingDirectory $clipfarmRoot -WindowStyle Hidden
