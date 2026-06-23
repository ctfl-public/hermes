# Quick Start

This guide introduces the basic HERMES workflow without requiring users to edit source files.
It uses a tiny generated cube example so the commands run quickly and the outputs are easy to inspect.

## 1. Activate HERMES

Run commands from the repository root with the Conda environment active.

```bash
conda activate hermes
```

## 2. Run The Example Config

The example config generates a small binary cube, writes voxel and mesh outputs, and computes basic properties.

```bash
python -m hermes run examples/quickstart/config.json
```

The config writes:

- `examples/quickstart/input/quickstart_cube.tif`
- `examples/quickstart/output/stl/quickstart_cube.stl`
- `examples/quickstart/output/voxels/quickstart_cube.dat`
- `examples/quickstart/output/properties.txt`

The property table includes surface area, closed volume, volume-to-area ratio, and porosity.
The example cube has a known material volume, so the test suite checks the output against analytical expectations.

## 3. Run Basic Commands Directly

The same fundamental tasks can be run as direct commands.
These are the simplest entry points for one-step work.

Generate an STL mesh from a binary volume.

```bash
python -m hermes mesh examples/quickstart/input/quickstart_cube.tif examples/quickstart/output/direct_cube.stl --voxel-size 1.0
```

Compute basic properties from a binary volume.

```bash
python -m hermes properties examples/quickstart/input/quickstart_cube.tif examples/quickstart/output/direct_properties.txt --voxel-size 1.0
```

Segment a grayscale TIFF using an automatic threshold.

```bash
python -m hermes segment input_grayscale.tif segmented.tif --method otsu
```

Segment a grayscale TIFF using manual thresholds.

```bash
python -m hermes segment input_grayscale.tif segmented.dat --method manual --min 10000 --max 65535 --voxel-size 1.0
```

## 4. Use HERMES From Python

The same public operations are available from Python scripts and notebooks.

```python
import hermes

hermes.segment("input_grayscale.tif", "segmented.tif", method="otsu")
hermes.mesh("segmented.tif", "mesh.stl", voxel_size=1.0)
props = hermes.properties("segmented.tif", "properties.txt", voxel_size=1.0)
result = hermes.run("examples/quickstart/config.json")
```

## What This Proves

This tutorial verifies the core install, config execution, TIFF loading, binary volume handling, padding, marching-cubes meshing, STL export, sparse DAT export, and property-table writing.
It is intentionally small so it can run quickly on a laptop.

## Current Scope

The direct CLI commands and Python API are the intended replacement direction for basic non-GUI work.
The config runner is the intended path for complete reproducible workflows.
The GUI, legacy serial script, and MPI script are still available, but they have not yet all been consolidated around this interface.
