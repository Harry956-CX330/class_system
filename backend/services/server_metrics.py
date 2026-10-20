"""Read-only Linux host/container metrics with explicit unavailable values elsewhere."""
import os
import shutil
import threading
import time
from pathlib import Path
from config import DATA_DIR

_lock=threading.Lock()
_cached=None
_previous=None


def read(path):
    try:return Path(path).read_text().strip()
    except OSError:return ''


def metrics():
    global _cached,_previous
    now=time.monotonic()
    with _lock:
        if _cached and now-_cached['sample_at']<2:return _cached['value']
        memory={}
        for line in read('/proc/meminfo').splitlines():
            parts=line.split()
            if len(parts)>1 and parts[1].isdigit():memory[parts[0].rstrip(':')]=int(parts[1])*1024
        total=memory.get('MemTotal');available=memory.get('MemAvailable')
        usage=read('/sys/fs/cgroup/memory.current') or read('/sys/fs/cgroup/memory/memory.usage_in_bytes')
        limit=read('/sys/fs/cgroup/memory.max') or read('/sys/fs/cgroup/memory/memory.limit_in_bytes')
        cpu_limit=None
        quota=read('/sys/fs/cgroup/cpu.max').split()
        if len(quota)==2 and quota[0].isdigit():cpu_limit=int(quota[0])/int(quota[1])
        elif read('/sys/fs/cgroup/cpu/cpu.cfs_quota_us').isdigit():
            cpu_limit=int(read('/sys/fs/cgroup/cpu/cpu.cfs_quota_us'))/max(1,int(read('/sys/fs/cgroup/cpu/cpu.cfs_period_us') or '100000'))
        cpu=0
        for line in read('/sys/fs/cgroup/cpu.stat').splitlines():
            if line.startswith('usage_usec '):cpu=int(line.split()[1])/1000000
        if not cpu:
            value=read('/sys/fs/cgroup/cpuacct/cpuacct.usage')
            if value.isdigit():cpu=int(value)/1000000000
        received=sent=0
        for line in read('/proc/net/dev').splitlines():
            if ':' not in line:continue
            name,values=line.split(':',1);parts=values.split()
            if name.strip()!='lo' and len(parts)>8:received+=int(parts[0]);sent+=int(parts[8])
        cpu_percent=rx=tx=None
        if _previous and now>_previous['time']:
            elapsed=now-_previous['time']
            cpu_percent=round(max(0,cpu-_previous['cpu'])/elapsed/max(cpu_limit or os.cpu_count() or 1,.01)*100,1) if cpu else None
            rx=round(max(0,received-_previous['rx'])/elapsed);tx=round(max(0,sent-_previous['tx'])/elapsed)
        _previous={'time':now,'cpu':cpu,'rx':received,'tx':sent}
        disk=shutil.disk_usage(DATA_DIR)
        value={'host_cpus':os.cpu_count(),'container_cpu_limit':cpu_limit,'container_cpu_percent':cpu_percent,
               'host_memory_total':total,'host_memory_available':available,
               'container_memory_used':int(usage) if usage.isdigit() else None,
               'container_memory_limit':int(limit) if limit.isdigit() and int(limit)<1<<60 else None,
               'disk_total':disk.total,'disk_free':disk.free,'network_receive_bytes_per_second':rx,
               'network_send_bytes_per_second':tx,'load_average':list(os.getloadavg()) if hasattr(os,'getloadavg') else None,
               'scope':'内存和 CPU 使用率为应用容器，宿主机可用内存单独列出；网络为当前网络命名空间。首次采样无速率。'}
        _cached={'sample_at':now,'value':value}
        return value
