"""Create a Bambu face-painted project from a validated mesh and an H2S preset project.

The template supplies settings only; its geometry, thumbnails and G-code are discarded.
Painting format: BambuStudio v02.08.02.61 Model.cpp CONST_FILAMENTS (slots 1..4).
Actual slicing must independently validate the resulting project.
"""
import argparse
from io import StringIO
import json
from pathlib import Path
import zipfile
import numpy as np

PAINT_CODES = {1: '4', 2: '8', 3: '0C', 4: '1C'}


def create(mesh_path, template, output, palette, flush_matrix=None):
    if not 1 <= len(palette) <= 4:
        raise ValueError('This writer supports one to four filaments')
    d=np.load(mesh_path,allow_pickle=False)
    vertices,faces,labels=d['vertices'],d['faces'],d['labels']
    if len(faces)!=len(labels) or not len(faces) or not np.isfinite(vertices).all():
        raise ValueError('Invalid mesh arrays')
    if min(labels)<1 or max(labels)>len(palette) or min(faces.ravel())<0 or max(faces.ravel())>=len(vertices):
        raise ValueError('Out-of-range labels or vertices')
    with zipfile.ZipFile(template) as z:
        settings=json.loads(z.read('Metadata/project_settings.config'))
    if settings.get('printer_model')!='Bambu Lab H2S':
        raise ValueError('Template must be a native H2S project')
    if len(settings.get('filament_colour',[]))!=len(palette):
        raise ValueError('Configure the same filament count in the template first')
    if settings['filament_colour']!=palette and flush_matrix is None:
        raise ValueError('Palette changed: provide an explicit purge matrix or recalculate it in Studio; do not reuse unrelated colours')
    if flush_matrix is not None:
        flush=np.asarray(flush_matrix,dtype=float)
        if flush.shape!=(len(palette),len(palette)) or not np.isfinite(flush).all() or (flush<0).any() or (flush>900).any() or np.any(np.diag(flush)!=0):
            raise ValueError('Invalid purge matrix (mm3, NxN, diagonal zero, range 0..900)')
        settings['flush_volumes_matrix']=[str(int(v)) for v in flush.ravel()]
    settings['filament_colour']=palette
    core='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    production='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
    body=StringIO();body.write(f'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xmlns="{core}"><resources><object id="1" type="model"><mesh><vertices>')
    for x,y,z in vertices:body.write(f'<vertex x="{x:.7g}" y="{y:.7g}" z="{z:.7g}"/>')
    body.write('</vertices><triangles>')
    for (v1,v2,v3),slot in zip(faces,labels):body.write(f'<triangle v1="{v1}" v2="{v2}" v3="{v3}" paint_color="{PAINT_CODES[int(slot)]}"/>')
    body.write('</triangles></mesh></object></resources><build/></model>')
    root=f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xmlns="{core}" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="{production}" requiredextensions="p">
<metadata name="Application">BambuStudio-02.08.02.61</metadata><metadata name="BambuStudio:3mfVersion">1</metadata><metadata name="BambuStudio:MmPaintingVersion">0</metadata>
<resources><object id="2" type="model"><components><component p:path="/3D/Objects/object_1.model" objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></components></object></resources>
<build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 170 150 0" printable="1"/></build></model>'''
    metadata=f'''<?xml version="1.0" encoding="UTF-8"?><config>
<object id="2"><metadata key="name" value="AI portrait - painted"/><metadata face_count="{len(faces)}"/>
<metadata key="extruder" value="1"/><part id="1" subtype="normal_part"><metadata key="name" value="Portrait and base"/><metadata key="extruder" value="1"/><metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
<mesh_stat face_count="{len(faces)}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/></part></object>
<plate><metadata key="plater_id" value="1"/><metadata key="plater_name" value="H2S portrait"/><metadata key="locked" value="false"/>
<model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/><metadata key="identify_id" value="1"/></model_instance></plate><assemble/></config>'''
    rels='http://schemas.openxmlformats.org/package/2006/relationships'
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels',f'<Relationships xmlns="{rels}"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/_rels/3dmodel.model.rels',f'<Relationships xmlns="{rels}"><Relationship Target="/3D/Objects/object_1.model" Id="rel1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',root)
        z.writestr('3D/Objects/object_1.model',body.getvalue())
        z.writestr('Metadata/project_settings.config',json.dumps(settings))
        z.writestr('Metadata/model_settings.config',metadata)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',required=True,type=Path);p.add_argument('--template',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--palette',nargs='+',required=True)
    p.add_argument('--flush-matrix',type=Path,help='JSON NxN purge volumes in mm3; required if palette differs from template')
    a=p.parse_args();flush=json.loads(a.flush_matrix.read_text()) if a.flush_matrix else None
    create(a.mesh,a.template,a.output,a.palette,flush)
    print('Project created; actual H2S slicing is still required')
