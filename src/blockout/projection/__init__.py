"""Módulo B — cámara y proyección. Solo importa de blockout.core (nunca de scene ni app)."""
from blockout.projection.camera import OrbitCamera, build_camera, intrinsics_from_fov, look_at
from blockout.projection.projection import (clip_polygon_near, clip_segment_near, project,
                                            project_points)

__all__ = ["intrinsics_from_fov", "look_at", "build_camera", "OrbitCamera",
           "project_points", "project", "clip_segment_near", "clip_polygon_near"]
