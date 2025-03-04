#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 14:42:41 2024

@author: lch285
"""

import pymeshlab
import os

def remove_floating_islands_keep_largest(input_stl, output_stl):
    """
    Removes all floating islands from an STL mesh except the one with the largest volume.

    Parameters:
        input_stl (str): Path to the input STL file.
        output_stl (str): Path to save the output STL file with the largest component retained.

    Returns:
        None
    """
    # Load the mesh
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_stl)

    # Compute connected components and select small components for deletion
    ms.apply_filter('select_small_disconnected_component',nbfaceratio=1)

    # Delete the selected small components
    ms.apply_filter('delete_selected_faces')

    # Save the resulting mesh as ASCII
    ms.save_current_mesh(output_stl, binary=False)

folder_path = '.'
extension = '.stl'

matching_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.endswith(extension)
    ]

for file in matching_files:
    remove_floating_islands_keep_largest(file, 'NoIslands/'+file[:-4]+'_NI.stl')
    print('Done with', file)


    
