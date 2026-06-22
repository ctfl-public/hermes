"""Command-line interface for small HERMES workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile as tiff

from hermes.pipeline import run_volume_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes", description="Run HERMES workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    quickstart = subparsers.add_parser(
        "quickstart",
        help="Generate a tiny synthetic volume and run the basic HERMES pipeline.",
    )
    quickstart.add_argument(
        "--output",
        default="hermes-quickstart-output",
        help="Directory for generated input and HERMES outputs.",
    )
    quickstart.add_argument("--voxel-size", type=float, default=1.0, help="Voxel size for the synthetic volume.")

    args = parser.parse_args(argv)
    if args.command == "quickstart":
        return run_quickstart(args.output, args.voxel_size)

    parser.error(f"Unknown command: {args.command}")
    return 2


def run_quickstart(output: str | Path, voxel_size: float = 1.0) -> int:
    output = Path(output)
    input_dir = output / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    input_path = input_dir / "quickstart_cube.tif"
    volume = np.zeros((16, 16, 16), dtype=np.uint8)
    volume[4:12, 4:12, 4:12] = 1
    tiff.imwrite(input_path, volume, imagej=True)

    result = run_volume_pipeline(
        input_path,
        voxel_size,
        output,
        name="quickstart_cube",
        outputs=("stl", "dat", "properties"),
        properties=("surface_area", "closed_volume", "volume_by_area", "porosity"),
    )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
