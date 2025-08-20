# /automation/modify_target.py
from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, Any, List, Tuple

# Resolve the parent folder and add it to sys.path once
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PARENT_DIR)

from common.automation_common import (
    get_project_root,
    find_uproject
)

# ------------------------------------------------------------
# Configure these two as needed in your environment.
# You said you'll replace these with your own resolution logic.
# ------------------------------------------------------------
PROJECT_ROOT: str = get_project_root()
PROJECT_NAME: str = os.path.splitext(find_uproject(PROJECT_ROOT).name)[0]
# ------------------------------------------------------------

TARGET_PATH: str = os.path.join(
    PROJECT_ROOT, "Binaries", "Android", f"{PROJECT_NAME}.target"
)

# Anchors that typically mark the project-relative portion inside absolute paths
ANCHORS: Tuple[str, ...] = (
    r"plugins\\",
    r"source\\",
    r"content\\",
    r"config\\",
)

ABS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
ABS_UNC_RE = re.compile(r"^\\\\")  # UNC path like \\server\share

def is_absolute_windows(p: str) -> bool:
    return bool(ABS_DRIVE_RE.match(p)) or bool(ABS_UNC_RE.match(p))

def normalize_slashes(p: str) -> str:
    # Work internally with backslashes for consistency with UE/Windows files
    return p.replace("/", "\\")

def find_relative_tail(abs_path: str) -> str | None:
    p = normalize_slashes(abs_path)
    p_lower = p.lower()

    # We normalized to backslashes, so search for 'plugins\'.
    anchor = "plugins\\"
    idx = p_lower.find(anchor)
    if idx == -1:
        return None  # no Plugins/ segment -> leave as-is

    # Return from 'Plugins\' onward (no leading slash to avoid os.path.join issues)
    return p[idx:]

def retarget_value(value: str) -> Tuple[str, bool, str | None]:
    """
    Returns (new_value, changed?, note)
    - Only modifies absolute Windows paths.
    - Leaves relative paths untouched.
    """
    original = value
    v = normalize_slashes(value)

    if not is_absolute_windows(v):
        return original, False, None

    rel_tail = find_relative_tail(v)
    
    if rel_tail is None:
        return original, False, "Could not determine project-relative tail; left as-is."

    new_abs = normalize_slashes(os.path.join(PROJECT_ROOT, rel_tail))
    return new_abs, (new_abs != original), None

def process_additional_properties(additional_props: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """
    Mutates AdditionalProperties in place; returns (num_changed, notes)
    """
    changed = 0
    notes: List[str] = []

    for entry in additional_props:
        # Only act on entries that look like path-bearing key pairs
        if not isinstance(entry, dict):
            continue
        if "Value" not in entry:
            continue
        val = entry.get("Value")
        if not isinstance(val, str):
            continue

        new_val, did_change, note = retarget_value(val)
        if did_change:
            entry["Value"] = new_val
            changed += 1
        if note:
            notes.append(f"{val} -> {note}")

    return changed, notes

def modify_android_target(target_path: str) -> int:

    if not os.path.isfile(target_path):
        raise RuntimeError(f"Target file not found: {target_path}")

    # Load JSON
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"[ERROR] JSON parse failed: {e}")

    # Navigate to AdditionalProperties
    addl = data.get("AdditionalProperties")
    if not isinstance(addl, list):
        print("[INFO] No AdditionalProperties array found; nothing to change.")
        return 0

    num_changed, notes = process_additional_properties(addl)

    # Save if changes
    if num_changed > 0:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"[OK] Updated {num_changed} entrie(s) in AdditionalProperties.")
    else:
        print("[OK] No absolute paths required changes.")

    # Print any notes for unmodified absolute paths
    if notes:
        print("\n[NOTES]")
        for n in notes:
            print(f" - {n}")

    return 0

if __name__ == "__main__":
    raise SystemExit(modify_android_target(TARGET_PATH))