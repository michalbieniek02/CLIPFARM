$ErrorActionPreference = 'Stop'
$clipfarmRoot = $PSScriptRoot
$env:TEMP = $clipfarmRoot
$env:TMP = $clipfarmRoot
$clipfarmBasePython = (Get-Command python -ErrorAction Stop).Source
& $clipfarmBasePython -m venv (Join-Path $clipfarmRoot 'runtime')
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się utworzyć środowiska. Użyj Python 3.12.' }
& (Join-Path $clipfarmRoot 'runtime\Scripts\python.exe') -m pip install -r (Join-Path $clipfarmRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować bibliotek.' }
