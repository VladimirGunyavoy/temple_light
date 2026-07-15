from ursina import Entity
import numpy as np
from typing import Any

class Scalable(Entity):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.real_position: np.ndarray = np.array(self.position)
        self.real_scale: np.ndarray = np.array(self.scale)

    def apply_transform(self, a: float, b: np.ndarray, **kwargs: Any) -> None:
        """
        Apply zoom transformations.

        Args:
            a: Scaling coefficient
            b: Translation vector
            **kwargs: Ignored (kept for compatibility)
        """
        self.position = self.real_position * a + b
        self.scale = self.real_scale * a

    def __str__(self) -> str:
        return f'{self.position}'

    def __repr__(self) -> str:
        return f'{self.position}'


class ScalableFloor(Scalable):
    """Floor object that can be scaled with zoom."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)



