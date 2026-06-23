from __future__ import annotations

import json
import subprocess
import sys

import pytest

from hermes.io import load_volume
from hermes.sampling import grid_specs, random_specs
from hermes.workflow import run_config


def _write_quickstart_config(path, output_dir="output"):
    config = {
        "name": "config_cube",
        "input": {
            "path": "input/config_cube.tif",
            "voxel_size": 1.0,
            "generate": {
                "kind": "binary_cube",
                "shape": [16, 16, 16],
                "bounds": [[4, 12], [4, 12], [4, 12]],
            },
        },
        "output_dir": output_dir,
        "outputs": ["stl", "dat", "properties"],
        "properties": ["surface_area", "closed_volume", "volume_by_area", "porosity"],
    }
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config


def test_run_config_writes_known_cube_outputs(tmp_path):
    config_path = tmp_path / "config.json"
    _write_quickstart_config(config_path)

    result = run_config(config_path)

    assert result["name"] == "config_cube"
    assert result["properties"]["closed_volume"] == pytest.approx(512.0, abs=80.0)
    assert result["properties"]["porosity"] == pytest.approx(1 - 512 / 16**3, abs=0.03)

    output = tmp_path / "output"
    assert (tmp_path / "input" / "config_cube.tif").exists()
    assert (output / "stl" / "config_cube.stl").stat().st_size > 0
    assert (output / "properties.txt").exists()

    dat_volume = load_volume(output / "voxels" / "config_cube.dat")
    assert dat_volume.shape == (18, 18, 18)
    assert int(dat_volume.sum()) == 512


def test_python_module_run_entrypoint_uses_json_config(tmp_path):
    config_path = tmp_path / "config.json"
    _write_quickstart_config(config_path)

    result = subprocess.run(
        [sys.executable, "-m", "hermes", "run", str(config_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "config_cube" in result.stdout
    assert (tmp_path / "output" / "stl" / "config_cube.stl").stat().st_size > 0
    assert (tmp_path / "output" / "voxels" / "config_cube.dat").exists()
    assert (tmp_path / "output" / "properties.txt").exists()


def test_config_runner_explicit_crop_preserves_known_tiff_content(tmp_path):
    config_path = tmp_path / "crop_config.json"
    config = {
        "name": "cropped_cube",
        "input": {
            "path": "input/crop_source.tif",
            "voxel_size": 1.0,
            "generate": {
                "kind": "binary_cube",
                "shape": [16, 16, 16],
                "bounds": [[4, 12], [4, 12], [4, 12]],
            },
        },
        "crop": {"corner": [4, 4, 4], "size": [8, 8, 8]},
        "output_dir": "crop_output",
        "outputs": ["tiff", "dat", "properties"],
        "properties": ["closed_volume", "porosity"],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    result = run_config(config_path)

    output = tmp_path / "crop_output"
    tiff_volume = load_volume(output / "tiff" / "cropped_cube.tif")
    dat_volume = load_volume(output / "voxels" / "cropped_cube.dat")

    assert tiff_volume.shape == (8, 8, 8)
    assert int(tiff_volume.sum()) == 512
    assert dat_volume.shape == (10, 10, 10)
    assert int(dat_volume.sum()) == 512
    assert result["properties"]["closed_volume"] == pytest.approx(512.0, abs=80.0)
    assert result["properties"]["porosity"] == pytest.approx(0.0, abs=0.03)


def test_sampling_helpers_make_deterministic_grid_and_seeded_random_specs():
    grid = grid_specs((24, 24, 24), voxel_size=1.0, volume_length=12)
    random_a = random_specs((24, 24, 24), voxel_size=1.0, volume_length=12, count=4, seed=123)
    random_b = random_specs((24, 24, 24), voxel_size=1.0, volume_length=12, count=4, seed=123)

    assert len(grid) == 8
    assert grid[0].corner == (0, 0, 0)
    assert grid[-1].corner == (12, 12, 12)
    assert [spec.corner for spec in random_a] == [spec.corner for spec in random_b]
    assert len({spec.corner for spec in random_a}) > 1


def test_config_runner_corner_sampling_writes_one_output_per_corner(tmp_path):
    config_path = tmp_path / "sampling_config.json"
    config = {
        "name": "sampled_cube",
        "input": {
            "path": "input/source.tif",
            "voxel_size": 1.0,
            "generate": {
                "kind": "binary_cube",
                "shape": [24, 24, 24],
                "bounds": [[4, 20], [4, 20], [4, 20]],
            },
        },
        "sampling": {
            "mode": "corners",
            "corners": [[4, 4, 4], [12, 12, 12]],
            "size": [8, 8, 8],
        },
        "output_dir": "sample_output",
        "outputs": ["tiff", "dat", "properties"],
        "properties": ["closed_volume", "porosity"],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    result = run_config(config_path)
    output = tmp_path / "sample_output"

    assert len(result["samples"]) == 2
    assert len(list((output / "tiff").glob("*.tif"))) == 2
    assert len(list((output / "voxels").glob("*.dat"))) == 2
    assert (output / "properties.txt").exists()
