import os
import shutil
import subprocess
import argparse
import sys
from pathlib import Path
import configparser

# === SCRIPT ARGUMENTS ===
# --dry-run
# ->Only prints operations

# === LOAD CONFIGURATION ===
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "build_and_push_to_cgi.config"

# === ENSURE CONFIGURATION FILE EXISTS ===
if not CONFIG_FILE.exists():
    print(f"Configuration file not found: {CONFIG_FILE}")
    print("Please create a configuration.ini file in the same folder as this script.")
    exit(1)


config = configparser.ConfigParser()
config.optionxform = str  # keep case-sensitive
config.read(CONFIG_FILE)

DEV_REPO_ROOT = (SCRIPT_DIR / config['Paths']['dev_repo_root']).resolve()
CGI_REPO_ROOT = (SCRIPT_DIR / config['Paths']['cgi_repo_root']).resolve()
UE_ROOT = (SCRIPT_DIR / config['Paths']['ue_root']).resolve()
PRECOMMIT_HOOK = CGI_REPO_ROOT / config['Git']['precommit_hook']

BUILD_COMMANDS = [value.strip() for key, value in config['Build'].items() if value and value.strip()]
files_to_copy_raw = config.get('FilesToCopy', 'paths', fallback='')
FILES_TO_COPY = [line.strip() for line in files_to_copy_raw.splitlines() if line.strip()]

##
#  Runs a build command, usually like 'UnrealBuildTool.dll GrimoireEditor Win64 DebugGame -project=Grimoire.uproject -clean'
##
def run_build_command(command, cwd=None, check=True):
    tokens = command.strip().split()

    # Replace 'UnrealBuildTool.dll" with that file's full absolute path
    if tokens[0] == "UnrealBuildTool.dll":
        ubt_dll_path = UE_ROOT / "Engine" / "Binaries" / "DotNET" / "UnrealBuildTool" / "UnrealBuildTool.dll"
        tokens = ["dotnet", str(ubt_dll_path)] + tokens[1:]  # replace dll with dotnet + dll

    # Replace -project=<something> with full absolute path
    for i, token in enumerate(tokens):
        if token.lower().startswith("-project=") or token.lower().startswith("-project=\""):
            project_file = token.split("=", 1)[1].strip('"')
            project_full_path = (cwd / project_file).resolve()
            tokens[i] = f'-Project={project_full_path}'
        
    print(f"Running: {' '.join(tokens)}")
    
    result = subprocess.run(tokens, cwd=cwd, check=check, stdout=sys.stdout, stderr=sys.stderr, text=True)
    
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(tokens)}")
    
    return result

##
#  Runs a git command, like 'git status --porcelain'
##
def run_git_command(command, cwd=None):
    tokens = command.strip().split()
        
    print(f"Running: {' '.join(tokens)}")
    
    result = subprocess.run(tokens, cwd=cwd, shell=True, capture_output=True, text=True)
        
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(tokens)}")
    return result

##
#  Checks if the target repo has no modified files. If it does, throws error
##
def check_cgi_repo_clean():
    result = run_git_command("git status --porcelain", cwd=CGI_REPO_ROOT)

    if result.stdout.strip():
        raise RuntimeError("CGI repo has uncommitted changes. Please commit or stash them first.")

##
#  Builds dev binaries from the dev , by running all commands defined in the config sequentially
##
def build_dev_binaries(dry_run=False):
    if not BUILD_COMMANDS:
        print("No build commands configured. Skipping build.")
        return
    
    print(f"Building binaries ({len(BUILD_COMMANDS)} step{'s' if len(BUILD_COMMANDS) != 1 else ''})...")
    for idx, command in enumerate(BUILD_COMMANDS, 1):
        print(f"Step {idx}: {command}")
        if not dry_run:
            run_build_command(command, cwd=DEV_REPO_ROOT)

##
#  Deletes (from CGI) all files that will be copied from dev to cgi
#  Files to be deleted are defined in the config file
##
def delete_old_files(dry_run=False):
    for rel_path in FILES_TO_COPY:
        target_path = CGI_REPO_ROOT / rel_path.lstrip('/')
        if target_path.exists():
            if target_path.is_dir():
                print(f"Would delete directory: {target_path}" if dry_run else f"Deleting directory: {target_path}")
                if not dry_run:
                    shutil.rmtree(target_path)
            else:
                print(f"Would delete file: {target_path}" if dry_run else f"Deleting file: {target_path}")
                if not dry_run:
                    target_path.unlink()

##
#  Copies the files
#  Files to be copied are defined in the config file
##
def copy_new_files(dry_run=False):
    for rel_path in FILES_TO_COPY:
        src_path = DEV_REPO_ROOT / rel_path.lstrip('/')
        dest_path = CGI_REPO_ROOT / rel_path.lstrip('/')
        if src_path.is_dir():
            print(f"Would copy directory: {src_path} -> {dest_path}" if dry_run else f"Copying directory: {src_path} -> {dest_path}")
            if not dry_run:
                shutil.copytree(src_path, dest_path)
        else:
            print(f"Would copy file: {src_path} -> {dest_path}" if dry_run else f"Copying file: {src_path} -> {dest_path}")
            if not dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)

##
#  Disables the pre-commit hook that normally prevents commits in the CGI branch
##
def temporarily_disable_hook(dry_run=False):
    if PRECOMMIT_HOOK.exists():
        print(f"Would temporarily disable pre-commit hook: {PRECOMMIT_HOOK}" if dry_run else f"Temporarily disabling pre-commit hook: {PRECOMMIT_HOOK}")
        if not dry_run:
            PRECOMMIT_HOOK.rename(PRECOMMIT_HOOK.with_suffix(".pre-commit.disabled"))
            return True
    return False

##
#  Restores the pre-commit hook that normally prevents commits in the CGI branch
##
def restore_hook(dry_run=False):
    disabled_hook = PRECOMMIT_HOOK.with_suffix(".pre-commit.disabled")
    if disabled_hook.exists():
        print(f"Would restore pre-commit hook: {PRECOMMIT_HOOK}" if dry_run else f"Restoring pre-commit hook: {PRECOMMIT_HOOK}")
        if not dry_run:
            disabled_hook.rename(PRECOMMIT_HOOK)

##
#  Adds all changed files in the CGI repo to git
##
def add_to_cgi_repo(dry_run=False):
    if dry_run:
        print("Would stage and commit changes to CGI repo.")
    else:
        # run git add, capture output to prevent it from being printed
        run_git_command("git add .", cwd=CGI_REPO_ROOT)
        #run_git_command('git commit -m "Update pre-built binaries from Dev"', cwd=CGI_REPO_ROOT)


def main():
    parser = argparse.ArgumentParser(description="Build and push pre-built binaries to CGI repo.")
    parser.add_argument('--dry-run', action='store_true', help="Preview actions without making changes.")
    args = parser.parse_args()
    dry_run = args.dry_run

    try:
        check_cgi_repo_clean()
        build_dev_binaries(dry_run=dry_run)
        delete_old_files(dry_run=dry_run)
        copy_new_files(dry_run=dry_run)

        #hook_disabled = temporarily_disable_hook(dry_run=dry_run)
        add_to_cgi_repo(dry_run=dry_run)
        #if hook_disabled:
            #restore_hook(dry_run=dry_run)

        print("Dry run completed!" if dry_run else "All done!")
    except Exception as e:
        print(f"Error: {e}")
        if PRECOMMIT_HOOK.with_suffix(".pre-commit.disabled").exists() and not dry_run:
            restore_hook()

if __name__ == "__main__":
    main()
