import json
import os
from ursina import color, Vec4
from typing import Dict, List, Optional, Any, Tuple

class ColorManager:
    def __init__(self, colors_file_path: Optional[str] = None):
        if colors_file_path is None:
            # Path to colors.json in player_zoom
            # .. -> src/ -> player_zoom/
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            colors_file_path = os.path.join(project_root, 'config', 'colors.json')

        self.colors_file_path: str = colors_file_path
        self.colors: Dict[str, Any] = self._load_colors()

    def _load_colors(self) -> Dict[str, Any]:
        """Load colors from JSON file"""
        try:
            with open(self.colors_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[ColorManager] Config file not found: {self.colors_file_path}")
            print(f"[ColorManager] Using default colors")
            return self._get_default_colors()
        except json.JSONDecodeError as e:
            print(f"[ColorManager] JSON parse error: {e}")
            print(f"[ColorManager] Using default colors")
            return self._get_default_colors()

    def _get_default_colors(self) -> Dict[str, Any]:
        """Returns default colors if config file is missing"""
        return {
            "frame": {
                "origin": [1.0, 1.0, 1.0, 1.0],
                "x_axis": [0.863, 0.196, 0.184, 1.0],
                "y_axis": [0.2, 0.7, 0.25, 1.0],
                "z_axis": [0.149, 0.545, 0.824, 1.0]
            },
            "scene": {
                "floor": [0.3, 0.3, 0.4, 0.5],
                "window_background": [0.08, 0.1, 0.2, 1.0],
                "ambient_light": [0.6, 0.6, 0.65, 1.0],
                "directional_light": [1.0, 1.0, 1.0, 1.0]
            }
        }

    def get_color(self, category: str, color_name: str) -> Vec4:
        """
        Get color in Ursina format

        Args:
            category (str): Color category (frame, scene, spore, link, ui)
            color_name (str): Color name in category

        Returns:
            ursina.color: Color in Ursina format
        """
        try:
            rgba = self.colors[category][color_name]
            return color.rgba(*rgba)
        except KeyError:
            print(f"[ColorManager] Color {category}.{color_name} not found. Using white.")
            return color.white

    def get_rgba(self, category: str, color_name: str) -> Tuple[float, float, float, float]:
        """
        Get color in RGBA tuple format

        Args:
            category (str): Color category
            color_name (str): Color name in category

        Returns:
            tuple: RGBA values (r, g, b, a)
        """
        try:
            return tuple(self.colors[category][color_name])
        except KeyError:
            print(f"[ColorManager] Color {category}.{color_name} not found. Using white.")
            return (1.0, 1.0, 1.0, 1.0)

    def reload_colors(self) -> None:
        """Reload colors from file"""
        self.colors = self._load_colors()
        print("[ColorManager] Colors reloaded from file")

    def save_colors(self) -> None:
        """Save current colors to file"""
        try:
            with open(self.colors_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.colors, f, ensure_ascii=False, indent=2)
            print(f"[ColorManager] Colors saved to {self.colors_file_path}")
        except Exception as e:
            print(f"[ColorManager] Error saving colors: {e}")

    def set_color(self, category: str, color_name: str, rgba: List[float]) -> None:
        """
        Set new color

        Args:
            category (str): Color category
            color_name (str): Color name
            rgba (list): RGBA values [r, g, b, a]
        """
        if category not in self.colors:
            self.colors[category] = {}
        self.colors[category][color_name] = rgba
        print(f"[ColorManager] Color {category}.{color_name} set to {rgba}")

    def get_value(self, section: str, name: str) -> Any:
        """Returns individual value (not color) from config."""
        try:
            return self.colors[section][name]
        except KeyError:
            print(f"Warning: Value for '{section}' -> '{name}' not found. Returning default (1).")
            return 1
