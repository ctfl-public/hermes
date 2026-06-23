from __future__ import annotations

import pytest

from hermes.io import load_volume
from hermes import serial
from tests.helpers import base_saving_options, base_surface_settings, read_property_table


pytestmark = pytest.mark.analytical


def test_serial_pipeline_writes_properties_for_known_cube(tmp_output, fixture_dir):
    saving = base_saving_options(
        tmp_output,
        stl_save=True,
        property_save=True,
        property_options={
            "surf_area": True,
            "closed_volume": True,
            "vol_by_area": True,
            "porosity": True,
        },
    )
    crop = ([str(fixture_dir / "cube_16.tif")], [1.0], 0, 0)

    serial.run_serial("Regular", crop, base_surface_settings(), saving)

    header, rows = read_property_table(tmp_output / "properties.txt")
    assert len(rows) == 1
    for name in ["StlName", "SurfaceArea", "ClosedVolume", "Volume/SurfaceArea", "Porosity"]:
        assert name in header
    porosity = float(rows[0][header.index("Porosity")])
    assert porosity == pytest.approx(1.0 - 512.0 / (16.0**3), abs=0.03)
    assert len(list((tmp_output / "stl").glob("*.stl"))) == 1


def test_serial_pipeline_exported_tiff_and_dat_preserve_known_crop_content(tmp_output, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")

    saving = base_saving_options(tmp_output, tiff_save=True, voxel_save=True)
    crop = ([str(fixture_dir / "cube_16.tif")], [1.0], [(3, 5, 4)], 8)

    serial.run_serial("Corners", crop, base_surface_settings(), saving)

    exported_tiff = next((tmp_output / "tiff").glob("*.tif"))
    exported_dat = next((tmp_output / "voxel").glob("*.dat"))
    tiff_volume = tiff.imread(exported_tiff)
    dat_volume = load_volume(exported_dat)

    assert tiff_volume.shape == (8, 8, 8)
    assert int(np.count_nonzero(tiff_volume)) == 8 * 8 * 8
    assert np.array_equal((tiff_volume > 0).astype(int), dat_volume[1:-1, 1:-1, 1:-1])


def test_serial_pipeline_corner_sampling_writes_one_output_per_corner(tmp_output, fixture_dir):
    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = ([str(fixture_dir / "small_primary_0.tif")], [1.0], [(0, 0, 0), (6, 6, 6)], 12)

    serial.run_serial("Corners", crop, base_surface_settings(), saving)

    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 2


def test_random_sampling_small_jobs_write_requested_output_count(tmp_output, fixture_dir):
    """Random sampling should produce one output per requested sub-volume."""
    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = ([str(fixture_dir / "solid_primary_24.tif")], [1.0], 4, 12)

    serial.run_serial("Regular", crop, base_surface_settings(), saving)

    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 4


def test_serial_pipeline_writes_complete_property_schema_for_fiber_fixture(tmp_output, fixture_dir):
    saving = base_saving_options(
        tmp_output,
        property_save=True,
        property_options={
            "min_max": True,
            "surf_area": True,
            "closed_volume": True,
            "vol_by_area": True,
            "porosity": True,
            "fiber_diameter": True,
            "fiber_diam_sphere": 6,
            "pore_distribution": True,
            "pore_dist_sphere": 6,
            "FiberAngle": True,
            "FiberAnglePlane": "XY",
            "FiberLength": True,
        },
    )
    crop = ([str(fixture_dir / "fiber_angle_48.tif")], [1.0], 0, 0)

    serial.run_serial("Regular", crop, base_surface_settings(), saving)

    header, rows = read_property_table(tmp_output / "properties.txt")
    expected_columns = [
        "StlName",
        "MinExtentsX",
        "MinExtentsY",
        "MinExtentsZ",
        "MaxExtentsX",
        "MaxExtentsY",
        "MaxExtentsZ",
        "SurfaceArea",
        "ClosedVolume",
        "Volume/SurfaceArea",
        "Porosity",
        "fiber_diameter_Mean",
        "fiber_diameter_Std",
        "meanPore",
        "stdPore",
        "poreDistribution",
        "ReferencePlane",
        "MeanAzimuthAngle",
        "StDAzimuthAngle",
        "MeanElevationAngle",
        "StDElevationAngle",
        "MeanLength",
        "StDLength",
    ]

    assert header == expected_columns
    assert len(rows) == 1
    assert len(rows[0]) == len(header)
    assert float(rows[0][header.index("fiber_diameter_Mean")]) > 0.0
    assert float(rows[0][header.index("fiber_diameter_Std")]) >= 0.0
    assert float(rows[0][header.index("Porosity")]) < 1.0


def test_multi_primary_random_sampling_distributes_outputs_across_input_volumes(
    monkeypatch, tmp_output, fixture_dir
):
    filenames = [str(fixture_dir / f"small_primary_{idx}.tif") for idx in range(3)]
    sequence = iter(filenames * 2)
    monkeypatch.setattr(serial.random, "choice", lambda values: next(sequence))
    monkeypatch.setattr(serial.random, "randint", lambda lower, upper: 4)

    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = (filenames, [1.0, 1.0, 1.0], 6, 12)

    serial.run_serial("Regular", crop, base_surface_settings(), saving)

    outputs = sorted(path.name for path in (tmp_output / "tiff").glob("*.tif"))
    assert len(outputs) == 6
    for idx in range(3):
        assert sum(name.startswith(f"small_primary_{idx}") for name in outputs) == 2


def test_large_random_sampling_uses_local_parallel_dispatch(monkeypatch, tmp_output, fixture_dir):
    submitted = []

    class FakeFuture:
        def __init__(self, result):
            self._result = result

        def result(self):
            return self._result

    class FakeExecutor:
        def __init__(self, max_workers):
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, args):
            submitted.append(args)
            return FakeFuture(f"processed {len(submitted)}")

    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = ([str(fixture_dir / "solid_primary_24.tif")], [1.0], 1001, 12)

    serial.run_serial(
        "Regular",
        crop,
        base_surface_settings(),
        saving,
        executor_class=FakeExecutor,
        as_completed_fn=lambda futures: futures,
    )

    assert len(submitted) == 1001
    assert all(args[-2] == base_surface_settings() for args in submitted)
