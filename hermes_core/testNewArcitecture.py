import numpy as np
from hermes_core import Workspace

def create_synthetic_data(size=50):
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

def main():
    # ==========================================================
    # 1. INITIALIZATION & DATA LOADING
    # ==========================================================
    print("\n--- Testing Initialization ---")
    dummy_data = create_synthetic_data(size=60)
    
    # Initialize workspace with the dummy data
    ws = Workspace(matrix=dummy_data, voxel_size=1, name="Test_Sphere")
    print(f"Created Workspace: {ws.name} | Shape: {ws.matrix.shape} | Voxel Size: {ws.voxel_size}")

    # ==========================================================
    # 2. SAMPLING MODULE
    # ==========================================================
    print("\n--- Testing Sampling ---")
    # Extract a specific subvolume (e.g., zooming in on the sphere)
    sub_ws = ws.extract_subvolume(corner=(10, 10, 10), dimensions=(40, 40, 40))
    print(f"Extracted Subvolume: {sub_ws.name} | Shape: {sub_ws.matrix.shape}")

    # ==========================================================
    # 3. SEGMENTATION
    # ==========================================================
    print("\n--- Testing Segmentation ---")
    # Use Otsu's method to binarize our noisy synthetic data
    sub_ws.segment(method="Otsu", invert=False)
    print(f"Segmentation complete. Unique values in matrix: {np.unique(sub_ws.matrix)}")

    # ==========================================================
    # 4. MESHING & SMOOTHING
    # ==========================================================
    print("\n--- Testing Meshing & Smoothing ---")
    # Pad the matrix to ensure closed meshes on the boundaries
    sub_ws.pad()
    
    # Generate the initial mesh
    sub_ws.generate_mesh()
    print(f"Initial Mesh Generated: {len(sub_ws.vertices)} vertices, {len(sub_ws.faces)} faces.")
    
    # Check if mesh is a valid volume
    is_vol = sub_ws.check_mesh()
    print(f"Is mesh a closed volume? {is_vol}")

    # Apply Laplacian smoothing
    smoothed_mesh = sub_ws.apply_smoothing({'laplacian': 5})
    print(f"Applied Smoothing. Workspace name updated to: {sub_ws.name}")

    # ==========================================================
    # 5. PROPERTIES QUANTIFICATION
    # ==========================================================
    print("\n--- Testing Property Quantification ---")
    # Run the full analytics suite
    # (Using smaller sphere sizes since our matrix is only 44x44x44 after padding)
    props = sub_ws.compute_all_properties(fiber_sphere=5, pore_sphere=5, plane='XY')
    
    print("Computed Properties:")
    for key, value in props.items():
        # Truncate long lists for cleaner console output
        if isinstance(value, list) and len(value) > 3:
            print(f"  * {key}: {value[:3]} ... (truncated)")
        else:
            print(f"  * {key}: {value}")

    # ==========================================================
    # 6. EXPORT / OUTPUT MODULES
    # ==========================================================
    print("\n--- Testing Data Export ---")
    
    # 6a. Export STL
    stl_path = "./output/test_mesh.stl"
    sub_ws.export_stl(stl_path)
    print(f"Exported STL to: {stl_path}")
    
    # 6b. Export VTU (for ParaView)
    vtu_path = "./output/test_volume.vtu"
    sub_ws.export_vtu(vtu_path, scalars_name="Material", filter_background=True)
    
    # 6c. Save Properties
    prop_path = "./output/test_properties.txt"
    sub_ws.save_properties(prop_path, append=False)
    print(f"Exported Properties to: {prop_path}")

    # ==========================================================
    # 7. VISUALIZATION
    # ==========================================================
    print("\n--- Testing Visualization ---")
    print("Launching Matplotlib Visualization. Close the window to end the script.")
    
    # Visualizing only the solid material (value = 1 after segmentation)
    sub_ws.visualize_matrix_cutoff_plt(vmin=1, vmax=1, downsample_factor=1)
    
    # Note: If you want to test the PyVista interactive renderer instead, 
    # comment out the line above and uncomment the line below:
    # sub_ws.visualize_matrix_cutoff(vmin=1, vmax=1)

if __name__ == "__main__":
    main()