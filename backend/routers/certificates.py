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
from fastapi.responses import Response
from models import Certificate
from models import User
from models import beijing_now
from schemas import CertificateResponse
from schemas import CertificateStats
from services.files import build_zip_response, safe_upload_path, save_upload, save_upload_async
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from services.utils import HAS_OPENPYXL
from services.utils import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from starlette.background import BackgroundTask
from urllib.parse import quote
import io
import os
import uuid
import zipfile

router = APIRouter(tags=["certificates"])


@router.post("/api/certificate/upload", response_model=CertificateResponse)
async def upload_certificate(award_name: str = Form(...), student_id: int = Form(...),
                              award_level: str = Form("校级"), award_date: str = Form(None),
                              file: UploadFile = File(...),
                              db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                              x_view_mode: str = Header(None)):
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="只能上传自己的奖状")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS: raise HTTPException(status_code=400, detail="不支持的文件格式")
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = safe_upload_path(filename)
    await save_upload_async(file, file_path)
    parsed_date = None
    if award_date:
        try: parsed_date = datetime.fromisoformat(award_date)
        except ValueError: parsed_date = beijing_now()
    cert = Certificate(student_id=student_id, award_name=award_name, award_level=award_level,
                       award_date=parsed_date or beijing_now(), image_path=filename)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    student = db.query(User).filter(User.id == cert.student_id).first()
    return CertificateResponse(id=cert.id, student_id=cert.student_id,
                               student_name=student.real_name if student else "",
                               student_student_id=student.student_id if student else "",
                               award_name=cert.award_name, award_level=cert.award_level,
                               award_date=cert.award_date, image_path=cert.image_path, created_at=cert.created_at)



@router.get("/api/certificates", response_model=list[CertificateResponse])
def list_certificates(student_id: int = Query(None), award_level: str = Query(None),
                      academic_year: str = Query(None), db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user),
                      x_view_mode: str = Header(None)):
    query = db.query(Certificate).options(joinedload(Certificate.student))
    can_view_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_view_all: query = query.filter(Certificate.student_id == current_user.id)
    if student_id and can_view_all: query = query.filter(Certificate.student_id == student_id)
    if award_level: query = query.filter(Certificate.award_level == award_level)
    if academic_year: query = query.filter(Certificate.award_date >= f"{academic_year}-01-01")
    certs = query.order_by(Certificate.created_at.desc()).all()
    return [CertificateResponse(id=c.id, student_id=c.student_id,
            student_name=c.student.real_name if c.student else "",
            student_student_id=c.student.student_id if c.student else "",
            award_name=c.award_name, award_level=c.award_level, award_date=c.award_date,
            image_path=c.image_path, created_at=c.created_at) for c in certs]



@router.get("/api/certificates/stats", response_model=CertificateStats)
def certificate_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    certs = db.query(Certificate).all()
    students = set()
    national = provincial = school = 0
    for c in certs:
        students.add(c.student_id)
        level = c.award_level or ""
        if level == "国家级":
            national += 1
        elif level == "省级":
            provincial += 1
        else:
            school += 1
    return CertificateStats(total=len(certs), national_count=national, provincial_count=provincial,
                            school_count=school, student_count=len(students))



@router.put("/api/certificates/{cert_id}", response_model=CertificateResponse)
def update_certificate(cert_id: int, award_name: str = Form(...), award_level: str = Form("校级"),
                       award_date: str = Form(None), file: UploadFile = File(None),
                       db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                       x_view_mode: str = Header(None)):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="奖状不存在")
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and current_user.id != cert.student_id:
        raise HTTPException(status_code=403, detail="只能修改自己的奖状")
    cert.award_name = award_name
    cert.award_level = award_level
    if award_date:
        try:
            cert.award_date = datetime.fromisoformat(award_date)
        except ValueError:
            pass
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        # 删除旧文件
        old_path = os.path.join(UPLOAD_DIR, cert.image_path) if cert.image_path else None
        if old_path and os.path.isfile(old_path):
            os.remove(old_path)
        # 保存新文件
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = safe_upload_path(filename)
        save_upload(file, file_path)
        cert.image_path = filename
    db.commit()
    db.refresh(cert)
    student = db.query(User).filter(User.id == cert.student_id).first()
    return CertificateResponse(id=cert.id, student_id=cert.student_id,
                               student_name=student.real_name if student else "",
                               student_student_id=student.student_id if student else "",
                               award_name=cert.award_name, award_level=cert.award_level,
                               award_date=cert.award_date, image_path=cert.image_path, created_at=cert.created_at)



@router.delete("/api/certificates/{cert_id}")
def delete_certificate(cert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                       x_view_mode: str = Header(None)):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="奖状不存在")
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and current_user.id != cert.student_id:
        raise HTTPException(status_code=403, detail="只能删除自己的奖状")
    # 删除图片文件
    if cert.image_path:
        file_path = os.path.join(UPLOAD_DIR, cert.image_path)
        if os.path.isfile(file_path):
            os.remove(file_path)
    db.delete(cert)
    db.commit()
    return {"message": "删除成功"}



@router.get("/api/certificates/export-excel")
def export_certificates_excel(start_date: str = Query(None), end_date: str = Query(None),
                              student_id: int = Query(None), award_level: str = Query(None),
                              db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                              x_view_mode: str = Header(None)):
    """导出奖状信息为Excel"""
    if not HAS_OPENPYXL:
        raise HTTPException(status_code=500, detail="服务器未安装openpyxl")

    query = db.query(Certificate).options(joinedload(Certificate.student))
    can_view_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_view_all:
        query = query.filter(Certificate.student_id == current_user.id)
    if student_id and can_view_all:
        query = query.filter(Certificate.student_id == student_id)
    if start_date:
        query = query.filter(Certificate.award_date >= start_date)
    if end_date:
        query = query.filter(Certificate.award_date <= end_date)
    if award_level:
        query = query.filter(Certificate.award_level == award_level)

    certs = query.order_by(Certificate.award_date.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "奖状列表"
    ws.append(["获奖人", "学号", "奖项名称", "级别", "获奖日期"])

    for c in certs:
        student_name = c.student.real_name if c.student else ""
        student_sid = c.student.student_id if c.student else ""
        ws.append([student_name, student_sid, c.award_name, c.award_level, c.award_date])

    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 14

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = quote("奖状列表.xlsx")
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )



@router.get("/api/certificates/download-zip")
def download_certificates_zip(start_date: str = Query(None), end_date: str = Query(None),
                              student_id: int = Query(None), award_level: str = Query(None),
                              db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                              x_view_mode: str = Header(None)):
    """下载所有奖状图片为压缩包，命名：级别_奖状名称_获奖人"""
    query = db.query(Certificate)
    can_view_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_view_all:
        query = query.filter(Certificate.student_id == current_user.id)
    if student_id and can_view_all:
        query = query.filter(Certificate.student_id == student_id)
    if start_date:
        query = query.filter(Certificate.award_date >= start_date)
    if end_date:
        query = query.filter(Certificate.award_date <= end_date)
    if award_level:
        query = query.filter(Certificate.award_level == award_level)

    certs = query.order_by(Certificate.award_date.desc()).all()

    if not certs:
        raise HTTPException(status_code=404, detail="没有符合条件的奖状")

    items = []
    for c in certs:
        if not c.image_path:
            continue
        full_path = safe_upload_path(c.image_path)
        if not os.path.isfile(full_path):
            continue
        ext = os.path.splitext(c.image_path)[1]
        student_name = c.student.real_name if c.student else str(c.student_id)
        filename_in_zip = f"{c.award_level}_{c.award_name}_{student_name}{ext}"
        filename_in_zip = "".join(ch for ch in filename_in_zip if ch not in r'\\/:*?"<>|')
        items.append({"path": full_path, "arcname": filename_in_zip, "size": os.path.getsize(full_path)})
    if not items:
        raise HTTPException(status_code=404, detail="没有可下载的奖状图片")
    return build_zip_response(items, "奖状图片.zip")
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for c in certs:
            if not c.image_path:
                continue
            full_path = os.path.join(UPLOAD_DIR, c.image_path)
            if not os.path.isfile(full_path):
                continue
            ext = os.path.splitext(c.image_path)[1]
            student_name = c.student.real_name if c.student else str(c.student_id)
            filename_in_zip = f"{c.award_level}_{c.award_name}_{student_name}{ext}"
            # 移除文件名中的非法字符
            filename_in_zip = "".join(ch for ch in filename_in_zip if ch not in r'\/:*?"<>|')
            zf.write(full_path, filename_in_zip)

    zip_buffer.seek(0)
    filename = quote("奖状图片.zip")
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

