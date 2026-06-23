# HERMES Test Catalog

This catalog describes the current pytest suite in plain language.
The suite uses small generated fixtures so the scientific contracts can be reviewed without large paper-scale datasets.

## Current Result

The expected local result in the HERMES Conda environment is:

```text
69 passed
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

`test_gui_run_pipeline_builds_expected_workflow_config`
- Inputs: `HERMESGUI.ui`, `cube_16.tif`
- Checks: the GUI Run button builds and launches a framework workflow config from table entries, sampling controls, save controls, smoothing controls, and property controls.
- Pass tolerance: input path and voxel size preserved exactly, sampling config exactly `{"mode": "grid", "volume_length": 8}`, outputs exactly `["tiff"]`, properties exactly `["surface_area"]`, and Laplacian smoothing enabled with `2` iterations.

`test_gui_run_pipeline_builds_workflow_config_for_multi_input`
- Inputs: `HERMESGUI.ui`, `small_primary_0.tif`, and `small_primary_1.tif`
- Checks: GUI Run builds and launches a framework workflow config for multi-input workflows.
- Pass tolerance: both input filenames and voxel sizes preserved exactly, sampling config exactly `{"mode": "random", "volume_length": 12, "count": 2}`, and outputs exactly `["tiff"]`.

`test_gui_adapter_builds_regular_serial_arguments`
- Input: `cube_16.tif` plus representative GUI field values
- Checks: pure GUI adapter builds the same `Regular` serial-run arguments expected by the framework.
- Pass tolerance: exact crop mode, file path, voxel size `1.0`, volume length `8`, requested count `0`, Laplacian iterations `2`, and requested TIFF/property options.

`test_gui_adapter_builds_corner_serial_arguments`
- Input: `cube_16.tif` plus two explicit GUI corner rows
- Checks: pure GUI adapter builds `Corners` serial-run arguments without needing to launch Qt.
- Pass tolerance: exact crop mode, exact corners `(0, 0, 0)` and `(4, 5, 6)`, and volume length `12`.

`test_gui_adapter_rejects_missing_outputs`
- Input: valid GUI file settings with all output checkboxes disabled
- Checks: pure GUI adapter rejects runs that would produce no output.
- Pass tolerance: raises `GuiAdapterError` with the expected output-selection message.

`test_gui_adapter_rejects_invalid_corner_row`
- Input: valid GUI file settings with a negative corner coordinate
- Checks: pure GUI adapter rejects invalid corner coordinates before calling the framework.
- Pass tolerance: raises `GuiAdapterError` with the expected invalid-corner message.

`test_gui_adapter_exports_regular_workflow_config`
- Input: `cube_16.tif` plus regular-sampling GUI field values and shared output paths
- Checks: pure GUI adapter exports a framework config for a regular grid-style workflow.
- Pass tolerance: exact input path, voxel size `1.0`, output root, output paths for TIFF and properties, outputs `["tiff", "properties"]`, properties `["surface_area", "porosity"]`, and sampling config `{"mode": "grid", "volume_length": 8}`.

`test_gui_adapter_exports_separate_output_paths`
- Input: `cube_16.tif` plus GUI output selections using separate TIFF, DAT, STL, and property paths.
- Checks: pure GUI adapter exports explicit framework output paths instead of requiring one shared output root.
- Pass tolerance: exact output paths for `tiff`, `dat`, `stl`, and `properties`.

`test_gui_adapter_exports_multi_input_workflow_config`
- Inputs: `small_primary_0.tif` and `small_primary_1.tif` plus regular-sampling GUI field values.
- Checks: pure GUI adapter exports a framework `inputs` list for multi-input workflows.
- Pass tolerance: exact input paths, voxel sizes `1.0` and `2.0`, no single `input` block, and sampling config exactly `{"mode": "grid", "volume_length": 12}`.

`test_gui_adapter_exports_corner_workflow_config`
- Input: `cube_16.tif` plus two explicit GUI corner rows and shared output paths
- Checks: pure GUI adapter exports a framework config for explicit-corner sampling.
- Pass tolerance: exact output root and sampling config with corners `[[0, 0, 0], [4, 5, 6]]` and size `12`.

`test_gui_adapter_exports_advanced_property_config`
- Input: valid GUI field values with min/max extents, fiber diameter, pore distribution, fiber angle, and fiber length selected
- Checks: pure GUI adapter exports advanced GUI property selections into the shared config schema.
- Pass tolerance: exact exported property list and exact property options for fiber sphere size, pore sphere size, and reference plane.

`test_gui_save_settings_embeds_framework_config`
- Inputs: `HERMESGUI.ui`, `cube_16.tif`, and a mocked settings-save path
- Checks: the GUI `Save Settings` workflow writes the legacy GUI settings plus an embedded framework `workflowConfig`.
- Pass tolerance: saved JSON contains `workflowConfig`, output root is exact, outputs are exactly `["tiff", "properties"]`, and properties are exactly `["surface_area", "porosity"]`.

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

`test_serial_pipeline_exported_tiff_and_dat_preserve_known_crop_content`
- Input: `cube_16.tif`
- Checks: a regular crop exported as TIFF and sparse DAT preserves the known binary crop content.
- Pass tolerance: exported TIFF shape exactly `(8, 8, 8)`, material count exactly `512`, and the reloaded DAT padded interior exactly equals the exported TIFF mask.

`test_serial_pipeline_corner_sampling_writes_one_output_per_corner`
- Input: `small_primary_0.tif`
- Checks: two requested corners produce two TIFF outputs.
- Pass tolerance: exactly `2` TIFF files.

`test_random_sampling_small_jobs_write_requested_output_count`
- Input: `solid_primary_24.tif`
- Checks: four requested random subvolumes produce four TIFF outputs.
- Pass tolerance: exactly `4` TIFF files.

`test_serial_pipeline_writes_complete_property_schema_for_fiber_fixture`
- Input: `fiber_angle_48.tif`
- Checks: a full property-table run writes every selected property column with one value per header entry.
- Pass tolerance: exact expected schema, one row, row length equals header length, positive fiber diameter, nonnegative fiber-diameter standard deviation, and porosity `< 1.0`.

`test_multi_primary_random_sampling_distributes_outputs_across_input_volumes`
- Inputs: `small_primary_0.tif`, `small_primary_1.tif`, `small_primary_2.tif`
- Checks: random sampling can distribute requested samples across multiple primary volumes.
- Pass tolerance: exactly `6` TIFF files and exactly `2` outputs for each primary volume.

`test_large_random_sampling_uses_local_parallel_dispatch`
- Input: `solid_primary_24.tif`
- Checks: the local multiprocessing dispatch path is used for large random-sampling jobs.
- Pass tolerance: exactly `1001` submitted local-parallel tasks and each task receives the expected surface settings.

## Config Runner

`test_run_config_writes_known_cube_outputs`
- Input: generated `config_cube.tif` from a JSON config file
- Checks: the shared workflow runner writes input TIFF, STL, sparse DAT, and property-table outputs.
- Pass tolerance: closed volume `512 +/- 80`, porosity `1 - 512 / 16^3 +/- 0.03`, STL file exists with nonzero size, DAT reloads to shape `(18, 18, 18)`, and DAT material count exactly `512`.

`test_python_module_run_entrypoint_uses_json_config`
- Input: JSON config file that generates `config_cube.tif`
- Checks: the exact `python -m hermes run CONFIG.json` entry point runs the shared config workflow.
- Pass tolerance: return code `0`, stdout contains `config_cube`, STL file exists with nonzero size, DAT file exists, and property table exists.

`test_config_runner_explicit_crop_preserves_known_tiff_content`
- Input: JSON config file that generates a larger binary cube volume and crops the exact material cube.
- Checks: config-driven explicit-corner cropping preserves TIFF and DAT content and computes near-zero porosity for the all-material crop.
- Pass tolerance: TIFF shape exactly `(8, 8, 8)`, TIFF material count exactly `512`, DAT shape exactly `(10, 10, 10)`, DAT material count exactly `512`, closed volume `512 +/- 80`, and porosity `0.0 +/- 0.03`.

`test_run_config_accepts_gui_settings_with_embedded_workflow_config`
- Input: GUI-style settings JSON containing an embedded `workflowConfig`
- Checks: `run_config()` accepts the GUI settings file directly and runs the embedded framework workflow.
- Pass tolerance: result name exactly `gui_cube`, TIFF output exists, and property table exists.

`test_config_runner_computes_advanced_gui_properties`
- Input: JSON config selecting min/max extents, fiber diameter, and pore distribution
- Checks: config-driven workflow computes advanced GUI property selections through the shared framework.
- Pass tolerance: result contains `min_extents`, `max_extents`, `fiber_diameter_mean`, and `pore_size_mean`, and a property table is written.

`test_config_runner_applies_gui_surface_settings`
- Input: JSON config selecting Laplacian smoothing with `2` iterations
- Checks: config-driven workflow applies GUI-style surface settings through the shared framework.
- Pass tolerance: result name exactly `smooth_cube_laplacian2` and matching STL output exists.

`test_config_runner_writes_gui_style_separate_output_paths`
- Input: JSON config with GUI-style separate output paths for TIFF, DAT, STL, and property files.
- Checks: config-driven workflow writes each selected output to the explicit GUI-style location.
- Pass tolerance: TIFF, DAT, STL, and property files all exist at the requested paths, and the returned TIFF path is exact.

`test_config_runner_processes_multi_input_workflow`
- Input: JSON config with two generated binary input volumes.
- Checks: config-driven workflow processes each input and appends both property rows into one property table.
- Pass tolerance: exact resolved input paths, exactly `2` per-input results, TIFF outputs for `multi_a` and `multi_b` exist, and the property table has one header plus two rows.

`test_sampling_helpers_make_deterministic_grid_and_seeded_random_specs`
- Input: synthetic `(24, 24, 24)` volume dimensions.
- Checks: framework sampling helpers reproduce deterministic grid behavior and seeded random behavior.
- Pass tolerance: exactly `8` grid samples, first grid corner exactly `(0, 0, 0)`, last grid corner exactly `(12, 12, 12)`, repeated seeded random corners exactly equal, and more than one unique random corner.

`test_config_runner_corner_sampling_writes_one_output_per_corner`
- Input: JSON config file with two explicit corner samples.
- Checks: config-driven sampling writes one TIFF, DAT, and property row set per requested corner.
- Pass tolerance: exactly `2` returned samples, exactly `2` TIFF files, exactly `2` DAT files, and `properties.txt` exists.

## Public API And Direct CLI

`test_public_api_segment_manual_writes_known_mask`
- Inputs: `grayscale_two_phase_24.tif`, `grayscale_two_phase_mask_24.tif`
- Checks: `hermes.segment()` writes a binary mask for manual thresholding.
- Pass tolerance: exact mask equality and porosity exact by `pytest.approx`.

`test_public_api_mesh_writes_valid_stl_for_known_cube`
- Input: `cube_16.tif`
- Checks: `hermes.mesh()` writes a nonempty STL and reports a valid volume mesh.
- Pass tolerance: STL exists with nonzero size, vertex count `> 0`, face count `> 0`, and `is_volume` exactly `True`.

`test_public_api_properties_match_known_cube`
- Input: `cube_16.tif`
- Checks: `hermes.properties()` writes a property table and returns known cube properties.
- Pass tolerance: closed volume `512 +/- 80`, porosity `1 - 512 / 16^3 +/- 0.03`, exact property header, and workspace name exactly `cube_16.tif`.

`test_segment_cli_command_writes_known_mask`
- Inputs: `grayscale_two_phase_24.tif`, `grayscale_two_phase_mask_24.tif`
- Checks: `python -m hermes segment` writes the same binary mask as the known manual threshold result.
- Pass tolerance: return code `0` and exact mask equality.

`test_mesh_and_properties_cli_commands_preserve_known_cube_contract`
- Input: `cube_16.tif`
- Checks: `python -m hermes mesh` writes a nonempty STL and `python -m hermes properties` writes known cube properties.
- Pass tolerance: both return codes `0`, STL size `> 0`, closed volume `512 +/- 80`, and porosity `1 - 512 / 16^3 +/- 0.03`.

## Mesh Cleanup And Outputs

`test_laplacian_smoothing_preserves_mesh_shape_and_marks_output_name`
- Input: `cube_16.tif`
- Checks: Laplacian smoothing runs on a known cube mesh, marks the output name, preserves array shapes, keeps finite vertices, and returns a valid volume mesh.
- Pass tolerance: name suffix `_laplacian2`, unchanged vertex and face array shapes, all finite vertices, and `checkMesh()` true.

`test_screened_poisson_reconstruction_uses_configured_depth`
- Input: `cube_16.tif`
- Checks: screened Poisson reconstruction is called when requested and receives the configured reconstruction depth.
- Pass tolerance: output name suffix `_screened_poisson4`, exactly one reconstruction call with `depth=4` and `preclean=True`, unchanged reconstructed vertex and face array shapes, and all returned vertices finite.

`test_remove_floating_islands_keeps_largest_component`
- Input: `two_islands_24.tif`
- Checks: optional island removal deletes disconnected small components and keeps one largest component.
- Pass tolerance: original mesh has more than one component, cleaned mesh has exactly one component, and cleaned face count is lower than original face count.
- Note: this test requires PyMeshLab and is skipped if PyMeshLab is unavailable.

`test_fix_mesh_runs_repair_filters_and_returns_valid_mesh`
- Input: `cube_16.tif`
- Checks: mesh repair runs the expected cleanup filter sequence and returns a repaired mesh object.
- Pass tolerance: output name suffix `_Fixed`, exact expected repair-filter sequence, and `checkMesh()` true for the repaired mesh.

`test_centerline_analysis_writes_direction_map_with_expected_columns`
- Input: `fiber_angle_48.tif`
- Checks: centerline analysis writes a voxel direction map with coordinate and vector columns.
- Pass tolerance: output file exists, has exactly `6` columns, has one row per material voxel, and all values are finite.

## Properties

`test_framework_legacy_property_row_matches_known_cube_schema`
- Input: `cube_16.tif`
- Checks: framework-level legacy property row construction preserves the current selected-property schema.
- Pass tolerance: exact expected header, STL name exactly `cube`, closed volume `512 +/- 80`, and porosity `1 - 512 / 16^3 +/- 0.03`.

`test_framework_legacy_property_writer_preserves_table_contract`
- Input: `cube_16.tif`
- Checks: framework-level legacy property writer emits the current tab-delimited table contract.
- Pass tolerance: exact expected header, exactly one row, closed volume `512 +/- 80`, and porosity `1 - 512 / 16^3 +/- 0.03`.

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

`test_directional_porosity_plot_is_written`
- Input: synthetic porosity series
- Checks: the directional porosity plotting helper writes a figure file.
- Pass tolerance: PNG output exists and has nonzero file size.

## MPI

`test_mpi_environment_is_discoverable`
- Inputs: none
- Checks: `mpirun` and `mpi4py` availability.
- Pass tolerance: present, or skipped if MPI is unavailable.

`test_mpi_tiny_fixture_matches_serial_contract`
- Input: `cube_16.tif`
- Checks: two-rank MPI CLI run completes one volume and writes expected outputs.
- Pass tolerance: return code `0`, stdout contains `Completed 1 volumes`, exactly one STL is written, and `properties.txt` exists.

`test_mpi_framework_processes_corner_samples_with_serial_backend`
- Input: `small_primary_0.tif`
- Checks: the package MPI sample runner uses the shared serial backend for two explicit corner samples.
- Pass tolerance: exactly two result messages are returned and exactly two TIFF outputs are written.

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
