"""Subvolume sampling helpers for HERMES workflows."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import random


@dataclass(frozen=True)
class SubvolumeSpec:
    corner: tuple[int, int, int]
    size: tuple[int, int, int] | None
    label: str


def full_volume_spec() -> list[SubvolumeSpec]:
    """Return a single full-volume sampling specification."""
    return [SubvolumeSpec((0, 0, 0), None, "Full")]


def corner_specs(corners, size) -> list[SubvolumeSpec]:
    """Return explicit-corner subvolume specifications."""
    size = _normalize_size(size)
    specs = []
    for index, corner in enumerate(corners):
        corner = tuple(int(value) for value in corner)
        specs.append(SubvolumeSpec(corner, size, f"V{index}_{corner[0]}-{corner[1]}-{corner[2]}-{size[0]}"))
    return specs


def grid_specs(volume_shape, voxel_size: float, volume_length: float) -> list[SubvolumeSpec]:
    """Return deterministic non-overlapping grid subvolume specifications."""
    block_size = int(volume_length / voxel_size)
    dimensions = [int(length * voxel_size / volume_length) for length in volume_shape]
    corners = itertools.product(
        [index * block_size for index in range(dimensions[0])],
        [index * block_size for index in range(dimensions[1])],
        [index * block_size for index in range(dimensions[2])],
    )
    return corner_specs(corners, (block_size, block_size, block_size))


def random_specs(volume_shape, voxel_size: float, volume_length: float, count: int, seed: int | None = None):
    """Return seeded uniform-random subvolume specifications."""
    rng = random.Random(seed)
    block_size = int(volume_length / voxel_size)
    specs = []
    for index in range(count):
        corner = (
            rng.randint(0, int(volume_shape[0] - block_size)),
            rng.randint(0, int(volume_shape[1] - block_size)),
            rng.randint(0, int(volume_shape[2] - block_size)),
        )
        specs.append(SubvolumeSpec(corner, (block_size, block_size, block_size), f"V{index}_{corner[0]}-{corner[1]}-{corner[2]}-{block_size}"))
    return specs


def specs_from_config(config: dict, volume_shape, voxel_size: float) -> list[SubvolumeSpec]:
    """Build subvolume specifications from a sampling config dictionary."""
    mode = config.get("mode", "full")
    if mode == "full":
        return full_volume_spec()
    if mode == "corners":
        return corner_specs(config["corners"], config["size"])
    if mode == "grid":
        return grid_specs(volume_shape, voxel_size, config["volume_length"])
    if mode == "random":
        return random_specs(
            volume_shape,
            voxel_size,
            config["volume_length"],
            int(config["count"]),
            seed=config.get("seed"),
        )
    raise ValueError(f"Unknown sampling mode: {mode}")


def _normalize_size(size) -> tuple[int, int, int]:
    if isinstance(size, (int, float)):
        value = int(size)
        return value, value, value
    return tuple(int(value) for value in size)
