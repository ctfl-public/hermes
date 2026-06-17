"""Mesh helpers shared by HERMES workflows."""

from __future__ import annotations

import numpy as np
import trimesh
from skimage import measure


def create_padding(image_volume: np.ndarray, padding_size: int = 1) -> np.ndarray:
    """Pad a 3D volume with zeros."""
    padded_volume = np.zeros(
        (
            image_volume.shape[0] + 2 * padding_size,
            image_volume.shape[1] + 2 * padding_size,
            image_volume.shape[2] + 2 * padding_size,
        ),
        dtype=image_volume.dtype,
    )

    x_range = slice(padding_size, padding_size + image_volume.shape[0])
    y_range = slice(padding_size, padding_size + image_volume.shape[1])
    z_range = slice(padding_size, padding_size + image_volume.shape[2])
    padded_volume[x_range, y_range, z_range] = image_volume

    return np.squeeze(np.array(padded_volume))


def generate_mesh(binary_volume: np.ndarray, voxel_size: float) -> tuple[np.ndarray, np.ndarray]:
    """Generate vertices and faces from a binary volume."""
    vertices, faces, _, _ = measure.marching_cubes(
        binary_volume,
        allow_degenerate=False,
        method="lewiner",
    )
    vertices = vertices * voxel_size - voxel_size
    faces = faces[:, ::-1]
    return vertices, faces


def load_trimesh(vertices: np.ndarray, faces: np.ndarray) -> trimesh.Trimesh:
    return trimesh.Trimesh(vertices=vertices, faces=faces)


def check_mesh(vertices: np.ndarray, faces: np.ndarray) -> bool:
    """Return whether a mesh is a watertight volume according to trimesh."""
    return bool(load_trimesh(vertices, faces).is_volume)
