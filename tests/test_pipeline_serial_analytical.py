from __future__ import annotations

import pytest

from tests.helpers import base_saving_options, base_surface_settings, read_property_table


pytestmark = pytest.mark.analytical


def test_serial_pipeline_writes_properties_for_known_cube(tmp_output, fixture_dir):
    v2s = pytest.importorskip("voxel2stl")

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

    v2s.voxel2stl("Regular", crop, base_surface_settings(), saving)

    header, rows = read_property_table(tmp_output / "properties.txt")
    assert len(rows) == 1
    for name in ["StlName", "SurfaceArea", "ClosedVolume", "Volume/SurfaceArea", "Porosity"]:
        assert name in header
    porosity = float(rows[0][header.index("Porosity")])
    assert porosity == pytest.approx(1.0 - 512.0 / (16.0**3), abs=0.03)
    assert len(list((tmp_output / "stl").glob("*.stl"))) == 1


def test_serial_pipeline_corner_sampling_writes_one_output_per_corner(tmp_output, fixture_dir):
    v2s = pytest.importorskip("voxel2stl")

    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = ([str(fixture_dir / "small_primary_0.tif")], [1.0], [(0, 0, 0), (6, 6, 6)], 12)

    v2s.voxel2stl("Corners", crop, base_surface_settings(), saving)

    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 2


def test_random_sampling_small_jobs_write_requested_output_count(tmp_output, fixture_dir):
    """Random sampling should produce one output per requested sub-volume."""
    v2s = pytest.importorskip("voxel2stl")

    saving = base_saving_options(tmp_output, tiff_save=True)
    crop = ([str(fixture_dir / "solid_primary_24.tif")], [1.0], 4, 12)

    v2s.voxel2stl("Regular", crop, base_surface_settings(), saving)

    assert len(list((tmp_output / "tiff").glob("*.tif"))) == 4
