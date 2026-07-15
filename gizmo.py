"""Ursina-side visuals for one luminaire: aim beam + aperture screens.

The geometry itself (aperture_square_corners) lives on Luminaire
(./src/luminaire.py, framework-free); this module only turns those corners
into ursina Entities and owns their create/destroy lifecycle, so main.py
doesn't have to.
"""
from ursina import Entity, Mesh, destroy


def line_entity(pos, start, end, thickness, col):
    """One straight-line-segment Entity from start to end (both relative
    to pos, ursina local-space convention)."""
    return Entity(model=Mesh(vertices=[start, end], mode='line', thickness=thickness),
                  position=pos, color=col)


def _draw_aperture_square(lum, light_world_pos, distance, col, out_entities):
    """Flat square outline ("screen") at the given distance, plus 4 rays
    from the light to each corner (frustum edges)."""
    corners = lum.aperture_square_corners(distance=distance)
    order = ['tr', 'tl', 'bl', 'br']
    for i in range(4):
        a, b = corners[order[i]], corners[order[(i + 1) % 4]]
        out_entities.append(line_entity(light_world_pos, a, b, thickness=2, col=col))
    for key in order:
        out_entities.append(
            line_entity(light_world_pos, (0, 0, 0), corners[key], thickness=2, col=col))


class LuminaireGizmo:
    """Owns the visual entities for one fixture: the aim beam line plus its
    main (full theta_max) and reference (half theta_max) aperture screens —
    `luminaire`/`luminaire_ref` are two separate Luminaire objects sharing
    the same position/aim, built with the fixture's real angle and half of
    it respectively (see main.py's build_light_visuals). Call rebuild()
    after the underlying luminaires' aim_dir changes (tilt)."""

    def __init__(self, luminaire, luminaire_ref, world_pos, color_main, color_ref,
                 beam_len, dist_main=0.25, dist_ref=1.0):
        self.luminaire = luminaire
        self.luminaire_ref = luminaire_ref
        self.world_pos = world_pos
        self.color_main = color_main
        self.color_ref = color_ref
        self.beam_len = beam_len
        self.dist_main = dist_main
        self.dist_ref = dist_ref
        self.entities = []

    def destroy(self):
        for e in self.entities:
            destroy(e)
        self.entities.clear()

    def rebuild(self):
        self.destroy()
        beam_end = tuple(c * self.beam_len for c in self.luminaire.aim_dir)
        self.entities.append(
            line_entity(self.world_pos, (0, 0, 0), beam_end, thickness=3, col=self.color_main))
        _draw_aperture_square(self.luminaire, self.world_pos, self.dist_main, self.color_main, self.entities)
        _draw_aperture_square(self.luminaire_ref, self.world_pos, self.dist_ref, self.color_ref, self.entities)
