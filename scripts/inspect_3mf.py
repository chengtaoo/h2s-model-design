"""Read-only archive checks; never claims a project can slice."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET


def paint_slots(encoded):
    """Decode Bambu/Prusa triangle selection tree without changing geometry."""
    if not encoded:
        return set()
    if len(encoded) > 100000 or any(c not in '0123456789ABCDEF' for c in encoded):
        raise ValueError('Invalid triangle painting encoding')
    nibbles = iter(int(c, 16) for c in reversed(encoded))
    slots = set()
    pending = 1
    try:
        while pending:
            code = next(nibbles)
            pending -= 1
            splits = code & 3
            if splits:
                pending += splits + 1
            else:
                state = code >> 2
                if state == 3:
                    while True:
                        extra = next(nibbles)
                        state += extra
                        if extra != 15:
                            break
                if state:
                    slots.add(state)
        if next(nibbles, None) is not None:
            raise ValueError('Trailing triangle painting data')
    except StopIteration:
        raise ValueError('Truncated triangle painting data') from None
    return slots


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
        painted_slots = set()
        painted_triangles = 0
        for name in names:
            if name.lower().endswith('.model'):
                raw = archive.read(name)
                if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                    raise ValueError('Unexpected XML entities')
                root = ET.fromstring(raw)
                for tri in root.findall('.//{*}triangle'):
                    paint = tri.get('paint_color', '')
                    if paint:
                        painted_triangles += 1
                        painted_slots.update(paint_slots(paint))
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
        effective_slots = []
        metadata_path = 'Metadata/model_settings.config'
        if metadata_path in names:
            raw = archive.read(metadata_path)
            if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                raise ValueError('Unexpected XML entities')
            metadata = ET.fromstring(raw)
            # Object-level extruder metadata can appear only after slicing.
            # Count explicit part mappings, not every metadata element.
            for obj in metadata.findall('object'):
                parent_slots = [m.get('value') for m in obj.findall('metadata') if m.get('key') == 'extruder']
                parent_slot = int(parent_slots[0]) if len(parent_slots) == 1 else None
                for part in obj.findall('part'):
                    slots = [m.get('value') for m in part.findall('metadata') if m.get('key') == 'extruder']
                    explicit = int(slots[0]) if len(slots) == 1 else None
                    part_slots.append(explicit)
                    # Studio may omit a redundant part slot on save. Resolve only
                    # an explicitly recorded immediate parent; never assume slot 1.
                    effective_slots.append(explicit if slots else parent_slot)
        palette_checked = max_filaments is not None
        if palette_checked:
            if not isinstance(colors, list) or not colors or len(colors) > max_filaments:
                raise ValueError('Missing palette or filament count exceeds the requested limit')
            if not effective_slots or any(s is None or not 1 <= s <= len(colors) for s in effective_slots):
                raise ValueError('Missing, unresolved or out-of-range filament assignments; review in Studio')
            if any(s > len(colors) for s in painted_slots):
                raise ValueError('Painted triangle refers to a filament outside the palette')
        return {'archive_readable': True, 'models': models,
                'bambu_project_settings_present': setting_path in names,
                'printer_model_hint': printer, 'printer_preset_hint': preset,
                'nozzle_diameter_hint': nozzle,
                'filament_colors': colors, 'explicit_part_filament_slots': part_slots,
                'effective_part_filament_slots': effective_slots,
                'painted_triangle_count': painted_triangles, 'painted_filament_slots': sorted(painted_slots),
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
