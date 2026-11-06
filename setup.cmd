@echo off
setlocal
cd /d "%~dp0"
py -3.12 scripts\bootstrap_dev.py
if errorlevel 1 (
  echo ThemeScope setup failed. Review the error above.
  pause
  exit /b 1
)
echo Run ThemeScope.cmd and select Refresh Data in the application.
pause
exit /b 0
