from __future__ import annotations

import pytest

from hermes.centerlines import analyze_centerline
from hermes.io import load_volume
from hermes.mesh import create_padding, generate_mesh
from hermes.properties import fiber_diameter_distribution, pore_distribution


pytestmark = pytest.mark.analytical


def test_fiber_diameter_for_known_cylinder_is_within_voxel_tolerance(fixture_dir):
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "fiber_z_48.tif")
    mean_diameter, std_diameter, _ = fiber_diameter_distribution(image, voxel_size=1.0, sphere_size=6)

    # The fixture has radius 5 voxels, but the current local-maxima sampling
    # reports the inscribed digital-cylinder diameter rather than the nominal
    # continuous diameter. Keep this tight enough to catch drift while allowing
    # voxelization effects.
    assert mean_diameter == pytest.approx(8.5, abs=0.75)
    assert std_diameter < 1.0


def test_pore_distribution_for_known_void_cube_is_finite_and_near_expected_size(fixture_dir):
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "porous_block_24.tif")
    mean_pore, std_pore, distribution = pore_distribution(image, voxel_size=1.0, sphere_size=6)

    assert len(distribution) > 0
    assert mean_pore == pytest.approx(11.5, abs=2.0)
    assert std_pore >= 0


def test_mesh_based_porosity_for_known_cuboid_is_close_to_analytical_value(fixture_dir):
    trimesh = pytest.importorskip("trimesh")

    volume = load_volume(fixture_dir / "cube_16.tif")
    vertices, faces = generate_mesh(create_padding(volume), 1.0)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    analytical_porosity = 1.0 - 512.0 / (16.0**3)
    mesh_porosity = 1.0 - abs(mesh.volume) / (16.0**3)

    assert mesh_porosity == pytest.approx(analytical_porosity, abs=0.03)


def test_single_angled_fiber_orientation_matches_current_reference_plane_convention(fixture_dir):
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "fiber_angle_48.tif")
    azimuth, elevation, length, az_std, el_std, length_std = analyze_centerline(
        image, 1.0, str(fixture_dir / "fiber_angle_48.tif"), plane="XZ"
    )

    assert azimuth == pytest.approx(90.0 - 22.34, abs=3.0)
    assert elevation == pytest.approx(0.0, abs=3.0)
    assert length == pytest.approx(36.0, abs=8.0)
