"""Input and output helpers for HERMES volume data."""

from __future__ import annotations

from pathlib import Path

import imageio
import numpy as np


def load_volume(path: str | Path) -> np.ndarray:
    """Load a TIFF volume or sparse DAT/TXT voxel file."""
    path = Path(path)
    path_text = str(path)

    if path.suffix.lower() in {".tif", ".tiff"}:
        image_volume = imageio.volread(path_text)
        return np.transpose(image_volume, (2, 1, 0))

    if path.suffix.lower() in {".txt", ".dat"}:
        with path.open("r", encoding="utf-8") as file_obj:
            header = file_obj.readline().split()
        tempdata = np.loadtxt(path_text, skiprows=2)
        tempdata = np.atleast_2d(tempdata)
        zero_based = np.min(tempdata[:, :3]) == 0
        shape = tuple(int(value) + 1 for value in header[:3]) if zero_based else tuple(int(value) for value in header[:3])
        image_volume = np.zeros(shape, dtype="int")
        offset = 0 if zero_based else 1
        for val in tempdata:
            image_volume[int(val[0]) - offset, int(val[1]) - offset, int(val[2]) - offset] = int(val[3])
        return np.transpose(image_volume, (2, 1, 0))

    raise ValueError(f"Unsupported volume file format: {path.suffix}")


def write_chen_format(path: str | Path, binary_volume: np.ndarray, voxel_size: float) -> None:
    """Write a sparse DAT file using the current HERMES coordinate convention."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    external_volume = np.transpose(binary_volume, (2, 1, 0))
    x_i, y_j, z_k = np.shape(external_volume)
    with path.open("w") as file_obj:
        file_obj.write(f"{x_i} {y_j} {z_k} {voxel_size * 10**-6}\n")
        file_obj.write("i j k voxel")
        for i in range(x_i):
            for j in range(y_j):
                for k in range(z_k):
                    if external_volume[i, j, k] == 1:
                        value = int(external_volume[i, j, k])
                        file_obj.write(f"\n{i + 1} {j + 1} {k + 1} {value}")
