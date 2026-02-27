@echo off
setlocal

REM === CONFIG ===
set STEAMCMD_EXE=D:\UE\SteamCMD\steamcmd.exe
set STEAM_USERNAME=sugarkickboy
set APP_BUILD_VDF=D:\UE\AncientBlood\AncientBloodCore\Config\automation\Steam\app_build.vdf

REM === RUN ===
"%STEAMCMD_EXE%" ^
	+login %STEAM_USERNAME% ^
	+run_app_build "%APP_BUILD_VDF%" ^
	+quit

echo.
echo Upload finished.
pause