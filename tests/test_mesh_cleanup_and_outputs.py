from __future__ import annotations

import pytest

from hermes.centerlines import analyze_centerline
from hermes.io import load_volume
from hermes.mesh import check_mesh, create_padding, generate_mesh, load_trimesh, repair_mesh, smooth_mesh


pytestmark = pytest.mark.analytical


def test_laplacian_smoothing_preserves_mesh_shape_and_marks_output_name(fixture_dir):
    np = pytest.importorskip("numpy")

    volume = create_padding(load_volume(fixture_dir / "cube_16.tif"))
    vertices, faces = generate_mesh(volume, 1.0)
    name, smoothed_vertices, smoothed_faces = smooth_mesh(
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
    assert check_mesh(smoothed_vertices, smoothed_faces)


def test_screened_poisson_reconstruction_uses_configured_depth(monkeypatch, fixture_dir):
    np = pytest.importorskip("numpy")

    volume = create_padding(load_volume(fixture_dir / "cube_16.tif"))
    vertices, faces = generate_mesh(volume, 1.0)
    calls = []

    class FakeMesh:
        def vertex_matrix(self):
            return vertices

        def face_matrix(self):
            return faces

    class FakeMeshSet:
        def apply_filter(self, name, **kwargs):
            calls.append((name, kwargs))

        def current_mesh(self):
            return FakeMesh()

    name, reconstructed_vertices, reconstructed_faces = smooth_mesh(
        "cube",
        vertices,
        faces,
        {
            "laplacianFlag": False,
            "laplacian_iter": None,
            "ScreenedPoissonFlag": True,
            "ScreenedPoisson_iter": 4,
            "RemoveIslandsFlag": False,
        },
        meshset_loader=lambda in_vertices, in_faces: FakeMeshSet(),
    )

    assert name.endswith("_screened_poisson4")
    assert calls == [("generate_surface_reconstruction_screened_poisson", {"depth": 4, "preclean": True})]
    assert reconstructed_vertices.shape == vertices.shape
    assert reconstructed_faces.shape == faces.shape
    assert np.isfinite(reconstructed_vertices).all()


@pytest.mark.pymeshlab
def test_remove_floating_islands_keeps_largest_component(fixture_dir):
    pytest.importorskip("pymeshlab")

    volume = create_padding(load_volume(fixture_dir / "two_islands_24.tif"))
    vertices, faces = generate_mesh(volume, 1.0)
    original_components = load_trimesh(vertices, faces).split(only_watertight=False)

    _, cleaned_vertices, cleaned_faces = smooth_mesh(
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
    cleaned_components = load_trimesh(cleaned_vertices, cleaned_faces).split(only_watertight=False)

    assert len(original_components) > 1
    assert len(cleaned_components) == 1
    assert cleaned_faces.shape[0] < faces.shape[0]


def test_fix_mesh_runs_repair_filters_and_returns_valid_mesh(monkeypatch, fixture_dir):
    volume = create_padding(load_volume(fixture_dir / "cube_16.tif"))
    vertices, faces = generate_mesh(volume, 1.0)
    damaged_faces = faces[:-20]
    calls = []

    class FakeMesh:
        def vertex_matrix(self):
            return vertices

        def face_matrix(self):
            return faces

    class FakeMeshSet:
        def apply_filter(self, name, **kwargs):
            calls.append((name, kwargs))

        def current_mesh(self):
            return FakeMesh()

    assert not check_mesh(vertices, damaged_faces)

    name, fixed_vertices, fixed_faces = repair_mesh(
        "damaged_cube",
        vertices,
        damaged_faces,
        meshset_loader=lambda in_vertices, in_faces: FakeMeshSet(),
    )

    assert name.endswith("_Fixed")
    assert [name for name, _ in calls] == [
        "generate_surface_reconstruction_screened_poisson",
        "meshing_remove_null_faces",
        "meshing_repair_non_manifold_edges",
        "meshing_repair_non_manifold_vertices",
        "meshing_remove_duplicate_faces",
        "meshing_remove_duplicate_vertices",
        "meshing_re_orient_faces_coherently",
    ]
    assert check_mesh(fixed_vertices, fixed_faces)


def test_centerline_analysis_writes_direction_map_with_expected_columns(tmp_path, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "fiber_angle_48.tif")
    surface_name = tmp_path / "fiber_angle_48.tif"

    analyze_centerline(image, 1.0, str(surface_name), plane="XY")

    direction_file = tmp_path / "fiber_angle_48_voxel_directions.txt"
    assert direction_file.exists()
    data = np.loadtxt(direction_file, skiprows=1)
    data = np.atleast_2d(data)
    assert data.shape[1] == 6
    assert data.shape[0] == int(np.count_nonzero(image))
    assert np.isfinite(data).all()
