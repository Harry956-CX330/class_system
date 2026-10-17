import hashlib
import json
import time
"""Bounded-memory file I/O shared by all business routers."""
import os
import shutil
import tempfile
import threading
import zipfile
import urllib.parse
from pathlib import Path, PurePosixPath
from fastapi import HTTPException
from starlette.responses import FileResponse
from config import TEMP_DIR, UPLOAD_DIR, MAX_UPLOAD_BYTES, MAX_ARCHIVES, MAX_ARCHIVE_BYTES, MIN_FREE_BYTES

CHUNK_SIZE = 256 * 1024
archive_slots = threading.BoundedSemaphore(MAX_ARCHIVES)


def safe_upload_path(filename):
    root = Path(UPLOAD_DIR).resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or path == root:
        raise HTTPException(400, "无效的文件路径")
    return str(path)


def save_upload(upload, destination, limit=MAX_UPLOAD_BYTES):
    """Called from sync endpoints: copy a spooled UploadFile in fixed-size chunks."""
    size = 0
    try:
        with open(destination, "xb") as target:
            while chunk := upload.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, "文件大小超过限制")
                target.write(chunk)
        return size
    except FileExistsError:
        raise
    except BaseException:
        Path(destination).unlink(missing_ok=True)
        raise


async def save_upload_async(upload, destination, limit=MAX_UPLOAD_BYTES):
    size = 0
    try:
        with open(destination, "xb") as target:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, "文件大小超过限制")
                target.write(chunk)
        return size
    except FileExistsError:
        raise
    except BaseException:
        Path(destination).unlink(missing_ok=True)
        raise


async def read_small_upload(upload, limit):
    chunks = []
    size = 0
    while chunk := await upload.read(CHUNK_SIZE):
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, "导入文件超过限制")
        chunks.append(chunk)
    return b"".join(chunks)


def attachment_headers(filename):
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"}


_cache_users = {}
_cache_lock = threading.Lock()

class CachedArchiveResponse(FileResponse):
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope,receive,send)
        finally:
            with _cache_lock:
                _cache_users[str(self.path)] = max(0,_cache_users.get(str(self.path),1)-1)

def build_zip_response(items, filename):
    if not archive_slots.acquire(blocking=False):
        raise HTTPException(503,"压缩包正在生成，请稍后重试",headers={"Retry-After":"10"})
    temporary = None
    try:
        size = sum(os.path.getsize(item["path"]) for item in items)
        if size > MAX_ARCHIVE_BYTES:
            raise HTTPException(413,"本次打包超过上限，请按任务或分批下载")
        TEMP_DIR.mkdir(parents=True,exist_ok=True)
        digest = hashlib.sha256(json.dumps([(i["path"],i["arcname"],os.stat(i["path"]).st_size,os.stat(i["path"]).st_mtime_ns) for i in items],ensure_ascii=False).encode()).hexdigest()
        path = TEMP_DIR / ("cached-"+digest+".zip")
        with _cache_lock:
            candidates = sorted(TEMP_DIR.glob("cached-*.zip"),key=lambda p:p.stat().st_mtime)
            total = sum(p.stat().st_size for p in candidates)
            for old in candidates:
                if old == path or _cache_users.get(str(old),0):
                    continue
                if time.time()-old.stat().st_mtime>7200 or (not path.exists() and total+size>MAX_ARCHIVE_BYTES):
                    total -= old.stat().st_size
                    old.unlink(missing_ok=True)
                    _cache_users.pop(str(old),None)
            if not path.exists() and total+size>MAX_ARCHIVE_BYTES:
                raise HTTPException(503,"其他压缩包仍在下载，请稍后重试",headers={"Retry-After":"30"})
        if not path.exists():
            if shutil.disk_usage(TEMP_DIR).free < size+size//50+MIN_FREE_BYTES:
                raise HTTPException(507,"磁盘可用空间不足，请按批次下载")
            fd,temporary = tempfile.mkstemp(prefix="archive-",suffix=".tmp",dir=TEMP_DIR)
            os.close(fd)
            seen = set()
            with zipfile.ZipFile(temporary,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
                for item in items:
                    entry = PurePosixPath(item["arcname"].replace("\\","/"))
                    if entry.is_absolute() or ".." in entry.parts or not entry.name:
                        raise HTTPException(400,"无效的压缩包文件名")
                    name = str(entry)
                    base,ext = os.path.splitext(name)
                    count = 1
                    while name.casefold() in seen:
                        name = f"{base}_{count}{ext}"
                        count += 1
                    seen.add(name.casefold())
                    archive.write(item["path"],name)
            os.replace(temporary,path)
            temporary = None
        with _cache_lock:
            _cache_users[str(path)] = _cache_users.get(str(path),0)+1
        return CachedArchiveResponse(path,media_type="application/zip",filename=filename,headers={"Cache-Control":"private, no-store"})
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
        archive_slots.release()
