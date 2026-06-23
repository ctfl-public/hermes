from __future__ import annotations

import pytest

from hermes.gui_adapter import GuiAdapterError, build_serial_run_arguments, build_workflow_config


pytestmark = pytest.mark.gui


def base_gui_state(fixture_dir, tmp_path, **overrides):
    state = {
        "input_rows": [(str(fixture_dir / "cube_16.tif"), "1.0")],
        "corner_rows": [],
        "active_tab_index": 0,
        "laplacian": True,
        "laplacian_iter": "2",
        "screened_poisson": False,
        "screened_poisson_iter": "",
        "remove_islands": False,
        "tiff_save": True,
        "tiff_path": str(tmp_path / "tiff"),
        "voxel_save": False,
        "voxel_path": "",
        "stl_save": False,
        "stl_path": "",
        "property_save": True,
        "property_path": str(tmp_path / "properties.txt"),
        "min_max": False,
        "surf_area": True,
        "closed_volume": False,
        "vol_by_area": False,
        "porosity": True,
        "fiber_diameter": False,
        "fiber_diam_sphere": "",
        "pore_distribution": False,
        "pore_dist_sphere": "",
        "fiber_angle": False,
        "fiber_angle_plane": "XY",
        "fiber_length": False,
        "regular_volume_length": "8",
        "regular_num_volumes": "0",
        "corner_volume_length": "",
    }
    state.update(overrides)
    return state


def test_gui_adapter_builds_regular_serial_arguments(fixture_dir, tmp_path):
    cropping_flag, crop_settings, surface_settings, saving_options = build_serial_run_arguments(
        base_gui_state(fixture_dir, tmp_path)
    )

    filenames, filevoxels, num_volumes, volume_length = crop_settings
    assert cropping_flag == "Regular"
    assert filenames == [str(fixture_dir / "cube_16.tif")]
    assert filevoxels == [1.0]
    assert num_volumes == 0
    assert volume_length == 8
    assert surface_settings == {
        "laplacianFlag": True,
        "laplacian_iter": 2,
        "ScreenedPoissonFlag": False,
        "ScreenedPoisson_iter": None,
        "RemoveIslandsFlag": False,
    }
    assert saving_options["tiff_save"] is True
    assert saving_options["property_save"] is True
    assert saving_options["property_options"]["surf_area"] is True
    assert saving_options["property_options"]["porosity"] is True


def test_gui_adapter_builds_corner_serial_arguments(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        active_tab_index=1,
        corner_rows=[("0", "0", "0"), ("4", "5", "6")],
        corner_volume_length="12",
    )

    cropping_flag, crop_settings, _, _ = build_serial_run_arguments(state)

    filenames, filevoxels, corners, volume_length = crop_settings
    assert cropping_flag == "Corners"
    assert filenames == [str(fixture_dir / "cube_16.tif")]
    assert filevoxels == [1.0]
    assert corners == [(0, 0, 0), (4, 5, 6)]
    assert volume_length == 12


def test_gui_adapter_rejects_missing_outputs(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        tiff_save=False,
        voxel_save=False,
        stl_save=False,
        property_save=False,
    )

    with pytest.raises(GuiAdapterError, match="Please select at least one"):
        build_serial_run_arguments(state)


def test_gui_adapter_rejects_invalid_corner_row(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        active_tab_index=1,
        corner_rows=[("0", "-1", "0")],
        corner_volume_length="12",
    )

    with pytest.raises(GuiAdapterError, match="Invalid corner values"):
        build_serial_run_arguments(state)


def test_gui_adapter_exports_regular_workflow_config(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        tiff_path=str(tmp_path / "output" / "tiff"),
        property_path=str(tmp_path / "output" / "properties.txt"),
    )

    config = build_workflow_config(state)

    assert config == {
        "name": "cube_16",
        "input": {
            "path": str(fixture_dir / "cube_16.tif"),
            "voxel_size": 1.0,
        },
        "output_dir": str(tmp_path / "output"),
        "output_paths": {
            "tiff": str(tmp_path / "output" / "tiff"),
            "properties": str(tmp_path / "output" / "properties.txt"),
        },
        "outputs": ["tiff", "properties"],
        "properties": ["surface_area", "porosity"],
        "property_options": {
            "fiber_diam_sphere": None,
            "pore_dist_sphere": None,
            "fiber_angle_plane": "XY",
        },
        "surface_settings": {
            "laplacianFlag": True,
            "laplacian_iter": 2,
            "ScreenedPoissonFlag": False,
            "ScreenedPoisson_iter": None,
            "RemoveIslandsFlag": False,
        },
        "sampling": {"mode": "grid", "volume_length": 8},
    }


def test_gui_adapter_exports_corner_workflow_config(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        active_tab_index=1,
        corner_rows=[("0", "0", "0"), ("4", "5", "6")],
        corner_volume_length="12",
        tiff_path=str(tmp_path / "output" / "tiff"),
        property_path=str(tmp_path / "output" / "properties.txt"),
    )

    config = build_workflow_config(state)

    assert config["sampling"] == {
        "mode": "corners",
        "corners": [[0, 0, 0], [4, 5, 6]],
        "size": 12,
    }
    assert config["output_dir"] == str(tmp_path / "output")


def test_gui_adapter_exports_separate_output_paths(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        tiff_path=str(tmp_path / "images"),
        voxel_save=True,
        voxel_path=str(tmp_path / "voxel-data"),
        stl_save=True,
        stl_path=str(tmp_path / "meshes"),
        property_path=str(tmp_path / "tables" / "props.txt"),
    )

    config = build_workflow_config(state)

    assert config["output_paths"] == {
        "tiff": str(tmp_path / "images"),
        "dat": str(tmp_path / "voxel-data"),
        "stl": str(tmp_path / "meshes"),
        "properties": str(tmp_path / "tables" / "props.txt"),
    }


def test_gui_adapter_exports_advanced_property_config(fixture_dir, tmp_path):
    state = base_gui_state(
        fixture_dir,
        tmp_path,
        min_max=True,
        fiber_diameter=True,
        fiber_diam_sphere="6",
        pore_distribution=True,
        pore_dist_sphere="6",
        fiber_angle=True,
        fiber_angle_plane="XZ",
        fiber_length=True,
        tiff_path=str(tmp_path / "output" / "tiff"),
        property_path=str(tmp_path / "output" / "properties.txt"),
    )

    config = build_workflow_config(state)

    assert config["properties"] == [
        "min_extents",
        "max_extents",
        "surface_area",
        "porosity",
        "fiber_diameter",
        "pore_distribution",
        "fiber_angle",
        "fiber_length",
    ]
    assert config["property_options"] == {
        "fiber_diam_sphere": 6,
        "pore_dist_sphere": 6,
        "fiber_angle_plane": "XZ",
    }
