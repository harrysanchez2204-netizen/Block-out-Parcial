"""Módulo A — escena y geometría. Solo importa de blockout.core (nunca de projection ni app)."""
from blockout.scene.scene import apply_action, create_scene, get_geometry
from blockout.scene.transforms import model_matrix, rot_axis_exact, transform_points

__all__ = ["create_scene", "apply_action", "get_geometry",
           "model_matrix", "rot_axis_exact", "transform_points"]
