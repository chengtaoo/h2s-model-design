"""Package tracked source files only. Run from any directory inside a Git checkout."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    files = [name for name in files if name]
    if 'SKILL.md' not in files:
        raise SystemExit('Stage the release sources in Git before packaging')
    args.output.mkdir(parents=True, exist_ok=True)
    dest = args.output / 'h2s-model-design.zip'
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(ROOT / name, 'h2s-model-design/' + name)
    with zipfile.ZipFile(dest) as archive:
        assert archive.testzip() is None
    checksum = hashlib.sha256(dest.read_bytes()).hexdigest()
    (args.output / 'SHA256SUMS.txt').write_text(checksum + '  ' + dest.name + '\n', encoding='utf-8')
    print(f'Packaged {len(files)} tracked files; SHA256 {checksum}')


if __name__ == '__main__':
    main()
