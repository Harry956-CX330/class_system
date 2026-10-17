"""Run on the Docker host after uploading a release. Never migrates or replaces its database."""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path


def run(*args, capture=False):
    result = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def inspect(name):
    return json.loads(run('docker', 'inspect', name, capture=True))[0]


def schema_digest(database):
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as connection:
        rows = connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
    return hashlib.sha256(json.dumps(rows, ensure_ascii=True).encode()).hexdigest()


def wait_ready(port, revision):
    url = f'http://127.0.0.1:{port}'
    last = None
    for _ in range(45):
        try:
            with urllib.request.urlopen(url+'/api/health', timeout=4) as response:
                health = json.load(response)
            if health['revision'] != revision or not health['frontend']['ready']:
                raise RuntimeError('The backend and frontend build identifiers must both match.')
            with urllib.request.urlopen(url+'/manifest.webmanifest', timeout=4) as response:
                if json.load(response)['name'] != 'sk2441班务':
                    raise RuntimeError('Unexpected manifest')
            return health
        except Exception as error:
            last = error
            time.sleep(1)
    raise RuntimeError('Application health check failed: ' + str(last))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True, help='Extracted release directory')
    parser.add_argument('--source', type=Path, required=True, help='Existing backend directory with data/data.db and static/uploads')
    parser.add_argument('--old-container', required=True)
    parser.add_argument('--deployment-root', type=Path, default=Path('/root/class-system-deployments'))
    options = parser.parse_args()
    source, release = options.source.resolve(), options.release.resolve()
    info = json.loads((release/'frontend-dist'/'build-info.json').read_text())
    revision = info['revision']
    if not re.fullmatch('[a-f0-9]{40}', revision):
        raise SystemExit('A full Git commit revision is required.')
    database, uploads = source/'data'/'data.db', source/'static'/'uploads'
    if not database.is_file() or not uploads.is_dir():
        raise SystemExit('The existing database and upload directory must already exist.')
    old = inspect(options.old_container)
    if not old['State']['Running']:
        raise SystemExit('The existing service must be running before rollout.')
    deployment = options.deployment_root/revision[:12]
    deployment.mkdir(parents=True, exist_ok=True, mode=0o700)
    deployment.chmod(0o700)
    old_state = deployment/'previous-container.json'
    old_state.write_text(json.dumps(old))
    old_state.chmod(0o600)
    before = schema_digest(database)
    image = 'class-system:'+revision[:12]
    # Prebuilt target avoids installing Node or compiling Vue on the small host.
    # Legacy builders traverse earlier stages too, so derive a runtime-only Dockerfile.
    dockerfile = (release/'Dockerfile').read_text()
    prebuilt_file = release/'Dockerfile.prebuilt'
    prebuilt_file.write_text(dockerfile[dockerfile.index('FROM python:'):dockerfile.index('FROM runtime AS production')])
    run('docker', 'build', '--file', str(prebuilt_file), '--target', 'prebuilt', '--build-arg', 'APP_REVISION='+revision,
        '--tag', image, str(release))
    network = 'class-system-private'
    if subprocess.run(['docker', 'network', 'inspect', network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        run('docker', 'network', 'create', network)
    archives = options.deployment_root/'archives'
    archives.mkdir(exist_ok=True)
    for directory in (source/'data', uploads, archives):
        os.chown(directory, 10001, 10001)
        for path in directory.rglob('*'):
            if not path.is_symlink():
                os.chown(path, 10001, 10001)
    for name in ('smtp_config.json', 'kdocs_config.json'):
        path = source/name
        if not path.is_file():
            path.write_text('{}')
        os.chown(path, 10001, 10001)
        path.chmod(0o600)
    environment = {
        'TZ':'Asia/Shanghai', 'PUBLIC_BASE_URL':'http://8.163.67.49:8000',
        'CORS_ORIGINS':'http://8.163.67.49:8000', 'DATA_DIR':'/app/data',
        'DATABASE_URL':'sqlite:////app/data/data.db', 'FRONTEND_DIST':'/app/static/dist',
        'TEMP_DIR':'/app/archive-tmp', 'SMTP_CONFIG_PATH':'/app/settings/smtp_config.json',
        'KDOCS_CONFIG_PATH':'/app/settings/kdocs_config.json', 'QQ_UPLOAD_ROOT':'/app/class-uploads',
        'MAX_UPLOAD_MB':'100','MAX_CONCURRENT_UPLOADS':'2','MAX_CONCURRENT_DOWNLOADS':'4',
        'MAX_CONCURRENT_ARCHIVES':'1','MAX_ARCHIVE_MB':'2048','MIN_FREE_DISK_MB':'256',
        'THREAD_TOKENS':'8','DOWNLOAD_KIB_PER_SECOND':'280',
    }
    # Preserve explicitly configured secrets and deployment allowlists without printing them.
    inherited = dict(value.split('=',1) for value in old['Config'].get('Env',[]) if '=' in value)
    for key in ('SECRET_KEY', 'SMTP_ALLOWED_HOSTS', 'QQ_ALLOWED_HOSTS'):
        if inherited.get(key):
            environment[key] = inherited[key]
    env_file = deployment/'app.env'
    if any('\n' in value or '\r' in value for value in environment.values()):
        raise SystemExit('Deployment environment values must be single-line.')
    env_file.write_text(''.join(f'{key}={value}\n' for key,value in environment.items()))
    env_file.chmod(0o600)
    volumes = [f'{source / "data"}:/app/data', f'{uploads}:/app/static/uploads',
               f'{archives}:/app/archive-tmp', f'{source / "smtp_config.json"}:/app/settings/smtp_config.json',
               f'{source / "kdocs_config.json"}:/app/settings/kdocs_config.json']
    candidate = 'class-system-check-'+revision[:12]
    try:
        command = ['docker','run','-d','--rm','--name',candidate,'--memory','512m','--cpus','1.5',
                   '--pids-limit','128','--cap-drop','ALL','--security-opt','no-new-privileges:true',
                   '--env-file',str(env_file),'-e','DATABASE_URL=sqlite:///file:/app/data/data.db?mode=ro&uri=true',
                   '-p','127.0.0.1:18000:8000']
        for volume in volumes:
            command += ['-v', volume+(':ro' if not volume.endswith('/app/archive-tmp') else '')]
        command.append(image)
        run(*command)
        health = wait_ready(18000, revision)
        print('Candidate verified: '+json.dumps(health), flush=True)
    finally:
        subprocess.run(['docker','stop','-t','10',candidate], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    compose = {
        'services': {'app': {'image': image, 'container_name':'class-system',
            'ports':['8000:8000'], 'cpus':1.5, 'mem_limit':'512m', 'pids_limit':128,
            'env_file':[str(env_file)], 'volumes':volumes,
            'cap_drop':['ALL'], 'security_opt':['no-new-privileges:true'], 'restart':'unless-stopped',
            'logging':{'driver':'json-file','options':{'max-size':'5m','max-file':'3'}},
            'networks':{network:{'aliases':['class-system']}}}},
        'networks':{network:{'external':True}}
    }
    compose_path = deployment/'compose.json'
    compose_path.write_text(json.dumps(compose, indent=2))
    compose_path.chmod(0o600)
    # A unique project prevents Compose replacing the renamed rollback container.
    project = 'sk2441-'+revision[:12]
    run('docker','compose','-p',project,'-f',str(compose_path),'config','--quiet')
    run('docker','stop','-t','30',options.old_container)
    old_name = options.old_container
    renamed = False
    if old_name == 'class-system':
        run('docker','rename',old_name,'class-system-before-'+revision[:12])
        old_name = 'class-system-before-'+revision[:12]
        renamed = True
    try:
        # A consistent final snapshot after writes stop, immediately before switching service.
        with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as connection:
            with sqlite3.connect(deployment/'data-before.db') as destination:
                connection.backup(destination)
                if destination.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Database backup integrity check failed')
        (deployment/'data-before.db').chmod(0o600)
        run('docker','compose','-p',project,'-f',str(compose_path),'up','-d','app')
        health = wait_ready(8000, revision)
        after = schema_digest(database)
        if after != before:
            raise RuntimeError('Unexpected database schema change')
        report = {'revision':revision, 'frontend':health['frontend'], 'schema_unchanged':True,
                  'schema_sha256':after, 'database':str(database), 'uploads':str(uploads),
                  'previous_container':old_name, 'image':image, 'compose':str(compose_path)}
        (deployment/'deployment-report.json').write_text(json.dumps(report, indent=2))
        rollback = deployment/'rollback.sh'
        import shlex
        rollback.write_text('#!/bin/sh\nset -eu\ndocker stop class-system\n'+
                            ('docker rename class-system class-system-failed-'+revision[:12]+'\ndocker rename '+shlex.quote(old_name)+' class-system\n' if renamed else '')+
                            'docker start '+shlex.quote(options.old_container)+'\n')
        rollback.chmod(0o700)
        print('DEPLOYED '+json.dumps(report), flush=True)
    except Exception:
        subprocess.run(['docker','stop','-t','10','class-system'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if renamed:
            run('docker','rename','class-system','class-system-failed-'+revision[:12])
            run('docker','rename',old_name,options.old_container)
        run('docker','start',options.old_container)
        raise


if __name__ == '__main__':
    main()
