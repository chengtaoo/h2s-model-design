"""Install this skill and its check dependencies without global Python changes."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent
FILES = ['SKILL.md', 'README.md', 'INSTALL.md', 'LICENSE', 'requirements-check.txt',
         'requirements-cad.txt', 'requirements-portrait.txt', 'agents', 'references', 'scripts', 'examples', 'tests']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, help='Skill directory; defaults to CODEX_HOME/skills/h2s-model-design')
    parser.add_argument('--with-cad', action='store_true', help='Also install optional CadQuery backend')
    parser.add_argument('--with-portrait', action='store_true', help='Install Tripo GLB processing and preview dependencies; Blender is not needed')
    parser.add_argument('--skip-deps', action='store_true', help='Copy only; for offline/manual dependency installation')
    parser.add_argument('--update', action='store_true', help='Explicitly allow updating existing skill files')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Use Python 3.11 or newer; Python 3.11 is the tested baseline')
    codex = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    target = (args.destination or codex / 'skills' / 'h2s-model-design').expanduser().resolve()
    if target == ROOT:
        parser.error('Destination must differ from the downloaded source directory')
    if target.exists() and not args.update:
        parser.error('Destination already exists. Use --update only to update that skill, or choose another destination')
    if target.exists() and not (target / 'SKILL.md').is_file():
        parser.error('Existing destination is not a skill directory; choose another destination')
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, target / name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(source, target / name)
    if args.skip_deps:
        print('Skill copied. Dependencies skipped; follow INSTALL.md before modeling.')
        return 0
    env = target / '.venv'
    venv.EnvBuilder(with_pip=True).create(env)
    python = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    requirements = target / ('requirements-cad.txt' if args.with_cad else 'requirements-check.txt')
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
    if args.with_portrait:
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(target/'requirements-portrait.txt')], check=True)
    subprocess.run([str(python), '-m', 'unittest', 'discover', '-s', str(target / 'tests')], check=True)
    if args.with_cad:
        subprocess.run([str(python), '-c', "import cadquery as cq; assert cq.Workplane('XY').box(10,10,10).val().isValid(); print('CAD OK')"], check=True)
    subprocess.run([str(python), str(target / 'scripts/check_environment.py')], check=True)
    print('Installed and check tests passed. Modeling backend and Bambu Studio must also be available.')
    print('Start a new task and invoke $h2s-model-design. No printer connection is required.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as exc:
        print('Installation incomplete: ' + str(exc), file=sys.stderr)
        sys.exit(1)
