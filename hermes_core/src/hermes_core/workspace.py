# workspace.py
import numpy as np
import imageio
from skimage import measure, filters, morphology
import trimesh
import networkx as nx
from scipy.ndimage import distance_transform_edt
from skimage.feature import peak_local_max
from scipy.spatial import cKDTree

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
        self.padding_size = 0
        
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
        self.faces = self.faces[:, ::-1]
        
    def get_trimesh(self):
        """Helper to quickly return a trimesh object for smoothing/export."""
        if self.vertices is None or self.faces is None:
            self.generate_mesh()
        return trimesh.Trimesh(vertices=self.vertices, faces=self.faces)
    
    # =========================================================================
    # PROPERTIES QUANTIFICATION MODULES
    # =========================================================================

    def compute_fiber_diameter(self, sphere_size_um):
        """Calculates internal localized thickness diameter trends using an anisotropic distance EDT map."""
        mat = self.matrix[self.padding_size:-self.padding_size, self.padding_size:-self.padding_size, self.padding_size:-self.padding_size] if self.padding_size > 0 else self.matrix
        if np.sum(mat) == 0:
            return 0.0, 0.0

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
            return None

        smoothed = (filters.gaussian(mat, sigma=1) >= np.max(filters.gaussian(mat, sigma=1)) * 0.5).astype(np.uint8)
        skeleton = morphology.skeletonize(smoothed)
        coords = np.column_stack(np.where(skeleton > 0))
        if coords.shape[0] == 0:
            return None

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
            return None
        az_m, el_m, len_m = np.mean(props, axis=0)
        az_s, el_s, len_s = np.std(props, axis=0)

        if save_dir_path:
            d_map, _, _ = self._map_direction_to_material_voxels(mat, d_coords, d_vecs, d_ids)
            self._save_voxel_direction_map_txt(save_dir_path, d_map)

        return {"azimuth_mean": float(az_m), "azimuth_std": float(az_s), "elevation_mean": float(el_m), "elevation_std": float(el_s), "length_mean": float(len_m), "length_std": float(len_s)}

    def compute_all_properties(self, fiber_sphere=10, pore_sphere=30, plane='XY', step_size=4):
        """Runs the entire characterization analytics portfolio and stores outputs in self.properties."""
        mesh = self.get_trimesh()
        if mesh is None:
            return self.properties

        self.properties.update({
            'surface_area': float(mesh.area), 'closed_volume': float(mesh.volume),
            'volume_by_area': float(mesh.volume / mesh.area) if mesh.area > 0 else 0.0
        })
        unpadded_shape = [s - 2 * self.padding_size for s in self.matrix.shape]
        self.properties['porosity'] = float(1.0 - (mesh.volume / (np.prod(unpadded_shape) * np.prod(self.voxel_size))))
        
        f_mean, f_std, f_dist = self.compute_fiber_diameter(fiber_sphere)
        self.properties.update({'fiber_diameter_mean': f_mean, 'fiber_diameter_std': f_std, 'fiber_diameter_distribution': f_dist})
        
        p_mean, p_std, p_dist = self.compute_pore_distribution(pore_sphere)
        self.properties.update({'pore_size_mean': p_mean, 'pore_size_std': p_std, 'pore_size_distribution': p_dist})
        
        cl_data = self.compute_centerline_orientation(plane=plane, step_size=step_size)
        if cl_data: self.properties.update(cl_data)
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

        for cl_id, centerline in enumerate(split_centerlines):
            vecs, length = [], 0.0

            for i in range(0, len(centerline) - step_size, step_size):
                vec = (np.array(centerline[min(i + step_size, len(centerline) - 1)]) - np.array(centerline[i])) * self.voxel_size
                vecs.append(vec)
                length += np.linalg.norm(vec)

            if not vecs: continue

            mean_v = np.mean(vecs, axis=0)

            if np.linalg.norm(mean_v) == 0: continue

            unit_v = mean_v / np.linalg.norm(mean_v)

            for vox in centerline:
                d_coords.append(vox); d_vecs.append(unit_v); d_ids.append(cl_id)
            
            if plane == 'XY': az, el = np.arctan2(mean_v[1], mean_v[0]), np.arcsin(mean_v[2] / np.linalg.norm(mean_v))
            
            elif plane == 'XZ': az, el = np.arctan2(mean_v[2], mean_v[0]), np.arcsin(mean_v[1] / np.linalg.norm(mean_v))
            
            elif plane == 'YZ': az, el = np.arctan2(mean_v[2], mean_v[1]), np.arcsin(mean_v[0] / np.linalg.norm(mean_v))
            
            else: raise ValueError("Invalid plane option. Choose from 'XY', 'XZ', or 'YZ'.")

            length += dt[tuple(np.round(centerline[0]).astype(int))] + dt[tuple(np.round(centerline[-1]).astype(int))]
            
            props.append([float(np.degrees(az)), float(np.degrees(el)), float(length)])
        return np.array(props, dtype=float), np.array(d_coords, dtype=int), np.array(d_vecs, dtype=np.float32), np.array(d_ids, dtype=np.int32)

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