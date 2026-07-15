"""Collection of Luminaire objects — see ../docs/LUMINAIRE.md."""


class Luminaires:
    """All luminaires in the scene, addressable by index (e.g. for
    per-fixture interactive tilt controls)."""

    def __init__(self, luminaires):
        self.all = list(luminaires)

    def tilt(self, index, delta_deg):
        self.all[index].tilt_pitch(delta_deg)

    def tilt_all(self, delta_deg, limit_deg):
        """Tilt every luminaire by delta_deg, clamping each fixture's
        resulting absolute tilt (Luminaire.current_tilt_deg) independently
        to [-limit_deg, limit_deg] — an absolute physical limit per
        fixture, not a shared budget relative to session/load start, so a
        fixture that's already close to the limit gets a smaller actual
        delta than the rest instead of overshooting past it. Each fixture
        still rotates around its own fixed right-axis (set at its own
        construction), so this stays a pure up/down pitch regardless of
        which way it's aimed horizontally. Returns True if anything moved."""
        changed = False
        for lum in self.all:
            current = lum.current_tilt_deg()
            new_angle = max(-limit_deg, min(limit_deg, current + delta_deg))
            applied = new_angle - current
            if abs(applied) > 1e-9:
                lum.tilt_pitch(applied)
                changed = True
        return changed
