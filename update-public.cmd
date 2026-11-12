@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-vnext\Scripts\python.exe" (
  ".venv-vnext\Scripts\python.exe" scripts\update_public.py %*
  exit /b
)
py -3.12 scripts\update_public.py %*
exit /b
