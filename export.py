"""CSV export of the current scenario state — framework-free (only needs
Structure/Luminaires objects, not ursina), so main.py can call it after
every recompute (e.g. on tilt) to keep the files in sync with what's on
screen.
"""
import csv


def write_segments_csv(path, structure):
    """One row per segment: which column, position, and its illuminance."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['column', 'segment', 'x_m', 'z_m', 'y_low_m', 'y_high_m',
                          'y_mid_m', 'length_m', 'normal_x', 'normal_z', 'E_lux'])
        for ci, col in enumerate(structure.columns):
            for si, seg in enumerate(col.segments):
                nx, _, nz = seg.surface_normal
                writer.writerow([ci, si, seg.x, seg.z, seg.y_low, seg.y_high,
                                  seg.y_mid, seg.length, nx, nz, seg.E])


def write_luminaires_csv(path, luminaires):
    """One row per fixture: position, aim direction, power, and each
    fixture's own absolute tilt from horizontal (Luminaire.current_tilt_deg,
    recovered from aim_dir — not a single shared value, since fixtures can
    each have their own base tilt from luminaires_rig.json)."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['index', 'group', 'enabled', 'x_m', 'y_m', 'z_m', 'aim_x', 'aim_y', 'aim_z',
                          'phi_lm', 'theta_max_deg', 'd_offset_m', 'i0_cd', 'tilt_deg'])
        for i, lum in enumerate(luminaires.all):
            x, y, z = lum.position
            ax, ay, az = lum.aim_dir
            writer.writerow([i, getattr(lum, 'group', ''), getattr(lum, 'enabled', True), x, y, z, ax, ay, az,
                              lum.phi, lum.theta_max_deg, lum.d_offset, lum.i0, lum.current_tilt_deg()])
