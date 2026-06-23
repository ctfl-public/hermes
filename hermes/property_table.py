"""Legacy-compatible property table construction for HERMES."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hermes.centerlines import analyze_centerline
from hermes.mesh import load_trimesh
from hermes.properties import fiber_diameter_distribution, pore_distribution


LEGACY_PROPERTY_HEADER = {
    "stl_name": "StlName",
    "min_extents": ["MinExtentsX", "MinExtentsY", "MinExtentsZ"],
    "max_extents": ["MaxExtentsX", "MaxExtentsY", "MaxExtentsZ"],
    "surface_area": "SurfaceArea",
    "closed_volume": "ClosedVolume",
    "volume_by_area": "Volume/SurfaceArea",
    "porosity": "Porosity",
    "fiber_diameter": ["fiber_diameter_Mean", "fiber_diameter_Std"],
    "pore_distribution": ["meanPore", "stdPore", "poreDistribution"],
    "fiber_angle": ["ReferencePlane", "MeanAzimuthAngle", "StDAzimuthAngle", "MeanElevationAngle", "StDElevationAngle"],
    "fiber_length": ["MeanLength", "StDLength"],
}


def build_legacy_property_row(
    stl_name: str,
    vertices,
    faces,
    volume,
    voxel_size: float,
    property_options: dict,
    surface_name: str,
) -> tuple[list[str], list[object]]:
    """Build the legacy HERMES property header and row for selected options."""
    values: list[object] = [stl_name]
    names: list[str] = [LEGACY_PROPERTY_HEADER["stl_name"]]

    if property_options["min_max"]:
        min_extents = np.min(vertices, axis=0)
        max_extents = np.max(vertices, axis=0)
        values.extend(list(min_extents) + list(max_extents))
        names.extend(LEGACY_PROPERTY_HEADER["min_extents"])
        names.extend(LEGACY_PROPERTY_HEADER["max_extents"])

    needs_mesh = (
        property_options["surf_area"]
        or property_options["closed_volume"]
        or property_options["porosity"]
        or property_options["vol_by_area"]
    )
    if needs_mesh:
        trimesh_mesh = load_trimesh(vertices, faces)
        mesh_volume = trimesh_mesh.volume
        mesh_surface_area = trimesh_mesh.area

    if property_options["surf_area"]:
        values.append(mesh_surface_area)
        names.append(LEGACY_PROPERTY_HEADER["surface_area"])

    if property_options["closed_volume"]:
        values.append(mesh_volume)
        names.append(LEGACY_PROPERTY_HEADER["closed_volume"])

    if property_options["vol_by_area"]:
        values.append(mesh_volume / mesh_surface_area)
        names.append(LEGACY_PROPERTY_HEADER["volume_by_area"])

    if property_options["porosity"]:
        full_volume = volume.shape[0] * volume.shape[1] * volume.shape[2] * voxel_size**3
        values.append(1 - (mesh_volume / full_volume))
        names.append(LEGACY_PROPERTY_HEADER["porosity"])

    if property_options["fiber_diameter"]:
        mean_diameter, std_diameter, _ = fiber_diameter_distribution(
            volume,
            voxel_size,
            property_options["fiber_diam_sphere"],
        )
        values.extend([mean_diameter, std_diameter])
        names.extend(LEGACY_PROPERTY_HEADER["fiber_diameter"])

    if property_options["pore_distribution"]:
        mean_pore, std_pore, pore_values = pore_distribution(
            volume,
            voxel_size,
            property_options["pore_dist_sphere"],
        )
        values.extend([mean_pore, std_pore, pore_values])
        names.extend(LEGACY_PROPERTY_HEADER["pore_distribution"])

    if property_options["FiberAngle"] or property_options["FiberLength"]:
        azimuth_mean, elevation_mean, length_mean, azimuth_std, elevation_std, length_std = analyze_centerline(
            volume,
            voxel_size,
            surface_name,
            property_options["FiberAnglePlane"],
        )
        if property_options["FiberAngle"]:
            values.extend(
                [
                    property_options["FiberAnglePlane"],
                    azimuth_mean,
                    azimuth_std,
                    elevation_mean,
                    elevation_std,
                ]
            )
            names.extend(LEGACY_PROPERTY_HEADER["fiber_angle"])
        if property_options["FiberLength"]:
            values.extend([length_mean, length_std])
            names.extend(LEGACY_PROPERTY_HEADER["fiber_length"])

    return names, values


def compute_and_write_legacy_properties(
    stl_name: str,
    vertices,
    faces,
    volume,
    voxel_size: float,
    saving_options: dict,
    surface_name: str,
) -> tuple[list[str], list[object]]:
    """Compute selected legacy properties and append them to the configured table."""
    property_names, property_values = build_legacy_property_row(
        stl_name,
        vertices,
        faces,
        volume,
        voxel_size,
        saving_options["property_options"],
        surface_name,
    )
    write_legacy_property_row(saving_options["property_path"], property_names, property_values)
    return property_names, property_values


def write_legacy_property_row(path: str | Path, property_names: list[str], property_values: list[object]) -> None:
    """Append a legacy HERMES property row, writing the header if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "\t".join(property_names) + "\n"
    with path.open("a+", encoding="utf-8") as file_obj:
        file_obj.seek(0)
        content = file_obj.read()
        if "StlName" not in content:
            file_obj.write(header)

        formatted = [_format_value_json(value) for value in property_values]
        file_obj.write("\t".join(formatted) + "\n")


def _format_value_json(value) -> str:
    """Format a property-table value using the current HERMES legacy convention."""
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            value = value.item()
        else:
            value = value.tolist()

    if isinstance(value, (list, tuple)):
        return json.dumps(value)

    try:
        number = float(value)
        return f"{number:.4f}" if abs(number) >= 1e-4 else f"{number:.4g}"
    except Exception:
        return str(value)
