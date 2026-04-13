"""
Core scale-cube export logic.

Framework-agnostic — runs Blender as a subprocess and reports progress
via callbacks.  Importable by other pipeline tools.
"""

import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

# Callback type: (message, detail, level)
# level: "info", "success", "warning", "error"
ProgressCallback = Callable[[str, str, str], None]

CUBE_SIZES = {
    "1 mm  (0.001 m)": 0.001,
    "1 cm  (0.01 m)":  0.01,
    "1 m   (1.0 m)":   1.0,
}

DEFAULT_BLENDER = Path(
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
)


def _notify(
    cb: Optional[ProgressCallback], message: str, detail: str = "", level: str = "info"
):
    if cb:
        cb(message, detail, level)


def validate_inputs(
    obj_path: Path,
    blender_exe: Path,
    blender_script: Path,
) -> Optional[str]:
    """Return an error string, or None if everything looks good."""
    if not obj_path.is_file():
        return f"OBJ file not found: {obj_path}"
    if not blender_exe.is_file():
        return f"Blender not found: {blender_exe}"
    if not blender_script.is_file():
        return f"blender_script.py not found: {blender_script}"
    return None


def process_obj(
    obj_path: Path,
    cube_size: float,
    blender_exe: Path,
    blender_script: Path,
    on_progress: Optional[ProgressCallback] = None,
) -> dict:
    """Run Blender headless on a single OBJ file.

    Returns:
        {"obj_name": str, "output_dir": str, "elapsed": float}
        or on error:
        {"obj_name": str, "error": str}
    """
    obj_name = obj_path.name
    start = time.time()

    err = validate_inputs(obj_path, blender_exe, blender_script)
    if err:
        _notify(on_progress, err, obj_name, "error")
        return {"obj_name": obj_name, "error": err}

    output_dir = obj_path.parent / "with_cube"
    _notify(on_progress, "Starting Blender", obj_name, "info")

    cmd = [
        str(blender_exe),
        "--background",
        "--python", str(blender_script),
        "--", str(obj_path), str(cube_size),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            # Surface meaningful lines from blender_script.py
            if line.startswith("["):
                _notify(on_progress, line, obj_name, "info")

        proc.wait()

        if proc.returncode != 0:
            _notify(on_progress, f"Blender exited with code {proc.returncode}", obj_name, "error")
            return {"obj_name": obj_name, "error": f"Blender exit code {proc.returncode}"}

    except Exception as e:
        _notify(on_progress, f"Error: {e}", obj_name, "error")
        return {"obj_name": obj_name, "error": str(e)}

    elapsed = round(time.time() - start, 1)
    _notify(on_progress, "Done", obj_name, "success")
    return {"obj_name": obj_name, "output_dir": str(output_dir), "elapsed": elapsed}


def process_batch(
    obj_paths: list[Path],
    cube_size: float,
    blender_exe: Path,
    blender_script: Path,
    on_progress: Optional[ProgressCallback] = None,
    on_file_done: Optional[Callable[[int, int, dict], None]] = None,
) -> list[dict]:
    """Process multiple OBJ files sequentially.

    on_file_done(current_index, total, result) is called after each file.
    Returns list of result dicts.
    """
    results = []
    total = len(obj_paths)
    for i, obj_path in enumerate(obj_paths):
        result = process_obj(obj_path, cube_size, blender_exe, blender_script, on_progress)
        results.append(result)
        if on_file_done:
            on_file_done(i + 1, total, result)
    return results
