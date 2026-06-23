from __future__ import annotations

import pytest

from hermes.io import load_volume
from hermes.workflow import run_workflow_config
from tests.helpers import base_surface_settings, read_property_table


pytestmark = pytest.mark.analytical


def test_workflow_pipeline_writes_properties_for_known_cube(tmp_output, fixture_dir):
    config = {
        "name": "cube_16",
        "input": {"path": str(fixture_dir / "cube_16.tif"), "voxel_size": 1.0},
        "output_dir": str(tmp_output),
        "outputs": ["stl", "properties"],
        "properties": ["surface_area", "closed_volume", "volume_by_area", "porosity"],
        "surface_settings": base_surface_settings(),
    }

    result = run_workflow_config(config)

    header, rows = read_property_table(tmp_output / "properties.txt")
    assert len(rows) == 1
    assert header == ["WorkspaceName", "surface_area", "closed_volume", "volume_by_area", "porosity"]
    assert result["properties"]["porosity"] == pytest.approx(1.0 - 512.0 / (16.0**3), abs=0.03)
    assert len(list((tmp_output / "stl").glob("*.stl"))) == 1


def test_workflow_pipeline_exported_tiff_and_dat_preserve_known_crop_content(tmp_output, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    config = {
        "name": "cube_16",
        "input": {"path": str(fixture_dir / "cube_16.tif"), "voxel_size": 1.0},
        "output_dir": str(tmp_output),
        "output_paths": {
            "tiff": str(tmp_output / "tiff"),
            "dat": str(tmp_output / "voxel"),
        },
        "outputs": ["tiff", "dat"],
        "properties": [],
        "sampling": {
            "mode": "corners",
            "corners": [[3, 5, 4]],
            "size": 8,
        },
        "surface_settings": base_surface_settings(),
    }

    run_workflow_config(config)

    exported_tiff = next((tmp_output / "tiff").glob("*.tif"))
    exported_dat = next((tmp_output / "voxel").glob("*.dat"))
    tiff_volume = tiff.imread(exported_tiff)
    dat_volume = load_volume(exported_dat)

    assert tiff_volume.shape == (8, 8, 8)
    assert int(np.count_nonzero(tiff_volume)) == 8 * 8 * 8
    assert np.array_equal((tiff_volume > 0).astype(int), dat_volume[1:-1, 1:-1, 1:-1])


def test_workflow_pipeline_corner_sampling_writes_one_output_per_corner(tmp_output, fixture_dir):
    config = {
        "input": {"path": str(fixture_dir / "small_primary_0.tif"), "voxel_size": 1.0},
        "output_dir": str(tmp_output),
        "outputs": ["tiff"],
        "properties": [],
        "sampling": {
            "mode": "corners",
            "corners": [[0, 0, 0], [6, 6, 6]],
            "size": 12,
        },
    }

    result = run_workflow_config(config)

    assert len(result["samples"]) == 2
    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 2


def test_workflow_random_sampling_small_jobs_write_requested_output_count(tmp_output, fixture_dir):
    config = {
        "input": {"path": str(fixture_dir / "solid_primary_24.tif"), "voxel_size": 1.0},
        "output_dir": str(tmp_output),
        "outputs": ["tiff"],
        "properties": [],
        "sampling": {
            "mode": "random",
            "volume_length": 12,
            "count": 4,
            "seed": 7,
        },
    }

    result = run_workflow_config(config)

    assert len(result["samples"]) == 4
    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 4


def test_workflow_pipeline_writes_complete_property_schema_for_fiber_fixture(tmp_output, fixture_dir):
    config = {
        "name": "fiber_angle_48",
        "input": {"path": str(fixture_dir / "fiber_angle_48.tif"), "voxel_size": 1.0},
        "output_dir": str(tmp_output),
        "outputs": ["properties"],
        "properties": [
            "min_extents",
            "max_extents",
            "surface_area",
            "closed_volume",
            "volume_by_area",
            "porosity",
            "fiber_diameter",
            "pore_distribution",
            "fiber_angle",
            "fiber_length",
        ],
        "property_options": {
            "fiber_diam_sphere": 6,
            "pore_dist_sphere": 6,
            "fiber_angle_plane": "XY",
        },
        "surface_settings": base_surface_settings(),
    }

    run_workflow_config(config)

    header, rows = read_property_table(tmp_output / "properties.txt")
    expected_columns = [
        "WorkspaceName",
        "surface_area",
        "closed_volume",
        "volume_by_area",
        "porosity",
        "min_extents",
        "max_extents",
        "fiber_diameter_mean",
        "fiber_diameter_std",
        "fiber_diameter_distribution",
        "pore_size_mean",
        "pore_size_std",
        "pore_size_distribution",
        "azimuth_mean",
        "azimuth_std",
        "elevation_mean",
        "elevation_std",
        "length_mean",
        "length_std",
    ]

    assert header == expected_columns
    assert len(rows) == 1
    assert len(rows[0]) == len(header)
    assert float(rows[0][header.index("fiber_diameter_mean")]) > 0.0
    assert float(rows[0][header.index("fiber_diameter_std")]) >= 0.0
    assert float(rows[0][header.index("porosity")]) < 1.0


def test_multi_primary_random_sampling_distributes_total_outputs_across_input_volumes(tmp_output, fixture_dir):
    inputs = [
        {
            "path": str(fixture_dir / "solid_primary_24.tif"),
            "voxel_size": 1.0,
            "name": f"primary_{idx}",
        }
        for idx in range(3)
    ]
    config = {
        "inputs": inputs,
        "output_dir": str(tmp_output),
        "outputs": ["tiff"],
        "properties": [],
        "sampling": {
            "mode": "random",
            "volume_length": 12,
            "count": 6,
            "count_mode": "total",
            "seed": 0,
        },
    }

    result = run_workflow_config(config)

    outputs = sorted(path.name for path in (tmp_output / "tiff").glob("*.tif"))
    assert len(result["results"]) == 3
    assert sum(len(item["samples"]) for item in result["results"]) == 6
    assert len(outputs) == 6
    assert any(name.startswith("primary_0") for name in outputs)
    assert any(name.startswith("primary_1") for name in outputs)
    assert any(name.startswith("primary_2") for name in outputs)


def test_workflow_random_sampling_large_jobs_write_requested_output_count(tmp_output, fixture_dir):
    config = {
        "input": {"path": str(fixture_dir / "solid_primary_24.tif"), "voxel_size": 1.0},
        "output_dir": str(tmp_output),
        "outputs": ["tiff"],
        "properties": [],
        "sampling": {
            "mode": "random",
            "volume_length": 12,
            "count": 12,
            "seed": 23,
        },
    }

    result = run_workflow_config(config)

    assert len(result["samples"]) == 12
    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 12
