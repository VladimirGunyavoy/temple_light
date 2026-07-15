"""Occlusion of light rays by a solid cylindrical wall — the "ignore the
gaps between boards, treat the ring as one continuous wall" simplification
(light/.llm/CONTEXT.md). A wall is the XZ circle of a column ring extruded
from y=0 up to the ring's column height (its top edge is the shadow-casting
edge — ../docs/PIECES.md).
"""


def ray_blocked_by_wall(origin, target, wall_radius, wall_height):
    """True if the straight ray from origin to target passes through the
    solid wall (circle of wall_radius in the XZ plane, extruded from y=0 to
    wall_height) at some point strictly between the two endpoints.

    Solves for where the ray's XZ projection crosses the circle (a quadratic
    in the line parameter t, up to two roots), then checks whether the
    crossing height falls inside the wall's solid band. A point sitting
    exactly on the wall (e.g. a sample point on that same ring) still works
    correctly: geometrically the only way a straight line from it can cross
    its own circle again strictly between the endpoints is if it first
    passes back through the disk interior, which is exactly the case where
    that point's own far side is legitimately self-shadowed.
    """
    ox, oy, oz = origin
    tx, ty, tz = target
    dx, dz = tx - ox, tz - oz
    a = dx * dx + dz * dz
    if a < 1e-12:
        return False
    b = 2 * (ox * dx + oz * dz)
    c = ox * ox + oz * oz - wall_radius * wall_radius
    disc = b * b - 4 * a * c
    if disc < 0:
        return False
    sqrt_disc = disc ** 0.5
    for t in ((-b - sqrt_disc) / (2 * a), (-b + sqrt_disc) / (2 * a)):
        if 1e-6 < t < 1 - 1e-6:
            y = oy + t * (ty - oy)
            if 0.0 <= y <= wall_height:
                return True
    return False
