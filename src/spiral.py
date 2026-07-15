"""Real construction plan geometry — two mirrored Archimedean spirals of
column plan positions, plus the Lagrange column-height profile, see
../docs/GEOMETRY.md. Used by Structure.spiral() to build the actual
construction instead of the synthetic test rings.

Pure math, no ursina dependency — but DOES depend on numpy (unlike the
other src/ modules), for ray_blocked_by_spiral_batch: occlusion is meant to
be called for every (segment sample point x luminaire) pair, and will get
called many more times once there's a placement-search optimizer running
this repeatedly, so it's worth batching with real array math instead of a
per-ray Python/math.* loop.
"""
import math

import numpy as np

# ../docs/GEOMETRY.md §2
A = 0.32                              # Archimedean spiral coefficient, R = a*phi
H_STEP = 0.17                         # m, Euler integration step = real column pitch (§8.6)
L = 79                                # controls total unrolled spiral length (independent of H_STEP, §3)
PHI0 = (1.0 / 3.5) * 2 * math.pi      # initial angle = center of the construction
N = math.floor(A * L / H_STEP)        # 148 -> 149 plan points per spiral, n = 0..N

# ../docs/GEOMETRY.md §5 — column-height profile control points (Lagrange, degree 5)
_X0 = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
_Y0 = [0.0, 0.1, 0.167, 0.255, 0.404, 1.0]


def lagrange_height(x):
    """F(x) — degree-5 Lagrange interpolation through the 6 control points
    above, scaled by 9 m. F(0)=0 m (outer edge), F(1)=9 m (center) fall out
    of the interpolation itself (no special-casing needed — all 6 knots are
    distinct, so the standard product formula never divides by zero, and
    interpolation reproduces the control values exactly at the knots)."""
    total = 0.0
    for i, (xi, yi) in enumerate(zip(_X0, _Y0)):
        li = 1.0
        for j, xj in enumerate(_X0):
            if j != i:
                li *= (x - xj) / (xi - xj)
        total += yi * li
    return 9.0 * total


def plan_points(a=A, h=H_STEP, phi0=PHI0, n_steps=None):
    """Euler-integrated Archimedean spiral plan points S(n) = (X(n), Y(n))
    for n = 0..n_steps, arc-length-uniform step h (../docs/GEOMETRY.md §3).
    n_steps defaults to floor(a*L/h) — the total unrolled length a*L is
    fixed (§3), so changing h changes how many columns fit along it."""
    if n_steps is None:
        n_steps = math.floor(a * L / h)
    phi = phi0
    R = a * phi
    points = [(-R * math.cos(phi), R * math.sin(phi))]
    for _ in range(n_steps):
        f_t = 1.0 / math.sqrt(a * a + R * R)
        phi += h * f_t
        R = a * phi
        points.append((-R * math.cos(phi), R * math.sin(phi)))
    return points


def _spiral_xy(phi, mirror=False, a=A):
    x = -a * phi * math.cos(phi)
    y = a * phi * math.sin(phi)
    return (-x, -y) if mirror else (x, y)


def _spiral_dxy(phi, mirror=False, a=A):
    """d/dphi of _spiral_xy — needed for Newton's method below."""
    dx = -a * math.cos(phi) + a * phi * math.sin(phi)
    dy = a * math.sin(phi) + a * phi * math.cos(phi)
    return (-dx, -dy) if mirror else (dx, dy)


def _s_of_phi(phi, a=A):
    """Arc length from phi=0 to phi (antiderivative of ds/dphi = a*sqrt(1+phi^2),
    ../docs/GEOMETRY.md §3's ds/dt=v0 relation integrated in phi instead of t)."""
    return a * (0.5 * phi * math.sqrt(1 + phi * phi) + 0.5 * math.asinh(phi))


_S0 = _s_of_phi(PHI0)
_TOTAL_LENGTH = A * L  # ../docs/GEOMETRY.md §3 — fixed, independent of column pitch h


def _solve_phi_max():
    """phi where the arc length from phi0 reaches the fixed total length
    a*L (../docs/GEOMETRY.md §3), via Newton's method (ds/dphi is smooth and
    monotonic, so this converges quickly from a decent initial guess)."""
    phi = PHI0 + _TOTAL_LENGTH / math.sqrt(A * A + (A * PHI0) ** 2)
    for _ in range(50):
        f = _s_of_phi(phi) - _S0 - _TOTAL_LENGTH
        fp = A * math.sqrt(1 + phi * phi)
        new_phi = phi - f / fp
        if abs(new_phi - phi) < 1e-13:
            return new_phi
        phi = new_phi
    return phi


PHI_MAX = _solve_phi_max()


def continuous_height(phi):
    """Height of the continuous solid "ribbon" wall at parameter phi — the
    same Lagrange height profile as the discrete columns (lagrange_height),
    but evaluated at the exact continuous arc-length fraction instead of a
    discrete k/N. Deliberately independent of column pitch h (§3: the total
    unrolled length a*L doesn't depend on h) — the occlusion silhouette is a
    property of the curve's shape, not of how densely we sample columns
    along it. Matches the discrete H(k) at real column positions to within
    ~0.06 m (out of up to 9 m) — the residual is accumulated Euler
    discretization error in the real column placement vs this exact
    analytic profile, consistent with the existing "ignore board gaps,
    treat as one continuous wall" simplification (light/.llm/CONTEXT.md)."""
    u = 1.0 - (_s_of_phi(phi) - _S0) / _TOTAL_LENGTH
    u = max(0.0, min(1.0, u))
    return lagrange_height(u)


# Coarse phi grid used to bracket roots before Newton refinement — fixed
# (doesn't depend on the ray), so the grid's spiral points are precomputed
# once here instead of recomputing sin/cos on every call. Only the points
# are cached (not derivatives) — Newton refinement moves phi off the grid,
# so hprime() still needs a fresh _spiral_dxy() at whatever phi it lands on.
# n=10 is the validated minimum (sim/spiral_line_intersection.ipynb):
# 6-7 already starts silently missing real crossings (the curve does ~1.7
# turns, so a coarser grid can straddle two sign changes in one bracket).
_COARSE_N = 10
_COARSE_STEP = (PHI_MAX - PHI0) / (_COARSE_N - 1)
_COARSE_PHIS = [PHI0 + i * _COARSE_STEP for i in range(_COARSE_N)]
_COARSE_TABLE = {
    mirror: [_spiral_xy(p, mirror) for p in _COARSE_PHIS]
    for mirror in (False, True)
}

# A target that sits exactly ON the spiral curve at one of the coarse grid
# points (e.g. a column at k=0, exactly at phi=PHI0 — very much a real
# case, it's the first column of the spiral) makes that grid point's H
# mathematically exactly zero. Whether it actually lands on 0.0 or a
# +-1e-16 float-noise neighbor is unstable and depends on the reduction
# order of whatever arithmetic computed it (observed: scalar math.cos/sin
# gives exactly 0.0, but points @ n.T in the batched path can give -1e-16
# depending on which OTHER rays share the batch — same ray, different
# answer, purely a floating-point artifact). Snapping anything this small
# to exactly 0.0 before the sign-change test avoids manufacturing a
# spurious bracket (and spurious Newton root) out of that noise.
_H_ZERO_EPS = 1e-9


def _line_spiral_roots(p1, p2, mirror=False, newton_iters=30, tol=1e-10):
    """phi values where the INFINITE line through 2D points p1, p2 crosses
    the spiral curve (or its S2 mirror) — coarse-sample the signed distance
    from spiral points to the line using the precomputed grid above,
    bracket sign changes, refine each with Newton's method using the
    analytic derivative (verified in sim/spiral_line_intersection.ipynb).
    Returns (phi, t) pairs, t being the line parameter (p1 -> p2) of the
    crossing — NOT clamped to [0,1], the caller decides what counts as "on
    the segment"."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    dd = dx * dx + dy * dy
    if dd < 1e-12:
        return []
    nx, ny = -dy, dx
    nlen = math.sqrt(nx * nx + ny * ny)
    nx, ny = nx / nlen, ny / nlen

    def h(phi):
        sx, sy = _spiral_xy(phi, mirror)
        return (sx - p1[0]) * nx + (sy - p1[1]) * ny

    def hprime(phi):
        sdx, sdy = _spiral_dxy(phi, mirror)
        return sdx * nx + sdy * ny

    points = _COARSE_TABLE[mirror]
    hvals = [(sx - p1[0]) * nx + (sy - p1[1]) * ny for sx, sy in points]
    hvals = [0.0 if abs(v) < _H_ZERO_EPS else v for v in hvals]

    roots = []
    for i in range(_COARSE_N - 1):
        a_, b_ = hvals[i], hvals[i + 1]
        if a_ == 0.0:
            roots.append(_COARSE_PHIS[i])
            continue
        if a_ * b_ < 0:
            phi = 0.5 * (_COARSE_PHIS[i] + _COARSE_PHIS[i + 1])
            for _ in range(newton_iters):
                hv = h(phi)
                if abs(hv) < tol:
                    break
                hp = hprime(phi)
                if hp == 0:
                    break
                phi = phi - hv / hp
            # h is periodic-ish (sin/cos of phi), so a bad step can send
            # Newton to a real zero of h that's way outside [PHI0, PHI_MAX]
            # — a mathematically valid root of the *unbounded* curve, but
            # not a point on the actual (bounded) spiral, so it isn't a
            # real intersection. Discard it rather than let a garbage phi
            # produce a bogus continuous_height() / t downstream.
            if PHI0 - 1e-6 <= phi <= PHI_MAX + 1e-6:
                roots.append(phi)

    # roots come from disjoint, increasing coarse-grid brackets, so they're
    # already ~sorted — only need to compare each new one to the last kept
    # one instead of scanning the whole list.
    dedup = []
    for r in roots:
        if not dedup or r - dedup[-1] > 1e-6:
            dedup.append(r)

    out = []
    for r in dedup:
        sx, sy = _spiral_xy(r, mirror)
        t = ((sx - p1[0]) * dx + (sy - p1[1]) * dy) / dd
        out.append((r, t))
    return out


def ray_blocked_by_spiral(origin, target):
    """True if the straight ray from origin to target (3D points) is
    blocked by the construction, treated as a continuous solid "ribbon"
    wall along both mirrored spiral curves (board gaps ignored, same
    simplification as the ring test's ray_blocked_by_wall). Finds where
    the ray's XZ projection crosses either spiral curve, then checks
    whether the crossing height falls under that point's continuous_height.
    Call it only for rays that would otherwise contribute (see
    Segment.compute_illuminance, which checks in_cone first)."""
    ox, oy, oz = origin
    tx, ty, tz = target
    p1, p2 = (ox, oz), (tx, tz)
    for mirror in (False, True):
        for phi, t in _line_spiral_roots(p1, p2, mirror=mirror):
            if 1e-6 < t < 1 - 1e-6:
                y = oy + t * (ty - oy)
                if 0.0 <= y <= continuous_height(phi):
                    return True
    return False


def _spiral_xy_np(phi, mirror, a=A):
    x = -a * phi * np.cos(phi)
    y = a * phi * np.sin(phi)
    return (-x, -y) if mirror else (x, y)


def _spiral_dxy_np(phi, mirror, a=A):
    dx = -a * np.cos(phi) + a * phi * np.sin(phi)
    dy = a * np.sin(phi) + a * phi * np.cos(phi)
    return (-dx, -dy) if mirror else (dx, dy)


def _s_of_phi_np(phi, a=A):
    return a * (0.5 * phi * np.sqrt(1 + phi * phi) + 0.5 * np.arcsinh(phi))


def _continuous_height_np(phi):
    u = 1.0 - (_s_of_phi_np(phi) - _S0) / _TOTAL_LENGTH
    u = np.clip(u, 0.0, 1.0)
    return lagrange_height(u)  # pure +-*/ on _X0/_Y0 floats -> works elementwise on ndarray


_COARSE_XY_NP = {mirror: np.array(_COARSE_TABLE[mirror]) for mirror in (False, True)}  # (N,2)
_COARSE_MIDS_NP = 0.5 * (np.array(_COARSE_PHIS[:-1]) + np.array(_COARSE_PHIS[1:]))     # (N-1,)


def ray_blocked_by_spiral_batch(origins, targets, newton_iters=12):
    """Vectorized ray_blocked_by_spiral for many (origin, target) pairs at
    once — origins/targets are (M,3) arrays, returns an (M,) bool array.

    Same algorithm as the scalar version, but restructured to avoid two
    numpy pitfalls: (1) evaluating the coarse grid stays a single matmul
    against the whole batch (that part is embarrassingly parallel — the
    grid doesn't depend on the ray); (2) Newton refinement is only run on
    the actual bracketed candidates (np.nonzero(signs)), NOT on all 9
    grid-slots x M rays — early benchmarking found that naively running
    Newton over every slot (most of which aren't a real bracket for a
    given ray) made the "vectorized" version no faster than the scalar
    loop, since it wastes ~4-5x the arithmetic vs. the scalar version's
    "only touch real brackets" behavior. Compacting to just the real
    brackets via boolean indexing keeps that same sparsity while still
    getting numpy's speed on the part that *is* dense work — ~6x faster
    than the scalar loop at realistic (tens of thousands of rays) batch
    sizes (measured, not just asymptotic).
    """
    origins = np.asarray(origins, dtype=float)
    targets = np.asarray(targets, dtype=float)
    M = origins.shape[0]
    p1 = origins[:, [0, 2]]
    p2 = targets[:, [0, 2]]
    oy = origins[:, 1]
    ty = targets[:, 1]
    d = p2 - p1
    dd = np.sum(d * d, axis=1)
    dd_safe = np.where(dd < 1e-12, 1.0, dd)
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    nlen = np.linalg.norm(nrm, axis=1)
    nlen_safe = np.where(nlen < 1e-12, 1.0, nlen)
    n = nrm / nlen_safe[:, None]

    blocked = np.zeros(M, dtype=bool)

    for mirror in (False, True):
        points = _COARSE_XY_NP[mirror]                                   # (_COARSE_N, 2)
        H = points @ n.T - np.sum(p1 * n, axis=1)[None, :]               # (_COARSE_N, M)
        H = np.where(np.abs(H) < _H_ZERO_EPS, 0.0, H)                    # see _H_ZERO_EPS
        signs = H[:-1, :] * H[1:, :] < 0                                 # (_COARSE_N-1, M)

        rows, cols = np.nonzero(signs)   # only the real brackets, flattened
        if rows.size == 0:
            continue

        phi = _COARSE_MIDS_NP[rows].copy()
        p1x, p1y = p1[cols, 0], p1[cols, 1]
        nx, ny = n[cols, 0], n[cols, 1]
        dxc, dyc = d[cols, 0], d[cols, 1]
        ddc = dd_safe[cols]
        oyc, tyc = oy[cols], ty[cols]

        for _ in range(newton_iters):
            sx, sy = _spiral_xy_np(phi, mirror)
            hv = (sx - p1x) * nx + (sy - p1y) * ny
            sdx, sdy = _spiral_dxy_np(phi, mirror)
            hp = sdx * nx + sdy * ny
            hp_safe = np.where(np.abs(hp) < 1e-14, 1.0, hp)
            phi = phi - np.where(np.abs(hp) < 1e-14, 0.0, hv / hp_safe)

        sx, sy = _spiral_xy_np(phi, mirror)
        t = ((sx - p1x) * dxc + (sy - p1y) * dyc) / ddc
        y_cross = oyc + t * (tyc - oyc)
        h_cross = _continuous_height_np(phi)

        # same out-of-domain guard as the scalar path (see
        # _line_spiral_roots) — Newton can wander phi outside
        # [PHI0, PHI_MAX] for a bad bracket, which isn't a real point on
        # the actual (bounded) spiral.
        in_domain = (phi >= PHI0 - 1e-6) & (phi <= PHI_MAX + 1e-6)
        valid = in_domain & (t > 1e-6) & (t < 1 - 1e-6) & (y_cross >= 0.0) & (y_cross <= h_cross)
        blocked[cols[valid]] = True

    return blocked


ray_blocked_by_spiral.batch = ray_blocked_by_spiral_batch


def column_at_s(s, mirror=False):
    """Plan position (x, z) and max mountable height at fractional
    parameter s in [0, 1] — s=0 is phi0 (tall center end), s=1 is phi_max
    (short outer end). NOTE despite the name, s is linear in the angular
    parameter phi (phi = phi0 + s*(phi_max - phi0)), NOT in true arc
    length along the curve — ds/dphi grows with phi for an Archimedean
    spiral, so equal steps in s cover more physical distance out near the
    wide outer turns than near the tightly-wound center (see
    ../docs/RIG.md's "Mechanics: what s_pct actually parametrizes" for the
    numbers). continuous_height(phi) still converts through the TRUE
    arc-length fraction internally, so the returned height is exact
    regardless of that nonlinearity — it's specifically the spacing of s
    itself that isn't arc-length-uniform. Treats the spiral curve itself
    as a "virtual column" at any such point via continuous_height
    (previously used only for occlusion, light/.llm/CONTEXT.md) — used to
    mount a luminaire on the construction at an arbitrary point along it
    without snapping to one of the discrete real columns
    (../docs/GEOMETRY.md's actual column pitch h=0.17 m is a separate,
    finer-grained concept)."""
    s = max(0.0, min(1.0, s))
    phi = PHI0 + s * (PHI_MAX - PHI0)
    x, z = _spiral_xy(phi, mirror=mirror)
    return x, z, continuous_height(phi)


def column_positions_and_heights(h=H_STEP):
    """(X, Y, height) for every column of BOTH mirrored spirals S1(k)/S2(k)
    (../docs/GEOMETRY.md §4/§6) — plan position (GeoGebra XY, not yet mapped to the
    engine's axes) plus that column's height H(k). h is the column pitch
    (Euler step) — pass a different value to space columns out for testing
    (fewer, wider-spaced columns) without touching the real ../docs/GEOMETRY.md
    default."""
    n_steps = math.floor(A * L / h)
    plan = plan_points(h=h, n_steps=n_steps)
    out = []
    for k, (x, y) in enumerate(plan):
        u = 1.0 - k / n_steps
        height = lagrange_height(u)
        out.append((x, y, height))
        out.append((-x, -y, height))
    return out
