@echo off
setlocal
set "PYTHONUTF8=1"
pushd "%~dp0"
if errorlevel 1 (
  echo Cannot open the ThemeScope folder.
  pause
  exit /b 1
)
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3.12 "%~dp0scripts\setup_local.py"
goto finished
:python_fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%~dp0scripts\setup_local.py"
goto finished
:missing_python
echo Python is not installed or not on PATH. Install Python 3.12, reopen PowerShell, and retry.
set "THEMESCOPE_RESULT=1"
goto wait_and_exit
:finished
set "THEMESCOPE_RESULT=%ERRORLEVEL%"
:wait_and_exit
if not "%THEMESCOPE_RESULT%"=="0" echo Setup failed. Read the error above and README.md.
pause
popd
exit /b %THEMESCOPE_RESULT%
