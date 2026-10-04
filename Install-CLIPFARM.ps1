$ErrorActionPreference = 'Stop'
$clipfarmRoot = $PSScriptRoot
$env:TEMP = $clipfarmRoot
$env:TMP = $clipfarmRoot
$clipfarmBasePython = (Get-Command python -ErrorAction Stop).Source
$clipfarmPythonVersion = & $clipfarmBasePython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if (-not (& $clipfarmBasePython -c "import sys; print(int(sys.version_info >= (3,11) and sys.maxsize > 2**32))").Trim().Equals('1')) {
    throw "CLIPFARM wymaga Python 3.11+ 64-bit. Wykryto Python $clipfarmPythonVersion. Zalecana, przetestowana wersja: Python 3.12."
}
& $clipfarmBasePython -m venv (Join-Path $clipfarmRoot 'runtime')
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się utworzyć środowiska Python.' }
& (Join-Path $clipfarmRoot 'runtime\Scripts\python.exe') -m pip install -r (Join-Path $clipfarmRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować bibliotek.' }
