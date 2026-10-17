"""Authenticated static uploads and compressed rich-text attachments."""
import json
import mimetypes
import os
import re
import uuid
import warnings
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from auth import get_current_user, require_admin
from config import MEDIA_DIR, ALLOWED_DOC_EXTENSIONS, UPLOAD_DIR, MIN_FREE_BYTES
from database import get_db
from models import User, FileSubmission, Certificate, SocialPractice, ResourceFile, ClassMeetingRecord
from services.files import safe_upload_path, save_upload
from sqlalchemy.orm import Session
import shutil

router = APIRouter(tags=["media"])
Image.MAX_IMAGE_PIXELS = 16000000

@router.post("/api/media")
def upload_media(file: UploadFile = File(...), user: User = Depends(require_admin)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(400, "不支持的附件格式")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(MEDIA_DIR).free < MIN_FREE_BYTES + 20*1024*1024:
        raise HTTPException(507, "磁盘可用空间不足")
    if sum(p.stat().st_size for p in MEDIA_DIR.iterdir() if p.is_file()) > 1024*1024*1024:
        raise HTTPException(507, "富文本附件空间已达到 1 GiB，请先清理不再使用的附件")
    image = ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    stored = uuid.uuid4().hex + (".webp" if image else ext)
    target = MEDIA_DIR / stored
    if image:
        if file.size is not None and file.size > 5*1024*1024:
            raise HTTPException(413, "图片不能超过 5 MiB")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(file.file) as source:
                    processed = ImageOps.exif_transpose(source)
                    processed.thumbnail((1600, 1600))
                    processed.convert("RGB").save(target, "WEBP", quality=78, method=3)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            target.unlink(missing_ok=True)
            raise HTTPException(400, "图片内容无效或分辨率过大")
    else:
        save_upload(file, target, limit=20*1024*1024)
    name = Path((file.filename or "附件").replace("\\", "/")).name[:180]
    target.with_suffix(target.suffix+".meta.json").write_text(json.dumps({"name":name,"owner":user.id}, ensure_ascii=False), encoding="utf-8")
    return {"url":"/static/rich/"+stored,"name":name,"size":target.stat().st_size,"image":image}

@router.post("/api/media-session")
def refresh_media_session(request: Request, user: User = Depends(get_current_user)):
    from auth import create_access_token
    from fastapi.responses import JSONResponse
    result = JSONResponse({"ok":True})
    result.set_cookie("media_session", create_access_token({"user_id":user.id}), max_age=3600, httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/static")
    return result

@router.get("/static/{filename:path}")
def private_static(filename: str, request: Request, db: Session = Depends(get_db, scope="function")):
    signed = request.scope.get("signed_media", False)
    user = None
    if not signed:
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("media_session", "")
        if not token:
            raise HTTPException(401, "请登录后查看附件")
        user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
    path = Path(safe_upload_path(filename))
    if not path.is_file():
        raise HTTPException(404, "文件不存在")
    rich = re.fullmatch(r"rich/[a-f0-9]{32}\.(?:jpg|png|webp|pdf|docx?|xlsx?|pptx?|txt|zip|rar)", filename)
    if signed and not rich:
        raise HTTPException(403, "无权访问")
    manager = user and (user.role == "admin" or user.is_class_leader)
    if not rich and not manager:
        allowed = False
        for model, field in ((FileSubmission, "file_path"), (Certificate,"image_path"), (SocialPractice,"certificate_image")):
            item = db.query(model).filter(getattr(model,field).in_([filename,"/static/"+filename])).first()
            if item:
                if item.student_id != user.id:
                    raise HTTPException(403, "无权查看他人的私有附件")
                allowed = True
                break
        resource = db.query(ResourceFile).filter(ResourceFile.filename == filename).first()
        if resource:
            if resource.visibility != "student":
                raise HTTPException(403, "无权访问此资料")
            allowed = True
        if not allowed:
            # Meeting records are class-wide; never expose unknown/unreferenced files.
            for record in db.query(ClassMeetingRecord).all():
                try:
                    images = json.loads(record.images or "[]")
                except (ValueError,TypeError):
                    images = []
                if filename == record.record_file or filename in images or "/static/"+filename in images:
                    allowed = True
                    break
        if not allowed:
            raise HTTPException(403, "附件未公开或无权访问")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if path.suffix.lower() in {".jpg",".jpeg",".png",".gif",".webp",".pdf"}:
        return FileResponse(path, media_type=media_type)
    name = path.name
    if rich:
        try:
            name = json.loads(path.with_suffix(path.suffix+".meta.json").read_text(encoding="utf-8")).get("name", name)
        except (OSError, ValueError, AttributeError):
            pass
    return FileResponse(path, media_type="application/octet-stream", filename=name)


@router.post("/api/logout")
def logout_media():
    from fastapi.responses import JSONResponse
    response = JSONResponse({"ok":True})
    response.delete_cookie("media_session",path="/static")
    return response
