from __future__ import annotations

import pytest


pytestmark = pytest.mark.analytical


def test_workspace_segments_known_grayscale_volume_and_extracts_subvolume(fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    from hermes import Workspace

    ws = Workspace.from_file(fixture_dir / "grayscale_two_phase_24.tif", voxel_size=1.0)
    expected = tiff.imread(fixture_dir / "grayscale_two_phase_mask_24.tif").astype(bool)

    ws.segment("Manual", min_manual=10000, max_manual=65535)

    assert np.array_equal(ws.matrix.astype(bool), expected)

    subvolume = ws.extract_subvolume(corner=(6, 6, 6), dimensions=(12, 12, 12), sub_id=3)

    assert subvolume.matrix.shape == (12, 12, 12)
    assert int(np.count_nonzero(subvolume.matrix)) == 12 * 12 * 12
    assert subvolume.origin == (6, 6, 6)
    assert "_V3_6-6-6-12" in subvolume.name


def test_workspace_mesh_and_properties_match_known_cube_scale(fixture_dir):
    np = pytest.importorskip("numpy")
    from hermes import Workspace

    ws = Workspace.from_file(fixture_dir / "cube_16.tif", voxel_size=1.0)
    ws.pad()
    vertices, faces = ws.generate_mesh()

    assert vertices.shape[1] == 3
    assert faces.shape[1] == 3
    assert ws.check_mesh()

    closed_volume = abs(ws.compute_closed_volume())
    porosity = ws.compute_porosity()

    assert closed_volume == pytest.approx(512.0, abs=80.0)
    assert porosity == pytest.approx(1.0 - 512.0 / (16 * 16 * 16), abs=0.025)
    assert np.isfinite(ws.compute_surface_area())


def test_workspace_saves_properties_table(tmp_path, fixture_dir):
    from hermes import Workspace

    ws = Workspace.from_file(fixture_dir / "cube_16.tif", voxel_size=1.0)
    ws.pad()
    ws.generate_mesh()
    ws.compute_surface_area()
    ws.compute_closed_volume()

    out = tmp_path / "properties.txt"
    ws.save_properties(out)

    text = out.read_text()
    assert text.startswith("WorkspaceName\tsurface_area\tclosed_volume\n")
    assert "cube_16.tif" in text
