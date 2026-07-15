"""A vertical stack of Segments standing at one plan position — see ../docs/PIECES.md."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment import Segment  # noqa: E402


class Column:
    """A vertical stack of Segments standing at plan position (x, z)."""

    def __init__(self, x, z, height, seg_len, surface_normal=(0.0, 0.0, 1.0)):
        self.x = x
        self.z = z
        self.height = height
        m = max(1, math.ceil(height / seg_len)) if height > 0 else 0
        actual_len = height / m if m else 0.0
        self.segments = [
            Segment(x, z, j * actual_len, (j + 1) * actual_len, surface_normal)
            for j in range(m)
        ]

    def compute_illuminance(self, luminaires, occluder=None):
        for seg in self.segments:
            seg.compute_illuminance(luminaires, occluder)
