import bpy,sys,argparse,json
import numpy as np
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.project=a.project.resolve()
out=a.project/'previews';out.mkdir(exist_ok=True)
d=np.load(a.project/'print-mesh.npz');spec=json.loads((a.project/'geometry-report.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
me=bpy.data.meshes.new('Preserved AI geometry');me.from_pydata(d['vertices'].tolist(),[],d['faces'].tolist());me.update()
o=bpy.data.objects.new('Four-color portrait',me);bpy.context.collection.objects.link(o)
for h in spec['palette']:
    mat=bpy.data.materials.new(h);mat.use_nodes=True
    rgb=[int(h[i:i+2],16)/255 for i in (1,3,5)];lin=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*lin,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.68;me.materials.append(mat)
me.polygons.foreach_set('material_index',(d['labels'].astype(int)-1))
for f in me.polygons:f.use_smooth=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20
scene.render.resolution_x=850;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.32,.32,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
scene.view_settings.view_transform='Standard'
for name,loc,power,size in [('Key',(-180,-220,250),1000000,180),('Fill',(180,-120,180),700000,200),('Rim',(0,150,250),1200000,160)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=loc;obj.rotation_euler=(Vector((0,0,80))-obj.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
clay=bpy.data.materials.new('Clay');clay.diffuse_color=(.5,.42,.32,1)
for name,loc,target,scale in [('four-color',(0,-380,130),(0,0,75),190),('face',(0,-380,140),(0,0,115),85),('clay-face',(0,-380,140),(0,0,115),85),('back',(0,380,140),(0,0,75),190)]:
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.view_layers[0].material_override=clay if name=='clay-face' else None
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
scene.view_layers[0].material_override=None
cam.location=(0,-380,130);cam.rotation_euler=(Vector((0,0,75))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=190
bpy.ops.wm.save_as_mainfile(filepath=str(a.project/'portrait-four-color.blend'))
