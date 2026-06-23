"""Centerline, fiber orientation, and direction-map utilities."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from skimage import filters, morphology


def analyze_centerline(image, voxel_size, surface_name, plane: str = "XY", direction_map_path=None):
    """Analyze fiber-like centerlines and write a voxel direction map."""
    image_smoothed = filters.gaussian(image, sigma=1)
    image_smoothed = (image_smoothed >= np.max(image_smoothed) * 0.5).astype(np.uint8)
    skeleton = morphology.skeletonize(image_smoothed)

    coords = np.column_stack(np.where(skeleton > 0))
    graph = nx.Graph()
    for z, y, x in coords:
        graph.add_node((z, y, x))

    neighbors_26 = [
        (dz, dy, dx)
        for dz in [-1, 0, 1]
        for dy in [-1, 0, 1]
        for dx in [-1, 0, 1]
        if not (dz == dy == dx == 0)
    ]
    max_distance = np.sqrt(3)

    for z, y, x in coords:
        for dz, dy, dx in neighbors_26:
            neighbor = (z + dz, y + dy, x + dx)
            if neighbor in graph:
                distance = np.linalg.norm(np.array([z, y, x]) - np.array(neighbor))
                if distance <= max_distance:
                    graph.add_edge((z, y, x), neighbor, weight=distance)

    minimum_spanning_tree = nx.minimum_spanning_tree(graph)
    branch_points = [node for node in minimum_spanning_tree.nodes() if minimum_spanning_tree.degree(node) > 2]
    split_centerlines, _ = split_and_order_centerlines(minimum_spanning_tree, branch_points)

    centerline_properties, direction_coords, direction_vectors, direction_centerline_ids = calculate_centerline_properties(
        split_centerlines,
        voxel_size,
        image,
        plane,
    )

    direction_map, _, _ = map_direction_to_material_voxels(
        image,
        direction_coords,
        direction_vectors,
        direction_centerline_ids,
    )
    if direction_map_path is None:
        direction_map_path = Path(str(surface_name)).with_suffix("").as_posix() + "_voxel_directions.txt"
    save_voxel_direction_map_txt(direction_map_path, direction_map)

    azimuth_mean, elevation_mean, length_mean = np.mean(centerline_properties, axis=0)
    azimuth_std, elevation_std, length_std = np.std(centerline_properties, axis=0, ddof=0)
    return azimuth_mean, elevation_mean, length_mean, azimuth_std, elevation_std, length_std


def save_voxel_direction_map_txt(filename, direction_map):
    """Save per-voxel direction vectors as text."""
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)
    coords = np.column_stack(np.where(~np.isnan(direction_map[..., 0])))
    vectors = direction_map[coords[:, 0], coords[:, 1], coords[:, 2]]
    data = np.column_stack((coords, vectors))
    np.savetxt(filename, data, fmt="%.6f", header="x y z vx vy vz", comments="")


def map_direction_to_material_voxels(image, direction_coords, direction_vectors, direction_centerline_ids=None):
    """Assign nearest centerline direction vectors to every material voxel."""
    material_coords = np.column_stack(np.where(image > 0))
    tree = cKDTree(direction_coords)
    distances, nearest_idx = tree.query(material_coords, k=1)

    direction_map = np.full(image.shape + (3,), np.nan, dtype=np.float32)
    distance_map = np.full(image.shape, np.nan, dtype=np.float32)
    centerline_id_map = np.full(image.shape, -1, dtype=np.int32) if direction_centerline_ids is not None else None

    x = material_coords[:, 0]
    y = material_coords[:, 1]
    z = material_coords[:, 2]
    direction_map[x, y, z, :] = direction_vectors[nearest_idx]
    distance_map[x, y, z] = distances

    if direction_centerline_ids is not None:
        centerline_id_map[x, y, z] = direction_centerline_ids[nearest_idx]

    return direction_map, distance_map, centerline_id_map


def split_and_order_centerlines(graph, branch_nodes, steps=4):
    """Split a skeleton graph into ordered centerline paths."""
    graph = graph.copy()
    split_centerlines = []

    if branch_nodes is None or len(branch_nodes) == 0:
        for component in nx.connected_components(graph):
            ordered_centerline = order_component(graph.subgraph(component).copy())
            if len(ordered_centerline) > 0:
                split_centerlines.append(ordered_centerline)
        return split_centerlines, graph

    for branch in branch_nodes:
        if branch not in graph:
            continue
        neighbors = list(graph.neighbors(branch))
        if len(neighbors) <= 1:
            continue

        branch_vectors = {}
        for neighbor in neighbors:
            current = neighbor
            previous = branch
            for _ in range(steps - 1):
                next_candidates = [node for node in graph.neighbors(current) if node != previous]
                if next_candidates:
                    previous = current
                    current = next_candidates[0]
                else:
                    break
            vector = np.array(current) - np.array(branch)
            norm = np.linalg.norm(vector)
            if norm != 0:
                branch_vectors[neighbor] = vector / norm

        if len(branch_vectors) < 2:
            continue

        differences = {}
        for node_1, vector_1 in branch_vectors.items():
            total_angle = 0
            for node_2, vector_2 in branch_vectors.items():
                if node_1 == node_2:
                    continue
                dot = np.clip(np.dot(vector_1, vector_2), -1, 1)
                total_angle += np.arccos(dot)
            differences[node_1] = total_angle

        branch_to_adjust = max(differences, key=differences.get)
        if branch_to_adjust in graph:
            graph.remove_node(branch_to_adjust)

    for component in nx.connected_components(graph):
        ordered_centerline = order_component(graph.subgraph(component).copy())
        if len(ordered_centerline) > 0:
            split_centerlines.append(ordered_centerline)

    return split_centerlines, graph


def order_component(subgraph):
    """Order a connected skeleton component into a path."""
    component_nodes = list(subgraph.nodes())
    if len(component_nodes) == 0:
        return []
    if len(component_nodes) == 1:
        return component_nodes

    endpoints = [node for node in component_nodes if subgraph.degree(node) == 1]
    start = endpoints[0] if len(endpoints) >= 1 else component_nodes[0]

    ordered_centerline = []
    visited = set()
    node = start
    while node is not None:
        ordered_centerline.append(node)
        visited.add(node)
        next_nodes = [next_node for next_node in subgraph._adj[node] if next_node not in visited]
        node = next_nodes[0] if next_nodes else None

    return ordered_centerline


def calculate_centerline_properties(split_centerlines, voxel_size, image, plane: str = "XY", step_size: int = 4):
    """Calculate azimuth, elevation, length, and local direction vectors."""
    distance_transform = distance_transform_edt(image > 0)
    centerline_properties = []
    direction_coords = []
    direction_vectors = []
    direction_centerline_ids = []

    for centerline_id, centerline in enumerate(split_centerlines):
        vectors = []
        length = 0.0
        for index in range(0, len(centerline) - step_size, step_size):
            point_1 = np.array(centerline[index])
            point_2 = np.array(centerline[min(index + step_size, len(centerline) - 1)])
            vector = point_2 - point_1
            vectors.append(vector)
            length += np.linalg.norm(vector) * voxel_size

        if not vectors:
            continue

        vectors = np.array(vectors)
        mean_vector = np.mean(vectors, axis=0)
        norm = np.linalg.norm(mean_vector)
        if norm == 0:
            continue

        mean_vector_unit = mean_vector / norm
        for voxel in centerline:
            direction_coords.append(voxel)
            direction_vectors.append(mean_vector_unit)
            direction_centerline_ids.append(centerline_id)

        if plane == "XY":
            average_azimuth = np.arctan2(mean_vector[1], mean_vector[0])
            average_elevation = np.arcsin(mean_vector[2] / norm)
        elif plane == "XZ":
            average_azimuth = np.arctan2(mean_vector[2], mean_vector[0])
            average_elevation = np.arcsin(mean_vector[1] / norm)
        elif plane == "YZ":
            average_azimuth = np.arctan2(mean_vector[2], mean_vector[1])
            average_elevation = np.arcsin(mean_vector[0] / norm)
        else:
            raise ValueError("Invalid plane option. Choose from 'XY', 'XZ', or 'YZ'.")

        first_point = tuple(np.round(centerline[0]).astype(int))
        last_point = tuple(np.round(centerline[-1]).astype(int))
        length += distance_transform[first_point] * voxel_size
        length += distance_transform[last_point] * voxel_size

        centerline_properties.append(
            [float(np.degrees(average_azimuth)), float(np.degrees(average_elevation)), float(length)]
        )

    return (
        np.array(centerline_properties, dtype=float),
        np.array(direction_coords, dtype=int),
        np.array(direction_vectors, dtype=np.float32),
        np.array(direction_centerline_ids, dtype=np.int32),
    )
