from __future__ import annotations

import shutil
import subprocess
import sys

import pytest


pytestmark = [pytest.mark.mpi, pytest.mark.analytical]


def test_mpi_environment_is_discoverable():
    if shutil.which("mpirun") is None:
        pytest.skip("mpirun is not installed")
    pytest.importorskip("mpi4py")


def test_mpi_tiny_fixture_matches_serial_contract(repo_root, fixture_dir, tmp_path):
    pytest.importorskip("mpi4py")
    if shutil.which("mpirun") is None:
        pytest.skip("mpirun is not installed")

    result = subprocess.run(
        [
            "mpirun",
            "-n",
            "2",
            sys.executable,
            "-m",
            "hermes",
            "mpi",
            "--input",
            str(fixture_dir / "cube_16.tif"),
            "--voxel-size",
            "1.0",
            "--output",
            str(tmp_path),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Completed 1 volumes" in result.stdout
    assert len(list((tmp_path / "stl").glob("*.stl"))) == 1
    assert (tmp_path / "properties.txt").exists()
