"""Public, compressed login photographs, managed by administrators and class leaders."""
import io
import re
import uuid
import warnings
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
from auth import get_current_user, require_admin
from config import DATA_DIR
from models import User
from services.private_settings import read_settings, write_settings, settings_lock

router = APIRouter(tags=["branding"])
DEFAULTS = [{"url":f"/login-slides/{i}.webp", "caption":caption} for i,caption in enumerate(["一起成长，记录班级的每一份精彩", "同心协力，共享荣誉", "青春同行，向阳而生"],1)]
PHOTO = re.compile(r"[a-f0-9]{32}\.webp")
def system_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "仅系统管理员可操作")
    return user

class Slide(BaseModel):
    url: str = Field(max_length=100)
    caption: str = Field(default="班级风采", max_length=60)
class Branding(BaseModel):
    slides: list[Slide] = Field(min_length=1, max_length=6)

@router.get("/api/branding")
def get_branding():
    with settings_lock:
        return read_settings("login-branding.json", {"slides":DEFAULTS})

@router.put("/api/branding")
def set_branding(data: Branding, user=Depends(require_admin)):
    with settings_lock:
        for slide in data.slides:
            name = slide.url.removeprefix("/api/branding/images/")
            if slide.url not in {item["url"] for item in DEFAULTS} and not (
                PHOTO.fullmatch(name) and (DATA_DIR/"login-images"/name).is_file()
            ):
                raise HTTPException(400, "请使用已上传的轮播图片")
        write_settings("login-branding.json", data.model_dump())
        # Published photos are deliberately public. Remove unreferenced uploads.
        folder = DATA_DIR/"login-images"
        used = {slide.url.rsplit("/",1)[-1] for slide in data.slides}
        if folder.exists():
            for photo in folder.glob("*.webp"):
                if photo.name not in used:
                    photo.unlink(missing_ok=True)
    return data

@router.post("/api/branding/images")
def upload_photo(file: UploadFile = File(...), user=Depends(require_admin)):
    raw = file.file.read(5*1024*1024+1)
    if len(raw) > 5*1024*1024:
        raise HTTPException(413, "图片不能超过 5 MiB")
    with settings_lock:
        folder = DATA_DIR/"login-images"
        folder.mkdir(parents=True, exist_ok=True)
        if sum(p.stat().st_size for p in folder.glob("*.webp")) > 20*1024*1024:
            raise HTTPException(413, "图片空间已满，请先保存并清理不用的图片")
        target = folder/(uuid.uuid4().hex+".webp")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.width*image.height > 16000000:
                        raise ValueError()
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((1440,1080))
                    image.save(target,"WEBP",quality=76,method=4)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            target.unlink(missing_ok=True)
            raise HTTPException(400, "图片无效或分辨率过大")
    return {"url":"/api/branding/images/"+target.name,"caption":"班级风采"}

@router.get("/api/branding/images/{name}")
def public_photo(name: str):
    if not PHOTO.fullmatch(name):
        raise HTTPException(404)
    path = DATA_DIR/"login-images"/name
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path,media_type="image/webp",headers={"Cache-Control":"public, max-age=86400"})
