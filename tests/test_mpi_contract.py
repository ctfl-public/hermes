from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from hermes import mpi
from tests.helpers import base_saving_options, base_surface_settings


pytestmark = [pytest.mark.mpi, pytest.mark.analytical]


class OneRankComm:
    def Get_rank(self):
        return 0

    def Get_size(self):
        return 1

    def bcast(self, value, root=0):
        return value

    def gather(self, value, root=0):
        return [value]


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


def test_mpi_framework_processes_corner_samples_with_workflow_backend(tmp_output, fixture_dir):
    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = ([str(fixture_dir / "small_primary_0.tif")], [1.0], [(0, 0, 0), (6, 6, 6)], 12)

    results = mpi.run_sample_mpi("Corners", crop, base_surface_settings(), saving, comm=OneRankComm())

    assert len(results) == 2
    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 2
