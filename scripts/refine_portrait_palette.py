"""Optional warm-skin/olive-clothing palette recipe; inspect preview before printing.

This is a color-family heuristic, not a general semantic segmentation model.
Use --lip-box only after inspecting actual mesh coordinates; no photo is bundled.
"""
import numpy as np,json,argparse
from pathlib import Path
from scipy.spatial import cKDTree
import trimesh
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path,required=True)
parser.add_argument('--lip-box',type=float,nargs=6,metavar=('XMIN','YMIN','ZMIN','XMAX','YMAX','ZMAX'))
parser.add_argument('--neutral-below-z',type=float,default=None,help='Optional chair region: map light neutral details to black below this height')
args=parser.parse_args();p=args.project
d=np.load(p/'print-mesh.npz');v=d['vertices'];f=d['faces'];rgb=d['rgb'].astype(float);c=v[f].mean(1)
report=json.loads((p/'geometry-report.json').read_text())
r,g,b=rgb.T;mx=rgb.max(1);mn=rgb.min(1)
labels=np.ones(len(f),np.uint8)
skin=(b/(g+1)>.75)&(r/(g+1)<1.55)&(mx>48)
labels[skin]=2
black=(mx<38)|((mx-mn)/(mx+1)<.16)&(mx<125)
labels[black]=3
red=(r>g*1.48)&(r>b*1.25)&(r>40)
if args.lip_box:
    box=np.array(args.lip_box);red&=((c>=box[:3])&(c<=box[3:])).all(1)
labels[red]=4
if args.neutral_below_z is not None:labels[(labels==2)&(c[:,2]<args.neutral_below_z)]=3
labels[c[:,2]<report['base_height_mm']+.01]=1
# Smooth local texture noise while preserving real small lip and eye regions.
tree=cKDTree(c);_,near=tree.query(c,k=13,workers=4)
for _ in range(2):
    counts=np.stack([(labels[near]==s).sum(1) for s in (1,2,3,4)],axis=1)
    best=counts.argmax(1)+1
    change=counts.max(1)>=9
    labels[change]=best[change]
np.savez_compressed(p/'print-mesh.npz',vertices=v,faces=f,labels=labels,rgb=rgb.astype(np.uint8))
report['face_counts_by_slot']=np.bincount(labels,minlength=5)[1:].tolist();report['color_method']='Illumination-tolerant warm/neutral ratios plus two bounded local majority passes; requires visual review'
report['palette_recipe']={'lip_box':args.lip_box,'neutral_below_z':args.neutral_below_z}
(p/'geometry-report.json').write_text(json.dumps(report,indent=2));print(report['face_counts_by_slot'])
