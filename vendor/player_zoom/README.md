# player_zoom (vendored subset)

Scene scaffolding for the Ursina viewer (`../../main.py`): first-person
camera/movement, lighting, color config, input dispatch, and a coordinate
axes gizmo. None of this is part of the light simulation itself — it only
draws the window you fly around in.

## Where this came from

`player_zoom` is the author's own personal Ursina sandbox project (a
learning project, not a third-party library), originally developed outside
this repository. These six files are the subset `main.py` actually imports;
they were copied in here so `ursina_sim` has no dependency outside its own
folder. **This is a snapshot, not a live link** — fixes made to the
original sandbox project will not appear here automatically, and vice
versa.

Not vendored (present in the original project, unused here): `zoom_manager.py`,
`window_manager.py`, `ui_manager.py`, `ui_constants.py`, `watcher.py`,
`my_object.py`, `main.py`, `run.py`.

## Files

- `src/scalable.py` — `Scalable` base class (numpy-backed uniform scaling
  helper) that `scene_setup.py`/`frame.py` build on.
- `src/color_manager.py` — loads scene colors from
  `config/json/colors.json` if present, otherwise falls back to sane
  defaults; used for the floor and axis-frame colors.
- `src/input_manager.py` — centralizes keyboard input dispatch;
  `register_key_handler(key, callback)` is the extension point `main.py`
  uses for the `1`/`2` (tilt) and `r` (rig reload) keys.
- `src/update_manager.py` — per-frame update dispatch for whatever's been
  registered with it (here, just the scene setup).
- `src/frame.py` — draws the X/Y/Z origin axes gizmo (loads
  `assets/arrow.obj`).
- `src/scene_setup.py` — builds the first-person camera/controller,
  lighting (directional + ambient), and cursor toggle.
- `assets/arrow.obj` — 3D arrow model used by the axes gizmo. Ursina
  compiles this to a `.bam` on first run into `ursina_sim/models_compressed/`
  (gitignored, regenerated automatically — not something to hand-edit).
