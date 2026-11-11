@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-vnext\Scripts\python.exe" (
  py -3.12 scripts\bootstrap_dev.py
  if errorlevel 1 goto failed
)
".venv-vnext\Scripts\python.exe" scripts\run_vnext.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo ThemeScope could not start. Review the error above.
pause
exit /b 1
