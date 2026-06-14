# Examples

<!-- TODO: Decide whether this file should be titled `Examples` or `Example Workflows` before the first public push. -->

This document describes the public examples that should accompany HERMES.
Large XRCT datasets are not included in this repository draft.
Small generated examples should mirror the same scientific workflows.

## 1. Synthetic Fiber Validation

<!-- TODO: Convert this from a workflow description into a runnable tiny example with generated input data and expected numerical outputs. -->

This example validates feature diameter, centerline length, and fiber orientation.

Workflow:

1. Generate a binary cylinder with known radius and length.
2. Run diameter extraction.
3. Compare mean diameter against the known digital-cylinder diameter.
4. Generate angled fibers at known angles.
5. Run centerline extraction and orientation analysis.
6. Compare measured elevation, azimuth, and length to known targets.

This example represents the synthetic-fiber validation workflow.

## 2. Fibrous Material Property Distributions

<!-- TODO: Add paper-scale dataset notes and a reduced runnable example that demonstrates primary-volume count, sample count, and sub-volume length studies. -->

This example compares fibrous materials using porosity and feature-size distributions.

Workflow:

1. Provide multiple primary fibrous volumes.
2. Segment or load binarized TIFF stacks.
3. Generate random sub-volumes.
4. Compute porosity and fiber diameter for each sub-volume.
5. Build distribution plots.
6. Repeat for different primary-volume counts, sample counts, and sub-volume lengths.

This example represents FiberForm-style analysis of fibrous carbon materials.

## 3. Woven C/C Property Distributions

<!-- TODO: Add the exact paper-scale input dimensions, sampled volume count, sampled volume size, voxel size, and computed output properties. -->

This example demonstrates property distributions for structured woven material.

Workflow:

1. Load a binarized woven C/C volume.
2. Randomly sample sub-volumes of selected size.
3. Generate STL meshes.
4. Compute surface area, porosity, closed volume, and volume-to-area ratio.
5. Plot distributions and mean values.

This example represents property-distribution analysis for a structured woven composite.

## 4. Irregular RTV Pore-Size Analysis

<!-- TODO: Add the exact paper-scale RTV dimensions, voxel size, thermal degradation condition, bin count, and pore-size settings. -->

This example demonstrates pore-size analysis for an unstructured material.

Workflow:

1. Segment or load a binarized RTV volume.
2. Use full-volume or deterministic sampling.
3. Invert the binary image so voids are the active phase.
4. Compute the Euclidean distance transform.
5. Detect local maxima in the void domain.
6. Build a pore-diameter probability distribution.

This example represents pore-size analysis for thermally degraded RTV silicone.

## 5. Directional Porosity Mapping

<!-- TODO: Confirm whether directional porosity should remain a documented example or move to post-processing documentation. -->

This example quantifies spatial porosity variation.

Workflow:

1. Load material and total-volume masks.
2. Compute porosity profiles along `x`, `y`, and `z`.
3. Save tabular porosity data.
4. Plot directional porosity.
5. Optionally compute a 3D blockwise porosity map.

## 6. MPI Scaling Workflow

<!-- TODO: Add the paper-scale rank counts, volume sizes, memory values, serial times, parallel times, and speedups. -->

This example evaluates high-throughput performance for large sampled ensembles.

Workflow:

1. Run a representative serial job and record wall time.
2. Run MPI jobs with increasing rank counts.
3. Keep workload per rank consistent for scaling studies.
4. Measure wall time and memory.
5. Compute speedup.

```text
speedup = serial time / parallel time
```

## Example Data Policy

<!-- TODO: Decide which generated fixtures will be committed as examples and which paper datasets will be linked externally. -->

The public repository should include small generated fixtures for testing and documentation.
Large XRCT datasets should be linked externally or described with instructions if they cannot be redistributed.
