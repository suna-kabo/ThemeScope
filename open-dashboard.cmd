@echo off
rem Default vNext application. Open Snapshot and refresh, then select Refresh Data for a new completed session.
call "%~dp0ThemeScope.cmd" %*
exit /b %ERRORLEVEL%
