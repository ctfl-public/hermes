"""Serial HERMES workflow orchestration."""

from __future__ import annotations

from pathlib import Path
import itertools
import os
import random

import numpy as np
import tifffile as tiff

from hermes.io import load_volume, write_chen_format
from hermes.mesh import check_mesh, create_padding, generate_mesh, load_trimesh, repair_mesh, smooth_mesh
from hermes.property_table import compute_and_write_legacy_properties


def run_serial(
    cropping_flag,
    crop_settings,
    surface_settings,
    saving_options,
    *,
    random_module=random,
    executor_class=None,
    as_completed_fn=None,
    meshset_loader=None,
):
    """Run a serial voxel-to-STL workflow from framework code."""
    if saving_options["property_save"]:
        _prepare_property_file(saving_options)

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

    temp_number = 0
    max_workers = min(8, (os.cpu_count() or 1))
    for surf in filenames:
        file_index = filenames.index(surf)
        image_volume = load_volume(surf)
        voxel_lengths = image_volume.shape

        if cropping_flag == "Regular":
            if volume_length == 0:
                corner = np.zeros(3, dtype="int")
                process_sample(
                    surf,
                    filevoxels[file_index],
                    temp_number,
                    "Full",
                    corner,
                    surface_settings,
                    saving_options,
                    meshset_loader=meshset_loader,
                )
                temp_number += 1
            elif num_volumes == 0:
                dim_x = int(voxel_lengths[0] * filevoxels[file_index] / volume_length)
                dim_y = int(voxel_lengths[1] * filevoxels[file_index] / volume_length)
                dim_z = int(voxel_lengths[2] * filevoxels[file_index] / volume_length)
                block_size = int(volume_length / filevoxels[file_index])
                corners = list(
                    itertools.product(
                        [index * block_size for index in range(dim_x)],
                        [index * block_size for index in range(dim_y)],
                        [index * block_size for index in range(dim_z)],
                    )
                )
                for corner in corners:
                    process_sample(
                        surf,
                        filevoxels[file_index],
                        temp_number,
                        volume_length,
                        corner,
                        surface_settings,
                        saving_options,
                        meshset_loader=meshset_loader,
                    )
                    temp_number += 1
            else:
                volumes_to_process = sample_counts[file_index]
                if volumes_to_process > 1000 and executor_class is not None and as_completed_fn is not None:
                    print(f"Processing {volumes_to_process} random volumes in parallel for {surf}...")
                    with executor_class(max_workers=max_workers) as executor:
                        futures = []
                        for index in range(volumes_to_process):
                            seed = random_module.randint(0, 1000000) + index
                            future = executor.submit(
                                process_random_sample,
                                (
                                    surf,
                                    filevoxels[file_index],
                                    temp_number + index,
                                    volume_length,
                                    voxel_lengths,
                                    seed,
                                    surface_settings,
                                    saving_options,
                                ),
                            )
                            futures.append(future)
                        for future in as_completed_fn(futures):
                            try:
                                print(future.result())
                            except Exception as exc:
                                print(f"Error processing volume: {exc}")
                    temp_number += volumes_to_process
                else:
                    for times in range(sample_counts[file_index]):
                        print("corner", times, "of", surf)
                        corner = np.zeros(3, dtype="int")
                        corner[0] = random_module.randint(0, int(voxel_lengths[0] - volume_length / filevoxels[file_index]))
                        corner[1] = random_module.randint(0, int(voxel_lengths[1] - volume_length / filevoxels[file_index]))
                        corner[2] = random_module.randint(0, int(voxel_lengths[2] - volume_length / filevoxels[file_index]))
                        process_sample(
                            surf,
                            filevoxels[file_index],
                            temp_number,
                            volume_length,
                            corner,
                            surface_settings,
                            saving_options,
                            meshset_loader=meshset_loader,
                        )
                        temp_number += 1

        elif cropping_flag == "Corners":
            for corner in corners_mtx:
                process_sample(
                    surf,
                    filevoxels[file_index],
                    temp_number,
                    volume_length,
                    corner,
                    surface_settings,
                    saving_options,
                    meshset_loader=meshset_loader,
                )
                temp_number += 1


def build_sample_tasks(cropping_flag, crop_settings, *, random_module=random):
    """Build legacy-style sample tasks from crop settings."""
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
        image_volume = load_volume(surf)
        voxel_lengths = image_volume.shape

        if cropping_flag == "Regular":
            if volume_length == 0:
                tasks.append(
                    {
                        "surface_name": surf,
                        "voxel_size": filevoxels[file_index],
                        "temp_number": temp_number,
                        "volume_length": "Full",
                        "corner": np.zeros(3, dtype="int").tolist(),
                    }
                )
                temp_number += 1
            elif num_volumes == 0:
                dim_x = int(voxel_lengths[0] * filevoxels[file_index] / volume_length)
                dim_y = int(voxel_lengths[1] * filevoxels[file_index] / volume_length)
                dim_z = int(voxel_lengths[2] * filevoxels[file_index] / volume_length)
                block_size = int(volume_length / filevoxels[file_index])
                corners = list(
                    itertools.product(
                        [index * block_size for index in range(dim_x)],
                        [index * block_size for index in range(dim_y)],
                        [index * block_size for index in range(dim_z)],
                    )
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
                    seed = random_module.randint(0, 1000000) + index
                    tasks.append(
                        {
                            "surface_name": surf,
                            "voxel_size": filevoxels[file_index],
                            "temp_number": temp_number,
                            "volume_length": volume_length,
                            "voxel_lengths": voxel_lengths,
                            "seed": seed,
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


def process_random_sample(args):
    """Worker function for random-volume processing."""
    surf, filevoxel, temp_number, volume_length, voxel_lengths, seed, surface_settings, saving_options = args
    random.seed(seed)
    corner = np.zeros(3, dtype="int")
    corner[0] = random.randint(0, int(voxel_lengths[0] - volume_length / filevoxel))
    corner[1] = random.randint(0, int(voxel_lengths[1] - volume_length / filevoxel))
    corner[2] = random.randint(0, int(voxel_lengths[2] - volume_length / filevoxel))
    process_sample(surf, filevoxel, temp_number, volume_length, corner, surface_settings, saving_options)
    return f"Processed corner {temp_number} of {surf}"


def process_sample(
    surface_name,
    voxel_size,
    temp_number,
    volume_length,
    corner,
    surface_settings,
    saving_options,
    *,
    meshset_loader=None,
):
    """Process one sample."""
    image_volume = load_volume(surface_name)
    temp_name = f"{surface_name[:-4]}_V{temp_number}_{corner[0]}-{corner[1]}-{corner[2]}-{volume_length}"

    if volume_length != "Full":
        sample_size = int(volume_length / voxel_size)
        temp_volume = image_volume[
            corner[0] : corner[0] + sample_size,
            corner[1] : corner[1] + sample_size,
            corner[2] : corner[2] + sample_size,
        ]
    else:
        temp_volume = image_volume

    if np.sum(temp_volume) == 0:
        print("Empty Volume, there is no material!")
        return "Empty"

    temp_volume = temp_volume / np.max(temp_volume)
    binary_volume = create_padding(temp_volume)

    if saving_options["voxel_save"]:
        output = _output_path(saving_options["voxel_path"], temp_name, ".dat")
        write_chen_format(output, binary_volume, voxel_size)

    vertices, faces = generate_mesh(binary_volume, voxel_size)
    if meshset_loader is None:
        temp_name, vertices, faces = smooth_mesh(temp_name, vertices, faces, surface_settings)
    else:
        temp_name, vertices, faces = smooth_mesh(
            temp_name,
            vertices,
            faces,
            surface_settings,
            meshset_loader=meshset_loader,
        )

    if not check_mesh(vertices, faces):
        print(f"{temp_name} needs fixing!")
        if meshset_loader is None:
            temp_name, vertices, faces = repair_mesh(temp_name, vertices, faces)
        else:
            temp_name, vertices, faces = repair_mesh(temp_name, vertices, faces, meshset_loader=meshset_loader)

    if saving_options["property_save"]:
        compute_and_write_legacy_properties(
            os.path.basename(temp_name) + ".stl",
            vertices,
            faces,
            temp_volume,
            voxel_size,
            saving_options,
            surface_name,
        )

    if saving_options["stl_save"]:
        mesh = load_trimesh(vertices, faces)
        mesh.export(_output_path(saving_options["stl_path"], temp_name, ".stl"), file_type="stl_ascii")

    if saving_options["tiff_save"]:
        output = _output_path(saving_options["tiff_path"], temp_name, ".tif")
        tiff.imwrite(output, binary_volume[1:-1, 1:-1, 1:-1].astype(np.uint16), imagej=True)


def _prepare_property_file(saving_options):
    if saving_options["property_path"] == "":
        saving_options["property_path"] = "propertyFile.txt"

    if os.path.exists(saving_options["property_path"]):
        base_name, extension = os.path.splitext(saving_options["property_path"])
        copy_name = f"{base_name}_copy{extension}"
        counter = 1
        while os.path.exists(copy_name):
            copy_name = f"{base_name}_copy{counter}{extension}"
            counter += 1
        saving_options["property_path"] = copy_name

    with open(saving_options["property_path"], "w", encoding="utf-8"):
        pass


def _output_path(output_dir, temp_name, suffix):
    path = Path(output_dir) if output_dir != "" else Path(".")
    path.mkdir(parents=True, exist_ok=True)
    return path / (os.path.basename(temp_name) + suffix)


# Backward-compatible names for the old wrapper layer.
voxel2stl_legacy = run_serial
process_single_volume_legacy = process_random_sample
get_stl_legacy = process_sample
