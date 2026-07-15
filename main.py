"""
Ursina visualization of the light simulation.

Self-contained: builds one of two scenarios (SCENARIO switch below) and
uses the Luminaire/Segment/Column classes in ./src directly, plus Structure
(all columns/segments), Luminaires (the fixture rig) and Orchestrator
(matches every segment against every luminaire to compute illuminance).
Default is 'spiral' — the real construction (docs/GEOMETRY.md), fixture
rig loaded from luminaires_rig.json (see docs/RIG.md). 'rings' is a
synthetic two-ring test scenario with a placeholder rig generated in code,
kept around to validate the physics/occlusion math against a simpler
shape. sim/wall_example.py is a separate, independent tool (still on the
older flat-wall scenario) for exporting the same kind of data to CSV/JSON
without needing ursina installed — it is NOT a dependency of this script.

Scene scaffolding is a vendored subset of player_zoom (vendor/player_zoom,
see its README) — SceneSetup with real lights + FirstPersonController,
ColorManager, InputManager, UpdateManager — instead of a bare EditorCamera,
so this renders as an actual lit 3D scene.

Requires the ursina-enabled Python install (see README.md), e.g.:
    python main.py
or run watcher.py, which restarts this automatically on normal exit (e.g.
pressing Escape) so edits are picked up without relaunching by hand.

Controls: WASD move, mouse look, Space/Shift up/down, Alt release/capture
cursor, Escape quit, H debug info.
"""
import functools
import math
import os
import sys
import time

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, SRC_DIR)
from luminaire import Luminaire                    # noqa: E402
from structure import Structure                    # noqa: E402
from luminaires import Luminaires                  # noqa: E402
from orchestrator import Orchestrator              # noqa: E402
from occlusion import ray_blocked_by_wall          # noqa: E402
from rig_io import load_rig, sync_tilt_deg, write_rig  # noqa: E402
import spiral                                      # noqa: E402

from color_ramp import ramp_color   # noqa: E402
from gizmo import LuminaireGizmo    # noqa: E402
from export import write_segments_csv, write_luminaires_csv  # noqa: E402

VENDOR_PLAYER_ZOOM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor', 'player_zoom')
sys.path.insert(0, VENDOR_PLAYER_ZOOM_DIR)
from src.scene_setup import SceneSetup        # noqa: E402
from src.color_manager import ColorManager    # noqa: E402
from src.input_manager import InputManager    # noqa: E402
from src.update_manager import UpdateManager  # noqa: E402
from src.frame import Frame                   # noqa: E402

from ursina import Ursina, Entity, Text, color, application, mouse, window, destroy  # noqa: E402
from ursina.scene import instance as scene  # noqa: E402
from pathlib import Path  # noqa: E402

# Ursina's model loader globs for named models (e.g. 'arrow.obj') under
# application.asset_folder, which defaults to *this script's* folder
# (sys.argv[0]). Point it at the vendored player_zoom so Frame can find
# assets/arrow.obj.
application.asset_folder = Path(VENDOR_PLAYER_ZOOM_DIR)

# ---- scenario select ----
# 'rings': synthetic two-ring test (occlusion/photometry validation), rig is
# a synthetic placeholder ring of lights.
# 'spiral': the real construction (docs/GEOMETRY.md), rig loaded from
# luminaires_rig.json (see rig_io.load_rig) — real fixture list, not synthetic.
SCENARIO = 'spiral'

# ---- scenario parameters (see docs/GEOMETRY.md / docs/PIECES.md / docs/LUMINAIRE.md) ----
SEG_LEN = 0.20          # m, target segment length from docs/PIECES.md
# real construction uses flat boards, not round posts (user decision) — a
# board has one well-defined face normal, unlike a cylinder (docs/PIECES.md's
# "single fixed normal" was an approximation there, exact here).
BOARD_WIDTH = 0.15       # m, tangential (along the ring) — placeholder, not finalized
BOARD_THICKNESS = 0.03   # m, radial (along the outward normal) — placeholder, not finalized

PHI = 5000.0            # lm, luminous flux
THETA_MAX_DEG = 60.0    # half-angle of beam cone
D_OFFSET = 0.05         # m, source offset from front glass

# ---- physics: structure ----
if SCENARIO == 'rings':
    COLUMN_RADIUS = 2.0     # m, radius of the outer column ring (test stand-in for the real spiral)
    COLUMN_HEIGHT = 2.0     # m, uniform column height for the outer ring
    COLUMN_RADIUS_2 = 1.5   # m, radius of the second (inner) ring — narrower and taller than the outer one
    COLUMN_HEIGHT_2 = 4.0   # m, uniform column height for the inner ring
    COLUMN_PITCH = 2      # m, docs/GEOMETRY.md's real pitch is 0.17 — widened here for this test (board-gap visibility)
    # two concentric column rings merged into one Structure, so both are
    # lit by the same rig and exported together.
    structure = Structure(
        Structure.circle(COLUMN_RADIUS, COLUMN_PITCH, COLUMN_HEIGHT, SEG_LEN).columns
        + Structure.circle(COLUMN_RADIUS_2, COLUMN_PITCH, COLUMN_HEIGHT_2, SEG_LEN).columns
    )
    # narrow-case occlusion: the outer ring, treated as one continuous solid
    # wall (board gaps ignored), can shadow the rest of the structure — not
    # yet a general every-ring-shadows-every-ring mechanism.
    occluder = functools.partial(ray_blocked_by_wall, wall_radius=COLUMN_RADIUS, wall_height=COLUMN_HEIGHT)
else:  # 'spiral'
    SPIRAL_PITCH = 0.2  # m, docs/GEOMETRY.md's real column pitch is spiral.H_STEP (0.17) — overridden here to test wider spacing
    structure = Structure.spiral(SEG_LEN, pitch=SPIRAL_PITCH)
    # occlusion: the two mirrored spirals treated as one continuous solid
    # "ribbon" wall (board gaps ignored, same simplification as the ring
    # case) — spiral.ray_blocked_by_spiral finds where a ray crosses either
    # curve and checks the crossing height against the continuous height
    # profile there (sim/spiral_line_intersection.ipynb).
    occluder = spiral.ray_blocked_by_spiral

# bounding radius/height of whatever structure got built above — used to
# size the 'rings' placeholder rig and the camera regardless of scenario.
STRUCT_MAX_R = max(math.hypot(seg.x, seg.z) for seg in structure.segments)
STRUCT_MAX_H = max(seg.y_high for seg in structure.segments)

# ---- physics: luminaire rig, orchestrator computes illuminance ----
if SCENARIO == 'rings':
    # N_LIGHTS fixtures evenly spaced on a ring of radius LIGHT_RADIUS around
    # the structure, each aimed horizontally inward at the center in the
    # untilted state (before the shared tilt is applied) — synthetic
    # placeholder rig, kept for this test scenario.
    N_LIGHTS = 3
    LIGHT_RADIUS = 3.0  # m
    LIGHT_HEIGHT = COLUMN_HEIGHT / 2  # m

    def _luminaire_on_ring(i, n, radius, height):
        theta = 2 * math.pi * i / n
        x, z = radius * math.cos(theta), radius * math.sin(theta)
        aim_dir = (-math.cos(theta), 0.0, -math.sin(theta))
        return Luminaire(position=(x, height, z), aim_dir=aim_dir,
                          phi=PHI, theta_max_deg=THETA_MAX_DEG, d_offset=D_OFFSET)

    luminaires_rig = Luminaires(
        [_luminaire_on_ring(i, N_LIGHTS, LIGHT_RADIUS, LIGHT_HEIGHT) for i in range(N_LIGHTS)])
    BEAM_LEN = LIGHT_RADIUS - STRUCT_MAX_R  # used by build_light_visuals() below
    rig_rows = None  # no source file for this scenario — 'r' reload is a no-op
    rig_groups = None
else:  # 'spiral' — real fixture list, luminaires_rig.json
    # (light/.llm/CONTEXT.md "что дальше" #2 — resolves the placeholder rig).
    RIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'luminaires_rig.json')
    rig_data = load_rig(RIG_FILE, D_OFFSET)
    luminaires_rig = Luminaires(rig_data.luminaires)
    rig_rows = rig_data.rows
    rig_groups = rig_data.groups

orchestrator = Orchestrator(structure, luminaires_rig, occluder)
orchestrator.compute()

# CSV export, rewritten every recompute (initial load + every tilt) so the
# files on disk always match what's on screen.
SEGMENTS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'segments_output.csv')
LUMINAIRES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'luminaires_output.csv')
write_segments_csv(SEGMENTS_CSV, structure)
write_luminaires_csv(LUMINAIRES_CSV, luminaires_rig)

all_segments = structure.segments
# Fixed (absolute) color-scale bounds, captured once at this "best case"
# configuration — every fixture untilted, aimed straight at the ring — and
# never recomputed afterward. A relative min/max (recomputed every tilt)
# would always stretch the *current* frame's darkest/brightest segment to
# the full color range, making brightness across different tilts
# uncomparable (a "light" segment at 45 deg could be dimmer in absolute
# lux than a "dark" one at 0 deg). With a fixed scale, tilting the lights
# away from the structure now visibly darkens it instead of just
# reshuffling colors within whatever range happens to be lit right now.
e_min = 0.0
e_max = max(seg.E for seg in all_segments)

# ---- scene ----
app = Ursina()

# ursina's built-in FPS/entity/collider counters default to flush against
# the top-right corner — nudge them in a bit so they're not clipped/hard
# to read against the window edge.
for hud_text in (window.fps_counter, window.entity_counter, window.collider_counter):
    hud_text.x -= 0.05
    hud_text.y -= 0.02

color_manager = ColorManager()
input_manager = InputManager()
update_manager = UpdateManager()

# camera pulled back so the whole rig and the tallest part of the
# structure are in view on start
scene_setup = SceneSetup(
    init_position=(-8.0, STRUCT_MAX_H / 2 + 3.0, -8.0),
    init_rotation_x=20,
    init_rotation_y=35,
    color_manager=color_manager,
    input_manager=input_manager,
    update_manager=update_manager,
)
input_manager.register_scene_setup(scene_setup)
update_manager.register_scene_setup(scene_setup)

# ground floor + origin frame, same as player_zoom/main.py (for scale reference)
floor = Entity(
    model='quad',
    scale=40,
    rotation_x=90,
    color=color_manager.get_color('scene', 'floor'),
    texture='white_cube',
    texture_scale=(40, 40),
)
frame = Frame(color_manager=color_manager, origin_scale=0.05)
input_manager.register_frame(frame)

# structure + lights are centered on the world origin (frame gizmo sits
# inside the column ring) — no scene-shift offset.

# columns, one flat board entity per segment, colored by illuminance.
# collider='box' makes them pickable by mouse.hovered_entity (see update()).
# Cube's local +z ("forward") is oriented along the segment's own
# surface_normal via look_at() — sidesteps guessing a rotation_y sign by
# hand (a board is symmetric in width, so which way "right" ends up
# doesn't matter, only that "forward"/thickness lines up with the normal).
segment_entities = []
for seg in all_segments:
    t = (seg.E - e_min) / (e_max - e_min or 1)
    nx, ny, nz = seg.surface_normal
    entity = Entity(
        model='cube',
        scale=(BOARD_WIDTH, seg.length, BOARD_THICKNESS),
        position=(seg.x, seg.y_mid, seg.z),
        color=ramp_color(t),
        collider='box',
    )
    entity.look_at((seg.x + nx, seg.y_mid + ny, seg.z + nz))
    entity.segment = seg
    segment_entities.append(entity)

# light source markers (fixed) + aim beam / aperture gizmos (rebuilt on tilt
# and on 'r' rig reload) — all fixtures share the same marker color, since
# they move together under the shared tilt control, so there's nothing to
# tell apart by color. A billboarded index number floats above each marker
# so a fixture visible in the scene can be matched back to its row in
# luminaires_rig.json / its index in luminaires_output.csv.
MARKER_COLOR = color.yellow
MARKER_COLOR_DISABLED = color.gray  # fixture off (its own or its group's "enabled" is false)
LABEL_Y_OFFSET = 0.35  # m, above the marker sphere so the number doesn't overlap it
# Rule: yellow screen = the fixture's real (full) theta_max, blue screen =
# half of that same fixture's theta_max — always relative to its own angle,
# not a fixed 60/30 (fixtures can each have their own theta_max_deg now,
# see rig_io.py).
COLOR_MAIN = color.rgba32(255, 230, 120, 200)
COLOR_HALF = color.rgba32(120, 200, 255, 200)
COLOR_MAIN_DISABLED = color.rgba32(120, 120, 120, 120)
COLOR_HALF_DISABLED = color.rgba32(120, 120, 120, 80)

marker_entities = []
label_entities = []
luminaires_half = []
gizmos = []
light_world_positions = []


def build_light_visuals():
    """(Re)builds everything derived from luminaires_rig.all: position
    markers, index labels, the half-angle reference fixtures, and the aim/
    aperture gizmos. Called once at startup and again from reload_rig()
    after luminaires_rig.all has been replaced by a fresh JSON read."""
    global light_world_positions, beam_lens

    for e in marker_entities:
        destroy(e)
    marker_entities.clear()
    for t in label_entities:
        destroy(t)
    label_entities.clear()
    for g in gizmos:
        g.destroy()
    gizmos.clear()
    luminaires_half.clear()

    light_world_positions = [lum.position for lum in luminaires_rig.all]
    if SCENARIO == 'rings':
        beam_lens = [BEAM_LEN] * len(luminaires_rig.all)
    else:
        beam_lens = [math.hypot(x, z) for x, _, z in light_world_positions]

    for i, (lum, wp) in enumerate(zip(luminaires_rig.all, light_world_positions)):
        m_color = MARKER_COLOR if getattr(lum, 'enabled', True) else MARKER_COLOR_DISABLED
        marker_entities.append(Entity(model='sphere', scale=0.10, position=wp, color=m_color))
        label_entities.append(Text(text=str(i), parent=scene, position=(wp[0], wp[1] + LABEL_Y_OFFSET, wp[2]),
                                    scale=15, origin=(0, 0), billboard=True, color=m_color))

    # Half-angle reference screen (1m) for each fixture — same position/aim
    # as the fixture's real full-angle screen (0.25m), always at HALF of
    # that specific fixture's own theta_max_deg (not a fixed 30), to
    # visually judge whether its configured angle is really the intended
    # aperture. Does NOT change illuminance, visual reference only. Uses
    # each fixture's own phi (irrelevant to this gizmo's geometry, but
    # keeps it meaningful now that 'spiral' fixtures no longer share one
    # global PHI).
    for lum in luminaires_rig.all:
        luminaires_half.append(Luminaire(position=lum.position, aim_dir=lum.aim_dir, phi=lum.phi,
                                          theta_max_deg=lum.theta_max_deg / 2.0, d_offset=D_OFFSET))

    for lum, lum_half, wp, bl in zip(luminaires_rig.all, luminaires_half, light_world_positions, beam_lens):
        enabled = getattr(lum, 'enabled', True)
        c_main = COLOR_MAIN if enabled else COLOR_MAIN_DISABLED
        c_half = COLOR_HALF if enabled else COLOR_HALF_DISABLED
        gizmos.append(LuminaireGizmo(lum, lum_half, wp, c_main, c_half, bl))


TILT_STEP_DEG = 2.5
TILT_LIMIT_DEG = 90.0  # absolute limit per fixture, from horizontal — see Luminaires.tilt_all

build_light_visuals()


def rebuild_gizmos():
    for g in gizmos:
        g.rebuild()


def recompute_illuminance():
    # e_min/e_max are the fixed color-scale bounds set once above — not
    # recomputed here, so the scale stays absolute across tilts.
    orchestrator.compute()
    for entity in segment_entities:
        t = (entity.segment.E - e_min) / (e_max - e_min or 1)
        entity.color = ramp_color(t)


_PITCH_DISPLAY = COLUMN_PITCH if SCENARIO == 'rings' else SPIRAL_PITCH


def info_lines():
    phis = [lum.phi for lum in luminaires_rig.all]
    phi_str = f"{phis[0]:.0f}" if max(phis) - min(phis) < 1e-6 else f"{min(phis):.0f}-{max(phis):.0f}"
    tilts = [lum.current_tilt_deg() for lum in luminaires_rig.all]
    tilt_str = f"{tilts[0]:+.0f}" if max(tilts) - min(tilts) < 0.5 else f"{min(tilts):+.0f}..{max(tilts):+.0f}"
    angles = [lum.theta_max_deg for lum in luminaires_rig.all]
    angle_str = f"{angles[0]:.0f}" if max(angles) - min(angles) < 0.5 else f"{min(angles):.0f}-{max(angles):.0f}"
    n_on = sum(1 for lum in luminaires_rig.all if getattr(lum, 'enabled', True))
    return (
        f"Phi={phi_str} lm  theta_max={angle_str} deg (per fixture)  "
        f"screens: full angle@0.25m (yellow) + half angle@1m (blue, ref only)  "
        f"I0={luminaires_rig.all[0].i0:.1f} cd\n"
        f"scenario={SCENARIO}  pitch={_PITCH_DISPLAY} m  seg_len~{SEG_LEN} m  d_offset={D_OFFSET} m  tilt={tilt_str} deg\n"
        f"scale (fixed): {e_min:.1f}-{e_max:.1f} lux   "
        f"E now: {min(seg.E for seg in all_segments):.1f}-{max(seg.E for seg in all_segments):.1f} lux   "
        f"pieces={len(all_segments)}   luminaires={n_on}/{len(luminaires_rig.all)} on"
    )


def tilt(delta_deg):
    if not luminaires_rig.tilt_all(delta_deg, TILT_LIMIT_DEG):
        return
    for lum_half, lum in zip(luminaires_half, luminaires_rig.all):
        lum_half.set_aim_dir(lum.aim_dir)

    recompute_illuminance()
    rebuild_gizmos()
    write_segments_csv(SEGMENTS_CSV, structure)
    write_luminaires_csv(LUMINAIRES_CSV, luminaires_rig)
    if rig_rows is not None:
        # persist each fixture's current absolute tilt_deg, so a later 'r'
        # reload (or a manual look at the file) sees the same angle instead
        # of losing it back to whatever was last saved.
        sync_tilt_deg(rig_rows, luminaires_rig.all)
        write_rig(RIG_FILE, rig_rows, rig_groups)
    info_text.text = info_lines()


def reload_rig():
    """Re-reads luminaires_rig.json from disk and rebuilds everything that
    depends on it — lets the user hand-edit the file (positions, power,
    tilt...) and see it applied without restarting the whole app. No-op for
    'rings' (no source file). The color scale's e_max is recaptured against
    the freshly-read rig, same as at original startup."""
    global luminaires_rig, e_max, rig_groups
    if rig_rows is None:
        return
    rig_data = load_rig(RIG_FILE, D_OFFSET)
    luminaires_rig.all = rig_data.luminaires
    rig_rows[:] = rig_data.rows
    rig_groups = rig_data.groups

    build_light_visuals()
    rebuild_gizmos()  # build_light_visuals() only constructs LuminaireGizmo objects — .rebuild() actually draws their beam/aperture entities
    orchestrator.compute()
    e_max = max(seg.E for seg in all_segments)
    for entity in segment_entities:
        t = (entity.segment.E - e_min) / (e_max - e_min or 1)
        entity.color = ramp_color(t)
    write_segments_csv(SEGMENTS_CSV, structure)
    write_luminaires_csv(LUMINAIRES_CSV, luminaires_rig)
    info_text.text = info_lines()


rebuild_gizmos()

info_text = Text(
    info_lines(),
    position=(-0.75, 0.47), scale=1.1, background=True,
)

hover_text = Text('', position=(-0.75, 0.30), scale=1.2, background=True, color=color.white)

# keys 1/2 tilt every fixture down/up together, via InputManager's generic
# key-handler extension point (not a built-in InputManager binding).
input_manager.register_key_handler('1', lambda: tilt(-TILT_STEP_DEG))
input_manager.register_key_handler('2', lambda: tilt(TILT_STEP_DEG))
# r: reload luminaires_rig.json from disk (hand-edit the file, see it live).
input_manager.register_key_handler('r', reload_rig)


def update():
    update_manager.update_all(time.dt)

    hovered = mouse.hovered_entity
    if hovered is not None and hasattr(hovered, 'segment'):
        seg = hovered.segment
        hover_text.text = (
            f"segment: x={seg.x:.2f} m  y={seg.y_low:.2f}-{seg.y_high:.2f} m\n"
            f"E = {seg.E:.1f} lux"
        )
    else:
        hover_text.text = ''


def input(key):
    input_manager.handle_input(key)


if __name__ == '__main__':
    app.run()
