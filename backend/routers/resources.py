from auth import get_current_user
from auth import require_admin
from config import ALLOWED_DOC_EXTENSIONS
from config import UPLOAD_DIR
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from datetime import datetime
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Header
from fastapi import Query
from fastapi import UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import ResourceCategory
from models import ResourceFile
from models import User
from schemas import ResourceCategoryCreate
from schemas import ResourceCategoryResponse
from schemas import ResourceCategoryUpdate
from schemas import ResourceFileResponse
from services.files import build_zip_response, safe_upload_path, save_upload, save_upload_async
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import os
import uuid

router = APIRouter(tags=["resources"])


@router.get("/api/resource-categories", response_model=list[ResourceCategoryResponse])
def list_resource_categories(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    categories = db.query(ResourceCategory).order_by(ResourceCategory.created_at.desc()).all()
    result = []
    for cat in categories:
        file_count = db.query(ResourceFile).filter(ResourceFile.category_id == cat.id).count()
        result.append({
            "id": cat.id, "name": cat.name, "description": cat.description,
            "created_at": cat.created_at, "file_count": file_count,
        })
    return result



@router.post("/api/resource-categories", response_model=ResourceCategoryResponse)
def create_resource_category(data: ResourceCategoryCreate, db: Session = Depends(get_db, scope="function"),
                             current_user: User = Depends(require_admin)):
    cat = ResourceCategory(name=data.name, description=data.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {
        "id": cat.id, "name": cat.name, "description": cat.description,
        "created_at": cat.created_at, "file_count": 0,
    }



@router.put("/api/resource-categories/{cat_id}", response_model=ResourceCategoryResponse)
def update_resource_category(cat_id: int, data: ResourceCategoryUpdate, db: Session = Depends(get_db, scope="function"),
                             current_user: User = Depends(require_admin)):
    cat = db.query(ResourceCategory).filter(ResourceCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    if data.name is not None:
        cat.name = data.name
    if data.description is not None:
        cat.description = data.description
    db.commit()
    db.refresh(cat)
    file_count = db.query(ResourceFile).filter(ResourceFile.category_id == cat.id).count()
    return {
        "id": cat.id, "name": cat.name, "description": cat.description,
        "created_at": cat.created_at, "file_count": file_count,
    }



@router.delete("/api/resource-categories/{cat_id}")
def delete_resource_category(cat_id: int, db: Session = Depends(get_db, scope="function"),
                             current_user: User = Depends(require_admin)):
    cat = db.query(ResourceCategory).filter(ResourceCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    for f in cat.files:
        try:
            os.remove(os.path.join(UPLOAD_DIR, f.filename))
        except OSError:
            pass
    db.delete(cat)
    db.commit()
    return {"message": "删除成功"}



@router.get("/api/resources", response_model=list[ResourceFileResponse])
def list_resources(category_id: int = Query(None), db: Session = Depends(get_db, scope="function"),
                   current_user: User = Depends(get_current_user),
                   x_view_mode: str = Header(None)):
    query = db.query(ResourceFile)
    if category_id:
        query = query.filter(ResourceFile.category_id == category_id)
    can_view_admin = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_view_admin:
        query = query.filter(ResourceFile.visibility != "admin")
    files = query.order_by(ResourceFile.created_at.desc()).all()
    return [{
        "id": f.id, "category_id": f.category_id,
        "category_name": f.category.name if f.category else "",
        "filename": f.filename, "original_name": f.original_name,
        "file_path": f.file_path, "file_size": f.file_size,
        "file_type": f.file_type, "visibility": f.visibility,
        "uploaded_by": f.uploaded_by,
        "uploader_name": f.uploader.real_name if f.uploader else "",
        "created_at": f.created_at,
    } for f in files]



@router.post("/api/resources/upload")
async def upload_resource(category_id: int = Form(...), visibility: str = Form("student"), file: UploadFile = File(...),
                          db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    cat = db.query(ResourceCategory).filter(ResourceCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = safe_upload_path(filename)
    file_size = await save_upload_async(file, file_path)
    resource = ResourceFile(
        category_id=category_id, filename=filename,
        original_name=file.filename, file_path=f"/static/{filename}",
        file_size=file_size, file_type=ext.lstrip("."),
        visibility=visibility,
        uploaded_by=current_user.id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {
        "id": resource.id, "category_id": resource.category_id,
        "category_name": cat.name,
        "filename": resource.filename, "original_name": resource.original_name,
        "file_path": resource.file_path, "file_size": resource.file_size,
        "file_type": resource.file_type, "visibility": resource.visibility,
        "uploaded_by": resource.uploaded_by,
        "uploader_name": current_user.real_name,
        "created_at": resource.created_at,
    }



@router.delete("/api/resources/{file_id}")
def delete_resource(file_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    resource = db.query(ResourceFile).filter(ResourceFile.id == file_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        os.remove(os.path.join(UPLOAD_DIR, resource.filename))
    except OSError:
        pass
    db.delete(resource)
    db.commit()
    return {"message": "删除成功"}



@router.post("/api/resources/batch-delete")
def batch_delete_resources(data: dict, db: Session = Depends(get_db, scope="function"),
                           current_user: User = Depends(require_admin)):
    ids = data.get("ids")
    resources = []
    if ids:
        resources = db.query(ResourceFile).filter(ResourceFile.id.in_(ids)).all()
    else:
        from_dt = datetime.strptime(data["from_date"] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        to_dt = datetime.strptime(data["to_date"] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        resources = db.query(ResourceFile).filter(
            ResourceFile.created_at >= from_dt, ResourceFile.created_at <= to_dt
        ).all()
    count = 0
    for r in resources:
        try:
            os.remove(os.path.join(UPLOAD_DIR, r.filename))
        except OSError:
            pass
        db.delete(r)
        count += 1
    db.commit()
    return {"deleted": count}

