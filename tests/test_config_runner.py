from __future__ import annotations

import json
import subprocess
import sys

import pytest

from hermes.io import load_volume
from hermes.pipeline import run_pipeline_config


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


def test_run_pipeline_config_writes_known_cube_outputs(tmp_path):
    config_path = tmp_path / "config.json"
    _write_quickstart_config(config_path)

    result = run_pipeline_config(config_path)

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

    result = run_pipeline_config(config_path)

    output = tmp_path / "crop_output"
    tiff_volume = load_volume(output / "tiff" / "cropped_cube.tif")
    dat_volume = load_volume(output / "voxels" / "cropped_cube.dat")

    assert tiff_volume.shape == (8, 8, 8)
    assert int(tiff_volume.sum()) == 512
    assert dat_volume.shape == (10, 10, 10)
    assert int(dat_volume.sum()) == 512
    assert result["properties"]["closed_volume"] == pytest.approx(512.0, abs=80.0)
    assert result["properties"]["porosity"] == pytest.approx(0.0, abs=0.03)
