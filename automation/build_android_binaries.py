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

def run_build(ue_root: Path, uproject_path: Path, configuration: str):
    runuat_path = ue_root / "Engine" / "Build" / "BatchFiles" / "RunUAT.bat"
    if not runuat_path.exists():
        raise RuntimeError(f"RunUAT.bat not found at {runuat_path}")

    command = [
        str(runuat_path),
        "BuildCookRun",
        f"-project={uproject_path}",
        "-noP4",
        f"-clientconfig={configuration}",
        f"-serverconfig={configuration}",
        "-platform=Android",
        "-targetplatform=Android",
        "-build",
        "-skipcook",
        "-stage"
    ]

    print(f"Running Unreal Automation Tool:")
    print(" ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError("BuildCookRun failed with exit code", result.returncode)

def move_so_to_precompiled(project_root: Path, uproject_path: Path):
    stem = uproject_path.stem
    source_so = project_root / "Binaries" / "Android" / f"{stem}-arm64.so"
    target_dir = project_root / "AndroidPrecompiled"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_so = target_dir / f"{stem}-arm64.so"

    if source_so.exists():
        shutil.copy2(source_so, target_so)
        print(f"Copied {source_so.name} to {target_so}")
    else:
        raise RuntimeError(f"Could not find {source_so.name} in Binaries/Android.")

def build_android(configuration: str) -> bool:
    try:
        project_root = get_project_root()
        print(f"Project root: {project_root}")

        uproject_path = find_uproject(project_root)
        print(f"Found .uproject: {uproject_path.name}")

        ue_root = load_ue_root()
        print(f"Using Unreal Engine from: {ue_root}")
        
        print(f"Build configuration: {configuration}")

        run_build(ue_root, uproject_path, configuration)
        move_so_to_precompiled(project_root, uproject_path)
        return True
        
    except Exception as e:
        print(f"Build failed: {e}")
        input("Press Enter to exit...")
        return False

def parse_args():
    parser = argparse.ArgumentParser(description="Build android binaries for Quest 3")
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
    sys.exit(0 if build_android(args.config) else 1)
