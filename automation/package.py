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
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Packaging failed.\n\n{e}")
    return False
    
def preinstall_pixelstreaming(global_data: GlobalData, output_dir: str, ):
    print("Pre-installing pixel streaming web-servers")
    project_root = os.path.join(output_dir, "Windows", global_data.project_name)
    webservers_dir = os.path.join(project_root, "Samples", "PixelStreaming", "WebServers")
    get_ps_servers = os.path.join(webservers_dir, "get_ps_servers.bat")
    ps_setup_script = os.path.join(os.path.dirname(__file__), "utils", "prebuild_ue_ps_servers.bat")
    ps_ue_scripts_location = os.path.join(output_dir, "Windows", global_data.project_name, "Samples", "PixelStreaming", "WebServers", "SignallingWebServer", "platform_scripts", "cmd")
    symbolic_links_script = os.path.join(os.path.dirname(__file__), "utils", "MaterializeSymbolicLinks.ps1")
    
    if not os.path.exists(get_ps_servers):
        print("No pixel streaming content detected, skipping.")
        return
  
    print("Fetching Pixel Streaming web-servers...")
    try:
        # .bat needs shell=True on Windows
        subprocess.run(get_ps_servers, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"get_ps_servers.bat failed with exit code {e.returncode}") from e
    
    
    try:
        print("Installing workspace dependencies (npm ci --workspaces)...")
        subprocess.run(["npm.cmd", "ci", "--workspaces"], cwd=webservers_dir, check=True)
        
        print("Pre-installing web servers")
        subprocess.run([ps_setup_script, ps_ue_scripts_location], check=True)
        
    except FileNotFoundError as e:
        raise RuntimeError("npm.cmd not found on PATH") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"npm ci failed with exit code {e.returncode}") from e
        
    
    
    print("Materializing symlinks/junctions for portability...")
    # Prefer Windows PowerShell; if missing, try PowerShell 7 (pwsh)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", symbolic_links_script, "-StartPath", webservers_dir],
            check=True
        )
    except FileNotFoundError:
        # Retry with pwsh
        try:
            subprocess.run(
                ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", symbolic_links_script, "-StartPath", webservers_dir],
                check=True
            )
        except FileNotFoundError as e2:
            raise RuntimeError("Neither 'powershell' nor 'pwsh' found on PATH") from e2
        except subprocess.CalledProcessError as e2:
            raise RuntimeError(f"MaterializeSymbolicLinks.ps1 failed (pwsh) with exit code {e2.returncode}") from e2
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"MaterializeSymbolicLinks.ps1 failed with exit code {e.returncode}") from e
        
        

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

    CurrentRow:int = 1

    # Full Rebuild
    b_full_rebuild = tk.BooleanVar()
    tk.Checkbutton(root, text="Full Rebuild & Recook", variable=b_full_rebuild, command=update_command_preview)\
        .grid(row=CurrentRow, column=1, **padding_options)
    CurrentRow += 1
    
    # Whether to pre-install pixel streaming (if applicable)
    b_preinstall_pixelstreaming = tk.BooleanVar(value=True)
    tk.Checkbutton(root, text="Preinstall Pixelstreaming (if applicable)", variable = b_preinstall_pixelstreaming)\
        .grid(row=CurrentRow, column=1, **padding_options)
    CurrentRow += 1

    # Output Directory
    tk.Label(root, text="Output Directory:").grid(row=3, column=0, **padding_options)
    default_output_dir = os.path.join(global_data.project_root, "Packaged")
    output_dir_var = tk.StringVar(value=default_output_dir)
    tk.Entry(root, textvariable=output_dir_var, width=60).grid(row=CurrentRow, column=1, **padding_options)

    def browse_and_update():
        selected = filedialog.askdirectory()
        if selected:
            output_dir_var.set(selected)
            update_command_preview()

    tk.Button(root, text="Browse", command=browse_and_update).grid(row=CurrentRow, column=2, **padding_options)
    output_dir_var.trace_add("write", lambda *_: update_command_preview())
    CurrentRow += 1

    # Platform
    tk.Label(root, text="Target Platform:").grid(row=4, column=0, **padding_options)
    platform_var = tk.StringVar(value="Win64")
    tk.OptionMenu(root, platform_var, "Win64", "Android", "iOS", command=lambda _: update_command_preview())\
        .grid(row=CurrentRow, column=1, **padding_options)
    CurrentRow += 1

    # Command Preview
    tk.Label(root, text="Command Preview:").grid(row=5, column=0, **padding_options)
    command_display = tk.Text(root, width=100, height=10, wrap="word")
    command_display.grid(row=CurrentRow, column=1, columnspan=2, **padding_options)
    CurrentRow += 1

    def execute_packaging():
        run_packaging(cached_command_string.get(), global_data, output_dir_var.get())
        if b_preinstall_pixelstreaming.get():
            preinstall_pixelstreaming(global_data, output_dir_var.get())
        print("Packaging completed!")

    # Run Button
    tk.Button(root, text="Package", command=execute_packaging)\
        .grid(row=CurrentRow, column=1, **padding_options)
    CurrentRow += 1

    update_command_preview()
    root.mainloop()

if __name__ == "__main__":
    create_ui()