"""Pure ASGI admission control; never buffers a request or a file response."""
from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse
from config import MAX_UPLOAD_BYTES, MAX_UPLOADS, MAX_DOWNLOADS


class ResourceLimitsMiddleware:
    def __init__(self, app, max_body=MAX_UPLOAD_BYTES, uploads=MAX_UPLOADS, downloads=MAX_DOWNLOADS):
        self.app = app
        self.max_body = max_body
        self.upload_limit = uploads
        self.download_limit = downloads
        self.uploads = 0
        self.downloads = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        upload = scope["method"] in {"POST", "PUT", "PATCH"} and b"multipart/form-data" in headers.get(b"content-type", b"").lower()
        path = scope.get("path", "")
        download = scope["method"] in {"GET", "HEAD"} and (
            path.startswith("/static/") or "download" in path or path.endswith("/export") or "/media/" in path
        )

        async def reject(code, detail):
            await JSONResponse({"detail": detail}, status_code=code, headers={"Retry-After": "5"} if code == 503 else {})(scope, receive, send)

        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            return await reject(400, "无效的 Content-Length")
        body_limit = self.max_body if upload else min(self.max_body, 1024*1024)
        if length > body_limit:
            return await reject(413, f"请求总大小超过 {body_limit // 1024 // 1024} MiB 限制")
        if (upload and self.uploads >= self.upload_limit) or (download and self.downloads >= self.download_limit):
            return await reject(503, "文件处理繁忙，请稍后重试")
        if upload:
            self.uploads += 1
        if download:
            self.downloads += 1
        received = 0
        overflow = False
        started = False

        async def limited_receive():
            nonlocal received, overflow
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > body_limit:
                    overflow = True
                    # Starlette closes partial multipart spool files on this exception.
                    raise MultiPartException("请求体过大")
            return message

        async def limited_send(message):
            nonlocal started
            if overflow:
                if not started:
                    started = True
                    await reject(413, f"请求总大小超过 {body_limit // 1024 // 1024} MiB 限制")
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, limited_send)
        except Exception:
            if overflow and not started:
                await reject(413, "请求总大小超过限制")
            else:
                raise
        finally:
            if upload:
                self.uploads -= 1
            if download:
                self.downloads -= 1
