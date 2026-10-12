SCALE CUBE EXPORTER
===================

HOW TO BUILD (one time only)
------------------------------
1. Make sure Python 3.x is installed on your PC
   (download from https://python.org — check "Add to PATH" during install)

2. Double-click BUILD.bat

3. Wait ~30 seconds. Your app will appear in:
      dist\ScaleCubeExporter\ScaleCubeExporter.exe

4. Move the entire "ScaleCubeExporter" folder anywhere you like.
   You can also create a shortcut to ScaleCubeExporter.exe on your desktop.


FAST BY DEFAULT (no Blender)
----------------------------
The cube is now added without Blender (core/fast_cube.py): the OBJ is read
once and written back with the cube at the end. Same result as before
(vertices scaled mm to m, cube centred 10 mm under the model, MTL and
textures copied), measured on test models:

   2M triangles    Blender 50 s       fast 3 s
  10M triangles    Blender 4 min 13   fast 14 s
  40M triangles    Blender ~17 min+   fast ~1 min (estimated)

Tick "Use Blender (slow, the old way)" to run blender_script.py as before.
From a terminal: python -m core.fast_cube <file.obj> 0.01


HOW TO USE
----------
1. Open ScaleCubeExporter.exe
2. Click Browse and select your .obj file
3. Choose cube size: 1mm / 1cm / 1m
4. If needed, update the Blender path using the second Browse button
5. Click RUN
6. When done, a "with_cube" folder will appear next to your OBJ
   containing the new OBJ, MTL, and JPG


NOTES
-----
- The Blender script (blender_script.py) must stay in the same folder as the .exe
- Your last used settings (OBJ path, Blender path, cube size) are remembered
- The cube sits 10mm below the model's lowest point
- The model is imported assuming millimeter units
