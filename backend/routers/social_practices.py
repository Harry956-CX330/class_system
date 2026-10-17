from auth import get_current_user
from config import ALLOWED_EXTENSIONS
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
from models import SocialPractice
from models import User
from schemas import SocialPracticeCreate
from schemas import SocialPracticeResponse
from schemas import SocialPracticeUpdate
from services.files import build_zip_response, safe_upload_path, save_upload, save_upload_async
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import os
import uuid

router = APIRouter(tags=["social_practices"])


def _make_sp_response(sp) -> SocialPracticeResponse:
    return SocialPracticeResponse(id=sp.id, student_id=sp.student_id,
        student_name=sp.student.real_name if sp.student else "",
        student_student_id=sp.student.student_id if sp.student else "",
        activity_name=sp.activity_name, role=sp.role, description=sp.description,
        start_date=sp.start_date, end_date=sp.end_date,
        certificate_image=sp.certificate_image, created_at=sp.created_at)



@router.get("/api/social-practices", response_model=list[SocialPracticeResponse])
def list_social_practices(student_id: int = Query(None), db: Session = Depends(get_db, scope="function"),
                          current_user: User = Depends(get_current_user),
                          x_view_mode: str = Header(None)):
    query = db.query(SocialPractice)
    can_view_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_view_all: query = query.filter(SocialPractice.student_id == current_user.id)
    if student_id and can_view_all: query = query.filter(SocialPractice.student_id == student_id)
    return [_make_sp_response(sp) for sp in query.order_by(SocialPractice.start_date.desc()).all()]



@router.post("/api/social-practices", response_model=SocialPracticeResponse)
def create_social_practice(data: SocialPracticeCreate, db: Session = Depends(get_db, scope="function"),
                           current_user: User = Depends(get_current_user),
                           x_view_mode: str = Header(None)):
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and current_user.id != data.student_id:
        raise HTTPException(status_code=403, detail="只能创建自己的社会实践记录")
    sp = SocialPractice(student_id=data.student_id, activity_name=data.activity_name,
                        role=data.role, description=data.description,
                        start_date=datetime.fromisoformat(data.start_date),
                        end_date=datetime.fromisoformat(data.end_date))
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return _make_sp_response(sp)



@router.put("/api/social-practices/{sp_id}", response_model=SocialPracticeResponse)
def update_social_practice(sp_id: int, data: SocialPracticeUpdate, db: Session = Depends(get_db, scope="function"),
                           current_user: User = Depends(get_current_user),
                           x_view_mode: str = Header(None)):
    sp = db.query(SocialPractice).filter(SocialPractice.id == sp_id).first()
    if not sp: raise HTTPException(status_code=404, detail="记录不存在")
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and current_user.id != sp.student_id:
        raise HTTPException(status_code=403, detail="无权限")
    if data.activity_name is not None: sp.activity_name = data.activity_name
    if data.role is not None: sp.role = data.role
    if data.description is not None: sp.description = data.description
    if data.start_date is not None: sp.start_date = datetime.fromisoformat(data.start_date)
    if data.end_date is not None: sp.end_date = datetime.fromisoformat(data.end_date)
    db.commit()
    db.refresh(sp)
    return _make_sp_response(sp)



@router.delete("/api/social-practices/{sp_id}")
def delete_social_practice(sp_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
                           x_view_mode: str = Header(None)):
    sp = db.query(SocialPractice).filter(SocialPractice.id == sp_id).first()
    if not sp: raise HTTPException(status_code=404, detail="记录不存在")
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and current_user.id != sp.student_id:
        raise HTTPException(status_code=403, detail="无权限")
    db.delete(sp)
    db.commit()
    return {"message": "删除成功"}



@router.post("/api/social-practices/upload-certificate")
async def upload_sp_certificate(sp_id: int = Form(...), file: UploadFile = File(...),
                                 db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    sp = db.query(SocialPractice).filter(SocialPractice.id == sp_id).first()
    if not sp: raise HTTPException(status_code=404, detail="记录不存在")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS: raise HTTPException(status_code=400, detail="不支持的文件格式")
    filename = f"sp_{uuid.uuid4().hex}{ext}"
    file_path = safe_upload_path(filename)
    await save_upload_async(file, file_path)
    sp.certificate_image = filename
    db.commit()
    return {"image_url": f"/static/{filename}"}



@router.get("/api/social-practices/stats")
def social_practice_stats(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    all_sp = db.query(SocialPractice).all()
    students = set()
    total_hours = 0
    for sp in all_sp:
        students.add(sp.student_id)
        delta = (sp.end_date - sp.start_date).days + 1
        if delta > 0: total_hours += delta * 8
    return {"total": len(all_sp), "student_count": len(students), "estimated_hours": total_hours}

