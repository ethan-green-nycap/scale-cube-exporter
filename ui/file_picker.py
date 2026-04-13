"""
Native Windows file picker for OBJ files.

Uses tkinter's file dialog (stdlib) — runs in a throwaway Tk root
so it works from any thread without conflicting with Flet.
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path


def pick_obj_files(
    title: str = "Select OBJ files",
    initial_dir: str = r"C:\Clients",
) -> list[Path]:
    """Open a native multi-select file dialog filtered to .obj files.

    Returns a list of Path objects, or an empty list on cancel.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    paths = filedialog.askopenfilenames(
        title=title,
        initialdir=initial_dir,
        filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")],
    )

    root.destroy()

    return [Path(p) for p in paths] if paths else []


def pick_exe_file(
    title: str = "Locate blender.exe",
    initial_dir: str = r"C:\Program Files",
) -> Path | None:
    """Open a native single-file dialog filtered to .exe files.

    Returns a Path, or None on cancel.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title=title,
        initialdir=initial_dir,
        filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
    )

    root.destroy()

    return Path(path) if path else None
