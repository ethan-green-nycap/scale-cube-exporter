"""
blender_script.py
-----------------
Blender 3.6 headless script. Called by the GUI app.
Do NOT rename this file — the GUI looks for it by name in its own folder.

Args after --:
  1. input OBJ path
  2. cube size in meters (e.g. 0.001 / 0.01 / 1.0)
"""

import bpy
import sys
import os
import shutil
import mathutils

DEFAULT_CUBE_SIZE = 0.01
GAP = 0.01  # 10mm


def get_args():
    argv = sys.argv
    input_path = ""
    cube_size = DEFAULT_CUBE_SIZE
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        if len(args) >= 1:
            input_path = args[0]
        if len(args) >= 2:
            try:
                cube_size = float(args[1])
            except ValueError:
                pass
    return input_path, cube_size


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def import_obj(path):
    before = set(bpy.data.objects[:])
    bpy.ops.import_scene.obj(filepath=path)
    after = set(bpy.data.objects[:])
    imported = list(after - before)
    for obj in imported:
        obj.scale = (0.001, 0.001, 0.001)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in imported:
        obj.select_set(True)
    bpy.ops.object.transform_apply(scale=True)
    return imported


def get_world_bounding_box(objects):
    all_corners = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        mat = obj.matrix_world
        for v in obj.bound_box:
            world_v = mat @ mathutils.Vector(v)
            all_corners.append(world_v)
    if not all_corners:
        return (0, 0, 0, 0, 0, 0)
    xs = [v.x for v in all_corners]
    ys = [v.y for v in all_corners]
    zs = [v.z for v in all_corners]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def add_scale_cube(bottom_z, center_x, center_y, cube_size):
    bpy.ops.mesh.primitive_cube_add(size=cube_size, location=(0, 0, 0))
    cube = bpy.context.active_object
    cube.name = f"Scale_Cube_{cube_size}m"
    cube.location.x = center_x
    cube.location.y = center_y
    cube.location.z = bottom_z - (cube_size / 2) - GAP
    return cube


def export_obj(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.obj(
        filepath=path,
        use_selection=True,
        use_materials=True,
        axis_forward='-Z',
        axis_up='Y',
    )
    print(f"[OK] Exported to: {path}")


def copy_textures(src_dir, dst_dir, obj_filename):
    image_exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
    for fname in os.listdir(src_dir):
        if os.path.splitext(fname)[1].lower() in image_exts:
            shutil.copy2(os.path.join(src_dir, fname), os.path.join(dst_dir, fname))
            print(f"[OK] Copied texture: {fname}")
    mtl_name = os.path.splitext(obj_filename)[0] + ".mtl"
    mtl_path = os.path.join(dst_dir, mtl_name)
    if os.path.isfile(mtl_path):
        with open(mtl_path, 'r') as f:
            lines = f.readlines()
        patched = []
        for line in lines:
            if line.strip().lower().startswith('map_'):
                parts = line.split(None, 1)
                if len(parts) == 2:
                    line = f"{parts[0]} {os.path.basename(parts[1].strip())}\n"
            patched.append(line)
        with open(mtl_path, 'w') as f:
            f.writelines(patched)
        print(f"[OK] Patched MTL: {mtl_name}")


def main():
    input_path, cube_size = get_args()
    if not input_path or not os.path.isfile(input_path):
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    src_dir      = os.path.dirname(input_path)
    obj_filename = os.path.basename(input_path)
    out_dir      = os.path.join(src_dir, "with_cube")
    output_path  = os.path.join(out_dir, obj_filename)

    os.makedirs(out_dir, exist_ok=True)
    print(f"[->] Input     : {input_path}")
    print(f"[->] Output    : {output_path}")
    print(f"[->] Cube size : {cube_size}m  |  Gap: {GAP}m")

    clear_scene()

    imported_objects = import_obj(input_path)
    if not imported_objects:
        print("[ERROR] No objects imported.")
        sys.exit(1)
    print(f"[OK] Imported {len(imported_objects)} object(s): {[o.name for o in imported_objects]}")

    min_x, min_y, min_z, max_x, max_y, max_z = get_world_bounding_box(imported_objects)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    print(f"[i] Model Z range (m): {min_z:.4f} -> {max_z:.4f}")

    cube = add_scale_cube(min_z, center_x, center_y, cube_size)
    print(f"[OK] Added '{cube.name}' at Z centre {cube.location.z:.4f}m")

    export_obj(output_path, imported_objects + [cube])
    copy_textures(src_dir, out_dir, obj_filename)
    print(f"\n[DONE] Output folder: {out_dir}")


if __name__ == "__main__":
    main()
