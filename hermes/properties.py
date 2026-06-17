"""Material property calculations shared by HERMES workflows."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.feature import peak_local_max

from hermes.mesh import load_trimesh


def mesh_surface_area(vertices: np.ndarray, faces: np.ndarray) -> float:
    return float(load_trimesh(vertices, faces).area)


def mesh_closed_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    return float(load_trimesh(vertices, faces).volume)


def volume_by_area(vertices: np.ndarray, faces: np.ndarray) -> float:
    mesh = load_trimesh(vertices, faces)
    return float(mesh.volume / mesh.area)


def porosity_from_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    volume_shape: tuple[int, int, int],
    voxel_size: float,
) -> float:
    mesh_volume = load_trimesh(vertices, faces).volume
    full_volume = volume_shape[0] * volume_shape[1] * volume_shape[2] * voxel_size**3
    return float(1 - (mesh_volume / full_volume))


def fiber_diameter_distribution(
    image_volume: np.ndarray,
    voxel_size: float,
    sphere_size: float,
) -> tuple[float, float, list[float]]:
    distance_transform = distance_transform_edt(image_volume)
    local_maxima_coords = peak_local_max(
        distance_transform,
        min_distance=int(0.5 * sphere_size / voxel_size),
        labels=image_volume.astype(int),
    )

    fiber_diameters = []
    for max_coords in local_maxima_coords:
        distances = distance_transform[tuple(max_coords)]
        fiber_diameters.append(2 * np.max(distances))

    fiber_diameters = np.multiply(fiber_diameters, voxel_size) - voxel_size / 2
    return float(np.mean(fiber_diameters)), float(np.std(fiber_diameters)), list(fiber_diameters)


def pore_distribution(
    image_volume: np.ndarray,
    voxel_size: float,
    sphere_size: float,
) -> tuple[float, float, list[float]]:
    inverted_volume = (image_volume == 0).astype(int)
    distance_transform = distance_transform_edt(inverted_volume)
    local_maxima_coords = peak_local_max(
        distance_transform,
        min_distance=int(0.5 * sphere_size / voxel_size),
        labels=inverted_volume.astype(int),
    )

    pores = []
    for max_coords in local_maxima_coords:
        distances = distance_transform[tuple(max_coords)]
        pores.append(2 * np.max(distances))

    pores = np.multiply(pores, voxel_size) - voxel_size / 2
    return float(np.mean(pores)), float(np.std(pores)), list(pores)
