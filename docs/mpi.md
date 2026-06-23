# MPI And HPC Usage

HERMES includes an MPI entry point for distributed microstructure processing.

## Purpose

Large XRCT studies often require many sampled sub-volumes to obtain meaningful property distributions.
The MPI support is intended to distribute independent volume-processing tasks across ranks on an HPC system.

## Basic Command

Run the MPI command from an activated HERMES environment.

```bash
mpirun -n 4 python -m hermes mpi --input segmented.tif --voxel-size 1.0 --output mpi-output
```

The current framework MPI command processes a single input volume through the shared `Workspace` path.
The package MPI module also contains the framework runner for regular, grid-like, random, and explicit-corner sampling tasks.
Use JSON configs for complete serial workflows.
Use the MPI command for the currently exposed distributed single-volume command-line workflow.

## SLURM Example

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

## Current MPI Command Workflow

1. MPI initializes ranks.
2. Rank 0 prepares the single-volume task.
3. Task metadata is broadcast and divided across ranks.
4. Each rank processes its local tasks.
5. Results are gathered back to rank 0.

## Scaling Guidance

HERMES scaling is often limited by memory.
Before launching large jobs, run a representative single-volume job and measure memory.

Estimate a safe rank count by dividing available node memory by peak memory per structure.

```text
safe structures per node = available node memory / peak memory per structure
```

## Current MPI Scope

- The tested MPI path lives in `hermes.mpi` and is exposed through `python -m hermes mpi`.
- Regular, grid-like, random, and explicit-corner sample task orchestration now lives in `hermes.mpi`.
- JSON config execution is currently handled by `python -m hermes run`.
- MPI contract tests cover the public MPI command and package-level sample orchestration.
