@echo off
setlocal EnableExtensions

REM ===============================================================
REM Minimal, build-only script for UE Pixel Streaming (UE 5.5)
REM Usage:
REM   build_only.bat "X:\...\Samples\PixelStreaming\WebServers\SignallingWebServer\platform_scripts\cmd"
REM Does:
REM   - Prepends embedded Node if present in the given cmd folder
REM   - Builds Common + Signalling (only if dist missing)
REM   - Builds Frontend into SignallingWebServer\www (always)
REM   - Builds Wilbur (only if dist missing)
REM   - Does NOT start the server
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
set "WILBUR_DIR=%CD%"
popd

pushd "%WILBUR_DIR%\.."
set "WEBROOTS_DIR=%CD%"
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

REM --- use embedded Node if present (no paren blocks)
set "NODE_DIR=%CMD_DIR%\node"
set "LOCAL_NODE=%NODE_DIR%\node.exe"
if exist "%LOCAL_NODE%" (
  REM avoid PATH expansion issues by jumping to a label
  goto :have_local_node
) else (
  goto :no_local_node
)

:have_local_node
set "PATH=%NODE_DIR%;%PATH%"
goto :after_node

:no_local_node
echo [i] Embedded Node not found at: %NODE_DIR%
echo     Will use system Node/npm if available on PATH.
goto :after_node

:after_node

REM --- build Common (if needed)
if exist "%COMMON_DIR%\dist" goto :common_ok
echo [*] Building Common (cjs)...
pushd "%COMMON_DIR%"
call npm run build:cjs
if errorlevel 1 (
  echo [!] Common build failed.
  popd
  exit /b 1
)
popd
:common_ok

REM --- build Signalling (if needed)
if exist "%SIGNALLING_LIB_DIR%\dist" goto :signalling_ok
echo [*] Building Signalling (cjs)...
pushd "%SIGNALLING_LIB_DIR%"
call npm run build:cjs
if errorlevel 1 (
  echo [!] Signalling build failed.
  popd
  exit /b 1
)
popd
:signalling_ok

REM --- build Frontend (always emit to www)
if not exist "%FRONTEND_DIR%" mkdir "%FRONTEND_DIR%"
set "WEBPACK_OUTPUT_PATH=%FRONTEND_DIR%"

echo [*] Building Frontend\library (cjs)...
pushd "%FRONTEND_LIB%"
call npm run build:cjs
if errorlevel 1 (
  echo [!] Frontend\library build failed.
  popd
  exit /b 1
)
popd

echo [*] Building Frontend\ui-library (cjs)...
pushd "%FRONTEND_UI_LIB%"
call npm run build:cjs
if errorlevel 1 (
  echo [!] Frontend\ui-library build failed.
  popd
  exit /b 1
)
popd

echo [*] Building Frontend\implementations\typescript (dev)...
pushd "%FRONTEND_TS%"
set "WEBPACK_OUTPUT_PATH=%FRONTEND_DIR%"
call npm run build:dev
if errorlevel 1 (
  echo [!] build:dev failed, trying build ...
  call npm run build
  if errorlevel 1 (
    echo [!] Frontend implementation build failed.
    popd
    exit /b 1
  )
)
popd

REM --- build Wilbur (if needed)
if exist "%WILBUR_DIR%\dist\index.js" goto :wilbur_ok
echo [*] Building Wilbur (dist missing)...
pushd "%WILBUR_DIR%"
call npm run build
if errorlevel 1 (
  echo [!] Wilbur build failed.
  popd
  exit /b 1
)
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
