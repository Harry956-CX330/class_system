"""Short-lived, path-bound download tickets for browser downloads and emails."""
import re
import time
from urllib.parse import urlsplit, parse_qs
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from auth import SECRET_KEY, ALGORITHM, get_current_user, create_access_token
from models import User

router = APIRouter(tags=["transfers"])
DOWNLOAD_PATH = re.compile(r"/api/(?:file-tasks/(?:[0-9]+/(?:download-zip|students/[0-9]+/download-zip)|download-all-zip|submissions/[0-9]+/download)|resources/[0-9]+/download|surveys/[0-9]+/export)$")
MEDIA_PATH = re.compile(r"/static/rich/[a-f0-9]{32}\.[a-z0-9]+$")

def make_ticket(path, user_id=None, view="", seconds=7200):
    return jwt.encode({"aud": "download", "path": path, "uid": user_id, "view": view, "exp": int(time.time())+seconds}, SECRET_KEY, algorithm=ALGORITHM)

class DownloadRequest(BaseModel):
    path: str = Field(max_length=2048)

@router.post("/api/transfers")
def prepare_download(data: DownloadRequest, request: Request, user: User = Depends(get_current_user)):
    parts = urlsplit(data.path)
    if parts.scheme or parts.netloc or not DOWNLOAD_PATH.fullmatch(parts.path):
        raise HTTPException(400, "不支持的下载地址")
    query = parse_qs(parts.query)
    if set(query) - {"structure", "batch", "sort_by", "sort_order", "include_all"}:
        raise HTTPException(400, "不支持的下载参数")
    token = make_ticket(data.path, user.id, request.headers.get("X-View-Mode", ""))
    return {"url": "/api/transfers/open/" + token, "expires_in": 7200}

class TransferTicketMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        prefix = "/api/transfers/open/"
        if scope["type"] != "http" or not scope.get("path", "").startswith(prefix):
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse
        try:
            if scope["method"] not in {"GET", "HEAD"}:
                raise ValueError
            token = scope["path"][len(prefix):]
            claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="download", options={"require": ["exp", "path", "aud"]})
            parts = urlsplit(claims["path"])
            if not (DOWNLOAD_PATH.fullmatch(parts.path) or MEDIA_PATH.fullmatch(parts.path)):
                raise ValueError
            headers = [(k,v) for k,v in scope.get("headers", []) if k.lower() not in {b"authorization", b"x-view-mode"}]
            if claims.get("uid") is not None:
                headers += [(b"authorization", ("Bearer " + create_access_token({"user_id": claims["uid"]})).encode()), (b"x-view-mode", claims.get("view", "").encode())]
            elif MEDIA_PATH.fullmatch(parts.path):
                scope = dict(scope, signed_media=True)
            else:
                raise ValueError
            scope = dict(scope, path=parts.path, raw_path=parts.path.encode(), query_string=parts.query.encode(), headers=headers)
        except (ValueError, KeyError, jwt.PyJWTError):
            return await JSONResponse({"detail": "下载链接已失效，请重新登录获取"}, 401)(scope, receive, send)
        await self.app(scope, receive, send)
