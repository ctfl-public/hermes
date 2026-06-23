# Examples

This document summarizes the example workflows that HERMES is designed to support.
The repository includes a small generated quick-start example, while paper-scale XRCT datasets should be supplied by the user or linked separately when redistribution is not possible.

## Runnable Quick Start

The runnable example is the best first test of the framework.

```bash
python -m hermes run examples/quickstart/config.json
```

It generates a small binary cube, writes STL and DAT outputs, and records basic geometric properties.
See [quickstart.md](quickstart.md) for the guided walkthrough.

## Synthetic Fiber Validation

Synthetic fiber volumes are useful for checking analytical quantities.
Typical checks include feature diameter, centerline length, azimuth, and elevation against known digital geometry.
The characterization tests include reduced versions of these cases using generated straight and angled fibers.

## Fibrous Material Property Distributions

For fibrous carbon materials, a common workflow is to sample many sub-volumes from one or more primary volumes and compute porosity, feature diameter, surface area, and related distributions.
This supports convergence studies over primary-volume count, sample count, and sampled sub-volume size.

## Woven C/C Property Distributions

For structured woven composites, HERMES can sample sub-volumes, reconstruct surfaces, clean meshes, and compute property distributions such as surface area, closed volume, porosity, and volume-to-area ratio.
These workflows are typically run from JSON configs so sampling and output choices can be reproduced.

## Irregular Pore-Size Analysis

For porous or degraded materials, HERMES can invert the segmented material phase and compute pore-size distributions using distance-transform local maxima.
The reduced tests include a known porous block to protect this behavior.

## Directional Porosity Mapping

Directional porosity utilities compute one-dimensional porosity profiles along principal axes and optional 3D blockwise porosity maps.
These utilities are useful for spatial variability studies and post-processing of segmented volumes.

## MPI Scaling Studies

MPI workflows distribute sampled volume processing across ranks for larger ensembles.
A typical scaling study compares wall time and memory against rank count for a fixed workload.
See [mpi.md](mpi.md) for command and HPC guidance.
