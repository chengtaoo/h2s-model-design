"""Extract a textured GLB into millimetres without Blender (Tripo uses glTF Y-up)."""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh


def extract(source, output, height=150, rotate_z=-90):
    if not 20 <= height <= 300:
        raise ValueError('Choose a portrait height between 20 and 300 mm')
    scene=trimesh.load(source,force='scene',process=False)
    if len(scene.graph.nodes_geometry)!=1:
        raise ValueError('Requires one textured mesh; inspect multiple objects before consolidating')
    mesh=scene.to_geometry()
    if mesh.visual.kind!='texture' or mesh.visual.uv is None:
        raise ValueError('GLB must contain UV texture coordinates')
    material=mesh.visual.material
    image=getattr(material,'baseColorTexture',None)
    if image is None:image=getattr(material,'image',None)
    if image is None:raise ValueError('No base-color texture found')
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
    low,high=mesh.bounds
    mesh.apply_translation([-float((low[0]+high[0])/2),-float((low[1]+high[1])/2),-float(low[2])])
    mesh.apply_scale(height/(high[2]-low[2]))
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(rotate_z),[0,0,1]))
    uv=mesh.visual.uv[mesh.faces].mean(axis=1)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    image.save(output/'base-color.png')
    np.savez(output/'surface.npz',vertices=np.asarray(mesh.vertices,np.float32),faces=np.asarray(mesh.faces,np.int32),uv=uv.astype(np.float32))
    mesh.export(output/'scaled-original.glb')
    report={'height_mm':height,'rotate_z':rotate_z,'dimensions_mm':mesh.extents.tolist(),'faces':len(mesh.faces),'backend':'trimesh; no Blender'}
    (output/'extraction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--height',type=float,default=150);p.add_argument('--rotate-z',type=float,default=-90)
    a=p.parse_args();print(json.dumps(extract(a.input,a.output,a.height,a.rotate_z)))
