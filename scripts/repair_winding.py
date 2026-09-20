"""Repair orientation of closed triangle meshes without moving vertices.

Use a sparse breadth-first spanning forest instead of a large NetworkX graph.
Reject inconsistent constraints instead of treating non-orientable surfaces as solids.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import breadth_first_order, connected_components


def repair(mesh):
    if not mesh.is_watertight:
        raise ValueError('Orientation repair requires a closed mesh')
    edges=mesh.edges
    sorted_edges=np.sort(edges,axis=1)
    order=np.lexsort((sorted_edges[:,1],sorted_edges[:,0]))
    first,second=order[::2],order[1::2]
    if not np.array_equal(sorted_edges[first],sorted_edges[second]):
        raise ValueError('Edge incidence is not two')
    left,right=first//3,second//3
    parity=(edges[first,0]==edges[second,0]).astype(np.uint8)
    graph=coo_matrix((np.r_[parity+1,parity+1],(np.r_[left,right],np.r_[right,left])),shape=(len(mesh.faces),len(mesh.faces))).tocsr()
    count,components=connected_components(graph,directed=False)
    flips=np.zeros(len(mesh.faces),dtype=bool)
    for component in range(count):
        root=int(np.flatnonzero(components==component)[0])
        traversal,parents=breadth_first_order(graph,root,directed=False)
        children=traversal[1:];parent=parents[children]
        constraints=np.asarray(graph[parent,children]).ravel()-1
        for child,prev,change in zip(children,parent,constraints):flips[child]=flips[prev]^bool(change)
    if not np.array_equal(flips[left]^flips[right],parity.astype(bool)):
        raise ValueError('Mesh has inconsistent orientation constraints')
    faces=mesh.faces.copy();faces[flips]=faces[flips,::-1]
    tri=mesh.vertices[faces]
    signed=np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2]))/6
    volumes=np.bincount(components,weights=signed)
    inward=volumes[components]<0
    faces[inward]=faces[inward,::-1]
    mesh.faces=faces
    return {'components':int(count),'faces_reoriented':int(np.count_nonzero(flips^inward)),'vertices_moved':0}
