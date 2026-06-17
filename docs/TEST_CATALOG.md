# HERMES Test Catalog

This catalog describes the current pytest suite in plain language.
The suite uses small generated fixtures so the scientific contracts can be reviewed without large paper-scale datasets.

## Current Result

The expected local result in the HERMES Conda environment is:

```text
29 passed
```

The MPI test may need permission for `mpirun` to open local communication sockets in sandboxed environments.

## Segmentation

`test_global_thresholds_recover_known_bright_cube`
- Inputs: `grayscale_two_phase_24.tif`, `grayscale_two_phase_mask_24.tif`
- Methods: Otsu, Li, Yen, Isodata, Triangle
- Checks: thresholded mask matches the known bright cube.
- Pass tolerance: mismatch fraction `< 0.01`.

`test_manual_threshold_recovers_exact_known_bright_cube`
- Inputs: `grayscale_two_phase_24.tif`, `grayscale_two_phase_mask_24.tif`
- Checks: manual range `(10000, 65535)` exactly recovers the known mask and porosity.
- Pass tolerance: exact mask equality and porosity exact by `pytest.approx`.

`test_darker_greys_selects_complement_of_lighter_phase`
- Input: `grayscale_two_phase_24.tif`
- Checks: dark-phase selection is the exact complement of light-phase selection.
- Pass tolerance: exact mask equality against the complement.

`test_adaptive_threshold_runs_on_gradient_fixture_and_returns_material_phase`
- Input: `grayscale_gradient_24.tif`
- Checks: adaptive thresholding returns a boolean mask with the original shape and selects material in the embedded cube.
- Pass tolerance: at least one selected voxel in `[8:16, 8:16, 8:16]`.

`test_gui_segmentation_thread_matches_manual_analytical_mask`
- Inputs: `grayscale_two_phase_24.tif`, `grayscale_two_phase_mask_24.tif`
- Checks: GUI `SegmentationThread` manual thresholding matches the analytical mask and porosity.
- Pass tolerance: exact mask equality and porosity exact by `pytest.approx`.

## GUI

`test_gui_import_and_required_widgets_exist`
- Input: `HERMESGUI.ui` through `HERMES.py`
- Checks: GUI imports and required widgets/buttons exist.
- Pass tolerance: all listed widget names must be found.

## IO And Mesh

`test_load_tiff_preserves_known_cube_shape_and_material_count`
- Input: `cube_16.tif`
- Checks: TIFF loading preserves shape and material count.
- Pass tolerance: shape exactly `(16, 16, 16)` and nonzero count exactly `512`.

`test_load_tiff_and_dat_represent_same_known_cube`
- Inputs: `cube_16.tif`, `cube_16.dat`
- Checks: TIFF and DAT imports represent the same cube.
- Pass tolerance: exact shape equality and exact binary volume equality.

`test_padding_adds_one_voxel_border_and_preserves_material_count`
- Input: `cube_16.tif`
- Checks: padding adds a one-voxel zero border and preserves material count.
- Pass tolerance: shape exactly `(18, 18, 18)`, count exactly `512`, and checked borders exactly zero.

`test_marching_cubes_cube_mesh_has_analytical_volume_within_voxel_tolerance`
- Input: `cube_16.tif`
- Checks: marching cubes produces vertices, faces, a watertight mesh, finite area, and cube-like volume.
- Pass tolerance: `abs(abs(mesh.volume) - 512.0) < 80.0`.

`test_chen_writer_round_trips_known_cube`
- Input: `cube_16.tif`, temporary DAT output
- Checks: DAT writer output reloads to the original binary volume.
- Pass tolerance: exact binary volume equality after write/read round trip.

## Serial Pipeline

`test_serial_pipeline_writes_properties_for_known_cube`
- Input: `cube_16.tif`
- Checks: serial pipeline writes one property row, one STL, expected property columns, and porosity.
- Pass tolerance: porosity `1 - 512 / 16^3` with `abs=0.03`.

`test_serial_pipeline_corner_sampling_writes_one_output_per_corner`
- Input: `small_primary_0.tif`
- Checks: two requested corners produce two TIFF outputs.
- Pass tolerance: exactly `2` TIFF files.

`test_random_sampling_small_jobs_write_requested_output_count`
- Input: `solid_primary_24.tif`
- Checks: four requested random subvolumes produce four TIFF outputs.
- Pass tolerance: exactly `4` TIFF files.

## Properties

`test_fiber_diameter_for_known_cylinder_is_within_voxel_tolerance`
- Input: `fiber_z_48.tif`
- Checks: synthetic digital-cylinder fiber diameter and standard deviation.
- Pass tolerance: mean diameter `8.5 +/- 0.75` and standard deviation `< 1.0`.

`test_pore_distribution_for_known_void_cube_is_finite_and_near_expected_size`
- Input: `porous_block_24.tif`
- Checks: pore distribution is nonempty and near the known void size.
- Pass tolerance: mean pore `11.5 +/- 2.0` and standard deviation `>= 0`.

`test_mesh_based_porosity_for_known_cuboid_is_close_to_analytical_value`
- Input: `cube_16.tif`
- Checks: mesh-derived porosity agrees with analytical cuboid porosity.
- Pass tolerance: analytical porosity with `abs=0.03`.

`test_single_angled_fiber_orientation_matches_current_reference_plane_convention`
- Input: `fiber_angle_48.tif`
- Checks: centerline azimuth, out-of-plane elevation, and length under the current reference-plane convention.
- Pass tolerance: azimuth `90.0 - 22.34 +/- 3.0` degrees, elevation `0.0 +/- 3.0` degrees, and length `36.0 +/- 8.0`.

## Directional Porosity

`test_directional_porosity_matches_known_layered_volume`
- Input: `layered_porosity_24.tif`
- Checks: 1D porosity by layer.
- Pass tolerance: locations exactly `[1, 6.0, 12.0, 18.0]` and porosity approximately `[1.0, 0.0, 1.0, 0.0]`.

`test_porosity_3d_map_matches_known_block_values`
- Input: `layered_porosity_24.tif`
- Checks: 3D porosity map file, row count, and valid porosity values.
- Pass tolerance: file exists, exactly `4 * 4 * 4` rows, and porosity values only `{0.0, 1.0}`.

## MPI

`test_mpi_environment_is_discoverable`
- Inputs: none
- Checks: `mpirun` and `mpi4py` availability.
- Pass tolerance: present, or skipped if MPI is unavailable.

`test_mpi_tiny_fixture_matches_serial_contract`
- Input: `cube_16.tif`
- Checks: two-rank MPI CLI run completes one volume and writes expected outputs.
- Pass tolerance: return code `0`, stdout contains `Completed 1 volumes`, exactly one STL is written, and `properties.txt` exists.

## Workspace Core

`test_workspace_segments_known_grayscale_volume_and_extracts_subvolume`
- Inputs: `grayscale_two_phase_24.tif`, `grayscale_two_phase_mask_24.tif`
- Checks: `Workspace.segment()` matches the known mask and subvolume extraction preserves shape, count, origin, and name.
- Pass tolerance: exact mask equality, shape `(12, 12, 12)`, count `1728`, and origin `(6, 6, 6)`.

`test_workspace_mesh_and_properties_match_known_cube_scale`
- Input: `cube_16.tif`
- Checks: workspace mesh validity, closed volume, porosity, and finite surface area.
- Pass tolerance: closed volume `512 +/- 80` and porosity `1 - 512 / 16^3 +/- 0.025`.

`test_workspace_saves_properties_table`
- Input: `cube_16.tif`
- Checks: workspace property table header and workspace name.
- Pass tolerance: header starts with `WorkspaceName`, `surface_area`, and `closed_volume`, and the file includes `cube_16.tif`.

## Fixture Generator

`scripts/make_test_fixtures.py` creates all small synthetic volumes used by the tests.
The fixtures include binary cubes, sparse DAT files, two-phase grayscale volumes, gradient thresholding volumes, straight and angled fibers, a porous block, layered porosity volumes, and small primary volumes for sampling tests.
