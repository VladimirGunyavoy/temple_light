"""Luminaire (light-source) photometric model — see ../docs/LUMINAIRE.md."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vectors import vec_sub, vec_norm, vec_scale, vec_dot, vec_cross, vec_rotate  # noqa: E402

PHI_DEFAULT = 5000.0
THETA_MAX_DEG_DEFAULT = 60.0
D_OFFSET_DEFAULT = 0.05
WORLD_UP = (0.0, 1.0, 0.0)


class Luminaire:
    """
    One spotlight: I(psi) = I0*cos(psi) inside a circular cone of half-angle
    theta_max, zero outside (../docs/LUMINAIRE.md §1/§4/§5). aim_dir points from the
    fixture toward the scene.

    I0 is calibrated so that integrating I(psi) over the actual beam cone
    (not the full hemisphere) recovers phi exactly: Phi =
    integral_0^theta_max I0*cos(psi) * 2*pi*sin(psi) dpsi = pi*I0*sin^2(theta_max),
    so I0 = phi / (pi * sin(theta_max)^2) — phi is the fixture's rated total
    output *within its beam angle*, not a bare-emitter hemisphere output that
    a hood then crops (../docs/LUMINAIRE.md §5). Narrowing theta_max
    concentrates the same phi into a smaller cone, so the center gets
    brighter — this is what lets each fixture carry its own arbitrary
    theta_max (rig_io.py's per-fixture `theta_max_deg` — the maximum
    deviation from center, i.e. a "30 deg" fixture lights a +/-30 deg cone,
    not a 30-deg-wide one) and have its angular intensity profile
    recalculated automatically. Reduces to the older phi/pi full-hemisphere
    formula exactly at theta_max=90 deg (sin^2(90)=1).

    Keeps a local (right, up) frame derived from aim_dir + world-up, used
    only for the gizmo helpers below (cutoff_edge_dirs / cutoff_corner_dirs
    / aperture_square_corners) — the photometric sample() itself only needs
    aim_dir (single circular cone, no box/axes involved).
    """

    def __init__(self, position, aim_dir, phi=PHI_DEFAULT,
                 theta_max_deg=THETA_MAX_DEG_DEFAULT, d_offset=D_OFFSET_DEFAULT):
        self.position = tuple(position)
        self.phi = phi
        self.theta_max_deg = theta_max_deg
        self.theta_max = math.radians(theta_max_deg)
        self.cos_theta_max = math.cos(self.theta_max)
        self.d_offset = d_offset
        # ../docs/LUMINAIRE.md §5 — I0 renormalized to the actual cone so
        # phi is conserved regardless of theta_max (see class docstring).
        self.i0 = phi / (math.pi * math.sin(self.theta_max) ** 2)

        self.set_aim_dir(aim_dir)
        # fixed "right" axis, computed once from the initial aim direction —
        # tilt_pitch() rotates around this constant axis, so repeated tilts
        # stay a pure up/down pitch instead of drifting into yaw/roll.
        self._right_axis = self.right

    def set_aim_dir(self, aim_dir):
        n = vec_norm(aim_dir)
        self.aim_dir = vec_scale(aim_dir, 1.0 / n)
        self.right = vec_norm_safe_cross(self.aim_dir, WORLD_UP)
        self.up = vec_cross(self.right, self.aim_dir)

    def tilt_pitch(self, delta_deg):
        """Tilt the aim direction up/down by delta_deg, rotating around the
        fixed right axis established at construction time."""
        angle = math.radians(delta_deg)
        new_aim = vec_rotate(self.aim_dir, self._right_axis, angle)
        n = vec_norm(new_aim)
        self.aim_dir = vec_scale(new_aim, 1.0 / n)
        self.right = self._right_axis
        self.up = vec_cross(self.right, self.aim_dir)

    def current_tilt_deg(self):
        """Absolute tilt from horizontal (positive = up), recovered
        directly from aim_dir's vertical component. Valid regardless of how
        many tilt_pitch() calls got aim_dir here (construction-time tilt,
        interactive keys, ...): every one of them is a pure rotation around
        the same fixed horizontal right axis starting from a horizontal
        reference, so aim_dir.y is always exactly sin(total tilt angle) —
        an absolute quantity, not something that needs separate bookkeeping
        of "how much was applied since when"."""
        return math.degrees(math.asin(max(-1.0, min(1.0, self.aim_dir[1]))))

    def sample(self, point, surface_normal):
        """Illuminance contribution of this luminaire at one point/surface."""
        d_vec = vec_sub(point, self.position)
        d = vec_norm(d_vec)
        if d < 1e-9:
            # degenerate: sample point coincides with the fixture itself
            # (e.g. a light placed exactly on a column) — no well-defined
            # direction, so contribute nothing rather than divide by zero.
            return dict(
                point=point, distance=0.0, cos_psi=0.0, in_cone=False,
                cos_incidence=0.0, intensity=0.0, illuminance=0.0,
            )
        n_hat = vec_scale(d_vec, 1.0 / d)

        cos_psi = vec_dot(n_hat, self.aim_dir)
        in_cone = cos_psi >= self.cos_theta_max

        incoming = vec_scale(n_hat, -1.0)  # from surface point back to the light
        cos_incidence = max(0.0, vec_dot(incoming, surface_normal))

        d_eff = d + self.d_offset
        intensity = self.i0 * cos_psi if in_cone else 0.0
        illuminance = intensity * cos_incidence / (d_eff ** 2) if in_cone else 0.0

        return dict(
            point=point, distance=d, cos_psi=cos_psi, in_cone=in_cone,
            cos_incidence=cos_incidence, intensity=intensity, illuminance=illuminance,
        )

    def _tangent_dir(self, theta_h, theta_v):
        """
        Direction for a rectangular-frustum cutoff (camera-FOV style),
        expressed in the luminaire's own (right, up, aim_dir) frame:
        d = normalize(right*tan(theta_h) + up*tan(theta_v) + aim_dir).
        This is the parametrization that keeps a square aperture actually
        looking square/symmetric under 90-degree rotation when viewed head
        -on along the aim axis — the earlier "latitude/longitude" version
        used for photometric integration (../docs/LUMINAIRE.md §3) does NOT have
        that property: its diagonal sits at ~63 deg azimuth instead of the
        expected 45 deg (caught by eye — looking at the fixture from
        behind, the corner rays visibly did not bisect the edge rays).
        """
        v = vec_add3(
            vec_scale(self.right, math.tan(theta_h)),
            vec_scale(self.up, math.tan(theta_v)),
            self.aim_dir,
        )
        n = vec_norm(v)
        return vec_scale(v, 1.0 / n)

    def cutoff_edge_dirs(self, length=1.0):
        """
        4 directions at the MIDPOINTS of the square aperture's edges
        (up/down/left/right) — each exactly theta_max off-axis along a
        single axis, the other axis at 0.
        """
        tm = self.theta_max
        local = {
            'up': self._tangent_dir(0.0, tm),
            'down': self._tangent_dir(0.0, -tm),
            'right': self._tangent_dir(tm, 0.0),
            'left': self._tangent_dir(-tm, 0.0),
        }
        return {k: tuple(x * length for x in v) for k, v in local.items()}

    def cutoff_corner_dirs(self, length=1.0):
        """
        4 diagonal directions of the square-cutoff aperture corners —
        each at +/-theta_max off-axis along BOTH the horizontal and the
        vertical direction at once, sitting exactly at 45 deg azimuth
        (halfway between the edge directions) when viewed along the aim
        axis. The true 3D angle from center at a corner is still larger
        than theta_max (cos(true angle) = 1/sqrt(1+2*tan^2(theta_max)),
        e.g. ~67.8 deg for theta_max=60 deg) — an inherent property of a
        square aperture, not an error.
        """
        tm = self.theta_max
        local = {
            'up_right': self._tangent_dir(tm, tm),
            'up_left': self._tangent_dir(-tm, tm),
            'down_right': self._tangent_dir(tm, -tm),
            'down_left': self._tangent_dir(-tm, -tm),
        }
        return {k: tuple(x * length for x in v) for k, v in local.items()}

    def aperture_square_corners(self, distance=1.0):
        """
        4 corners (relative to self.position) of the square cross-section
        of the aperture frustum at the given distance along aim_dir — a
        single flat "screen" outline. Corner order is tr, tl, bl, br (draw
        as a closed quad).
        """
        half = math.tan(self.theta_max) * distance
        center = vec_scale(self.aim_dir, distance)
        r, u = self.right, self.up
        return {
            'tr': vec_add3(center, vec_scale(r, half), vec_scale(u, half)),
            'tl': vec_add3(center, vec_scale(r, -half), vec_scale(u, half)),
            'bl': vec_add3(center, vec_scale(r, -half), vec_scale(u, -half)),
            'br': vec_add3(center, vec_scale(r, half), vec_scale(u, -half)),
        }


def vec_add3(a, b, c):
    return (a[0] + b[0] + c[0], a[1] + b[1] + c[1], a[2] + b[2] + c[2])


def vec_norm_safe_cross(aim_dir, world_up):
    """right = normalize(cross(aim_dir, world_up)); falls back to world X
    axis if aim_dir is (near) parallel to world_up (gimbal edge case)."""
    r = vec_cross(aim_dir, world_up)
    n = vec_norm(r)
    if n < 1e-6:
        return (1.0, 0.0, 0.0)
    return vec_scale(r, 1.0 / n)
