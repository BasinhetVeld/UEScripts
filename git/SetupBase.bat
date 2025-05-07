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

rem Check for Content plugin submodule
if exist "Plugins\Content\.git" (
    echo Found Git repo in Plugins\Content. Installing LFS...
    pushd Plugins\Content
    git lfs install
    popd
) else (
    echo Plugins\Content is not a git repo or does not exist.
)

rem Show result
echo %HOOK_TYPE% hooks installed:
git config --get core.hooksPath

echo "Your project will use .githooks\%HOOK_TYPE% for its git hooks"

pause
