"""Package tracked application sources and the verified, prebuilt Vue bundle."""
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
    raise SystemExit('Commit reviewed sources before creating a release.')
bundle = root/'client'/'dist'
info = json.loads((bundle/'build-info.json').read_text(encoding='utf-8'))
if info['revision'] != revision:
    raise SystemExit('Rebuild the frontend after committing; its revision must match HEAD.')
files = subprocess.check_output(['git', 'ls-files', '-z', 'backend', 'Dockerfile'], cwd=root).decode().split('\0')
output = root/'temp'/'releases'/f'class-system-{revision[:12]}.tar.gz'
output.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(output, 'w:gz', compresslevel=6) as archive:
    for name in sorted(filter(None, files)):
        path = root/name
        if path.suffix in {'.db', '.sqlite', '.sqlite3', '.pyc'} or path.name in {'smtp_config.json', 'kdocs_config.json', '.env'}:
            raise SystemExit('Private runtime data must never be packaged: ' + name)
        archive.add(path, arcname=name, recursive=False)
    for path in sorted(bundle.rglob('*')):
        if path.is_file():
            archive.add(path, arcname='frontend-dist/'+path.relative_to(bundle).as_posix())
print(json.dumps({'path':str(output), 'revision':revision, 'bytes':output.stat().st_size,
                  'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2))
