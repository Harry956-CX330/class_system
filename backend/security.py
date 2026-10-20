"""Bounded in-memory limits and response hardening for a single worker."""
import asyncio
import time
import os
from collections import OrderedDict
from starlette.responses import JSONResponse
from config import DOWNLOAD_BYTES_PER_SECOND

class WindowLimiter:
    def __init__(self, capacity=2048):
        self.windows = OrderedDict()
        self.capacity = capacity
    def allow(self, key, limit, seconds):
        now = time.monotonic()
        start, count = self.windows.pop(key, (now, 0))
        if now - start >= seconds:
            start, count = now, 0
        self.windows[key] = (start, count + 1)
        while len(self.windows) > self.capacity:
            self.windows.popitem(last=False)
        return count < limit

login_accounts = WindowLimiter()

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.limiter = WindowLimiter()
        self.next_byte_at = 0.0
        self.bandwidth_lock = asyncio.Lock()
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        secure_origin = os.environ.get("HTTPS_REDIRECT_URL", "").rstrip("/")
        host = dict(scope.get("headers", [])).get(b"host",b"").decode("ascii",errors="ignore").split(":")[0]
        if secure_origin and scope.get("scheme") != "https" and host == "8.163.67.49":
            from starlette.responses import RedirectResponse
            target = secure_origin + scope.get("raw_path",path.encode()).decode("ascii")
            if scope.get("query_string"):
                target += "?" + scope["query_string"].decode("ascii")
            return await RedirectResponse(target,status_code=308)(scope,receive,send)
        peer = (scope.get("client") or ("unknown", 0))[0]
        from services.server_monitor import monitor
        tracked = path.startswith('/api/') and not (path == '/api/health' and peer in {'127.0.0.1','::1'})
        if tracked:
            retry = monitor.enter(peer, path)
            if retry:
                return await JSONResponse({'detail':'请求过于频繁，已触发自动防护，请等待后重试'},429,
                    headers={'Retry-After':str(retry), 'X-Content-Type-Options':'nosniff', 'Cache-Control':'no-store'})(scope,receive,send)
        response_status = 500
        if scope["method"] == "POST" and (path.endswith(("/notify", "/remind", "/send-email", "/send-emails", "/send-dorm-emails", "/remind-leaders", "/remind-one", "/resend")) or "qq-remind-" in path):
            identity = dict(scope.get("headers", [])).get(b"authorization", b"")
            if not self.limiter.allow((peer, identity, path), 2, 60):
                if tracked: monitor.leave(peer,path,429)
                return await JSONResponse({"detail": "提醒正在处理，请一分钟后重试"}, 429, headers={"Retry-After": "60"})(scope, receive, send)
        download = path.startswith(("/static/", "/api/transfers/open/")) or any(k in path for k in ("download", "/export", "/media/"))
        if download:
            scope = dict(scope, extensions={k:v for k,v in scope.get("extensions", {}).items() if k != "http.response.pathsend"})
        async def guarded_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                headers = list(message.get("headers", []))
                headers.extend([(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"), (b"permissions-policy", b"camera=(self), microphone=(), geolocation=()"),
                    (b"content-security-policy", b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self' data:; connect-src 'self'; frame-src https:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")])
                if path.startswith(("/api/", "/static/")) and not path.startswith('/api/branding/images/'):
                    headers = [(k,v) for k,v in headers if k.lower() != b"cache-control"]
                    headers.append((b"cache-control", b"private, no-store"))
                if scope.get("scheme") == "https":
                    headers.append((b"strict-transport-security", b"max-age=31536000"))
                message = dict(message, headers=headers)
            if download and message["type"] == "http.response.body" and message.get("body"):
                body = message["body"]
                for offset in range(0, len(body), 32768):
                    chunk = body[offset:offset+32768]
                    async with self.bandwidth_lock:
                        now = time.monotonic()
                        scheduled = max(now, self.next_byte_at)
                        self.next_byte_at = scheduled + len(chunk) / DOWNLOAD_BYTES_PER_SECOND
                    await asyncio.sleep(max(0, scheduled - now))
                    await send(dict(message, body=chunk, more_body=offset+32768 < len(body) or message.get("more_body", False)))
                return
            await send(message)
        try:
            await self.app(scope, receive, guarded_send)
        finally:
            if tracked: monitor.leave(peer,path,response_status)
