@echo off
setlocal
cd /d "%~dp0"
py -3.12 scripts\bootstrap_dev.py
if errorlevel 1 (
  echo ThemeScope setup failed. Review the error above.
  pause
  exit /b 1
)
echo Run ThemeScope.cmd and open Snapshot and refresh, then select Refresh Data.
pause
exit /b 0
