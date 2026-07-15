# The fixture rig (`luminaires_rig.json`) — how to use it

This is the practical, field-by-field guide to `luminaires_rig.json`, the
file that defines every spotlight in the `SCENARIO='spiral'` scene (the
default scenario — see `../main.py`). If you just want to add, move, or
retune a fixture, this document has what you need. For the math behind
the numbers (photometry, the spiral's geometry) see `LUMINAIRE.md` and
`GEOMETRY.md`; for the loader's own implementation notes see
`../src/rig_io.py`'s module docstring — this file explains the *shape*
of the JSON and how to work with it day to day, `rig_io.py` explains how
that shape gets turned into `Luminaire` objects.

`SCENARIO='rings'` does not read this file at all — its rig is a small
synthetic ring of lights generated in code (`main.py`'s
`_luminaire_on_ring`). Everything below applies only to `'spiral'`.

## The edit-and-see-it workflow

1. Run `python main.py` (or `python watcher.py` to auto-restart on exit).
2. Edit `luminaires_rig.json` by hand in any text editor while the app is
   running.
3. Save the file, then press **R** in the app window. It re-reads the
   file from disk and rebuilds everything that depends on it — fixture
   markers, index labels, aim/aperture gizmos, the illuminance color
   scale — without restarting the app.
4. Pressing **1**/**2** (tilt every fixture down/up) writes each
   fixture's new absolute tilt angle straight back into this same file,
   so the file always reflects the last angle you saw on screen — you
   don't need to copy numbers back by hand.

If the file has a mistake `load_rig()` can't work around (a missing
required field, an out-of-range value — see "Validation errors" below),
startup (or the R-reload) raises a Python exception naming the exact
fixture index and field at fault. There is no partial/best-effort load —
either the whole rig loads or none of it does.

## Top-level shape

```json
{
  "groups": {
    "<group name>": {
      "...shared settings...": "...",
      "fixtures": [ { "...fixture...": "..." }, ... ]
    }
  },
  "fixtures": [
    { "...fixture with no group...": "..." }
  ]
}
```

Two places a fixture can live:

- **Nested inside a group**, under `groups.<name>.fixtures` — the normal
  case. The fixture inherits any shared setting (`mode`, `power_lm`,
  `tilt_deg`, `theta_max_deg`, `d_offset`) its group defines, and only
  needs to specify what's actually its own (position, and anything it
  wants to override).
- **In the top-level `fixtures` array**, alongside `"groups"` — for a
  one-off fixture that doesn't belong to any group. It gets *no*
  fallback values from anywhere, so it must set every required field
  itself (`mode`, `power_lm`, `theta_max_deg`, plus its position fields).
  The real rig currently has exactly one of these: fixture 20, a 15000 lm
  floodlight aimed at the construction's peak (see the worked example
  below).

A fixture's group membership is purely *where it's written in the file*
— there is no `"group": "..."` field on the fixture object anymore (an
older version of this file worked that way; if you're looking at an old
copy or an old note that mentions a per-fixture `"group"` field, it's
out of date).

## Group settings (`groups.<name>`)

| field | required? | meaning |
|---|---|---|
| `enabled` | no (default `true`) | see "Enabling/disabling" below |
| `mode` | yes, unless every fixture in the group sets its own | `"free"` or `"spiral"` — see "Fixture position" below |
| `power_lm` | yes, unless every fixture sets its own | luminous flux Φ, lumens (`LUMINAIRE.md` §1) |
| `tilt_deg` | no (default `0.0`) | absolute tilt from horizontal, degrees, positive = up |
| `theta_max_deg` | yes, unless every fixture sets its own | beam half-angle, degrees, `(0, 90]` |
| `d_offset` | no (default: whatever `main.py` passes to `load_rig`, currently `0.05` m) | source offset added to distance before the inverse-square falloff, avoids a divide-by-near-zero blowout for very close segments |
| `fixtures` | yes (can be an empty array) | this group's fixture list |

Any of `mode`/`power_lm`/`tilt_deg`/`theta_max_deg`/`d_offset` can
instead be set (or overridden) directly on an individual fixture inside
the group — the fixture's own value always wins if present, otherwise
the group's value is used. This is the main point of grouping: put a
setting once on the group instead of repeating it on every fixture, and
override just the one fixture that needs to differ (a narrower spot, a
custom tilt, ...).

`mode`, `power_lm` and `theta_max_deg` are the three fields that must be
resolvable *somehow* — set on the fixture, on its group, or (for a
groupless fixture) directly, since there's no group to check. If none of
those apply, loading fails with a `ValueError` naming the fixture index
and the missing field.

## Fixture fields

Every fixture, wherever it lives, can have:

| field | meaning |
|---|---|
| `index` | ignored on read — `load_rig()` always overwrites it with the fixture's position in the flattened list (see "Index numbering" below). Written back to the file for your own reference (matches the number floating above the fixture in the scene). |
| `enabled` | `true`/`false`, default `true` — see "Enabling/disabling" |
| `mode` | overrides the group's `mode`, or sets it (groupless fixture) |
| `power_lm` | overrides the group's `power_lm` |
| `tilt_deg` | overrides the group's `tilt_deg` (or the `0.0` default) |
| `theta_max_deg` | overrides the group's `theta_max_deg` |
| `d_offset` | overrides the group's `d_offset` |
| *position fields* | **not** inherited from the group — always set per-fixture, see below |

### Position: `mode: "free"`

```json
{ "mode": "free", "x_m": 3.0, "y_m": 1.5, "z_m": 0.0, ... }
```

`x_m`/`y_m`/`z_m` — absolute world position in meters, anywhere. This is
the escape hatch for anything not mounted directly on the construction:
floor floodlights, a light on a truss, a pole, whatever. No range checks
are applied — you're responsible for the position making physical sense.

### Position: `mode: "spiral"`

```json
{ "mode": "spiral", "s_pct": 34.0, "side": 1, "h_m": 2.97, ... }
```

Mounts the fixture directly on the construction itself, treating the
analytic spiral curve as a "virtual column" at any point along it (not
snapped to one of the discrete real columns — `GEOMETRY.md`'s actual
0.17 m column pitch is a separate, finer-grained concept from this
placement).

- **`s_pct`** — position along the spiral's length, as a percentage,
  **0 to 100**. `s_pct=0` is the tall, center end (height 9.0 m);
  `s_pct=100` is the short, outer end (height 0 m). Height decreases
  monotonically as `s_pct` increases. Some reference points on the real
  curve (independent of column pitch — a property of the curve's shape):

  | `s_pct` | column height there |
  |---|---|
  | 0 | 9.00 m (the very peak) |
  | 33.46 | 4.00 m |
  | 64.06 | 2.00 m |
  | 100 | 0.00 m |

- **`side`** — `1` or `2` (default `1`), which of the two mirrored
  spiral arms. The two arms are point-reflections of each other through
  the origin, so `side=1`/`side=2` at the same `s_pct` sit at opposite
  ends of the construction, same height.
- **`h_m`** — mounting height above the ground, meters. Must satisfy
  **both**:
  1. `2.0 <= h_m <= 4.0` (a person mounting a fixture by hand won't
     reach below head height or above what a ladder comfortably allows —
     `MOUNT_HEIGHT_MIN`/`MOUNT_HEIGHT_MAX` in `rig_io.py`), and
  2. `h_m` does not exceed the actual column height at that `s_pct`/
     `side` (you can't float a fixture above the top of the column it's
     mounted on).

  Combining both constraints: mounting is only physically possible for
  `s_pct` roughly in `[0, 64.06]` — beyond that the column itself is
  already shorter than the 2 m minimum reach.

The built fixture is nudged 0.10 m radially toward the center from the
exact curve point (`SPIRAL_MOUNT_INSET_M` in `rig_io.py`) — mounting a
fixture exactly on the line of "its own" column would put it right
against (practically touching) the very column it's illuminating,
producing a nonphysical near-zero-distance blowout in the segments right
at the mount point. The `h_m` range checks above use the true on-column
point, before this shift — only the built `Luminaire`'s actual position
moves.

#### Mechanics: what `s_pct` actually parametrizes (read this before spacing fixtures)

`s_pct` is **not** a fraction of physical distance along the spiral,
even though "position along the spiral's length" (and the code's own
naming — `spiral.column_at_s`, "spiral-length fraction") suggests it. It
is actually a fraction of the spiral's underlying **angular parameter**
φ, over the fixed range `[φ0, φ_max]` (`GEOMETRY.md` §2/§3):

```
phi = phi0 + (s_pct / 100) * (phi_max - phi0)
(x, z) = point on the Archimedean curve R = a*phi at that phi
height  = continuous_height(phi)   <- the TRUE Lagrange profile,
                                       evaluated at the real arc-length
                                       fraction of that phi (see below)
```

`φ0 ≈ 1.795` rad is fixed (the construction's tall center end); `φ_max
≈ 12.622` rad is solved numerically (Newton's method, `spiral.py`,
`_solve_phi_max`) so that the arc length from `φ0` to `φ_max` equals the
construction's fixed total unrolled length (`a·L ≈ 25.28` m,
`GEOMETRY.md` §3) — that solve is independent of column pitch, so it
doesn't change if `main.py`'s `SPIRAL_PITCH` is overridden for testing.

**Why this matters in practice:** an Archimedean spiral's arc length
does not grow linearly with φ — `ds/dφ = a·√(1+φ²)` gets larger as φ
(and the radius) grows, so a fixed step in φ (equivalently, a fixed step
in `s_pct`) covers *more* physical distance out near the wide outer
turns than it does near the tightly-wound center. Concretely, measured
against the true arc-length fraction from the center:

| `s_pct` | true arc-length fraction from center |
|---|---|
| 0 | 0 % |
| 10 | 3.5 % |
| 32 | 16.1 % |
| 48 | 29.7 % |
| 64 | 47.1 % |
| 80 | 68.3 % |
| 100 | 100 % |

So `s_pct=64` is only **47 %** of the way along the actual curve, not
64 %. The column **height** you get is still exactly physically correct
— `continuous_height(phi)` always converts through the real arc-length
fraction internally (`GEOMETRY.md` §5's Lagrange profile is defined
against true arc length, not φ), which is why the height numbers in the
table above this section are accurate. It's specifically the *spacing*
implied by evenly-stepped `s_pct` values that is not arc-length-uniform.

**What this means for the real rig:** the `columns` group's five
`s_pct` values (32/40/48/56/64, evenly spaced *in `s_pct`*) are
therefore **not** evenly spaced along the actual construction — they sit
closer together physically than the even 8-point spacing suggests, all
bunched into the outer ~47% of the arc length (per the table above).
This was an accepted simplification when that test layout was built, not
a considered choice about physical fixture spacing. If you need fixtures
truly evenly spaced along the real curve, don't step `s_pct` evenly —
compute the φ (or arc-length) values you want first and convert back to
`s_pct = 100 * (phi - phi0) / (phi_max - phi0)`, or treat `s_pct` as a
rough "how far from the center" dial rather than a ruler.

## Aiming and tilt

Every fixture aims the same way, no matter its mode or position:
**horizontally toward the central vertical axis** (the line `x=0, z=0`
through the world origin), **then tilted up or down by `tilt_deg`**.
There is currently no way to aim a fixture at an arbitrary 3D point —
only "toward the axis" (horizontal) composed with "up/down by this many
degrees" (vertical). If you need a fixture to hit a specific point that
isn't on (or very near) the central axis, you have to work out the
right `tilt_deg` yourself the same way a floor fixture is aimed at the
structure: `tilt_deg = degrees(atan2(target_height - y_m, horizontal_distance_to_axis))`.

**Worked example** — fixture 20 in the real rig, a floodlight aimed at
the construction's peak:

```json
{
  "index": 20, "mode": "free", "power_lm": 15000, "theta_max_deg": 45,
  "tilt_deg": 41.987, "x_m": 0.0, "y_m": 0.0, "z_m": 10.0
}
```

It sits on the ground (`y_m=0`) 10 m out along +Z. The peak (the tall
end of each spiral arm, `s_pct=0`) is 9.0 m up and *almost* — but not
exactly — on the central axis (it's actually ~0.57 m off-axis; see
`GEOMETRY.md` §2's `PHI0`). `tilt_deg` was computed as
`degrees(atan2(9.0, 10.0)) ≈ 41.987°`, i.e. "aim at the axis, tilted up
enough to hit 9 m at 10 m out" — the same approximation every other
fixture in the rig already uses, and at 10 m away the ~0.57 m horizontal
miss is a fraction of a degree, not worth a more exact calculation.

`tilt_deg` in the file is always this **absolute** angle from horizontal
— never a delta relative to a previous edit or session. Pressing 1/2 in
the running app changes every fixture's absolute tilt (clamped
independently per fixture to ±90°, 2.5° per press — `TILT_STEP_DEG`/
`TILT_LIMIT_DEG` in `main.py`) and immediately overwrites `tilt_deg` in
the file to match, for every fixture, group or no group. That means: if
you hand-edit `tilt_deg` values and then also press 1/2 in the app, your
hand-edited values get overwritten with whatever the app computed — save
your edits, reload with R, *then* fine-tune with 1/2 if you want both.

## `theta_max_deg` — beam angle

The maximum deviation from the aim axis, in degrees, i.e. `30` lights a
`±30°` cone (`60°` full width), not a `30°`-wide one. Must be in
`(0, 90]`. Changing it automatically redistributes the fixture's
`power_lm` over the new cone (a narrower beam gets brighter at the
center, same total flux) — no other field needs adjusting when you
change this (see `LUMINAIRE.md` §5 for the formula).

## Enabling/disabling

A fixture actually contributes light only if **both** are true:

- its own `enabled` (default `true`), **and**
- its group's `enabled` (default `true`; groupless fixtures have no
  group, so only their own `enabled` applies).

So `groups.columns.enabled: false` turns off all ten `columns` fixtures
in one edit, while an individual fixture's own `"enabled": false` turns
off just that one regardless of its group. Disabled fixtures are **not**
removed from the scene — they still get a marker (shown gray instead of
yellow) and keep their index, so you can still see where they are and
re-enable them later without renumbering anything. They're simply
skipped when illuminance is computed.

## Index numbering

`index` is always recomputed on load, never read from the file. The
numbering walks every group's `fixtures` array (groups in the order they
appear in `groups`), then the top-level (groupless) `fixtures` array —
so index order follows file order. In the real rig: `columns` fixtures
are 0-9, `floor` fixtures are 10-19, and the groupless peak floodlight is
20. If you add, remove, or reorder fixtures, every following index
shifts accordingly on the next load/reload — this is expected, and is
also exactly what the number floating above each marker in the scene
will show.

## Validation errors you might hit

All of these are raised as `ValueError` naming the offending fixture
index (and field, where applicable) at load time — nothing loads
partially.

- Missing `mode` / `power_lm` / `theta_max_deg`, and no group (or no
  group value) to fall back to.
- `theta_max_deg` outside `(0, 90]`.
- `mode` is something other than `"free"` or `"spiral"`.
- `mode: "spiral"` with `h_m` outside `[2.0, 4.0]`.
- `mode: "spiral"` with `h_m` greater than the actual column height at
  that `s_pct`/`side`.
- Missing a mode-specific position field (`x_m`/`y_m`/`z_m` for `free`;
  `s_pct`/`h_m` for `spiral` — `side` is optional, defaults to `1`).

## What ends up in `luminaires_output.csv`

Every recompute (startup, every tilt keypress, every R reload) rewrites
`luminaires_output.csv` — one row per fixture, in the same index order,
columns: `index, group, enabled, x_m, y_m, z_m, aim_x, aim_y, aim_z,
phi_lm, theta_max_deg, d_offset_m, i0_cd, tilt_deg`. `group` is the empty
string for a groupless fixture. `aim_x/aim_y/aim_z` and `tilt_deg` are
always the fixture's *current* resolved values (after applying any
group fallback and any interactive tilt) — this file is a flat,
fully-resolved dump for inspection/analysis, not something you hand-edit
(unlike `luminaires_rig.json` itself, which is the source of truth).
