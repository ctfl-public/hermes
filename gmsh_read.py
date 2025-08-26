import gmsh
import sys

path = 'CC0_7.73504_6273_V0_539-592-479-2000_laplacian4_NI.stl'

gmsh.initialize()
gmsh.merge(path)


s = gmsh.model.getEntities(2)
l = gmsh.model.geo.addSurfaceLoop([e[1] for e in s])
V0 = gmsh.model.geo.addVolume([l])

gmsh.model.addPhysicalGroup(3, [V0], 1)
gmsh.model.geo.synchronize()
gmsh.model.mesh.generate(3)

#obtain the model dimension
dimensionBox = gmsh.model.getBoundingBox(-1, -1)

gmsh.write("CC0_7.73504_6273_V0_539-592-479-2000_laplacian4_NI.msh")
gmsh.finalize()