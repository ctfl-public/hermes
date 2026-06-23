from __future__ import annotations

import json

import pytest


pytestmark = pytest.mark.gui


def test_gui_import_and_required_widgets_exist(qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication
    from HERMES import UI

    app = QApplication.instance() or QApplication([])
    ui = UI()
    try:
        for name in [
            "FileNamestableWidget",
            "RunpushButton",
            "LoadTiffSegmentationpushButton",
            "OtsupushButton",
            "LipushButton",
            "YenpushButton",
            "AdaptivepushButton",
            "manualThresholdingpushButton",
            "SaveTiffSegmentationpushButton",
        ]:
            assert ui.findChild(object, name) is not None
    finally:
        ui.close()


def test_gui_run_pipeline_builds_expected_workflow_config(monkeypatch, tmp_path, fixture_dir, qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication, QTableWidgetItem
    import HERMES
    from HERMES import UI

    captured = {}

    def fake_run_workflow_config(config):
        captured["config"] = config

    monkeypatch.setattr(HERMES, "run_workflow_config", fake_run_workflow_config)

    app = QApplication.instance() or QApplication([])
    ui = UI()
    try:
        ui.tableWidget.setRowCount(1)
        ui.tableWidget.setItem(0, 0, QTableWidgetItem(str(fixture_dir / "cube_16.tif")))
        ui.tableWidget.setItem(0, 1, QTableWidgetItem("1.0"))
        ui.tabWidget.setCurrentIndex(0)
        ui.VolumnLengthlineEdit.setText("8")
        ui.VolumnNumberlineEdit.setText("0")
        ui.TiffSavecheckBox.setChecked(True)
        ui.TiffSavePathtextEdit.setText(str(tmp_path / "tiff"))
        ui.LaplaciancheckBox.setChecked(True)
        ui.LaplacianItertextEdit.setText("2")
        ui.SurfAreacheckBox.setChecked(True)

        ui.run_voxel2stl()

        assert captured["config"]["input"] == {
            "path": str(fixture_dir / "cube_16.tif"),
            "voxel_size": 1.0,
        }
        assert captured["config"]["sampling"] == {"mode": "grid", "volume_length": 8}
        assert captured["config"]["outputs"] == ["tiff"]
        assert captured["config"]["properties"] == ["surface_area"]
        assert captured["config"]["surface_settings"]["laplacianFlag"] is True
        assert captured["config"]["surface_settings"]["laplacian_iter"] == 2
    finally:
        ui.close()


def test_gui_run_pipeline_builds_workflow_config_for_multi_input(monkeypatch, tmp_path, fixture_dir, qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication, QTableWidgetItem
    import HERMES
    from HERMES import UI

    captured = {}

    def fake_run_workflow_config(config):
        captured["config"] = config

    monkeypatch.setattr(HERMES, "run_workflow_config", fake_run_workflow_config)

    app = QApplication.instance() or QApplication([])
    ui = UI()
    try:
        ui.tableWidget.setRowCount(2)
        ui.tableWidget.setItem(0, 0, QTableWidgetItem(str(fixture_dir / "small_primary_0.tif")))
        ui.tableWidget.setItem(0, 1, QTableWidgetItem("1.0"))
        ui.tableWidget.setItem(1, 0, QTableWidgetItem(str(fixture_dir / "small_primary_1.tif")))
        ui.tableWidget.setItem(1, 1, QTableWidgetItem("1.0"))
        ui.tabWidget.setCurrentIndex(0)
        ui.VolumnLengthlineEdit.setText("12")
        ui.VolumnNumberlineEdit.setText("2")
        ui.TiffSavecheckBox.setChecked(True)
        ui.TiffSavePathtextEdit.setText(str(tmp_path / "tiff"))

        ui.run_voxel2stl()

        assert captured["config"]["inputs"] == [
            {
                "path": str(fixture_dir / "small_primary_0.tif"),
                "voxel_size": 1.0,
            },
            {
                "path": str(fixture_dir / "small_primary_1.tif"),
                "voxel_size": 1.0,
            },
        ]
        assert captured["config"]["sampling"] == {"mode": "random", "volume_length": 12, "count": 2}
        assert captured["config"]["outputs"] == ["tiff"]
    finally:
        ui.close()


def test_gui_save_settings_embeds_framework_config(monkeypatch, tmp_path, fixture_dir, qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication, QFileDialog, QTableWidgetItem
    from HERMES import UI

    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(settings_path), ""))

    app = QApplication.instance() or QApplication([])
    ui = UI()
    try:
        ui.tableWidget.setRowCount(1)
        ui.tableWidget.setItem(0, 0, QTableWidgetItem(str(fixture_dir / "cube_16.tif")))
        ui.tableWidget.setItem(0, 1, QTableWidgetItem("1.0"))
        ui.tabWidget.setCurrentIndex(0)
        ui.VolumnLengthlineEdit.setText("8")
        ui.VolumnNumberlineEdit.setText("0")
        ui.TiffSavecheckBox.setChecked(True)
        ui.TiffSavePathtextEdit.setText(str(tmp_path / "output" / "tiff"))
        ui.PropertySavecheckBox.setChecked(True)
        ui.PropertySavePathtextEdit.setText(str(tmp_path / "output" / "properties.txt"))
        ui.SurfAreacheckBox.setChecked(True)
        ui.PorositycheckBox.setChecked(True)

        ui.save_settings()

        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "workflowConfig" in settings
        assert settings["workflowConfig"]["output_dir"] == str(tmp_path / "output")
        assert settings["workflowConfig"]["outputs"] == ["tiff", "properties"]
        assert settings["workflowConfig"]["properties"] == ["surface_area", "porosity"]
    finally:
        ui.close()


def test_gui_load_settings_accepts_raw_workflow_config(monkeypatch, tmp_path, fixture_dir, qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication, QFileDialog
    from HERMES import UI

    config_path = tmp_path / "workflow_config.json"
    config = {
        "input": {
            "path": str(fixture_dir / "cube_16.tif"),
            "voxel_size": 1.0,
        },
        "output_dir": "output",
        "output_paths": {
            "tiff": "images",
            "properties": "tables/properties.txt",
        },
        "outputs": ["tiff", "properties"],
        "properties": ["surface_area", "porosity"],
        "surface_settings": {
            "laplacianFlag": True,
            "laplacian_iter": 2,
            "ScreenedPoissonFlag": False,
            "ScreenedPoisson_iter": None,
            "RemoveIslandsFlag": False,
        },
        "sampling": {"mode": "grid", "volume_length": 8},
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(config_path), ""))

    app = QApplication.instance() or QApplication([])
    ui = UI()
    try:
        ui.load_settings()

        assert ui.tableWidget.rowCount() == 1
        assert ui.tableWidget.item(0, 0).text() == str(fixture_dir / "cube_16.tif")
        assert ui.tableWidget.item(0, 1).text() == "1.0"
        assert ui.TiffSavecheckBox.isChecked() is True
        assert ui.TiffSavePathtextEdit.text() == str(tmp_path / "images")
        assert ui.PropertySavecheckBox.isChecked() is True
        assert ui.PropertySavePathtextEdit.text() == str(tmp_path / "tables" / "properties.txt")
        assert ui.SurfAreacheckBox.isChecked() is True
        assert ui.PorositycheckBox.isChecked() is True
        assert ui.LaplaciancheckBox.isChecked() is True
        assert ui.LaplacianItertextEdit.text() == "2"
        assert ui.VolumnLengthlineEdit.text() == "8"
        assert ui.VolumnNumberlineEdit.text() == "0"
    finally:
        ui.close()


def test_gui_run_pipeline_reports_config_errors_without_serial_fallback(monkeypatch, fixture_dir, qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication, QTableWidgetItem
    import HERMES
    from HERMES import UI

    captured = {}

    def fail_run_workflow_config(config):
        raise AssertionError("workflow should not run with invalid GUI state")

    monkeypatch.setattr(HERMES, "run_workflow_config", fail_run_workflow_config)

    app = QApplication.instance() or QApplication([])
    ui = UI()
    try:
        monkeypatch.setattr(ui, "show_error_message", lambda title, message: captured.update({"title": title, "message": message}))
        ui.tableWidget.setRowCount(1)
        ui.tableWidget.setItem(0, 0, QTableWidgetItem(str(fixture_dir / "cube_16.tif")))
        ui.tableWidget.setItem(0, 1, QTableWidgetItem("1.0"))
        ui.tabWidget.setCurrentIndex(0)
        ui.VolumnLengthlineEdit.setText("8")
        ui.VolumnNumberlineEdit.setText("0")

        ui.run_voxel2stl()

        assert captured["title"] == "Error"
        assert "Please select at least one" in captured["message"]
    finally:
        ui.close()
