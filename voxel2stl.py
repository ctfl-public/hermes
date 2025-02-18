#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 16:12:17 2023

@author: ctfl
"""
import numpy as np
import trimesh
from skimage import measure
import imageio
import random
import tifffile as tiff
import itertools
from scipy.spatial import ConvexHull
from collections import defaultdict
import multiprocessing
import pymeshlab as ml
import os
from scipy.ndimage import distance_transform_edt
from skimage.feature import peak_local_max


def computeProperties(stlName, vertices,faces,temp_volume,trimesh_mesh,tifvoxelsize):
    
    min_extents = np.min(vertices, axis=0)
    max_extents = np.max(vertices, axis=0)
    
    mesh_surface_area = trimesh_mesh.area

    mesh_volume = trimesh_mesh.volume

    lengthbyarea = mesh_volume/mesh_surface_area
    
    fulltempVolume = temp_volume.shape[0]*temp_volume.shape[1]*temp_volume.shape[2]*tifvoxelsize**3
    porosity_ = 1 - (mesh_volume/fulltempVolume)
        
    meanDiameter, stdDiameter = getDiamter(temp_volume,tifvoxelsize)
    
    return stlName, min_extents,max_extents, mesh_surface_area, mesh_volume, lengthbyarea, porosity_, meanDiameter, stdDiameter

def checkMesh(vertices,faces):
    mesh = loadMeshTrimesh(vertices,faces)
    manifoldMesh =  mesh.is_volume
    watertightMesh = mesh.is_watertight
    
    return manifoldMesh, watertightMesh

def loadMeshTrimesh(vertices,faces):
    return trimesh.Trimesh(vertices=vertices, faces=faces)
    
def loadMeshPymeshlab(vertices,faces):
    # Create meshLab mesh from vertices and faces
    meshTarget = ml.Mesh(vertices,faces)
    
    # Create a MeshSet object
    ms = ml.MeshSet(verbose=True)
    
    ms.add_mesh(meshTarget)
    
    return ms

def removeIslands(min_face_count,vertices,faces):
    ms = loadMeshPymeshlab(vertices,faces)
    
    ms.apply_filter("meshing_remove_connected_component_by_face_number", mincomponentsize=min_face_count, removeunref=True)
    
    vertices = ms.vertex_matrix()
    faces = ms.face_matrix()
    
    return vertices, faces

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

    FileName = FileName+'_Fixed.stl'
    ms.save_current_mesh(FileName, binary=False)
    
    return loadMeshTrimesh(ms.vertex_matrix(),ms.face_matrix())
    
    
def stlSmoothing(FileName, vertices, faces,temp_volume,tifvoxelsize):
    
    # Load mesh from vertices and faces
    trimesh_mesh = loadMeshTrimesh(vertices,faces)

    propertiesList = computeProperties(FileName+'_noSmoothing',vertices,faces,temp_volume,trimesh_mesh,tifvoxelsize)
    writeProperties(propertiesFile, propertiesList)
    
    # basestl = FileName+"no-smoothing.stl"
    # print('Start saving',basestl)
    # trimesh_mesh.export(basestl, file_type="stl_ascii")
    # print('Finish saving',basestl)
    
    # print('Start computing properites',basestl)
    # propertiesList = computeProperties(basestl,vertices,faces,temp_volume,trimesh_mesh,tifvoxelsize)
    # # print('Finish computing properites',basestl)
    
    # writeProperties(propertiesFile, propertiesList)
    
    # Apply filter iteration i
    if laplacian == 1:
        triFlag = 1
        filterName = 'laplacian'+str(iter)
        trimesh_mesh = trimesh.smoothing.filter_laplacian(trimesh_mesh, lamb=0.5, iterations=iter, volume_constraint=True)
    
    elif humphrey == 1:
        triFlag = 1
        filterName = 'humphrey'+str(iter)
        trimesh_mesh = trimesh.smoothing.filter_humphrey(trimesh_mesh, alpha=0.1, beta=0.5, iterations=iter, laplacian_operator=None)
    
    elif taubin == 1:
        triFlag = 1
        filterName = 'taubin'+str(iter)
        trimesh_mesh = trimesh.smoothing.filter_taubin(trimesh_mesh, lamb=0.5, nu=0.5, iterations=iter, laplacian_operator=None)
    
    elif screened_poisson == 1:
        depth=8
        filterName = 'screened_poisson'+str(depth)
        
        # Load mesh 
        ms = loadMeshPymeshlab(vertices,faces)
        ms.apply_filter('generate_surface_reconstruction_screened_poisson', depth=depth, preclean=True)
    
    else:
        triFlag = 1
        filterName = ''
    
    FileName = FileName+filterName+'.stl'
    
    volume_check, watertight_check = checkMesh(trimesh_mesh.vertices,trimesh_mesh.faces)

    # if ((volume_check == False) or (watertight_check == False)):
    #     trimesh_mesh = fixMesh(FileName,trimesh_mesh.vertices,trimesh_mesh.faces)

    #     volume_check, watertight_check = checkMesh(trimesh_mesh.vertices,trimesh_mesh.faces)

    # if ((volume_check == False) or (watertight_check == False)):
    #     print("Warning: Voulume check fail")
        
    if triFlag:
        trimesh_mesh.export(FileName, file_type="stl_ascii")
        faces = trimesh_mesh.faces
        vertices = trimesh_mesh.vertices
        
    elif screened_poisson:
        ms.save_current_mesh(FileName, binary=False)
        vertices = ms.vertex_matrix()
        faces = ms.face_matrix()
    
    # Compute properties of smooth STL
    propertiesList = computeProperties(FileName,vertices,faces,temp_volume,trimesh_mesh,tifvoxelsize)
    writeProperties(propertiesFile, propertiesList)
    
    return FileName, vertices, faces

def writeProperties(fileName, propertiesList):
    with open(fileName, 'a+') as f:
        for poperValue in propertiesList:
            f.write(str(poperValue)+'\t')
        f.write('\n')
        

def compute_volume(vertices, faces):
        volume = 0.0
        for face in faces:
            v0, v1, v2 = vertices[face]
            volume += np.dot(v0, np.cross(v1, v2)) / 6.0
        return abs(volume)

def compute_surface_area(vertices, faces):
      area = 0.0
      for face in faces:
        v0, v1, v2 = vertices[face]
        e1 = v1 - v0
        e2 = v2 - v0
        cross_product = np.cross(e1, e2)
        area += 0.5 * np.linalg.norm(cross_product)
      return area

# def compute_volume(vertices, faces):
#     v0 = vertices[faces[:, 0]]  # Select v0 for all faces
#     v1 = vertices[faces[:, 1]]  # Select v1 for all faces
#     v2 = vertices[faces[:, 2]]  # Select v2 for all faces
    
#     cross_product = np.cross(v1 - v0, v2 - v0)  # Compute cross products for all faces
#     volume = np.sum(np.dot(v0, cross_product.T)) / 6.0  # Take dot product and sum
    
#     return abs(volume)

# def compute_surface_area(vertices, faces):
#     v0 = vertices[faces[:, 0]]  # Select v0 for all faces
#     v1 = vertices[faces[:, 1]]  # Select v1 for all faces
#     v2 = vertices[faces[:, 2]]  # Select v2 for all faces
    
#     e1 = v1 - v0  # Compute edge 1 for all faces
#     e2 = v2 - v0  # Compute edge 2 for all faces
    
#     cross_product = np.cross(e1, e2)  # Compute cross product for all faces
#     area = np.sum(0.5 * np.linalg.norm(cross_product, axis=1))  # Compute area
    
#     return area

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
    #print(binary_volume[:5, :, :])
    return vertices, faces

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

def writeChenFormat(tempName,binary_volume,tifvoxelsize):
    chen = tempName+str(".dat")
    file1 = open(chen,'w')
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
                   print(f"Point ({i}, {j}, {k}) has a value of 1")
                else:
                    print(f"Point ({i}, {j}, {k}) does not have a value of 1")#print(f"Point ({i}, {j}, {k}): {temp_volume[i, j, k]}")
    pcount = 1
    file1.close()
    
def saveProperties(fileName, listProperties):
    with open(fileName, 'a') as f:
        for propertyValue in listProperties:
            f.write(str(propertyValue)+'\t')
        f.write('\n')

def getDiamter(image_volume,tifvoxelsize):
    # Distance transform
    distance_transform = distance_transform_edt(image_volume)
    
    # Detect local maxima
    local_maxima_coords = peak_local_max(distance_transform, min_distance=5, labels=image_volume.astype(int))
    
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
    
def getstl(surfacename, tifvoxelsize, temp_number,volumeLength, corner): #NEEED TOO REStructure this
    
    print('start reading tif to creat stl temp %s\n'%(temp_number))
    
    # Create image_volume
    image_volume = loadData(surfacename)
           
    
    print('Finish reading tif to creat stl temp %s\n'%(temp_number))
    
        
    # Surface file name
    tempName = surfacename[:-4]+'_V%i_%i-%i-%i-%s-'%(temp_number,corner[0],corner[1],corner[2],volumeLength)
    
    if volumeLength != 'Full':
        # adjust nummber volumelength 
        volumeLength = int(volumeLength/tifvoxelsize)
        
        print('Volume is %s in voxels and voxelsize is %s\n'%(volumeLength,tifvoxelsize))
    
        # Crop the volume of interest
        temp_volume = image_volume[corner[0]:corner[0]+volumeLength,corner[1]:corner[1]+volumeLength,corner[2]:corner[2]+volumeLength]
        
        print('temp_volume is %s\n'%(str(np.shape(temp_volume))))
        
    else: # Create stl from full tif
        temp_volume = image_volume
    
    if np.sum(temp_volume) == 0:
        print('Empty Volume, there is no material!')
        return 'Empty'
    # Make a binary MTX
    temp_volume = temp_volume/ np.max(temp_volume)
    
    # Calculate porosity
    fulltempVolume = temp_volume.shape[0]*temp_volume.shape[1]*temp_volume.shape[2]
    materialVolume = np.sum(temp_volume/np.max(temp_volume))     ### This calculation might be incorrect
    porosity = round((fulltempVolume - materialVolume)/fulltempVolume , 4)
    
    # Creat padding around volume 
    print('Creating padding temp %s'%(surfacename))
    binary_volume = createPadding(temp_volume)
    
    # Remove Ilands
    if chenFlag == 1:
        writeChenFormat(tempName,binary_volume,tifvoxelsize)
        
    # Get vertices and faces 
    print('Starting mesh creation for temp %s'%(tempName))
    vertices, faces = getMesh(binary_volume,volumeLength,tifvoxelsize)
    print('Finish mesh creation for temp %s'%(tempName))
    
    
    print('Starting smoothing for temp %s'%(tempName))
    # Perform smoothing 
    tempName, vertices, faces = stlSmoothing(tempName, vertices,faces,temp_volume,tifvoxelsize)   
    print('Finish smoothing for temp %s'%(tempName))
    
    
    print('Starting tif saving for  temp %s'%(str(tempName)))
    # Save the volume as a 3D TIFF file (uncomment to double check stl)[:-4]
    tiff.imwrite(tempName[:-4]+'.tif', binary_volume[1:-1,1:-1,1:-1].astype(np.uint16),imagej=True)

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
            for temp in range(numVolumes):
                tempName = random.choice(filenames)
                tempNameIndex = filenames.index(tempName)
                tempMTX[tempNameIndex] += 1
     
    temp_number = 0
    for surf in filenames:
        tempNameIndex = filenames.index(surf)
        
        # Load data
        image_volume = loadData(surf)
                
        # max voxel length in x, y, and z
        voxelsLegth = (image_volume.shape[0],image_volume.shape[1],image_volume.shape[2])
        
        if normalFlag:
            if volumeLength == 0: # create stl from all the volume
                corner = np.zeros(3, dtype='int')
                fullvolume = 'Full'
                getstl(surf, filevoxels[tempNameIndex], temp_number,fullvolume, corner)
                temp_number += 1
            
            elif numVolumes == 0:
                # Number of volumes in each direction
                dimX = int(voxelsLegth[0]*filevoxels[tempNameIndex]/volumeLength)
                dimY = int(voxelsLegth[0]*filevoxels[tempNameIndex]/volumeLength)
                dimZ = int(voxelsLegth[0]*filevoxels[tempNameIndex]/volumeLength)
                
                totalvolumes = dimX*dimY*dimZ
                # if totalvolumes > 10:
                #     print('Do this in parallel, %i volumes'%(totalvolumes))
                #     return
                xCorners = [i*int(volumeLength/filevoxels[tempNameIndex]) for i in range(dimX)]
                yCorners = [i*int(volumeLength/filevoxels[tempNameIndex]) for i in range(dimY)]
                zCorners = [i*int(volumeLength/filevoxels[tempNameIndex]) for i in range(dimZ)]
                corners = list(itertools.product(xCorners,yCorners,zCorners))
                for corner in corners:
                    getstl(surf, filevoxels[tempNameIndex], temp_number,volumeLength, corner)
                    temp_number += 1
                    
            else:
                for times in range(tempMTX[tempNameIndex]):
                    
                    print('corner',times,'of',surf)
                    if numVolumes != 0:
                         
                        # name of iteration volume
                        # tempName = filenames[:-4]+'_V%i'%(temp)
                        
                        corner = np.zeros(3, dtype='int')
                        # get random temp corner
                        corner[0] = random.randint(0,voxelsLegth[0]-volumeLength) 
                        corner[1] = random.randint(0,voxelsLegth[1]-volumeLength)
                        corner[2] = random.randint(0,voxelsLegth[2]-volumeLength)
                        # center crop
                        # corner[0] = (voxelsLegth[0]-volumeLength)/2 #random.randint(0,voxelsLegth[0]-volumeLength) 
                        # corner[1] = (voxelsLegth[1]-volumeLength)/2 #random.randint(0,voxelsLegth[1]-volumeLength)
                        # corner[2] = (voxelsLegth[2]-volumeLength)/2 #random.randint(0,voxelsLegth[2]-volumeLength)

                        
                        getstl(surf, filevoxels[tempNameIndex], temp_number,volumeLength, corner)
                        temp_number += 1

        elif cornerFlag:
            for corner in cornersMTX:
                getstl(surf, filevoxels[tempNameIndex], temp_number,volumeLength, corner)
                temp_number += 1

    
        
if __name__ == '__main__':
    
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    random.seed(500)
    filenames = [r'sample1_100.dat' ] #, 'S2_0.9438_2040_NI8.tif' , 'S4_1.0487_2201_NI8.tif' ,\
                  # 'S6_0.9928_1322_NI8.tif', 'S8_0.9556_2005_NI8.tif', 'S1_0.8580_1518_NI8.tif',  \
                  #     'S3_0.9438_1884_NI8.tif',  'S5_0.9438_1984_NI8.tif',  'S7_0.9556_1929_NI8.tif',  \
                  #         'S9_1.00775_2255_NI8.tif'] # One or more
    filevoxels = [1] #,0.9438,1.0487,0.9928,0.9556,0.8580,0.9438,0.9438,0.9556,1.00775] # One or more
    # filenames = ['grid_400.tif'] # One or more
    # filevoxels = [1]
    laplacian, humphrey, taubin, screened_poisson = 1,0,0,0 # Any one filter should be set to 1, rest 0  
    iter = 2 # iterations for the Filter
    min_face_count = 25000
    pde_mode = 0 # 0 or 1 -> in 1 hanging fibers will be removed according to min_face_count.
    chenFlag = 0 # same as pde mode
    
    surfaceSettings = laplacian, humphrey,taubin, iter, min_face_count, pde_mode
    
    normalFlag = 1
    cornerFlag = 0
    croppingFlags = normalFlag, cornerFlag
    
    if normalFlag:
        numVolumes = 1 # zero for Lego
        volumeLength = 0 # zero for full volume
        cropSettings = filenames, filevoxels, numVolumes, volumeLength
    
    elif cornerFlag:
        cornersMTX = np.array([[0,1020,0],[0,1020,68]]) # One or more in Array
        volumeLength = 200 # One or more in Array
        
        cropSettings = filenames, filevoxels, cornersMTX, volumeLength
        
    propertiesFile = r'propertiesTest.txt'
    
    with open(propertiesFile,'a+') as f:
        f.write('stlName\tmin_extents\tmax_extents\tmesh_surface_area\tmesh_volume\tlengthbyarea\tporosity_\tmeanDiameter\tstdDiameter\n')
    # file_path = "properties-"+str(laplacian)+str(humphrey)+str(taubin)+"-"+str(iter)+".dat"
    # file = open(file_path, 'w')

    voxel2stl(croppingFlags,cropSettings, surfaceSettings)

