"""Command-line interface for small HERMES workflows."""

from __future__ import annotations

import argparse
import json

import hermes
from hermes.workflow import run_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes", description="Run HERMES workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run a HERMES workflow from a JSON config file.")
    run.add_argument("config", help="Path to a HERMES JSON config file.")

    segment = subparsers.add_parser("segment", help="Segment a grayscale TIFF volume.")
    segment.add_argument("input", help="Input grayscale TIFF volume.")
    segment.add_argument("output", help="Output binary TIFF or DAT volume.")
    segment.add_argument("--method", default="otsu", help="Threshold method: manual, otsu, li, yen, isodata, triangle, or adaptive.")
    segment.add_argument("--phase", choices=("lighter", "darker"), default="lighter", help="Whether material is lighter or darker than the threshold.")
    segment.add_argument("--min", dest="minimum", type=int, default=0, help="Manual lower threshold.")
    segment.add_argument("--max", dest="maximum", type=int, default=255, help="Manual upper threshold.")
    segment.add_argument("--block-size", type=int, default=51, help="Odd block size for adaptive thresholding.")
    segment.add_argument("--offset", type=float, default=10, help="Offset for adaptive thresholding.")
    segment.add_argument("--voxel-size", type=float, default=1.0, help="Voxel size to store when writing DAT output.")

    mesh = subparsers.add_parser("mesh", help="Generate an STL mesh from a binary volume.")
    mesh.add_argument("input", help="Input binary TIFF or DAT volume.")
    mesh.add_argument("output", help="Output STL file.")
    mesh.add_argument("--voxel-size", type=float, default=1.0, help="Input voxel size.")
    mesh.add_argument("--no-pad", action="store_true", help="Disable one-voxel zero padding before meshing.")

    properties = subparsers.add_parser("properties", help="Compute basic geometric properties for a binary volume.")
    properties.add_argument("input", help="Input binary TIFF or DAT volume.")
    properties.add_argument("output", help="Output tab-delimited property table.")
    properties.add_argument("--voxel-size", type=float, default=1.0, help="Input voxel size.")
    properties.add_argument("--no-pad", action="store_true", help="Disable one-voxel zero padding before meshing.")

    args = parser.parse_args(argv)
    if args.command == "run":
        result = run_config(args.config)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "segment":
        result = hermes.segment(
            args.input,
            args.output,
            method=args.method,
            phase=args.phase,
            minimum=args.minimum,
            maximum=args.maximum,
            block_size=args.block_size,
            offset=args.offset,
            voxel_size=args.voxel_size,
        )
        print(json.dumps({"output": args.output, "porosity": result.porosity}, indent=2, sort_keys=True))
        return 0
    if args.command == "mesh":
        result = hermes.mesh(args.input, args.output, voxel_size=args.voxel_size, pad=not args.no_pad)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "properties":
        result = hermes.properties(args.input, args.output, voxel_size=args.voxel_size, pad=not args.no_pad)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
