"""Directional and blockwise porosity utilities."""

from __future__ import annotations

from pathlib import Path
import itertools
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hermes.io import load_volume


mpl.rcParams["axes.linewidth"] = 1.5
mpl.rcParams["xtick.major.width"] = 1.5
mpl.rcParams["ytick.major.width"] = 1.5


def load_data(path: str | Path) -> np.ndarray:
    """Load a TIFF, DAT, or TXT volume."""
    return load_volume(path)


def directional_porosity(
    material: np.ndarray,
    volume: np.ndarray,
    direction: str,
    *,
    bins: int = 0,
    voxel_size: float = 1.0,
) -> tuple[list[float], list[float]]:
    """Compute binned porosity along x, y, or z."""
    axis_map = {"x": 2, "y": 1, "z": 0}
    if direction not in axis_map:
        raise ValueError("Direction must be 'x', 'y', or 'z'")

    axis = axis_map[direction]
    size = material.shape[axis]
    if bins == 0:
        bins = size

    edges = np.linspace(0, size, bins + 1, dtype=int)
    porosity = []
    locations = []
    first_center = None

    for index in range(bins):
        slices = [slice(None)] * 3
        slices[axis] = slice(edges[index], edges[index + 1])

        material_bin = material[tuple(slices)]
        volume_bin = volume[tuple(slices)]
        material_count = np.count_nonzero(material_bin)
        volume_count = np.count_nonzero(volume_bin)
        void_count = volume_count - material_count

        if volume_count > 0:
            porosity.append(void_count / volume_count)
            center = ((edges[index] + edges[index + 1]) / 2.0) * voxel_size
            if first_center is None:
                first_center = center
                center = 1
            else:
                center -= first_center
            locations.append(center)

    return locations, porosity


def plot_porosity_scatter(
    locations,
    porosity,
    save_path: str | Path,
    xlabel: str = "Distance (um)",
    ylabel: str = "Porosity",
    title: str | None = None,
    labels=None,
) -> None:
    """Plot one or more porosity distributions and save a PNG."""
    plt.figure(figsize=(6, 4), dpi=150)
    plt.rcParams.update(
        {
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.titleweight": "bold",
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )

    if not isinstance(locations[0], (list, tuple, range)) and not hasattr(locations[0], "__len__"):
        locations = [locations]
        porosity = [porosity]

    colors = list(plt.cm.tab10.colors)
    markers = ["o", "s", "^", "d", "v", "<", ">", "p", "*", "h"]

    for index, (loc, por) in enumerate(zip(locations, porosity)):
        label = labels[index] if labels and index < len(labels) else None
        plt.scatter(
            loc,
            por,
            marker=markers[index % len(markers)],
            s=1,
            facecolors=colors[index % len(colors)],
            label=label,
        )

    plt.xlabel(xlabel, fontweight="bold")
    plt.ylabel(ylabel, fontweight="bold")
    if title:
        plt.title(title)

    ax = plt.gca()
    ax.minorticks_on()
    if labels:
        plt.legend(frameon=False)
    plt.tick_params(direction="out")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def save_porosity_data(locations, porosity, save_path: str | Path) -> None:
    """Save locations and porosity values to a tab-delimited text file."""
    data = np.column_stack((locations, porosity))
    np.savetxt(save_path, data, header="Location\tPorosity", fmt="%.6f", delimiter="\t")


def load_porosity_data(file_path: str | Path):
    """Load porosity data saved by ``save_porosity_data``."""
    data = np.loadtxt(file_path, skiprows=1)
    data = np.atleast_2d(data)
    locations = data[:, 0]
    porosity = data[:, 1]
    if data.shape[1] > 2:
        return locations, porosity, data[:, 2]
    return locations, porosity


def load_porosity_distributions(folders, prefix: str = "", suffix: str = ".txt"):
    """Load directional porosity distribution files from one or more folders."""
    data = {"x": [], "y": [], "z": []}

    for folder in folders:
        for filename in os.listdir(folder):
            if not filename.endswith(suffix):
                continue
            if prefix and not filename.startswith(prefix):
                continue

            if "_posityDistributionx" in filename:
                direction = "x"
            elif "_posityDistributiony" in filename:
                direction = "y"
            elif "_posityDistributionz" in filename:
                direction = "z"
            else:
                continue

            path = Path(folder) / filename
            array = np.loadtxt(path)
            if array.ndim == 1:
                locations, porosity = [array[0]], [array[1]]
            else:
                locations, porosity = array[:, 0], array[:, 1]
            data[direction].append((locations, porosity, filename))

    return data


def porosity_3d_map(
    volume_length: float,
    material: np.ndarray,
    volume: np.ndarray,
    save_path: str | Path,
    *,
    voxel_size: float = 1.0,
) -> pd.DataFrame:
    """Compute a blockwise 3D porosity map and save it as a table."""
    voxel_lengths = material.shape
    dim_x = int(voxel_lengths[0] * voxel_size / volume_length)
    dim_y = int(voxel_lengths[1] * voxel_size / volume_length)
    dim_z = int(voxel_lengths[2] * voxel_size / volume_length)
    block_size = int(volume_length / voxel_size)

    x_corners = [index * block_size for index in range(dim_x)]
    y_corners = [index * block_size for index in range(dim_y)]
    z_corners = [index * block_size for index in range(dim_z)]

    results = []
    for corner in itertools.product(x_corners, y_corners, z_corners):
        block_material = material[
            corner[0] : corner[0] + block_size,
            corner[1] : corner[1] + block_size,
            corner[2] : corner[2] + block_size,
        ]
        block_volume = volume[
            corner[0] : corner[0] + block_size,
            corner[1] : corner[1] + block_size,
            corner[2] : corner[2] + block_size,
        ]
        material_count = np.sum(block_material)
        volume_count = np.sum(block_volume)
        if volume_count > 0:
            results.append([corner[0], corner[1], corner[2], (volume_count - material_count) / volume_count])

    dataframe = pd.DataFrame(results, columns=["Xcorner", "Ycorner", "Zcorner", "Porosity"])
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(save_path, sep="\t", index=False)
    return dataframe
