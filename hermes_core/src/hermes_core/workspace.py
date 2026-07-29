# workspace.py
import numpy as np
import imageio
from skimage import measure, filters, morphology
from skimage.filters import (threshold_otsu, threshold_local, threshold_li, 
                             threshold_yen, threshold_isodata, threshold_triangle)
import trimesh
import networkx as nx
from scipy.ndimage import distance_transform_edt
from skimage.feature import peak_local_max
from scipy.spatial import cKDTree
import pyvista as pv
from pathlib import Path
import re

class Workspace:
    def __init__(self, matrix=None, voxel_size=1e-6, name="Workspace", origin=(0,0,0), direction_map=None):
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
        self.padding_size = 0
        
        # Placeholders for generated geometrical data
        self.vertices = None
        self.faces = None
        self.direction_map = direction_map
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

    @classmethod
    def from_vtu(cls, filepath, voxel_size=None, scalars_name="Material"):
        """
        Generates a Workspace by loading a .vtu (Unstructured Grid) file.
        Reconstructs the 3D numpy array by mapping unstructured hexahedral cell centers.
        
        :param filepath: Path to the .vtu file.
        :param voxel_size: Optional. If None, auto-detects from the first cell's bounds.
        :param scalars_name: The name of the cell data array to load as matrix values.
        """
        mesh = pv.read(filepath)
        
        # 1. Check for valid scalar data in the VTU
        if scalars_name not in mesh.cell_data:
            if mesh.active_scalars_name and len(mesh.cell_data[mesh.active_scalars_name]) > 0:
                print(f"'{scalars_name}' not found. Defaulting to active scalars: '{mesh.active_scalars_name}'")
                scalars_name = mesh.active_scalars_name
            else:
                raise ValueError(f"Could not find valid cell data array '{scalars_name}' in the VTU.")
                
        scalars = mesh.cell_data[scalars_name]
        
        # 2. Auto-detect voxel size if not explicitly provided
        if voxel_size is None:
            # Extract the first cell and measure its physical bounding box
            cb = mesh.get_cell(0).bounds
            voxel_size = np.array([cb[1]-cb[0], cb[3]-cb[2], cb[5]-cb[4]], dtype=float)
            print(f"Auto-detected voxel size from VTU: {voxel_size}")
        elif isinstance(voxel_size, (int, float)):
            voxel_size = np.array([voxel_size, voxel_size, voxel_size], dtype=float)
        else:
            voxel_size = np.array(voxel_size, dtype=float)
            
        # 3. Extract cell centers to map unstructured data back to a structured 3D grid
        centers = mesh.cell_centers().points
        min_coords = centers.min(axis=0)
        max_coords = centers.max(axis=0)
        
        # 4. Determine the bounding box grid shape based on physical distance and voxel size
        # Add 1 because indices are 0-based
        shape = np.round((max_coords - min_coords) / voxel_size).astype(int) + 1
        
        # Initialize an empty background matrix (0 for void/background)
        matrix = np.zeros(shape, dtype=np.uint16)
        
        # 5. Convert physical center coordinates to 3D matrix indices
        indices = np.round((centers - min_coords) / voxel_size).astype(int)
        
        # 6. Populate the matrix with the scalar values from the VTU
        matrix[indices[:, 0], indices[:, 1], indices[:, 2]] = scalars.astype(np.uint16)
        
        # 7. Extract the orientation map if it exists
        direction_map = None
        if "Orientation" in mesh.cell_data:
            vec_data = mesh.cell_data["Orientation"]
            
            # Create a 4D array formatted as [X, Y, Z, 3]
            vector_shape = tuple(shape) + (vec_data.shape[1],)
            direction_map = np.zeros(vector_shape, dtype=vec_data.dtype)
            
            # Map the N x 3 vectors back into the 3D grid layout
            direction_map[indices[:, 0], indices[:, 1], indices[:, 2], :] = vec_data
            print("Successfully loaded 'Orientation' map from VTU.")

        # Clean up the name for the workspace
        name = filepath.split('/')[-1].split('\\')[-1]
        
        return cls(matrix=matrix, voxel_size=voxel_size, name=name, direction_map=direction_map)

    @classmethod
    def from_image_sequence(cls, dir_path, pattern="*.tif", voxel_size=1e-6, name=None):
        """
        Generates a Workspace by loading a sequence of 2D TIFF files from a directory.
        Assumes files are organized sequentially (e.g., nameOfFile_0001.tif).
        
        :param dir_path: Path to the directory containing the images.
        :param pattern: File matching pattern (default is '*.tif').
        :param voxel_size: Physical size of a single voxel.
        :param name: Optional. If None, uses the directory name.
        """
        
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"The path {dir_path} is not a valid directory.")
            
        # 1. Gather all matching files
        # Also handles .tiff extensions safely if the pattern is just *.tif
        files = list(dir_path.glob(pattern))
        if not files:
            # Fallback check just in case they used .tiff instead of .tif
            files = list(dir_path.glob("*.tiff"))
            if not files:
                raise FileNotFoundError(f"No files matching '{pattern}' found in {dir_path}")

        # 2. Sort files naturally based on trailing numerical values
        # This ensures name_2.tif comes BEFORE name_10.tif
        def extract_number(filepath):
            match = re.search(r'_(\d+)\.tiff?$', filepath.name, re.IGNORECASE)
            return int(match.group(1)) if match else filepath.name

        try:
            files.sort(key=extract_number)
        except TypeError:
            # Fallback to standard alphabetical sort if the regex fails to find numbers
            files.sort()

        print(f"Loading {len(files)} images from {dir_path}...")

        # 3. Read images into a list
        images = [imageio.imread(f) for f in files]
        
        # 4. Stack 2D arrays into a 3D volume
        # axis=-1 stacks them along the Z-axis (resulting in X, Y, Z shape)
        # Assuming the 2D images are read as (X, Y)
        image_volume = np.stack(images, axis=-1)
        
        # 5. Clean up name
        if name is None:
            name = dir_path.name
            
        return cls(matrix=image_volume, voxel_size=voxel_size, name=name)
    
    # =========================================================================
    # Sampling module
    # =========================================================================
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

    def sample_subvolumes(self, mode='deterministic', num_samples=10, sub_dims=(50, 50, 50)):
        """
        Samples subvolumes from the current matrix.
        
        :param mode: 'deterministic' (grid) or 'stochastic' (random).
        :param num_samples: Number of volumes for stochastic mode. 
                           For deterministic, this is ignored (uses grid calculation).
        :param sub_dims: Tuple of (dx, dy, dz) dimensions for the subvolumes.
        :return: List of Workspace objects.
        """
        subvolumes = []
        dx, dy, dz = sub_dims
        Mx, My, Mz = self.matrix.shape

        if mode == 'deterministic':
            # Create a Cartesian grid of samples
            for x in range(0, Mx - dx + 1, dx):
                for y in range(0, My - dy + 1, dy):
                    for z in range(0, Mz - dz + 1, dz):
                        subvolumes.append(self.extract_subvolume((x, y, z), (dx, dy, dz), sub_id=len(subvolumes)))
            print(f"Deterministic sampling created {len(subvolumes)} subvolumes.")

        elif mode == 'stochastic':
            # Randomly sample N times
            for i in range(num_samples):
                x = np.random.randint(0, Mx - dx)
                y = np.random.randint(0, My - dy)
                z = np.random.randint(0, Mz - dz)
                subvolumes.append(self.extract_subvolume((x, y, z), (dx, dy, dz), sub_id=i))
            print(f"Stochastic sampling created {num_samples} subvolumes.")
            
        else:
            raise ValueError("Mode must be 'deterministic' or 'stochastic'.")

        return subvolumes
    
    # =========================================================================
    # Meshing Module
    # =========================================================================
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
        self.padding_size += padding_size

    def generate_mesh(self):
        """
        Creates a mesh using the marching cubes algorithm and stores it in the object.
        (Replaces your getMesh function)
        """
        # Ensure it's a binary matrix (0.0 to 1.0) before meshing
        binary_matrix = self.matrix / np.max(self.matrix) if np.max(self.matrix) > 0 else self.matrix
        
        self.vertices, self.faces, _, _ = measure.marching_cubes(binary_matrix, allow_degenerate=False, method='lewiner', spacing=self.voxel_size)
        
        # Flip normals by reversing face winding
        self.invert_faces()
        
    def get_trimesh(self):
        """Helper to quickly return a trimesh object for smoothing/export."""
        if np.sum(self.matrix) == 0:
            print(f'{self.name} is empty')
            return None
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        return trimesh.Trimesh(vertices=self.vertices, faces=self.faces)
    
    def check_mesh(self):
        """
        Check if mesh is a volume (no non-manifolds)
        
        :param self: Description
        :return: True or false
        """
        mesh = self.get_trimesh()
        if mesh:
            return mesh.is_volume
        else:
            return None
    
    def apply_smoothing(self, smoothing_params):
        """
        Applies requested smoothing filters to a provided trimesh object.
        
        :param smoothing_params: Dictionary containing filter options {'laplacian': 2}, {'ScreenPoisson':7}.
        :return: Smoothed trimesh object.
        """
        if not smoothing_params:
            print('No smoothing filter specified!')
            return 
        
        mesh = self.get_trimesh()
        
        if smoothing_params.get('laplacian'):
            mesh = trimesh.smoothing.filter_laplacian(
                mesh, 
                iterations=smoothing_params['laplacian'],
                volume_constraint=True
            )

            self.vertices = mesh.vertices
            self.faces = mesh.faces
            self.name = self.name+'.laplacian'+str(smoothing_params['laplacian'])

        elif smoothing_params.get('ScreenPoisson'):

            import pymeshlab as ml
            meshTarget = ml.Mesh(mesh.vertices,mesh.faces) 
            ms = ml.MeshSet(verbose=True)
            ms.add_mesh(meshTarget)

            ms.apply_filter('generate_surface_reconstruction_screened_poisson', depth=smoothing_params['ScreenPoisson'], preclean=True)
            
            mesh = ms.current_mesh()

            self.vertices = mesh.vertex_matrix()
            self.faces = mesh.face_matrix() 

            mesh = trimesh.Trimesh(vertices=self.vertices, faces=self.faces)
        
        else:
            print('Filter not recognized.')

        return mesh
    
    def invert_faces(self):
        """
        Inverts the triangle faces by reversing their vertex winding order.
        This effectively flips the surface normals of the mesh.
        """
        if self.vertices is None or self.faces is None:
            print("No mesh data found. Generating the initial mesh first...")
            self.generate_mesh()
            return

        # Reverse the order of the vertex indices for every face triangle
        self.faces = self.faces[:, ::-1]
    
    
    # =========================================================================
    # ADVANCED SEGMENTATION ENGINE (From HERMES.py)
    # =========================================================================

    def segment(self, method, invert=False, block_size=51, offset=10, min_manual=0, max_manual=255):
        """
        Binarizes the internal greyscale matrix using advanced threshold algorithms.
        Converts self.matrix in place into a binary format (0 for void, 1 for solid features).
        
        :param method: "Otsu", "Adaptive", "Li", "Yen", "Isodata", "Triangle", or "Manual".
        :param invert: False targets bright foreground objects (Fibers). True targets dark fields (Pores).
        :param block_size: Odd integer bounding box size for local "Adaptive" calculation.
        :param offset: Constant subtracted from local mean in "Adaptive" tracking.
        :param min_manual: Minimum intensity floor bound used in "Manual" slicing.
        :param max_manual: Maximum intensity cell ceiling bound used in "Manual" slicing.
        """
        method = method.strip().capitalize()
        
        if method == "Manual":
            mask = (self.matrix >= min_manual) & (self.matrix <= max_manual)
            self.matrix = mask.astype(np.uint16)
            return

        # Execute scikit-image automated filters
        if method == "Otsu":
            threshold = threshold_otsu(self.matrix)
        elif method == "Adaptive":
            if block_size % 2 == 0:
                raise ValueError("Adaptive threshold block_size must be an ODD integer.")
            threshold = threshold_local(self.matrix, block_size, offset=offset)
        elif method == "Li":
            threshold = threshold_li(self.matrix)
        elif method == "Yen":
            threshold = threshold_yen(self.matrix)
        elif method == "Isodata":
            threshold = threshold_isodata(self.matrix)
        elif method == "Triangle":
            threshold = threshold_triangle(self.matrix)
        else:
            raise ValueError(f"Unknown thresholding segmentation method variant: {method}")

        # Construct binary arrays based on target object profile maps
        if not invert:
            mask = self.matrix > threshold
        else:
            mask = self.matrix < threshold
            
        # Clear out geometry cache hooks since the matrix underlying values changed
        self.vertices = None
        self.faces = None
        
        # Save array container state in place back to the grid domain
        self.matrix = mask.astype(np.uint16)

    # =========================================================================
    # IMAGE FILTERING MODULE
    # =========================================================================

    def apply_image_filter(self, method, **kwargs):
        """
        Applies 3D image processing filters to the internal matrix in-place.
        Useful for noise reduction, smoothing, and contrast enhancement prior to segmentation.
        
        :param method: "Median", "Gaussian", "Equalize", or "Rescale".
        :param kwargs: Optional parameters like 'size' (Median) or 'sigma' (Gaussian).
        """
        method = method.strip().capitalize()
        
        # 1. Noise Reduction & Smoothing
        if method == "Median":
            # Excellent for removing salt-and-pepper noise while preserving sharp boundaries
            from scipy.ndimage import median_filter
            size = kwargs.get('size', 3)
            print(f"Applying 3D Median filter (size={size})...")
            self.matrix = median_filter(self.matrix, size=size)
            
        elif method == "Gaussian":
            # Standard low-pass filter for general volumetric smoothing
            from scipy.ndimage import gaussian_filter
            sigma = kwargs.get('sigma', 1.0)
            orig_dtype = self.matrix.dtype
            print(f"Applying 3D Gaussian filter (sigma={sigma})...")
            
            # Gaussian filter scales to float; cast back to original dtype to protect memory
            smoothed = gaussian_filter(self.matrix.astype(float), sigma=sigma)
            self.matrix = smoothed.astype(orig_dtype)

        # 2. Contrast Enhancement
        elif method == "Equalize":
            # Global histogram equalization to boost contrast across the whole volume
            from skimage import exposure
            orig_dtype = self.matrix.dtype
            print("Applying Histogram Equalization...")
            
            # Equalize returns a float64 array scaled from 0.0 to 1.0
            equalized = exposure.equalize_hist(self.matrix)
            
            # Safely scale it back to the original integer range (e.g., 0-65535 for uint16)
            if np.issubdtype(orig_dtype, np.integer):
                max_val = np.iinfo(orig_dtype).max
                self.matrix = (equalized * max_val).astype(orig_dtype)
            else:
                self.matrix = equalized.astype(orig_dtype)
                
        elif method == "Rescale":
            # Stretches the intensity histogram to fill the maximum possible data range
            from skimage import exposure
            in_range = kwargs.get('in_range', 'image')
            out_range = kwargs.get('out_range', 'dtype')
            print(f"Applying Intensity Rescaling (in_range={in_range}, out_range={out_range})...")
            
            self.matrix = exposure.rescale_intensity(self.matrix, in_range=in_range, out_range=out_range)
            
        else:
            raise ValueError(f"Unknown filter method: {method}. Choose 'Median', 'Gaussian', 'Equalize', or 'Rescale'.")
            
        # CRITICAL: Clear the geometry cache since the underlying voxel values have changed
        self.vertices = None
        self.faces = None
    # =========================================================================
    # PROPERTIES QUANTIFICATION MODULES
    # =========================================================================

    def compute_fiber_diameter(self, sphere_size_um):
        """Calculates internal localized thickness diameter trends using an anisotropic distance EDT map."""
        mat = self.matrix[self.padding_size:-self.padding_size, self.padding_size:-self.padding_size, self.padding_size:-self.padding_size] if self.padding_size > 0 else self.matrix
        if np.sum(mat) == 0:
            return 0.0, 0.0, []

        distance_transform = distance_transform_edt(mat, sampling=self.voxel_size)
        min_dist_voxels = max(1, int(0.5 * sphere_size_um / np.min(self.voxel_size)))
        local_maxima_coords = peak_local_max(distance_transform, min_distance=min_dist_voxels, labels=mat.astype(int))
        
        fiber_diameters = [2 * distance_transform[tuple(max_coords)] for max_coords in local_maxima_coords]
        return (float(np.mean(fiber_diameters)), float(np.std(fiber_diameters)), fiber_diameters) if fiber_diameters else (0.0, 0.0, [])

    def compute_pore_distribution(self, sphere_size_um):
        """Inverts material maps to quantify internal geometric pore sizes across void regions."""
        mat = self.matrix[self.padding_size:-self.padding_size, self.padding_size:-self.padding_size, self.padding_size:-self.padding_size] if self.padding_size > 0 else self.matrix
        inverted_mat = (mat == 0).astype(int)
        if np.sum(inverted_mat) == 0:
            return 0.0, 0.0, []

        distance_transform = distance_transform_edt(inverted_mat, sampling=self.voxel_size)
        min_dist_voxels = max(1, int(0.5 * sphere_size_um / np.min(self.voxel_size)))
        local_maxima_coords = peak_local_max(distance_transform, min_distance=min_dist_voxels, labels=inverted_mat)
        
        pore_distribution = [2 * distance_transform[tuple(max_coords)] for max_coords in local_maxima_coords]
        return (float(np.mean(pore_distribution)), float(np.std(pore_distribution)), pore_distribution) if pore_distribution else (0.0, 0.0, [])

    def compute_centerline_orientation(self, plane='XY', step_size=4, branch_steps=4, save_dir_path=None):
        """Skeletonizes structures into network graphs to resolve tensor orientation profiles and structural vectors."""
        mat = self.matrix[self.padding_size:-self.padding_size, self.padding_size:-self.padding_size, self.padding_size:-self.padding_size] if self.padding_size > 0 else self.matrix
        if np.sum(mat) == 0:
            return None, None, None, None, None, None

        smoothed = (filters.gaussian(mat, sigma=1) >= np.max(filters.gaussian(mat, sigma=1)) * 0.5).astype(np.uint8)
        skeleton = morphology.skeletonize(smoothed)
        coords = np.column_stack(np.where(skeleton > 0))
        if coords.shape[0] == 0:
            return None, None, None, None, None, None

        G = nx.Graph()
        for pt in coords: G.add_node(tuple(pt))
        # Define 26-connectivity neighbors using clean dx, dy, dz notation
        neighbors_26 = [(dx, dy, dz) for dx in [-1,0,1] for dy in [-1,0,1] for dz in [-1,0,1] if not (dx==dy==dz==0)]
        
        # Corrected variable names to match the true (X, Y, Z) architecture
        for x, y, z in coords:
            for dx, dy, dz in neighbors_26:
                nbr = (x + dx, y + dy, z + dz)
                if nbr in G and np.linalg.norm(np.array([x, y, z]) - np.array(nbr)) <= np.sqrt(3):
                    G.add_edge((x, y, z), nbr, weight=np.linalg.norm(np.array([x, y, z]) - np.array(nbr)))

        MST = nx.minimum_spanning_tree(G)
        branch_nodes = [node for node in MST.nodes() if MST.degree(node) > 2]
        split_cl, _ = self._split_and_order_centerlines(MST, branch_nodes, steps=branch_steps)
        props, d_coords, d_vecs, d_ids = self._calculate_centerline_properties(split_cl, mat, plane=plane, step_size=step_size)
        
        if props.size == 0:
            return None, None, None, None, None, None 
        az_m, el_m, len_m = np.mean(props, axis=0)
        az_s, el_s, len_s = np.std(props, axis=0)

        # Always calculate the map so we can use it for VTU export
        d_map_unpadded, _, _ = self._map_direction_to_material_voxels(mat, d_coords, d_vecs, d_ids)
        
        # Create a full-size array (matching the padded matrix) initialized with NaNs
        self.direction_map = np.full(self.matrix.shape + (3,), np.nan, dtype=np.float32)
        
        # Re-insert the unpadded vectors into the correct spatial location
        if self.padding_size > 0:
            p = self.padding_size
            self.direction_map[p:-p, p:-p, p:-p, :] = d_map_unpadded
        else:
            self.direction_map = d_map_unpadded

        if save_dir_path:
            self._save_voxel_direction_map_txt(save_dir_path, d_map_unpadded)

        return  float(az_m), float(az_s), float(el_m), float(el_s), float(len_m), float(len_s)

    def compute_surface_area(self):
        mesh = self.get_trimesh()
        if mesh:
            self.properties['surface_area'] = float(mesh.area)
        else:
            self.properties['surface_area'] = float(0)

    def compute_closed_volume(self):
        mesh = self.get_trimesh()
        if mesh:
            self.properties['closed_volume'] = float(mesh.volume)
        else:
            self.properties['closed_volume'] = float(0)

    def compute_volume_by_area(self):
        mesh = self.get_trimesh()
        if mesh:
            self.properties['volume_by_area'] = float(mesh.volume / mesh.area) if mesh.area > 0 else 0.0
        else:
            self.properties['volume_by_area'] = float(0)
    def compute_porosity(self):
        mesh = self.get_trimesh()
        if mesh:
            unpadded_shape = [s - 2 * self.padding_size for s in self.matrix.shape]
            volume_total = np.prod(unpadded_shape) * np.prod(self.voxel_size)
            self.properties['porosity'] = float(1.0 - (mesh.volume / volume_total))
        else:
            self.properties['porosity'] = float(1.0)

    def compute_fiber_diameters(self, sphere_size):

        f_mean, f_std, f_dist = self.compute_fiber_diameter(sphere_size)
        self.properties.update({
            'fiber_diameter_mean': f_mean, 
            'fiber_diameter_std': f_std, 
            'fiber_diameter_distribution': f_dist
            })

    def compute_pore_distributions(self, sphere_size):
        p_mean, p_std, p_dist = self.compute_pore_distribution(sphere_size)
        self.properties.update({
            'pore_size_mean': p_mean, 
            'pore_size_std': p_std,
            'pore_size_distribution': p_dist
        })

    def compute_centerline_orientations(self, plane='XY', step_size=4, save_dir_path=None):
        az_m, az_s, el_m, el_s, len_m, len_s = self.compute_centerline_orientation(plane=plane, step_size=step_size, save_dir_path=save_dir_path)

        self.properties.update({
            "azimuth_mean": az_m, 
            "azimuth_std": az_s, 
            "elevation_mean": el_m, 
            "elevation_std": el_s, 
            "length_mean": len_m, 
            "length_std": len_s
        })
    def compute_all_properties(self, fiber_sphere=10, pore_sphere=30, plane='XY', step_size=4):
        """Runs the entire characterization analytics portfolio and stores outputs in self.properties."""
        # Ensure mesh exists for geometric properties
        if np.sum(self.faces) == 0:
            self.generate_mesh()

        # Execute modules
        self.compute_surface_area()
        self.compute_closed_volume()
        self.compute_volume_by_area()
        self.compute_porosity()
        self.compute_fiber_diameters(fiber_sphere)
        self.compute_pore_distributions(pore_sphere)
        self.compute_centerline_orientations(plane=plane, step_size=step_size)

        return self.properties

    # Private internal math helper functions
    def _split_and_order_centerlines(self, graph, branch_nodes, steps=4):
        G = graph.copy()

        # -------------------------------------------------
        # If no branch nodes, no splitting needed
        # Just order each connected component and return
        # -------------------------------------------------
        if not branch_nodes:
            return [[node for node in self._order_component(G.subgraph(c).copy())] for c in nx.connected_components(G)], G
        
        # -------------------------------------------------
        # Branch adjustment
        # -------------------------------------------------

        # For each branch node, adjust the intersection by removing the first voxel
        # along the branch that deviates most from the others.
        for branch in branch_nodes:
            if branch not in G: continue

            nbrs = list(G.neighbors(branch))

            if len(nbrs) <= 1: continue

            diffs = {}
            for n1 in nbrs:
                curr, prev, total = n1, branch, 0
                for _ in range(steps - 1):
                    cand = [nb for nb in G.neighbors(curr) if nb != prev]
                    if cand: prev = curr, curr = cand[0]
                    else: break
                v1 = (np.array(curr) - np.array(branch))

                if np.linalg.norm(v1) == 0: continue

                v1 = v1 / np.linalg.norm(v1)

                for n2 in nbrs:
                    if n1 == n2: continue

                    curr2, prev2 = n2, branch
                    for _ in range(steps - 1):
                        cand2 = [nb for nb in G.neighbors(curr2) if nb != prev2]
                        if cand2: prev2, curr2 = curr2, cand2[0]
                        else: break
                    v2 = (np.array(curr2) - np.array(branch))

                    if np.linalg.norm(v2) == 0: continue

                    total += np.arccos(np.clip(np.dot(v1, v2 / np.linalg.norm(v2)), -1.0, 1.0))
                diffs[n1] = total
            if diffs: G.remove_node(max(diffs, key=diffs.get))
        return [self._order_component(G.subgraph(c).copy()) for c in nx.connected_components(G)], G

    def _order_component(self, subgraph):
        nodes = list(subgraph.nodes())

        if len(nodes) <= 1: return nodes

        ends = [n for n in nodes if subgraph.degree(n) == 1]

        node, visited, ordered = ends[0] if ends else nodes[0], set(), []

        while node is not None:
            ordered.append(node)
            visited.add(node)
            next_n = [n for n in subgraph._adj[node] if n not in visited]
            node = next_n[0] if next_n else None
        return ordered

    def _calculate_centerline_properties(self, split_centerlines, image, plane='XY', step_size=4):

        dt = distance_transform_edt(image > 0, sampling=self.voxel_size)

        props, d_coords, d_vecs, d_ids = [], [], [], []
        
        # Track the last valid vector across centerlines (for the zero-norm fallback)
        last_valid_vector = np.zeros(3, dtype=np.float32)

        for cl_id, centerline in enumerate(split_centerlines):
            # 1. Convert the entire centerline to a single numpy array once
            cl_arr = np.array(centerline)
            n_voxels = len(cl_arr)
            
            if n_voxels == 0:
                continue

            # 2. Vectorized calculation of target indices (clipped to array bounds)
            target_indices = np.clip(np.arange(n_voxels) + step_size, 0, n_voxels - 1)
            
            # 3. Vectorized math: Subtraction and scaling for all voxels simultaneously
            vecs = (cl_arr[target_indices] - cl_arr) * self.voxel_size
            norms = np.linalg.norm(vecs, axis=1)
            
            # 4. Vectorized normalization (safely avoiding divide-by-zero)
            valid = norms > 0
            unit_vecs = np.zeros_like(vecs, dtype=np.float32)
            unit_vecs[valid] = vecs[valid] / norms[valid, np.newaxis]
            
            # 5. Handle the zero-norm fallback (usually the last few voxels)
            if not np.all(valid):
                if np.any(valid):
                    # If there are valid vectors, fill the invalid ones with the last valid one in this line
                    last_valid_idx = np.where(valid)[0][-1]
                    unit_vecs[~valid] = unit_vecs[last_valid_idx]
                else:
                    # If the entire line is invalid/too short, use the global history fallback
                    unit_vecs[~valid] = last_valid_vector
            
            # Update global fallback for the next centerline
            last_valid_vector = unit_vecs[-1]

            # Store the batch arrays directly (much faster than element-wise appending)
            d_coords.append(cl_arr)
            d_vecs.append(unit_vecs)
            d_ids.append(np.full(n_voxels, cl_id, dtype=np.int32))

            # 6. Mean vector and total length
            length = np.sum(norms)
            mean_v = np.mean(vecs, axis=0)
            mean_norm = np.linalg.norm(mean_v)

            # 7. Angle calculations
            if mean_norm == 0:
                az, el = 0.0, 0.0
            else:
                # Note: Added np.clip to prevent NaN runtime warnings from floating point errors
                if plane == 'XY':
                    az, el = np.arctan2(mean_v[1], mean_v[0]), np.arcsin(np.clip(mean_v[2] / mean_norm, -1.0, 1.0))
                elif plane == 'XZ':
                    az, el = np.arctan2(mean_v[2], mean_v[0]), np.arcsin(np.clip(mean_v[1] / mean_norm, -1.0, 1.0))
                elif plane == 'YZ':
                    az, el = np.arctan2(mean_v[2], mean_v[1]), np.arcsin(np.clip(mean_v[0] / mean_norm, -1.0, 1.0))
                else:
                    raise ValueError("Invalid plane option. Choose from 'XY', 'XZ', or 'YZ'.")

            # Start and End EDT addition
            start_idx = tuple(np.round(cl_arr[0]).astype(int))
            end_idx = tuple(np.round(cl_arr[-1]).astype(int))
            length += dt[start_idx] + dt[end_idx]

            props.append([float(np.degrees(az)), float(np.degrees(el)), float(length)])

        # Handle empty graphs to prevent vstack errors
        if not props:
            return (np.array([], dtype=float), np.array([], dtype=int), 
                    np.array([], dtype=np.float32), np.array([], dtype=np.int32))

        # Stack the collected batch arrays into final outputs
        return (np.array(props, dtype=float), 
                np.vstack(d_coords).astype(int), 
                np.vstack(d_vecs).astype(np.float32), 
                np.concatenate(d_ids).astype(np.int32))

    def _map_direction_to_material_voxels(self, image, d_coords, d_vecs, d_ids):
        mat_coords = np.column_stack(np.where(image > 0))
        _, nearest = cKDTree(d_coords).query(mat_coords, k=1)
        d_map = np.full(image.shape + (3,), np.nan, dtype=np.float32)
        x, y, z = mat_coords[:, 0], mat_coords[:, 1], mat_coords[:, 2]
        d_map[x, y, z, :] = d_vecs[nearest]
        return d_map, None, None

    def _save_voxel_direction_map_txt(self, filename, d_map):
        coords = np.column_stack(np.where(~np.isnan(d_map[..., 0])))
        np.savetxt(filename, np.column_stack((coords, d_map[coords[:, 0], coords[:, 1], coords[:, 2]])), fmt="%.6f", header="x y z vx vy vz", comments='')

    # =========================================================================
    # Output MODULES
    # =========================================================================

    def save_voxel_data(self, filepath):
        """Saves current binarized matrix to a .dat file (Chen format)."""

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        x_i, y_j, z_k = self.matrix.shape
        with open(filepath, 'w') as f:
            f.write(f"{x_i-1} {y_j-1} {z_k-1} {self.voxel_size[0]*10**-6}\n")
            f.write("i j k voxel")
            coords = np.column_stack(np.where(self.matrix == 1))
            for pt in coords:
                f.write(f"\n{pt[0]} {pt[1]} {pt[2]} 1")

    def export_stl(self, filepath):
        """Generates and exports the mesh to STL."""

        self._make_parent_path(filepath)
        
        if self.vertices is None:
            self.generate_mesh()
        
        mesh = self.get_trimesh()
        
        mesh.export(filepath, file_type="stl_ascii")

    def save_properties(self, filepath, append=True):
        """Appends the internally computed self.properties to a text file."""
        import json
        
        if not append:
            filepath = self._get_versioned_path(filepath)
        else:
            self._make_parent_path(filepath)

        # Ensure properties are computed
        if not self.properties:
            print('No properties computed yet!')
            return
            
        # Prepend 'WorkspaceName' and 'self.name' to the headers and values respectively
        keys = ['WorkspaceName'] + list(self.properties.keys())
        values = [self.name] + list(self.properties.values())
        
        header = '\t'.join(keys) + '\n'
        line = '\t'.join([str(v) if not isinstance(v, (list, np.ndarray)) 
                          else json.dumps(v) for v in values]) + '\n'   
        with open(filepath, "a+") as f:
            f.seek(0)
            if "WorkspaceName" not in f.read():
                f.write(header)
            f.write(line)
        print(f'Saving properties of {self.name} to {filepath}')

    def export_vtu(self, filepath, scalars_name="Material", filter_background=False):
        """
        Exports the current 3D matrix as a volumetric Hexahedral mesh (.vtu) via PyVista.
        """
        self._make_parent_path(filepath)
        
        if np.sum(self.matrix) == 0:
            print(f"Warning: {self.name} matrix is completely empty. Skipping VTU export.")
            return

        grid = pv.ImageData()
        grid.dimensions = np.array(self.matrix.shape) + 1
        grid.spacing = self.voxel_size
        
        # 1. Attach Scalar Field (The binary/greyscale matrix)
        grid.cell_data[scalars_name] = self.matrix.flatten(order="F")
        
        # 2. Attach Vector Field (The orientation mapping)
        if hasattr(self, 'direction_map') and self.direction_map is not None:
            # Flatten spatial dimensions (F-order) but preserve the X, Y, Z components
            vec_x = self.direction_map[..., 0].flatten(order="F")
            vec_y = self.direction_map[..., 1].flatten(order="F")
            vec_z = self.direction_map[..., 2].flatten(order="F")
            
            # Stack into an (N, 3) array that PyVista recognizes as vectors
            vectors = np.column_stack((vec_x, vec_y, vec_z))
            
            # Replace NaNs with [0,0,0] to prevent Paraview rendering errors on void space
            grid.cell_data["Orientation"] = np.nan_to_num(vectors)
        
        # 3. Filter and Export
        if filter_background:
            max_val = np.max(self.matrix)
            vtu_mesh = grid.threshold([1e-6, max_val], scalars=scalars_name)
        else:
            vtu_mesh = grid.cast_to_unstructured_grid()
            
        vtu_mesh.save(filepath)
        print(f"Successfully exported hexahedral .vtu mesh to: {filepath}")

    def _get_versioned_path(self, filepath):
        """
        Ensures the directory exists and returns a versioned filename 
        if the file already exists.
        """
        path = self._make_parent_path(filepath)
        
        # 2. Handle file versioning if it exists
        if path.exists():
            base = path.stem
            ext = path.suffix
            directory = path.parent
            
            # Look for existing copies and increment
            counter = 1
            new_path = directory / f"{base}_copy{counter}{ext}"
            while new_path.exists():
                counter += 1
                new_path = directory / f"{base}_copy{counter}{ext}"
            
            return str(new_path)
        
        return str(path)
    
    def _make_parent_path(self, filepath):
        """
        Ensures the directory exists and returns path
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        return path

    # =========================================================================
    # Visualization MODULES
    # =========================================================================
    def visualize_matrix_cutoff(self, vmin, vmax, cmap="viridis"):
        """
        Visualizes the workspace's 3D matrix in PyVista, showing only values within a cutoff range.
        Acts as an interactive voxel threshold slider similar to PuMA/ParaView.
        
        :param vmin: Minimum cutoff value to display.
        :param vmax: Maximum cutoff value to display.
        :param cmap: Colormap for the visualization (default is "viridis").
        """

        # 1. Initialize a PyVista 3D grid
        # Add 1 to the shape because dimensions represent nodes, but data represents cells
        grid = pv.ImageData()
        grid.dimensions = np.array(self.matrix.shape) + 1
        
        # 2. Assign the matrix data to the grid
        # Flattened in Fortran order (column-major) to align with VTK memory mapping
        grid.cell_data["values"] = self.matrix.flatten(order="F")
        
        # 3. Apply the threshold filter to extract targeted voxels
        thresholded_mesh = grid.threshold([vmin, vmax], scalars="values")
        
        # 4. Set up the interactive plotter
        plotter = pv.Plotter()
        
        # Prevent crashes if the user selects a range with zero voxels
        if thresholded_mesh.n_cells == 0:
            print(f"No voxels found in the range [{vmin}, {vmax}] for workspace '{self.name}'.")
            return
            
        # Render the thresholded mesh
        plotter.add_mesh(
            thresholded_mesh, 
            scalars="values", 
            cmap=cmap, 
            show_edges=False, 
            scalar_bar_args={"title": "Voxel Intensity"}
        )
        
        # Add spatial context
        plotter.add_axes()
        plotter.add_bounding_box(color='black', line_width=1.5)
        
        # Launch the GUI window
        plotter.show()

    def visualize_matrix_cutoff_plt(self, vmin, vmax, downsample_factor=1):
        """
        Visualizes the 3D matrix using Matplotlib (bypassing OpenGL requirements).
        
        :param vmin: Minimum cutoff value to display.
        :param vmax: Maximum cutoff value to display.
        :param downsample_factor: Increase this integer (e.g., 2, 3) to speed up rendering for huge matrices.
        """
        import matplotlib.pyplot as plt
        
        # 1. Downsample the matrix if requested (takes every Nth voxel)
        if downsample_factor > 1:
            mat = self.matrix[::downsample_factor, ::downsample_factor, ::downsample_factor]
            print(f"Downsampled matrix for visualization from {self.matrix.shape} to {mat.shape}")
        else:
            mat = self.matrix
            
        # 2. Create a boolean mask of voxels that fall within the cutoff range
        voxel_mask = (mat >= vmin) & (mat <= vmax)
        
        if not np.any(voxel_mask):
            print(f"No voxels found in the range [{vmin}, {vmax}] for workspace '{self.name}'.")
            return
            
        # 3. Render using Matplotlib 3D
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot using one of our stylish colors from earlier!
        # (edgecolor makes the individual cubes visible, alpha makes them slightly transparent)
        ax.voxels(voxel_mask, facecolors='#118AB2', edgecolor='black', alpha=0.6)
        
        physical_aspect = np.array(mat.shape) * self.voxel_size
        ax.set_box_aspect(physical_aspect)

        ax.set_title(f"Workspace: {self.name} | Cutoff: {vmin} - {vmax}")
        
        # This will perfectly pipe to your VS Code Interactive Window!
        plt.show()
    
    def visualize_standalone_dashboard(self, cmap='gray'):
        """
        A standalone Python dashboard for 3D matrix visualization using pure Matplotlib.
        Allows real-time switching of both the slice and the viewing axis.
        Automatically resets to the center slice when changing axes.
        """
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider, RadioButtons

        # 1. Setup the figure and strict layout zones
        fig = plt.figure(figsize=(10, 8))
        
        ax_main = fig.add_axes([0.25, 0.15, 0.7, 0.75])     # Main display
        ax_slider = fig.add_axes([0.25, 0.05, 0.7, 0.03])   # Slider at the bottom
        ax_radio = fig.add_axes([0.05, 0.7, 0.1, 0.15])     # Radio buttons on the left

        # 2. Application state tracker
        state = {
            'axis_label': 'Z',
            'axis_idx': 2,
            'image': None,
            'title': None
        }

        # 3. Initialize UI elements
        radio = RadioButtons(ax_radio, ('X', 'Y', 'Z'), active=2)
        
        max_slice = self.matrix.shape[2] - 1
        initial_slice = max_slice // 2
        slider = Slider(ax_slider, 'Slice', 0, max_slice, valinit=initial_slice, valstep=1)

        # 4. Define UI Update Logic
        def render_full_axis():
            """Fully clears and redraws the main axis when changing X/Y/Z."""
            ax_idx = state['axis_idx']
            axis_val = state['axis_label']
            
            # Update slider bounds dynamically
            new_max = self.matrix.shape[ax_idx] - 1
            slider.valmax = new_max
            slider.ax.set_xlim(0, new_max) 
            
            # CRITICAL UPDATE: Force slider to the exact center of the new axis
            center_idx = new_max // 2
            
            # Temporarily disable slider events to prevent a double-render crash
            slider.eventson = False 
            slider.set_val(center_idx)
            slider.eventson = True
            
            idx = center_idx
            
            # Calculate physical aspect ratio
            if axis_val == 'X': aspect = self.voxel_size[2] / self.voxel_size[1]
            elif axis_val == 'Y': aspect = self.voxel_size[2] / self.voxel_size[0]
            else: aspect = self.voxel_size[1] / self.voxel_size[0]

            # Extract new center slice
            if ax_idx == 0: data = self.matrix[idx, :, :]
            elif ax_idx == 1: data = self.matrix[:, idx, :]
            else: data = self.matrix[:, :, idx]

            # Redraw image
            ax_main.clear()
            state['image'] = ax_main.imshow(data, cmap=cmap, aspect=aspect, interpolation='nearest')
            state['title'] = ax_main.set_title(f"Workspace: {self.name} | Axis: {axis_val} | Slice: {idx}")
            fig.canvas.draw_idle()

        def update_slice(val):
            """Fast memory update when sliding."""
            if state['image'] is None: return
            
            idx = int(slider.val)
            ax_idx = state['axis_idx']
            
            # Extract slice
            if ax_idx == 0: new_data = self.matrix[idx, :, :]
            elif ax_idx == 1: new_data = self.matrix[:, idx, :]
            else: new_data = self.matrix[:, :, idx]
            
            # Fast swap
            state['image'].set_data(new_data)
            state['title'].set_text(f"Workspace: {self.name} | Axis: {state['axis_label']} | Slice: {idx}")
            fig.canvas.draw_idle()

        def update_axis(label):
            """Triggered by the RadioButtons to change the axis."""
            state['axis_label'] = label
            axis_map = {'X': 0, 'Y': 1, 'Z': 2}
            state['axis_idx'] = axis_map[label]
            render_full_axis()

        # 5. Connect events to logic
        slider.on_changed(update_slice)
        radio.on_clicked(update_axis)

        # 6. Garbage Collection Safety
        fig._slider_ref = slider
        fig._radio_ref = radio

        # 7. Render initial state and launch window
        render_full_axis()
        plt.show()