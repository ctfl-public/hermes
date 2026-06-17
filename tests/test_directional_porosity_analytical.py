from __future__ import annotations

import types

import pytest


pytestmark = pytest.mark.analytical


def load_direction_porosity_functions(repo_root):
    """Load function definitions without executing hard-coded paper paths."""
    source = (repo_root / "directionPorosityPlotting.py").read_text(encoding="utf-8")
    prefix = source.split("# TiffPath = ", 1)[0]
    module = types.ModuleType("directionPorosityPlotting_functions_only")
    exec(compile(prefix, "directionPorosityPlotting.py", "exec"), module.__dict__)
    return module


def test_directional_porosity_matches_known_layered_volume(repo_root, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    dpp = load_direction_porosity_functions(repo_root)

    material = tiff.imread(fixture_dir / "layered_porosity_24.tif")
    volume = np.ones_like(material)
    locations, porosity = dpp.get1DPorosity(
        material, volume, np.zeros_like(material), direction="x", bins=4, voxel_size=1
    )

    assert locations == [1, 6.0, 12.0, 18.0]
    assert porosity == pytest.approx([1.0, 0.0, 1.0, 0.0])


def test_porosity_3d_map_matches_known_block_values(repo_root, tmp_path, fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    dpp = load_direction_porosity_functions(repo_root)

    material = tiff.imread(fixture_dir / "layered_porosity_24.tif")
    volume = np.ones_like(material)
    out = tmp_path / "maps" / "porosity3d.txt"
    df = dpp.porosity3DMap(6, material, volume, str(out), voxel_size=1)

    assert out.exists()
    assert len(df) == 4 * 4 * 4
    assert set(df["Porosity"].unique()).issubset({0.0, 1.0})


def test_directional_porosity_plot_is_written(repo_root, tmp_path):
    dpp = load_direction_porosity_functions(repo_root)

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
