import imageio
import numpy as np
import matplotlib.pyplot as plt
import os
import itertools
import pandas as pd
import matplotlib as mpl

mpl.rcParams['axes.linewidth'] = 1.5      # axis border thickness
mpl.rcParams['xtick.major.width'] = 1.5  # x ticks thickness
mpl.rcParams['ytick.major.width'] = 1.5  # y ticks thickness

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

def get1DPorosity(materialMTX,volumeMTX,openPoreMTX,direction,bins=0,voxel_size=1): # voxel_size in um 
    """
    Count non-zeros in materialMTX and volumeMTX along a given direction and bin them.
    
    Parameters:
        materialMTX (ndarray): 3D numpy array for material
        volumeMTX (ndarray): 3D numpy array for volume
        direction (str): 'x', 'y', or 'z'
        bins (int): number of bins along the chosen axis
    
    Returns:
        material_counts (ndarray): counts of nonzeros per bin for material
        void_counts (ndarray): counts of nonzeros per bin for void
    """
    
    # Map direction to axis
    axis_map = {'x': 2, 'y': 1, 'z': 0}
    if direction not in axis_map:
        raise ValueError("Direction must be 'x', 'y', or 'z'")
    
    axis = axis_map[direction]
    size = materialMTX.shape[axis]
    
    # If bins=0, make one bin per voxel
    if bins == 0:
        bins = size

    # Bin edges
    edges = np.linspace(0, size, bins+1, dtype=int)
    
    porosity = []
    openPorosity = []
    locations = []
    firstValueFlag = 1
    # Loop through bins
    for i in range(bins):
        slc = [slice(None)] * 3
        slc[axis] = slice(edges[i], edges[i+1])
        
        mat_bin = materialMTX[tuple(slc)]
        volume_bin = volumeMTX[tuple(slc)]
        # openPore_bin = openPoreMTX[tuple(slc)]
        
        mat_count = np.count_nonzero(mat_bin)
        volume_count = np.count_nonzero(volume_bin)
        void_count = volume_count - mat_count
        if void_count < 0:
            print()

        # openPore_count = np.count_nonzero(openPore_bin)
        
        
        if volume_count > 0:
            porosity.append(void_count / volume_count)
            # openPorosity.append(openPore_count/volume_count)

            # Bin center in physical units
            center = ((edges[i] + edges[i+1]) / 2.0) * voxel_size
            if firstValueFlag:
                adjustemnt = center
                center = 1
                firstValueFlag = 0
            else:
                center -= adjustemnt

            locations.append(center)

    return locations,porosity,#openPorosity

# def plot_porosity_scatter(locations, porosity, openPorsity, save_path, xlabel="Distance (um)", ylabel="Porosity", title=None, labels=None):
def plot_porosity_scatter(locations, porosity, save_path, xlabel="Distance (um)", ylabel="Porosity", title=None, labels=None):
    """
    Plot porosity vs. location as scatter data (single or multiple datasets) and save as PNG (300 dpi).
    
    Parameters:
        locations (list/array or list of lists/arrays): x-axis data
        porosity (list/array or list of lists/arrays): y-axis data
        save_path (str): output file path (.png)
        xlabel (str): label for x-axis
        ylabel (str): label for y-axis
        title (str): optional plot title
        labels (list): optional legend labels for each dataset
    """
    plt.figure(figsize=(6,4), dpi=150)

    plt.rcParams.update({
    'font.weight': 'bold',
    'axes.labelweight': 'bold',
    'axes.titleweight': 'bold'
    })

    plt.rcParams['font.weight'] = 'bold'
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['xtick.labelsize'] = 8
    plt.rcParams['ytick.labelsize'] = 8
    
    # Ensure inputs are lists of datasets
    if not isinstance(locations[0], (list, tuple, range)) and not hasattr(locations[0], "__len__"):
        locations = [locations]
        porosity = [porosity]
        # openPorsity = [openPorsity]

    # Define a fixed set of colors and markers
    colors = list(plt.cm.tab10.colors)  # 10 distinct colors
    markers = ['o', 's', '^', 'd', 'v', '<', '>', 'p', '*', 'h']

    # for i, (loc, por, openPor) in enumerate(zip(locations, porosity, openPorsity)):
    for i, (loc, por) in enumerate(zip(locations, porosity)):
        # Define distinct colors and markers
        color = colors[i % len(colors)]      # cycle through colors
        marker = markers[i % len(markers)]  # cycle through markers
        label = labels[i] if labels and i < len(labels) else None

        plt.scatter(loc, por, marker=marker, s=1, facecolors=color, label=label)
        # plt.scatter(loc, openPor, marker=marker, s=1, facecolors='k', label=label+': Open Porosity')

    plt.xlabel(xlabel, fontweight='bold')
    plt.ylabel(ylabel, fontweight='bold')

    # Get current axis (since we're not using subplots)
    ax = plt.gca()

    # Turn on minor ticks
    ax.minorticks_on()

    # if title:
    #     plt.title(title)

    if labels:
        plt.legend(frameon=False)
        # plt.text(,fontsize=12, fontweight='bold')
        
    plt.tick_params(direction='out')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()

# def save_porosity_data(locations, porosity, openPorosity, save_path):
def save_porosity_data(locations, porosity, save_path):
    """
    Save porosity and locations to a text file with two columns.
    
    Parameters:
        locations (list or array): physical bin centers
        porosity (list or array): porosity values
        save_path (str): output text file path (.txt or .csv)
    """
    # data = np.column_stack((locations, porosity, openPorosity))
    data = np.column_stack((locations, porosity))
    header = "Location\tPorosity\tOpenPorosity"
    np.savetxt(save_path, data, header=header, fmt="%.6f", delimiter="\t")

def load_porosity_data(file_path):
    """
    Load porosity data from a text file saved with save_porosity_data().
    Returns locations, porosity as numpy arrays.
    """
    data = np.loadtxt(file_path, skiprows=1)
    locations, porosity,openPorosity = data[:,0], data[:,1], data[:,2]
    return locations, porosity, openPorosity

def load_porosity_distributions(folders, prefix="", suffix=".txt"):
    """
    Load porosity distributions from files in multiple folders.
    Files must end with '_posityDistributionx.txt', '_posityDistributiony.txt', or '_posityDistributionz.txt'.
    
    Parameters:
        folders (list of str): paths to folders containing distribution files
        prefix (str): optional prefix filter for filenames
        suffix (str): file suffix (default='.txt')
    
    Returns:
        data (dict): {'x': [(locations, porosity, filename), ...],
                      'y': [(locations, porosity, filename), ...],
                      'z': [(locations, porosity, filename), ...]}
    """
    data = {"x": [], "y": [], "z": []}

    for folder in folders:
        for fname in os.listdir(folder):
            if not fname.endswith(suffix):
                continue
            if prefix and not fname.startswith(prefix):
                continue

            # Extract direction
            if "_posityDistributionx" in fname:
                direction = "x"
            elif "_posityDistributiony" in fname:
                direction = "y"
            elif "_posityDistributionz" in fname:
                direction = "z"
            else:
                continue  # skip unrelated files

            # Load data
            path = os.path.join(folder, fname)
            arr = np.loadtxt(path)

            if arr.ndim == 1:  # single line case
                locations, porosity = [arr[0]], [arr[1]]
            else:
                locations, porosity = arr[:,0], arr[:,1]

            data[direction].append((locations, porosity, fname))

    return data

def porosity3DMap(volumeLength,materialMTX,volumeMTX,saving3DPath,voxel_size=1):

    # max voxel length in x, y, and z
    voxelsLength = (materialMTX.shape[0],materialMTX.shape[1],materialMTX.shape[2])

    # Number of volumes in each direction
    dimX = int(voxelsLength[0]*voxel_size/volumeLength)
    dimY = int(voxelsLength[1]*voxel_size/volumeLength)
    dimZ = int(voxelsLength[2]*voxel_size/volumeLength)

    blockSize = int(volumeLength/voxel_size)

    xCorners = [i*blockSize for i in range(dimX)]
    yCorners = [i*blockSize for i in range(dimY)]
    zCorners = [i*blockSize for i in range(dimZ)]

    corners = list(itertools.product(xCorners,yCorners,zCorners))
    
    # Store results
    results = []

    for corner in corners:
        # Crop the volume of interest
        temp_materialMTX = materialMTX[corner[0]:corner[0]+blockSize,corner[1]:corner[1]+blockSize,corner[2]:corner[2]+blockSize]
        temp_volumeMTX = volumeMTX[corner[0]:corner[0]+blockSize,corner[1]:corner[1]+blockSize,corner[2]:corner[2]+blockSize]

        # if material in volume
        materialCount = np.sum(temp_materialMTX)
        volumeCount = np.sum(temp_volumeMTX)
        if volumeCount > 0:
            temp_porosity = (volumeCount-materialCount)/volumeCount
            results.append([corner[0], corner[1], corner[2], temp_porosity])
        
        # Convert to DataFrame
    df = pd.DataFrame(results, columns=["Xcorner", "Ycorner", "Zcorner", "Porosity"])

    # Save to txt
    os.makedirs(os.path.dirname(saving3DPath), exist_ok=True)
    df.to_csv(saving3DPath, sep="\t", index=False)

    print(f"Saved porosity map to {saving3DPath}")
    return df
        


# TiffPath = r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44323-23_2nd\Segmentation\9_12_25_PICA-RTV_44323-23_2nd_3.32934.transformed.filtered.Cropped.labels.masked.tif'
# VolumePath = r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44323-23_2nd\Segmentation\9_12_25_PICA-RTV_44323-23_2nd_3.32934.transformed.filtered.Cropped.filtered.dilute.eroded55.tif'

TiffPaths = [
    # r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44325-28\Segmentation\9_12_25_FF-RTV_44325-28.filtered.labels.Cropped.tif',
    r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44323-23_2nd\Segmentation\9_12_25_PICA-RTV_44323-23_2nd_3.32934.transformed.filtered.Cropped.filtered.tif'
]

VolumePaths = [
    # r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44325-28\Segmentation\9_12_25_FF-RTV_44325-28.filtered.labels.Cropped.or_totalVolumeMask_(2).tif',
    r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44323-23_2nd\Segmentation\9_12_25_PICA-RTV_44323-23_2nd_3.32934.transformed.filtered.Cropped.filtered.or_totalVolumeMask(2).tif'
]

OpenPorePaths =[
    # r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44325-28\Segmentation\9_12_25_FF-RTV_44325-28.filtered.labels.Cropped.OpenPores.masked.tif',
    r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44323-23_2nd\Segmentation\9_12_25_PICA-RTV_44323-23_2nd_3.32934.transformed.filtered.Cropped.OpenPores.masked.tif'
]

labels = [
    # 'N2_2',
    'CO2_1'
]
volumeLength = 400

for i in range(len(TiffPaths)):
    materialMTX = loadData(TiffPaths[i])
    volumeMTX = loadData(VolumePaths[i])
    openPoreMTX = None # loadData(OpenPorePaths[i])
    for direction in ['x', 'y', 'z']:
        # locationList,PorosityList,openPorosityList = get1DPorosity(materialMTX,volumeMTX,openPoreMTX,direction,bins=0,voxel_size=3.3293)
        locationList,PorosityList, = get1DPorosity(materialMTX,volumeMTX,openPoreMTX,direction,bins=0,voxel_size=3.3293)

        saveFigurePath = TiffPaths[i][:-4]+r'_posityDistribution%s'%direction

        # save_porosity_data(locationList, PorosityList, openPorosityList, saveFigurePath+'.txt')
        save_porosity_data(locationList, PorosityList, saveFigurePath+'.txt')

        # locationList,PorosityList,openPorosityList = load_porosity_data(saveFigurePath+'.txt')

        # plot_porosity_scatter(locationList, PorosityList, openPorosityList, saveFigurePath+'.png',labels=labels)
        plot_porosity_scatter(locationList, PorosityList, saveFigurePath+'.png',labels=labels[i])

    # saving3DPath = TiffPaths[i][:-4]+r'_%s_3DMap.txt'%volumeLength
    # porosity3DMap(volumeLength,materialMTX,volumeMTX,saving3DPath,voxel_size=3.3293)

folders = [
    r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44325-28\Segmentation',
    r'F:\Luis\PICA-RTV\9_12_25_PICA-RTV_44323-23_2nd\Segmentation',
]

labels = [
    r'N$_2$-2',
    r'CO$_2$-1'
]

savePlotPath = r'F:\Luis\PICA-RTV\Paper'
# Load data from all folders
data = load_porosity_distributions(folders)

# Directions to loop over
directions = ['x', 'y', 'z']

for direction in directions:
    locs = [d[0] for d in data[direction]]
    poros = [d[1] for d in data[direction]]

    save_path = savePlotPath+f"/{direction}_porosity.png"
    title = f"{direction.upper()}-direction Porosity"

    plot_porosity_scatter(locs, poros, save_path,
                          xlabel="Distance (µm)", ylabel="Porosity",
                          title=title, labels=labels)