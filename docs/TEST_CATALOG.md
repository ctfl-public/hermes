# HERMES Test Catalog

This catalog describes the tests in plain language so the scientific contract can be reviewed without reading pytest code.

## Guiding Principle

Tests should compare HERMES outputs against analytical or known synthetic quantities whenever possible. Smoke tests are reserved for GUI/MPI wiring and optional dependencies.

## Test Environment

Use the canonical environment file at the repository root:

```bash
conda env create -f environment.yml
conda activate hermes
python -m pytest
```

The older environment files are platform/history snapshots. `environment.yml` is the intended single environment for running the characterization tests and current HERMES functionality.

## Current Test Files

### `tests/test_io_and_mesh.py`

- `test_load_tiff_preserves_known_cube_shape_and_material_count`
  - Loads a generated `16x16x16` TIFF cube.
  - Verifies the shape and exact `8 * 8 * 8` material voxel count.
  - Protects TIFF input behavior.

- `test_load_tiff_and_dat_represent_same_known_cube`
  - Loads a generated TIFF cube and equivalent Chen DAT file.
  - Verifies exact shape and voxel equality.
  - Currently marked `xfail` because the current DAT loader ignores header dimensions.

- `test_padding_adds_one_voxel_border_and_preserves_material_count`
  - Pads the known cube.
  - Verifies the new shape is two voxels larger in every direction and material count is unchanged.
  - Protects marching-cubes pre-processing.

- `test_marching_cubes_cube_mesh_has_analytical_volume_within_voxel_tolerance`
  - Converts the known cube to a mesh.
  - Compares mesh volume to the analytical cube volume within a voxel-discretization tolerance.
  - Protects STL/mesh geometry behavior and current normal orientation assumptions.

- `test_chen_writer_round_trips_known_cube`
  - Writes the known cube to Chen DAT and reads it back.
  - Verifies exact voxel equality.
  - Protects voxel export/import behavior.
  - Currently marked `xfail` because the writer and loader disagree on zero-based versus one-based indexing.

### `tests/test_segmentation_analytical.py`

- `test_global_thresholds_recover_known_bright_cube`
  - Runs Otsu, Li, Yen, Isodata, and Triangle thresholding on a two-phase grayscale TIFF.
  - Compares the selected material phase to a known analytical mask.
  - Covers the paper thresholding methods plus GUI extras.

- `test_manual_threshold_recovers_exact_known_bright_cube`
  - Applies manual min/max thresholding to the same two-phase volume.
  - Requires exact mask recovery and exact porosity.
  - Protects the simple grayscale thresholding workflow in the paper.

- `test_darker_greys_selects_complement_of_lighter_phase`
  - Verifies darker-phase selection is the complement of lighter-phase selection.
  - Protects the GUI phase-selection option.
  - Currently marked `xfail` because the current `< threshold` comparison can omit voxels equal to the threshold.

- `test_adaptive_threshold_runs_on_gradient_fixture_and_returns_material_phase`
  - Runs adaptive thresholding on a local-gradient synthetic image.
  - Verifies the bright embedded phase is detected.
  - Protects the adaptive thresholding workflow.

- `test_gui_segmentation_thread_matches_manual_analytical_mask`
  - Calls the GUI segmentation thread against the same analytical mask.
  - Verifies GUI thresholding agrees with the known truth.
  - Requires GUI dependencies and is skipped if unavailable.

### `tests/test_properties_analytical.py`

- `test_fiber_diameter_for_known_cylinder_is_within_voxel_tolerance`
  - Computes fiber diameter on a synthetic cylinder of known radius.
  - Verifies mean diameter is near the expected digital-cylinder value and standard deviation is small.
  - Protects the paper's distance-transform feature-size method.

- `test_pore_distribution_for_known_void_cube_is_finite_and_near_expected_size`
  - Computes pore size on a material block with a known central void.
  - Verifies the mean pore size is near the known void size.
  - Protects the RTV/pore-size workflow in reduced form.

- `test_mesh_based_porosity_for_known_cuboid_is_close_to_analytical_value`
  - Computes porosity from mesh volume for the known cuboid.
  - Compares against analytical porosity.
  - Protects closed-volume-to-porosity logic.

- `test_single_angled_fiber_orientation_matches_analytical_angle`
  - Generates a known angled fiber and checks centerline orientation/length.
  - Currently marked `xfail` because the angle convention needs to be locked during cleanup.
  - Represents the paper's FiberGen-style orientation validation contract.

### `tests/test_directional_porosity_analytical.py`

- `test_directional_porosity_matches_known_layered_volume`
  - Uses a layered volume with exact x-direction porosity profile.
  - Verifies binned directional porosity exactly.
  - Protects directional porosity post-processing.

- `test_porosity_3d_map_matches_known_block_values`
  - Creates a 3D porosity map from the layered volume.
  - Verifies block count and porosity values.
  - Protects 3D porosity-map generation.

### `tests/test_pipeline_serial_analytical.py`

- `test_serial_pipeline_writes_properties_for_known_cube`
  - Runs the current serial pipeline on a known cube.
  - Verifies STL output and property file values, especially analytical porosity.
  - Protects the end-to-end serial workflow.

- `test_serial_pipeline_corner_sampling_writes_one_output_per_corner`
  - Runs explicit corner sampling on a tiny primary volume.
  - Verifies one output TIFF per requested corner.
  - Protects single/corner sub-volume extraction.

- `test_random_sampling_small_jobs_write_requested_output_count`
  - Runs random sampling on a tiny fixture.
  - Verifies one output per requested sub-volume.
  - Protects the basic random sampling contract; local parallel execution will be tested directly after the runner is separated from the current monolithic pipeline.

### `tests/test_mpi_contract.py`

- `test_mpi_environment_is_discoverable`
  - Verifies `mpirun` and `mpi4py` are available.
  - Skips when MPI is not installed.

- `test_mpi_tiny_fixture_matches_serial_contract`
  - Defines the desired MPI CLI behavior on a tiny analytical fixture.
  - Currently marked `xfail` because `voxel2stl_mpi.py` has hard-coded inputs and is not yet a reusable CLI.
  - Protects the future MPI cleanup target.

### `tests/test_gui_contract.py`

- `test_gui_import_and_required_widgets_exist`
  - Instantiates the GUI and verifies core widgets exist.
  - This is intentionally a wiring smoke test because analytical thresholding is covered separately.

## Fixture Generator

`scripts/make_test_fixtures.py` creates all small synthetic volumes used by the tests:

- Binary cuboid.
- Chen DAT version of the cuboid.
- Empty volume.
- Two disconnected islands.
- Two-phase grayscale thresholding volume.
- Gradient thresholding volume.
- Straight fibers along x/y/z.
- Angled fiber.
- Porous block.
- Layered directional-porosity volume.
- Three small primary volumes for multi-primary sampling.
- A solid primary volume for random sampling output-count tests.

These fixtures are deliberately tiny so the tests can run locally and in CI.

## Known Gaps Captured As `xfail`

- Centerline angle conventions need to be agreed upon and locked.
- Current MPI script is not yet a tiny-fixture command-line runner.
- Current darker-greys thresholding can omit voxels equal to the threshold.
- Directional porosity utilities execute hard-coded paper paths at import time; tests currently load only the function definitions to avoid that side effect.

The cleanup/refactor should turn these `xfail` tests into passing tests.
