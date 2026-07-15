"""Load/save a luminaire rig (fixture list) from a JSON file — see
light/.llm/CONTEXT.md "что дальше" #2 (real luminaire list from the user).

The file is a JSON object: {"groups": {...}, "fixtures": [...]}. Each entry
of `groups` is a group's shared settings PLUS its own `"fixtures"` array
(fixtures live nested inside their group, not as a flat list with a
`"group"` back-reference — a fixture's group membership is its position in
the file, not a field on the fixture). The top-level `"fixtures"` array
holds fixtures that don't belong to any group at all — for those, every
required field (`mode`, `power_lm`, `theta_max_deg`) must be set directly
on the fixture, since there's no group to fall back to. Every fixture aims
horizontally at the central vertical axis (through the world origin) by
default, then tilts up/down by `tilt_deg` — the exact same rotation as
Luminaire.tilt_pitch / the interactive 1/2 keys (positive = up), just
applied once at load time instead of interactively. `power_lm` is the
fixture's luminous flux (Phi, ../docs/LUMINAIRE.md §1).

Any non-positional field — `mode`, `power_lm`, `tilt_deg`, `theta_max_deg`,
`d_offset` — can be set on a fixture's group instead of repeating it on
every fixture: a fixture's own value wins if it sets one, otherwise it
falls back to its group's shared value (see `_group_value`/
`_require_group_value` below). `mode`, `power_lm` and `theta_max_deg` are
required one way or the other (on the fixture or its group) — load_rig
raises ValueError naming the fixture and field if neither sets it.
`tilt_deg` falls back further, to 0.0, if neither sets it. `d_offset`
falls back to whatever the caller passed into load_rig() (main.py's
D_OFFSET) if neither sets it. Position fields (x_m/y_m/z_m/s_pct/side/h_m
below) are NOT covered by this fallback — those are inherently per-fixture,
not something a whole group shares. Groupless fixtures have no group to
fall back to at all, so they must set every required field themselves.

`theta_max_deg` — the beam's maximum deviation from center (half-angle),
e.g. "30" lights a +/-30 deg cone around aim_dir, not a 30-deg-wide one —
must be in (0, 90] deg. Luminaire renormalizes I0 to whatever cone it's
given (see its docstring/../docs/LUMINAIRE.md §5), so changing a fixture's
(or its group's) angle automatically redistributes the same power_lm over
the new cone — no other field needs adjusting.

Position has two modes, picked by the `mode` key:

  mode="free":   x_m, y_m, z_m    — absolute world position, anywhere.
  mode="spiral": s_pct, side, h_m — mounted on the (virtual) column at
                                    parameter s_pct in [0, 100]
                                    (spiral.column_at_s takes the 0..1
                                    fraction, s_pct/100 — NOTE it's linear
                                    in the spiral's angular parameter phi,
                                    not in true arc length, see its
                                    docstring / ../docs/RIG.md; side: 1 or
                                    2 selects which of the two mirrored
                                    spiral arms, default 1), at height h_m
                                    above the ground. h_m must not exceed
                                    that column's height there — the user
                                    can only mount a light on a column, not
                                    float it above one — and must fall
                                    within [MOUNT_HEIGHT_MIN,
                                    MOUNT_HEIGHT_MAX] (user-supplied
                                    physical reach limits for someone
                                    mounting a fixture by hand: not below
                                    head height, not above what a person
                                    can reach).

Each fixture belongs to a `group` (a free-form string label, e.g.
"columns"/"floor" for the two groups currently in use). `enabled` is the
one field that does NOT use the plain fixture-overrides-group fallback
above — it's a separate AND: a fixture is actually lit only if BOTH its
own `enabled` (default true) AND its group's `enabled` (also default true)
are true, so a whole group can be switched off with one edit (set
`groups.<name>.enabled: false`) without that overriding a fixture that
explicitly wants to stay off (or on) regardless of its group. Disabled
fixtures still get a Luminaire object (kept in RigData.luminaires, same
1:1 order as rows) so indices/markers/labels stay stable — they're just
skipped when computing illuminance (Segment.compute_illuminance /
Orchestrator, via the `.enabled` attribute this module stamps on each
Luminaire).

Example:
    {
      "groups": {
        "columns": {"enabled": false, "mode": "spiral", "power_lm": 5000,
                    "tilt_deg": 87.5, "theta_max_deg": 60,
                    "fixtures": [
                      {"index": 0, "s_pct": 34.0, "side": 1, "h_m": 2.97},
                      {"index": 1, "theta_max_deg": 15,
                       "s_pct": 50.0, "side": 1, "h_m": 2.5}
                    ]},
        "floor": {"enabled": true, "mode": "free", "power_lm": 5000,
                  "tilt_deg": 57.5, "theta_max_deg": 45,
                  "fixtures": [
                    {"index": 2, "x_m": 3.0, "y_m": 1.5, "z_m": 0.0}
                  ]}
      },
      "fixtures": [
        {"index": 3, "mode": "free", "power_lm": 15000, "theta_max_deg": 45,
         "tilt_deg": 42.0, "x_m": 0.0, "y_m": 0.0, "z_m": 10.0}
      ]
    }
(fixture 0 takes mode/power_lm/tilt_deg/theta_max_deg entirely from its
"columns" group; fixture 1 is also a "columns" fixture but overrides just
its own angle to a narrow 15-deg spot, everything else still from the
group; fixture 2 takes everything from "floor"; fixture 3 sits in the
top-level `fixtures` array — it has no group, so it sets every required
field itself.)

`index` is stamped by load_rig() itself on every load/reload — it always
matches the fixture's position when every group's `fixtures` array (in
`groups` insertion order) and then the top-level `fixtures` array are
flattened into one sequence (same numbering as the billboarded labels
above each fixture in the scene, and the `index` column in
luminaires_output.csv), so it stays correct even if rows are added/
removed/reordered by hand; whatever value was in the file is overwritten,
not read.

load_rig() also hands back the raw parsed row dicts and a groups dict
(RigData.rows / RigData.groups, the latter WITHOUT the nested `fixtures`
arrays — just each group's shared settings) so the caller can round-trip
the file:
main.py's `r` key reloads it (edit-by-hand workflow, no app restart) and
every interactive tilt keypress writes each fixture's current absolute
tilt_deg back into these same rows via sync_tilt_deg() + write_rig(), so a
later reload picks up the tilt exactly where it was left
(light/.llm/CONTEXT.md) — tilt_deg is always an absolute angle from
horizontal, never a delta relative to a previous load/session.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luminaire import Luminaire  # noqa: E402
import spiral                    # noqa: E402

# Spiral-mode mounting height limits, m — a person mounting fixtures by hand
# won't go below head height or above arm's reach on a ladder (user's
# real-world constraint, not a structural one — free mode has no such limit).
MOUNT_HEIGHT_MIN = 2.0
MOUNT_HEIGHT_MAX = 4.0

# Spiral-mode mounting stand-off, m — column_at_s() places the fixture
# exactly ON the virtual column's own line, which otherwise puts the
# fixture right against (and its aim ray originating from) the very post
# it's mounted on: segments of that post sit at ~the same (x, z) at nearby
# heights, so distance -> ~0 and illuminance blows up right at the mount
# point. Shifting the fixture radially inward (toward the center) by this
# amount clears it off that post — also a reasonable stand-in for a real
# mounting bracket. Placeholder value, not finalized (like board_width/
# board_thickness in main.py).
SPIRAL_MOUNT_INSET_M = 0.10


class RigData:
    """Result of load_rig(): the constructed fixtures plus the raw row
    dicts and groups dict (parsed JSON) so the file can be written back out
    unchanged except for whatever the caller edits (see add_tilt_delta)."""

    def __init__(self, luminaires, rows, groups):
        self.luminaires = luminaires
        self.rows = rows
        self.groups = groups


def _aim_at_center(x, z):
    r = math.hypot(x, z)
    if r < 1e-9:
        return (1.0, 0.0, 0.0)  # degenerate: fixture sits exactly on the central axis
    return (-x / r, 0.0, -z / r)


def _group_value(row, groups, group, key):
    """A fixture's own `key` if it set one, else its group's shared value
    for `key` (groups.<group>.<key> in the JSON), else None. Lets a group
    carry a default for any non-positional field (mode, power_lm, tilt_deg,
    theta_max_deg, ...) that every fixture in it would otherwise repeat —
    a fixture can still override just that one field by setting it itself.
    Not used for position fields (x_m/y_m/z_m/s_pct/side/h_m) — those are
    inherently per-fixture, not something a whole group shares.

    Not used for `enabled` either — that's a separate, deliberately
    different mechanism (see load_rig): both the fixture's own and its
    group's `enabled` apply together (AND), rather than one overriding the
    other."""
    if key in row:
        return row[key]
    return groups.get(group, {}).get(key)


def _require_group_value(row, groups, group, key, path, i):
    value = _group_value(row, groups, group, key)
    if value is None:
        raise ValueError(
            f"{path}: fixture {i}: missing required field {key!r} "
            f"(set it on the fixture itself or on its group {group!r})"
        )
    return value


def load_rig(path, d_offset):
    """Returns a RigData built from the JSON fixture rig at path."""
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)

    raw_groups = raw.get('groups', {})
    # Group settings without the nested 'fixtures' array — this is what
    # _group_value/_require_group_value look up, and what RigData.groups
    # hands back to the caller for round-tripping (write_rig re-nests the
    # fixtures back under each group at save time).
    groups = {name: {k: v for k, v in gdata.items() if k != 'fixtures'}
              for name, gdata in raw_groups.items()}

    # Flatten: every group's fixtures (in groups' file order), then the
    # top-level (groupless) fixtures — this fixes the global 'index'
    # numbering used for scene labels/luminaires_output.csv.
    entries = []  # (group_name_or_None, raw_row)
    for group_name, gdata in raw_groups.items():
        for raw_row in gdata.get('fixtures', []):
            entries.append((group_name, raw_row))
    for raw_row in raw.get('fixtures', []):
        entries.append((None, raw_row))

    fixtures = []
    rows = []
    for i, (group, raw_row) in enumerate(entries):
        # stamp/refresh 'index' (and 'group') first so they always match
        # array position / nesting, regardless of whatever was (or wasn't)
        # in the file already.
        row = {'index': i, 'group': group,
               **{k: v for k, v in raw_row.items() if k not in ('index', 'group')}}
        rows.append(row)

        mode = str(_require_group_value(row, groups, group, 'mode', path, i)).strip().lower()
        power = float(_require_group_value(row, groups, group, 'power_lm', path, i))
        tilt_raw = _group_value(row, groups, group, 'tilt_deg')
        tilt_deg = float(tilt_raw) if tilt_raw is not None else 0.0
        fixture_theta_max_deg = float(_require_group_value(row, groups, group, 'theta_max_deg', path, i))
        if not (0.0 < fixture_theta_max_deg <= 90.0):
            # 0 would divide-by-zero in Luminaire's cone calibration (see its
            # docstring); >90 deg would spill the cone into the back
            # hemisphere, which isn't a real spotlight aperture.
            raise ValueError(
                f"{path}: fixture {i}: theta_max_deg={fixture_theta_max_deg:.3f} "
                f"must be in (0, 90] deg"
            )
        fixture_enabled = bool(row.get('enabled', True))
        group_enabled = bool(groups.get(group, {}).get('enabled', True))
        enabled = fixture_enabled and group_enabled

        if mode == 'free':
            x = float(row['x_m'])
            y = float(row['y_m'])
            z = float(row['z_m'])
        elif mode == 'spiral':
            s = float(row['s_pct']) / 100.0
            side = int(row.get('side', 1))
            h = float(row['h_m'])
            if not (MOUNT_HEIGHT_MIN - 1e-9 <= h <= MOUNT_HEIGHT_MAX + 1e-9):
                raise ValueError(
                    f"{path}: fixture {i}: h_m={h:.3f} outside allowed mount range "
                    f"[{MOUNT_HEIGHT_MIN}, {MOUNT_HEIGHT_MAX}] m"
                )
            x, z, max_h = spiral.column_at_s(s, mirror=(side == 2))
            if h > max_h + 1e-9:
                raise ValueError(
                    f"{path}: fixture {i}: h_m={h:.3f} exceeds column height "
                    f"{max_h:.3f} m at s_pct={row['s_pct']} side={side}"
                )
            y = h
            # shift off the column's own line, toward the center, so the
            # fixture doesn't sit exactly on the post it's mounted on (see
            # SPIRAL_MOUNT_INSET_M above). Height-range/max_h checks above
            # use the true on-column point — this only moves the built
            # Luminaire's position, not what's validated.
            r = math.hypot(x, z)
            if r > 1e-9:
                x -= x / r * SPIRAL_MOUNT_INSET_M
                z -= z / r * SPIRAL_MOUNT_INSET_M
        else:
            raise ValueError(f"{path}: fixture {i}: unknown mode {mode!r} (expected 'free' or 'spiral')")

        d_offset_raw = _group_value(row, groups, group, 'd_offset')
        fixture_d_offset = float(d_offset_raw) if d_offset_raw is not None else d_offset

        lum = Luminaire(position=(x, y, z), aim_dir=_aim_at_center(x, z),
                         phi=power, theta_max_deg=fixture_theta_max_deg, d_offset=fixture_d_offset)
        if abs(tilt_deg) > 1e-9:
            lum.tilt_pitch(tilt_deg)
        lum.enabled = enabled
        lum.group = group or ''
        fixtures.append(lum)

    return RigData(fixtures, rows, groups)


def sync_tilt_deg(rows, luminaires):
    """Overwrite each row's tilt_deg with that fixture's current absolute
    tilt (Luminaire.current_tilt_deg) in place — used before write_rig() so
    an interactive keypress persists as the fixture's true angle, not a
    delta relative to whatever was last saved."""
    for row, lum in zip(rows, luminaires):
        row['tilt_deg'] = round(lum.current_tilt_deg(), 3)


def write_rig(path, rows, groups):
    """Write rows/groups back out as the same nested JSON object shape they
    were read from (each group's settings plus its own 'fixtures' array,
    groupless fixtures in the top-level 'fixtures' array) — used to persist
    interactive tilt changes into the source file. `rows` carries a 'group'
    key per fixture (None for groupless, stamped by load_rig) that decides
    where each one is re-nested; that key itself is dropped from the
    written-out fixture object since nesting already encodes it."""
    out_groups = {name: {**settings, 'fixtures': []} for name, settings in groups.items()}
    ungrouped = []
    for row in rows:
        group = row.get('group')
        out_row = {k: v for k, v in row.items() if k != 'group'}
        if group is not None and group in out_groups:
            out_groups[group]['fixtures'].append(out_row)
        else:
            ungrouped.append(out_row)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'groups': out_groups, 'fixtures': ungrouped}, f, indent=2, ensure_ascii=False)
        f.write('\n')
