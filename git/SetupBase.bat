@echo off

if "%1"=="" (
    echo "Usage: SetupHooks.bat [dev|cgi]. Call SetupCGI.bat or SetupDev.bat"
    exit /b 1
)

set HOOK_TYPE=%1

if /I not "%HOOK_TYPE%"=="dev" if /I not "%HOOK_TYPE%"=="cgi" (
    echo Invalid hook type: %HOOK_TYPE%
    echo "Usage: SetupHooks.bat [dev|cgi].
    exit /b 1
)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\.."

rem Ensure .githooks directory exists
if not exist ".githooks" mkdir .githooks

rem Copy selected hooks
xcopy /E /Y UEScripts\git\.githooks\%HOOK_TYPE% .githooks\

rem Install git lfs
git lfs install

rem Set git hook path
git config core.hooksPath .githooks

rem Show result
git config --get core.hooksPath

echo %HOOK_TYPE% hooks installed.
pause