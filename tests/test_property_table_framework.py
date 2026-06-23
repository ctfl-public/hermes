from __future__ import annotations

import pytest

from hermes.io import load_volume
from hermes.mesh import create_padding, generate_mesh
from hermes.property_table import build_legacy_property_row, compute_and_write_legacy_properties

from tests.helpers import base_saving_options, read_property_table


pytestmark = pytest.mark.analytical


def test_framework_legacy_property_row_matches_known_cube_schema(fixture_dir):
    volume = load_volume(fixture_dir / "cube_16.tif")
    vertices, faces = generate_mesh(create_padding(volume), 1.0)
    options = base_saving_options(
        fixture_dir,
        property_options={
            "min_max": True,
            "surf_area": True,
            "closed_volume": True,
            "vol_by_area": True,
            "porosity": True,
        },
    )["property_options"]

    header, row = build_legacy_property_row(
        "cube",
        vertices,
        faces,
        volume,
        1.0,
        options,
        str(fixture_dir / "cube_16.tif"),
    )

    assert header == [
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
    ]
    assert row[0] == "cube"
    assert row[header.index("ClosedVolume")] == pytest.approx(512.0, abs=80.0)
    assert row[header.index("Porosity")] == pytest.approx(1 - 512 / 16**3, abs=0.03)


def test_framework_legacy_property_writer_preserves_table_contract(tmp_path, fixture_dir):
    volume = load_volume(fixture_dir / "cube_16.tif")
    vertices, faces = generate_mesh(create_padding(volume), 1.0)
    saving_options = base_saving_options(
        tmp_path,
        property_save=True,
        property_options={
            "surf_area": True,
            "closed_volume": True,
            "vol_by_area": True,
            "porosity": True,
        },
    )

    compute_and_write_legacy_properties(
        "cube",
        vertices,
        faces,
        volume,
        1.0,
        saving_options,
        str(fixture_dir / "cube_16.tif"),
    )

    header, rows = read_property_table(tmp_path / "properties.txt")
    assert header == ["StlName", "SurfaceArea", "ClosedVolume", "Volume/SurfaceArea", "Porosity"]
    assert len(rows) == 1
    assert float(rows[0][header.index("ClosedVolume")]) == pytest.approx(512.0, abs=80.0)
    assert float(rows[0][header.index("Porosity")]) == pytest.approx(1 - 512 / 16**3, abs=0.03)
