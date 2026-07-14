import numpy as np
from hermes_core import Workspace

def create_synthetic_sphere(size=50):
    """Creates a 3D matrix with a solid sphere in the center surrounded by noise."""
    print("Generating synthetic 3D data...")
    x, y, z = np.ogrid[-size//2:size//2, -size//2:size//2, -size//2:size//2]
    mask = x**2 + y**2 + z**2 <= (size//3)**2
    
    # Create a base matrix: 50 background, 200 foreground (sphere)
    matrix = np.full((size, size, size), 50, dtype=np.uint16)
    matrix[mask] = 200
    
    # Add some random noise to test segmentation robustness
    noise = np.random.randint(-20, 20, (size, size, size), dtype=np.int16)
    matrix = np.clip(matrix + noise, 0, 255).astype(np.uint16)
    return matrix

def create_synthetic_ring(size=60, major_radius=15, minor_radius=6):
    """Creates a 3D matrix with a solid ring (torus) in the center surrounded by noise."""
    print("Generating synthetic 3D ring data...")
    
    # Create a 3D coordinate grid centered at (0,0,0)
    x, y, z = np.ogrid[-size//2:size//2, -size//2:size//2, -size//2:size//2]
    
    # Torus equation: (sqrt(x^2 + y^2) - R)^2 + z^2 <= r^2
    # R = major_radius (distance from center to middle of the tube)
    # r = minor_radius (radius of the tube itself)
    distance_from_z_axis = np.sqrt(x**2 + y**2)
    mask = (distance_from_z_axis - major_radius)**2 + z**2 <= minor_radius**2
    
    # Create a base matrix: 50 background, 200 foreground (ring)
    matrix = np.full((size, size, size), 50, dtype=np.uint16)
    matrix[mask] = 200
    
    # Add some random noise to test segmentation robustness
    noise = np.random.randint(-20, 20, (size, size, size), dtype=np.int16)
    matrix = np.clip(matrix + noise, 0, 255).astype(np.uint16)
    
    return matrix

def create_synthetic_fibers(size=60, num_fibers=15, fiber_radius=5):
    """Creates a 3D matrix with randomly oriented intersecting fibers surrounded by noise."""
    print(f"Generating synthetic 3D fiber data ({num_fibers} fibers)...")
    
    # Create a base matrix: 50 background
    matrix = np.full((size, size, size), 50, dtype=np.uint16)
    
    # Create a coordinate grid for the entire volume
    # Shape of coords: (size, size, size, 3)
    I, J, K = np.indices((size, size, size))
    coords = np.stack((I, J, K), axis=-1)
    
    for _ in range(num_fibers):
        # Pick a random point in the volume for the fiber to pass through
        p0 = np.random.rand(3) * size
        
        # Generate a random 3D direction vector for the fiber
        direction = np.random.randn(3)
        direction /= np.linalg.norm(direction)
        
        # Calculate perpendicular distance from all voxels to the 3D line
        # Distance = ||(Point - LineOrigin) x LineDirection||
        diff = coords - p0
        cross_prod = np.cross(diff, direction)
        dist = np.linalg.norm(cross_prod, axis=-1)
        
        # Mask voxels that fall within the fiber radius
        mask = dist <= fiber_radius
        matrix[mask] = 200
        
    # Add some random noise to test segmentation robustness
    noise = np.random.randint(-20, 20, (size, size, size), dtype=np.int16)
    matrix = np.clip(matrix + noise, 0, 255).astype(np.uint16)
    
    return matrix

from scipy.ndimage import distance_transform_edt

def create_synthetic_bending_fibers(size=60, num_fibers=10, fiber_radius=5):
    """Creates a 3D matrix with curved, bending fibers using Bezier curves and EDT."""
    print(f"Generating synthetic 3D bending fiber data ({num_fibers} fibers)...")
    
    # Initialize a boolean array where True = background, False = fiber skeleton
    # (EDT calculates the distance to the nearest False value)
    skeleton_volume = np.ones((size, size, size), dtype=bool)
    
    for _ in range(num_fibers):
        # 1. Generate 4 random 3D control points for the Bezier curve
        # Scaling by size*1.5 and shifting slightly allows fibers to start/end outside the box
        p0 = (np.random.rand(3) * size * 1.5) - (size * 0.25)
        p1 = (np.random.rand(3) * size * 1.5) - (size * 0.25)
        p2 = (np.random.rand(3) * size * 1.5) - (size * 0.25)
        p3 = (np.random.rand(3) * size * 1.5) - (size * 0.25)
        
        # 2. Evaluate the curve at N points (ensuring continuous voxel lines)
        t = np.linspace(0, 1, num=size * 4)[:, np.newaxis]
        
        # 3. Apply the cubic Bezier equation
        curve = ((1-t)**3)*p0 + 3*((1-t)**2)*t*p1 + 3*(1-t)*(t**2)*p2 + (t**3)*p3
        
        # 4. Convert spatial curve coordinates to integer voxel indices
        coords = np.round(curve).astype(int)
        
        # 5. Filter out coordinates that fall outside our bounding box
        valid = (coords[:, 0] >= 0) & (coords[:, 0] < size) & \
                (coords[:, 1] >= 0) & (coords[:, 1] < size) & \
                (coords[:, 2] >= 0) & (coords[:, 2] < size)
        coords = coords[valid]
        
        # 6. Burn the valid skeleton points into the volume
        if len(coords) > 0:
            skeleton_volume[coords[:, 0], coords[:, 1], coords[:, 2]] = False
            
    # 7. Calculate distance from every voxel to the nearest skeleton voxel
    distance_map = distance_transform_edt(skeleton_volume)
    
    # 8. Create the greyscale matrix
    matrix = np.full((size, size, size), 50, dtype=np.uint16)
    
    # 9. Thicken the skeletons into solid fibers
    mask = distance_map <= fiber_radius
    matrix[mask] = 200
    
    # 10. Add random noise for realism
    noise = np.random.randint(-20, 20, (size, size, size), dtype=np.int16)
    matrix = np.clip(matrix + noise, 0, 255).astype(np.uint16)
    
    return matrix

def main():
    # ==========================================================
    # 1. INITIALIZATION & DATA LOADING
    # ==========================================================
    # print("\n--- Testing Initialization ---")
    # dummy_data = create_synthetic_bending_fibers(size=50, num_fibers=1)
    
    # Initialize workspace with the dummy data
    # ws = Workspace(matrix=dummy_data, voxel_size=1, name="exampleMatrix")
    ws = Workspace.from_file(r'/beegfs/users/lchacon/Projects/HERMES/Git/hermes/grid_physical_15Elevation_1.0.tif', voxel_size=1)
    print(f"Created Workspace: {ws.name} | Shape: {ws.matrix.shape} | Voxel Size: {ws.voxel_size}")

    # ==========================================================
    # 2. SAMPLING MODULE
    # ==========================================================
    # print("\n--- Testing Sampling ---")
    # # Extract a specific subvolume (e.g., zooming in on the sphere)
    # sub_ws = ws.extract_subvolume(corner=(10, 10, 10), dimensions=(40, 40, 40))
    # print(f"Extracted Subvolume: {sub_ws.name} | Shape: {sub_ws.matrix.shape}")

    # ==========================================================
    # 3. SEGMENTATION
    # ==========================================================
    print("\n--- Testing Segmentation ---")
    # Use Otsu's method to binarize our noisy synthetic data
    ws.segment(method="Otsu", invert=False)
    print(f"Segmentation complete. Unique values in matrix: {np.unique(ws.matrix)}")

    # ==========================================================
    # 4. MESHING & SMOOTHING
    # ==========================================================
    print("\n--- Testing Meshing & Smoothing ---")
    # Pad the matrix to ensure closed meshes on the boundaries
    ws.pad()
    
    # Generate the initial mesh
    ws.generate_mesh()
    print(f"Initial Mesh Generated: {len(ws.vertices)} vertices, {len(ws.faces)} faces.")
    
    # Check if mesh is a valid volume
    is_vol = ws.check_mesh()
    print(f"Is mesh a closed volume? {is_vol}")

    # Apply Laplacian smoothing
    smoothed_mesh = ws.apply_smoothing({'laplacian': 5})
    print(f"Applied Smoothing. Workspace name updated to: {ws.name}")

    # ==========================================================
    # 5. PROPERTIES QUANTIFICATION
    # ==========================================================
    print("\n--- Testing Property Quantification ---")
    # Run the full analytics suite
    props = ws.compute_all_properties(fiber_sphere=10, pore_sphere=30, plane='XY', step_size=7)
    
    print("Computed Properties:")
    for key, value in props.items():
        # Truncate long lists for cleaner console output
        if isinstance(value, list) and len(value) > 3:
            print(f"  * {key}: {value[:3]} ... (truncated)")
        else:
            print(f"  * {key}: {value}")
    
    # print(f"Direction Map: {ws.direction_map}")

    # ==========================================================
    # 6. EXPORT / OUTPUT MODULES
    # ==========================================================
    print("\n--- Testing Data Export ---")
    
    # 6a. Export STL
    stl_path = "./outputs/stlFiles/test_mesh.stl"
    ws.export_stl(stl_path)
    print(f"Exported STL to: {stl_path}")
    
    # 6b. Export VTU (for ParaView)
    vtu_path = "./outputs/vtuFiles/test_volume.vtu"
    ws.export_vtu(vtu_path, scalars_name="Material")
    
    # 6c. Save Properties
    prop_path = "./outputs/propertiesFiles/test_properties.txt"
    ws.save_properties(prop_path, append=False)
    print(f"Exported Properties to: {prop_path}")

    # ==========================================================
    # 7. VISUALIZATION
    # ==========================================================
    print("\n--- Testing Visualization ---")
    print("Launching Matplotlib Visualization. Close the window to end the script.")
    
    # Visualizing only the solid material (value = 1 after segmentation)
    ws.visualize_matrix_cutoff_plt(vmin=1, vmax=1, downsample_factor=1)
    
    # Note: If you want to test the PyVista interactive renderer instead, 
    # comment out the line above and uncomment the line below:
    # ws.visualize_matrix_cutoff(vmin=1, vmax=1)

if __name__ == "__main__":
    main()