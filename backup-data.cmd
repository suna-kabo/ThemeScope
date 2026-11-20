@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-vnext\Scripts\python.exe" (
  ".venv-vnext\Scripts\python.exe" scripts\local_tools.py backup
) else (
  py -3.12 scripts\local_tools.py backup
)
set "exitcode=%errorlevel%"
pause
exit /b %exitcode%
