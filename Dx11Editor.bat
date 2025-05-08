rem Get the parent directory
set "PARENT_DIR=%~dp0.."
pushd "%PARENT_DIR%"
set "PARENT_DIR=%CD%"
popd

rem Find the .uproject file in the parent directory
for %%f in ("%PARENT_DIR%\*.uproject") do set "PROJECT_PATH=%%f"

set "UE_EDITOR_PATH=C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64\UnrealEditor.exe"

"%UE_EDITOR_PATH%" "%PROJECT_PATH%" -d3d11