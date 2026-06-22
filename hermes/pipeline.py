"""Small reusable pipeline entry points for HERMES workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import json
import numpy as np
import tifffile as tiff

from hermes.io import write_tiff_volume
from hermes.workspace import Workspace


DEFAULT_PROPERTIES = ("surface_area", "closed_volume", "volume_by_area", "porosity")
DEFAULT_OUTPUTS = ("stl", "dat", "properties")


def run_volume_pipeline(
    input_path: str | Path,
    voxel_size: float,
    output_dir: str | Path,
    *,
    name: str | None = None,
    outputs: Iterable[str] = DEFAULT_OUTPUTS,
    properties: Iterable[str] = DEFAULT_PROPERTIES,
    pad: bool = True,
    crop: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run a compact volume-to-properties workflow without editing source files."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_set = set(outputs)
    property_set = set(properties)

    workspace = Workspace.from_file(input_path, voxel_size=voxel_size)
    workspace.matrix = (workspace.matrix > 0).astype(np.uint8)
    if crop is not None:
        workspace = workspace.extract_subvolume(
            corner=tuple(int(value) for value in crop.get("corner", [0, 0, 0])),
            dimensions=tuple(int(value) for value in crop["size"]),
        )
    workspace.name = name or workspace.name

    if pad:
        workspace.pad()

    workspace.generate_mesh()

    if "surface_area" in property_set:
        workspace.compute_surface_area()
    if "closed_volume" in property_set:
        workspace.compute_closed_volume()
    if "volume_by_area" in property_set:
        workspace.compute_volume_by_area()
    if "porosity" in property_set:
        workspace.compute_porosity()

    written: dict[str, str] = {}
    if "stl" in output_set:
        stl_path = output_dir / "stl" / f"{workspace.name}.stl"
        workspace.export_stl(stl_path)
        written["stl"] = str(stl_path)
    if "dat" in output_set:
        dat_path = output_dir / "voxels" / f"{workspace.name}.dat"
        workspace.save_voxel_data(dat_path)
        written["dat"] = str(dat_path)
    if "tiff" in output_set:
        tiff_path = output_dir / "tiff" / f"{workspace.name}.tif"
        write_tiff_volume(tiff_path, workspace._unpadded_matrix().astype(np.uint8))
        written["tiff"] = str(tiff_path)
    if "properties" in output_set:
        properties_path = output_dir / "properties.txt"
        workspace.save_properties(properties_path, append=False)
        written["properties"] = str(properties_path)

    return {
        "name": workspace.name,
        "input": str(input_path),
        "output_dir": str(output_dir),
        "properties": dict(workspace.properties),
        "written": written,
    }


def run_pipeline_config(config_path: str | Path) -> dict[str, object]:
    """Run a HERMES workflow from a JSON config file."""
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as file_obj:
        config = json.load(file_obj)

    base_dir = config_path.parent
    input_config = config["input"]
    input_path = _resolve_path(input_config["path"], base_dir)
    output_dir = _resolve_path(config["output_dir"], base_dir)

    if "generate" in input_config:
        _write_generated_volume(input_path, input_config["generate"])

    return run_volume_pipeline(
        input_path,
        float(input_config.get("voxel_size", 1.0)),
        output_dir,
        name=config.get("name"),
        outputs=config.get("outputs", DEFAULT_OUTPUTS),
        properties=config.get("properties", DEFAULT_PROPERTIES),
        pad=bool(config.get("pad", True)),
        crop=config.get("crop"),
    )


def _resolve_path(path: str | Path, base_dir: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return base_dir / path


def _write_generated_volume(path: Path, generate_config: dict[str, object]) -> None:
    kind = generate_config.get("kind")
    if kind != "binary_cube":
        raise ValueError(f"Unsupported generated volume kind: {kind}")

    shape = tuple(int(value) for value in generate_config.get("shape", [16, 16, 16]))
    bounds = generate_config.get("bounds", [[4, 12], [4, 12], [4, 12]])
    volume = np.zeros(shape, dtype=np.uint8)
    x_bounds, y_bounds, z_bounds = bounds
    volume[
        int(x_bounds[0]) : int(x_bounds[1]),
        int(y_bounds[0]) : int(y_bounds[1]),
        int(z_bounds[0]) : int(z_bounds[1]),
    ] = 1

    path.parent.mkdir(parents=True, exist_ok=True)
    tiff.imwrite(path, volume, imagej=True)
