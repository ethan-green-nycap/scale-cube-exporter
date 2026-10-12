"""
Fast scale cube: the same result as blender_script.py, without Blender.

Blender spends almost all its time importing and exporting the OBJ (about
50 s for 2M triangles in Blender 3.6, so 15+ min for a 40M model). A cube is
8 points and 6 faces, so this reads the OBJ once, as text, and writes it
straight back out with the cube added at the end:

  - every vertex is scaled by `scale` (0.001: millimetres in, metres out,
    exactly as the Blender script's import + transform_apply does);
    texture coordinates, normals and faces are copied byte for byte;
  - the cube (cube_size metres) sits centred under the model's footprint,
    GAP below its lowest point (Y up, as the OBJ is written);
  - the MTL is copied with texture paths cut to file names, plus a plain
    grey material for the cube; textures next to the OBJ are copied too.

Output: <obj folder>/with_cube/<same name>.obj, as before.
Memory stays flat whatever the model size: the file is streamed.
"""

import shutil
import time
from pathlib import Path
from typing import Callable, Optional

GAP = 0.01  # metres between the model's lowest point and the cube's top
CHUNK = 64 * 1024 * 1024
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
CUBE_MATERIAL = "scale_cube"

# (message, detail, level), as core/exporter.py
ProgressCallback = Callable[[str, str, str], None]


def _notify(cb, message, detail="", level="info"):
    if cb:
        cb(message, detail, level)


def _cube_text(cx, cy_bottom, cz, size, v0, vn0):
    """OBJ text for a cube whose bottom face is at cy_bottom. v0 / vn0: vertices / normals already in the file."""
    h = size / 2
    y0, y1 = cy_bottom, cy_bottom + size
    xs = (cx - h, cx + h)
    zs = (cz - h, cz + h)
    verts = [(x, y, z) for x in xs for y in (y0, y1) for z in zs]  # index = 4*xi + 2*yi + zi
    lines = [f"o Scale_Cube_{size:g}m", f"usemtl {CUBE_MATERIAL}", "s off"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in verts]
    normals = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]
    lines += [f"vn {a:.4f} {b:.4f} {c:.4f}" for a, b, c in normals]

    def idx(xi, yi, zi):
        return v0 + 4 * xi + 2 * yi + zi + 1

    faces = [  # counter-clockwise seen from outside
        (0, [idx(0, 0, 0), idx(0, 0, 1), idx(0, 1, 1), idx(0, 1, 0)]),  # -X
        (1, [idx(1, 0, 0), idx(1, 1, 0), idx(1, 1, 1), idx(1, 0, 1)]),  # +X
        (2, [idx(0, 0, 0), idx(1, 0, 0), idx(1, 0, 1), idx(0, 0, 1)]),  # -Y
        (3, [idx(0, 1, 0), idx(0, 1, 1), idx(1, 1, 1), idx(1, 1, 0)]),  # +Y
        (4, [idx(0, 0, 0), idx(0, 1, 0), idx(1, 1, 0), idx(1, 0, 0)]),  # -Z
        (5, [idx(0, 0, 1), idx(1, 0, 1), idx(1, 1, 1), idx(0, 1, 1)]),  # +Z
    ]
    for n, quad in faces:
        lines.append("f " + " ".join(f"{i}//{vn0 + n + 1}" for i in quad))
    return "\n".join(lines) + "\n"


def _copy_mtl_and_textures(src_dir: Path, dst_dir: Path, obj_path: Path, mtl_names, on_progress):
    for f in src_dir.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
            shutil.copy2(f, dst_dir / f.name)
            _notify(on_progress, "Copied texture", f.name)
    names = list(mtl_names) or [obj_path.stem + ".mtl"]
    for name in names:
        src = src_dir / name
        lines = []
        if src.is_file():
            for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().lower().startswith("map_"):
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        line = f"{parts[0]} {Path(parts[1].strip().replace(chr(92), '/')).name}"
                lines.append(line)
        lines += ["", f"newmtl {CUBE_MATERIAL}", "Ka 0.8 0.8 0.8", "Kd 0.8 0.8 0.8", "Ks 0 0 0", "d 1", "illum 1"]
        (dst_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        _notify(on_progress, "Wrote MTL", name)
        break  # the cube's material goes in the first library only


def add_scale_cube(
    obj_path: Path,
    cube_size: float,
    on_progress: Optional[ProgressCallback] = None,
    scale: float = 0.001,
    gap: float = GAP,
) -> dict:
    """Write <obj folder>/with_cube/<name>.obj with the cube added.

    Returns {"obj_name", "output_dir", "elapsed", "vertices", "bottom", "height"}
    or {"obj_name", "error"}.
    """
    obj_path = Path(obj_path)
    start = time.time()
    if not obj_path.is_file():
        return {"obj_name": obj_path.name, "error": f"OBJ file not found: {obj_path}"}

    out_dir = obj_path.parent / "with_cube"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / obj_path.name
    if out_path.resolve() == obj_path.resolve():
        return {"obj_name": obj_path.name, "error": "The input is already inside a with_cube folder."}

    total = obj_path.stat().st_size
    inf = float("inf")
    min_x = min_y = min_z = inf
    max_x = max_y = max_z = -inf
    n_v = n_vn = 0
    mtl_names = []
    done = 0
    last_pct = -1
    _notify(on_progress, "Reading and writing", f"{total / 1e9:.2f} GB")

    with open(obj_path, "rb") as src, open(out_path, "wb", buffering=CHUNK) as dst:
        rest = b""
        while True:
            chunk = src.read(CHUNK)
            if not chunk:
                break
            done += len(chunk)
            data = rest + chunk
            cut = data.rfind(b"\n")
            if cut < 0:
                rest = data
                continue
            rest = data[cut + 1:]
            out = []
            append = out.append
            for line in data[:cut].split(b"\n"):
                if line[:2] == b"v ":
                    p = line.split()
                    x = float(p[1]) * scale
                    y = float(p[2]) * scale
                    z = float(p[3]) * scale
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
                    if z < min_z: min_z = z
                    if z > max_z: max_z = z
                    n_v += 1
                    extra = (b" " + b" ".join(p[4:])) if len(p) > 4 else b""
                    append(b"v %.6f %.6f %.6f%s" % (x, y, z, extra))
                else:
                    if line[:3] == b"vn ":
                        n_vn += 1
                    elif line[:7] == b"mtllib ":
                        mtl_names.append(line[7:].strip().decode("utf-8", "replace"))
                    append(line.rstrip(b"\r"))
            dst.write(b"\n".join(out))
            dst.write(b"\n")
            pct = int(done * 100 / max(total, 1))
            if pct // 10 != last_pct // 10:
                last_pct = pct
                _notify(on_progress, f"{pct}%", obj_path.name)
        if rest.strip():
            line = rest
            if line[:2] == b"v ":
                # A last vertex line without a newline: same handling.
                p = line.split()
                x, y, z = (float(p[i]) * scale for i in (1, 2, 3))
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
                min_z, max_z = min(min_z, z), max(max_z, z)
                n_v += 1
                line = b"v %.6f %.6f %.6f" % (x, y, z)
            dst.write(line.rstrip(b"\r") + b"\n")

        if n_v == 0:
            return {"obj_name": obj_path.name, "error": "No vertices found in the OBJ."}
        cx = (min_x + max_x) / 2
        cz = (min_z + max_z) / 2
        bottom = min_y - gap - cube_size
        dst.write(_cube_text(cx, bottom, cz, cube_size, n_v, n_vn).encode("ascii"))

    _copy_mtl_and_textures(obj_path.parent, out_dir, obj_path, mtl_names, on_progress)
    elapsed = round(time.time() - start, 1)
    _notify(on_progress, "Done", f"{elapsed}s", "success")
    return {
        "obj_name": obj_path.name,
        "output_dir": str(out_dir),
        "elapsed": elapsed,
        "vertices": n_v,
        "bottom": min_y,
        "height": max_y - min_y,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python -m core.fast_cube <file.obj> <cube size in metres: 0.001 | 0.01 | 1>")
        sys.exit(2)
    res = add_scale_cube(Path(sys.argv[1]), float(sys.argv[2]), on_progress=lambda m, d, l: print(f"[{l}] {m} {d}"))
    print(res)
    sys.exit(1 if "error" in res else 0)
