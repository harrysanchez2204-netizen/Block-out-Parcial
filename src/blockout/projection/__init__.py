"""Módulo B — cámara y proyección. Solo importa de blockout.core (nunca de scene ni app)."""
from blockout.projection.camera import build_camera, intrinsics_from_fov, look_at
from blockout.projection.projection import clip_segment_near, project, project_points

__all__ = ["intrinsics_from_fov", "look_at", "build_camera",
           "project_points", "project", "clip_segment_near"]
