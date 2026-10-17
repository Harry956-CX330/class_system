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


class TemporaryArchiveResponse(FileResponse):
    """Release disk space and the archive slot on success, errors and disconnects."""
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                Path(self.path).unlink(missing_ok=True)
            finally:
                archive_slots.release()


def build_zip_response(items, filename):
    if not archive_slots.acquire(blocking=False):
        raise HTTPException(503, "已有压缩包正在生成或下载，请稍后重试", headers={"Retry-After": "5"})
    path = None
    try:
        size = sum(item["size"] for item in items)
        if size > MAX_ARCHIVE_BYTES:
            raise HTTPException(413, "本次打包过大，请按任务或批次下载")
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(TEMP_DIR).free < size + size // 50 + MIN_FREE_BYTES:
            raise HTTPException(507, "磁盘可用空间不足，请减少本次打包文件")
        fd, path = tempfile.mkstemp(prefix="archive-", suffix=".zip", dir=TEMP_DIR)
        os.close(fd)
        seen = set()
        # Accepted PDFs/images/office archives are usually already compressed.
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for item in items:
                entry = PurePosixPath(item["arcname"].replace("\\", "/"))
                if entry.is_absolute() or ".." in entry.parts or not entry.name:
                    raise HTTPException(400, "无效的压缩包文件名")
                name = str(entry)
                base, ext = os.path.splitext(name)
                count = 1
                while name.casefold() in seen:
                    name = f"{base}_{count}{ext}"
                    count += 1
                seen.add(name.casefold())
                archive.write(item["path"], name)
        return TemporaryArchiveResponse(path, media_type="application/zip", filename=filename,
                                        headers={"Cache-Control": "private, no-store"})
    except BaseException:
        if path:
            Path(path).unlink(missing_ok=True)
        archive_slots.release()
        raise
