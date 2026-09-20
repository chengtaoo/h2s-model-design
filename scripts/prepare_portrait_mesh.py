"""Repair an extracted portrait, add an overlapping oval plinth and sample a four-color palette.
Run the palette refinement and inspect actual previews before slicing.
"""
import argparse,json
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf
from PIL import Image
from scipy.spatial import cKDTree
from repair_winding import repair

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--simplify-mm',type=float,default=.02);p.add_argument('--clip-mm',type=float,default=3);p.add_argument('--base-mm',type=float,default=5)
p.add_argument('--palette',nargs=4,default=['#857047','#E8CBB3','#242326','#8C4048'])
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
if not 0<=a.clip_mm<a.base_mm or not 0<a.simplify_mm<=.1:raise ValueError('Require overlapping plinth and a bounded simplification tolerance')
d=np.load(a.input/'surface.npz');v=d['vertices'];f=d['faces'];uv=d['uv']
im=np.asarray(Image.open(a.input/'base-color.png').convert('RGB'))
xy=np.clip(uv,0,1);rgb=im[np.rint((1-xy[:,1])*(im.shape[0]-1)).astype(int),np.rint(xy[:,0]*(im.shape[1]-1)).astype(int)]
original=trimesh.Trimesh(v,f,process=False)
print('source',len(f),flush=True)
m=trimesh.Trimesh(v,f,process=True);m.update_faces(m.unique_faces());m.update_faces(m.nondegenerate_faces())
print('geometry',len(m.vertices),len(m.faces),m.is_watertight,m.is_winding_consistent,flush=True)
if not m.is_winding_consistent:
    print('normals repaired',repair(m),flush=True)
elif m.volume<0:
    m.invert()
mesh=mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32));mesh.merge();solid=mf.Manifold(mesh)
print('manifold',solid.status(),flush=True)
if solid.status()!=mf.Error.NoError:raise ValueError('Repair required before export')
before=solid.volume()
parts=solid.decompose();parts=sorted(parts,key=lambda x:abs(x.volume()),reverse=True)
print('components',len(parts),'volumes',[x.volume() for x in parts[:12]],flush=True)
if len(parts)>1:
    # Keep the dominant physical body; report every discarded shell.
    raise ValueError('Detached components require explicit inspection; this tool does not discard them')
solid=solid.simplify(a.simplify_mm)
print('simplified',solid.num_tri(),flush=True)
# Plane clips only the uneven lower edge. A plinth overlaps all bottom contacts.
solid=solid.trim_by_plane((0,0,1),a.clip_mm)
b=solid.bounding_box();rx=(b[3]-b[0])/2+3;ry=(b[4]-b[1])/2+3
base=mf.Manifold.cylinder(a.base_mm,1,1,128).scale((rx,ry,1)).translate(((b[0]+b[3])/2,(b[1]+b[4])/2,0))
solid=solid+base
print('base-union',solid.status(),solid.num_tri(),flush=True)
data=solid.to_mesh();out=trimesh.Trimesh(np.asarray(data.vert_properties)[:,:3],np.asarray(data.tri_verts),process=True)
if not out.is_watertight or not out.is_winding_consistent:raise ValueError('Final mesh not closed and consistently wound')
tree=cKDTree(original.triangles_center)
dist,idx=tree.query(out.triangles_center,workers=4)
colors=rgb[idx].copy()
base_rgb=[int(a.palette[0][i:i+2],16) for i in (1,3,5)]
colors[out.triangles_center[:,2]<a.base_mm+.01]=base_rgb
# Per-face color labels preserve geometry; no voxel remeshing of the face.
palette=a.palette
def lab(rgb):
    q=np.asarray(rgb,dtype=float)/255;q=np.where(q<=.04045,q/12.92,((q+.055)/1.055)**2.4)
    xyz=q@np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]]).T
    xyz/=np.array([.95047,1,1.08883]);t=np.where(xyz>.008856,xyz**(1/3),7.787*xyz+16/116)
    return np.stack([116*t[:,1]-16,500*(t[:,0]-t[:,1]),200*(t[:,1]-t[:,2])],axis=1)
prgb=np.array([[int(h[i:i+2],16) for i in (1,3,5)] for h in palette]);q=lab(colors);pl=lab(prgb)
distance=((q[:,None,:]-pl[None,:,:])**2).sum(axis=2)
labels=distance.argmin(axis=1)+1
np.savez_compressed(a.output/'print-mesh.npz',vertices=out.vertices.astype(np.float32),faces=out.faces.astype(np.int32),labels=labels.astype(np.uint8),rgb=colors)
out.export(a.output/'portrait.stl')
report={'faces':len(out.faces),'vertices':len(out.vertices),'watertight':bool(out.is_watertight),'winding_consistent':bool(out.is_winding_consistent),'volume_mm3':float(out.volume),'dimensions_mm':out.extents.tolist(),'original_volume_mm3':before,'original_components':len(parts),'discarded_volume_mm3':0,'simplification_tolerance_mm':a.simplify_mm,'bottom_clip_mm':a.clip_mm,'base_height_mm':a.base_mm,'palette':palette,'face_counts_by_slot':np.bincount(labels,minlength=5)[1:].tolist(),'components_after':len(solid.decompose()),'color_transfer_distance_p99_mm':float(np.quantile(dist[out.triangles_center[:,2]>a.base_mm+.01],.99))}
(a.output/'geometry-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
