"""Blender background: extract transformed millimetre geometry and UV colour samples.
Run: blender --background --python this.py -- --input model.glb --output scratch --height 150
"""
import argparse
import json
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--input',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--height',type=float,default=150)
p.add_argument('--rotate-z',type=float,default=-90)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
a.output.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(a.input.resolve()))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
if len(objects)!=1:
    raise ValueError('This extractor requires one textured mesh; consolidate explicitly first')
o=objects[0]
world=o.matrix_world.copy()
verts=np.array([world@v.co for v in o.data.vertices],dtype=np.float64)
low=verts.min(axis=0);high=verts.max(axis=0)
verts-=[(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]]
verts*=a.height/(high[2]-low[2])
angle=np.deg2rad(a.rotate_z);rot=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
verts=verts@rot.T
o.parent=None;o.matrix_world=Matrix.Identity(4)
o.data.vertices.foreach_set('co',verts.astype(np.float32).ravel())
bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(o.data);bm.free()
o.data.calc_loop_triangles()
triangles=np.array([t.vertices[:] for t in o.data.loop_triangles],dtype=np.int32)
loops=np.array([t.loops[:] for t in o.data.loop_triangles],dtype=np.int32)
uv=np.empty(len(o.data.uv_layers.active.data)*2,dtype=np.float32)
o.data.uv_layers.active.data.foreach_get('uv',uv)
uv=uv.reshape(-1,2)[loops].mean(axis=1)
images=[]
for mat in o.data.materials:
    if mat and mat.use_nodes:
        bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        links=bsdf.inputs['Base Color'].links
        if links and links[0].from_node.type=='TEX_IMAGE':images.append(links[0].from_node.image)
if len(images)!=1 or not images[0].packed_file:
    raise ValueError('Requires one packed base-color image; do not guess material mapping')
image=images[0]
(a.output/'base-color.png').write_bytes(image.packed_file.data)
np.savez(a.output/'surface.npz',vertices=verts.astype(np.float32),faces=triangles,uv=uv)
(a.output/'extraction.json').write_text(json.dumps({'height_mm':a.height,'faces':len(triangles),'rotate_z':a.rotate_z,'dimensions_mm':np.ptp(verts,axis=0).tolist()},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(a.output/'scaled-original.blend'))
print('EXTRACTED',len(triangles),flush=True)
