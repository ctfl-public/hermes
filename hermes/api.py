"""Public Python API for HERMES workflows."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hermes.io import load_volume, write_chen_format, write_tiff_volume
from hermes.pipeline import run_pipeline_config
from hermes.segmentation import SegmentationResult, segment_greyscale
from hermes.workspace import Workspace


def segment(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    method: str = "otsu",
    phase: str = "lighter",
    minimum: int = 0,
    maximum: int = 255,
    block_size: int = 51,
    offset: int | float = 10,
    voxel_size: float = 1.0,
) -> SegmentationResult:
    """Segment a grayscale volume and optionally write the binary mask."""
    image = load_volume(input_path)
    result = segment_greyscale(
        image,
        method,
        select_lighter=phase.lower() != "darker",
        block_size=block_size,
        offset=offset,
        min_manual=minimum,
        max_manual=maximum,
    )

    if output_path is not None:
        _write_binary_volume(output_path, result.mask.astype(np.uint8), voxel_size)

    return result


def mesh(
    input_path: str | Path,
    output_path: str | Path,
    *,
    voxel_size: float = 1.0,
    pad: bool = True,
) -> dict[str, object]:
    """Generate an STL mesh from a binary volume."""
    workspace = Workspace.from_file(input_path, voxel_size=voxel_size)
    workspace.matrix = (workspace.matrix > 0).astype(np.uint8)
    workspace.name = Path(output_path).stem
    if pad:
        workspace.pad()
    workspace.generate_mesh()
    workspace.export_stl(output_path)
    return {
        "output": str(output_path),
        "vertices": int(len(workspace.vertices)),
        "faces": int(len(workspace.faces)),
        "is_volume": workspace.check_mesh(),
    }


def properties(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    voxel_size: float = 1.0,
    pad: bool = True,
    names: tuple[str, ...] = ("surface_area", "closed_volume", "volume_by_area", "porosity"),
) -> dict[str, object]:
    """Compute basic geometric properties for a binary volume."""
    workspace = Workspace.from_file(input_path, voxel_size=voxel_size)
    workspace.matrix = (workspace.matrix > 0).astype(np.uint8)
    if pad:
        workspace.pad()
    workspace.generate_mesh()

    if "surface_area" in names:
        workspace.compute_surface_area()
    if "closed_volume" in names:
        workspace.compute_closed_volume()
    if "volume_by_area" in names:
        workspace.compute_volume_by_area()
    if "porosity" in names:
        workspace.compute_porosity()

    if output_path is not None:
        workspace.save_properties(output_path, append=False)

    return dict(workspace.properties)


def run(config_path: str | Path) -> dict[str, object]:
    """Run a complete HERMES workflow from a config file."""
    return run_pipeline_config(config_path)


def _write_binary_volume(output_path: str | Path, volume: np.ndarray, voxel_size: float) -> None:
    output_path = Path(output_path)
    suffix = output_path.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        write_tiff_volume(output_path, volume.astype(np.uint8))
        return
    if suffix in {".dat", ".txt"}:
        write_chen_format(output_path, volume.astype(np.uint8), voxel_size)
        return
    raise ValueError(f"Unsupported output format: {output_path.suffix}")
