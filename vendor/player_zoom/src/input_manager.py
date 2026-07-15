"""
Simplified InputManager for player_zoom
Handles only basic commands: zoom, movement, UI
"""

from ursina import held_keys, mouse, application
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .scene_setup import SceneSetup
    from .zoom_manager import ZoomManager
    from .frame import Frame
    from .window_manager import WindowManager
    from .my_object import MyObject


class InputManager:
    """
    Simplified class for handling user input in player_zoom.
    Supports only basic commands.

    Components can be registered after initialization to avoid circular dependencies.
    """
    def __init__(self):
        self.scene_setup: Optional["SceneSetup"] = None
        self.zoom_manager: Optional["ZoomManager"] = None
        self.frame: Optional["Frame"] = None
        self.window_manager: Optional["WindowManager"] = None
        self.my_object: Optional["MyObject"] = None
        self.key_handlers: dict = {}

        print(f"[DEBUG] InputManager initialized (simplified version)")

    def register_key_handler(self, key: str, callback) -> None:
        """
        Generic extension point: register a no-arg callback for a specific
        key, without InputManager needing to know about the caller's
        classes. Takes priority over the built-in bindings below.
        """
        self.key_handlers[key] = callback
        print(f"   key_handler: registered for '{key}'")

    def register_scene_setup(self, scene_setup: "SceneSetup") -> None:
        """Register SceneSetup component."""
        self.scene_setup = scene_setup
        print(f"   scene_setup: registered")

    def register_zoom_manager(self, zoom_manager: "ZoomManager") -> None:
        """Register ZoomManager component."""
        self.zoom_manager = zoom_manager
        print(f"   zoom_manager: registered")

    def register_frame(self, frame: "Frame") -> None:
        """Register Frame component."""
        self.frame = frame
        print(f"   frame: registered")

    def register_window_manager(self, window_manager: "WindowManager") -> None:
        """Register WindowManager component."""
        self.window_manager = window_manager
        print(f"   window_manager: registered")

    def register_my_object(self, my_object: "MyObject") -> None:
        """Register MyObject component."""
        self.my_object = my_object
        print(f"   my_object: registered")

    def handle_input(self, key: str) -> None:
        """Handle key press."""

        # Exit
        if key == 'escape':
            application.quit()
            return

        # === CUSTOM KEY HANDLERS (generic extension point, checked first) ===
        if key in self.key_handlers:
            self.key_handlers[key]()
            return

        # Fullscreen mode
        if key == 'f11' and self.window_manager:
            self.window_manager.toggle_fullscreen()
            print(f"   [Window] Fullscreen: {'enabled' if self.window_manager.is_fullscreen() else 'disabled'}")
            return

        # Toggle cursor
        if key == 'alt' and self.scene_setup:
            self.scene_setup.toggle_freeze()
            return

        # If input is frozen, don't process other commands
        if self.scene_setup and self.scene_setup.input_frozen:
            return

        # === ZOOM ===
        if self.zoom_manager:
            if key == 'e':
                self.zoom_manager.zoom_in()
                print("   [Zoom] Zoom in")
                return

            if key == 'q':
                self.zoom_manager.zoom_out()
                print("   [Zoom] Zoom out")
                return

            if key == 'r':
                self.zoom_manager.reset_zoom()
                print("   [Zoom] Reset")
                return

        # === MY OBJECT SPEED CONTROL ===
        if self.my_object:
            if key == '1':
                self.my_object.decrease_speed()
                return

            if key == '2':
                self.my_object.increase_speed()
                return

        # === DEBUG ===
        if key == 'h':
            self._print_debug_info()
            return

    def _print_debug_info(self):
        """Print debug information."""
        print("\n" + "=" * 50)
        print("DEBUG INFO")
        print("=" * 50)

        if self.scene_setup:
            print(f"Camera position: {self.scene_setup.player.position}")
            print(f"Camera rotation: y={self.scene_setup.player.rotation_y}, "
                  f"x={self.scene_setup.player.camera_pivot.rotation_x}")
            print(f"Cursor locked: {self.scene_setup.cursor_locked}")
            print(f"Input frozen: {self.scene_setup.input_frozen}")

        if self.zoom_manager:
            print(f"Zoom transform: a={self.zoom_manager.a_transformation:.4f}")
            print(f"Zoom translation: {self.zoom_manager.b_translation}")
            print(f"Registered objects: {len(self.zoom_manager.objects)}")

            # Look point
            look_x, look_z = self.zoom_manager.identify_invariant_point()
            print(f"Look point: ({look_x:.4f}, {look_z:.4f})")

        if self.frame:
            print(f"Frame visible: {self.frame.is_visible()}")

        print("=" * 50 + "\n")

    def update(self):
        """Update state (called every frame)."""
        # Currently nothing, but can add logic here
        pass
