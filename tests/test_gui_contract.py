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
