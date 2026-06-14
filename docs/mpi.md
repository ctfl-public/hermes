# MPI And HPC Usage

HERMES includes an MPI script for high-throughput microstructure generation and property extraction.

## Purpose

Large XRCT studies often require many sampled sub-volumes to obtain meaningful property distributions.
The MPI workflow distributes those sub-volume tasks across ranks so they can be processed concurrently on an HPC system.

## Basic Command

<!-- TODO: Add a tiny MPI fixture command once `voxel2stl_mpi.py` accepts reusable input paths or a config file. -->

Run the MPI script from an activated HERMES environment.
Before running, edit `run_voxel2stl()` in `voxel2stl_mpi.py` so `filenames`, `filevoxels`, output paths, sampling settings, and property options match the target job.

```bash
mpirun -n 4 python voxel2stl_mpi.py
```

The current MPI script is configured by editing `run_voxel2stl()` in `voxel2stl_mpi.py`.

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
mpirun -n "$SLURM_NTASKS" python voxel2stl_mpi.py
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

The current MPI script is useful but should be cleaned before a stable public release.

- It duplicates logic from `voxel2stl.py`.
- It uses edited-in settings rather than command-line arguments or config files.
- Property writing should be made rank-safe by gathering rows before writing.
- Full-volume behavior should be unified with the serial backend.
- Scalar and three-axis volume-length behavior should be unified with the serial backend.
- Documentation and command examples should consistently reference `voxel2stl_mpi.py`.

The characterization tests include MPI contract tests that describe the desired future behavior.
