import numpy as np
import imageio
from skimage import measure
import trimesh

class Workspace:
    def __init__(self, matrix=None, voxel_size=1e-6, name="Workspace", origin=(0,0,0)):
        """
        Workspace class holding the domain as a numpy matrix.
        
        :param matrix: 3D numpy array of the volume.
        :param voxel_size: physical size of a single voxel.
        :param name: Identifier for the workspace (useful for saving STL/properties).
        :param origin: (x, y, z) tuple indicating where this volume originated 
                       from in a larger primary volume.
        """
        if matrix is None:
            self.matrix = np.zeros((1, 1, 1), dtype=np.uint16)
        else:
            self.matrix = matrix
            
        # If the user provides a single number, expand it to [x, y, z]
        if isinstance(voxel_size, (int, float)):
            self.voxel_size = np.array([voxel_size, voxel_size, voxel_size], dtype=float)
        # Otherwise, ensure it's a 3-element array
        else:
            self.voxel_size = np.array(voxel_size, dtype=float)
            if self.voxel_size.shape != (3,):
                raise ValueError("voxel_size must be a single number or a list/tuple of 3 numbers (x, y, z).")
            
        self.name = name
        self.origin = origin
        
        # Placeholders for generated geometrical data
        self.vertices = None
        self.faces = None
        self.properties = {}

    @classmethod
    def from_file(cls, filepath, voxel_size=1e-6):
        """
        Generates a Workspace by loading a TIFF or DAT file. 
        (This replaces your loadData function)
        """
        if filepath.endswith(('.tif', '.tiff')):
            image_volume = imageio.volread(filepath)
            image_volume = np.transpose(image_volume, (2, 1, 0))
        elif filepath.endswith(('.txt', '.dat')):
            tempdata = np.loadtxt(filepath, skiprows=2)
            xmax, ymax, zmax = int(max(tempdata[:, 0])), int(max(tempdata[:, 1])), int(max(tempdata[:, 2]))
            image_volume = np.zeros((xmax, ymax, zmax), dtype='int')
            for val in tempdata:
                image_volume[int(val[0]) - 1, int(val[1]) - 1, int(val[2]) - 1] = int(val[3])
        else:
            raise ValueError("Unsupported file format.")
            
        name = filepath.split('/')[-1].split('\\')[-1]
        return cls(matrix=image_volume, voxel_size=voxel_size, name=name)

    def extract_subvolume(self, corner, dimensions, sub_id=0):
        """
        Crops the matrix and returns a NEW Workspace object for the subvolume.
        This preserves the OOP architecture so you can call properties directly on the subvolume.
        """
        x, y, z = corner
        dx, dy, dz = dimensions
        
        # Handle "Full" volume extraction logic
        if dimensions == 'Full':
            sub_matrix = self.matrix.copy()
            new_name = f"{self.name[:-4]}_Full"
        else:
            sub_matrix = self.matrix[x:x+dx, y:y+dy, z:z+dz].copy()
            new_name = f"{self.name[:-4]}_V{sub_id}_{x}-{y}-{z}-{dx}"
            
        # Return a new instance of Workspace containing just the subvolume
        return Workspace(
            matrix=sub_matrix, 
            voxel_size=self.voxel_size, 
            name=new_name, 
            origin=(x, y, z)
        )

    def pad(self, padding_size=1):
        """
        Pads the workspace matrix. (Replaces your createPadding function)
        """
        padded_volume = np.zeros(
            (self.matrix.shape[0] + 2 * padding_size,
             self.matrix.shape[1] + 2 * padding_size,
             self.matrix.shape[2] + 2 * padding_size),
            dtype=self.matrix.dtype,
        )
        
        x_range = slice(padding_size, padding_size + self.matrix.shape[0])
        y_range = slice(padding_size, padding_size + self.matrix.shape[1])
        z_range = slice(padding_size, padding_size + self.matrix.shape[2])
        
        padded_volume[x_range, y_range, z_range] = self.matrix
        self.matrix = np.squeeze(np.array(padded_volume))

    def generate_mesh(self):
        """
        Creates a mesh using the marching cubes algorithm and stores it in the object.
        (Replaces your getMesh function)
        """
        # Ensure it's a binary matrix (0.0 to 1.0) before meshing
        binary_matrix = self.matrix / np.max(self.matrix) if np.max(self.matrix) > 0 else self.matrix
        
        self.verts, self.faces, _, _ = measure.marching_cubes(binary_matrix, allow_degenerate=False, method='lewiner', spacing=self.voxel_size)
        
        # Flip normals by reversing face winding
        self.faces = self.faces[:, ::-1]

        print(f'Generated mesh with {len(self.faces)} faces!')
        
    def get_trimesh(self):
        """Helper to quickly return a trimesh object for smoothing/export."""
        # if self.vertices is None or self.faces is None:
        #     self.generate_mesh()
        return trimesh.Trimesh(vertices=self.vertices, faces=self.faces)