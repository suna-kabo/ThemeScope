@echo off
rem Default vNext application. Select Refresh Data for a new completed session.
call "%~dp0ThemeScope.cmd" %*
exit /b %ERRORLEVEL%
