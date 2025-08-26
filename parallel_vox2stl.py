#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 16:12:17 2023

@author: ctfl
"""

from memory_profiler import profile
import os
import sys
import pymeshlab as ml
import numpy as np
import trimesh
from skimage import measure
import matplotlib.pyplot as plt
import imageio
import random
import tifffile as tiff
import itertools
from scipy.spatial import ConvexHull
from collections import defaultdict
import multiprocessing
from scipy.ndimage import distance_transform_edt
from scipy.ndimage import distance_transform_edt
from skimage.feature import peak_local_max
import time
import psutil
from concurrent.futures import ProcessPoolExecutor, as_completed



def process_single_volume(args):
    """
    Worker function to process a single volume in parallel.
    """
    surf, filevoxel, temp_number, volumeLength, voxelsLength, seed = args
    
    # Set random seed for reproducibility in parallel processing
    random.seed(seed)
    
    corner = np.zeros(3, dtype='int')
    # get random temp corner
    corner[0] = random.randint(0, voxelsLength[0] - volumeLength) 
    corner[1] = random.randint(0, voxelsLength[1] - volumeLength)
    corner[2] = random.randint(0, voxelsLength[2] - volumeLength)
    
    # Call getstl function
    getstl(surf, filevoxel, temp_number, volumeLength, corner)
    
    return f"Processed corner {temp_number} of {surf}"

#@profile
def voxel2stl(croppingFlags, cropSettings, surfaceSettings):
    
    laplacian, humphrey,taubin, iter, min_face_count, pde_mode = surfaceSettings
    
    normalFlag, cornerFlag = croppingFlags
    
    if normalFlag:
        filenames, filevoxels, numVolumes, volumeLength = cropSettings
    
    if cornerFlag:
        filenames, filevoxels, cornersMTX, volumeLength = cropSettings
        
    
    # matrix to store Volumes data 
    sim_mtx = [] #
    if normalFlag:
        if volumeLength != 0 and numVolumes != 0:
            tempMTX= np.zeros(len(filenames),dtype= 'int')
            print(tempMTX)
            for temp in range(numVolumes):
                print(temp)
                tempName = random.choice(filenames)
                print(tempName)
                tempNameIndex = filenames.index(tempName)
                print(tempNameIndex)
                tempMTX[tempNameIndex] += 1
                print(tempMTX[tempNameIndex])
    #print(tempMTX[tempNameIndex]) 
    #print(tempMTX)
    #exit(0)
    temp_number = 0
    max_workers = min(8, (os.cpu_count() or 1))  # Cap at 8 workers
    for surf in filenames:
        tempNameIndex = filenames.index(surf)
        
        # Load data
        image_volume = loadData(surf)
                
        # max voxel length in x, y, and z
        voxelsLength = (image_volume.shape[0], image_volume.shape[1], image_volume.shape[2])
        
        if normalFlag:
            if volumeLength == 0:  # create stl from all the volume
                corner = np.zeros(3, dtype='int')
                fullvolume = 'Full'
                getstl(surf, filevoxels[tempNameIndex], temp_number, fullvolume, corner)
                temp_number += 1
            
            elif numVolumes == 0:
                # Number of volumes in each direction
                dimX = int(voxelsLength[0] * filevoxels[tempNameIndex] / volumeLength)
                dimY = int(voxelsLength[1] * filevoxels[tempNameIndex] / volumeLength)
                dimZ = int(voxelsLength[2] * filevoxels[tempNameIndex] / volumeLength)
                
                totalvolumes = dimX * dimY * dimZ
                
                xCorners = [i * int(volumeLength / filevoxels[tempNameIndex]) for i in range(dimX)]
                yCorners = [i * int(volumeLength / filevoxels[tempNameIndex]) for i in range(dimY)]
                zCorners = [i * int(volumeLength / filevoxels[tempNameIndex]) for i in range(dimZ)]
                corners = list(itertools.product(xCorners, yCorners, zCorners))
                
                for corner in corners:
                    getstl(surf, filevoxels[tempNameIndex], temp_number, volumeLength, corner)
                    temp_number += 1
                    
            else:  # PARALLELIZED SECTION
                volumes_to_process = numVolumes #tempMTX[tempNameIndex]
                
                if volumes_to_process > 5:  # Only parallelize if worth it
                    print(f'Processing {volumes_to_process} random volumes in parallel for {surf}...')
                    
                    with ProcessPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks
                        futures = []
                        for i in range(volumes_to_process):
                            seed = random.randint(0, 1000000) + i
                            future = executor.submit(process_single_volume, 
                                                   (surf, filevoxels[tempNameIndex], temp_number + i,
                                                    volumeLength, voxelsLength, seed))
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
                    for times in range(volumes_to_process):
                        print('corner', times, 'of', surf)
                        
                        corner = np.zeros(3, dtype='int')
                        corner[0] = 0#random.randint(0, voxelsLength[0] - volumeLength) 
                        corner[1] = 0#random.randint(0, voxelsLength[1] - volumeLength)
                        corner[2] = 0#random.randint(0, voxelsLength[2] - volumeLength)
                        
                        getstl(surf, filevoxels[tempNameIndex], temp_number, volumeLength, corner)
                        temp_number += 1

        elif cornerFlag:
            for corner in cornersMTX:
                getstl(surf, filevoxels[tempNameIndex], temp_number, volumeLength, corner)
                temp_number += 1

    
        
if __name__ == '__main__':
    
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    random.seed(500)
    
    start_wall = time.perf_counter()
    start_cpu = time.process_time()

    filenames = ['CC0_7.73504_6273.tif']#['S0_1.06923_2307_NI8.tif' , 'S2_0.9438_2040_NI8.tif' ]#, 'S4_1.0487_2201_NI8.tif' ,\
                #   'S6_0.9928_1322_NI8.tif', 'S8_0.9556_2005_NI8.tif', 'S1_0.8580_1518_NI8.tif',  \
                #       'S3_0.9438_1884_NI8.tif',  'S5_0.9438_1984_NI8.tif',  'S7_0.9556_1929_NI8.tif',  \
                #          'S9_1.00775_2255_NI8.tif'] # One or more
    filevoxels = [7.73504] #[1.06923,0.9438,1.0487,0.9928,0.9556,0.8580,0.9438,0.9438,0.9556,1.00775] # One or more
    # filenames = ['grid_400.tif'] # One or more
    # filevoxels = [1]
    laplacian, humphrey, taubin, screened_poisson = 1,0,0,0 # Any one filter should be set to 1, rest 0  
    iter = 2 # iterations for the Filter
    min_face_count = 9000
    pde_mode = 0 # 0 or 1 -> in 1 hanging fibers will be removed according to min_face_count.
    chenFlag = 0 #9000 # same as pde mode
    
    surfaceSettings = laplacian, humphrey,taubin, iter, min_face_count, pde_mode
    
    normalFlag = 1
    cornerFlag = 0
    croppingFlags = normalFlag, cornerFlag
    
    if normalFlag:
        numVolumes = 1 # zero for Lego
        volumeLength = 2000 # zero for full volume
        cropSettings = filenames, filevoxels, numVolumes, volumeLength
    
    elif cornerFlag:
        cornersMTX = np.array([[0,1020,0],[0,1020,68]]) # One or more in Array
        volumeLength = 200 # One or more in Array
        
        cropSettings = filenames, filevoxels, cornersMTX, volumeLength
        
    propertiesFile = 'propertiesTIF1.txt'
    
    with open(propertiesFile,'a+') as f:
        f.write('stlName\tmin_extents\tmax_extents\tmesh_surface_area\tmesh_volume\tlengthbyarea\tporosity_\tmeanDiameter\tstdDiameter\n')
    # file_path = "properties-"+str(laplacian)+str(humphrey)+str(taubin)+"-"+str(iter)+".dat"
    # file = open(file_path, 'w')
    #startTime = time.time()

    voxel2stl(croppingFlags,cropSettings, surfaceSettings)
    
    #endTime = time.time()
    #print('It took %i sec to genereate the surface !'%(endTime-startTime))
    end_wall = time.perf_counter()
    end_cpu = time.process_time()

    wall_time = end_wall - start_wall
    cpu_time = end_cpu - start_cpu

    print(f'Wall-clock time: {wall_time:.4f} seconds')
    print(f'CPU time: {cpu_time:.4f} seconds')

