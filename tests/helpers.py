from __future__ import annotations

from pathlib import Path


def base_surface_settings():
    return {
        "laplacianFlag": False,
        "laplacian_iter": None,
        "ScreenedPoissonFlag": False,
        "ScreenedPoisson_iter": None,
        "RemoveIslandsFlag": False,
    }


def base_saving_options(output_dir: Path, **overrides):
    options = {
        "tiff_save": False,
        "tiff_path": str(output_dir / "tiff"),
        "voxel_save": False,
        "voxel_path": str(output_dir / "voxel"),
        "stl_save": False,
        "stl_path": str(output_dir / "stl"),
        "property_save": False,
        "property_path": str(output_dir / "properties.txt"),
        "property_options": {
            "min_max": False,
            "surf_area": False,
            "closed_volume": False,
            "vol_by_area": False,
            "porosity": False,
            "fiber_diameter": False,
            "fiber_diam_sphere": 6,
            "pore_distribution": False,
            "pore_dist_sphere": 6,
            "FiberAngle": False,
            "FiberAnglePlane": "XY",
            "FiberLength": False,
        },
    }
    for key, value in overrides.items():
        if key == "property_options":
            options["property_options"].update(value)
        else:
            options[key] = value
    return options


def read_property_table(path: Path):
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    header = lines[0].split("\t")
    rows = [line.split("\t") for line in lines[1:]]
    return header, rows
