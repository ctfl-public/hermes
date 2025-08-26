import numpy as np
import tifffile
from PIL import Image
from PIL.TiffTags import TAGS
import os
from datetime import datetime

def analyze_tiff_file(filepath, voxel_resolution=None):
    """
    Analyze a TIFF file to determine if it's binarized and extract metadata.
    
    Parameters:
    filepath (str): Path to the TIFF file
    voxel_resolution (tuple): Voxel resolution as (x, y, z) in units like µm, nm, etc.
    """
    
    print("="*60)
    print(f"TIFF FILE ANALYSIS: {os.path.basename(filepath)}")
    print("="*60)
    
    # Check if file exists
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return
    
    # File size
    file_size = os.path.getsize(filepath) / (1024 * 1024)  # Convert to MB
    print(f"\nFile size: {file_size:.2f} MB")
    
    # Read the file using tifffile
    try:
        with tifffile.TiffFile(filepath) as tif:
            # Get first page for analysis
            page = tif.pages[0]
            
            # Read the image data
            img_array = tif.asarray()
            
            print("\n--- BASIC PROPERTIES ---")
            print(f"Data type: {img_array.dtype}")
            print(f"Shape: {img_array.shape}")
            print(f"Number of pages/slices: {len(tif.pages)}")
            
            # Determine dimensionality
            if len(img_array.shape) == 2:
                print(f"Image type: 2D grayscale")
                print(f"Dimensions: {img_array.shape[0]} x {img_array.shape[1]} pixels")
            elif len(img_array.shape) == 3:
                if len(tif.pages) > 1:
                    print(f"Image type: 3D stack")
                    print(f"Dimensions: {img_array.shape[1]} x {img_array.shape[2]} x {img_array.shape[0]} voxels")
                else:
                    print(f"Image type: 2D color (RGB/multi-channel)")
                    print(f"Dimensions: {img_array.shape[0]} x {img_array.shape[1]} pixels, {img_array.shape[2]} channels")
            
            # Memory usage
            memory_usage = img_array.nbytes / (1024 * 1024)  # Convert to MB
            print(f"Memory usage (uncompressed): {memory_usage:.2f} MB")
            
            # Voxel resolution
            if voxel_resolution:
                print(f"\n--- VOXEL RESOLUTION ---")
                if len(voxel_resolution) == 2:
                    print(f"X resolution: {voxel_resolution[0]} units/pixel")
                    print(f"Y resolution: {voxel_resolution[1]} units/pixel")
                elif len(voxel_resolution) == 3:
                    print(f"X resolution: {voxel_resolution[0]} units/voxel")
                    print(f"Y resolution: {voxel_resolution[1]} units/voxel")
                    print(f"Z resolution: {voxel_resolution[2]} units/voxel")
                
                # Calculate physical dimensions
                if len(img_array.shape) >= 2:
                    phys_x = img_array.shape[-1] * voxel_resolution[0]
                    phys_y = img_array.shape[-2] * voxel_resolution[1]
                    print(f"Physical dimensions: {phys_x:.2f} x {phys_y:.2f} units")
                    if len(voxel_resolution) == 3 and len(img_array.shape) == 3 and len(tif.pages) > 1:
                        phys_z = img_array.shape[0] * voxel_resolution[2]
                        print(f"Physical Z dimension: {phys_z:.2f} units")
            
            # Check if binarized
            print(f"\n--- BINARIZATION CHECK ---")
            unique_values = np.unique(img_array)
            print(f"Number of unique values: {len(unique_values)}")
            print(f"Unique values: {unique_values[:10]}{'...' if len(unique_values) > 10 else ''}")
            
            is_binary = len(unique_values) <= 2
            print(f"Is binarized: {'YES' if is_binary else 'NO'}")
            
            if is_binary and len(unique_values) == 2:
                print(f"Binary values: {unique_values[0]} (background), {unique_values[1]} (foreground)")
                # Calculate percentage of each value
                bg_percent = (img_array == unique_values[0]).sum() / img_array.size * 100
                fg_percent = (img_array == unique_values[1]).sum() / img_array.size * 100
                print(f"Background pixels: {bg_percent:.1f}%")
                print(f"Foreground pixels: {fg_percent:.1f}%")
            
            # Value statistics
            print(f"\n--- VALUE STATISTICS ---")
            print(f"Min value: {img_array.min()}")
            print(f"Max value: {img_array.max()}")
            print(f"Mean value: {img_array.mean():.2f}")
            print(f"Std deviation: {img_array.std():.2f}")
            
            # Technical metadata
            print(f"\n--- TECHNICAL METADATA ---")
            print(f"Bits per sample: {page.bitspersample}")
            print(f"Sample format: {page.sampleformat}")
            print(f"Compression: {page.compression}")
            print(f"Photometric interpretation: {page.photometric}")
            print(f"Planar configuration: {page.planarconfig}")
            
            # Additional tags
            print(f"\n--- ADDITIONAL TAGS ---")
            important_tags = ['Software', 'DateTime', 'ImageDescription', 'Make', 'Model']
            for tag in page.tags.values():
                if tag.name in important_tags and tag.value:
                    print(f"{tag.name}: {tag.value}")
            
            # Check for special metadata
            if hasattr(tif, 'imagej_metadata') and tif.imagej_metadata:
                print(f"\nImageJ metadata detected")
            if hasattr(tif, 'ome_metadata') and tif.ome_metadata:
                print(f"OME-TIFF metadata detected")
                
    except Exception as e:
        print(f"Error reading TIFF file: {e}")
        return
    
    print("\n" + "="*60)

# Example usage
if __name__ == "__main__":
    # Replace with your file path
    tiff_file = "CC0_7.73504_6273.tif"
    
    # Specify your voxel resolution (x, y, z) or (x, y) for 2D
    # Example: (0.65, 0.65, 2.0) for 0.65 µm x 0.65 µm x 2.0 µm voxels
    voxel_res = (7.73504, 7.73504, 7.73504)  # Adjust these values to your actual resolution
    
    # Run the analysis
    analyze_tiff_file(tiff_file, voxel_resolution=voxel_res)