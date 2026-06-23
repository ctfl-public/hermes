# Legacy MPI Notes

This file preserves the older root-level MPI notes for provenance while pointing users to the current MPI documentation.
For current instructions, use [mpi.md](mpi.md).

## Original Guidance To Preserve

The old notes described an HPC workflow with these steps.

1. Install a Conda environment on the Linux cluster.
2. Activate the environment before launching the job.
3. Load the TIFF file and voxel resolution in the script settings.
4. Under `croppingFlag == "Regular"`, set the cube length and number of generated volumes.
5. Choose the number of nodes and MPI ranks based on the memory available per node.

The old notes also emphasized that rank count should be selected with memory in mind.
For example, two nodes with 128 GB each provide 256 GB total, and the number of MPI ranks should leave enough memory for each sampled structure.

## Current Replacement

The current framework MPI entry point is `python -m hermes mpi`.
The old root-level MPI script has been removed after the tested behavior moved into `hermes.mpi`.
The public MPI instructions are maintained in [mpi.md](mpi.md).
