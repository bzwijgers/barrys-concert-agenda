@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Barry-Concertapp-Bijwerken.ps1"
echo.
pause
