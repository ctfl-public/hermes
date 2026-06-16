# main.py
import numpy as np
from hermes_core import Workspace # Imports your new clean data structure!

# 1. Create dummy data
dummy_matrix = np.ones((50, 50, 50), dtype=np.uint16)

# 2. Instantiate your Workspace
ws = Workspace(matrix=dummy_matrix, voxel_size=1.0, name="TestBlock")

# 3. Process it
ws.pad()
ws.generate_mesh()
mesh = ws.get_trimesh()

print(f"Successfully created a mesh for {ws.name}!")
print(f"Surface Area: {mesh.area:.2f}")