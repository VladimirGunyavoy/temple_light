# docs/ — design background + usage guides

Two kinds of document here: design background (the math/reasoning behind
the code, read once to understand *why*) and a usage guide (read
whenever you're actually editing the rig). Read the design docs in this
order:

1. **GEOMETRY.md** — shape of the construction: two mirrored Archimedean
   spirals of columns in plan, each column's height given by a Lagrange
   interpolation profile. Units, axes, and the column-pitch/scale
   decisions are all recorded here.
2. **PIECES.md** — how a column is broken into `Segment`s for illuminance
   sampling (board cross-section, not a cylinder; one fixed outward face
   normal per board).
3. **LUMINAIRE.md** — the spotlight photometric model (`I(psi) =
   I0*cos(psi)` inside a cone, calibrated over the fixture's actual beam
   cone) that `src/luminaire.py` implements.

Then, separately:

4. **RIG.md** — practical, field-by-field guide to `luminaires_rig.json`
   (the fixture list for `SCENARIO='spiral'`): the JSON shape, every
   field and what it means, both position modes (including the
   non-obvious mechanics of `mode="spiral"`'s `s_pct`), aiming/tilt,
   enabling/disabling, and the validation errors you might hit. Start
   here if you just want to add or move a fixture and don't care about
   the underlying math.

GEOMETRY/PIECES/LUMINAIRE describe the *design*, not the current code
state — e.g. numeric placeholders (board width/thickness, segment
length) may have been superseded by later values in `main.py`/
`src/rig_io.py`. When in doubt, the code is authoritative for current
numbers; these docs are authoritative for the reasoning behind them.
RIG.md is a live usage guide, not a design-history doc — if it and the
code ever disagree, that's a bug in RIG.md, not "historical context" (see
`src/rig_io.py`'s own module docstring, which is the implementation-level
counterpart to RIG.md's user-facing one).
