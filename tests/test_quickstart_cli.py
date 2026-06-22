from __future__ import annotations

import csv
import subprocess
import sys

import pytest

from hermes.cli import main
from hermes.io import load_volume


def test_quickstart_cli_writes_known_cube_outputs(tmp_path, capsys):
    output = tmp_path / "quickstart"

    assert main(["quickstart", "--output", str(output)]) == 0

    captured = capsys.readouterr()
    assert "quickstart_cube" in captured.out

    input_tiff = output / "input" / "quickstart_cube.tif"
    stl_path = output / "stl" / "quickstart_cube.stl"
    dat_path = output / "voxels" / "quickstart_cube.dat"
    properties_path = output / "properties.txt"

    assert input_tiff.exists()
    assert stl_path.exists()
    assert stl_path.stat().st_size > 0
    assert dat_path.exists()
    assert properties_path.exists()

    dat_volume = load_volume(dat_path)
    assert dat_volume.shape == (18, 18, 18)
    assert int(dat_volume.sum()) == 512

    with properties_path.open(newline="") as file_obj:
        rows = list(csv.reader(file_obj, delimiter="\t"))

    header = rows[0]
    values = rows[1]
    assert header == ["WorkspaceName", "surface_area", "closed_volume", "volume_by_area", "porosity"]
    assert values[0] == "quickstart_cube"
    assert float(values[2]) == pytest.approx(512.0, abs=80.0)
    assert float(values[4]) == pytest.approx(1 - 512 / 16**3, abs=0.03)


def test_python_module_quickstart_entrypoint_runs(tmp_path):
    output = tmp_path / "module-quickstart"

    result = subprocess.run(
        [sys.executable, "-m", "hermes", "quickstart", "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "quickstart_cube" in result.stdout
    assert (output / "input" / "quickstart_cube.tif").exists()
    assert (output / "stl" / "quickstart_cube.stl").stat().st_size > 0
    assert (output / "voxels" / "quickstart_cube.dat").exists()
    assert (output / "properties.txt").exists()
