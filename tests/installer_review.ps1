$ErrorActionPreference = 'Stop'
$clipfarmRepo = Split-Path -Parent $PSScriptRoot
$clipfarmChecks = Join-Path $clipfarmRepo 'checks'
$clipfarmTestRoot = Join-Path $clipfarmChecks ('installer-' + [Guid]::NewGuid().ToString('N'))
$clipfarmFixture = Join-Path $clipfarmTestRoot ('CLIPFARM test ' + [char]0x0142 + [char]0x00F3 + [char]0x017C + [char]0x6F22)
$clipfarmDesktop = Join-Path $clipfarmTestRoot ('Pulpit ' + [char]0x015B + [char]0x0107 + [char]0x5B57)
$clipfarmCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$clipfarmSavedLog = $env:CLIPFARM_INSTALLER_TEST_LOG
$clipfarmSavedPip = $env:CLIPFARM_INSTALLER_TEST_PIP_RESULT
$clipfarmSavedMinor = $env:CLIPFARM_INSTALLER_TEST_MINOR

function Assert-Installer {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Invoke-TestInstaller {
    param([string[]]$Arguments, [int]$ExpectedExit = 0)
    # Capture native stderr without PS5.1 treating the expected failure as terminating.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $output = & (Join-Path $clipfarmFixture 'Install-CLIPFARM.exe') --no-pause @Arguments 2>&1; $result = $LASTEXITCODE }
    finally { $ErrorActionPreference = $previousPreference }
    Assert-Installer ($result -eq $ExpectedExit) "Unexpected installer status $result (expected $ExpectedExit): $output"
    return $output -join "`n"
}

try {
    [void][Reflection.Assembly]::LoadFrom((Join-Path $clipfarmRepo 'Install-CLIPFARM.exe'))
    [void](New-Item -ItemType Directory -Path $clipfarmFixture, $clipfarmDesktop, (Join-Path $clipfarmFixture 'assets'), (Join-Path $clipfarmFixture 'qml') -Force)
    foreach ($file in @('Install-CLIPFARM.ps1', 'Install-CLIPFARM.exe', 'CLIPFARM.exe', 'Start-CLIPFARM.ps1')) {
        Copy-Item -LiteralPath (Join-Path $clipfarmRepo $file) -Destination $clipfarmFixture
    }
    Copy-Item -LiteralPath (Join-Path $clipfarmRepo 'assets\clipfarm.ico') -Destination (Join-Path $clipfarmFixture 'assets')
    foreach ($file in @('app.py', 'qt_app.py', 'qml\Main.qml', 'requirements.txt')) {
        Set-Content -LiteralPath (Join-Path $clipfarmFixture $file) -Value '# isolated installer fixture' -Encoding ascii
    }
    # Exercise the real Python probe and venv creation through EXE -> PS5.1.
    # Empty requirements keep this check offline and do not install application dependencies.
    $nativePython = Join-Path $clipfarmRepo 'runtime\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $nativePython)) {
        $nativePython = (Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    }
    [void](Invoke-TestInstaller @('-DesktopPath', $clipfarmDesktop, '-PythonPath', $nativePython, '-Verbose'))
    $nativeRuntime = [IO.Path]::GetFullPath((Join-Path $clipfarmFixture 'runtime'))
    Assert-Installer (Test-Path -LiteralPath (Join-Path $nativeRuntime 'pyvenv.cfg')) 'Real Python did not create a venv.'
    Assert-Installer (Test-Path -LiteralPath (Join-Path $clipfarmDesktop 'CLIPFARM.lnk')) 'Real installation did not create a shortcut.'
    $fixtureBoundary = [IO.Path]::GetFullPath($clipfarmFixture).TrimEnd('\') + '\'
    Assert-Installer ($nativeRuntime.StartsWith($fixtureBoundary, [StringComparison]::OrdinalIgnoreCase)) 'Unsafe runtime cleanup path.'
    Remove-Item -LiteralPath $nativeRuntime -Recurse -Force
    $helperSource = @'
using System;
using System.IO;
using System.Reflection;
internal static class FakePython {
    static string Json(string value) {
        var encoded = new System.Text.StringBuilder();
        foreach (char c in value.Replace("\\", "\\\\").Replace("\"", "\\\""))
            if (c > 127) encoded.Append("\\u").Append(((int)c).ToString("x4"));
            else encoded.Append(c);
        return encoded.ToString();
    }
    static int Main(string[] args) {
        string executable = Assembly.GetExecutingAssembly().Location;
        string folder = Path.GetDirectoryName(executable);
        string log = Environment.GetEnvironmentVariable("CLIPFARM_INSTALLER_TEST_LOG");
        if (!String.IsNullOrEmpty(log)) File.AppendAllText(log, String.Join("|", args) + Environment.NewLine);
        if (Array.IndexOf(args, "-c") >= 0) {
            bool venv = new DirectoryInfo(folder).Name == "Scripts";
            string prefix = venv ? Directory.GetParent(folder).FullName : folder;
            string minor = Environment.GetEnvironmentVariable("CLIPFARM_INSTALLER_TEST_MINOR") ?? "12";
            Console.WriteLine("{\"executable\":\"" + Json(executable) + "\",\"major\":3,\"minor\":" + minor + ",\"bits\":64,\"machine\":\"AMD64\",\"prefix\":\"" + Json(prefix) + "\",\"venv\":" + (venv ? "true" : "false") + "}");
            return 0;
        }
        if (args.Length >= 3 && args[0] == "-m" && args[1] == "venv") {
            string scripts = Path.Combine(args[2], "Scripts");
            Directory.CreateDirectory(scripts);
            File.Copy(executable, Path.Combine(scripts, "python.exe"));
            return 0;
        }
        if (args.Length >= 3 && args[0] == "-m" && args[1] == "pip") {
            int result;
            Int32.TryParse(Environment.GetEnvironmentVariable("CLIPFARM_INSTALLER_TEST_PIP_RESULT"), out result);
            Console.WriteLine("Fixture pip result: " + result);
            return result;
        }
        return 9;
    }
}
'@
    $helperSourcePath = Join-Path $clipfarmTestRoot 'FakePython.cs'
    $basePython = Join-Path $clipfarmTestRoot 'python.exe'
    Set-Content -LiteralPath $helperSourcePath -Value $helperSource -Encoding ascii
    & $clipfarmCompiler /nologo /target:exe "/out:$basePython" $helperSourcePath
    Assert-Installer ($LASTEXITCODE -eq 0) 'Could not compile the isolated Python/pip fixture.'
    $env:CLIPFARM_INSTALLER_TEST_LOG = Join-Path $clipfarmTestRoot 'python-calls.log'
    $env:CLIPFARM_INSTALLER_TEST_PIP_RESULT = '0'
    $env:CLIPFARM_INSTALLER_TEST_MINOR = '12'
    $sentinels = @('projects\saved.json', 'exports\clip.mp4', 'models\cached.txt', 'settings.json', '.env')
    foreach ($file in $sentinels) {
        $path = Join-Path $clipfarmFixture $file
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $path) -Force)
        Set-Content -LiteralPath $path -Value 'existing user data' -Encoding ascii
    }
    # PS5.1 corrupts trailing backslashes in quoted native array arguments before
    # the EXE receives them; use the normal GetFolderPath-style directory value.
    [void](Invoke-TestInstaller @('-DesktopPath', $clipfarmDesktop, '-PythonPath', $basePython))
    $linkPath = Join-Path $clipfarmDesktop 'CLIPFARM.lnk'
    Assert-Installer (Test-Path -LiteralPath $linkPath) 'Success did not create the shortcut.'
    $link = [ClipfarmShortcut]::Read($linkPath)
    Assert-Installer ($link[0] -eq (Join-Path $clipfarmFixture 'CLIPFARM.exe')) 'Shortcut target does not use the bundled launcher.'
    Assert-Installer ($link[2] -eq $clipfarmFixture) 'Shortcut working directory is incorrect.'
    Assert-Installer ($link[3] -eq ((Join-Path $clipfarmFixture 'assets\clipfarm.ico') + ',0')) 'Shortcut branded icon is incorrect.'
    Assert-Installer ($link[4] -match 'CLIPFARM') 'Shortcut description is missing.'
    Set-Content -LiteralPath (Join-Path $clipfarmFixture 'runtime\keep.txt') -Value 'preserved runtime' -Encoding ascii
    [void](Invoke-TestInstaller @('-DesktopPath', $clipfarmDesktop))
    $calls = Get-Content -LiteralPath $env:CLIPFARM_INSTALLER_TEST_LOG
    Assert-Installer (@($calls | Where-Object { $_ -like '-m|venv|*' }).Count -eq 1) 'A valid runtime was recreated.'
    Assert-Installer (@($calls | Where-Object { $_ -like '-m|pip|*' }).Count -eq 2) 'Full installation did not check pip on both runs.'
    foreach ($file in $sentinels) {
        Assert-Installer ((Get-Content -LiteralPath (Join-Path $clipfarmFixture $file)) -eq 'existing user data') "User file changed: $file"
    }
    Assert-Installer ((Get-Content -LiteralPath (Join-Path $clipfarmFixture 'runtime\keep.txt')) -eq 'preserved runtime') 'Runtime content changed.'

    $errorDesktop = Join-Path $clipfarmTestRoot 'Failed desktop'
    [void](New-Item -ItemType Directory -Path $errorDesktop)
    $env:CLIPFARM_INSTALLER_TEST_PIP_RESULT = '7'
    $failure = Invoke-TestInstaller @('-DesktopPath', $errorDesktop) 1
    Assert-Installer ($failure -match 'bibliotek') 'Pip failure did not explain the dependency error.'
    Assert-Installer (-not (Test-Path -LiteralPath (Join-Path $errorDesktop 'CLIPFARM.lnk'))) 'Pip failure created a success shortcut.'

    # Recreate only the link without touching pip; also exercise the PS1 launcher fallback.
    Remove-Item -LiteralPath (Join-Path $clipfarmFixture 'CLIPFARM.exe')
    [void](Invoke-TestInstaller @('-DesktopPath', $errorDesktop, '-ShortcutOnly'))
    $link = [ClipfarmShortcut]::Read((Join-Path $errorDesktop 'CLIPFARM.lnk'))
    Assert-Installer ($link[0] -like '*\powershell.exe') 'Fallback shortcut does not target PowerShell.'
    Assert-Installer ($link[1].Contains('"' + (Join-Path $clipfarmFixture 'Start-CLIPFARM.ps1') + '"')) 'Fallback script path is not quoted.'
    Assert-Installer ($link[2] -eq $clipfarmFixture) 'Fallback working directory is incorrect.'
    $calls = Get-Content -LiteralPath $env:CLIPFARM_INSTALLER_TEST_LOG
    Assert-Installer (@($calls | Where-Object { $_ -like '-m|pip|*' }).Count -eq 3) 'ShortcutOnly called pip.'

    $invalidDesktop = Join-Path $clipfarmTestRoot 'Invalid desktop'
    [void](New-Item -ItemType Directory -Path $invalidDesktop)
    $env:CLIPFARM_INSTALLER_TEST_MINOR = '10'
    $failure = Invoke-TestInstaller @('-DesktopPath', $invalidDesktop) 1
    Assert-Installer ($failure -match 'runtime') 'Invalid runtime failure is unclear.'
    Assert-Installer (-not (Test-Path -LiteralPath (Join-Path $invalidDesktop 'CLIPFARM.lnk'))) 'Invalid runtime created a shortcut.'
    Assert-Installer (Test-Path -LiteralPath (Join-Path $clipfarmFixture 'runtime\keep.txt')) 'Invalid runtime was removed.'
    $env:CLIPFARM_INSTALLER_TEST_MINOR = '12'
    Remove-Item -LiteralPath (Join-Path $clipfarmFixture 'app.py')
    $failure = Invoke-TestInstaller @('-DesktopPath', $invalidDesktop) 1
    Assert-Installer ($failure -match 'ZIP') 'Incomplete extraction failure is unclear.'
    Remove-Item -LiteralPath (Join-Path $clipfarmFixture 'Install-CLIPFARM.ps1')
    $failure = Invoke-TestInstaller @('-DesktopPath', $invalidDesktop) 1
    Assert-Installer ($failure -match 'Install-CLIPFARM.ps1') 'Wrapper did not report its missing script.'
    Write-Host 'PASS: real Python/venv, branded COM shortcut, Unicode paths, runtime reuse, user data preservation, pip failure, fallback and wrapper exit status.'
} finally {
    $env:CLIPFARM_INSTALLER_TEST_LOG = $clipfarmSavedLog
    $env:CLIPFARM_INSTALLER_TEST_PIP_RESULT = $clipfarmSavedPip
    $env:CLIPFARM_INSTALLER_TEST_MINOR = $clipfarmSavedMinor
    # Only remove the unique directory created by this test, under the repository checks folder.
    $resolvedTestRoot = [IO.Path]::GetFullPath($clipfarmTestRoot)
    $resolvedChecks = [IO.Path]::GetFullPath($clipfarmChecks).TrimEnd('\') + '\'
    if (-not $resolvedTestRoot.StartsWith($resolvedChecks, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test cleanup path.' }
    if (Test-Path -LiteralPath $resolvedTestRoot) { Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force }
}
