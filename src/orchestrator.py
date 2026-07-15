"""Matches every segment of the structure against every luminaire in the
rig to compute illuminance — see ../docs/LUMINAIRE.md §6.

Also the place occlusion is wired in (light/.llm/CONTEXT.md "что дальше"
#3): occluder is a callable (origin, target) -> bool, e.g.
occlusion.ray_blocked_by_wall bound to a fixed wall (rings scenario, via
functools.partial) or spiral.ray_blocked_by_spiral (spiral scenario).

If occluder exposes a `.batch(origins, targets) -> bool array` (as
spiral.ray_blocked_by_spiral does), compute() uses it instead of calling
occluder per-ray through Segment.compute_illuminance: it collects every
sample point x luminaire pair that would otherwise contribute across the
WHOLE structure into one batch and checks occlusion for all of them in a
single vectorized call. Measured ~6x faster than the per-ray path at
realistic (tens of thousands of rays) scene sizes (light/.llm/CONTEXT.md) —
worth it since this will get called repeatedly by a future placement-search
optimizer, not just once per tilt keypress.
"""


class Orchestrator:
    def __init__(self, structure, luminaires, occluder=None):
        self.structure = structure
        self.luminaires = luminaires
        self.occluder = occluder

    def compute(self):
        batch_fn = getattr(self.occluder, 'batch', None) if self.occluder is not None else None
        if batch_fn is None:
            for seg in self.structure.segments:
                seg.compute_illuminance(self.luminaires.all, self.occluder)
            return
        self._compute_batched(batch_fn)

    def _compute_batched(self, batch_fn):
        segments = self.structure.segments
        luminaires = self.luminaires.all

        # first pass: plain photometry (cheap) for every sample point x
        # luminaire pair, everywhere in the structure at once — also
        # collects which of those pairs need an occlusion check (only the
        # ones that already sample non-zero; see Segment.compute_illuminance
        # for why an already-zero ray isn't worth an occlusion test).
        candidates = []   # sample dicts that might still get zeroed
        origins = []
        targets = []
        for seg in segments:
            detail = {}
            for name, p in seg.sample_points().items():
                samples = []
                for lum in luminaires:
                    if not getattr(lum, 'enabled', True):
                        continue
                    s = lum.sample(p, seg.surface_normal)
                    s['blocked'] = False
                    samples.append(s)
                    if s['illuminance'] > 0.0:
                        candidates.append(s)
                        origins.append(lum.position)
                        targets.append(p)
                detail[name] = samples
            seg.rays = detail

        # second pass: one vectorized occlusion check for every candidate
        # ray across the whole structure, instead of one Python call each.
        if candidates:
            blocked = batch_fn(origins, targets)
            for s, is_blocked in zip(candidates, blocked):
                if is_blocked:
                    s['intensity'] = 0.0
                    s['illuminance'] = 0.0
                    s['blocked'] = True

        # third pass: fold the (possibly now-zeroed) per-luminaire samples
        # back into each segment's E, same averaging as
        # Segment.compute_illuminance.
        for seg in segments:
            e_per_ray = {name: sum(s['illuminance'] for s in samples)
                         for name, samples in seg.rays.items()}
            seg.E = sum(e_per_ray.values()) / 3.0
