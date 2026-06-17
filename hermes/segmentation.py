"""Segmentation routines shared by the GUI and script workflows."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from skimage.filters import (
    threshold_isodata,
    threshold_li,
    threshold_local,
    threshold_otsu,
    threshold_triangle,
    threshold_yen,
)


@dataclass(frozen=True)
class SegmentationResult:
    mask: np.ndarray
    min_threshold: int | str
    max_threshold: int | str
    porosity: float


def segment_greyscale(
    image: np.ndarray,
    method: str,
    *,
    select_lighter: bool = True,
    block_size: int = 51,
    offset: int | float = 10,
    min_manual: int = 0,
    max_manual: int = 255,
) -> SegmentationResult:
    """Segment a greyscale volume into a binary material mask."""
    normalized_method = method.strip().capitalize()
    image = np.asarray(image)

    min_threshold: int | str = ""
    max_threshold: int | str = ""

    if normalized_method == "Manual":
        min_threshold = int(min_manual)
        max_threshold = int(max_manual)
        mask = (image > min_threshold) & (image < max_threshold)
    else:
        threshold = _compute_threshold(
            image,
            normalized_method,
            block_size=block_size,
            offset=offset,
        )
        mask = image > threshold if select_lighter else image <= threshold

        if np.isscalar(threshold):
            threshold_value = int(threshold)
            if select_lighter:
                min_threshold = threshold_value
                max_threshold = int(np.max(image))
            else:
                min_threshold = 0
                max_threshold = threshold_value

    porosity = float(np.count_nonzero(~mask) / mask.size)
    return SegmentationResult(mask=mask, min_threshold=min_threshold, max_threshold=max_threshold, porosity=porosity)


def _compute_threshold(
    image: np.ndarray,
    method: str,
    *,
    block_size: int,
    offset: int | float,
) -> float | np.ndarray:
    if method == "Otsu":
        return threshold_otsu(image)
    if method == "Adaptive":
        if block_size % 2 == 0:
            raise ValueError("Adaptive threshold block_size must be an odd integer.")
        return threshold_local(image, block_size, offset=offset)
    if method == "Li":
        return threshold_li(image)
    if method == "Yen":
        return threshold_yen(image)
    if method == "Isodata":
        return threshold_isodata(image)
    if method == "Triangle":
        return threshold_triangle(image)
    raise ValueError(f"Unknown thresholding segmentation method: {method}")
