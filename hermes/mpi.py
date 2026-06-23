"""MPI dispatch helpers for HERMES workflows."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path
import random

import numpy as np

from hermes import Workspace
from hermes.io import load_volume
from hermes.workflow import run_workspace


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


def run_sample_mpi(cropping_flag, crop_settings, surface_settings, saving_options, *, comm=None) -> list[str] | None:
    """Distribute sample tasks over an MPI communicator."""
    if comm is None:
        from mpi4py import MPI

        comm = MPI.COMM_WORLD

    rank = comm.Get_rank()
    size = comm.Get_size()

    saving_options = comm.bcast(saving_options, root=0)

    if rank == 0:
        tasks = build_sample_tasks(cropping_flag, crop_settings)
        print(f"Total tasks to distribute: {len(tasks)}", flush=True)
    else:
        tasks = []

    tasks = comm.bcast(tasks, root=0)
    local_tasks = np.array_split(tasks, size)[rank]
    print(f"Rank {rank}: Processing {len(local_tasks)} tasks", flush=True)

    local_results = []
    for task in local_tasks:
        result = process_sample_task(task, surface_settings, saving_options)
        local_results.append(result)
        print(f"Rank {rank}: {result}", flush=True)

    all_results = comm.gather(local_results, root=0)
    if rank == 0:
        results = [item for sublist in all_results for item in sublist]
        print(f"Completed {len(results)} volumes", flush=True)
        return results

    return None


def process_sample_task(task: dict, surface_settings: dict, saving_options: dict) -> str:
    """Process one distributed sample task using the shared workflow framework."""
    if "seed" in task:
        rng = random.Random(task["seed"])
        block_size = int(task["volume_length"] / task["voxel_size"])
        task = {
            **task,
            "corner": [
                rng.randint(0, int(task["voxel_lengths"][0] - block_size)),
                rng.randint(0, int(task["voxel_lengths"][1] - block_size)),
                rng.randint(0, int(task["voxel_lengths"][2] - block_size)),
            ],
        }

    workspace = Workspace.from_file(task["surface_name"], voxel_size=task["voxel_size"])
    workspace.matrix = (workspace.matrix > 0).astype(np.uint8)
    volume_length = task["volume_length"]
    corner = tuple(int(value) for value in task["corner"])
    if volume_length == "Full":
        workspace = workspace.extract_subvolume(corner=corner, dimensions="Full", sub_id=task["temp_number"])
    else:
        sample_size = int(volume_length / task["voxel_size"])
        workspace = workspace.extract_subvolume(
            corner=corner,
            dimensions=(sample_size, sample_size, sample_size),
            sub_id=task["temp_number"],
        )

    if np.sum(workspace.matrix) == 0:
        return "Empty"

    workspace.name = _sample_name(task, corner)
    run_workspace(
        workspace,
        _output_dir_from_saving_options(saving_options),
        outputs=_outputs_from_saving_options(saving_options),
        properties=_properties_from_saving_options(saving_options),
        property_options=_property_options_from_saving_options(saving_options),
        surface_settings=surface_settings,
        output_paths=_output_paths_from_saving_options(saving_options),
    )
    return f"Processed corner {task['temp_number']} of {task['surface_name']}"


def build_sample_tasks(cropping_flag, crop_settings, *, random_module=random):
    """Build sample tasks from crop settings."""
    if cropping_flag == "Regular":
        filenames, filevoxels, num_volumes, volume_length = crop_settings
    elif cropping_flag == "Corners":
        filenames, filevoxels, corners_mtx, volume_length = crop_settings
    else:
        raise ValueError(f"Unknown cropping flag: {cropping_flag}")

    sample_counts = None
    if cropping_flag == "Regular" and volume_length != 0 and num_volumes != 0:
        sample_counts = np.zeros(len(filenames), dtype="int")
        for _ in range(num_volumes):
            selected_name = random_module.choice(filenames)
            sample_counts[filenames.index(selected_name)] += 1

    tasks = []
    temp_number = 0
    for surf in filenames:
        file_index = filenames.index(surf)
        voxel_lengths = load_volume(surf).shape

        if cropping_flag == "Regular":
            if volume_length == 0:
                tasks.append(
                    {
                        "surface_name": surf,
                        "voxel_size": filevoxels[file_index],
                        "temp_number": temp_number,
                        "volume_length": "Full",
                        "corner": [0, 0, 0],
                    }
                )
                temp_number += 1
            elif num_volumes == 0:
                block_size = int(volume_length / filevoxels[file_index])
                dimensions = [int(length * filevoxels[file_index] / volume_length) for length in voxel_lengths]
                corners = itertools.product(
                    [index * block_size for index in range(dimensions[0])],
                    [index * block_size for index in range(dimensions[1])],
                    [index * block_size for index in range(dimensions[2])],
                )
                for corner in corners:
                    tasks.append(
                        {
                            "surface_name": surf,
                            "voxel_size": filevoxels[file_index],
                            "temp_number": temp_number,
                            "volume_length": volume_length,
                            "corner": list(corner),
                        }
                    )
                    temp_number += 1
            else:
                for index in range(sample_counts[file_index]):
                    tasks.append(
                        {
                            "surface_name": surf,
                            "voxel_size": filevoxels[file_index],
                            "temp_number": temp_number,
                            "volume_length": volume_length,
                            "voxel_lengths": voxel_lengths,
                            "seed": random_module.randint(0, 1000000) + index,
                        }
                    )
                    temp_number += 1

        elif cropping_flag == "Corners":
            for corner in corners_mtx:
                tasks.append(
                    {
                        "surface_name": surf,
                        "voxel_size": filevoxels[file_index],
                        "temp_number": temp_number,
                        "volume_length": volume_length,
                        "corner": list(corner),
                    }
                )
                temp_number += 1

    return tasks


def _sample_name(task: dict, corner: tuple[int, int, int]) -> str:
    stem = Path(task["surface_name"]).stem
    return f"{stem}_V{task['temp_number']}_{corner[0]}-{corner[1]}-{corner[2]}-{task['volume_length']}"


def _outputs_from_saving_options(saving_options: dict) -> list[str]:
    outputs = []
    if saving_options.get("stl_save"):
        outputs.append("stl")
    if saving_options.get("voxel_save"):
        outputs.append("dat")
    if saving_options.get("tiff_save"):
        outputs.append("tiff")
    if saving_options.get("property_save"):
        outputs.append("properties")
    return outputs


def _properties_from_saving_options(saving_options: dict) -> list[str]:
    property_options = saving_options.get("property_options", {})
    properties = []
    if property_options.get("min_max"):
        properties.extend(["min_extents", "max_extents"])
    if property_options.get("surf_area"):
        properties.append("surface_area")
    if property_options.get("closed_volume"):
        properties.append("closed_volume")
    if property_options.get("vol_by_area"):
        properties.append("volume_by_area")
    if property_options.get("porosity"):
        properties.append("porosity")
    if property_options.get("fiber_diameter"):
        properties.append("fiber_diameter")
    if property_options.get("pore_distribution"):
        properties.append("pore_distribution")
    if property_options.get("FiberAngle"):
        properties.append("fiber_angle")
    if property_options.get("FiberLength"):
        properties.append("fiber_length")
    return properties


def _property_options_from_saving_options(saving_options: dict) -> dict[str, object]:
    property_options = saving_options.get("property_options", {})
    return {
        "fiber_diam_sphere": property_options.get("fiber_diam_sphere"),
        "pore_dist_sphere": property_options.get("pore_dist_sphere"),
        "fiber_angle_plane": property_options.get("FiberAnglePlane", "XY"),
    }


def _output_paths_from_saving_options(saving_options: dict) -> dict[str, str]:
    output_paths = {}
    if saving_options.get("stl_save") and saving_options.get("stl_path"):
        output_paths["stl"] = saving_options["stl_path"]
    if saving_options.get("voxel_save") and saving_options.get("voxel_path"):
        output_paths["dat"] = saving_options["voxel_path"]
    if saving_options.get("tiff_save") and saving_options.get("tiff_path"):
        output_paths["tiff"] = saving_options["tiff_path"]
    if saving_options.get("property_save") and saving_options.get("property_path"):
        output_paths["properties"] = saving_options["property_path"]
    return output_paths


def _output_dir_from_saving_options(saving_options: dict) -> Path:
    for key in ("tiff_path", "voxel_path", "stl_path", "property_path"):
        path = saving_options.get(key)
        if path:
            path = Path(path)
            return path.parent if path.suffix else path
    return Path(".")


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
