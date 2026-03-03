from __future__ import annotations

import configparser
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

from automation.common.automation_common import (
    find_uproject,
    get_project_root,
    load_ue_root,
)


@dataclass(frozen=True)
class Paths:
    ue_root: Path
    dev_repo_root: Path
    uproject: Path


def _hide_own_console_window_if_any() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32")
        user32 = ctypes.WinDLL("user32")
        h_wnd = kernel32.GetConsoleWindow()
        if h_wnd:
            user32.ShowWindow(h_wnd, 0)  # SW_HIDE
    except Exception:
        pass


def _load_dev_repo_root_from_project_config() -> Path:
    project_root = get_project_root()
    config_path = project_root / "UEScripts" / "automation" / "config" / "project.config"
    if not config_path.exists():
        raise RuntimeError(f"project.config not found at: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        dev_repo_root = Path(config["Paths"]["dev_repo_root"])
    except KeyError:
        raise RuntimeError("Missing 'dev_repo_root' in [Paths] section of project.config")

    if not dev_repo_root.exists():
        raise RuntimeError(f"dev_repo_root path does not exist: {dev_repo_root}")

    return dev_repo_root


def _resolve_paths(argv: List[str]) -> Paths:
    ue_root_override: Path | None = None
    dev_repo_root_override: Path | None = None

    def pop_arg_value(flag: str) -> str | None:
        if flag in argv:
            index = argv.index(flag)
            if index + 1 >= len(argv):
                raise RuntimeError(f"Missing value after {flag}")
            value = argv[index + 1]
            del argv[index : index + 2]
            return value
        return None

    ue_root_value = pop_arg_value("--ue_root")
    dev_repo_root_value = pop_arg_value("--dev_repo_root")

    if ue_root_value:
        ue_root_override = Path(ue_root_value)
        if not ue_root_override.exists():
            raise RuntimeError(f"--ue_root does not exist: {ue_root_override}")

    if dev_repo_root_value:
        dev_repo_root_override = Path(dev_repo_root_value)
        if not dev_repo_root_override.exists():
            raise RuntimeError(f"--dev_repo_root does not exist: {dev_repo_root_override}")

    ue_root = ue_root_override if ue_root_override else load_ue_root()
    dev_repo_root = dev_repo_root_override if dev_repo_root_override else _load_dev_repo_root_from_project_config()
    uproject = find_uproject(dev_repo_root)

    return Paths(ue_root=ue_root, dev_repo_root=dev_repo_root, uproject=uproject)


def _load_predefined_maps(config: configparser.ConfigParser) -> List[Tuple[str, str]]:
    if "Maps" not in config:
        return []

    maps_section = config["Maps"]
    results: List[Tuple[str, str]] = []

    for key, value in maps_section.items():
        if key.lower() == "predefined":
            continue
        name = key.strip()
        path = value.strip()
        if name and path:
            results.append((name, path))

    if "predefined" in maps_section:
        raw = maps_section.get("predefined", "").strip()
        if raw:
            for entry in raw.split(","):
                map_path = entry.strip()
                if map_path:
                    display_name = map_path.split("/")[-1]
                    results.append((display_name, map_path))

    seen: set[str] = set()
    deduped: List[Tuple[str, str]] = []
    for name, path in results:
        if path not in seen:
            seen.add(path)
            deduped.append((name, path))

    return deduped


def _unreal_editor_exe(ue_root: Path) -> Path:
    exe_path = ue_root / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
    if not exe_path.exists():
        raise RuntimeError(f"UnrealEditor.exe not found at: {exe_path}")
    return exe_path


def _parse_optional_int(text: str) -> int | None:
    stripped = text.strip()
    if not stripped:
        return None
    return int(stripped)


def _build_command(
    *,
    exe_path: Path,
    uproject: Path,
    mode: str,
    map_value: str,
    extra_args: str,
    enable_log: bool,
    new_console: bool,
    pos_x: str,
    pos_y: str,
    res_x: str,
    res_y: str,
) -> List[str]:
    cmd: List[str] = [str(exe_path), str(uproject)]

    mode_lower = mode.lower()

    if mode_lower != "client":
        if map_value.strip():
            cmd.append(map_value.strip())
    else:
        # Keep your current behavior:
        cmd.append("127.0.0.1")

    if mode_lower == "ds":
        cmd.append("-server")
    elif mode_lower == "listen server":
        cmd.extend(["-game", "-listen"])
    elif mode_lower == "client":
        cmd.append("-game")
    else:
        raise RuntimeError(f"Unknown mode: {mode}")

    if enable_log:
        cmd.append("-log")

    if pos_x.strip():
        cmd.append(f"-PosX={pos_x.strip()}")
    if pos_y.strip():
        cmd.append(f"-PosY={pos_y.strip()}")

    parsed_res_x = _parse_optional_int(res_x) if res_x.strip() else None
    parsed_res_y = _parse_optional_int(res_y) if res_y.strip() else None
    if parsed_res_x is not None or parsed_res_y is not None:
        cmd.append("-WINDOWED")
        if parsed_res_x is not None:
            cmd.append(f"-ResX={parsed_res_x}")
        if parsed_res_y is not None:
            cmd.append(f"-ResY={parsed_res_y}")

    if new_console:
        cmd.append("-NewConsole")

    if extra_args.strip():
        cmd.extend(extra_args.strip().split())

    return cmd


def _format_command_for_display(cmd: List[str]) -> str:
    def quote(arg: str) -> str:
        if not arg:
            return '""'
        if any(ch.isspace() for ch in arg) or '"' in arg:
            return '"' + arg.replace('"', '\\"') + '"'
        return arg

    return " ".join(quote(arg) for arg in cmd)


# ---------------------------
# Config persistence
# ---------------------------

def _mode_to_section(mode: str) -> str:
    # Stable section names in config file
    normalized = mode.strip().lower()
    if normalized == "ds":
        return "State.DS"
    if normalized == "client":
        return "State.Client"
    if normalized == "listen server":
        return "State.ListenServer"
    # fallback
    return "State.DS"


def _load_config_file(path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if path.exists():
        config.read(path)
    return config


def _save_config_file(path: Path, config: configparser.ConfigParser) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        config.write(file)


def main() -> int:
    _hide_own_console_window_if_any()

    argv = sys.argv[1:]
    try:
        paths = _resolve_paths(argv)
        exe_path = _unreal_editor_exe(paths.ue_root)
    except Exception as exc:
        try:
            tk.Tk().withdraw()
            messagebox.showerror("RunEditor", str(exc))
        except Exception:
            print(f"[RunEditor] Error: {exc}")
        return 1

    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / "RunEditor.config"

    config = _load_config_file(config_path)
    predefined_maps = _load_predefined_maps(config)

    root = tk.Tk()
    root.title("Run Editor")
    root.columnconfigure(1, weight=1)

    # Variables
    default_mode = config.get("State", "last_mode", fallback="DS")
    mode_var = tk.StringVar(value=default_mode)

    map_dropdown_var = tk.StringVar(value=(predefined_maps[0][0] if predefined_maps else ""))
    map_text_var = tk.StringVar(value="")
    extra_args_var = tk.StringVar(value="")
    log_var = tk.BooleanVar(value=True)
    new_console_var = tk.BooleanVar(value=True)
    pos_x_var = tk.StringVar(value="0")
    pos_y_var = tk.StringVar(value="0")
    res_x_var = tk.StringVar(value="")
    res_y_var = tk.StringVar(value="")

    def add_row(label: str, widget: tk.Widget, row: int) -> None:
        ttk.Label(root, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=6)
        widget.grid(row=row, column=1, sticky="ew", padx=10, pady=6)

    # UI
    mode_combo = ttk.Combobox(
        root,
        textvariable=mode_var,
        values=["DS", "Listen Server", "Client"],
        state="readonly",
    )
    add_row("Mode", mode_combo, 0)

    map_names = [name for name, _ in predefined_maps]
    map_dropdown = ttk.Combobox(
        root,
        textvariable=map_dropdown_var,
        values=map_names,
        state="readonly" if map_names else "disabled",
    )
    add_row("Map", map_dropdown, 1)

    map_entry = ttk.Entry(root, textvariable=map_text_var)
    add_row("Map (Custom)", map_entry, 2)

    extra_entry = ttk.Entry(root, textvariable=extra_args_var)
    add_row("Extra args", extra_entry, 3)

    flags_frame = ttk.Frame(root)
    ttk.Checkbutton(flags_frame, text="Log (-log)", variable=log_var).pack(side="left", padx=(0, 12))
    ttk.Checkbutton(flags_frame, text="New Console (-NewConsole)", variable=new_console_var).pack(side="left")
    add_row("Options", flags_frame, 4)

    pos_frame = ttk.Frame(root)
    ttk.Label(pos_frame, text="PosX").pack(side="left")
    ttk.Entry(pos_frame, textvariable=pos_x_var, width=6).pack(side="left", padx=(6, 14))
    ttk.Label(pos_frame, text="PosY").pack(side="left")
    ttk.Entry(pos_frame, textvariable=pos_y_var, width=6).pack(side="left", padx=(6, 0))
    add_row("Window position", pos_frame, 5)

    res_frame = ttk.Frame(root)
    ttk.Label(res_frame, text="ResX").pack(side="left")
    ttk.Entry(res_frame, textvariable=res_x_var, width=8).pack(side="left", padx=(6, 14))
    ttk.Label(res_frame, text="ResY").pack(side="left")
    ttk.Entry(res_frame, textvariable=res_y_var, width=8).pack(side="left", padx=(6, 0))
    add_row("Windowed resolution", res_frame, 6)

    info_text = f"UE: {paths.ue_root}\nProject: {paths.dev_repo_root}\nUProject: {paths.uproject}\nConfig: {config_path}"
    info_label = ttk.Label(root, text=info_text, justify="left")
    add_row("Paths", info_label, 7)

    # Command preview
    command_preview = tk.Text(root, height=3, wrap="word")
    command_preview.configure(state="disabled")
    add_row("Command preview", command_preview, 8)

    # -------------
    # State load/save logic
    # -------------

    is_applying_mode_state = False
    pending_save_handle: str | None = None

    def _ensure_section(section: str) -> None:
        if not config.has_section(section):
            config.add_section(section)

    def _apply_mode_state(mode: str) -> None:
        nonlocal is_applying_mode_state
        is_applying_mode_state = True
        try:
            section = _mode_to_section(mode)
            if not config.has_section(section):
                # No saved settings for this mode yet: keep current values
                return

            map_dropdown_var.set(config.get(section, "map_dropdown", fallback=map_dropdown_var.get()))
            map_text_var.set(config.get(section, "map_text", fallback=map_text_var.get()))
            extra_args_var.set(config.get(section, "extra_args", fallback=extra_args_var.get()))
            log_var.set(config.getboolean(section, "log", fallback=log_var.get()))
            new_console_var.set(config.getboolean(section, "new_console", fallback=new_console_var.get()))
            pos_x_var.set(config.get(section, "pos_x", fallback=pos_x_var.get()))
            pos_y_var.set(config.get(section, "pos_y", fallback=pos_y_var.get()))
            res_x_var.set(config.get(section, "res_x", fallback=res_x_var.get()))
            res_y_var.set(config.get(section, "res_y", fallback=res_y_var.get()))
        finally:
            is_applying_mode_state = False

    def _write_current_state_to_config() -> None:
        # Store last mode
        _ensure_section("State")
        config.set("State", "last_mode", mode_var.get())

        # Store per-mode
        section = _mode_to_section(mode_var.get())
        _ensure_section(section)

        config.set(section, "map_dropdown", map_dropdown_var.get())
        config.set(section, "map_text", map_text_var.get())
        config.set(section, "extra_args", extra_args_var.get())
        config.set(section, "log", "true" if log_var.get() else "false")
        config.set(section, "new_console", "true" if new_console_var.get() else "false")
        config.set(section, "pos_x", pos_x_var.get())
        config.set(section, "pos_y", pos_y_var.get())
        config.set(section, "res_x", res_x_var.get())
        config.set(section, "res_y", res_y_var.get())

        _save_config_file(config_path, config)

    def _schedule_save() -> None:
        # Debounce writes (typing in entry boxes)
        nonlocal pending_save_handle
        if is_applying_mode_state:
            return

        if pending_save_handle is not None:
            root.after_cancel(pending_save_handle)
            pending_save_handle = None

        pending_save_handle = root.after(250, _write_current_state_to_config)

    def resolve_selected_map() -> str:
        text_value = map_text_var.get().strip()
        if text_value:
            return text_value

        selected_name = map_dropdown_var.get().strip()
        if not selected_name:
            return ""

        for name, path in predefined_maps:
            if name == selected_name:
                return path

        return selected_name

    def get_current_command() -> List[str]:
        chosen_map = resolve_selected_map()
        return _build_command(
            exe_path=exe_path,
            uproject=paths.uproject,
            mode=mode_var.get(),
            map_value=chosen_map,
            extra_args=extra_args_var.get(),
            enable_log=log_var.get(),
            new_console=new_console_var.get(),
            pos_x=pos_x_var.get(),
            pos_y=pos_y_var.get(),
            res_x=res_x_var.get(),
            res_y=res_y_var.get(),
        )

    def update_command_preview(*_args: object) -> None:
        try:
            cmd = get_current_command()
            text = _format_command_for_display(cmd)
        except Exception as exc:
            text = f"[Invalid settings] {exc}"

        command_preview.configure(state="normal")
        command_preview.delete("1.0", "end")
        command_preview.insert("1.0", text)
        command_preview.configure(state="disabled")

        _schedule_save()

    # Apply saved state for initial mode
    _apply_mode_state(mode_var.get())

    # Save+preview update hooks
    for var in [map_dropdown_var, map_text_var, extra_args_var, pos_x_var, pos_y_var, res_x_var, res_y_var]:
        var.trace_add("write", update_command_preview)
    for var in [log_var, new_console_var]:
        var.trace_add("write", update_command_preview)

    def on_mode_changed(*_args: object) -> None:
        # Save last mode immediately, then apply that mode's stored settings
        _ensure_section("State")
        config.set("State", "last_mode", mode_var.get())
        _save_config_file(config_path, config)

        _apply_mode_state(mode_var.get())
        update_command_preview()

    mode_var.trace_add("write", on_mode_changed)
    mode_combo.bind("<<ComboboxSelected>>", lambda _e: on_mode_changed())

    # Initial preview + ensure we persist at least once
    update_command_preview()
    _schedule_save()

    def on_run() -> None:
        try:
            cmd = get_current_command()

            creation_flags = 0
            if sys.platform.startswith("win") and new_console_var.get():
                creation_flags |= subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]

            subprocess.Popen(cmd, cwd=str(exe_path.parent), creationflags=creation_flags)
        except Exception as exc:
            messagebox.showerror("Run failed", str(exc))

    buttons = ttk.Frame(root)
    ttk.Button(buttons, text="Run", command=on_run).pack(side="left")
    buttons.grid(row=9, column=0, columnspan=2, sticky="e", padx=10, pady=12)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())