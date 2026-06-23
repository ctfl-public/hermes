from __future__ import annotations

import pytest


pytestmark = pytest.mark.analytical


def _run_skimage_threshold(method, image, select_lighter=True, block_size=9, manual=(0, 65535)):
    from hermes.segmentation import segment_greyscale

    lo, hi = manual
    result = segment_greyscale(
        image,
        method,
        select_lighter=select_lighter,
        block_size=block_size,
        min_manual=lo,
        max_manual=hi,
    )
    return result.mask


@pytest.mark.parametrize("method", ["Otsu", "Li", "Yen", "Isodata", "Triangle"])
def test_global_thresholds_recover_known_bright_cube(fixture_dir, method):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "grayscale_two_phase_24.tif")
    expected = tiff.imread(fixture_dir / "grayscale_two_phase_mask_24.tif").astype(bool)
    actual = _run_skimage_threshold(method, image, select_lighter=True)

    mismatch = np.count_nonzero(actual != expected)
    assert mismatch / expected.size < 0.01


def test_manual_threshold_recovers_exact_known_bright_cube(fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "grayscale_two_phase_24.tif")
    expected = tiff.imread(fixture_dir / "grayscale_two_phase_mask_24.tif").astype(bool)
    actual = _run_skimage_threshold("Manual", image, manual=(10000, 65535))

    assert np.array_equal(actual, expected)
    expected_porosity = 1.0 - (12 * 12 * 12) / (24 * 24 * 24)
    actual_porosity = np.count_nonzero(~actual) / actual.size
    assert actual_porosity == pytest.approx(expected_porosity)


def test_darker_greys_selects_complement_of_lighter_phase(fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "grayscale_two_phase_24.tif")
    lighter = _run_skimage_threshold("Otsu", image, select_lighter=True)
    darker = _run_skimage_threshold("Otsu", image, select_lighter=False)

    assert np.array_equal(darker, ~lighter)


def test_adaptive_threshold_runs_on_gradient_fixture_and_returns_material_phase(fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")

    image = tiff.imread(fixture_dir / "grayscale_gradient_24.tif")
    actual = _run_skimage_threshold("Adaptive", image, select_lighter=True, block_size=9)

    assert actual.shape == image.shape
    assert actual.dtype == np.bool_
    assert np.count_nonzero(actual[8:16, 8:16, 8:16]) > 0


@pytest.mark.gui
def test_gui_segmentation_thread_matches_manual_analytical_mask(fixture_dir):
    np = pytest.importorskip("numpy")
    tiff = pytest.importorskip("tifffile")
    pytest.importorskip("PyQt5")
    pytest.importorskip("pyvista")
    pytest.importorskip("pyvistaqt")
    from hermes.gui import SegmentationThread

    image = tiff.imread(fixture_dir / "grayscale_two_phase_24.tif")
    expected = tiff.imread(fixture_dir / "grayscale_two_phase_mask_24.tif").astype(bool)
    captured = {}

    thread = SegmentationThread(image, "Manual", 0, minManual="10000", maxManual="65535")
    thread.finished.connect(
        lambda mask, lo, hi, porosity: captured.update(
            mask=mask, lo=lo, hi=hi, porosity=porosity
        )
    )
    thread.run()

    assert np.array_equal(captured["mask"], expected)
    assert captured["porosity"] == pytest.approx(np.count_nonzero(~expected) / expected.size)
