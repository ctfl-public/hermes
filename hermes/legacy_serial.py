"""Compatibility shim for the renamed serial module.

New code should import from ``hermes.serial``.
"""

from hermes.serial import (
    get_stl_legacy,
    process_sample,
    process_single_volume_legacy,
    process_random_sample,
    run_serial,
    voxel2stl_legacy,
)

__all__ = [
    "get_stl_legacy",
    "process_sample",
    "process_single_volume_legacy",
    "process_random_sample",
    "run_serial",
    "voxel2stl_legacy",
]
