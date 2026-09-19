"""Portable, read-only dependency discovery. Does not execute applications."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys

SKILL_ROOT = Path(__file__).resolve().parent.parent
APPS = {
    'bambu_studio': ('BAMBU_STUDIO_EXE', ['bambu-studio', 'BambuStudio', 'bambu-studio.exe']),
    'blender': ('BLENDER_EXE', ['blender', 'blender.exe']),
    'openscad': ('OPENSCAD_EXE', ['openscad', 'openscad.exe']),
}


def inspect(config_path=None):
    config = {}
    base = SKILL_ROOT
    if config_path:
        config_path = Path(config_path).resolve()
        config = json.loads(config_path.read_text(encoding='utf-8-sig'))
        base = config_path.parent
    apps = {}
    for name, (env, candidates) in APPS.items():
        raw = config.get(name) or os.environ.get(env)
        resolved = None
        source = 'PATH'
        if raw:
            source = 'config' if config.get(name) else env
            candidate = Path(os.path.expandvars(raw)).expanduser()
            if not candidate.is_absolute():
                candidate = (base if source == 'config' else Path.cwd()) / candidate
            if candidate.is_file():
                resolved = str(candidate.resolve())
            elif shutil.which(raw):
                resolved = shutil.which(raw)
        else:
            resolved = next((shutil.which(c) for c in candidates if shutil.which(c)), None)
        apps[name] = {'found': resolved is not None, 'path': resolved, 'source': source}
    packages = {}
    for name in ('numpy', 'trimesh', 'cadquery'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {'python': sys.version.split()[0], 'packages': packages, 'applications': apps,
            'mesh_dependencies_found': all(packages[n] for n in ('numpy', 'trimesh')),
            'notes': ['Discovery only; application launch and slicing are not tested',
                      'Blender bundled Python is separate from this Python environment',
                      'Absolute paths in this report are local diagnostics, not portable settings']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Optional JSON; relative app paths resolve beside this file')
    parser.add_argument('--report', help='Optional output report')
    args = parser.parse_args()
    try:
        report = inspect(args.config)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 1
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        dest = Path(args.report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data, encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
