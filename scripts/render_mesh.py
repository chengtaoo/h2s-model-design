"""Render actual GLB or face-painted mesh with an offscreen OpenGL context, no Blender."""
import argparse,json
from pathlib import Path
import numpy as np
import trimesh
import pyrender
from PIL import Image


def camera_pose(eye,target):
    z=np.asarray(eye,dtype=float)-target;z/=np.linalg.norm(z)
    x=np.cross([0,0,1],z);x/=np.linalg.norm(x);y=np.cross(z,x)
    pose=np.eye(4);pose[:3,:3]=np.column_stack([x,y,z]);pose[:3,3]=eye
    return pose


def render(source,output,palette=None,face=False,clay=False,back=False):
    source=Path(source)
    if source.suffix=='.npz':
        d=np.load(source,allow_pickle=False);mesh=trimesh.Trimesh(d['vertices'],d['faces'],process=False)
        if palette is None:raise ValueError('Supply a palette for labelled geometry')
        rgb=np.array([[int(h[i:i+2],16) for i in (1,3,5)] for h in palette],dtype=np.float32)/255
        colors=rgb[d['labels'].astype(int)-1]
        if clay:colors[:]=[.65,.6,.55]
        positions=mesh.vertices[mesh.faces].reshape(-1,3).astype(np.float32)
        normals=mesh.vertex_normals[mesh.faces].reshape(-1,3).astype(np.float32)
        # glTF vertex colors are linear; inputs here are sRGB filament swatches.
        colors=np.where(colors<=.04045,colors/12.92,((colors+.055)/1.055)**2.4)
        primitive=pyrender.Primitive(positions=positions,normals=normals,color_0=np.repeat(colors,3,axis=0),
            material=pyrender.MetallicRoughnessMaterial(metallicFactor=0,roughnessFactor=.85))
        render_mesh=pyrender.Mesh(primitives=[primitive])
    else:
        mesh=trimesh.load(source,force='scene',process=False).to_geometry()
        if clay:mesh.visual=trimesh.visual.ColorVisuals(mesh,vertex_colors=[175,162,150,255])
        render_mesh=pyrender.Mesh.from_trimesh(mesh,smooth=True)
    low,high=mesh.bounds;center=(low+high)/2;height=float(high[2]-low[2])
    target=center.copy();target[2]=low[2]+height*(.81 if face else .5)
    if face:
        head=mesh.vertices[mesh.vertices[:,2]>low[2]+height*.7]
        target[:2]=(head.min(0)[:2]+head.max(0)[:2])/2
    eye=target+np.array([0,(3 if back else -3)*height,height*.20])
    scale=height*(.23 if face else .62)
    scene=pyrender.Scene(bg_color=[.91,.92,.93,1],ambient_light=[.30,.30,.30])
    scene.add(render_mesh)
    pose=camera_pose(eye,target)
    scene.add(pyrender.OrthographicCamera(xmag=scale*.85,ymag=scale,znear=.1,zfar=height*10),pose=pose)
    for offset,intensity in [([-height,-2*height,2*height],2.2),([height,-height,height],1.1),([0,height,height],1.4)]:
        lightpose=camera_pose(target+offset,target)
        scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=intensity),pose=lightpose)
    renderer=pyrender.OffscreenRenderer(850,1000)
    try:color,_=renderer.render(scene)
    finally:renderer.delete()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(color).save(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    p.add_argument('--palette',nargs='+');p.add_argument('--face',action='store_true');p.add_argument('--clay',action='store_true');p.add_argument('--back',action='store_true')
    a=p.parse_args();render(a.input,a.output,a.palette,a.face,a.clay,a.back)
