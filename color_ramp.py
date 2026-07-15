"""Sequential color ramp for illuminance visualization (ursina-dependent —
lives next to main.py, not in ./src, which stays framework-free).

Brightest/lightest color = highest value, darkest = lowest — the usual
sequential-heatmap convention (dark=high) reversed, per user preference:
brighter should look brighter (light/.llm/CONTEXT.md).
"""
import math

from ursina import color

# same sequential blue ramp used in the HTML heatmap (dataviz palette.md), reversed,
# with an extra near-black anchor appended so E=0 reads as dark/off rather than
# merely dark navy (user wants the zero end to look meaningfully darker), and
# the two palest entries dropped so E=e_max no longer reads as near-white
# under scene lighting (user wants the bright end capped too).
_HEX = [
    "9ec5f4", "86b6ef", "6da7ec", "5598e7",
    "3987e5", "2a78d6", "256abf", "1c5cab", "184f95", "104281", "0d366b",
    "040a14",
][::-1]
_RGB = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in _HEX]


def ramp_color(t):
    """t in [0, 1] -> ursina color; t=0 darkest, t=1 lightest."""
    t = max(0.0, min(1.0, t))
    pos = t * (len(_RGB) - 1)
    i0 = int(math.floor(pos))
    i1 = min(len(_RGB) - 1, i0 + 1)
    f = pos - i0
    c0, c1 = _RGB[i0], _RGB[i1]
    r = c0[0] + (c1[0] - c0[0]) * f
    g = c0[1] + (c1[1] - c0[1]) * f
    b = c0[2] + (c1[2] - c0[2]) * f
    return color.rgb32(r, g, b)
