import subprocess
import shutil
import sys
import os
from pathlib import Path
import configparser

def get_project_root() -> Path:
    # Assumes script is in <project_root>/UEScripts/automation/
    return Path(__file__).resolve().parents[2]

def find_uproject(project_root: Path) -> Path:
    uproject_files = list(project_root.glob("*.uproject"))
    if not uproject_files:
        print("No .uproject file found in project root:", project_root)
        input("Press Enter to exit...")
        sys.exit(1)
    return uproject_files[0]

def load_ue_root() -> Path:
    config_path = Path(__file__).resolve().parents[0] / "config" / "project.config"
    if not config_path.exists():
        print(f"project.config not found at: {config_path}")
        input("Press Enter to exit...")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        ue_root = Path(config["Paths"]["ue_root"])
    except KeyError:
        print("Missing 'ue_root' in [Paths] section of project.config")
        input("Press Enter to exit...")
        sys.exit(1)

    if not ue_root.exists():
        print(f"ue_root path does not exist: {ue_root}")
        input("Press Enter to exit...")
        sys.exit(1)

    return ue_root

def run_build(ue_root: Path, uproject_path: Path):
    runuat_path = ue_root / "Engine" / "Build" / "BatchFiles" / "RunUAT.bat"
    if not runuat_path.exists():
        print(f"RunUAT.bat not found at {runuat_path}")
        input("Press Enter to exit...")
        sys.exit(1)

    command = [
        str(runuat_path),
        "BuildCookRun",
        f"-project={uproject_path}",
        "-noP4",
        "-clientconfig=Shipping",
        "-serverconfig=Shipping",
        "-platform=Android",
        "-targetplatform=Android",
        "-build",
        "-cook",
        "-pak",
        "-stage",
        "-archive",
        "-archivedirectory=Saved/AndroidBuild"
    ]

    print(f"Running Unreal Automation Tool:")
    print(" ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        print("BuildCookRun failed with exit code", result.returncode)
        input("Press Enter to exit...")
        sys.exit(result.returncode)

def copy_binaries(project_root: Path):
    lib_name = f"lib{uproject_path.stem}.so"
    source_so = project_root / "Saved" / "AndroidBuild" / "Android_ASTC" / "Engine" / "Binaries" / "Android" / lib_name
    target_dir = project_root / "Binaries" / "AndroidPrecompiled"
    target_dir.mkdir(parents=True, exist_ok=True)

    if source_so.exists():
        shutil.copy2(source_so, target_dir / "libUE4.so")
        print(f"Copied libUE4.so to {target_dir}")
    else:
        input("Press Enter to exit...")
        print("libUE4.so not found. Build may have failed or was generated for a different texture format.")

def main():
    project_root = get_project_root()
    print(f"Project root: {project_root}")

    uproject_path = find_uproject(project_root)
    print(f"Found .uproject: {uproject_path.name}")

    ue_root = load_ue_root()
    print(f"Using Unreal Engine from: {ue_root}")

    run_build(ue_root, uproject_path)
    copy_binaries(project_root)

if __name__ == "__main__":
    main()