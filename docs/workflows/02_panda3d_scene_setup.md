# 02. Panda3D scene setup

## 1. Objective

Render the warehouse as a real 3D scene in Panda3D, off-screen for the browser and in a
window for the native viewer, using only procedural geometry.

## 2. Technical requirements

- Panda3D 1.10.16 and a graphics driver with OpenGL (an integrated GPU is enough).
- Configuration must be loaded before `ShowBase` is created.
- No external model, texture or font files.

## 3. Implementation steps

1. `configure_panda` sets `window-type offscreen`, the buffer size, a 30 FPS limited clock and
   a null audio library through `loadPrcFileData`.
2. `geometry.py` builds lit meshes by hand: `GeomVertexData` with the `V3n3` format, one flat
   normal per face, assembled into `GeomTriangles`.
3. `WarehouseScene.build` creates the static world: textured floor, walls, shelves with
   cartons, pallet stacks, zone decals with borders, checkpoints and the grid overlay.
4. The robot, packages and forklifts are built as small node hierarchies under a `dynamic` node.
5. Lighting: an ambient light, a shadow-casting directional light whose orthographic lens
   covers the warehouse, a fill light, and `render.setShaderAuto()` for per-pixel lighting.
6. `CameraRig` orbits the centre of the grid with three presets and a clamped zoom.
7. `SimulationEngine.capture_jpeg` reads the frame buffer into a `PNMImage` and encodes it.

## 4. Relevant files

- `backend/simulation/geometry.py` - boxes, cylinders, decals, procedural textures
- `backend/simulation/scene.py` - `WarehouseScene`
- `backend/simulation/engine.py` - `configure_panda`, `CameraRig`, `SimulationEngine`
- `backend/simulation/panda_viewer.py` - the windowed viewer

## 5. Important code sections

```python
def make_box(size_x, size_y, size_z, color, name="box") -> NodePath:
    mesh = _MeshBuilder(name)
    mesh.quad((-hx, -hy, z1), (hx, -hy, z1), (hx, hy, z1), (-hx, hy, z1), (0, 0, 1))  # top
    ...
    return mesh.build(color)

sun = DirectionalLight("sun")
sun.setShadowCaster(True, 2048, 2048)
sun.getLens().setFilmSize(34, 34)      # must cover the whole warehouse
```

## 6. Design decisions

- **Procedural geometry.** The repository stays small, has no asset licences to track, and
  every shape is explained by code.
- **Seeded decoration.** Carton sizes and colours on a shelf come from a `Random` seeded by
  the cell, so the scene looks varied but renders identically every time.
- **Unlit decals in fixed bins.** Zone markings are drawn slightly above the floor with depth
  writing off, which avoids z-fighting.
- **Scene options are a dataclass.** Grid, route, incident marks and labels are toggled by
  showing or hiding four group nodes.

## 7. Problems encountered

- `PNMImage.write` silently failed for Windows paths. Panda3D expects its own path syntax;
  `Filename.fromOsSpecific` fixed it.
- The first camera cut off the loading dock. The distance is now derived from the grid size
  and the aspect ratio.
- The frame buffer ignored the request for multisampling on the integrated GPU. The engine
  logs the warning and continues without it.

## 8. Debugging approach

A probe script rendered one lit box off-screen and printed the pipe type, the renderer and
the time per frame (about 28 ms including JPEG encoding at 960 x 540). After that, a test
script saved full frames to PNG so each visual change could be inspected directly.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_panda_scene.py
python -m simulation.panda_viewer --scenario obstacle-navigation --agent astar
```

## 10. Expected result

A lit, shadowed warehouse with shelves, pallets, coloured zones, a robot with a heading arrow
and forklifts. The engine reports about 30 FPS and produces valid JPEG frames.
