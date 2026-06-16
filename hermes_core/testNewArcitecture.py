# main.py
import numpy as np
from hermes_core import Workspace

# 1. Create dummy data
dummy_matrix = np.ones((50, 50, 50), dtype=np.uint16)

# 2. Instantiate your Workspace
ws = Workspace(matrix=dummy_matrix, voxel_size=1.0, name="TestBlock")

# 3. Process it
ws.pad()
ws.generate_mesh()
mesh = ws.get_trimesh()

print(f"Successfully created a mesh for {ws.name}!")
print(f"Surface Area: {mesh.area}")

properties = ws.compute_all_properties(fiber_sphere=10, pore_sphere=30, plane='XY')

print(f"Porosity: {properties['porosity']:.4f}")
print(f"Mean Fiber Diameter: {properties['fiber_diameter_mean']:.2f} um")
print(f"Mean Azimuth Angle: {properties.get('azimuth_mean', 0.0):.2f}°")