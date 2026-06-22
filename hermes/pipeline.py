"""Small reusable pipeline entry points for HERMES workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

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
) -> dict[str, object]:
    """Run a compact volume-to-properties workflow without editing source files."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_set = set(outputs)
    property_set = set(properties)

    workspace = Workspace.from_file(input_path, voxel_size=voxel_size)
    workspace.name = name or input_path.stem
    workspace.matrix = (workspace.matrix > 0).astype(np.uint8)

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
