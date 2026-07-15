"""One vertical slice of a column — see ../docs/PIECES.md."""


class Segment:
    """One vertical slice of a column. Illuminance is sampled at its bottom,
    middle and top points and averaged (../docs/PIECES.md §3/§4)."""

    def __init__(self, x, z, y_low, y_high, surface_normal=(0.0, 0.0, 1.0)):
        self.x = x
        self.z = z
        self.y_low = y_low
        self.y_high = y_high
        self.y_mid = (y_low + y_high) / 2
        self.surface_normal = surface_normal
        self.rays = {}   # name -> list of per-luminaire Luminaire.sample() results
        self.E = 0.0

    @property
    def length(self):
        return self.y_high - self.y_low

    def sample_points(self):
        return {
            'bottom': (self.x, self.y_low, self.z),
            'mid': (self.x, self.y_mid, self.z),
            'top': (self.x, self.y_high, self.z),
        }

    def compute_illuminance(self, luminaires, occluder=None):
        """occluder, if given, is a callable (origin, target) -> bool
        deciding whether a straight ray between those two 3D points is
        blocked by the structure (light/.llm/CONTEXT.md) — e.g.
        occlusion.ray_blocked_by_wall bound to a fixed wall (rings
        scenario) or spiral.ray_blocked_by_spiral (spiral scenario).

        Checked only for rays that already sample non-zero (in-cone,
        correctly facing) — occlusion tests can be expensive (the spiral
        one solves for line/curve intersections), so there's no point
        running one on a ray that's already zero for other reasons."""
        e_per_ray = {}
        detail = {}
        for name, p in self.sample_points().items():
            samples = []
            for lum in luminaires:
                if not getattr(lum, 'enabled', True):
                    continue
                s = lum.sample(p, self.surface_normal)
                if s['illuminance'] > 0.0 and occluder is not None and occluder(lum.position, p):
                    s['intensity'] = 0.0
                    s['illuminance'] = 0.0
                    s['blocked'] = True
                else:
                    s['blocked'] = False
                samples.append(s)
            e_per_ray[name] = sum(s['illuminance'] for s in samples)
            detail[name] = samples
        self.rays = detail
        self.E = sum(e_per_ray.values()) / 3.0
        return self.E
