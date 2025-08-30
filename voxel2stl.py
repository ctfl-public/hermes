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

def voxel2stl(croppingFlag, cropSettings, surfaceSettings, savingOptions):
    
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
    for surf in filenames:
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
                dimY = int(voxelsLength[0]*filevoxels[tempNameIndex]/volumeLength)
                dimZ = int(voxelsLength[0]*filevoxels[tempNameIndex]/volumeLength)
                
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
                volumes_to_process = numVolumes

                if volumes_to_process > 5:  # Only parallelize if worth it
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
                            corner[0] = random.randint(0,int(voxelsLength[0]-volumeLength)) 
                            corner[1] = random.randint(0,int(voxelsLength[1]-volumeLength))
                            corner[2] = random.randint(0,int(voxelsLength[2]-volumeLength))
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
    corner[0] = random.randint(0, voxelsLength[0] - volumeLength) 
    corner[1] = random.randint(0, voxelsLength[1] - volumeLength)
    corner[2] = random.randint(0, voxelsLength[2] - volumeLength)
    
    # Call getstl function
    getstl(surf, filevoxel, temp_number, volumeLength, corner, surfaceSettings, savingOptions)
    
    return f"Processed corner {temp_number} of {surf}"

def loadData(surf):
    if surf.endswith('.tif'):
        # Load the TIFF file
        image_volume = imageio.volread(surf)
    
    elif surf.endswith('.txt') or surf.endswith('.dat'):
        tempdata = np.loadtxt(surf, skiprows=2)
        xmax = int(max(tempdata[:, 0]))
        ymax = int(max(tempdata[:, 1]))
        zmax = int(max(tempdata[:, 2]))
        image_volume = np.zeros((xmax, ymax, zmax), dtype='int')
        for val in tempdata:
            image_volume[int(val[0]) - 1, int(val[1]) - 1, int(val[2]) - 1] = int(val[3])
            
    return image_volume

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
    # Set the desired padding size (in pixels) for each dimension
    padding_size = 1  # Adjust this value based on your needs
    
    # Create a padded volume with the same data type as the original image
    padded_volume = np.zeros(
        (image_volume.shape[0] + 2 * padding_size,
         image_volume.shape[1] + 2 * padding_size,
         image_volume.shape[2] + 2 * padding_size),
        dtype=image_volume.dtype,
    )
    
    # Calculate padding ranges for each dimension
    x_range = slice(padding_size, padding_size + image_volume.shape[0])
    y_range = slice(padding_size, padding_size + image_volume.shape[1])
    z_range = slice(padding_size, padding_size + image_volume.shape[2])
    
    # Copy the original image into the center of the padded volume
    padded_volume[x_range, y_range, z_range] = image_volume
    
    
    #Load padded volume
    binary_volume = np.squeeze(np.array(padded_volume))
    
    return binary_volume

def writeChenFormat(tempName,binary_volume,tifvoxelsize):
    file1 = open(tempName,'w')
    #chen files
    x_i,y_j,z_k = np.shape(binary_volume)
    file1.write(str(x_i-1)+' '+str(y_j-1)+' '+str(z_k-1)+' '+str(tifvoxelsize*10**-6)+'\n')
    file1.write("i j k voxel")
    count = 1
    for i in range(x_i):
        for j in range(y_j):
            for k in range(z_k):
                if binary_volume[i, j, k] == 1:
                   value = int(binary_volume[i, j, k])
                   file1.write(f"\n{i} {j} {k} {value}")
                   count = count + 1
                   # print(f"Point ({i}, {j}, {k}) has a value of 1")
                # else:
                    # print(f"Point ({i}, {j}, {k}) does not have a value of 1")#print(f"Point ({i}, {j}, {k}): {temp_volume[i, j, k]}")
    file1.close()

def getMesh(binary_volume,length,voxel_size):
    
    # Create a mesh using the marching cubes algorithm
    vertices, faces, _, _ = measure.marching_cubes(binary_volume)  ##add the parallel marching cubes here
    
    # Swap x and z to make it match the tif
    # Indices of the columns you want to swap
    column_index1 = 0  # Replace with the index of the first column
    column_index2 = 2  # Replace with the index of the second column
    
    # Swap the columns using array indexing
    vertices[:, [column_index1, column_index2]] = vertices[:, [column_index2, column_index1]]
 
    # Convert vertices to physical coordinates using voxel size
    vertices = vertices * voxel_size - voxel_size
    
    return vertices, faces

def stlSmoothing(FileName, vertices, faces, surfaceSettings ):
    
    # basestl = FileName+"no-smoothing.stl"
    # print('Start saving',basestl)
    # trimesh_mesh.export(basestl, file_type="stl_ascii")
    # print('Finish saving',basestl)
    
    # Apply filter iteration i
    if surfaceSettings['laplacianFlag']:
        # Load mesh from vertices and faces
        trimesh_mesh = loadMeshTrimesh(vertices,faces)
        filterName = '_laplacian'+str(surfaceSettings['laplacian_iter'])
        trimesh_mesh = trimesh.smoothing.filter_laplacian(trimesh_mesh, lamb=0.5, iterations=surfaceSettings['laplacian_iter'], volume_constraint=True)
        faces = trimesh_mesh.faces
        vertices = trimesh_mesh.vertices
        
    elif surfaceSettings['ScreenedPoissonFlag']:
        filterName = '_screened_poisson'+str(surfaceSettings['ScreenedPoisson_iter'])
        # Load mesh 
        ms = loadMeshPymeshlab(vertices,faces)
        ms.apply_filter('generate_surface_reconstruction_screened_poisson', depth=surfaceSettings['ScreenedPoisson_iter'], preclean=True)
        mesh = ms.current_mesh()
        vertices = mesh.vertex_matrix()
        faces = mesh.face_matrix() 
    else:
        filterName = ''
    
    if surfaceSettings['RemoveIslandsFlag']: 
        ms = remove_floating_islands_Stl(vertices,faces)
        removeIsland = '_NI'
        mesh = ms.current_mesh()
        vertices = mesh.vertex_matrix()
        faces = mesh.face_matrix()
    else:
        removeIsland = ''
        
    FileName = FileName+filterName+removeIsland
    
    return FileName, vertices, faces

def loadMeshTrimesh(vertices,faces):
    return trimesh.Trimesh(vertices=vertices, faces=faces)

def loadMeshPymeshlab(vertices,faces):
    import pymeshlab as ml
    # Create meshLab mesh from vertices and faces
    meshTarget = ml.Mesh(vertices,faces)
    
    # Create a MeshSet object
    ms = ml.MeshSet(verbose=True)
    
    ms.add_mesh(meshTarget)
    
    return ms

def remove_floating_islands_Stl(vertices,faces):

    # Load the mesh
    ms = loadMeshPymeshlab(vertices,faces)

    # Compute connected components and select small components for deletion
    ms.apply_filter('compute_selection_by_small_disconnected_components_per_face',nbfaceratio=1)

    # Delete the selected small components
    ms.apply_filter('meshing_remove_selected_vertices_and_faces')

    return ms

def checkMesh(vertices,faces):
    mesh = loadMeshTrimesh(vertices,faces)
    manifoldMesh =  mesh.is_volume
    # watertightMesh = mesh.is_watertight
    
    return manifoldMesh

def fixMesh(FileName,vertices,faces):
    # Load mesh 
    ms = loadMeshPymeshlab(vertices,faces)
    
    ms.apply_filter('generate_surface_reconstruction_screened_poisson', depth=8, preclean=True)
    ms.apply_filter('meshing_remove_null_faces')
    ms.apply_filter('meshing_repair_non_manifold_edges') 
    ms.apply_filter('meshing_repair_non_manifold_vertices')
    ms.apply_filter('meshing_remove_duplicate_faces')
    ms.apply_filter('meshing_remove_duplicate_vertices')
    ms.apply_filter('meshing_re_orient_faces_coherently')

    FileName = FileName+'_Fixed'
    # ms.save_current_mesh(FileName+'.stl', binary=False)
    
    return FileName, ms.vertex_matrix(), ms.face_matrix()

def computeProperties(stlName, vertices, faces, temp_volume, tifvoxelsize, savingOptions,surfacename):
    propertyList = [stlName]
    propertyNames = ['StlName']  # To store the names of selected properties

    if savingOptions['property_options']['min_max']:
        min_extents = np.min(vertices, axis=0)
        max_extents = np.max(vertices, axis=0)
        propertyList.extend([min_extents, max_extents])
        propertyNames.extend(["MinExtentsX", "MinExtentsY", "MinExtentsZ",
                              "MaxExtentsX", "MaxExtentsY", "MaxExtentsZ"])

    if savingOptions['property_options']['surf_area'] or savingOptions['property_options']['closed_volume'] or savingOptions['property_options']['porosity'] or savingOptions['property_options']['vol_by_area']:
        trimesh_mesh = loadMeshTrimesh(vertices, faces)
        mesh_volume = trimesh_mesh.volume
        mesh_surface_area = trimesh_mesh.area
        
    if savingOptions['property_options']['surf_area']:
        propertyList.append(mesh_surface_area)
        propertyNames.append("SurfaceArea")

    if savingOptions['property_options']['closed_volume']:
        propertyList.append(mesh_volume)
        propertyNames.append("ClosedVolume")

    if savingOptions['property_options']['vol_by_area']:
        lengthbyarea = mesh_volume / mesh_surface_area
        propertyList.append(lengthbyarea)
        propertyNames.append("Volume/SurfaceArea")

    if savingOptions['property_options']['porosity']:
        fulltempVolume = temp_volume.shape[0] * temp_volume.shape[1] * temp_volume.shape[2] * tifvoxelsize**3
        porosity = 1 - (mesh_volume / fulltempVolume)
        propertyList.append(porosity)
        propertyNames.append("Porosity")

    if savingOptions['property_options']['fiber_diameter']:
        meanDiameter, stdDiameter = getDiamter(temp_volume, tifvoxelsize, savingOptions['property_options']['fiber_diam_sphere'])
        propertyList.append(meanDiameter)
        propertyList.append(stdDiameter)
        propertyNames.extend(["fiber_diameter_Mean", "fiber_diameter_Std"])

    if savingOptions['property_options']['pore_distribution']:
        meanPore, stdPore = getPoreDistribution(temp_volume, tifvoxelsize, savingOptions['property_options']['pore_dist_sphere'])
        propertyList.append(meanPore)
        propertyList.append(stdPore)
        propertyNames.extend(["meanPore", "stdPore"])
    
    if savingOptions['property_options']['FiberAngle'] or savingOptions['property_options']['FiberLength']:
        azimuthMean, elevationMean, lengthMean, azimuthSTD, elevationSTD,lengthSTD  = analyzeCenterLine(temp_volume,tifvoxelsize,surfacename,savingOptions['property_options']['FiberAnglePlane'])
        if savingOptions['property_options']['FiberAngle']:
            propertyList.append(azimuthMean)
            propertyNames.append("MeanAzimuthAngle")
            propertyList.append(azimuthSTD)
            propertyNames.append("StDAzimuthAngle")
            propertyList.append(elevationMean)
            propertyNames.append("MeanElevationAngle")
            propertyList.append(elevationSTD)
            propertyNames.append("StDElevationAngle")
        if savingOptions['property_options']['FiberLength']:
            propertyList.append(lengthMean)
            propertyNames.append("MeanLength")
            propertyList.append(lengthSTD)
            propertyNames.append("StDLength")
        
    writeProperties(savingOptions, propertyNames, propertyList)

def getPoreDistribution(image_volume, tifvoxelsize, sphereSize):
    # Invert image_volume
    image_volume = (image_volume == 0).astype(int)

    # Distance transform
    distance_transform = distance_transform_edt(image_volume)
    
    # Detect local maxima
    local_maxima_coords = peak_local_max(distance_transform, min_distance=int(sphereSize/2), labels=image_volume.astype(int))
    
    # Measure diameters
    pore_diameters = []
    
    for max_coords in local_maxima_coords:
        distances = distance_transform[tuple(max_coords)]
        pore_diameters.append(2 * np.max(distances))
    
    # Scale given voxel size
    pore_diameters = np.multiply(pore_diameters,tifvoxelsize)-tifvoxelsize/2
    
    meanPore = np.mean(pore_diameters)
    stdPore = np.std(pore_diameters)
    
    return meanPore, stdPore

def getDiamter(image_volume,tifvoxelsize,sphereSize):
    # Distance transform
    distance_transform = distance_transform_edt(image_volume)
    
    # Detect local maxima
    local_maxima_coords = peak_local_max(distance_transform, min_distance=int(sphereSize/2), labels=image_volume.astype(int))
    
    # Measure diameters
    fiber_diameters = []
    
    for max_coords in local_maxima_coords:
        distances = distance_transform[tuple(max_coords)]
        fiber_diameters.append(2 * np.max(distances))
    
    # Scale given voxel size
    fiber_diameters = np.multiply(fiber_diameters,tifvoxelsize)-tifvoxelsize/2
    
    meanDiameter = np.mean(fiber_diameters)
    stdDiameter = np.std(fiber_diameters)
    
    return meanDiameter, stdDiameter

def analyzeCenterLine(image,tifvoxelsize,surfacename,plane='XY'):
    
    # Preprocess the image
    # Apply Gaussian filter with sigma=2
    image_smoothed = filters.gaussian(image, sigma=1)
    
    # Convert to binary: 1 for values greater than the threshold, 0 otherwise
    image_smoothed = (image_smoothed >= np.max(image_smoothed) * 0.5).astype(np.uint8)
    
    # Skeletonize the image
    skeleton = morphology.skeletonize(image_smoothed)
    
    tiff.imwrite(surfacename[:-4]+'_skeleton.tif', skeleton.astype(np.uint16),imagej=True)
    
    # Extract centerline coordinates
    coords = np.column_stack(np.where(skeleton > 0))  # Get (Z, Y, X) coordinates
    
    # Build graph from skeleton pixels
    G = nx.Graph()
    for z, y, x in coords:
        G.add_node((z, y, x))
    
    # Define 26-connectivity neighbors
    neighbors_26 = [(dz, dy, dx) for dz in [-1, 0, 1] 
                                    for dy in [-1, 0, 1] 
                                    for dx in [-1, 0, 1] if not (dz == dy == dx == 0)]
    
    # Set a **distance threshold** to avoid unwanted shortcuts
    max_distance = np.sqrt(3)  # Maximum Euclidean distance for direct neighbors
    
    
    # Connect neighboring pixels while **pruning bad connections**
    for z, y, x in coords:
        for dz, dy, dx in neighbors_26:
            neighbor = (z+dz, y+dy, x+dx)
            if neighbor in G:
                # Compute Euclidean distance
                distance = np.linalg.norm(np.array([z, y, x]) - np.array(neighbor))
                if distance <= max_distance:
                    G.add_edge((z, y, x), neighbor, weight=distance)
    
    # Compute the **Minimal Spanning Tree (MST)** to remove unwanted edges
    MST = nx.minimum_spanning_tree(G)
    
    # Identify true branch points (nodes with degree > 2)
    branch_points = [node for node in MST.nodes() if MST.degree(node) > 2]
    
    # Split centerlines at detected branch points
    split_centerlines, graph_centerlines = split_and_order_centerlines(MST, branch_points)
    
    # Number of centerlines before and after split
    num_centerlines = len(list(nx.connected_components(MST)))
    num_split_centerlines = len(split_centerlines)
    
    
    # labeled_image = assign_voxels_to_centerlines_with_kdtree(image, split_centerlines)
    
    # tiff.imwrite(fileName[:-4]+'test.tif', labeled_image.astype(np.uint16),imagej=True)
    
    # plot_centerlines_and_voxels(image, split_centerlines, labeled_image)
    
    # Compute angles
    centerline_properties = calculate_centerline_properties(split_centerlines,tifvoxelsize,image,plane)
    
    azimuthMean,elevationMean,lengthMean = np.mean(centerline_properties,axis=0)
    azimuthSTD, elevationSTD,lengthSTD = np.std(centerline_properties, axis=0, ddof=0)
    
    return azimuthMean,elevationMean,lengthMean, azimuthSTD, elevationSTD,lengthSTD 
    
# Function to split centerlines at branch points
def split_and_order_centerlines(graph, branch_nodes, steps=4):
    """
    Splits the graph's centerlines at branch points with improved handling of intersections.
    Instead of removing the branch node itself, it looks at the connected branches and removes
    (shifts) the voxel from the branch with the most deviated direction.
    
    Parameters:
        graph (networkx.Graph): The input graph representing the skeleton.
        branch_nodes (list): List of nodes where branches occur.
        steps (int): How many voxels along the branch to consider for adjustment (default=1).
        
    Returns:
        tuple: (split_centerlines, modified_graph)
            - split_centerlines: a list of ordered centerline node lists.
            - modified_graph: the graph after branch adjustment.
    """
    # Work on a copy so that the original graph is not modified
    G = graph.copy()
    
    # For each branch node, adjust the intersection by removing the first voxel
    # along the branch that deviates most from the others.
    for branch in branch_nodes:
        neighbors = list(G.neighbors(branch))
        if len(neighbors) <= 1:
            # Not really an intersection if only one neighbor.
            continue
        
        branch_vectors = {}
        # For each connected branch from the branch node, compute a unit direction vector.
        for n in neighbors:
            # If possible, follow the branch "steps" voxels ahead.
            current = n
            prev = branch
            for _ in range(steps - 1):
                # Look for a neighbor that is not the previous node.
                next_candidates = [nbr for nbr in G.neighbors(current) if nbr != prev]
                if next_candidates:
                    prev = current
                    current = next_candidates[0]
                else:
                    break
            # Compute vector from branch to the voxel 'current'
            vec = np.array(current) - np.array(branch)
            norm = np.linalg.norm(vec)
            if norm != 0:
                branch_vectors[n] = vec / norm
        
        if len(branch_vectors) < 2:
            # Not enough branches to compare
            continue
        
        # Compute total angular difference for each branch direction
        differences = {}
        for n1, v1 in branch_vectors.items():
            total_angle = 0
            for n2, v2 in branch_vectors.items():
                if n1 == n2:
                    continue
                # Compute angle difference using dot product
                dot = np.dot(v1, v2)
                # Clip dot to avoid numerical issues
                dot = np.clip(dot, -1, 1)
                angle = np.arccos(dot)
                total_angle += angle
            differences[n1] = total_angle
        
        # Identify the neighbor whose branch has the maximum total angular difference.
        branch_to_adjust = max(differences, key=differences.get)
        
        # Instead of removing the branch node, remove the neighbor on the branch that is most different.
        if branch_to_adjust in G:
            G.remove_node(branch_to_adjust)
    
    # After adjusting the intersections, split the modified graph into ordered centerlines.
    split_centerlines = []

    # Process each connected component separately
    for component in nx.connected_components(G):
        subgraph = G.subgraph(component)

        # Find endpoints (nodes with only 1 adjacent node)
        endpoints = [node for node in component if len(subgraph._adj[node]) == 1]

        if len(endpoints) < 2:
            # If no clear start, just keep it as is
            split_centerlines.append(list(component))
            continue

        # Start from one of the endpoints
        start = endpoints[0]
        ordered_centerline = []
        visited = set()

        # Traverse from start node in order
        node = start
        while node is not None:
            ordered_centerline.append(node)
            visited.add(node)

            # Move to next node
            next_nodes = [n for n in subgraph._adj[node] if n not in visited]
            node = next_nodes[0] if next_nodes else None  # Pick the next unvisited node

        split_centerlines.append(ordered_centerline)

    return split_centerlines, G

def calculate_centerline_properties(split_centerlines,tifvoxelsize,image, plane='XY', step_size=4):
    """
    Calculates average azimuth, elevation, length, and distance to background 
    for endpoints of each centerline.

    Parameters:
        split_centerlines (list of lists): Ordered centerlines, each a list of (x, y, z) tuples.
        tifvoxelsize (float): Size of one voxel in real-world units.
        image (ndarray): 3D image array where background is 0.
        plane (str): Plane used for azimuth/elevation computation ('XY', 'XZ', 'YZ').

    Returns:
        list of dicts: Each dict contains avg_azimuth, avg_elevation, length, 
                       first_point_distance, last_point_distance.
    """
    # Compute distance transform from background (0 == background)
    dist_transform = distance_transform_edt(image > 0)
    centerline_properties = []

    for centerline in split_centerlines:
        vectors = []
        length = 0.0
        
        # Compute direction vectors and segment lengths
        for i in range(0, len(centerline) - step_size, step_size):
            p1 = np.array(centerline[i])  
            p2 = np.array(centerline[min(i + step_size, len(centerline) - 1)])
            vec = p2 - p1  
            vectors.append(vec)
            length += np.linalg.norm(vec)*tifvoxelsize  # Sum Euclidean distances

        if not vectors:
            # centerline_properties.append([None, None, 0.0])
            continue

        vectors = np.array(vectors)
        
        # Compute mean direction vector
        mean_vector = np.mean(vectors, axis=0)
        norm = np.linalg.norm(mean_vector)

        if norm == 0:
            # centerline_properties.append([None, None, length])
            continue

        # Compute azimuth and elevation based on selected plane
        if plane == 'XY':
            avg_azimuth = np.arctan2(mean_vector[1], mean_vector[2])  # θ (rotation in XY)
            avg_elevation = np.arcsin(mean_vector[0] / norm)  # φ (tilt in Z)
        elif plane == 'XZ':
            avg_azimuth = np.arctan2(mean_vector[0], mean_vector[2])  # θ (rotation in XZ)
            avg_elevation = np.arcsin(mean_vector[1] / norm)  # φ (tilt in Y)
        elif plane == 'YZ':
            avg_azimuth = np.arctan2(mean_vector[0], mean_vector[1])  # θ (rotation in YZ)
            avg_elevation = np.arcsin(mean_vector[2] / norm)  # φ (tilt in X)
        else:
            raise ValueError("Invalid plane option. Choose from 'XY', 'XZ', or 'YZ'.")
        
        # Get scaled distance to background for first and last points
        first_point = tuple(np.round(centerline[0]).astype(int))
        last_point = tuple(np.round(centerline[-1]).astype(int))

        first_distance = dist_transform[first_point] * tifvoxelsize
        last_distance = dist_transform[last_point] * tifvoxelsize
        
        length += first_distance + last_distance

        centerline_properties.append([float(np.degrees(avg_azimuth)), float(np.degrees(avg_elevation)), float(length)])

    return np.array(centerline_properties,dtype=float)

def writeProperties(savingOptions, propertyNames, propertiesList):
    
    if savingOptions['property_path'] == '':
        savingOptions['property_path'] = 'propertyFile.txt' 
    
    
    # Check if file exists to determine if we need to create a new name
    file_exists = os.path.exists(savingOptions['property_path'])
    
    if re.search(r'_V(\d+)_', propertiesList[0]).group(1) == '0':
        if file_exists:
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
        
        
        # Open the new file in write mode to save the data
        with open(savingOptions['property_path'], 'w') as f:
            # Write headers
            f.write('\t'.join(propertyNames) + '\n')
            
            # Write the property values
            f.write('\t'.join(f"{float(x):.4f}" if (isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('e-', '', 1).replace('e+', '', 1).isdigit())) and abs(float(x)) >= 1e-4  
                else f"{float(x):.4g}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('e-', '', 1).replace('e+', '', 1).isdigit())  
                else str(x) for x in propertiesList) + '\n')
    else:
        with open(savingOptions['property_path'], '+a') as f:
            # Write the property values
            f.write('\t'.join(f"{float(x):.4f}" if (isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('e-', '', 1).replace('e+', '', 1).isdigit())) and abs(float(x)) >= 1e-4  
                else f"{float(x):.4g}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('e-', '', 1).replace('e+', '', 1).isdigit())  
                else str(x) for x in propertiesList) + '\n')  
        

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
    
    filenames = [r'E:\LuisChacon\HERMES\1-31-25_Americarb_HiRes\1-31-25_Americarb_HiRes_binarizedtifs.labels.filtered_cropped.tif',] # one or more Ex: ['file1.tif', 'file2.dat', ...]
    
    filevoxels = [1.33174] # one or more correspondig to filenames Ex: [1, 1.8, ...]
    
    # Saving Flags 1 or 0 for True or False, respectively
    savingOptions = {
        "tiff_save": 0,
        "tiff_path": '', # Path where files will be saved or '' for current directory
        "voxel_save": 0,
        "voxel_path": '',  # Path where files will be saved or '' for current directory
        "stl_save": 0,
        "stl_path": '',  # Path where files will be saved or '' for current directory
        "property_save": 1,
        "property_path": r'E:\LuisChacon\HERMES\1-31-25_Americarb_HiRes\Americarb_HiRes_properties_700.txt',  # Path where files will be saved or '' for current directory
        "property_options": {
            "min_max": 0,
            "surf_area": 1,
            "closed_volume": 1,
            "vol_by_area": 1,
            "porosity": 1,
            "fiber_diameter": 0,
            "fiber_diam_sphere": 0,
            "pore_distribution": 0,
            "pore_dist_sphere": 0,
            "FiberAngle": 0,
            "FiberAnglePlane": 'YZ',
            "FiberLength": 0,
            
        }
    }
    print(savingOptions)
    
    if croppingFlag == 'Regular':
        # If both are set to 0 Full volume will be prioritize
        volumeLength = 700 # In um or enter 0 for Full volume
        numVolumes = 200 # Number of volumes or enter 0 for Lego

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