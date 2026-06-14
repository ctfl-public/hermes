#!/usr/bin/env python3
"""Generate small analytical fixtures for HERMES tests."""

from __future__ import annotations

from pathlib import Path


def _require_deps():
    try:
        import numpy as np
        import tifffile as tiff
    except ImportError as exc:
        raise SystemExit(
            "Fixture generation requires numpy and tifffile. "
            "Activate the HERMES environment before running this script."
        ) from exc
    return np, tiff


def write_chen_dat(path, volume, voxel_size=1.0):
    np, _ = _require_deps()
    coords = np.column_stack(np.where(volume > 0))
    with open(path, "w", encoding="utf-8") as f:
        sx, sy, sz = volume.shape
        f.write(f"{sx} {sy} {sz} {voxel_size * 1e-6}\n")
        f.write("i j k voxel")
        for x, y, z in coords:
            f.write(f"\n{x + 1} {y + 1} {z + 1} 1")


def make_cylinder(shape, axis, radius, margin=4):
    np, _ = _require_deps()
    grid = np.indices(shape)
    center = [(s - 1) / 2.0 for s in shape]
    if axis == "x":
        dist = np.sqrt((grid[1] - center[1]) ** 2 + (grid[2] - center[2]) ** 2)
        length_mask = (grid[0] >= margin) & (grid[0] < shape[0] - margin)
    elif axis == "y":
        dist = np.sqrt((grid[0] - center[0]) ** 2 + (grid[2] - center[2]) ** 2)
        length_mask = (grid[1] >= margin) & (grid[1] < shape[1] - margin)
    elif axis == "z":
        dist = np.sqrt((grid[0] - center[0]) ** 2 + (grid[1] - center[1]) ** 2)
        length_mask = (grid[2] >= margin) & (grid[2] < shape[2] - margin)
    else:
        raise ValueError(axis)
    return ((dist <= radius) & length_mask).astype("uint8")


def make_angled_fiber(shape=(48, 48, 48), radius=3.0, angle_deg=22.34):
    np, _ = _require_deps()
    coords = np.indices(shape).astype(float)
    center = np.array([(s - 1) / 2.0 for s in shape])
    points = np.moveaxis(coords, 0, -1) - center
    theta = np.deg2rad(angle_deg)
    # Direction in x-z plane, matching the paper-style elevation validation.
    direction = np.array([np.sin(theta), 0.0, np.cos(theta)])
    projection = np.sum(points * direction, axis=-1)
    closest = projection[..., None] * direction
    radial = np.linalg.norm(points - closest, axis=-1)
    length_mask = np.abs(projection) < 18
    return ((radial <= radius) & length_mask).astype("uint8")


def generate_fixtures(root: Path):
    np, tiff = _require_deps()
    root.mkdir(parents=True, exist_ok=True)

    cube = np.zeros((16, 16, 16), dtype="uint8")
    cube[4:12, 5:13, 3:11] = 1
    tiff.imwrite(root / "cube_16.tif", cube, imagej=True)
    write_chen_dat(root / "cube_16.dat", cube)

    tiff.imwrite(root / "empty_8.tif", np.zeros((8, 8, 8), dtype="uint8"), imagej=True)

    islands = np.zeros((24, 24, 24), dtype="uint8")
    islands[4:14, 4:14, 4:14] = 1
    islands[19:21, 19:21, 19:21] = 1
    tiff.imwrite(root / "two_islands_24.tif", islands, imagej=True)

    two_phase = np.full((24, 24, 24), 1000, dtype="uint16")
    two_phase[6:18, 6:18, 6:18] = 50000
    tiff.imwrite(root / "grayscale_two_phase_24.tif", two_phase, imagej=True)
    tiff.imwrite(root / "grayscale_two_phase_mask_24.tif", (two_phase > 10000).astype("uint8"), imagej=True)

    x = np.linspace(0, 50000, 24, dtype="float32")
    gradient = np.broadcast_to(x[None, None, :], (24, 24, 24)).astype("uint16")
    gradient[8:16, 8:16, 8:16] = 60000
    tiff.imwrite(root / "grayscale_gradient_24.tif", gradient, imagej=True)

    for axis in ("x", "y", "z"):
        tiff.imwrite(root / f"fiber_{axis}_48.tif", make_cylinder((48, 48, 48), axis, 5), imagej=True)
    tiff.imwrite(root / "fiber_angle_48.tif", make_angled_fiber(), imagej=True)

    porous = np.ones((24, 24, 24), dtype="uint8")
    porous[6:18, 6:18, 6:18] = 0
    tiff.imwrite(root / "porous_block_24.tif", porous, imagej=True)

    layered = np.ones((24, 24, 24), dtype="uint8")
    layered[:, :, 0:6] = 0
    layered[:, :, 12:18] = 0
    tiff.imwrite(root / "layered_porosity_24.tif", layered, imagej=True)

    for idx, offset in enumerate((0, 2, 4)):
        primary = np.zeros((24, 24, 24), dtype="uint8")
        primary[4 + offset : 12 + offset, 4:12, 4:12] = 1
        tiff.imwrite(root / f"small_primary_{idx}.tif", primary, imagej=True)

    tiff.imwrite(root / "solid_primary_24.tif", np.ones((24, 24, 24), dtype="uint8"), imagej=True)


if __name__ == "__main__":
    generate_fixtures(Path(__file__).resolve().parents[1] / "tests" / "fixtures")
