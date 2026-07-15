from ursina import (
    Entity, DirectionalLight, AmbientLight, color, window, mouse, held_keys, application, Light
)
from ursina.prefabs.first_person_controller import FirstPersonController # Import FirstPersonController
import numpy as np
import time
from typing import Optional, List, Tuple, TYPE_CHECKING

from .scalable import Scalable
from .color_manager import ColorManager

if TYPE_CHECKING:
    from .input_manager import InputManager
    from .update_manager import UpdateManager

# Class for setting up scene, camera and lighting
class SceneSetup:
    def __init__(self,
                 init_position: Tuple[float, float, float] = (1.5, -1, -2),
                 init_rotation_x: float = 21,
                 init_rotation_y: float = -35,
                 color_manager: Optional[ColorManager] = None,
                 input_manager: Optional["InputManager"] = None,
                 update_manager: Optional["UpdateManager"] = None,
                 **kwargs):
        # Use provided ColorManager or create new one
        self.color_manager: ColorManager = color_manager if color_manager is not None else ColorManager()

        # Store manager references (injected dependencies)
        self.input_manager: Optional["InputManager"] = input_manager
        self.update_manager: Optional["UpdateManager"] = update_manager

        self.lights: List[Light] = [
            DirectionalLight(rotation=(-45, -45, 45), color=self.color_manager.get_color('scene', 'directional_light'), intensity=1.5),
            DirectionalLight(rotation=(45, 0, 0), color=self.color_manager.get_color('scene', 'directional_light'), intensity=1.2),
            AmbientLight(color=self.color_manager.get_color('scene', 'ambient_light'))
        ]

        self.base_position: Tuple[float, float, float] = init_position
        self.base_speed: float = 2

        self.player: FirstPersonController = FirstPersonController(
            gravity=0,
            position=init_position,
            speed=self.base_speed
        )
        
        self.player.camera_pivot.rotation_x = init_rotation_x
        self.player.rotation_y = init_rotation_y
        
        # New flag for input "freeze"
        # input_frozen = False means cursor is captured (default)
        # input_frozen = True means cursor is released
        self.input_frozen: bool = False

        # Flag for delegating control to InputManager
        self.input_manager_mode: bool = False

        # Cursor locked by default (captured in application)
        self.cursor_locked: bool = True

        # Force capture cursor
        mouse.locked = True
        mouse.visible = False  # Hide mouse cursor

        window.color = self.color_manager.get_color('scene', 'window_background')
        self._update_cursor_state()
        
    def _update_cursor_state(self) -> None:
        """Update cursor state according to input_frozen flag."""
        mouse.locked = not self.input_frozen
        mouse.visible = self.input_frozen
        print(f"[SceneSetup] Cursor state: locked={mouse.locked}, visible={mouse.visible}")
        

    def toggle_freeze(self) -> None:
        """Toggle input freeze mode."""
        self.input_frozen = not self.input_frozen

        # Update cursor state
        self._update_cursor_state()

        # Block/unblock player
        self.player.enabled = not self.input_frozen

        status = "unlocked" if self.input_frozen else "locked"
        print(f"[SceneSetup] Cursor {status} (input_frozen={self.input_frozen})")

    def update(self, dt: float) -> None:
        """Updates additional parameters not included in FirstPersonController"""
        if self.input_manager_mode:
            return

        if self.input_frozen:
            return

        self.player.y += (held_keys['space'] - held_keys['shift']) * self.player.speed * dt
    
    def input_handler(self, key: str) -> None:
        """Input handler for program closing and speed control"""
        # If InputManager mode is enabled, don't handle keys here
        if self.input_manager_mode:
            return

        if key == 'q':
            application.quit()

    def enable_input_manager_mode(self, enabled: bool = True) -> None:
        """Enable or disable InputManager mode."""
        self.input_manager_mode = enabled
        print(f"[SceneSetup] InputManager mode: {'enabled' if enabled else 'disabled'}")
        self._update_cursor_state()
