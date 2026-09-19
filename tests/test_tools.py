import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile
import trimesh

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

meshqa, archiveqa, envqa = (load(n) for n in ('check_mesh', 'inspect_3mf', 'check_environment'))

class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='h2s test ')
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def mesh(self, shape, name='part.stl'):
        path = self.root / name
        shape.export(path)
        return meshqa.inspect(path)
    def archive(self, settings=False):
        path = self.root / 'fixture.3mf'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
            z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            z.writestr('3D/3dmodel.model', '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter"><resources/><build/></model>')
            if settings:
                z.writestr('Metadata/project_settings.config', json.dumps({'printer_model':'Bambu Lab H2S','nozzle_diameter':['0.4']}))
        return archiveqa.inspect(path)
    def test_closed_mesh_dimensions(self):
        r = self.mesh(trimesh.creation.box(extents=[20,30,40]), '中文模型.stl')
        self.assertTrue(r['basic_checks_pass'])
        self.assertEqual(r['dimensions_mm'], [20,30,40])
    def test_open_mesh(self):
        m = trimesh.creation.box()
        m.update_faces(list(range(11)))
        self.assertFalse(self.mesh(m)['checks']['watertight'])
    def test_oversize(self):
        self.assertFalse(self.mesh(trimesh.creation.box(extents=[341,20,20]))['basic_checks_pass'])
    def test_generic_archive_not_native_project(self):
        r = self.archive()
        self.assertFalse(r['bambu_project_settings_present'])
        self.assertFalse(r['slice_verified'])
    def test_metadata_not_slicing_proof(self):
        r = self.archive(True)
        self.assertTrue(r['bambu_project_settings_present'])
        self.assertFalse(r['slice_verified'])
    def test_corrupt_archive(self):
        path = self.root / 'bad.3mf'
        path.write_bytes(b'not a zip')
        with self.assertRaises(zipfile.BadZipFile):
            archiveqa.inspect(path)
    def palette_archive(self, slots, count=4):
        self.archive(True)
        path = self.root / 'fixture.3mf'
        # Rebuild the settings entry instead of making a duplicate ZIP entry.
        with zipfile.ZipFile(path) as z:
            entries = {n:z.read(n) for n in z.namelist()}
        entries['Metadata/project_settings.config'] = json.dumps({'filament_colour':['#112233']*count})
        entries['Metadata/model_settings.config'] = '<config><object><metadata key="extruder" value="1"/>' + ''.join(
            '<part>' + (f'<metadata key="extruder" value="{s}"/>' if s is not None else '') + '</part>' for s in slots) + '</object></config>'
        with zipfile.ZipFile(path, 'w') as z:
            for name, data in entries.items():
                z.writestr(name, data)
        return path
    def test_many_parts_four_filaments(self):
        r = archiveqa.inspect(self.palette_archive([1,1,2,3,2,2,4]), 4)
        self.assertEqual(r['explicit_part_filament_slots'], [1,1,2,3,2,2,4])
        self.assertTrue(r['filament_limit_checked'])
        self.assertFalse(r['slice_verified'])
    def test_palette_over_budget(self):
        with self.assertRaises(ValueError):
            archiveqa.inspect(self.palette_archive([1,2,3,4,5], 5), 4)
    def test_missing_and_invalid_part_assignments(self):
        for slots in ([None], [0], [5], []):
            with self.subTest(slots=slots), self.assertRaises(ValueError):
                archiveqa.inspect(self.palette_archive(slots), 4)
    def test_generic_archive_cannot_verify_palette(self):
        self.archive()
        with self.assertRaises(ValueError):
            archiveqa.inspect(self.root / 'fixture.3mf', 4)
    def test_config_relative_path(self):
        app = self.root / 'tools' / 'placeholder.exe'
        app.parent.mkdir()
        app.write_bytes(b'discovery only, never executed')
        config = self.root / 'tools.local.json'
        config.write_text(json.dumps({'bambu_studio':'tools/placeholder.exe'}))
        with patch.dict(os.environ, {'BAMBU_STUDIO_EXE':'invalid-override'}):
            r = envqa.inspect(config)
        self.assertEqual(r['applications']['bambu_studio']['path'], str(app.resolve()))
    def test_installer_copy_and_explicit_update(self):
        destination = self.root / '中文 skill'
        command = [sys.executable, str(ROOT / 'scripts/install.py'), '--skip-deps', '--destination', str(destination)]
        first = subprocess.run(command, cwd=self.root, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue((destination / 'SKILL.md').is_file())
        self.assertTrue((destination / 'examples/make_cad_tray.py').is_file())
        self.assertFalse((destination / '.git').exists())
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(command + ['--update'], capture_output=True).returncode, 0)

if __name__ == '__main__':
    unittest.main()
