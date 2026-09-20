"""Synthetic, private-data-free checks for the optional portrait backend."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]
AVAILABLE=all(importlib.util.find_spec(name) for name in ('scipy','PIL','manifold3d'))

@unittest.skipUnless(AVAILABLE,'Install requirements-portrait.txt for optional mesh pipeline tests')
class PortraitPipeline(unittest.TestCase):
    def test_repair_preserves_vertices(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from repair_winding import repair
        m=trimesh.creation.icosphere(subdivisions=2);vertices=m.vertices.copy();f=m.faces.copy();f[::3]=f[::3,::-1];m.faces=f
        r=repair(m)
        self.assertGreater(r['faces_reoriented'],0)
        self.assertTrue(m.is_winding_consistent and m.is_watertight and m.volume>0)
        np.testing.assert_array_equal(vertices,m.vertices)

    def test_glb_to_closed_painted_base_without_blender(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix='h2s portrait ') as tmp:
            folder=Path(tmp)
            m=trimesh.creation.icosphere(subdivisions=2)
            m.visual=trimesh.visual.TextureVisuals(uv=np.full((len(m.vertices),2),.5),image=Image.new('RGB',(8,8),(200,160,130)))
            m.export(folder/'source.glb')
            def run(script,*args):
                subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],check=True,capture_output=True,text=True)
            run('extract_glb.py','--input',folder/'source.glb','--output',folder/'extract','--height',50)
            run('prepare_portrait_mesh.py','--input',folder/'extract','--output',folder/'result')
            report=json.loads((folder/'result/geometry-report.json').read_text())
            self.assertTrue(report['watertight'] and report['winding_consistent'])
            self.assertEqual(report['components_after'],1)
            self.assertAlmostEqual(report['dimensions_mm'][2],50,places=2)
            with np.load(folder/'result/print-mesh.npz') as mesh:before=mesh['vertices'].copy()
            run('smooth_palette.py','--project',folder/'result')
            with np.load(folder/'result/print-mesh.npz') as after:np.testing.assert_array_equal(before,after['vertices'])

if __name__=='__main__':unittest.main()
