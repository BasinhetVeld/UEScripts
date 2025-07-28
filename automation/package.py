import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from common.automation_common import get_project_root, find_uproject, load_ue_root

def build_command(
    ue_root: str,
    uproject_file: str,
    uproject_name: str,
    build_config: str,
    full_rebuild: bool,
    output_dir: str,
    platform: str
) -> list[str]:
    unreal_cmd = os.path.join(ue_root, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe")

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
        f"-target={os.path.splitext(uproject_name)[0]}",
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
        f"-clientconfig={build_config}",
        "-nocompile",
        "-nocompileuat"
    ]

    if full_rebuild:
        args.append("-clean")

    return args

def run_packaging(args_list: list[str], runuat_path: str):

    cmd_args = " ".join(args_list)

    try:
        subprocess.run(runuat_path + " " + cmd_args, check=True)
        messagebox.showinfo("Success", "Packaging completed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Packaging failed.\n\n{e}")

def create_ui():
    project_root = get_project_root()
    ue_root = str(load_ue_root())
    runuat_path = os.path.join(ue_root, "Engine", "Build", "BatchFiles", "RunUAT.bat")
    uproject_path = find_uproject(project_root)
    uproject_name = uproject_path.name
    uproject_file = str(uproject_path)

    root = tk.Tk()
    root.title("Unreal Build Packager")
    root.geometry("1024x540")

    cached_command_string = tk.StringVar()
    cached_command: list[str] = []

    def update_command_preview(*_):
        nonlocal cached_command
        cached_command = build_command(
            ue_root=ue_root,
            uproject_file=uproject_file,
            uproject_name=uproject_name,
            build_config=build_config_var.get(),
            full_rebuild=b_full_rebuild.get(),
            output_dir=output_dir_var.get(),
            platform=platform_var.get()
        )
        cached_command_string.set(" ".join(cached_command))
	
        command_display.delete("1.0", tk.END)
        command_display.insert(tk.END, f'"{runuat_path}" {cached_command_string.get()}')

    padding_options = {"padx": 10, "pady": 5, "sticky": "w"}

    # Build Config
    tk.Label(root, text="Build Config:").grid(row=0, column=0, **padding_options)
    build_config_var = tk.StringVar(value="Development")
    tk.OptionMenu(root, build_config_var, "Debug", "Development", "Shipping", command=lambda _: update_command_preview())\
        .grid(row=0, column=1, **padding_options)

    # Full Rebuild
    b_full_rebuild = tk.BooleanVar()
    tk.Checkbutton(root, text="Full Rebuild", variable=b_full_rebuild, command=update_command_preview)\
        .grid(row=1, column=1, **padding_options)

    # Output Directory
    tk.Label(root, text="Output Directory:").grid(row=2, column=0, **padding_options)
    default_output_dir = os.path.join(project_root, "Packaged")
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
    tk.Button(root, text="Package", command=lambda: run_packaging(cached_command, runuat_path))\
        .grid(row=5, column=1, **padding_options)

    update_command_preview()
    root.mainloop()

if __name__ == "__main__":
    create_ui()