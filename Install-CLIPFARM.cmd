@echo off
setlocal DisableDelayedExpansion
title CLIPFARM - instalacja
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-CLIPFARM.ps1" %*
set "clipfarmExitCode=%errorlevel%"
echo.
if not "%clipfarmExitCode%"=="0" echo Instalacja nie powiodla sie. Sprawdz blad powyzej.
pause
exit /b %clipfarmExitCode%
