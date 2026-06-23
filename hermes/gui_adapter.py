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
