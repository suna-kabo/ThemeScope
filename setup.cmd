@echo off
setlocal
cd /d "%~dp0"
py -3.12 scripts\bootstrap_dev.py
if errorlevel 1 (
  echo ThemeScope setup failed. Review the error above.
  pause
  exit /b 1
)
".venv-vnext\Scripts\python.exe" scripts\local_tools.py credentials --if-missing
if errorlevel 1 (
  echo Credential setup did not finish. Run configure-credentials.cmd to retry.
  pause
  exit /b 1
)
echo Setup complete. Double-click ThemeScope.cmd to open your local dashboard.
pause
exit /b 0
