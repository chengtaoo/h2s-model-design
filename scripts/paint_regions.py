"""Apply explicit millimetre-space colour corrections to an existing print mesh."""
import argparse,json
from pathlib import Path
import numpy as np


def apply(project,config):
    project=Path(project);spec=json.loads(Path(config).read_text(encoding='utf-8'))
    with np.load(project/'print-mesh.npz',allow_pickle=False) as d:arrays={k:d[k] for k in d.files}
    centers=arrays['vertices'][arrays['faces']].mean(axis=1);labels=arrays['labels'].copy();changes=[]
    for region in spec['regions']:
        box=np.asarray(region['bounds'],float)
        if box.shape!=(6,) or not np.isfinite(box).all() or (box[:3]>box[3:]).any():raise ValueError('Invalid correction box')
        if region['to'] not in (1,2,3,4):raise ValueError('Invalid filament')
        mask=((centers>=box[:3])&(centers<=box[3:])).all(axis=1)&np.isin(labels,region['from'])
        changes.append({'name':region.get('name','region'),'changed_faces':int((mask&(labels!=region['to'])).sum())})
        labels[mask]=region['to']
    arrays['labels']=labels;np.savez_compressed(project/'print-mesh.npz',**arrays)
    report=json.loads((project/'geometry-report.json').read_text());report['face_counts_by_slot']=np.bincount(labels,minlength=5)[1:].tolist()
    report['paint_corrections']={'regions':spec['regions'],'changes':changes,'vertices_moved':0}
    (project/'geometry-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return changes


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',required=True);p.add_argument('--config',required=True);a=p.parse_args();print(json.dumps(apply(a.project,a.config)))
