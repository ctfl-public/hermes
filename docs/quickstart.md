# Quick Start

This guide runs a tiny HERMES workflow without editing source files.
It generates a synthetic binary cube, builds a surface mesh, writes voxel data, and computes basic geometric properties.

## Run The Example

Activate the Conda environment from the repository root.

```bash
conda activate hermes
```

Run the quick-start command.

```bash
python -m hermes quickstart --output hermes-quickstart-output
```

The command prints a JSON summary of the generated input, output files, and computed properties.

## Outputs

The quick-start command writes:

- `hermes-quickstart-output/input/quickstart_cube.tif`
- `hermes-quickstart-output/stl/quickstart_cube.stl`
- `hermes-quickstart-output/voxels/quickstart_cube.dat`
- `hermes-quickstart-output/properties.txt`

The property table includes surface area, closed volume, volume-to-area ratio, and porosity.
The example cube has a known material volume, so the test suite checks the output against analytical expectations.

## What This Proves

This quick-start verifies the core install, TIFF loading, binary volume handling, padding, marching-cubes meshing, STL export, sparse DAT export, and property-table writing.
It is intentionally small so it can run quickly on a laptop.

## Current Scope

The quick-start is the first unified command-line workflow.
The GUI, legacy serial script, and MPI script are still available, but they have not yet all been consolidated around this interface.
