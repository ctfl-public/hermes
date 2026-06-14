# HERMES Test Catalog

This catalog describes the tests in plain language so the scientific contract can be reviewed without reading pytest code.

## Guiding Principle

Tests should compare HERMES outputs against analytical or known synthetic quantities whenever possible.
Smoke tests are reserved for GUI, MPI, and optional dependency wiring.

## Test Environment

Use the canonical environment file at the repository root.

```bash
conda env create -f environment.yml
conda activate hermes
python -m pytest
```

The older environment files are platform and history snapshots.
`environment.yml` is the intended single environment for running the characterization tests and current HERMES functionality.

## `tests/test_io_and_mesh.py`

### `test_load_tiff_preserves_known_cube_shape_and_material_count`

This test loads a generated `16x16x16` TIFF cube.
It verifies the shape and exact `8 * 8 * 8` material voxel count.
It protects TIFF input behavior.

### `test_load_tiff_and_dat_represent_same_known_cube`

This test loads a generated TIFF cube and an equivalent sparse voxel DAT file.
It verifies exact shape and voxel equality.
It is currently marked `xfail` because the current DAT loader ignores header dimensions.

### `test_padding_adds_one_voxel_border_and_preserves_material_count`

This test pads the known cube.
It verifies the padded shape and confirms that material count is unchanged.
It protects marching-cubes preprocessing.

### `test_marching_cubes_cube_mesh_has_analytical_volume_within_voxel_tolerance`

This test converts the known cube to a mesh.
It compares mesh volume to the analytical cube volume within a voxel-discretization tolerance.
It protects STL and mesh geometry behavior.

### `test_chen_writer_round_trips_known_cube`

This test writes the known cube to sparse voxel DAT and reads it back.
It verifies exact voxel equality.
It is currently marked `xfail` because the writer and loader disagree on zero-based versus one-based indexing.

## `tests/test_segmentation_analytical.py`

### `test_global_thresholds_recover_known_bright_cube`

This test runs the global, entropy-based, iterative, and histogram-shape thresholding methods on a two-phase grayscale TIFF.
It compares the selected material phase to a known analytical mask.
It covers the documented thresholding methods and current GUI extras.

### `test_manual_threshold_recovers_exact_known_bright_cube`

This test applies manual min/max thresholding to a two-phase volume.
It requires exact mask recovery and exact porosity.
It protects the manual grayscale thresholding workflow.

### `test_darker_greys_selects_complement_of_lighter_phase`

This test verifies that darker-phase selection is the complement of lighter-phase selection.
It is currently marked `xfail` because the current `< threshold` comparison can omit voxels equal to the threshold.

### `test_adaptive_threshold_runs_on_gradient_fixture_and_returns_material_phase`

This test runs adaptive thresholding on a local-gradient synthetic image.
It verifies that the bright embedded phase is detected.
It protects the adaptive thresholding workflow.

### `test_gui_segmentation_thread_matches_manual_analytical_mask`

This test calls the GUI segmentation thread against a known analytical mask.
It verifies that GUI thresholding agrees with the known truth.
It requires GUI dependencies and is skipped if unavailable.

## `tests/test_properties_analytical.py`

### `test_fiber_diameter_for_known_cylinder_is_within_voxel_tolerance`

This test computes fiber diameter on a synthetic cylinder of known radius.
It verifies mean diameter near the expected digital-cylinder value and checks that standard deviation remains small.
It protects the distance-transform feature-size method.

### `test_pore_distribution_for_known_void_cube_is_finite_and_near_expected_size`

This test computes pore size on a material block with a known central void.
It verifies that mean pore size is near the known void size.
It protects the pore-size workflow in reduced form.

### `test_mesh_based_porosity_for_known_cuboid_is_close_to_analytical_value`

This test computes porosity from mesh volume for the known cuboid.
It compares against analytical porosity.
It protects closed-volume-to-porosity logic.

### `test_single_angled_fiber_orientation_matches_analytical_angle`

This test generates a known angled fiber and checks centerline orientation and length.
It is currently marked `xfail` because the angle convention needs to be locked during cleanup.
It represents the synthetic-fiber orientation validation contract.

## `tests/test_directional_porosity_analytical.py`

### `test_directional_porosity_matches_known_layered_volume`

This test uses a layered volume with an exact x-direction porosity profile.
It verifies binned directional porosity exactly.
It protects directional porosity post-processing.

### `test_porosity_3d_map_matches_known_block_values`

This test creates a 3D porosity map from the layered volume.
It verifies block count and porosity values.
It protects 3D porosity-map generation.

## `tests/test_pipeline_serial_analytical.py`

### `test_serial_pipeline_writes_properties_for_known_cube`

This test runs the current serial pipeline on a known cube.
It verifies STL output and property-file values.
It protects the end-to-end serial workflow.

### `test_serial_pipeline_corner_sampling_writes_one_output_per_corner`

This test runs explicit corner sampling on a tiny primary volume.
It verifies one output TIFF per requested corner.
It protects single and corner sub-volume extraction.

### `test_random_sampling_small_jobs_write_requested_output_count`

This test runs random sampling on a solid tiny fixture.
It verifies one output per requested sub-volume.
It protects the basic random sampling contract.

## `tests/test_mpi_contract.py`

### `test_mpi_environment_is_discoverable`

This test verifies that `mpirun` and `mpi4py` are available.
It skips when MPI is not installed.

### `test_mpi_tiny_fixture_matches_serial_contract`

This test defines the desired MPI CLI behavior on a tiny analytical fixture.
It is currently marked `xfail` because `voxel2stl_mpi.py` has hard-coded inputs and is not yet a reusable CLI.
It protects the future MPI cleanup target.

## `tests/test_gui_contract.py`

### `test_gui_import_and_required_widgets_exist`

This test instantiates the GUI and verifies core widgets exist.
It is intentionally a wiring smoke test because analytical thresholding is covered separately.

## Fixture Generator

`scripts/make_test_fixtures.py` creates all small synthetic volumes used by the tests.

- Binary cuboid.
- Sparse voxel DAT version of the cuboid.
- Empty volume.
- Two disconnected islands.
- Two-phase grayscale thresholding volume.
- Gradient thresholding volume.
- Straight fibers along x, y, and z.
- Angled fiber.
- Porous block.
- Layered directional-porosity volume.
- Three small primary volumes for multi-primary sampling.
- Solid primary volume for random sampling output-count tests.

These fixtures are deliberately tiny so the tests can run locally and in CI.

## Known Gaps Captured As `xfail`

- Centerline angle conventions need to be agreed upon and locked.
- Current MPI script is not yet a tiny-fixture command-line runner.
- Current darker-greys thresholding can omit voxels equal to the threshold.
- DAT loading and DAT writing need one consistent coordinate convention.
- Directional porosity utilities execute hard-coded paper paths at import time, so tests currently load only the function definitions to avoid that side effect.

The cleanup should turn these `xfail` tests into passing tests.
