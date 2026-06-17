# main.py
import numpy as np
from hermes_core import Workspace

# 1. Create dummy data
dummy_matrix = np.ones((50, 50, 50), dtype=np.uint16)

# 2. Instantiate your Workspace
ws = Workspace.from_file(r'/beegfs/users/lchacon/Projects/HERMES/Git/hermes/grid_physical_15Elevation_1.0.tif', voxel_size=1.0)

# 2. Segment the raw data dynamically using Otsu filter thresholding
ws.segment(method="Otsu")

# 3. Process it
ws.pad()
ws.generate_mesh()
mesh = ws.get_trimesh()

print(f"Successfully created a mesh for {ws.name}!")
print(f"Surface Area: {mesh.area}")

properties = ws.compute_all_properties(fiber_sphere=10, pore_sphere=10, plane='XY')

print(f"Porosity: {properties['porosity']:.4f}")
print(f"Mean Fiber Diameter: {properties['fiber_diameter_mean']:.2f} um")
print(f"Mean Pore Diameter: {properties['pore_size_mean']:.2f} um")
print(f"Mean Elevation Angle: {properties['elevation_mean']:.2f}°")
print(f"Mean Azimuth Angle: {properties['azimuth_mean']:.2f}°")

ws.save_voxel_data('outputs/voxelFiles/chenFormat.txt')
ws.save_properties('outputs/propertiesFiles/results.txt')

ws.export_stl('outputs/stlFiles/output.stl')
mesh = ws.apply_smoothing({'laplacian':1})
ws.export_stl('outputs/stlFiles/output_smooth.stl')


# ws.visualize_matrix_cutoff_plt(vmin=1, vmax=1)