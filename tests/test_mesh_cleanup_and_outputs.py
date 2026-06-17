from __future__ import annotations

import pytest


pytestmark = pytest.mark.analytical


def test_laplacian_smoothing_preserves_mesh_shape_and_marks_output_name(fixture_dir):
    np = pytest.importorskip("numpy")
    v2s = pytest.importorskip("voxel2stl")

    volume = v2s.createPadding(v2s.loadData(str(fixture_dir / "cube_16.tif")))
    vertices, faces = v2s.getMesh(volume, 16, 1.0)
    name, smoothed_vertices, smoothed_faces = v2s.stlSmoothing(
        "cube",
        vertices.copy(),
        faces.copy(),
        {
            "laplacianFlag": True,
            "laplacian_iter": 2,
            "ScreenedPoissonFlag": False,
            "ScreenedPoisson_iter": None,
            "RemoveIslandsFlag": False,
        },
    )

    assert name.endswith("_laplacian2")
    assert smoothed_vertices.shape == vertices.shape
    assert smoothed_faces.shape == faces.shape
    assert np.isfinite(smoothed_vertices).all()
    assert v2s.checkMesh(smoothed_vertices, smoothed_faces)


@pytest.mark.pymeshlab
def test_remove_floating_islands_keeps_largest_component(fixture_dir):
    pytest.importorskip("pymeshlab")
    v2s = pytest.importorskip("voxel2stl")

    volume = v2s.createPadding(v2s.loadData(str(fixture_dir / "two_islands_24.tif")))
    vertices, faces = v2s.getMesh(volume, 24, 1.0)
    original_components = v2s.loadMeshTrimesh(vertices, faces).split(only_watertight=False)

    _, cleaned_vertices, cleaned_faces = v2s.stlSmoothing(
        "two_islands",
        vertices,
        faces,
        {
            "laplacianFlag": False,
            "laplacian_iter": None,
            "ScreenedPoissonFlag": False,
            "ScreenedPoisson_iter": None,
            "RemoveIslandsFlag": True,
        },
    )
    cleaned_components = v2s.loadMeshTrimesh(cleaned_vertices, cleaned_faces).split(only_watertight=False)

    assert len(original_components) > 1
    assert len(cleaned_components) == 1
    assert cleaned_faces.shape[0] < faces.shape[0]


def test_centerline_analysis_writes_direction_map_with_expected_columns(tmp_path, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    v2s = pytest.importorskip("voxel2stl")

    image = tiff.imread(fixture_dir / "fiber_angle_48.tif")
    surface_name = tmp_path / "fiber_angle_48.tif"

    v2s.analyzeCenterLine(image, 1.0, str(surface_name), plane="XY")

    direction_file = tmp_path / "fiber_angle_48_voxel_directions.txt"
    assert direction_file.exists()
    data = np.loadtxt(direction_file, skiprows=1)
    data = np.atleast_2d(data)
    assert data.shape[1] == 6
    assert data.shape[0] == int(np.count_nonzero(image))
    assert np.isfinite(data).all()
