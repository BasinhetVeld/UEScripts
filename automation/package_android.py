import subprocess
import shutil
import sys
import argparse
from pathlib import Path
import configparser

from common.automation_common import (
    get_project_root,
    find_uproject,
    load_ue_root
)

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
    try:
        project_root = get_project_root()
        uproject_path = find_uproject(project_root)
        ue_root = load_ue_root()

        print(f"Project root: {project_root}")
        print(f"UProject: {uproject_path.name}")
        print(f"UE Root: {ue_root}")
        print(f"Build Configuration: {configuration}")

        run_content_only_build(ue_root, uproject_path, configuration)
        apk_path = find_apk(project_root, uproject_path)
        install_apk_to_quest(apk_path)

        print("Package and install completed.")
        return True

    except Exception as e:
        print(f"Package and install failed: {e}")
        input("Press Enter to exit...")
        return False

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
