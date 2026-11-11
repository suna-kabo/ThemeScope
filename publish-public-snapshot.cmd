@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-vnext\Scripts\python.exe" (
  ".venv-vnext\Scripts\python.exe" scripts\publish_public_snapshot.py %*
  exit /b
)
py -3.12 scripts\publish_public_snapshot.py %*
exit /b
