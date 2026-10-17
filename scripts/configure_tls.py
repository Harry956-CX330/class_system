"""Run on the Docker host after an IP certificate has been issued in /root/class-system-tls.

Adds a small HTTPS proxy and a systemd certificate renewal timer; never modifies the DB.
"""
import json
import os
from pathlib import Path
import subprocess
import argparse

def run(*args):
    return subprocess.check_output(args,text=True).strip()

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port',type=int,default=443)
parser.add_argument('--backend-port',type=int,default=8000)
options=parser.parse_args()
origin='https://8.163.67.49'+('' if options.port==443 else ':'+str(options.port))
root=Path('/root/class-system-tls')
root.mkdir(mode=0o700,exist_ok=True)
certificate=root/'config/live/8.163.67.49/fullchain.pem'
if not certificate.is_file():
    raise SystemExit('Issue the IP certificate before configuring the proxy.')
runtime=json.loads(run('docker','inspect','class-system'))[0]['Image']
nginx=json.loads(run('docker','image','inspect',os.environ.get('NGINX_IMAGE','nginx:stable-alpine')))[0]['RepoDigests'][0]
(root/'webroot/.well-known/acme-challenge').mkdir(parents=True,exist_ok=True)
configuration='''worker_processes 1;
events { worker_connections 256; }
http {
  access_log off;
  error_log /dev/stderr warn;
  client_max_body_size 100m;
  client_body_timeout 120s;
  keepalive_timeout 15;
  server {
    listen 80;
    server_name 8.163.67.49;
    location /.well-known/acme-challenge/ { root /var/www/acme; }
    location / { return 308 https://8.163.67.49$request_uri; }
  }
  server {
    listen 443 ssl;
    server_name 8.163.67.49;
    ssl_certificate /etc/letsencrypt/live/8.163.67.49/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/8.163.67.49/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:TLS:2m;
    ssl_session_tickets off;
    add_header Strict-Transport-Security "max-age=31536000" always;
    location / {
      proxy_pass http://127.0.0.1:8000;
      proxy_http_version 1.1;
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-Proto https;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header Connection "";
      proxy_buffering off;
      proxy_request_buffering off;
      proxy_read_timeout 600s;
      proxy_send_timeout 600s;
    }
  }
}
'''
configuration=configuration.replace('https://8.163.67.49$request_uri',origin+'$request_uri')
configuration=configuration.replace('listen 443 ssl;',f'listen {options.port} ssl;\n    error_page 497 =308 {origin}$request_uri;')
configuration=configuration.replace('proxy_pass http://127.0.0.1:8000;',f'proxy_pass http://127.0.0.1:{options.backend_port};')
(root/'nginx.conf').write_text(configuration)
compose={'services':{'https':{'image':nginx,'container_name':'class-system-https','network_mode':'host',
    'restart':'unless-stopped','cpus':0.15,'mem_limit':'48m','pids_limit':32,
    'security_opt':['no-new-privileges:true'],
    'volumes':[str(root/'nginx.conf')+':/etc/nginx/nginx.conf:ro',str(root/'config')+':/etc/letsencrypt:ro',str(root/'webroot')+':/var/www/acme:ro'],
    'logging':{'driver':'json-file','options':{'max-size':'2m','max-file':'2'}}}}}
(root/'compose.json').write_text(json.dumps(compose,indent=2))
run('docker','compose','-p','sk2441-tls','-f',str(root/'compose.json'),'up','-d')
run('docker','exec','class-system-https','nginx','-t')
run('docker','exec','class-system-https','nginx','-s','reload')
# Use webroot challenges so automatic renewal never interrupts HTTPS or port 80.
renew=root/'renew.sh'
renew.write_text('''#!/bin/sh
set -eu
exec 9>/root/class-system-tls/renew.lock
flock -n 9 || exit 0
docker run --rm --user 0 --memory 128m --cpus 0.2 \\
  -v /root/class-system-tls:/tls -e PYTHONPATH=/tls/lib --entrypoint python '''+runtime+''' \\
  /tls/lib/bin/certbot renew --quiet --no-random-sleep-on-renew --webroot -w /tls/webroot \\
  --config-dir /tls/config --work-dir /tls/work --logs-dir /tls/log "$@"
docker exec class-system-https nginx -s reload
''')
renew.chmod(0o700)
Path('/etc/systemd/system/class-system-certificate.service').write_text('''[Unit]
Description=Renew class system IP TLS certificate
After=docker.service network-online.target
Requires=docker.service
[Service]
Type=oneshot
ExecStart=/root/class-system-tls/renew.sh
TimeoutStartSec=300
''')
Path('/etc/systemd/system/class-system-certificate.timer').write_text('''[Unit]
Description=Check class system certificate every six hours
[Timer]
OnCalendar=*-*-* 00,06,12,18:17:00
RandomizedDelaySec=1800
Persistent=true
[Install]
WantedBy=timers.target
''')
run('systemctl','daemon-reload')
run('systemctl','enable','--now','class-system-certificate.timer')
print(json.dumps({'https':origin,'certificate':str(certificate),'nginx':nginx,'renewal':'class-system-certificate.timer'}))
