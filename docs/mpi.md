# MPI And HPC Usage

HERMES includes an MPI entry point for high-throughput microstructure generation and property extraction.

## Purpose

Large XRCT studies often require many sampled sub-volumes to obtain meaningful property distributions.
The MPI workflow distributes those sub-volume tasks across ranks so they can be processed concurrently on an HPC system.

## Basic Command

Run the MPI command from an activated HERMES environment.

```bash
mpirun -n 4 python -m hermes mpi --input segmented.tif --voxel-size 1.0 --output mpi-output
```

The current framework MPI command processes a single input volume through the shared `Workspace` path.
The remaining MPI cleanup should expand this command to run full config workflows.

## SLURM Example

<!-- TODO: Validate the SLURM example on the target cluster and update partition, module, and Conda activation guidance. -->

```bash
#!/bin/bash
#SBATCH --job-name=hermes
#SBATCH --nodes=2
#SBATCH --ntasks=16
#SBATCH --time=00:30:00
#SBATCH --partition=compute

conda activate hermes
mpirun -n "$SLURM_NTASKS" python -m hermes mpi --input segmented.tif --voxel-size 1.0 --output mpi-output
```

Adjust node count, task count, memory, partition, and wall time for the target cluster.

## Current MPI Workflow

1. MPI initializes ranks.
2. Rank 0 prepares output paths and builds the sub-volume task list.
3. Task metadata is broadcast and divided across ranks.
4. Each rank processes its local tasks.
5. Results are gathered back to rank 0.
6. Profiling data may be written per rank.

## Memory Planning

HERMES scaling is often limited by memory.
Before launching large jobs, run a representative single-volume job and measure memory.

Useful metrics include:

- resident set size
- virtual memory size
- Python allocation peak
- wall-clock runtime.

Estimate a safe rank count by dividing available node memory by peak memory per structure.

```text
safe structures per node = available node memory / peak memory per structure
```

## Current Limitations To Address During Cleanup

<!-- TODO: Remove this section or move it to developer documentation once the public interface is stable. -->

The current MPI framework path is useful but should be expanded before a stable public release.

- `voxel2stl_mpi.py` still contains substantial legacy code.
- The tested MPI path now lives in `hermes.mpi` and is exposed through `python -m hermes mpi`.
- Property writing should be made rank-safe by gathering rows before writing.
- Full-volume behavior should be unified with the serial backend.
- Scalar and three-axis volume-length behavior should be unified with the serial backend.
- Full config execution should be added to `hermes.mpi`.

The characterization tests include MPI contract tests that describe the desired future behavior.
