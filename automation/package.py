import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from common.automation_common import get_project_root, find_uproject, load_ue_root, bring_console_to_front
import shutil
from dataclasses import dataclass
from pathlib import Path

# Global data that's set once and will not change throughout program execution
@dataclass
class GlobalData:
    project_root: str
    engine_root: str
    runuat_path: str
    project_name: str

def build_command(
    global_data: GlobalData,
    build_config: str,
    full_rebuild: bool,
    output_dir: str,
    platform: str
) -> str:
    unreal_cmd = os.path.join(global_data.engine_root, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe")
    uproject_file = os.path.join(global_data.project_root, global_data.project_name + ".uproject")

    args = [
        f"-ScriptsForProject=\"{uproject_file}\"",
        "Turnkey",
        "-command=VerifySdk",
        f"-platform={platform}",
        "-UpdateIfNeeded",
        "-EditorIO",
        "-EditorIOPort=55930",
        f"-project=\"{uproject_file}\"",
        "BuildCookRun",
        "-nop4",
        "-utf8output",
        "-nocompileeditor",
        "-skipbuildeditor",
        "-cook",
        f"-project=\"{uproject_file}\"",
        f"-target={os.path.splitext(global_data.project_name)[0]}",
        f"-unrealexe=\"{unreal_cmd}\"",
        f"-platform={platform}",
        "-installed",
        "-stage",
        "-archive",
        "-package",
        "-build",
        "-pak",
        "-iostore",
        "-compressed",
        "-prereqs",
        f"-archivedirectory=\"{output_dir}\"",
        f"-clientconfig={build_config}"
    ]

    if full_rebuild:
        args.extend(["-clean", "-forcecook"])

    return " ".join(args)

def move_packaging_includes(global_data: GlobalData, output_dir: str):
    source_dir = Path(os.path.join(global_data.project_root, "Script", "PackagingIncludes"))
    output_dir = Path(output_dir)
    
    if not os.path.exists(source_dir):
        print(f"[Packaging] No PackagingIncludes found at {source_dir}, skipping.")
        return

    for item in source_dir.iterdir():
        dest_item = output_dir / item.name
        try:
            if item.is_dir():
                for sub_item in item.rglob("*"):
                    rel_path = sub_item.relative_to(item)
                    target_path = dest_item / rel_path
                    if sub_item.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sub_item, target_path)
            else:
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_item)
        except Exception as e:
            print(f"Failed to copy {item} to {dest_item}: {e}")


def run_packaging(cmd_args: str, global_data: GlobalData, output_dir: str) -> bool :
    try:
        bring_console_to_front()

        full_command = '"' + global_data.runuat_path + '" ' + cmd_args + ' -nocompile -nocompileuat'

        print("command\n")
        print(full_command)

        subprocess.run(full_command, shell=True, check=True)

        move_packaging_includes(global_data, output_dir)

        print("Packaging successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Packaging failed.\n\n{e}")
    return False

def create_ui():
    engine_root = str(load_ue_root())
    project_root = get_project_root()
    
    global_data = GlobalData(
        project_root = project_root,
        engine_root = engine_root,
        runuat_path = str(os.path.join(engine_root, "Engine", "Build", "BatchFiles", "RunUAT.bat")),
        project_name = os.path.splitext(find_uproject(project_root).name)[0]
    )

    root = tk.Tk()
    root.title("Unreal Build Packager")
    root.geometry("1024x540")

    cached_command_string = tk.StringVar()

    def update_command_preview(*_):
        cached_command_string.set(build_command(
            global_data=global_data,
            build_config=build_config_var.get(),
            full_rebuild=b_full_rebuild.get(),
            output_dir=output_dir_var.get(),
            platform=platform_var.get()
        ))
	
        command_display.delete("1.0", tk.END)
        command_display.insert(tk.END, f'"{global_data.runuat_path}" {cached_command_string.get()}')

    padding_options = {"padx": 10, "pady": 5, "sticky": "w"}

    # Build Config
    tk.Label(root, text="Build Config:").grid(row=0, column=0, **padding_options)
    build_config_var = tk.StringVar(value="Development")
    tk.OptionMenu(root, build_config_var, "Debug", "Development", "Shipping", command=lambda _: update_command_preview())\
        .grid(row=0, column=1, **padding_options)

    # Full Rebuild
    b_full_rebuild = tk.BooleanVar()
    tk.Checkbutton(root, text="Full Rebuild & Recook", variable=b_full_rebuild, command=update_command_preview)\
        .grid(row=1, column=1, **padding_options)

    # Output Directory
    tk.Label(root, text="Output Directory:").grid(row=2, column=0, **padding_options)
    default_output_dir = os.path.join(global_data.project_root, "Packaged")
    output_dir_var = tk.StringVar(value=default_output_dir)
    tk.Entry(root, textvariable=output_dir_var, width=60).grid(row=2, column=1, **padding_options)

    def browse_and_update():
        selected = filedialog.askdirectory()
        if selected:
            output_dir_var.set(selected)
            update_command_preview()

    tk.Button(root, text="Browse", command=browse_and_update).grid(row=2, column=2, **padding_options)
    output_dir_var.trace_add("write", lambda *_: update_command_preview())

    # Platform
    tk.Label(root, text="Target Platform:").grid(row=3, column=0, **padding_options)
    platform_var = tk.StringVar(value="Win64")
    tk.OptionMenu(root, platform_var, "Win64", "Android", "iOS", command=lambda _: update_command_preview())\
        .grid(row=3, column=1, **padding_options)

    # Command Preview
    tk.Label(root, text="Command Preview:").grid(row=4, column=0, **padding_options)
    command_display = tk.Text(root, width=100, height=10, wrap="word")
    command_display.grid(row=4, column=1, columnspan=2, **padding_options)

    # Run Button
    tk.Button(root, text="Package", command=lambda: run_packaging(cached_command_string.get(), global_data, output_dir_var.get()))\
        .grid(row=5, column=1, **padding_options)

    update_command_preview()
    root.mainloop()

if __name__ == "__main__":
    create_ui()