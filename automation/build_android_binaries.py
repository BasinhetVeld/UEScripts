import subprocess
import shutil
import sys
from pathlib import Path
import configparser

def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def find_uproject(project_root: Path) -> Path:
    uproject_files = list(project_root.glob("*.uproject"))
    if not uproject_files:
        print("No .uproject file found in project root:", project_root)
        input("Press Enter to exit...")
        sys.exit(1)
    return uproject_files[0]

def load_ue_root() -> Path:
    config_path = Path(__file__).resolve().parent / "config" / "project.config"
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

def load_build_settings() -> str:
    config_path = Path(__file__).resolve().parent / "config" / "build_android_binaries.config"
    if not config_path.exists():
        print(f"build_android_binaries.config not found at: {config_path}")
        input("Press Enter to exit...")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        return config["Build"]["configuration"]
    except KeyError:
        print("Missing 'configuration' in [Build] section of build_android_binaries.config")
        input("Press Enter to exit...")
        sys.exit(1)

def run_build(ue_root: Path, uproject_path: Path, configuration: str):
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
        f"-clientconfig={configuration}",
        f"-serverconfig={configuration}",
        "-platform=Android",
        "-targetplatform=Android",
        "-build",
        "-cook",
        "-pak",
        "-stage",
        "-archive"
        # Removed: "-archivedirectory=Saved/AndroidBuild"
    ]

    print(f"Running Unreal Automation Tool:")
    print(" ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        print("BuildCookRun failed with exit code", result.returncode)
        input("Press Enter to exit...")
        sys.exit(result.returncode)

def report_outputs(project_root: Path, uproject_path: Path):
    stem = uproject_path.stem
    output_dir = project_root / "Binaries" / "Android"
    apk_file = output_dir / f"{stem}-arm64.apk"
    so_file = output_dir / f"{stem}-arm64.so"

    print("\nBuild Output Summary:")
    if apk_file.exists():
        print(f"APK: {apk_file}")
    else:
        print(f"APK not found: {apk_file}")

    if so_file.exists():
        print(f"SO : {so_file}")
    else:
        print(f"SO not found: {so_file}")

def main():
    project_root = get_project_root()
    print(f"Project root: {project_root}")

    uproject_path = find_uproject(project_root)
    print(f"Found .uproject: {uproject_path.name}")

    ue_root = load_ue_root()
    print(f"Using Unreal Engine from: {ue_root}")

    configuration = load_build_settings()
    print(f"Build configuration: {configuration}")

    run_build(ue_root, uproject_path, configuration)
    report_outputs(project_root, uproject_path)

if __name__ == "__main__":
    main()
