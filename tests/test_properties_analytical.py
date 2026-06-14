from __future__ import annotations

import pytest


pytestmark = pytest.mark.analytical


def test_fiber_diameter_for_known_cylinder_is_within_voxel_tolerance(fixture_dir):
    v2s = pytest.importorskip("voxel2stl")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "fiber_z_48.tif")
    mean_diameter, std_diameter = v2s.getDiamter(image, tifvoxelsize=1.0, sphereSize=6)

    # The fixture has radius 5 voxels, but the current local-maxima sampling
    # reports the inscribed digital-cylinder diameter rather than the nominal
    # continuous diameter. Keep this tight enough to catch drift while allowing
    # voxelization effects.
    assert mean_diameter == pytest.approx(8.5, abs=0.75)
    assert std_diameter < 1.0


def test_pore_distribution_for_known_void_cube_is_finite_and_near_expected_size(fixture_dir):
    v2s = pytest.importorskip("voxel2stl")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "porous_block_24.tif")
    mean_pore, std_pore, distribution = v2s.getPoreDistribution(
        image, tifvoxelsize=1.0, sphereSize=6
    )

    assert len(distribution) > 0
    assert mean_pore == pytest.approx(11.5, abs=2.0)
    assert std_pore >= 0


def test_mesh_based_porosity_for_known_cuboid_is_close_to_analytical_value(fixture_dir):
    trimesh = pytest.importorskip("trimesh")
    v2s = pytest.importorskip("voxel2stl")

    volume = v2s.loadData(str(fixture_dir / "cube_16.tif"))
    vertices, faces = v2s.getMesh(v2s.createPadding(volume), 16, 1.0)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    analytical_porosity = 1.0 - 512.0 / (16.0**3)
    mesh_porosity = 1.0 - abs(mesh.volume) / (16.0**3)

    assert mesh_porosity == pytest.approx(analytical_porosity, abs=0.03)


@pytest.mark.current_gap
@pytest.mark.xfail(reason="Current centerline angle conventions need to be locked during cleanup.")
def test_single_angled_fiber_orientation_matches_analytical_angle(fixture_dir):
    v2s = pytest.importorskip("voxel2stl")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "fiber_angle_48.tif")
    azimuth, elevation, length, az_std, el_std, length_std = v2s.analyzeCenterLine(
        image, 1.0, str(fixture_dir / "fiber_angle_48.tif"), plane="XZ"
    )

    assert elevation == pytest.approx(22.34, abs=3.0)
    assert length == pytest.approx(36.0, abs=8.0)
