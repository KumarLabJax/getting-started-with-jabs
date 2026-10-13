@echo off
rem Double-click launcher for Windows: runs start_jabs.ps1 without changing the execution policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_jabs.ps1" %*
pause
