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


def load_pymeshlab_mesh(vertices: np.ndarray, faces: np.ndarray):
    """Load vertices and faces into a PyMeshLab MeshSet."""
    import pymeshlab as ml

    mesh = ml.Mesh(vertices, faces)
    mesh_set = ml.MeshSet(verbose=True)
    mesh_set.add_mesh(mesh)
    return mesh_set


def remove_floating_islands(vertices: np.ndarray, faces: np.ndarray, *, meshset_loader=load_pymeshlab_mesh):
    """Remove small disconnected mesh components with PyMeshLab."""
    mesh_set = meshset_loader(vertices, faces)
    mesh_set.apply_filter("compute_selection_by_small_disconnected_components_per_face", nbfaceratio=1)
    mesh_set.apply_filter("meshing_remove_selected_vertices_and_faces")
    return mesh_set


def smooth_mesh(
    name: str,
    vertices: np.ndarray,
    faces: np.ndarray,
    surface_settings: dict,
    *,
    meshset_loader=load_pymeshlab_mesh,
) -> tuple[str, np.ndarray, np.ndarray]:
    """Apply optional smoothing and island removal to a mesh."""
    filter_name = ""
    if surface_settings["laplacianFlag"]:
        mesh = load_trimesh(vertices, faces)
        filter_name = "_laplacian" + str(surface_settings["laplacian_iter"])
        mesh = trimesh.smoothing.filter_laplacian(
            mesh,
            lamb=0.5,
            iterations=surface_settings["laplacian_iter"],
            volume_constraint=True,
        )
        vertices = mesh.vertices
        faces = mesh.faces
    elif surface_settings["ScreenedPoissonFlag"]:
        filter_name = "_screened_poisson" + str(surface_settings["ScreenedPoisson_iter"])
        mesh_set = meshset_loader(vertices, faces)
        mesh_set.apply_filter(
            "generate_surface_reconstruction_screened_poisson",
            depth=surface_settings["ScreenedPoisson_iter"],
            preclean=True,
        )
        mesh = mesh_set.current_mesh()
        vertices = mesh.vertex_matrix()
        faces = mesh.face_matrix()

    island_name = ""
    if surface_settings["RemoveIslandsFlag"]:
        mesh_set = remove_floating_islands(vertices, faces, meshset_loader=meshset_loader)
        island_name = "_NI"
        mesh = mesh_set.current_mesh()
        vertices = mesh.vertex_matrix()
        faces = mesh.face_matrix()

    return name + filter_name + island_name, vertices, faces


def repair_mesh(
    name: str,
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    meshset_loader=load_pymeshlab_mesh,
) -> tuple[str, np.ndarray, np.ndarray]:
    """Run the legacy PyMeshLab repair filter sequence."""
    mesh_set = meshset_loader(vertices, faces)
    mesh_set.apply_filter("generate_surface_reconstruction_screened_poisson", depth=8, preclean=True)
    mesh_set.apply_filter("meshing_remove_null_faces")
    mesh_set.apply_filter("meshing_repair_non_manifold_edges")
    mesh_set.apply_filter("meshing_repair_non_manifold_vertices")
    mesh_set.apply_filter("meshing_remove_duplicate_faces")
    mesh_set.apply_filter("meshing_remove_duplicate_vertices")
    mesh_set.apply_filter("meshing_re_orient_faces_coherently")
    mesh = mesh_set.current_mesh()
    return name + "_Fixed", mesh.vertex_matrix(), mesh.face_matrix()
