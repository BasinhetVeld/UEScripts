@echo off

if "%1"=="" (
    echo "Usage: SetupHooks.bat [dev|cgi]. Call SetupCGI.bat or SetupDev.bat"
    pause
    exit /b 1
)

set HOOK_TYPE=%1

if /I not "%HOOK_TYPE%"=="dev" if /I not "%HOOK_TYPE%"=="cgi" (
    echo Invalid hook type: %HOOK_TYPE%
    echo "Usage: SetupHooks.bat [dev|cgi].
    pause
    exit /b 1
)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\.."

rem Install git lfs
git lfs install

rem Set git hook path
git config core.hooksPath ".githooks\%HOOK_TYPE%"

rem Show result
echo %HOOK_TYPE% hooks installed:
git config --get core.hooksPath

echo "Your project will use .githooks\%HOOK_TYPE% for its git hooks"

pause
