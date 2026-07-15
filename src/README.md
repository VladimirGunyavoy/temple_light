# src/ — framework-free physics core

No Ursina, no numpy except `spiral.py` — this is the single source of
truth for the light-simulation math, shared by both the interactive
Ursina viewer (`../main.py`) and the standalone CSV exporter
(`../sim/wall_example.py`). Background/formulas live in `../docs/`.

## Files

- `vectors.py` — plain-tuple 3D vector ops (add/sub/scale/dot/cross/
  normalize/rotate). Everything else here is built on these.
- `luminaire.py` — `Luminaire`: one spotlight's photometric model
  (`I(psi) = I0*cos(psi)` inside a cone, `docs/LUMINAIRE.md`), plus the
  tilt/aim helpers and the gizmo-geometry helpers used to draw its
  aperture cone.
- `luminaires.py` — `Luminaires`: a collection of `Luminaire`s addressable
  by index, with `tilt_all()` for the shared up/down tilt controls.
- `column.py` / `segment.py` — a column (vertical post) sliced into
  `Segment`s; each segment samples illuminance at its bottom/mid/top
  points (`docs/PIECES.md`).
- `structure.py` — `Structure`: all columns/segments for one scenario.
  Three constructors: `wall()` (old flat test wall, used only by
  `../sim/wall_example.py`), `circle()` (synthetic ring, `SCENARIO='rings'`
  in main.py), `spiral()` (the real construction, `SCENARIO='spiral'`).
- `spiral.py` — analytic geometry of the real two-armed Archimedean
  spiral (`docs/GEOMETRY.md`): plan positions, the Lagrange column-height
  profile, and ray/spiral-curve intersection for occlusion
  (`ray_blocked_by_spiral` + a numpy-vectorized `.batch` version). The
  only module here that needs numpy.
- `occlusion.py` — `ray_blocked_by_wall`: the simpler occlusion check used
  by the synthetic ring scenario (ray vs. a single cylindrical wall).
- `orchestrator.py` — `Orchestrator`: matches every segment of a
  `Structure` against every luminaire in a `Luminaires` rig to compute
  illuminance, wiring in whichever occlusion check the scenario uses
  (batched if the occluder exposes one, e.g. `spiral.ray_blocked_by_spiral`).
- `rig_io.py` — loads/saves a luminaire rig from
  `../luminaires_rig.json`: fixture positions (free-form or mounted on the
  spiral), per-fixture/per-group enable flags, absolute tilt persistence.
  See its module docstring for the JSON schema.
