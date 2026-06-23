from __future__ import annotations

import csv
import subprocess
import sys

import numpy as np
import pytest

import hermes
from hermes.io import load_volume


def test_public_api_segment_manual_writes_known_mask(fixture_dir, tmp_path):
    output = tmp_path / "manual_mask.tif"

    result = hermes.segment(
        fixture_dir / "grayscale_two_phase_24.tif",
        output,
        method="manual",
        minimum=10000,
        maximum=65535,
    )

    actual = load_volume(output).astype(bool)
    expected = load_volume(fixture_dir / "grayscale_two_phase_mask_24.tif").astype(bool)
    assert np.array_equal(actual, expected)
    assert result.porosity == pytest.approx(1 - np.count_nonzero(expected) / expected.size)


def test_public_api_mesh_writes_valid_stl_for_known_cube(fixture_dir, tmp_path):
    output = tmp_path / "cube.stl"

    result = hermes.mesh(fixture_dir / "cube_16.tif", output, voxel_size=1.0)

    assert output.exists()
    assert output.stat().st_size > 0
    assert result["vertices"] > 0
    assert result["faces"] > 0
    assert result["is_volume"] is True


def test_public_api_properties_match_known_cube(fixture_dir, tmp_path):
    output = tmp_path / "properties.txt"

    result = hermes.properties(fixture_dir / "cube_16.tif", output, voxel_size=1.0)

    assert result["closed_volume"] == pytest.approx(512.0, abs=80.0)
    assert result["porosity"] == pytest.approx(1 - 512 / 16**3, abs=0.03)

    with output.open(newline="") as file_obj:
        rows = list(csv.reader(file_obj, delimiter="\t"))
    assert rows[0] == ["WorkspaceName", "surface_area", "closed_volume", "volume_by_area", "porosity"]
    assert rows[1][0] == "cube_16.tif"


def test_segment_cli_command_writes_known_mask(fixture_dir, tmp_path):
    output = tmp_path / "mask.tif"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes",
            "segment",
            str(fixture_dir / "grayscale_two_phase_24.tif"),
            str(output),
            "--method",
            "manual",
            "--min",
            "10000",
            "--max",
            "65535",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    actual = load_volume(output).astype(bool)
    expected = load_volume(fixture_dir / "grayscale_two_phase_mask_24.tif").astype(bool)
    assert np.array_equal(actual, expected)


def test_mesh_and_properties_cli_commands_preserve_known_cube_contract(fixture_dir, tmp_path):
    stl_output = tmp_path / "cube.stl"
    property_output = tmp_path / "properties.txt"

    mesh_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes",
            "mesh",
            str(fixture_dir / "cube_16.tif"),
            str(stl_output),
            "--voxel-size",
            "1.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    properties_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes",
            "properties",
            str(fixture_dir / "cube_16.tif"),
            str(property_output),
            "--voxel-size",
            "1.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert mesh_result.returncode == 0, mesh_result.stderr + mesh_result.stdout
    assert properties_result.returncode == 0, properties_result.stderr + properties_result.stdout
    assert stl_output.stat().st_size > 0

    with property_output.open(newline="") as file_obj:
        rows = list(csv.reader(file_obj, delimiter="\t"))
    header = rows[0]
    values = rows[1]
    assert float(values[header.index("closed_volume")]) == pytest.approx(512.0, abs=80.0)
    assert float(values[header.index("porosity")]) == pytest.approx(1 - 512 / 16**3, abs=0.03)
