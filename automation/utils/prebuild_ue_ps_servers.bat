@echo off
setlocal EnableExtensions

REM ===============================================================
REM Build-only script for UE Pixel Streaming (mirrors start.bat setup)
REM Usage:
REM   build_only.bat "X:\...\WebServers\SignallingWebServer\platform_scripts\cmd"
REM Does:
REM   - Install embedded Node into <cmd>\node (if missing), from WebServers\NODE_VERSION
REM   - npm install at WebServers root only if Node was just installed
REM   - Build Common (cjs) + Signalling (cjs) if dist missing
REM   - Build Frontend into SignallingWebServer\www (always)
REM   - Build Wilbur (if dist missing)
REM   - DOES NOT start the server
REM ===============================================================

REM --- require 1 arg: path to platform_scripts\cmd
if "%~1"=="" (
  echo [!] Please pass the path to platform_scripts\cmd
  echo     Example:
  echo     build_only.bat "D:\UE\Proj\Samples\PixelStreaming\WebServers\SignallingWebServer\platform_scripts\cmd"
  exit /b 2
)

REM --- normalize the cmd dir
for %%I in ("%~1") do set "CMD_DIR=%%~fI"

REM --- derive main folders
pushd "%CMD_DIR%\..\.."
set "WILBUR_DIR=%CD%"                                         REM ...\SignallingWebServer
popd

pushd "%WILBUR_DIR%\.."
set "WEBROOTS_DIR=%CD%"                                       REM ...\WebServers
popd

set "COMMON_DIR=%WEBROOTS_DIR%\Common"
set "SIGNALLING_LIB_DIR=%WEBROOTS_DIR%\Signalling"
set "FRONTEND_LIB=%WEBROOTS_DIR%\Frontend\library"
set "FRONTEND_UI_LIB=%WEBROOTS_DIR%\Frontend\ui-library"
set "FRONTEND_TS=%WEBROOTS_DIR%\Frontend\implementations\typescript"
set "FRONTEND_DIR=%WILBUR_DIR%\www"

echo [i] WebServers dir:     %WEBROOTS_DIR%
echo [i] Wilbur dir:         %WILBUR_DIR%
echo [i] Frontend output:    %FRONTEND_DIR%
echo.

REM -----------------------------------------------------------------------
REM SetupNode (like common.bat) — fetch embedded Node if missing
REM -----------------------------------------------------------------------
set "NODE_DIR=%CMD_DIR%\node"
set "LOCAL_NODE=%NODE_DIR%\node.exe"
set "NPM_EXE=npm"
set "INSTALL_DEPS=1"

if exist "%LOCAL_NODE%" goto :have_local_node

REM read NODE_VERSION from WebServers\NODE_VERSION (e.g., v18.17.1)
set "NODE_VERSION_FILE=%WEBROOTS_DIR%\NODE_VERSION"
if not exist "%NODE_VERSION_FILE%" (
  echo [!] Missing %NODE_VERSION_FILE% ; cannot determine Node version to install.
  echo     Either run once with UE's start.bat, or install Node on PATH and re-run.
  exit /b 1
)

set /p NODE_VERSION=<"%NODE_VERSION_FILE%"
if "%NODE_VERSION%"=="" (
  echo [!] NODE_VERSION file is empty.
  exit /b 1
)

REM check curl and tar
set "TAR_EXE=%SystemRoot%\System32\tar.exe"
where curl >nul 2>nul
if errorlevel 1 (
  echo [!] curl not found on PATH. Windows 10+ usually has it. Install curl or add to PATH.
  exit /b 1
)
if not exist "%TAR_EXE%" (
  echo [!] tar.exe not found at %TAR_EXE%. Install a tar-capable tool or ensure Windows tar is available.
  exit /b 1
)

echo [*] Installing embedded Node %NODE_VERSION% into:
echo     %NODE_DIR%

mkdir "%NODE_DIR%" >nul 2>nul
pushd "%CMD_DIR%"
set "NODE_ZIP=node.zip"
set "NODE_NAME=node-%NODE_VERSION%-win-x64"
REM download Node
curl -L -o "%NODE_ZIP%" "https://nodejs.org/dist/%NODE_VERSION%/%NODE_NAME%.zip"
if errorlevel 1 (
  echo [!] Failed to download Node from nodejs.org.
  popd
  exit /b 1
)
REM extract
"%TAR_EXE%" -xf "%NODE_ZIP%"
if errorlevel 1 (
  echo [!] Failed to extract Node zip.
  popd
  exit /b 1
)
REM rename to 'node'
if exist "%CMD_DIR%\%NODE_NAME%" (
  rmdir /s /q "%NODE_DIR%" >nul 2>nul
  ren "%NODE_NAME%" "node"
) else (
  echo [!] Expected folder "%NODE_NAME%" not found after extraction.
  del "%NODE_ZIP%" >nul 2>nul
  popd
  exit /b 1
)
del "%NODE_ZIP%" >nul 2>nul
popd

:have_local_node
REM prefer embedded npm if present
if exist "%LOCAL_NODE%" (
  set "PATH=%NODE_DIR%;%PATH%"
  set "NPM_EXE=%CMD_DIR%\node\npm"
)

REM if we just installed Node, install deps at WebServers root (like common.bat)
if not "%INSTALL_DEPS%"=="1" goto :skip_deps
echo [*] Installing workspace dependencies (npm install)...
pushd "%WEBROOTS_DIR%"
call "%NPM_EXE%" install
if errorlevel 1 (
  echo [!] npm install failed.
  popd
  exit /b 1
)
popd
:skip_deps

REM -----------------------------------------------------------------------
REM SetupLibraries (Common, Signalling) — build if dist missing
REM -----------------------------------------------------------------------
if exist "%COMMON_DIR%\dist" goto :common_ok
echo [*] Building Common (cjs)...
pushd "%COMMON_DIR%"
call "%NPM_EXE%" run build:cjs
if errorlevel 1 ( echo [!] Common build failed. & popd & exit /b 1 )
popd
:common_ok

if exist "%SIGNALLING_LIB_DIR%\dist" goto :signalling_ok
echo [*] Building Signalling (cjs)...
pushd "%SIGNALLING_LIB_DIR%"
call "%NPM_EXE%" run build:cjs
if errorlevel 1 ( echo [!] Signalling build failed. & popd & exit /b 1 )
popd
:signalling_ok

REM -----------------------------------------------------------------------
REM SetupFrontend — always emit to www (via WEBPACK_OUTPUT_PATH)
REM -----------------------------------------------------------------------
if not exist "%FRONTEND_DIR%" mkdir "%FRONTEND_DIR%"
set "WEBPACK_OUTPUT_PATH=%FRONTEND_DIR%"

echo [*] Building Frontend\library (cjs)...
pushd "%FRONTEND_LIB%"
call "%NPM_EXE%" run build:cjs
if errorlevel 1 ( echo [!] Frontend\library build failed. & popd & exit /b 1 )
popd

echo [*] Building Frontend\ui-library (cjs)...
pushd "%FRONTEND_UI_LIB%"
call "%NPM_EXE%" run build:cjs
if errorlevel 1 ( echo [!] Frontend\ui-library build failed. & popd & exit /b 1 )
popd

echo [*] Building Frontend\implementations\typescript (dev)...
pushd "%FRONTEND_TS%"
set "WEBPACK_OUTPUT_PATH=%FRONTEND_DIR%"
call "%NPM_EXE%" run build:dev
if errorlevel 1 (
  echo [!] build:dev failed, trying build ...
  call "%NPM_EXE%" run build
  if errorlevel 1 ( echo [!] Frontend implementation build failed. & popd & exit /b 1 )
)
popd

REM -----------------------------------------------------------------------
REM BuildWilbur — build if dist missing
REM -----------------------------------------------------------------------
if exist "%WILBUR_DIR%\dist\index.js" goto :wilbur_ok
echo [*] Building Wilbur (dist missing)...
pushd "%WILBUR_DIR%"
call "%NPM_EXE%" run build
if errorlevel 1 ( echo [!] Wilbur build failed. & popd & exit /b 1 )
popd
:wilbur_ok

echo.
if exist "%FRONTEND_DIR%\player.html" (
  echo [OK] Frontend ready at: %FRONTEND_DIR%
) else (
  echo [!] Warning: player.html not found in %FRONTEND_DIR%
)

if exist "%WILBUR_DIR%\dist\index.js" (
  echo [OK] Wilbur dist present: %WILBUR_DIR%\dist
) else (
  echo [!] Wilbur dist missing: %WILBUR_DIR%\dist
)

echo.
echo [DONE] Build steps completed. Server was not started.
echo [TIP] Later, start with:
echo       node "%WILBUR_DIR%\dist\index.js" --serve --http_root="%FRONTEND_DIR%" --https=false --https_redirect=false --peer_options="{\"iceServers\":[]}"
exit /b 0
