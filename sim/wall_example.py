"""
Simple validation example: flat wall of columns lit by one spotlight.

Geometry/photometry per ../docs/GEOMETRY.md, ../docs/PIECES.md, ../docs/LUMINAIRE.md.
Local axes for this script: X = width (wall), Y = height (up), Z = depth
(wall plane at Z=0, light in front at Z=LIGHT_DISTANCE).

Core classes (Luminaire / Segment / Column) live in ../src/ and are shared
with main.py — single source of truth for the formulas. More luminaires
can be added later; Segment.compute_illuminance already sums contributions
from a list of luminaires (LUMINAIRE.md §6).

For each segment of each column, three sample rays are cast (to the
segment's bottom, middle and top point) so the same per-ray machinery
can later support partial-occlusion shadow tests. Each ray stores its
geometry, cone-cutoff result, incidence cosine and illuminance; the
segment's reported illuminance is the mean of the three rays.
"""
import csv
import json
import math
import os
import sys

LIGHT_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, LIGHT_SRC_DIR)
from luminaire import Luminaire  # noqa: E402
from column import Column        # noqa: E402

# ---- parameters (see GEOMETRY.md / PIECES.md / LUMINAIRE.md) ----
WALL_WIDTH = 2.0        # m
WALL_HEIGHT = 2.0       # m
COLUMN_PITCH = 0.17     # m, h from GEOMETRY.md (confirmed real column spacing)
SEG_LEN = 0.10          # m, target segment length from PIECES.md
R_PILLAR = 0.05         # m, placeholder ("on the eye" per PIECES.md, not finalized)

PHI = 5000.0            # lm, luminous flux
THETA_MAX_DEG = 60.0    # half-angle of beam cone
D_OFFSET = 0.05         # m, source offset from front glass

LIGHT_DISTANCE = 2.0    # m, perpendicular distance from wall plane


def build_wall_columns(width, height, pitch, seg_len):
    """A single row of columns along X (z=0.0), pitch apart, from x=0 to
    roughly x=width."""
    n_cols = math.floor(width / pitch) + 1
    return [Column(x=c * pitch, z=0.0, height=height, seg_len=seg_len) for c in range(n_cols)]


def main():
    """Build the wall, light it with one spotlight, write
    wall_example_output.csv (one row per ray) and wall_example_viz.json
    (heatmap grid + per-ray detail for an offline viewer)."""
    columns = build_wall_columns(WALL_WIDTH, WALL_HEIGHT, COLUMN_PITCH, SEG_LEN)
    luminaire = Luminaire(
        position=(WALL_WIDTH / 2, WALL_HEIGHT / 2, LIGHT_DISTANCE),
        aim_dir=(0.0, 0.0, -1.0),
        phi=PHI, theta_max_deg=THETA_MAX_DEG, d_offset=D_OFFSET,
    )
    for col in columns:
        col.compute_illuminance([luminaire])

    rows = []
    for ci, col in enumerate(columns):
        for si, seg in enumerate(col.segments):
            row = dict(
                column_index=ci, segment_index=si,
                x=seg.x, y_low=seg.y_low, y_high=seg.y_high, y_mid=seg.y_mid,
                r_pillar=R_PILLAR, E_final_lux=seg.E,
            )
            for name in ('bottom', 'mid', 'top'):
                r = seg.rays[name][0]  # single luminaire for now
                prefix = f"ray_{name}_"
                row[prefix + "px"], row[prefix + "py"], row[prefix + "pz"] = r["point"]
                row[prefix + "distance_m"] = r["distance"]
                row[prefix + "cos_psi"] = r["cos_psi"]
                row[prefix + "in_cone"] = r["in_cone"]
                row[prefix + "cos_incidence"] = r["cos_incidence"]
                row[prefix + "intensity_cd"] = r["intensity"]
                row[prefix + "illuminance_lux"] = r["illuminance"]
            rows.append(row)

    out_csv = "wall_example_output.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # JSON for the visualization: heatmap grid + full per-ray detail for the hover inspector
    def ray_summary(r, name):
        p = "ray_" + name + "_"
        return dict(
            p=[round(r[p + "px"], 3), round(r[p + "py"], 3), round(r[p + "pz"], 3)],
            d=round(r[p + "distance_m"], 4),
            cos_psi=round(r[p + "cos_psi"], 4),
            in_cone=r[p + "in_cone"],
            cos_inc=round(r[p + "cos_incidence"], 4),
            I=round(r[p + "intensity_cd"], 2),
            E=round(r[p + "illuminance_lux"], 4),
        )

    viz_rows = [
        dict(
            col=r["column_index"], seg=r["segment_index"],
            x=round(r["x"], 4), y_low=round(r["y_low"], 4), y_high=round(r["y_high"], 4),
            E=round(r["E_final_lux"], 4),
            rays=dict(
                bottom=ray_summary(r, "bottom"),
                mid=ray_summary(r, "mid"),
                top=ray_summary(r, "top"),
            ),
        )
        for r in rows
    ]
    meta = dict(
        wall_width=WALL_WIDTH, wall_height=WALL_HEIGHT,
        column_pitch=COLUMN_PITCH, seg_len=columns[0].segments[0].length, r_pillar=R_PILLAR,
        phi=PHI, theta_max_deg=THETA_MAX_DEG, d_offset=D_OFFSET,
        light_distance=LIGHT_DISTANCE, i0=luminaire.i0,
        light_pos=luminaire.position, n_cols=len(columns), n_segs=len(columns[0].segments),
        e_min=min(r["E"] for r in viz_rows), e_max=max(r["E"] for r in viz_rows),
    )
    with open("wall_example_viz.json", "w", encoding="utf-8") as f:
        json.dump(dict(meta=meta, rows=viz_rows), f, ensure_ascii=False)

    print(f"I0 = {luminaire.i0:.2f} cd")
    print(f"columns = {len(columns)}, segments/column = {len(columns[0].segments)}, total pieces = {len(rows)}")
    print(f"E range: {meta['e_min']:.2f} .. {meta['e_max']:.2f} lux")
    print(f"wrote {out_csv} and wall_example_viz.json")


if __name__ == "__main__":
    main()
