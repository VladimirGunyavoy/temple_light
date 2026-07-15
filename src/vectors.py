"""Small 3D vector helpers shared by the light-simulation classes."""
import math


def vec_sub(a, b):
    """a - b, componentwise."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec_norm(v):
    """Euclidean length of v."""
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def vec_scale(v, s):
    """v scaled by scalar s."""
    return (v[0] * s, v[1] * s, v[2] * s)


def vec_dot(a, b):
    """Dot product a . b."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec_add(a, b):
    """a + b, componentwise."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec_cross(a, b):
    """Cross product a x b."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vec_rotate(v, axis, angle_rad):
    """Rotate vector v by angle_rad (radians) around a unit vector axis
    (Rodrigues' rotation formula)."""
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    term1 = vec_scale(v, cos_a)
    term2 = vec_scale(vec_cross(axis, v), sin_a)
    term3 = vec_scale(axis, vec_dot(axis, v) * (1 - cos_a))
    return vec_add(vec_add(term1, term2), term3)
