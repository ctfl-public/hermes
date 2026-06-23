"""Deprecated compatibility wrapper for the HERMES serial framework.

New code should use ``python -m hermes ...`` or import from ``hermes``.
This file is retained temporarily while older callers migrate.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import random

from hermes.centerlines import (
    analyze_centerline,
    calculate_centerline_properties,
    map_direction_to_material_voxels,
    order_component,
    save_voxel_direction_map_txt,
    split_and_order_centerlines,
)
from hermes.io import load_volume, write_chen_format
from hermes.mesh import (
    check_mesh,
    create_padding,
    generate_mesh,
    load_pymeshlab_mesh,
    load_trimesh,
    remove_floating_islands,
    repair_mesh,
    smooth_mesh,
)
from hermes.properties import fiber_diameter_distribution, pore_distribution
from hermes.property_table import (
    _format_value_json,
    compute_and_write_legacy_properties,
    write_legacy_property_row,
)
from hermes.serial import process_random_sample, process_sample, run_serial


def voxel2stl(croppingFlag, cropSettings, surfaceSettings, savingOptions):
    return run_serial(
        croppingFlag,
        cropSettings,
        surfaceSettings,
        savingOptions,
        random_module=random,
        executor_class=ProcessPoolExecutor,
        as_completed_fn=as_completed,
        meshset_loader=loadMeshPymeshlab,
    )


def process_single_volume(args):
    return process_random_sample(args)


def loadData(surf):
    return load_volume(surf)


def getstl(surfacename, tifvoxelsize, temp_number, volumeLength, corner, surfaceSettings, savingOptions):
    return process_sample(
        surfacename,
        tifvoxelsize,
        temp_number,
        volumeLength,
        corner,
        surfaceSettings,
        savingOptions,
        meshset_loader=loadMeshPymeshlab,
    )


def createPadding(image_volume):
    return create_padding(image_volume)


def writeChenFormat(tempName, binary_volume, tifvoxelsize):
    write_chen_format(tempName, binary_volume, tifvoxelsize)


def getMesh(binary_volume, length, voxel_size):
    return generate_mesh(binary_volume, voxel_size)


def stlSmoothing(FileName, vertices, faces, surfaceSettings):
    return smooth_mesh(FileName, vertices, faces, surfaceSettings, meshset_loader=loadMeshPymeshlab)


def loadMeshTrimesh(vertices, faces):
    return load_trimesh(vertices, faces)


def loadMeshPymeshlab(vertices, faces):
    return load_pymeshlab_mesh(vertices, faces)


def remove_floating_islands_Stl(vertices, faces):
    return remove_floating_islands(vertices, faces, meshset_loader=loadMeshPymeshlab)


def checkMesh(vertices, faces):
    return check_mesh(vertices, faces)


def fixMesh(FileName, vertices, faces):
    print("trying to fix it", FileName)
    FileName, vertices, faces = repair_mesh(FileName, vertices, faces, meshset_loader=loadMeshPymeshlab)
    print(FileName, "fixed!")
    return FileName, vertices, faces


def computeProperties(stlName, vertices, faces, temp_volume, tifvoxelsize, savingOptions, surfacename):
    return compute_and_write_legacy_properties(
        stlName,
        vertices,
        faces,
        temp_volume,
        tifvoxelsize,
        savingOptions,
        surfacename,
    )


def getPoreDistribution(image_volume, tifvoxelsize, sphereSize):
    return pore_distribution(image_volume, tifvoxelsize, sphereSize)


def getDiamter(image_volume, tifvoxelsize, sphereSize):
    mean_diameter, std_diameter, _ = fiber_diameter_distribution(image_volume, tifvoxelsize, sphereSize)
    return mean_diameter, std_diameter


def analyzeCenterLine(image, tifvoxelsize, surfacename, plane="XY"):
    return analyze_centerline(image, tifvoxelsize, surfacename, plane=plane)


def writeProperties(savingOptions, propertyNames, propertiesList):
    write_legacy_property_row(savingOptions["property_path"], propertyNames, propertiesList)


def run_voxel2stl():
    raise SystemExit(
        "voxel2stl.py is deprecated. Use `python -m hermes run CONFIG.json`, "
        "`python -m hermes mesh ...`, or `python -m hermes properties ...`."
    )


if __name__ == "__main__":
    run_voxel2stl()
