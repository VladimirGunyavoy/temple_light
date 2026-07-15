"""Structure holding all columns/segments — see ../docs/PIECES.md."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from column import Column  # noqa: E402
import spiral              # noqa: E402


class Structure:
    """All columns making up the construction under test."""

    def __init__(self, columns):
        self.columns = columns

    @property
    def segments(self):
        return [seg for col in self.columns for seg in col.segments]

    @classmethod
    def wall(cls, width, height, pitch, seg_len):
        """Synthetic flat-wall test scenario (main.py) — a
        row of columns along X centered on x=0 (spanning roughly
        [-width/2, width/2]), wall plane at Z=0. The real spiral layout
        from ../docs/GEOMETRY.md is not wired in yet (light/.llm/CONTEXT.md)."""
        n_cols = math.floor(width / pitch) + 1
        span = (n_cols - 1) * pitch
        columns = [
            Column(x=c * pitch - span / 2, z=0.0, height=height, seg_len=seg_len)
            for c in range(n_cols)
        ]
        return cls(columns)

    @classmethod
    def circle(cls, radius, pitch, height, seg_len):
        """Synthetic ring test scenario — columns spaced ~pitch apart around
        a circle of the given radius in the X-Z plane, centered on the
        origin. A step closer to the real spiral (../docs/GEOMETRY.md) than the
        flat wall, still synthetic (uniform radius/height, not the actual
        spiral curve). Each column's surface_normal points radially
        outward (away from center), since the light rig sits outside the
        ring — see ../docs/PIECES.md on why a single fixed normal (fine for
        the flat wall) doesn't work once columns face different ways."""
        n_cols = max(1, round(2 * math.pi * radius / pitch))
        columns = []
        for i in range(n_cols):
            theta = 2 * math.pi * i / n_cols
            x, z = radius * math.cos(theta), radius * math.sin(theta)
            normal = (math.cos(theta), 0.0, math.sin(theta))
            columns.append(Column(x=x, z=z, height=height, seg_len=seg_len, surface_normal=normal))
        return cls(columns)

    @classmethod
    def spiral(cls, seg_len, pitch=spiral.H_STEP):
        """The real construction — two mirrored Archimedean spirals of
        vertical columns (../docs/GEOMETRY.md §1/§3/§4), each column's height from
        the Lagrange height profile F (../docs/GEOMETRY.md §5): tall at the center,
        down to 0 at the outer edge. Column normal points radially outward
        from the construction's center (origin) — same convention as
        circle() (../docs/PIECES.md §1: "outward from the center of the
        construction", not a local per-spiral-curve normal). GeoGebra plan
        axes (X, Y) map to the engine's (x, z) (height Z maps to engine y,
        handled by Column/Segment separately — ../docs/GEOMETRY.md §8.4). pitch
        defaults to ../docs/GEOMETRY.md's real column spacing (spiral.H_STEP) —
        pass a wider value to space columns out for visual testing."""
        columns = []
        for x, z, height in spiral.column_positions_and_heights(h=pitch):
            r = math.hypot(x, z)
            normal = (x / r, 0.0, z / r) if r > 1e-9 else (1.0, 0.0, 0.0)
            columns.append(Column(x=x, z=z, height=height, seg_len=seg_len, surface_normal=normal))
        return cls(columns)
