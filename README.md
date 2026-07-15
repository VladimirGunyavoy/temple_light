# ursina_sim — spiral art-construction lighting simulator

Simulates how a set of spotlight fixtures light up a spiral art
construction (a forest of vertical boards arranged along two mirrored
Archimedean spirals, each with its own height — see
[docs/GEOMETRY.md](docs/GEOMETRY.md)): computes per-segment illuminance
(including self-occlusion by the construction), renders it as an
interactive 3D scene, and exports the same data as CSV for offline
analysis.

## Requirements

- Python 3.11+ (Ursina does not yet support every newer Python release —
  if `pip install ursina` fails on your default interpreter, install a
  3.11.x side by side and use that one)
- `pip install -r requirements.txt` (Ursina + numpy)

## Running

```bash
python main.py
```

or, to auto-restart the scene whenever you exit normally (Escape) so
edited files are picked up without relaunching by hand:

```bash
python watcher.py
```

If you run `watcher.py` with a *different* interpreter than the one that
has Ursina installed (e.g. a system default Python next to a separate
Ursina-enabled install), point it at the right one with an environment
variable instead of editing the script:

```bash
URSINA_PYTHON="/path/to/ursina-python" python watcher.py
```

### Controls

- **WASD** — move, **mouse** — look, **Space/Shift** — up/down, **Alt** —
  release/capture cursor, **Escape** — quit, **H** — debug info
- **1 / 2** — tilt every fixture down/up together (2.5° per press, clamped
  to ±90° from horizontal per fixture)
- **R** — reload `luminaires_rig.json` from disk (hand-edit the file,
  press R, see it applied without restarting)

## Scenarios

`main.py` has a `SCENARIO` switch near the top:

- `'spiral'` (default) — the real construction, geometry from
  `src/spiral.py`, fixture rig loaded from `luminaires_rig.json`.
- `'rings'` — a synthetic two-ring test stand-in (used to validate the
  physics/occlusion math against a simpler shape), with a placeholder
  rig generated in code.

## The fixture rig (`luminaires_rig.json`)

**See [docs/RIG.md](docs/RIG.md) for the full field-by-field guide** —
this is just the shape, for orientation.

A JSON object: `{"groups": {...}, "fixtures": [...]}`. Fixtures live
*nested inside their group* (`groups.<name>.fixtures`, sharing that
group's settings unless they override one); the top-level `fixtures`
array is only for fixtures with no group at all, which must set every
required field themselves.

Each fixture has a position mode:

- `"mode": "free"` — absolute world position (`x_m, y_m, z_m`).
- `"mode": "spiral"` — mounted on the construction itself, given as a
  parameter along its length (`s_pct`, 0-100 — *not* a linear physical
  distance, see docs/RIG.md), which of the two mirrored arms (`side`: 1
  or 2), and mount height (`h_m`, must be within a person's reach and not
  exceed the column's actual height there).

A fixture can be switched on/off two ways: `groups.<name>.enabled` turns
off every fixture in that group at once, or a fixture's own
`"enabled": false` turns off just that one — a fixture only lights up if
**both** are true. Disabled fixtures stay visible in the scene (as gray
markers) so you can still see where they are; they just don't contribute
light.

`tilt_deg` is always the fixture's absolute angle from horizontal
(never a delta) — pressing 1/2 in the scene writes each fixture's current
tilt back into this file, so it persists across restarts.

## Outputs

Every run (and every tilt keypress) rewrites, in this folder:

- `segments_output.csv` — one row per structure segment: position,
  surface normal, illuminance.
- `luminaires_output.csv` — one row per fixture: position, aim direction,
  power, group/enabled, current tilt.

Both are gitignored (regenerated, not source).

## Project layout

```
ursina_sim/
├── main.py              entry point: scene, scenario setup, keybindings
├── watcher.py            auto-restart wrapper around main.py
├── color_ramp.py         illuminance -> color mapping for the segment view
├── gizmo.py              Ursina entities for a fixture's aim beam + aperture cone
├── export.py             framework-free CSV export
├── luminaires_rig.json   the fixture rig for SCENARIO='spiral' (see above)
├── src/                  framework-free physics core — see src/README.md
├── docs/                 design background (geometry/pieces/photometry) — see docs/README.md
├── sim/                  standalone CSV export tool, no Ursina needed — see sim/README.md
└── vendor/               vendored scene-scaffolding dependency — see vendor/README.md
```

## What's still a placeholder

- Board width/thickness and segment length (`main.py`) are eyeballed, not
  finalized.
- The `'spiral'` rig's fixture count/positions are a working test layout,
  not the final real-equipment list.
- Occlusion treats each spiral arm as one continuous solid ribbon (board
  gaps between individual columns are ignored) — a deliberate
  simplification, not a bug.
- Light reflections off the construction/ground are not modeled at all.
