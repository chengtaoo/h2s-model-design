"""Read-only archive checks; never claims a project can slice."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET


def inspect(path, max_filaments=None):
    if max_filaments is not None and max_filaments < 1:
        raise ValueError('max_filaments must be positive')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 20000 or sum(i.file_size for i in entries) > 1024**3:
            raise ValueError('Archive exceeds inspection limits')
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('Duplicate archive entries')
        bad = archive.testzip()
        if bad:
            raise ValueError('CRC failure: ' + bad)
        if '[Content_Types].xml' not in names or '_rels/.rels' not in names:
            raise ValueError('Missing required package structure')
        models = []
        for name in names:
            if name.lower().endswith('.model'):
                raw = archive.read(name)
                if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                    raise ValueError('Unexpected XML entities')
                root = ET.fromstring(raw)
                models.append({'path': name, 'unit': root.get('unit', 'millimeter'),
                               'objects': len(root.findall('.//{*}object')),
                               'triangles': len(root.findall('.//{*}triangle')),
                               'build_items': len(root.findall('.//{*}build/{*}item'))})
        if not models:
            raise ValueError('No 3MF model documents')
        setting_path = 'Metadata/project_settings.config'
        settings = json.loads(archive.read(setting_path)) if setting_path in names else {}
        printer = settings.get('printer_model')
        preset = settings.get('printer_settings_id')
        nozzle = settings.get('nozzle_diameter')
        colors = settings.get('filament_colour', [])
        part_slots = []
        metadata_path = 'Metadata/model_settings.config'
        if metadata_path in names:
            raw = archive.read(metadata_path)
            if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                raise ValueError('Unexpected XML entities')
            metadata = ET.fromstring(raw)
            # Object-level extruder metadata can appear only after slicing.
            # Count explicit part mappings, not every metadata element.
            for part in metadata.iter('part'):
                slots = [m.get('value') for m in part.findall('metadata') if m.get('key') == 'extruder']
                part_slots.append(int(slots[0]) if len(slots) == 1 else None)
        palette_checked = max_filaments is not None
        if palette_checked:
            if not isinstance(colors, list) or not colors or len(colors) > max_filaments:
                raise ValueError('Missing palette or filament count exceeds the requested limit')
            if not part_slots or any(s is None or not 1 <= s <= len(colors) for s in part_slots):
                raise ValueError('Missing, inherited or out-of-range part filament assignments; review in Studio')
        return {'archive_readable': True, 'models': models,
                'bambu_project_settings_present': setting_path in names,
                'printer_model_hint': printer, 'printer_preset_hint': preset,
                'nozzle_diameter_hint': nozzle,
                'filament_colors': colors, 'explicit_part_filament_slots': part_slots,
                'filament_limit_checked': palette_checked, 'max_filaments': max_filaments,
                'gcode_entries': [i.filename for i in entries if i.filename.lower().endswith('.gcode') and i.file_size],
                'slice_verified': False,
                'limitations': ['Metadata hints are not compatibility proof',
                                'Transforms, part mapping and geometry are not validated here',
                                'Actual slicing and layer review required']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--report', required=True)
    parser.add_argument('--max-filaments', type=int, help='Require an explicit palette and part assignments within this limit')
    args = parser.parse_args()
    try:
        report = inspect(args.project, args.max_filaments)
        code = 0
    except Exception as exc:
        report = {'archive_readable': False, 'slice_verified': False, 'error': str(exc)}
        code = 1
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
