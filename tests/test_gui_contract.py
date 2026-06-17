from __future__ import annotations

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


def test_gui_run_pipeline_builds_expected_serial_call(monkeypatch, tmp_path, fixture_dir, qtbot=None):
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from PyQt5.QtWidgets import QApplication, QTableWidgetItem
    import HERMES
    from HERMES import UI

    captured = {}

    def fake_voxel2stl(cropping_flag, crop_settings, surface_settings, saving_options):
        captured["cropping_flag"] = cropping_flag
        captured["crop_settings"] = crop_settings
        captured["surface_settings"] = surface_settings
        captured["saving_options"] = saving_options

    monkeypatch.setattr(HERMES, "voxel2stl", fake_voxel2stl)

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

        assert captured["cropping_flag"] == "Regular"
        filenames, filevoxels, num_volumes, volume_length = captured["crop_settings"]
        assert filenames == [str(fixture_dir / "cube_16.tif")]
        assert filevoxels == [1.0]
        assert num_volumes == 0
        assert volume_length == 8
        assert captured["surface_settings"]["laplacianFlag"] is True
        assert captured["surface_settings"]["laplacian_iter"] == 2
        assert captured["saving_options"]["tiff_save"] is True
        assert captured["saving_options"]["property_options"]["surf_area"] is True
    finally:
        ui.close()
