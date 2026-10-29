"""Módulo A — escena y geometría. Solo importa de blockout.core (nunca de projection ni app)."""
from blockout.scene.scene import apply_action, create_scene, get_geometry, occupied_cells
from blockout.scene.transforms import model_matrix, rot_axis_angle, rot_axis_exact, transform_points

__all__ = ["create_scene", "apply_action", "get_geometry", "occupied_cells",
           "model_matrix", "rot_axis_exact", "rot_axis_angle", "transform_points"]
