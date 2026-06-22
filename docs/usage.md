# Usage

HERMES currently provides three main entry points.

- `python -m hermes quickstart` runs a tiny no-edit workflow for installation checks and first-time use.
- `HERMES.py` runs the GUI workflow.
- `voxel2stl.py` runs the serial script workflow.
- `voxel2stl_mpi.py` runs the MPI workflow.

Activate the environment before using any workflow.

```bash
conda activate hermes
```

## Quick-Start Workflow

Run the quick-start command to generate a synthetic input volume and write HERMES outputs without editing source files.

```bash
python -m hermes quickstart --output hermes-quickstart-output
```

See [quickstart.md](quickstart.md) for the output files and expected checks.

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

## Serial Script Workflow

<!-- TODO: Add a minimal annotated `run_voxel2stl()` configuration using a tiny included TIFF fixture. -->

Edit the settings in `run_voxel2stl()` and then run the serial script.

```bash
python voxel2stl.py
```

The current script is configured by editing values in `run_voxel2stl()`.
The defaults in the current code are examples and should be replaced with local input paths, voxel sizes, save paths, sampling options, and property options before running.
The most important settings are listed below.

- `surfaceSettings` controls Laplacian smoothing, screened Poisson reconstruction, and island removal.
- `croppingFlag` selects `Regular` or `Corners`.
- `filenames` lists input TIFF or DAT files.
- `filevoxels` lists voxel sizes for each input.
- `savingOptions` controls TIFF, DAT, STL, and property outputs.
- `property_options` selects the computed properties.
- `cropSettings` controls volume length, sample count, or explicit corners.

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
