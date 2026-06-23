# HERMES Feature Overview

This document describes the public HERMES feature set.
It is written as a standalone reference for users who want to understand what the repository can do.

## 1. Input Data

HERMES works with three-dimensional volumetric microstructure data.
The paper examples focus on XRCT and micro-CT datasets, but the current code operates on supported 3D TIFF and sparse voxel DAT volumes rather than on XRCT acquisition metadata itself.

- **TIFF stacks**: HERMES can load grayscale and binary 3D TIFF volumes.
- **Sparse voxel DAT files**: HERMES can load voxel files with coordinate and occupancy data.
- **Multiple primary volumes**: HERMES can sample from more than one large reconstructed volume to reduce bias and better capture material variability.
- **Voxel-size metadata**: HERMES uses the physical voxel size of each input to report mesh and feature measurements in physical units.

## 2. Material Segmentation

<!-- TODO: Mark which thresholding methods are available in the GUI, CLI, Python API, and config runner after thresholding is unified. -->

Segmentation classifies each voxel as material or void.
HERMES supports both manual and automatic segmentation workflows.

### Manual Thresholding

Manual thresholding uses user-provided minimum and maximum grayscale values for the material phase.
This is useful when material and void intensities are cleanly separated.

### Automatic Thresholding

HERMES includes several automatic thresholding methods from scikit-image.

- **Variance-based global thresholding** selects a threshold by minimizing intensity variance within the separated classes.
- **Minimum cross-entropy thresholding** uses an iterative entropy criterion to separate material and void intensities.
- **Automatic multilevel thresholding** uses an entropy-based criterion for foreground-background separation.
- **Locally adaptive thresholding** computes local thresholds from a user-defined block size.
- **Iterative intermeans thresholding** is available in the current GUI.
- **Histogram-shape thresholding** is available in the current GUI.

HERMES supports both lighter-material and darker-material phase selection.

## 3. Sub-Volume Sampling

HERMES is designed to generate property distributions from many sampled sub-volumes.

### Uniform Random Sampling

Uniform random sampling selects random starting corners inside each primary volume.
Overlap between sampled sub-volumes is allowed.
This mode is useful when a large ensemble of random samples is desired.

### Deterministic Grid Sampling

Deterministic sampling partitions a primary volume into a Cartesian grid of non-overlapping sub-volumes.
This mode is useful when the user wants regular coverage or wants to avoid missing irregular features.

### Explicit Corner Sampling

Explicit corner sampling extracts sub-volumes from user-provided `(x, y, z)` coordinates.
This mode supports targeted inspection and reproducible single-volume studies.

### Multi-Primary Sampling

HERMES can distribute a requested sample count across several primary volumes.
This supports studies where no single scan should dominate the property distribution.

## 4. Voxel-To-Surface Reconstruction

HERMES converts binary voxel volumes to triangulated surface meshes.

- **Padding** adds a zero-valued border around sampled volumes before meshing.
- **Marching cubes** generates triangular surfaces from binarized data.
- **Physical scaling** converts voxel coordinates to physical coordinates using voxel size.
- **STL export** writes triangulated surfaces for downstream tools.
- **TIFF and DAT export** writes cropped voxel representations for verification and downstream workflows.

## 5. Surface Smoothing

Voxel-derived surfaces can be jagged.
HERMES includes optional smoothing workflows.

- **Laplacian smoothing** uses Trimesh to move vertices while preserving mesh connectivity.
- **Screened Poisson reconstruction** uses PyMeshLab to reconstruct a smoother surface with a user-selected reconstruction depth.

Laplacian smoothing is lighter weight.
Screened Poisson reconstruction can produce smoother remeshed surfaces at higher computational cost.

## 6. Mesh Validation And Repair

Mesh quality affects volume, area, rendering, and downstream simulation.
HERMES includes mesh checks and repair operations.

- Check whether a mesh forms a valid closed volume.
- Check watertightness.
- Remove zero-area faces.
- Remove duplicate faces and vertices.
- Repair non-manifold edges and vertices.
- Reorient faces coherently.
- Remove floating islands and disconnected components.
- Export cleaned STL meshes.

## 7. Geometric Property Extraction

HERMES computes geometric descriptors from surface meshes and voxel data.

### Closed Volume

Closed volume is computed from the triangulated surface mesh.

### Surface Area

Surface area is computed by summing the areas of mesh triangles.

### Porosity

Porosity is computed from the closed material volume and total sampled volume.

```text
porosity = (total volume - material volume) / total volume
```

### Volume-To-Area Ratio

The volume-to-area ratio is computed from closed volume and surface area.
This provides a compact descriptor of geometric scale and surface exposure.

## 8. Feature And Pore Size Distributions

HERMES computes size distributions using three-dimensional distance transforms.

### Fiber And Feature Diameter

For the material phase, HERMES computes a 3D Euclidean distance transform.
Local maxima in the distance field are converted to feature diameters.
The result can be summarized by mean and standard deviation or retained as a distribution.

### Pore Size

For pore-size analysis, HERMES inverts the binary volume so voids become the active phase.
The same distance-transform and local-maxima workflow is then applied to compute pore diameters.

## 9. Fiber Identification, Length, And Orientation

HERMES includes a centerline-based workflow for fiber-like microstructures.

### Centerline Extraction

The binary material phase is smoothed and skeletonized.
The skeleton provides one-voxel-wide centerline candidates.

### Graph Construction

Skeleton voxels are converted to a graph using 26-neighbor connectivity.
Minimum spanning tree logic is used to reduce unwanted shortcut connections.

### Branch Splitting

Branch nodes are analyzed using local direction vectors.
Divergent branches are separated so individual fiber-like paths can be identified.

### Fiber Length

Ordered centerline voxels are traversed to compute length.
Endpoint distance-transform corrections account for the distance from centerline endpoints to the fiber surface.

### Fiber Orientation

Local and mean direction vectors are used to compute azimuth and elevation angles.
Angles can be referenced to selected planes such as `XY`, `XZ`, or `YZ`.

### Direction Maps

HERMES can assign the nearest centerline direction vector to material voxels.
Direction maps can be used by downstream models that require local material orientation.

## 10. Directional Porosity

HERMES includes utilities for spatially resolved porosity analysis.

- Compute one-dimensional porosity profiles along `x`, `y`, or `z`.
- Save directional porosity tables.
- Plot directional porosity curves.
- Generate 3D blockwise porosity maps.

## 11. Property Distributions And Convergence Studies

HERMES is built for distribution-based analysis of heterogeneous materials.
Users can generate many sampled sub-volumes and compute property tables for each sample.

Supported study types include:

- varying the number of primary volumes
- varying the number of sampled sub-volumes
- varying sampled sub-volume length
- comparing fibrous material systems
- computing distributions for woven materials
- computing pore-size distributions for irregular porous materials.

## 12. Parallel And MPI Execution

<!-- TODO: Revisit this section after serial, local parallel, and MPI execution share one backend. -->

HERMES supports several execution modes.

- **Serial execution** processes samples one at a time.
- **Local multiprocessing** supports high-throughput processing on one machine.
- **MPI execution** distributes sampled sub-volume tasks across ranks on HPC systems.

The MPI workflow is intended for large ensembles where hundreds of sub-volumes may be processed concurrently.

## 13. Memory Monitoring And Scaling

Large volumetric-image workflows can be limited by memory.
HERMES workflows can track memory and timing data for resource planning.

- Resident set size.
- Virtual memory size.
- Python allocation peaks.
- Wall-clock runtime.
- Speedup for parallel runs.

These measurements help estimate how many structures can safely run at once on a node.

## 14. User Interfaces

<!-- TODO: Replace the cleanup note below with stable interface documentation once the GUI and script paths are unified. -->

HERMES currently provides several user-facing entry points.

- A PyQt GUI for interactive setup, segmentation, previewing, and execution.
- Direct command-line commands for segmentation, meshing, property extraction, config execution, and MPI execution.
- A Python API for scripts and notebooks.
- JSON config files for reproducible batch workflows.
- Directional porosity utilities for post-processing.

The planned cleanup will consolidate these entry points around one shared backend while preserving the scientific feature set.
