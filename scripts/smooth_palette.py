"""Suppress tiny colour speckles on a labelled mesh without modifying geometry."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree


def smooth(project, radius=.45, passes=2):
    project=Path(project)
    with np.load(project/'print-mesh.npz',allow_pickle=False) as d:arrays={k:d[k] for k in d.files}
    labels=arrays['labels'].copy();before=labels.copy()
    c=arrays['vertices'][arrays['faces']].mean(axis=1)
    distances,near=cKDTree(c).query(c,k=13,workers=4)
    valid=distances<=radius
    for _ in range(passes):
        counts=np.stack([((labels[near]==slot)&valid).sum(axis=1) for slot in range(1,5)],axis=1)
        # A strong local majority only; small well-defined details survive.
        change=(counts.max(axis=1)>=np.maximum(5,np.ceil(valid.sum(axis=1)*.75)))
        labels[change]=counts.argmax(axis=1)[change]+1
    arrays['labels']=labels;np.savez_compressed(project/'print-mesh.npz',**arrays)
    report=json.loads((project/'geometry-report.json').read_text())
    report['face_counts_by_slot']=np.bincount(labels,minlength=5)[1:].tolist()
    report['palette_smoothing']={'radius_mm':radius,'passes':passes,'changed_faces':int(np.count_nonzero(before!=labels)),'vertices_moved':0}
    (project/'geometry-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report['palette_smoothing']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',required=True,type=Path);p.add_argument('--radius',type=float,default=.45);p.add_argument('--passes',type=int,default=2)
    a=p.parse_args();print(json.dumps(smooth(a.project,a.radius,a.passes)))
