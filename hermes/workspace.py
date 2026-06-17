"""Object-oriented workspace wrapper for shared HERMES operations."""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np

from hermes.io import load_volume, write_chen_format
from hermes.mesh import check_mesh, create_padding, generate_mesh, load_trimesh
from hermes.properties import (
    fiber_diameter_distribution,
    mesh_closed_volume,
    mesh_surface_area,
    pore_distribution,
    porosity_from_mesh,
    volume_by_area,
)
from hermes.segmentation import segment_greyscale


class Workspace:
    """Container for a 3D volume, its voxel scale, and derived mesh state."""

    def __init__(
        self,
        matrix: np.ndarray | None = None,
        voxel_size: float = 1.0,
        name: str = "Workspace",
        origin: tuple[int, int, int] = (0, 0, 0),
    ):
        self.matrix = np.zeros((1, 1, 1), dtype=np.uint16) if matrix is None else matrix
        self.voxel_size = voxel_size
        self.name = name
        self.origin = origin
        self.padding_size = 0
        self.vertices: np.ndarray | None = None
        self.faces: np.ndarray | None = None
        self.properties: dict[str, object] = {}

    @classmethod
    def from_file(cls, path: str | Path, voxel_size: float = 1.0) -> "Workspace":
        path = Path(path)
        return cls(matrix=load_volume(path), voxel_size=voxel_size, name=path.name)

    def extract_subvolume(
        self,
        corner: tuple[int, int, int] = (0, 0, 0),
        dimensions: tuple[int, int, int] | str = "Full",
        sub_id: int = 0,
    ) -> "Workspace":
        if dimensions == "Full":
            return Workspace(
                matrix=self.matrix.copy(),
                voxel_size=self.voxel_size,
                name=f"{Path(self.name).stem}_Full",
                origin=corner,
            )

        x, y, z = corner
        dx, dy, dz = dimensions
        sub_matrix = self.matrix[x : x + dx, y : y + dy, z : z + dz].copy()
        return Workspace(
            matrix=sub_matrix,
            voxel_size=self.voxel_size,
            name=f"{Path(self.name).stem}_V{sub_id}_{x}-{y}-{z}-{dx}",
            origin=corner,
        )

    def segment(self, method: str, **kwargs) -> None:
        result = segment_greyscale(self.matrix, method, **kwargs)
        self.matrix = result.mask.astype(np.uint16)
        self.vertices = None
        self.faces = None

    def pad(self, padding_size: int = 1) -> None:
        self.matrix = create_padding(self.matrix, padding_size=padding_size)
        self.padding_size += padding_size
        self.vertices = None
        self.faces = None

    def generate_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        binary_matrix = self.matrix / np.max(self.matrix) if np.max(self.matrix) > 0 else self.matrix
        self.vertices, self.faces = generate_mesh(binary_matrix, self.voxel_size)
        return self.vertices, self.faces

    def get_trimesh(self):
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        return load_trimesh(self.vertices, self.faces)

    def check_mesh(self) -> bool:
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        return check_mesh(self.vertices, self.faces)

    def compute_surface_area(self) -> float:
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        value = mesh_surface_area(self.vertices, self.faces)
        self.properties["surface_area"] = value
        return value

    def compute_closed_volume(self) -> float:
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        value = mesh_closed_volume(self.vertices, self.faces)
        self.properties["closed_volume"] = value
        return value

    def compute_volume_by_area(self) -> float:
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        value = volume_by_area(self.vertices, self.faces)
        self.properties["volume_by_area"] = value
        return value

    def compute_porosity(self) -> float:
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        mat = self._unpadded_matrix()
        value = porosity_from_mesh(self.vertices, self.faces, mat.shape, self.voxel_size)
        self.properties["porosity"] = value
        return value

    def compute_fiber_diameter(self, sphere_size: float) -> tuple[float, float, list[float]]:
        value = fiber_diameter_distribution(self._unpadded_matrix(), self.voxel_size, sphere_size)
        self.properties["fiber_diameter_mean"] = value[0]
        self.properties["fiber_diameter_std"] = value[1]
        self.properties["fiber_diameter_distribution"] = value[2]
        return value

    def compute_pore_distribution(self, sphere_size: float) -> tuple[float, float, list[float]]:
        value = pore_distribution(self._unpadded_matrix(), self.voxel_size, sphere_size)
        self.properties["pore_size_mean"] = value[0]
        self.properties["pore_size_std"] = value[1]
        self.properties["pore_size_distribution"] = value[2]
        return value

    def compute_centerline_orientation(self, plane: str = "XY"):
        from voxel2stl import analyzeCenterLine

        azimuth_mean, elevation_mean, length_mean, azimuth_std, elevation_std, length_std = analyzeCenterLine(
            self._unpadded_matrix(),
            self.voxel_size,
            self.name,
            plane,
        )
        self.properties.update(
            {
                "azimuth_mean": azimuth_mean,
                "azimuth_std": azimuth_std,
                "elevation_mean": elevation_mean,
                "elevation_std": elevation_std,
                "length_mean": length_mean,
                "length_std": length_std,
            }
        )
        return azimuth_mean, elevation_mean, length_mean, azimuth_std, elevation_std, length_std

    def compute_all_properties(
        self,
        fiber_sphere: float = 10,
        pore_sphere: float = 30,
        plane: str = "XY",
    ) -> dict[str, object]:
        self.compute_surface_area()
        self.compute_closed_volume()
        self.compute_volume_by_area()
        self.compute_porosity()
        self.compute_fiber_diameter(fiber_sphere)
        self.compute_pore_distribution(pore_sphere)
        self.compute_centerline_orientation(plane=plane)
        return self.properties

    def save_voxel_data(self, path: str | Path) -> None:
        write_chen_format(path, self.matrix, self.voxel_size)

    def export_stl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.get_trimesh().export(path, file_type="stl_ascii")

    def save_properties(self, path: str | Path, append: bool = True) -> None:
        if not self.properties:
            return

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a+" if append else "w"
        keys = ["WorkspaceName"] + list(self.properties.keys())
        values = [self.name] + list(self.properties.values())

        with path.open(mode) as file_obj:
            file_obj.seek(0)
            existing = file_obj.read()
            if "WorkspaceName" not in existing:
                file_obj.write("\t".join(keys) + "\n")
            line = "\t".join(_format_property_value(value) for value in values)
            file_obj.write(line + "\n")

    def _unpadded_matrix(self) -> np.ndarray:
        if self.padding_size == 0:
            return self.matrix
        pad = self.padding_size
        return self.matrix[pad:-pad, pad:-pad, pad:-pad]


def _format_property_value(value: object) -> str:
    if isinstance(value, np.ndarray):
        return json.dumps(value.tolist())
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value))
    return str(value)
