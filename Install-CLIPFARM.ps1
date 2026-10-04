[CmdletBinding()]
param(
    [string]$DesktopPath,
    [string]$PythonPath,
    [switch]$ShortcutOnly
)

$ErrorActionPreference = 'Stop'
$clipfarmRoot = $PSScriptRoot

function Test-ClipfarmPython {
    param([string]$Path, [string[]]$LauncherArguments = @())
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    # Never launch the Windows Store's python.exe alias during discovery.
    if ($Path -match '\\WindowsApps\\python(?:3)?\.exe$') { return $null }
    try {
        # Single Python quotes survive Windows PowerShell 5.1 native arguments.
        $probe = 'import json,platform,struct,sys; print(json.dumps(dict(executable=sys.executable,major=sys.version_info.major,minor=sys.version_info.minor,bits=struct.calcsize(''P'')*8,machine=platform.machine(),prefix=sys.prefix,venv=sys.prefix!=sys.base_prefix),ensure_ascii=True))'
        $output = & $Path @LauncherArguments -c $probe 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $python = ($output -join "`n") | ConvertFrom-Json
        if ($python.major -ne 3 -or $python.minor -lt 11 -or $python.bits -ne 64 -or $python.machine -notin @('AMD64', 'x86_64')) { return $null }
        if (-not (Test-Path -LiteralPath $python.executable -PathType Leaf)) { return $null }
        return $python
    } catch { return $null }
}

function Find-ClipfarmPython {
    $found = @()
    $launcherPaths = @((Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue).Source)
    $launcherPaths += Join-Path $env:WINDIR 'py.exe'
    if ($env:LOCALAPPDATA) { $launcherPaths += Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\py.exe' }
    foreach ($launcher in ($launcherPaths | Where-Object { $_ } | Select-Object -Unique)) {
        foreach ($version in @('-3.12', '-3')) {
            $python = Test-ClipfarmPython $launcher @($version)
            if ($python) { $found += $python }
        }
    }
    $paths = @((Get-Command python.exe, python3.exe -CommandType Application -ErrorAction SilentlyContinue).Source)
    $installRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, ($env:SystemDrive + '\'))
    if ($env:LOCALAPPDATA) { $installRoots += Join-Path $env:LOCALAPPDATA 'Programs\Python' }
    foreach ($installRoot in ($installRoots | Where-Object { $_ } | Select-Object -Unique)) {
        foreach ($folder in (Get-ChildItem -LiteralPath $installRoot -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue)) {
            $paths += Join-Path $folder.FullName 'python.exe'
        }
    }
    foreach ($path in ($paths | Where-Object { $_ } | Select-Object -Unique)) {
        $python = Test-ClipfarmPython $path
        if ($python) { $found += $python }
    }
    return $found | Sort-Object @{ Expression = { $_.minor -eq 12 }; Descending = $true }, @{ Expression = { $_.minor }; Descending = $true } | Select-Object -First 1
}

function New-ClipfarmShortcut {
    param([string]$Destination)
    if (-not $Destination) { $Destination = [Environment]::GetFolderPath('DesktopDirectory') }
    if (-not $Destination -or -not (Test-Path -LiteralPath $Destination -PathType Container)) {
        throw "Nie znaleziono folderu pulpitu: $Destination. Mozesz podac -DesktopPath z istniejacym folderem."
    }
    $shortcutPath = Join-Path ([IO.Path]::GetFullPath($Destination)) 'CLIPFARM.lnk'
    $shell = New-Object -ComObject WScript.Shell
    try {
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $launcher = Join-Path $clipfarmRoot 'CLIPFARM.exe'
        if (Test-Path -LiteralPath $launcher -PathType Leaf) {
            $shortcut.TargetPath = $launcher
            $shortcut.Arguments = ''
        } else {
            $shortcut.TargetPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
            $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $clipfarmRoot 'Start-CLIPFARM.ps1') + '"'
        }
        $shortcut.WorkingDirectory = $clipfarmRoot
        $shortcut.IconLocation = (Join-Path $clipfarmRoot 'assets\clipfarm.ico') + ',0'
        $shortcut.Description = 'CLIPFARM - edytor klipow wideo'
        $shortcut.Save()
    } finally {
        if ($shortcut) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut) }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }
    Write-Host "Skrot CLIPFARM jest gotowy: $shortcutPath"
}

$clipfarmOldTemp = $env:TEMP
$clipfarmOldTmp = $env:TMP
Push-Location -LiteralPath $clipfarmRoot
try {
    Write-Host 'CLIPFARM - przygotowanie aplikacji'
    $env:TEMP = $clipfarmRoot
    $env:TMP = $clipfarmRoot
    foreach ($required in @('app.py', 'qt_app.py', 'qml\Main.qml', 'requirements.txt', 'assets\clipfarm.ico')) {
        if (-not (Test-Path -LiteralPath (Join-Path $clipfarmRoot $required) -PathType Leaf)) {
            throw "Brak pliku $required. Wypakuj caly ZIP do jednego folderu i uruchom instalator ponownie."
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $clipfarmRoot 'CLIPFARM.exe') -PathType Leaf) -and -not (Test-Path -LiteralPath (Join-Path $clipfarmRoot 'Start-CLIPFARM.ps1') -PathType Leaf)) {
        throw 'Brak pliku CLIPFARM.exe lub Start-CLIPFARM.ps1. Wypakuj caly ZIP.'
    }
    $clipfarmRuntime = Join-Path $clipfarmRoot 'runtime'
    $clipfarmPythonPath = Join-Path $clipfarmRuntime 'Scripts\python.exe'
    $clipfarmPython = Test-ClipfarmPython $clipfarmPythonPath
    if (Test-Path -LiteralPath $clipfarmRuntime) {
        if (-not $clipfarmPython -or -not $clipfarmPython.venv -or [IO.Path]::GetFullPath($clipfarmPython.prefix).TrimEnd('\') -ne $clipfarmRuntime.TrimEnd('\')) {
            throw 'Istniejacy folder runtime nie zawiera dzialajacego Python 3.11+ x64. Zachowaj go pod inna nazwa i uruchom instalator ponownie.'
        }
        Write-Host "Uzywam istniejacego srodowiska Python 3.$($clipfarmPython.minor)."
    } elseif ($ShortcutOnly) {
        throw 'Brak srodowiska runtime. Uruchom instalator bez -ShortcutOnly.'
    } else {
        if ($PythonPath) {
            $clipfarmBasePython = Test-ClipfarmPython $PythonPath
            if (-not $clipfarmBasePython) { throw 'Podany -PythonPath nie wskazuje na dzialajacy Python 3.11+ x64.' }
        } else { $clipfarmBasePython = Find-ClipfarmPython }
        if (-not $clipfarmBasePython) {
            $winget = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue
            if (-not $winget) { throw 'Zainstaluj Python 3.12 (Windows installer, 64-bit) z https://www.python.org/downloads/windows/ i uruchom instalator ponownie.' }
            Write-Host 'Instaluje Python 3.12 x64 dla biezacego uzytkownika przez winget...'
            & $winget.Source install --id Python.Python.3.12 --exact --source winget --scope user --architecture x64 --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
            $wingetExitCode = $LASTEXITCODE
            $clipfarmBasePython = Find-ClipfarmPython
            if (-not $clipfarmBasePython) { throw "Nie udalo sie przygotowac Python (winget: $wingetExitCode). Zainstaluj Python 3.12 x64 z https://www.python.org/downloads/windows/ i uruchom instalator ponownie." }
        }
        Write-Host "Tworze srodowisko aplikacji: Python 3.$($clipfarmBasePython.minor)."
        & $clipfarmBasePython.executable -m venv $clipfarmRuntime
        if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie utworzyc srodowiska Python.' }
        $clipfarmPython = Test-ClipfarmPython $clipfarmPythonPath
        if (-not $clipfarmPython -or -not $clipfarmPython.venv) { throw 'Nowe srodowisko Python nie dziala. Uruchom instalator ponownie po zachowaniu folderu runtime pod inna nazwa.' }
    }
    if (-not $ShortcutOnly) {
        Write-Host 'Instaluje biblioteki aplikacji. Pierwsza instalacja moze potrwac kilka minut...'
        & $clipfarmPythonPath -m pip install --disable-pip-version-check -r (Join-Path $clipfarmRoot 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie zainstalowac bibliotek. Sprawdz blad powyzej i uruchom instalator ponownie.' }
    }
    New-ClipfarmShortcut $DesktopPath
    Write-Host 'Gotowe. Uruchom CLIPFARM skrotem z pulpitu.'
} catch {
    [Console]::Error.WriteLine("Instalacja nie powiodla sie: $($_.Exception.Message)")
    exit 1
} finally {
    $env:TEMP = $clipfarmOldTemp
    $env:TMP = $clipfarmOldTmp
    Pop-Location
}
