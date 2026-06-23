"""Adapters between GUI widget state and framework workflow calls."""

from __future__ import annotations

from pathlib import Path


class GuiAdapterError(ValueError):
    """Raised when GUI state cannot be converted into workflow settings."""


def build_serial_run_arguments(state: dict):
    """Build ``run_serial`` arguments from GUI state."""
    filenames, filevoxels = _parse_input_rows(state["input_rows"])
    corners = _parse_corner_rows(state.get("corner_rows", []))
    surface_settings = _surface_settings(state)
    saving_options = _saving_options(state)
    cropping_flag = _cropping_flag(state.get("active_tab_index", 0))

    if cropping_flag == "Regular":
        volume_length = _required_int(state.get("regular_volume_length"), "Please enter both the volume length and the number of volumes.")
        num_volumes = _required_int(state.get("regular_num_volumes"), "Please enter both the volume length and the number of volumes.")
        crop_settings = filenames, filevoxels, num_volumes, volume_length
    elif cropping_flag == "Corners":
        volume_length = _required_int(state.get("corner_volume_length"), "Please enter the volume length.")
        crop_settings = filenames, filevoxels, corners, volume_length
    else:
        raise GuiAdapterError("Unknown workflow tab selected.")

    return cropping_flag, crop_settings, surface_settings, saving_options


def build_workflow_config(state: dict) -> dict:
    """Build a shared workflow config from GUI state when the config model supports it."""
    filenames, filevoxels = _parse_input_rows(state["input_rows"])

    _, _, _, saving_options = build_serial_run_arguments(state)
    output_dir = _config_output_dir(saving_options)
    config = {
        "output_dir": output_dir,
        "output_paths": _config_output_paths(saving_options),
        "outputs": _config_outputs(saving_options),
        "properties": _config_properties(saving_options["property_options"]),
        "property_options": _config_property_options(saving_options["property_options"]),
        "surface_settings": _surface_settings(state),
    }
    if len(filenames) == 1:
        config["name"] = Path(filenames[0]).stem
        config["input"] = {
            "path": filenames[0],
            "voxel_size": filevoxels[0],
        }
    else:
        config["inputs"] = [
            {
                "path": filename,
                "voxel_size": voxel_size,
            }
            for filename, voxel_size in zip(filenames, filevoxels)
        ]

    sampling = _config_sampling(state, filevoxels[0])
    if sampling is not None:
        config["sampling"] = sampling

    return config


def legacy_settings_from_workflow_config(config: dict, *, base_dir: str | Path | None = None) -> dict:
    """Translate a framework workflow config into the current GUI settings format."""
    if "workflowConfig" in config:
        config = config["workflowConfig"]
    base_dir = Path(base_dir) if base_dir is not None else None
    inputs = config["inputs"] if "inputs" in config else [config["input"]]
    outputs = config.get("outputs", [])
    output_dir = _resolve_config_path(config.get("output_dir", "."), base_dir)
    output_paths = {
        key: _resolve_config_path(value, base_dir)
        for key, value in config.get("output_paths", {}).items()
    }
    properties = set(config.get("properties", []))
    property_options = config.get("property_options", {})
    surface_settings = config.get("surface_settings", {})
    sampling = config.get("sampling", {"mode": "full"})
    sampling_settings = _legacy_sampling_settings(sampling)

    return {
        "fileNameTable": [
            [
                str(_resolve_config_path(input_config["path"], base_dir)),
                str(input_config.get("voxel_size", 1.0)),
            ]
            for input_config in inputs
        ],
        "cornerTable": sampling_settings["cornerTable"],
        "TiffSavePath": str(output_paths.get("tiff", output_dir / "tiff")),
        "VoxelSavePath": str(output_paths.get("dat", output_dir / "voxels")),
        "StlSavePath": str(output_paths.get("stl", output_dir / "stl")),
        "PropertySavePath": str(output_paths.get("properties", output_dir / "properties.txt")),
        "PropertySaveFlags": {
            "MinMax": "min_extents" in properties or "max_extents" in properties,
            "SurfArea": "surface_area" in properties,
            "ClosedVolume": "closed_volume" in properties,
            "VolbyArea": "volume_by_area" in properties,
            "Porosity": "porosity" in properties,
            "FiberDiameter": "fiber_diameter" in properties,
            "FiberDiamSphere": str(property_options.get("fiber_diam_sphere", "")),
            "PoreDistribution": "pore_distribution" in properties,
            "PoreDistriDiamSphere": str(property_options.get("pore_dist_sphere", "")),
            "FiberLength": "fiber_length" in properties,
            "FiberAngle": "fiber_angle" in properties,
            "FiberAnglePlane": str(property_options.get("fiber_angle_plane", "XY")),
        },
        "Laplacian": bool(surface_settings.get("laplacianFlag")),
        "LaplacianIter": _optional_text(surface_settings.get("laplacian_iter")),
        "ScreenedPoisson": bool(surface_settings.get("ScreenedPoissonFlag")),
        "ScreenedPoissonIter": _optional_text(surface_settings.get("ScreenedPoisson_iter")),
        "RemoveIslands": bool(surface_settings.get("RemoveIslandsFlag")),
        "VoxelLength": sampling_settings["VoxelLength"],
        "VolumeLength": sampling_settings["VolumeLength"],
        "VolumeLengthCorner": sampling_settings["VolumeLengthCorner"],
        "TiffSave": "tiff" in outputs,
        "VoxelSave": "dat" in outputs,
        "StlSave": "stl" in outputs,
        "PropertySave": "properties" in outputs,
    }


def _parse_input_rows(rows):
    if not rows:
        raise GuiAdapterError("Please add at least one file with its voxel size.")

    filenames = []
    filevoxels = []
    for index, row in enumerate(rows, start=1):
        if row is None or len(row) != 2 or row[0] is None or row[1] is None:
            raise GuiAdapterError(f"Row {index}: Missing file name or voxel size.")

        file_path = str(row[0]).strip()
        voxel_size_text = str(row[1]).strip()
        if not Path(file_path).exists():
            raise GuiAdapterError(f"File not found: {file_path}")

        try:
            voxel_size = float(voxel_size_text)
            if voxel_size == 0:
                raise ValueError
        except ValueError as exc:
            raise GuiAdapterError(f"Row {index}: Invalid voxel size. Please enter a number greater than 0.") from exc

        filenames.append(file_path)
        filevoxels.append(voxel_size)

    return filenames, filevoxels


def _resolve_config_path(path, base_dir: Path | None) -> Path:
    path = Path(path)
    if path.is_absolute() or base_dir is None:
        return path
    return base_dir / path


def _legacy_sampling_settings(sampling):
    mode = sampling.get("mode", "full")
    if mode == "corners":
        return {
            "cornerTable": [[str(value) for value in corner] for corner in sampling.get("corners", [])],
            "VoxelLength": "",
            "VolumeLength": "",
            "VolumeLengthCorner": str(_first_size_value(sampling.get("size", ""))),
        }
    if mode == "grid":
        return {
            "cornerTable": [],
            "VoxelLength": str(sampling.get("volume_length", "")),
            "VolumeLength": "0",
            "VolumeLengthCorner": "",
        }
    if mode == "random":
        return {
            "cornerTable": [],
            "VoxelLength": str(sampling.get("volume_length", "")),
            "VolumeLength": str(sampling.get("count", "")),
            "VolumeLengthCorner": "",
        }
    return {
        "cornerTable": [],
        "VoxelLength": "0",
        "VolumeLength": "0",
        "VolumeLengthCorner": "",
    }


def _first_size_value(size):
    if isinstance(size, (list, tuple)):
        return size[0] if size else ""
    return size


def _optional_text(value):
    if value is None:
        return ""
    return str(value)


def _parse_corner_rows(rows):
    corners = []
    for index, row in enumerate(rows, start=1):
        if row is None or len(row) != 3 or any(value is None for value in row):
            raise GuiAdapterError(f"Row {index}: Missing corner values.")

        try:
            corner = tuple(int(str(value).strip()) for value in row)
            if any(value < 0 for value in corner):
                raise ValueError
        except ValueError as exc:
            raise GuiAdapterError(f"Row {index}: Invalid corner values. Please enter integers greater than or equal to 0.") from exc

        corners.append(corner)

    return corners


def _surface_settings(state):
    return {
        "laplacianFlag": bool(state.get("laplacian")),
        "laplacian_iter": int(state.get("laplacian_iter")) if state.get("laplacian") else None,
        "ScreenedPoissonFlag": bool(state.get("screened_poisson")),
        "ScreenedPoisson_iter": int(state.get("screened_poisson_iter")) if state.get("screened_poisson") else None,
        "RemoveIslandsFlag": bool(state.get("remove_islands")),
    }


def _saving_options(state):
    if not any(
        bool(state.get(key))
        for key in ["tiff_save", "voxel_save", "stl_save", "property_save"]
    ):
        raise GuiAdapterError("Please select at least one of the save options (TIFF, Voxel, STL, or Properties).")

    return {
        "tiff_save": bool(state.get("tiff_save")),
        "tiff_path": state.get("tiff_path") if state.get("tiff_save") else None,
        "voxel_save": bool(state.get("voxel_save")),
        "voxel_path": state.get("voxel_path") if state.get("voxel_save") else None,
        "stl_save": bool(state.get("stl_save")),
        "stl_path": state.get("stl_path") if state.get("stl_save") else None,
        "property_save": bool(state.get("property_save")),
        "property_path": state.get("property_path") if state.get("property_save") else None,
        "property_options": {
            "min_max": bool(state.get("min_max")),
            "surf_area": bool(state.get("surf_area")),
            "closed_volume": bool(state.get("closed_volume")),
            "vol_by_area": bool(state.get("vol_by_area")),
            "porosity": bool(state.get("porosity")),
            "fiber_diameter": bool(state.get("fiber_diameter")),
            "fiber_diam_sphere": _optional_required_int(
                state.get("fiber_diam_sphere"),
                enabled=bool(state.get("fiber_diameter")),
                missing_message="Fiber Diameter Sphere value is required when 'Fiber Diameter' is selected.",
                invalid_message="Invalid Fiber Diameter Sphere value. Please enter a valid number.",
            ),
            "pore_distribution": bool(state.get("pore_distribution")),
            "pore_dist_sphere": _optional_required_int(
                state.get("pore_dist_sphere"),
                enabled=bool(state.get("pore_distribution")),
                missing_message="Pore Distribution Sphere value is required when 'Pore Distribution' is selected.",
                invalid_message="Invalid Pore Distribution Sphere value. Please enter a valid number.",
            ),
            "FiberAngle": bool(state.get("fiber_angle")),
            "FiberAnglePlane": state.get("fiber_angle_plane"),
            "FiberLength": bool(state.get("fiber_length")),
        },
    }


def _cropping_flag(active_tab_index):
    flags = ["Regular", "Corners"]
    if active_tab_index >= len(flags):
        return None
    return flags[active_tab_index]


def _config_outputs(saving_options):
    outputs = []
    if saving_options["stl_save"]:
        outputs.append("stl")
    if saving_options["voxel_save"]:
        outputs.append("dat")
    if saving_options["tiff_save"]:
        outputs.append("tiff")
    if saving_options["property_save"]:
        outputs.append("properties")
    return outputs


def _config_properties(property_options):
    supported = {
        "min_max": ("min_extents", "max_extents"),
        "surf_area": "surface_area",
        "closed_volume": "closed_volume",
        "vol_by_area": "volume_by_area",
        "porosity": "porosity",
        "fiber_diameter": "fiber_diameter",
        "pore_distribution": "pore_distribution",
        "FiberAngle": "fiber_angle",
        "FiberLength": "fiber_length",
    }
    properties = []
    for gui_name, config_name in supported.items():
        if not property_options.get(gui_name):
            continue
        if isinstance(config_name, tuple):
            properties.extend(config_name)
        else:
            properties.append(config_name)
    return properties


def _config_property_options(property_options):
    return {
        "fiber_diam_sphere": property_options.get("fiber_diam_sphere"),
        "pore_dist_sphere": property_options.get("pore_dist_sphere"),
        "fiber_angle_plane": property_options.get("FiberAnglePlane", "XY"),
    }


def _config_sampling(state, voxel_size):
    cropping_flag = _cropping_flag(state.get("active_tab_index", 0))
    if cropping_flag == "Regular":
        volume_length = _required_int(state.get("regular_volume_length"), "Please enter both the volume length and the number of volumes.")
        num_volumes = _required_int(state.get("regular_num_volumes"), "Please enter both the volume length and the number of volumes.")
        if volume_length == 0:
            return None
        if num_volumes == 0:
            return {"mode": "grid", "volume_length": volume_length}
        return {"mode": "random", "volume_length": volume_length, "count": num_volumes}

    if cropping_flag == "Corners":
        volume_length = _required_int(state.get("corner_volume_length"), "Please enter the volume length.")
        size = int(volume_length / voxel_size)
        return {
            "mode": "corners",
            "corners": [list(corner) for corner in _parse_corner_rows(state.get("corner_rows", []))],
            "size": size,
        }

    raise GuiAdapterError("Unknown workflow tab selected.")


def _config_output_dir(saving_options):
    roots = []
    if saving_options["tiff_save"]:
        roots.append(_infer_output_root(saving_options["tiff_path"], {"tiff"}))
    if saving_options["voxel_save"]:
        roots.append(_infer_output_root(saving_options["voxel_path"], {"voxel", "voxels"}))
    if saving_options["stl_save"]:
        roots.append(_infer_output_root(saving_options["stl_path"], {"stl"}))
    if saving_options["property_save"]:
        roots.append(_infer_property_root(saving_options["property_path"]))

    resolved_roots = [Path(root).expanduser() for root in roots if root not in (None, "")]
    if not resolved_roots:
        return "."

    first = resolved_roots[0]
    return str(first)


def _config_output_paths(saving_options):
    output_paths = {}
    if saving_options["tiff_save"] and saving_options["tiff_path"] not in (None, ""):
        output_paths["tiff"] = saving_options["tiff_path"]
    if saving_options["voxel_save"] and saving_options["voxel_path"] not in (None, ""):
        output_paths["dat"] = saving_options["voxel_path"]
    if saving_options["stl_save"] and saving_options["stl_path"] not in (None, ""):
        output_paths["stl"] = saving_options["stl_path"]
    if saving_options["property_save"] and saving_options["property_path"] not in (None, ""):
        output_paths["properties"] = saving_options["property_path"]
    return output_paths


def _infer_output_root(path, conventional_names):
    if path in (None, ""):
        return ""
    path = Path(path)
    if path.name.lower() in conventional_names:
        return path.parent
    return path


def _infer_property_root(path):
    if path in (None, ""):
        return ""
    path = Path(path)
    if path.suffix:
        return path.parent
    return path


def _required_int(value, missing_message):
    if value is None or str(value).strip() == "":
        raise GuiAdapterError(missing_message)
    return int(value)


def _optional_required_int(value, *, enabled, missing_message, invalid_message):
    if not enabled:
        return None
    if value is None or str(value).strip() == "":
        raise GuiAdapterError(missing_message)
    try:
        return int(value)
    except ValueError as exc:
        raise GuiAdapterError(invalid_message) from exc
