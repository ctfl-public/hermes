"""MPI dispatch helpers for HERMES workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from hermes import Workspace


def run_mpi_cli(argv=None, *, comm=None) -> int:
    """Run a small MPI HERMES conversion job from command-line arguments."""
    parser = argparse.ArgumentParser(description="Run a small MPI HERMES conversion job.")
    parser.add_argument("--input", required=True, help="Input TIFF or DAT volume.")
    parser.add_argument("--voxel-size", required=True, type=float, help="Voxel size for the input volume.")
    parser.add_argument("--output", required=True, help="Output directory.")
    args = parser.parse_args(argv)

    return run_single_volume_mpi(args.input, args.voxel_size, args.output, comm=comm)


def run_single_volume_mpi(input_path: str, voxel_size: float, output_dir: str, *, comm=None) -> int:
    """Distribute a tiny single-volume workflow over an MPI communicator."""
    if comm is None:
        from mpi4py import MPI

        comm = MPI.COMM_WORLD

    rank = comm.Get_rank()
    size = comm.Get_size()
    tasks = [{"input": input_path, "voxel_size": voxel_size, "output": output_dir, "task_id": 0}]
    local_tasks = np.array_split(tasks, size)[rank]

    local_results = []
    for task in local_tasks:
        local_results.append(process_single_volume_task(task))

    all_results = comm.gather(local_results, root=0)
    if rank == 0:
        results = [item for sublist in all_results for item in sublist]
        print(f"Completed {len(results)} volumes", flush=True)
    return 0


def process_single_volume_task(task: dict) -> str:
    """Process one MPI task using the shared Workspace framework."""
    output = Path(task["output"])
    workspace = Workspace.from_file(task["input"], voxel_size=task["voxel_size"])
    workspace.pad()
    workspace.generate_mesh()
    workspace.compute_surface_area()
    workspace.compute_closed_volume()
    workspace.compute_volume_by_area()
    workspace.compute_porosity()

    stem = Path(task["input"]).stem
    workspace.export_stl(output / "stl" / f"{stem}_V{task['task_id']}_Full.stl")
    workspace.save_properties(output / "properties.txt")
    return f"Processed {task['input']}"
