"""Fail deployment when a host mount conceals the verified frontend bundle."""
import hashlib
import json
import os
from pathlib import Path


def inspect_build(root, revision=None):
    root = Path(root).resolve()
    revision = revision or os.environ.get('APP_REVISION', 'unknown')
    result = {"ready": False, "version": "unknown", "revision": "unknown"}
    try:
        info = json.loads((root / 'build-info.json').read_text(encoding='utf-8'))
        result.update({key: info[key] for key in ('version', 'revision', 'built_at')})
        if revision != 'unknown' and info['revision'] != revision:
            raise ValueError('Frontend and backend revisions do not match')
        if hashlib.sha256((root / 'index.html').read_bytes()).hexdigest() != info['index_sha256']:
            raise ValueError('Frontend index does not match its build manifest')
        if not info['assets']:
            raise ValueError('No frontend entry assets')
        for name, digest in info['assets'].items():
            path = (root / name.lstrip('/')).resolve()
            if not name.startswith('/assets/') or not path.is_relative_to(root):
                raise ValueError('Invalid frontend asset path')
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Frontend assets do not match their build manifest')
        manifest = json.loads((root / 'manifest.webmanifest').read_text(encoding='utf-8'))
        if manifest.get('name') != 'sk2441班务':
            raise ValueError('Unexpected app manifest')
        result['ready'] = True
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['error'] = str(error)
    return result
