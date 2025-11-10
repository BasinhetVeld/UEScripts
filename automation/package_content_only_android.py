
# This script packages for Android, specifically for Quest3.
# Arguments allowed are Development|Debug|Shipping
# Binaries for Android must exist at <ProjectDir>/Binaries/Android, they will not be built as part of this script


import subprocess
import shutil
import sys
import argparse
import os
from pathlib import Path
import configparser

from common.automation_common import (
    get_project_root,
    find_uproject,
    load_ue_root
)

from utils.modify_android_target import(
    modify_android_target
)

def make_android_target_backup(target_path: str, backup_path: str):
    if os.path.exists(backup_path):
        print("Backup still exists. Not creating backup")
        return
    
    try:
        with open(target_path, "rb") as rf, open(backup_path, "wb") as wf:
            wf.write(rf.read())
        print(f"[INFO] Backup created: {backup_path}")
    except Exception as e:
        raise RuntimeError("Failed creating backup.")

def restore_backup(backup_path: str, target_path: str):
    if not os.path.isfile(backup_path):
        raise RuntimeError("Failed to restore backup!")
    
    if os.path.exists(target_path):
        os.remove(target_path)

    print("restoring backup:")
    print(f"{backup_path} -> {target_path}")
    os.rename(backup_path, target_path)
    

def run_content_only_build(ue_root: Path, uproject_path: Path, configuration: str):
    runuat_path = ue_root / "Engine" / "Build" / "BatchFiles" / "RunUAT.bat"
    if not runuat_path.exists():
        raise RuntimeError(f"RunUAT.bat not found at {runuat_path}")

    command = [
        str(runuat_path),
        "BuildCookRun",
        f"-project={uproject_path}",
        "-noP4",
        "-nocompile",
        "-nocompileeditor",
        "-nobuild",
        f"-clientconfig={configuration}",
        f"-serverconfig={configuration}",
        "-platform=Android",
        "-targetplatform=Android",
        "-AdditionalCookerOptions=\"-targetdevice=NativeHMD\"", # Custom command that we use to detect whether we're building for HMD/Quest
        "-cook",
        "-pak",
        "-stage",
        "-package"
    ]

    print("Packaging content-only build:")
    print(" ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError(f"BuildCookRun failed with exit code {result.returncode}")

def find_apk(project_root: Path, uproject_path: Path) -> Path:
    apk_path = project_root / "Binaries" / "Android" / f"{uproject_path.stem}-arm64.apk"
    if not apk_path.exists():
        raise RuntimeError(f"APK not found after build: {apk_path}")
    return apk_path

def install_apk_to_quest(apk_path: Path):
    print(f"Installing APK to Quest: {apk_path}")
    result = subprocess.run(["adb", "install", "-r", str(apk_path)])
    if result.returncode != 0:
        raise RuntimeError(f"ADB install failed with exit code {result.returncode}")

def package_and_install(configuration: str) -> bool:
    
    project_root = get_project_root()
    uproject_path = find_uproject(project_root)
    ue_root = load_ue_root()
    project_name = os.path.splitext(uproject_path.name)[0]

    print(f"Project root: {project_root}")
    print(f"UProject: {uproject_path.name}")
    print(f"UE Root: {ue_root}")
    print(f"Build Configuration: {configuration}")
    
    android_target_path:str = os.path.join(project_root, "Binaries", "Android", f"{project_name}.target")
    # Backup
    backup_path = f"{android_target_path}.bak"
    
    try:

        make_android_target_backup(android_target_path, backup_path)
        # modify the Android <Project>.target. This edits absolute paths to represent the current project path - project plugins often use hardcoded system-specific paths
        modify_android_target(android_target_path)
        
        run_content_only_build(ue_root, uproject_path, configuration)
        apk_path = find_apk(project_root, uproject_path)
        install_apk_to_quest(apk_path)

        print("Package and install completed.")
    except Exception as e:
        print(f"Package and install failed: {e}")
        
    # Restore backup, even if we failed
    restore_backup(backup_path, android_target_path)
    input("Press Enter to exit...")

def parse_args():
    parser = argparse.ArgumentParser(description="Package and install updated content to Quest")
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="Development",
        choices=["Debug", "Development", "Shipping"],
        help="Build configuration (default: Development)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    sys.exit(0 if package_and_install(args.config) else 1)
