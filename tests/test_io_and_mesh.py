from __future__ import annotations

import pytest

from hermes.io import load_volume, write_chen_format
from hermes.mesh import create_padding, generate_mesh


pytestmark = pytest.mark.analytical


def test_load_tiff_preserves_known_cube_shape_and_material_count(fixture_dir):
    np = pytest.importorskip("numpy")

    tiff_volume = load_volume(fixture_dir / "cube_16.tif")

    assert tiff_volume.shape == (16, 16, 16)
    assert int(np.count_nonzero(tiff_volume)) == 8 * 8 * 8


def test_load_tiff_and_dat_represent_same_known_cube(fixture_dir):
    np = pytest.importorskip("numpy")

    tiff_volume = load_volume(fixture_dir / "cube_16.tif")
    dat_volume = load_volume(fixture_dir / "cube_16.dat")

    assert dat_volume.shape == tiff_volume.shape
    assert np.array_equal((tiff_volume > 0).astype(int), dat_volume)


def test_padding_adds_one_voxel_border_and_preserves_material_count(fixture_dir):
    np = pytest.importorskip("numpy")

    volume = load_volume(fixture_dir / "cube_16.tif")
    padded = create_padding(volume)

    assert padded.shape == (18, 18, 18)
    assert int(np.count_nonzero(padded)) == 8 * 8 * 8
    assert np.all(padded[0, :, :] == 0)
    assert np.all(padded[-1, :, :] == 0)
    assert np.all(padded[:, 0, :] == 0)
    assert np.all(padded[:, :, -1] == 0)


def test_marching_cubes_cube_mesh_has_analytical_volume_within_voxel_tolerance(fixture_dir):
    np = pytest.importorskip("numpy")
    trimesh = pytest.importorskip("trimesh")

    volume = load_volume(fixture_dir / "cube_16.tif")
    binary = create_padding(volume)
    vertices, faces = generate_mesh(binary, 1.0)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    assert len(vertices) > 0
    assert len(faces) > 0
    assert mesh.is_watertight
    # The analytical cuboid is 8x8x8 voxels. Marching cubes places the surface
    # on half-voxel interfaces, so allow a small discretization tolerance.
    assert abs(abs(mesh.volume) - 512.0) < 80.0
    assert np.isfinite(mesh.area)


def test_chen_writer_round_trips_known_cube(tmp_path, fixture_dir):
    np = pytest.importorskip("numpy")

    volume = load_volume(fixture_dir / "cube_16.tif")
    out = tmp_path / "cube.dat"
    write_chen_format(out, volume, 1.0)

    loaded = load_volume(out)
    assert np.array_equal((volume > 0).astype(int), loaded)
