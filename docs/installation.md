# Installation

HERMES uses a scientific Python stack with native libraries for image processing, meshing, visualization, and MPI.
Conda is the recommended installation method for the public release.

## Install Conda

On macOS, Miniforge is recommended.

```bash
brew install --cask miniforge
```

Initialize Conda for `zsh`.

```bash
conda init zsh
```

Restart the terminal after initialization.

## Create The HERMES Environment

Create the environment from the repository root.

```bash
conda env create -f environment.yml
conda activate hermes
```

Verify the environment.

```bash
python -m pytest
```

The expected characterization-test result for this draft is:

```text
52 passed
```

In sandboxed environments, the MPI test may need permission for `mpirun` to open local communication sockets.

## Platform Notes

<!-- TODO: Verify installation notes on a clean macOS machine, a Linux workstation, and one representative HPC environment before the first public release. -->

### macOS

The GUI requires Qt and visualization libraries.
If the GUI fails to launch, confirm that the `hermes` Conda environment is active and that the command is being run from the repository root.

### Linux And HPC

For MPI runs, the environment includes OpenMPI and `mpi4py`.
Some clusters prefer site-provided MPI modules.
If a cluster requires a specific MPI stack, rebuild the environment against that stack.

### PyMeshLab

<!-- TODO: Confirm the best PyMeshLab installation route for macOS, Linux, and cluster environments after dependency testing. -->

PyMeshLab is installed through `pip` in `environment.yml` because Conda availability can vary by platform.
Most serial workflows can run without exercising PyMeshLab unless screened Poisson reconstruction is selected.

## Legacy Environment Files

The repository contains older environment snapshots.

- `HERMES.yml`
- `hermes_mpi.yml`
- `mani_linux.yml`
- `HERMESWINDOWS_Enviroment.yml`

These files are retained for provenance.
The intended public environment is `environment.yml`.
