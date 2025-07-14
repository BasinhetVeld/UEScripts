import subprocess
import shutil
import sys
from pathlib import Path
import configparser

from common.automation_common import (
    get_project_root,
    find_uproject,
    load_ue_root
)

def load_build_settings() -> str:
    config_path = Path(__file__).resolve().parent / "config" / "build_android_binaries.config"
    if not config_path.exists():
        raise RuntimeError(f"build_android_binaries.config not found at: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        return config["Build"]["configuration"]
    except KeyError:
        raise RuntimeError("Missing 'configuration' in [Build] section of build_android_binaries.config")

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
        "-cook",
        "-pak",
        "-stage",
        "-archive"
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

def build_android() -> bool:
    try:
        project_root = get_project_root()
        print(f"Project root: {project_root}")

        uproject_path = find_uproject(project_root)
        print(f"Found .uproject: {uproject_path.name}")

        ue_root = load_ue_root()
        print(f"Using Unreal Engine from: {ue_root}")

        configuration = load_build_settings()
        print(f"Build configuration: {configuration}")

        run_build(ue_root, uproject_path, configuration)
        move_so_to_precompiled(project_root, uproject_path)
        return True
        
    except Exception as e:
        print(f"Build failed: {e}")
        input("Press Enter to exit...")
        return False

if __name__ == "__main__":
    sys.exit(0 if build_android() else 1)
