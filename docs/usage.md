# Usage

HERMES currently provides four user-facing modes.

- Direct CLI commands run basic tasks without a config file.
- `python -m hermes run CONFIG.json` runs a workflow from a JSON config file.
- `import hermes` exposes the Python API for scripts and notebooks.
- `HERMES.py` runs the GUI workflow.

Activate the environment before using any workflow.

```bash
conda activate hermes
```

## Quick-Start Workflow

The Quickstart documentation is a short tutorial for fundamental tasks.
It should be the first place new users go after installation.

See [quickstart.md](quickstart.md) for a generated-data example and direct command walkthrough.

## Direct CLI Commands

Use direct commands for single-step tasks.

```bash
python -m hermes segment input.tif segmented.tif --method otsu
python -m hermes segment input.tif segmented.dat --method manual --min 10000 --max 65535 --voxel-size 1.0
python -m hermes mesh segmented.tif mesh.stl --voxel-size 1.0
python -m hermes properties segmented.tif properties.txt --voxel-size 1.0
```

The current direct commands are:

- `segment`: threshold a grayscale TIFF and write a binary TIFF or DAT.
- `mesh`: convert a binary TIFF or DAT volume to STL.
- `properties`: compute basic geometric properties for a binary TIFF or DAT volume.

## Config Workflow

Run a workflow from a JSON config file.

```bash
python -m hermes run examples/quickstart/config.json
```

The example config generates a tiny binary cube, writes outputs to `examples/quickstart/output`, and computes surface area, closed volume, volume-to-area ratio, and porosity.
This is the first stable command shape for the unified framework.
The config runner also supports an explicit crop block with `corner` and `size` fields for reproducible sub-volume extraction.
It also supports a `sampling` block for `full`, `corners`, `grid`, and seeded `random` sub-volume generation.
Future GUI, serial, and MPI cleanup should converge on this config model.

## Python API

The same basic tasks can be called from Python.

```python
import hermes

hermes.segment("input.tif", "segmented.tif", method="otsu")
hermes.mesh("segmented.tif", "mesh.stl", voxel_size=1.0)
props = hermes.properties("segmented.tif", "properties.txt", voxel_size=1.0)
result = hermes.run("examples/quickstart/config.json")
```

The public API is intended to stay concise.
Internal helper names should not be needed for normal use.

## Legacy Script Workflows

`voxel2stl.py` remains temporarily as a deprecated compatibility wrapper.
`voxel2stl_mpi.py` remains available during cleanup and still contains legacy edit-in-source settings.
The new direct CLI, Python API, and config workflow are the intended replacement direction.

## GUI Workflow

Launch the GUI from the repository root.

```bash
python HERMES.py
```

The GUI supports adding TIFF or DAT inputs.
It supports assigning voxel sizes.
It supports selecting smoothing and island-removal options.
It supports configuring random, deterministic, or corner-based sampling.
It supports selecting TIFF, DAT, STL, and property outputs.
It supports selecting geometric properties to compute.
It supports loading grayscale TIFF data for segmentation.
It supports applying automatic or manual thresholding.
It supports previewing slices and histograms.
It supports cropping segmented volumes.
It supports rendering voxel masks.
It supports saving segmented TIFFs.

## Segmentation Workflow

The segmentation tab operates on grayscale TIFF volumes.

1. Load a grayscale TIFF stack.
2. Select whether material corresponds to lighter or darker grayscale values.
3. Choose manual thresholding or one of the automatic global, entropy-based, histogram-based, or locally adaptive thresholding options.
4. Review the segmentation overlay and histogram.
5. Optionally crop the volume.
6. Save the segmented TIFF.

The segmented TIFF can then be used as input for mesh generation and property extraction.

## Serial Workflow

Use direct CLI commands or a JSON config file for serial work.
Do not edit `voxel2stl.py` for new workflows.

## Sampling Modes

### Full Volume

In regular mode, setting volume length to `0` prioritizes full-volume processing.

### Random Sampling

In regular mode, specify a nonzero volume length and nonzero number of volumes.
HERMES selects random corners and extracts sub-volumes.

### Deterministic Grid Sampling

In regular mode, specify a nonzero volume length and set the number of volumes to `0`.
HERMES partitions the domain into non-overlapping sub-volumes.

### Explicit Corner Sampling

Use `croppingFlag = "Corners"` and provide explicit `(x, y, z)` corner tuples.

## Property Options

The current property options include:

- mesh extents
- surface area
- closed volume
- volume-to-area ratio
- porosity
- fiber diameter
- pore-size distribution
- fiber angle
- fiber length.

## Output Files

<!-- TODO: Add a concrete example output directory tree once a tiny runnable example is included. -->

Depending on selected save flags, HERMES writes several products.

- `.tif` cropped binary volumes.
- `.dat` voxel files.
- `.stl` triangulated surfaces.
- tab-delimited property files.
- skeleton files.
- direction-map files.

Output names encode the source file, sub-volume index, selected corner, volume length, and selected smoothing or cleanup settings.

## Current Interface Limits

The GUI is the current interactive interface.
The serial and MPI scripts are current script entry points, but they are configured by editing Python variables rather than command-line arguments.
The cleanup work should replace edited-in settings with a shared backend and a stable config or CLI interface.

## Directional Porosity Utilities

<!-- TODO: Update this section after hard-coded analysis paths are separated from reusable directional porosity functions. -->

`directionPorosityPlotting.py` contains helper functions for directional porosity analysis.
It can load TIFF or DAT data.
It can compute 1D porosity profiles in `x`, `y`, or `z`.
It can save porosity data.
It can plot porosity profiles.
It can generate 3D blockwise porosity maps.

The current file includes paper-specific analysis code at module level.
The cleanup should separate reusable functions from hard-coded analysis paths.
