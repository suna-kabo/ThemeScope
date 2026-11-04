@echo off
setlocal
set "PYTHONUTF8=1"
pushd "%~dp0"
if errorlevel 1 (
  echo Cannot open the ThemeScope folder.
  pause
  exit /b 1
)
if not exist "%~dp0.venv\Scripts\python.exe" goto not_ready
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\serve_local.py" --site %*
set "THEMESCOPE_RESULT=%ERRORLEVEL%"
goto finished
:not_ready
echo Run setup.cmd first. The local Python environment is missing.
set "THEMESCOPE_RESULT=1"
:finished
if not "%THEMESCOPE_RESULT%"=="0" echo Could not preview site. Read the error above.
pause
popd
exit /b %THEMESCOPE_RESULT%
