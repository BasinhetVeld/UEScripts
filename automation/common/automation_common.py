from pathlib import Path
import configparser

def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]

def find_uproject(project_root: Path) -> Path:
    uproject_files = list(project_root.glob("*.uproject"))
    if not uproject_files:
        raise RuntimeError(f"No .uproject file found in project root: {project_root}")
    return uproject_files[0]

def load_ue_root() -> Path:
    config_path = Path(__file__).resolve().parents[1] / "config" / "project.config"
    if not config_path.exists():
        raise RuntimeError(f"project.config not found at: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        ue_root = Path(config["Paths"]["ue_root"])
    except KeyError:
        raise RuntimeError("Missing 'ue_root' in [Paths] section of project.config")

    if not ue_root.exists():
        raise RuntimeError(f"ue_root path does not exist: {ue_root}")

    return ue_root