import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
paint=load('painted_3mf');qa=load('inspect_3mf');api=load('tripo_api')

class PaintTests(unittest.TestCase):
    def test_leaf_and_split_decoding(self):
        for slot,code in paint.PAINT_CODES.items():self.assertEqual(qa.paint_slots(code),{slot})
        self.assertEqual(qa.paint_slots('480C1C3'),{1,2,3,4})
        for code in ('G','C','444'):
            with self.assertRaises(ValueError):qa.paint_slots(code)

    def test_painted_cube_preserves_mesh_and_rejects_hidden_fifth_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);mesh=trimesh.creation.box();labels=np.arange(12)%4+1
            np.savez(p/'mesh.npz',vertices=mesh.vertices,faces=mesh.faces,labels=labels)
            with zipfile.ZipFile(p/'template.3mf','w') as z:
                z.writestr('Metadata/project_settings.config',json.dumps({'printer_model':'Bambu Lab H2S','filament_colour':['#000000']*4}))
                z.writestr('old-private-photo.png',b'never copy')
            palette=['#111111','#aaaaaa','#445544','#aa3333']
            with self.assertRaises(ValueError):paint.create(p/'mesh.npz',p/'template.3mf',p/'new.3mf',palette)
            paint.create(p/'mesh.npz',p/'template.3mf',p/'new.3mf',palette,[[0 if i==j else 400 for j in range(4)] for i in range(4)])
            r=qa.inspect(p/'new.3mf',4)
            self.assertEqual(r['painted_filament_slots'],[1,2,3,4]);self.assertEqual(r['painted_triangle_count'],12)
            with zipfile.ZipFile(p/'new.3mf') as z:
                self.assertNotIn('old-private-photo.png',z.namelist())
                records={n:z.read(n) for n in z.namelist()}
            records['3D/Objects/object_1.model']=records['3D/Objects/object_1.model'].replace(b'paint_color="1C"',b'paint_color="2C"')
            with zipfile.ZipFile(p/'bad.3mf','w') as z:
                for n,data in records.items():z.writestr(n,data)
            with self.assertRaises(ValueError):qa.inspect(p/'bad.3mf',4)

    def test_region_and_no_secret_in_error(self):
        with patch.dict(os.environ,{'TRIPO_API_KEY':'test-secret'}):
            cn=api.Tripo('cn');ov=api.Tripo('global')
            self.assertEqual(cn.base,'https://openapi.tripo3d.com/v3')
            self.assertEqual(ov.base,'https://openapi.tripo3d.ai/v3')
            from urllib.error import HTTPError
            with patch('urllib.request.urlopen',side_effect=HTTPError('secret-url',401,'test-secret',None,None)):
                with self.assertRaises(RuntimeError) as caught:cn.request('/account/balance')
            self.assertNotIn('test-secret',str(caught.exception));self.assertNotIn('secret-url',str(caught.exception))

if __name__=='__main__':unittest.main()
