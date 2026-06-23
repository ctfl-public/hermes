from __future__ import annotations

import pytest


pytestmark = pytest.mark.analytical
def test_directional_porosity_matches_known_layered_volume(fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    dpp = pytest.importorskip("hermes.directional_porosity")

    material = tiff.imread(fixture_dir / "layered_porosity_24.tif")
    volume = np.ones_like(material)
    locations, porosity = dpp.directional_porosity(
        material, volume, direction="x", bins=4, voxel_size=1
    )

    assert locations == [1, 6.0, 12.0, 18.0]
    assert porosity == pytest.approx([1.0, 0.0, 1.0, 0.0])


def test_porosity_3d_map_matches_known_block_values(tmp_path, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    dpp = pytest.importorskip("hermes.directional_porosity")

    material = tiff.imread(fixture_dir / "layered_porosity_24.tif")
    volume = np.ones_like(material)
    out = tmp_path / "maps" / "porosity3d.txt"
    df = dpp.porosity_3d_map(6, material, volume, str(out), voxel_size=1)

    assert out.exists()
    assert len(df) == 4 * 4 * 4
    assert set(df["Porosity"].unique()).issubset({0.0, 1.0})


def test_directional_porosity_plot_is_written(tmp_path):
    dpp = pytest.importorskip("hermes.directional_porosity")

    out = tmp_path / "x_porosity.png"
    dpp.plot_porosity_scatter(
        [0, 1, 2, 3],
        [0.0, 0.25, 0.5, 0.75],
        str(out),
        xlabel="Distance",
        ylabel="Porosity",
        labels=["synthetic"],
    )

    assert out.exists()
    assert out.stat().st_size > 0
