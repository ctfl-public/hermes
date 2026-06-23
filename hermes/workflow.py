"""Workflow entry points for HERMES analyses."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import json
import numpy as np
import random
import tifffile as tiff

from hermes.io import write_tiff_volume
from hermes.mesh import repair_mesh, smooth_mesh
from hermes.sampling import specs_from_config
from hermes.workspace import Workspace


DEFAULT_PROPERTIES = ("surface_area", "closed_volume", "volume_by_area", "porosity")
DEFAULT_OUTPUTS = ("stl", "dat", "properties")


def run_volume(
    input_path: str | Path,
    voxel_size: float,
    output_dir: str | Path,
    *,
    name: str | None = None,
    outputs: Iterable[str] = DEFAULT_OUTPUTS,
    properties: Iterable[str] = DEFAULT_PROPERTIES,
    property_options: dict[str, object] | None = None,
    surface_settings: dict[str, object] | None = None,
    output_paths: dict[str, str] | None = None,
    pad: bool = True,
    crop: dict[str, object] | None = None,
    append_properties: bool = False,
) -> dict[str, object]:
    """Run a compact volume-to-properties workflow without editing source files."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    workspace = Workspace.from_file(input_path, voxel_size=voxel_size)
    workspace.matrix = (workspace.matrix > 0).astype(np.uint8)
    if crop is not None:
        workspace = workspace.extract_subvolume(
            corner=tuple(int(value) for value in crop.get("corner", [0, 0, 0])),
            dimensions=tuple(int(value) for value in crop["size"]),
        )
    workspace.name = name or workspace.name

    return run_workspace(
        workspace,
        output_dir,
        outputs=outputs,
        properties=properties,
        property_options=property_options,
        surface_settings=surface_settings,
        output_paths=output_paths,
        pad=pad,
        append_properties=append_properties,
    )


def run_workspace(
    workspace: Workspace,
    output_dir: str | Path,
    *,
    outputs: Iterable[str] = DEFAULT_OUTPUTS,
    properties: Iterable[str] = DEFAULT_PROPERTIES,
    property_options: dict[str, object] | None = None,
    surface_settings: dict[str, object] | None = None,
    output_paths: dict[str, str] | None = None,
    pad: bool = True,
    append_properties: bool = False,
) -> dict[str, object]:
    """Run mesh, output, and property steps for an in-memory workspace."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_set = set(outputs)
    property_set = set(properties)
    property_options = property_options or {}
    surface_settings = surface_settings or _default_surface_settings()
    output_paths = output_paths or {}

    if pad:
        workspace.pad()

    workspace.generate_mesh()
    if _uses_surface_processing(surface_settings):
        workspace.name, workspace.vertices, workspace.faces = smooth_mesh(
            workspace.name,
            workspace.vertices,
            workspace.faces,
            surface_settings,
        )
    if not workspace.check_mesh():
        workspace.name, workspace.vertices, workspace.faces = repair_mesh(
            workspace.name,
            workspace.vertices,
            workspace.faces,
        )

    if "surface_area" in property_set:
        workspace.compute_surface_area()
    if "closed_volume" in property_set:
        workspace.compute_closed_volume()
    if "volume_by_area" in property_set:
        workspace.compute_volume_by_area()
    if "porosity" in property_set:
        workspace.compute_porosity()
    if "min_extents" in property_set:
        workspace.compute_min_extents()
    if "max_extents" in property_set:
        workspace.compute_max_extents()
    if "fiber_diameter" in property_set:
        workspace.compute_fiber_diameter(float(property_options.get("fiber_diam_sphere", 10)))
    if "pore_distribution" in property_set:
        workspace.compute_pore_distribution(float(property_options.get("pore_dist_sphere", 30)))
    if "fiber_angle" in property_set or "fiber_length" in property_set:
        workspace.compute_centerline_orientation(
            plane=str(property_options.get("fiber_angle_plane", "XY")),
            direction_map_path=output_dir / "direction_maps" / f"{workspace.name}_voxel_directions.txt",
        )

    written: dict[str, str] = {}
    if "stl" in output_set:
        stl_dir = Path(output_paths.get("stl", output_dir / "stl"))
        stl_path = stl_dir / f"{workspace.name}.stl"
        workspace.export_stl(stl_path)
        written["stl"] = str(stl_path)
    if "dat" in output_set:
        dat_dir = Path(output_paths.get("dat", output_dir / "voxels"))
        dat_path = dat_dir / f"{workspace.name}.dat"
        workspace.save_voxel_data(dat_path)
        written["dat"] = str(dat_path)
    if "tiff" in output_set:
        tiff_dir = Path(output_paths.get("tiff", output_dir / "tiff"))
        tiff_path = tiff_dir / f"{workspace.name}.tif"
        write_tiff_volume(tiff_path, workspace._unpadded_matrix().astype(np.uint8))
        written["tiff"] = str(tiff_path)
    if "properties" in output_set:
        properties_path = Path(output_paths.get("properties", output_dir / "properties.txt"))
        workspace.save_properties(properties_path, append=append_properties)
        written["properties"] = str(properties_path)

    return {
        "name": workspace.name,
        "output_dir": str(output_dir),
        "properties": dict(workspace.properties),
        "written": written,
    }


def run_config(config_path: str | Path) -> dict[str, object]:
    """Run a HERMES workflow from a JSON config file."""
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as file_obj:
        config = json.load(file_obj)
    config = _unwrap_workflow_config(config)

    return run_workflow_config(config, base_dir=config_path.parent)


def run_workflow_config(config: dict[str, object], *, base_dir: str | Path = ".") -> dict[str, object]:
    """Run a HERMES workflow from an in-memory config dictionary."""
    base_dir = Path(base_dir)
    output_dir = _resolve_path(config.get("output_dir", "."), base_dir)
    output_paths = _resolve_output_paths(config.get("output_paths", {}), base_dir)
    input_configs = _input_configs(config)

    if len(input_configs) > 1:
        results = []
        property_rows_written = 0
        sampling_overrides = _multi_input_sampling_overrides(config, input_configs)
        for index, input_config in enumerate(input_configs):
            input_config_run = config
            if sampling_overrides is not None:
                input_config_run = {**config, "sampling": sampling_overrides[index]}
            result = _run_input_config(
                input_config,
                input_config_run,
                base_dir=base_dir,
                output_dir=output_dir,
                output_paths=output_paths,
                append_first_properties=property_rows_written > 0,
            )
            property_rows_written += _property_result_count(result, config.get("outputs", DEFAULT_OUTPUTS))
            results.append(result)
        return {
            "inputs": [str(_resolve_path(input_config["path"], base_dir)) for input_config in input_configs],
            "output_dir": str(output_dir),
            "results": results,
        }

    return _run_input_config(
        input_configs[0],
        config,
        base_dir=base_dir,
        output_dir=output_dir,
        output_paths=output_paths,
        append_first_properties=False,
    )


def _run_input_config(
    input_config: dict[str, object],
    config: dict[str, object],
    *,
    base_dir: Path,
    output_dir: Path,
    output_paths: dict[str, str],
    append_first_properties: bool,
) -> dict[str, object]:
    input_path = _resolve_path(input_config["path"], base_dir)
    if "generate" in input_config:
        _write_generated_volume(input_path, input_config["generate"])

    if "sampling" in config:
        voxel_size = float(input_config.get("voxel_size", 1.0))
        source = Workspace.from_file(input_path, voxel_size=voxel_size)
        source.matrix = (source.matrix > 0).astype(np.uint8)
        base_name = input_config.get("name", config.get("name", Path(input_path).stem))
        results = []
        specs = specs_from_config(config["sampling"], source.matrix.shape, voxel_size)
        for index, spec in enumerate(specs):
            if spec.size is None:
                workspace = source.extract_subvolume(corner=spec.corner, dimensions="Full", sub_id=index)
            else:
                workspace = source.extract_subvolume(corner=spec.corner, dimensions=spec.size, sub_id=index)
            workspace.name = f"{base_name}_{spec.label}"
            results.append(
                run_workspace(
                    workspace,
                    output_dir,
                    outputs=config.get("outputs", DEFAULT_OUTPUTS),
                    properties=config.get("properties", DEFAULT_PROPERTIES),
                    property_options=config.get("property_options"),
                    surface_settings=config.get("surface_settings"),
                    output_paths=output_paths,
                    pad=bool(config.get("pad", True)),
                    append_properties=append_first_properties or index > 0,
                )
            )
        return {"input": str(input_path), "output_dir": str(output_dir), "samples": results}

    return run_volume(
        input_path,
        float(input_config.get("voxel_size", 1.0)),
        output_dir,
        name=input_config.get("name", config.get("name", Path(input_path).stem)),
        outputs=config.get("outputs", DEFAULT_OUTPUTS),
        properties=config.get("properties", DEFAULT_PROPERTIES),
        property_options=config.get("property_options"),
        surface_settings=config.get("surface_settings"),
        output_paths=output_paths,
        pad=bool(config.get("pad", True)),
        crop=config.get("crop"),
        append_properties=append_first_properties,
    )


def _unwrap_workflow_config(config: dict[str, object]) -> dict[str, object]:
    """Accept either a raw workflow config or a GUI settings file containing one."""
    if "workflowConfig" in config:
        return config["workflowConfig"]
    return config


def _input_configs(config: dict[str, object]) -> list[dict[str, object]]:
    if "inputs" in config:
        return list(config["inputs"])
    return [config["input"]]


def _property_result_count(result: dict[str, object], outputs: Iterable[str]) -> int:
    if "properties" not in set(outputs):
        return 0
    if "samples" in result:
        return len(result["samples"])
    return 1


def _multi_input_sampling_overrides(
    config: dict[str, object],
    input_configs: list[dict[str, object]],
) -> list[dict[str, object]] | None:
    sampling = config.get("sampling")
    if not sampling or sampling.get("mode") != "random" or sampling.get("count_mode") != "total":
        return None

    rng = random.Random(sampling.get("seed"))
    counts = [0 for _ in input_configs]
    for _ in range(int(sampling["count"])):
        counts[rng.randrange(len(input_configs))] += 1

    overrides = []
    for index, count in enumerate(counts):
        input_sampling = dict(sampling)
        input_sampling["count"] = count
        if sampling.get("seed") is not None:
            input_sampling["seed"] = int(sampling["seed"]) + index
        overrides.append(input_sampling)
    return overrides


def _default_surface_settings() -> dict[str, object]:
    return {
        "laplacianFlag": False,
        "laplacian_iter": None,
        "ScreenedPoissonFlag": False,
        "ScreenedPoisson_iter": None,
        "RemoveIslandsFlag": False,
    }


def _uses_surface_processing(surface_settings: dict[str, object]) -> bool:
    return bool(
        surface_settings.get("laplacianFlag")
        or surface_settings.get("ScreenedPoissonFlag")
        or surface_settings.get("RemoveIslandsFlag")
    )


def _resolve_path(path: str | Path, base_dir: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return base_dir / path


def _resolve_output_paths(output_paths: dict[str, str], base_dir: Path) -> dict[str, str]:
    return {key: str(_resolve_path(path, base_dir)) for key, path in output_paths.items()}


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
