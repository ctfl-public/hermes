#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 16:12:17 2023

@author: ctfl
"""
import numpy as np
import trimesh
from skimage import measure, filters, morphology
import imageio
import random
import tifffile as tiff
import itertools
import os
from scipy.ndimage import distance_transform_edt
from skimage.feature import peak_local_max
from pathlib import Path
import re
import networkx as nx
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from numbers import Number
from scipy.spatial import cKDTree
from hermes.centerlines import (
    analyze_centerline,
    calculate_centerline_properties as framework_calculate_centerline_properties,
    map_direction_to_material_voxels as framework_map_direction_to_material_voxels,
    order_component as framework_order_component,
    save_voxel_direction_map_txt as framework_save_voxel_direction_map_txt,
    split_and_order_centerlines as framework_split_and_order_centerlines,
)
from hermes.io import load_volume, write_chen_format
from hermes.mesh import check_mesh, create_padding, generate_mesh, load_pymeshlab_mesh, load_trimesh, repair_mesh, smooth_mesh
from hermes.property_table import compute_and_write_legacy_properties, write_legacy_property_row
from hermes.properties import fiber_diameter_distribution, pore_distribution

def voxel2stl(croppingFlag, cropSettings, surfaceSettings, savingOptions):

    if savingOptions['property_save']:
        if savingOptions['property_path'] == '':
            savingOptions['property_path'] = 'propertyFile.txt' 
        
        # Check if file exists to determine if we need to create a new name     
        if os.path.exists(savingOptions['property_path']):
            # Create a new name for the file with '_copy' and increment if needed
            base_name, ext = os.path.splitext(savingOptions['property_path'])
            copy_fileName = f"{base_name}_copy{ext}"
    
            # If the file copy already exists, increment the number until a unique name is found
            counter = 1
            while os.path.exists(copy_fileName):
                copy_fileName = f"{base_name}_copy{counter}{ext}"
                counter += 1
            
            # Update fileName to the new copy file name
            savingOptions['property_path'] = copy_fileName
        
        
        # Open the new file in write mode to save the data when computed
        with open(savingOptions['property_path'], 'w') as f:
            pass
    
    if croppingFlag == 'Regular':
        filenames, filevoxels, numVolumes, volumeLength = cropSettings
    
    elif croppingFlag == 'Corners':
        filenames, filevoxels, cornersMTX, volumeLength = cropSettings
        
    
    # matrix to store Volumes data 
    sim_mtx = [] #
    if croppingFlag == 'Regular':
        if volumeLength != 0 and numVolumes != 0:
            tempMTX= np.zeros(len(filenames),dtype= 'int')
            for temp in range(numVolumes):
                tempName = random.choice(filenames)
                tempNameIndex = filenames.index(tempName)
                tempMTX[tempNameIndex] += 1
     
    temp_number = 0
    max_workers = min(8, (os.cpu_count() or 1))  # Cap at 8 workers
    for num, surf in enumerate(filenames):
        tempNameIndex = filenames.index(surf)
        
        # Load data
        image_volume = loadData(surf)
                
        # max voxel length in x, y, and z
        voxelsLength = (image_volume.shape[0],image_volume.shape[1],image_volume.shape[2])
        
        if croppingFlag == 'Regular':
            if volumeLength == 0: # create stl from all the volume
                corner = np.zeros(3, dtype='int')
                fullvolume = 'Full'
                getstl(surf, filevoxels[tempNameIndex], temp_number,fullvolume, corner, surfaceSettings, savingOptions)
                temp_number += 1
            
            elif numVolumes == 0:
                # Number of volumes in each direction
                dimX = int(voxelsLength[0]*filevoxels[tempNameIndex]/volumeLength)
                dimY = int(voxelsLength[1]*filevoxels[tempNameIndex]/volumeLength)
                dimZ = int(voxelsLength[2]*filevoxels[tempNameIndex]/volumeLength)
                
                totalvolumes = dimX*dimY*dimZ
                # if totalvolumes > 10:
                #     print('Do this in parallel, %i volumes'%(totalvolumes))
                #     return
                xCorners = [i*int(volumeLength/filevoxels[tempNameIndex]) for i in range(dimX)]
                yCorners = [i*int(volumeLength/filevoxels[tempNameIndex]) for i in range(dimY)]
                zCorners = [i*int(volumeLength/filevoxels[tempNameIndex]) for i in range(dimZ)]
                corners = list(itertools.product(xCorners,yCorners,zCorners))
                for corner in corners:
                    getstl(surf, filevoxels[tempNameIndex], temp_number,volumeLength, corner, surfaceSettings, savingOptions)
                    temp_number += 1
                    
            else:
                volumes_to_process = tempMTX[num]

                if volumes_to_process > 1000:  # Only parallelize if worth it
                    print(f'Processing {volumes_to_process} random volumes in parallel for {surf}...')
                    
                    with ProcessPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks
                        futures = []
                        for i in range(volumes_to_process):
                            seed = random.randint(0, 1000000) + i
                            future = executor.submit(process_single_volume, 
                                                   (surf, filevoxels[tempNameIndex], temp_number + i,
                                                    volumeLength, voxelsLength, seed, surfaceSettings, savingOptions))
                            futures.append(future)
                        
                        # Wait for completion and handle results
                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                print(result)
                            except Exception as e:
                                print(f"Error processing volume: {e}")
                    
                    temp_number += volumes_to_process

                else:
                    # Process sequentially for small number of volumes
                    for times in range(tempMTX[tempNameIndex]):
                        
                        print('corner',times,'of',surf)
                        if numVolumes != 0:
                            
                            # name of iteration volume
                            # tempName = filenames[:-4]+'_V%i'%(temp)
                            
                            corner = np.zeros(3, dtype='int')
                            # get random temp corner
                            corner[0] = random.randint(0,int(voxelsLength[0]-volumeLength/filevoxels[tempNameIndex])) 
                            corner[1] = random.randint(0,int(voxelsLength[1]-volumeLength/filevoxels[tempNameIndex]))
                            corner[2] = random.randint(0,int(voxelsLength[2]-volumeLength/filevoxels[tempNameIndex]))
                            # center crop
                            # corner[0] = (voxelsLength[0]-volumeLength)/2 #random.randint(0,voxelsLength[0]-volumeLength) 
                            # corner[1] = (voxelsLength[1]-volumeLength)/2 #random.randint(0,voxelsLength[1]-volumeLength)
                            # corner[2] = (voxelsLength[2]-volumeLength)/2 #random.randint(0,voxelsLength[2]-volumeLength)

                            
                            getstl(surf, filevoxels[tempNameIndex], temp_number,volumeLength, corner, surfaceSettings, savingOptions)
                            temp_number += 1

        elif croppingFlag == 'Corners':
            for corner in cornersMTX:
                getstl(surf, filevoxels[tempNameIndex], temp_number,volumeLength, corner, surfaceSettings, savingOptions)
                temp_number += 1

def process_single_volume(args):
    """
    Worker function to process a single volume in parallel.
    """
    surf, filevoxel, temp_number, volumeLength, voxelsLength, seed, surfaceSettings, savingOptions = args
    
    # Set random seed for reproducibility in parallel processing
    random.seed(seed)
    
    corner = np.zeros(3, dtype='int')
    # get random temp corner
    corner[0] = random.randint(0,int(voxelsLength[0]-volumeLength/filevoxel)) 
    corner[1] = random.randint(0,int(voxelsLength[1]-volumeLength/filevoxel))
    corner[2] = random.randint(0,int(voxelsLength[2]-volumeLength/filevoxel))
    
    # Call getstl function
    getstl(surf, filevoxel, temp_number, volumeLength, corner, surfaceSettings, savingOptions)
    
    return f"Processed corner {temp_number} of {surf}"

def loadData(surf):
    return load_volume(surf)

def getstl(surfacename, tifvoxelsize, temp_number,volumeLength, corner, surfaceSettings, savingOptions): 
    
    # Create image_volume
    image_volume = loadData(surfacename)

    # Surface file name
    tempName = surfacename[:-4]+'_V%i_%i-%i-%i-%s'%(temp_number,corner[0],corner[1],corner[2],volumeLength)
    
    if volumeLength != 'Full':
        # adjust nummber volumelength 
        volumeLength = int(volumeLength/tifvoxelsize)
        
        # Crop the volume of interest
        temp_volume = image_volume[corner[0]:corner[0]+volumeLength,corner[1]:corner[1]+volumeLength,corner[2]:corner[2]+volumeLength]
        
    else: # Create stl from full tif
        temp_volume = image_volume
    
    if np.sum(temp_volume) == 0:
        print('Empty Volume, there is no material!')
        return 'Empty'
    # Make a binary MTX
    temp_volume = temp_volume/ np.max(temp_volume)
    
    # Creat padding around volume 
    binary_volume = createPadding(temp_volume)
    
    # Remove Ilands
    if savingOptions['voxel_save']:
        if savingOptions['voxel_path'] != '':
            if not os.path.exists(savingOptions['voxel_path']):
                Path(savingOptions['voxel_path']).mkdir(parents=True, exist_ok=True) 
            writeChenFormat(os.path.join(savingOptions['voxel_path'],os.path.basename(tempName))+'.dat',binary_volume,tifvoxelsize)
        else:
            writeChenFormat(os.path.basename(tempName)+'.dat',binary_volume,tifvoxelsize)
        
    # Get vertices and faces 
    vertices, faces = getMesh(binary_volume,volumeLength,tifvoxelsize)
    
    # Perform smoothing 
    tempName, vertices, faces = stlSmoothing(tempName, vertices, faces, surfaceSettings)   
    
    # Check mesh 
    volume_check = checkMesh(vertices, faces)

    if not volume_check:
        print('%s needs fixing!'%tempName)
        tempName, vertices, faces = fixMesh(tempName, vertices, faces)

    if savingOptions['property_save']:
        computeProperties(os.path.basename(tempName)+'.stl', vertices,faces,temp_volume,tifvoxelsize,savingOptions,surfacename)
        
    if savingOptions['stl_save']:
        trimesh_mesh = loadMeshTrimesh(vertices,faces)
        if savingOptions['stl_path'] != '':
            if not os.path.exists(savingOptions['stl_path']):
                Path(savingOptions['stl_path']).mkdir(parents=True, exist_ok=True)
            # Load mesh from vertices and faces
            trimesh_mesh.export(os.path.join(savingOptions['stl_path'],os.path.basename(tempName)+'.stl') , file_type="stl_ascii")
        else:
            trimesh_mesh.export(os.path.basename(tempName)+'.stl', file_type="stl_ascii")
            
    if savingOptions['tiff_save']:
        if savingOptions['tiff_path'] != '':
            if not os.path.exists(savingOptions['tiff_path']):
                Path(savingOptions['tiff_path']).mkdir(parents=True, exist_ok=True)
            # Save the volume as a 3D TIFF file (uncomment to double check stl)[:-4]
            tiff.imwrite(os.path.join(savingOptions['tiff_path'],os.path.basename(tempName)+'.tif'), binary_volume[1:-1,1:-1,1:-1].astype(np.uint16),imagej=True)
        else:
            # Save the volume as a 3D TIFF file (uncomment to double check stl)[:-4]
            tiff.imwrite(os.path.basename(tempName)+'.tif', binary_volume[1:-1,1:-1,1:-1].astype(np.uint16),imagej=True)
    

def createPadding(image_volume):
    return create_padding(image_volume)

def writeChenFormat(tempName,binary_volume,tifvoxelsize):
    write_chen_format(tempName, binary_volume, tifvoxelsize)

def getMesh(binary_volume,length,voxel_size):
    return generate_mesh(binary_volume, voxel_size)

def stlSmoothing(FileName, vertices, faces, surfaceSettings ):
    return smooth_mesh(FileName, vertices, faces, surfaceSettings, meshset_loader=loadMeshPymeshlab)

def loadMeshTrimesh(vertices,faces):
    return load_trimesh(vertices, faces)

def loadMeshPymeshlab(vertices,faces):
    return load_pymeshlab_mesh(vertices, faces)

def remove_floating_islands_Stl(vertices,faces):

    # Load the mesh
    ms = loadMeshPymeshlab(vertices,faces)

    # Compute connected components and select small components for deletion
    ms.apply_filter('compute_selection_by_small_disconnected_components_per_face',nbfaceratio=1)

    # Delete the selected small components
    ms.apply_filter('meshing_remove_selected_vertices_and_faces')

    return ms

def checkMesh(vertices,faces):
    return check_mesh(vertices, faces)

def fixMesh(FileName,vertices,faces):
    print('trying to fix it', FileName)
    FileName, vertices, faces = repair_mesh(FileName, vertices, faces, meshset_loader=loadMeshPymeshlab)
    print(FileName, 'fixed!')
    return FileName, vertices, faces

def computeProperties(stlName, vertices, faces, temp_volume, tifvoxelsize, savingOptions,surfacename):
    compute_and_write_legacy_properties(
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

def getDiamter(image_volume,tifvoxelsize,sphereSize):
    meanDiameter, stdDiameter, _ = fiber_diameter_distribution(image_volume, tifvoxelsize, sphereSize)
    return meanDiameter, stdDiameter

def analyzeCenterLine(image,tifvoxelsize,surfacename,plane='XY'):
    return analyze_centerline(image, tifvoxelsize, surfacename, plane=plane)

def save_voxel_direction_map_txt(filename, direction_map):
    return framework_save_voxel_direction_map_txt(filename, direction_map)

def map_direction_to_material_voxels(image, direction_coords, direction_vectors, direction_centerline_ids=None):
    return framework_map_direction_to_material_voxels(image, direction_coords, direction_vectors, direction_centerline_ids)

# Function to split centerlines at branch points
def split_and_order_centerlines(graph, branch_nodes, steps=4):
    return framework_split_and_order_centerlines(graph, branch_nodes, steps=steps)

def order_component(subgraph):
    return framework_order_component(subgraph)


def calculate_centerline_properties(split_centerlines,tifvoxelsize,image, plane='XY', step_size=4):
    return framework_calculate_centerline_properties(split_centerlines, tifvoxelsize, image, plane=plane, step_size=step_size)

# def writeProperties(savingOptions, propertyNames, propertiesList):

    
#         with open(savingOptions['property_path'], "a+") as f:
#             f.seek(0)  # rewind to the beginning so we can read
#             content = f.read()

#             if "StlName" not in content:
#                 # Write properties header at the end (file may be empty)
#                 f.write('\t'.join(propertyNames) + '\n')
                
#             # Write the property values
#             f.write('\t'.join(f"{float(x):.4f}" if (isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('e-', '', 1).replace('e+', '', 1).isdigit())) and abs(float(x)) >= 1e-4  
#                 else f"{float(x):.4g}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('e-', '', 1).replace('e+', '', 1).isdigit())  
#                 else str(x) for x in propertiesList) + '\n')  
    
def writeProperties(savingOptions, propertyNames, propertiesList):
    write_legacy_property_row(savingOptions['property_path'], propertyNames, propertiesList)

def _format_value_json(x):
    """
    Format a property value as JSON:
    - Scalars → numeric or string
    - Lists/tuples/ndarrays → JSON array
    """
    # Convert numpy scalars to Python scalars
    if isinstance(x, np.ndarray):
        if x.ndim == 0:
            x = x.item()
        else:
            x = x.tolist()

    # Convert numpy arrays/lists/tuples into Python lists
    if isinstance(x, (list, tuple)):
        return json.dumps(x)

    # Try numeric scalar formatting
    try:
        f = float(x)
        # choose fixed or general formatting for readability
        return f"{f:.4f}" if abs(f) >= 1e-4 else f"{f:.4g}"
    except:
        # Fall back to string safely
        return str(x)


def run_voxel2stl():
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    random.seed(500)
    
    # Surface Settings
    surfaceSettings = {
        "laplacianFlag": 1,
        "laplacian_iter": 1,
        "ScreenedPoissonFlag": 0,
        "ScreenedPoisson_iter": 8,
        "RemoveIslandsFlag": 0
        }
    
    croppingFlag = 'Regular' # 'Regular' or 'Corner'
    print(croppingFlag)
    
    filenames = [r'C:\Users\Luis Chacon\OneDrive - University of Kentucky\Universidad - OneDrive\Research\Github\hermes-OLD\grid_physical_15Elevation_1.0.tif'  ] # one or more Ex: ['file1.tif', 'file2.dat', ...]
    
    filevoxels = [1] # one or more correspondig to filenames Ex: [1, 1.8, ...]
    
    # Saving Flags 1 or 0 for True or False, respectively
    savingOptions = {
        "tiff_save": 0,
        "tiff_path": '', # Path where files will be saved or '' for current directory
        "voxel_save": 0,
        "voxel_path": '',  # Path where files will be saved or '' for current directory
        "stl_save": 1,
        "stl_path": r'C:\Users\Luis Chacon\OneDrive - University of Kentucky\Universidad - OneDrive\Research\Github\puma\HERMESResults',  # Path where files will be saved or '' for current directory
        "property_save": 1,
        "property_path": r'C:\Users\Luis Chacon\OneDrive - University of Kentucky\Universidad - OneDrive\Research\Github\puma\HERMESResults\propertiesAngle.txt',  # Path where files will be saved or '' for current directory
        "property_options": {
            "min_max": 0,
            "surf_area": 1,
            "closed_volume": 0,
            "vol_by_area": 1,
            "porosity": 1,
            "fiber_diameter": 1,
            "fiber_diam_sphere": 10, # in um
            "pore_distribution": 0,
            "pore_dist_sphere": 30, # in um
            "FiberAngle": 1,
            "FiberAnglePlane": 'XY',
            "FiberLength": 1,
            
        }
    }
    print(savingOptions)
    
    if croppingFlag == 'Regular':
        # If both are set to 0 Full volume will be prioritize
        volumeLength = 0 # In um or enter 0 for Full volume
        numVolumes = 1 # Number of volumes or enter 0 for Lego

        cropSettings = filenames, filevoxels, numVolumes, volumeLength
        print(cropSettings)
        
    elif croppingFlag == 'Corners':
        volumeLength = 100 # In um
        
        cornersMTX = [(1,2,3), (3,2,6)] # list of tuple coordinates in the format (x,y,z)
        
        cropSettings = filenames, filevoxels, cornersMTX, volumeLength
        print(cropSettings)
    if surfaceSettings['laplacianFlag'] and surfaceSettings['ScreenedPoissonFlag']:
        print('Only one filter (Laplacian or Screened Poisson) should be selected')
        return
    
    for file_path in filenames:
        if not os.path.exists(file_path):
            print('File {file_path} was not found!')
    
    voxel2stl(croppingFlag, cropSettings, surfaceSettings, savingOptions)

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    run_voxel2stl()
