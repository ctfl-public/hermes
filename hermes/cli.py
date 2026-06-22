"""Command-line interface for small HERMES workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hermes.pipeline import run_pipeline_config


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

    run = subparsers.add_parser("run", help="Run a HERMES workflow from a JSON config file.")
    run.add_argument("config", help="Path to a HERMES JSON config file.")

    args = parser.parse_args(argv)
    if args.command == "quickstart":
        return run_quickstart(args.output, args.voxel_size)
    if args.command == "run":
        result = run_pipeline_config(args.config)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def run_quickstart(output: str | Path, voxel_size: float = 1.0) -> int:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config_path = output / "quickstart.json"
    config = {
        "name": "quickstart_cube",
        "input": {
            "path": "input/quickstart_cube.tif",
            "voxel_size": voxel_size,
            "generate": {
                "kind": "binary_cube",
                "shape": [16, 16, 16],
                "bounds": [[4, 12], [4, 12], [4, 12]],
            },
        },
        "output_dir": ".",
        "outputs": ["stl", "dat", "properties"],
        "properties": ["surface_area", "closed_volume", "volume_by_area", "porosity"],
    }
    with config_path.open("w", encoding="utf-8") as file_obj:
        json.dump(config, file_obj, indent=2)
        file_obj.write("\n")

    result = run_pipeline_config(config_path)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
