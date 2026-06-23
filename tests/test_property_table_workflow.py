from __future__ import annotations

import pytest

from hermes.workspace import Workspace
from tests.helpers import read_property_table


pytestmark = pytest.mark.analytical


def test_workspace_property_table_matches_known_cube_schema(tmp_path, fixture_dir):
    workspace = Workspace.from_file(fixture_dir / "cube_16.tif", voxel_size=1.0)
    workspace.matrix = (workspace.matrix > 0).astype("uint8")
    workspace.pad()
    workspace.generate_mesh()
    workspace.compute_surface_area()
    workspace.compute_closed_volume()
    workspace.compute_volume_by_area()
    workspace.compute_porosity()

    output = tmp_path / "properties.txt"
    workspace.save_properties(output, append=False)

    header, rows = read_property_table(output)
    assert header == ["WorkspaceName", "surface_area", "closed_volume", "volume_by_area", "porosity"]
    assert len(rows) == 1
    assert rows[0][0] == "cube_16.tif"
    assert float(rows[0][header.index("closed_volume")]) == pytest.approx(512.0, abs=80.0)
    assert float(rows[0][header.index("porosity")]) == pytest.approx(1 - 512 / 16**3, abs=0.03)


def test_workspace_property_table_appends_rows_without_duplicate_header(tmp_path, fixture_dir):
    output = tmp_path / "properties.txt"
    for name in ["first_cube", "second_cube"]:
        workspace = Workspace.from_file(fixture_dir / "cube_16.tif", voxel_size=1.0)
        workspace.name = name
        workspace.matrix = (workspace.matrix > 0).astype("uint8")
        workspace.pad()
        workspace.generate_mesh()
        workspace.compute_closed_volume()
        workspace.compute_porosity()
        workspace.save_properties(output, append=True)

    lines = output.read_text(encoding="utf-8").strip().splitlines()
    header, rows = read_property_table(output)
    assert lines.count("\t".join(header)) == 1
    assert header == ["WorkspaceName", "closed_volume", "porosity"]
    assert [row[0] for row in rows] == ["first_cube", "second_cube"]
