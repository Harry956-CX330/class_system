from auth import get_current_user
from auth import require_admin
from config import ALLOWED_EXTENSIONS
from config import DOCUMENT_EXTENSIONS
from config import UPLOAD_DIR
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import ClassMeeting
from models import ClassMeetingRecord
from models import User
from models import beijing_now
from schemas import BatchDeleteRequest
from schemas import ClassMeetingCreate
from schemas import ClassMeetingResponse
from schemas import ClassMeetingUpdate
from schemas import MeetingRecordUpdate
from services.files import build_zip_response, safe_upload_path, save_upload, save_upload_async
from services.mailer import _save_email_history
from services.mailer import load_smtp_config
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import json
import os
import smtplib
import uuid

router = APIRouter(tags=["meetings"])


def _leader_name(db: Session, user_id) -> str:
    if not user_id:
        return ""
    u = db.query(User).filter(User.id == user_id).first()
    return u.real_name if u else ""



@router.get("/api/class-meetings", response_model=list[ClassMeetingResponse])
def list_class_meetings(status: str = Query(None), from_date: str = Query(None), to_date: str = Query(None),
                        db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    # 时间超过班会召开时间自动标记为已举行
    now = beijing_now()
    expired = db.query(ClassMeeting).filter(
        ClassMeeting.status == "upcoming",
        ClassMeeting.meeting_date < now,
    ).all()
    if expired:
        for m in expired:
            m.status = "completed"
        db.commit()
    query = db.query(ClassMeeting)
    if status:
        query = query.filter(ClassMeeting.status == status)
    if from_date:
        try:
            query = query.filter(ClassMeeting.meeting_date >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            query = query.filter(ClassMeeting.meeting_date <= datetime.fromisoformat(to_date))
        except ValueError:
            pass
    meetings = query.order_by(ClassMeeting.meeting_date.desc()).all()
    result = []
    for m in meetings:
        record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == m.id).first()
        record_text = record.record_text if record else ""
        record_images = json.loads(record.images) if record and record.images else []
        record_file = record.record_file if record else ""
        record_file_name = record.record_file_name if record else ""
        result.append({
            "id": m.id, "title": m.title, "meeting_date": m.meeting_date,
            "location": m.location, "description": m.description,
            "status": m.status, "created_at": m.created_at,
            "author_id": m.author_id,
            "author_name": m.author.real_name if m.author else "",
            "record_text": record_text, "record_images": record_images,
            "record_file": record_file, "record_file_name": record_file_name,
            "attendance_leader_id": m.attendance_leader_id,
            "attendance_leader_name": _leader_name(db, m.attendance_leader_id),
            "host_leader_id": m.host_leader_id,
            "host_leader_name": _leader_name(db, m.host_leader_id),
        })
    return result



@router.post("/api/class-meetings", response_model=ClassMeetingResponse)
def create_class_meeting(data: ClassMeetingCreate, db: Session = Depends(get_db, scope="function"),
                         current_user: User = Depends(require_admin)):
    meeting = ClassMeeting(
        title=data.title,
        meeting_date=datetime.fromisoformat(data.meeting_date),
        location=data.location,
        description=data.description,
        status=data.status,
        author_id=current_user.id,
        attendance_leader_id=data.attendance_leader_id,
        host_leader_id=data.host_leader_id,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return {
        "id": meeting.id, "title": meeting.title, "meeting_date": meeting.meeting_date,
        "location": meeting.location, "description": meeting.description,
        "status": meeting.status, "created_at": meeting.created_at,
        "author_id": meeting.author_id, "author_name": current_user.real_name,
        "record_text": "", "record_images": [],
        "record_file": "", "record_file_name": "",
        "attendance_leader_id": meeting.attendance_leader_id,
        "attendance_leader_name": _leader_name(db, meeting.attendance_leader_id),
        "host_leader_id": meeting.host_leader_id,
        "host_leader_name": _leader_name(db, meeting.host_leader_id),
    }



@router.put("/api/class-meetings/{meeting_id}", response_model=ClassMeetingResponse)
def update_class_meeting(meeting_id: int, data: ClassMeetingUpdate, db: Session = Depends(get_db, scope="function"),
                         current_user: User = Depends(require_admin)):
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting: raise HTTPException(status_code=404, detail="班会不存在")
    if data.title is not None:
        meeting.title = data.title
    if data.meeting_date is not None:
        meeting.meeting_date = datetime.fromisoformat(data.meeting_date)
    if data.location is not None:
        meeting.location = data.location
    if data.description is not None:
        meeting.description = data.description
    if data.status is not None:
        meeting.status = data.status
    if data.attendance_leader_id is not None:
        meeting.attendance_leader_id = data.attendance_leader_id
    if data.host_leader_id is not None:
        meeting.host_leader_id = data.host_leader_id
    db.commit()
    db.refresh(meeting)
    record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == meeting.id).first()
    record_text = record.record_text if record else ""
    record_images = json.loads(record.images) if record and record.images else []
    record_file = record.record_file if record else ""
    record_file_name = record.record_file_name if record else ""
    return {
        "id": meeting.id, "title": meeting.title, "meeting_date": meeting.meeting_date,
        "location": meeting.location, "description": meeting.description,
        "status": meeting.status, "created_at": meeting.created_at,
        "author_id": meeting.author_id,
        "author_name": meeting.author.real_name if meeting.author else "",
        "record_text": record_text, "record_images": record_images,
        "record_file": record_file, "record_file_name": record_file_name,
        "attendance_leader_id": meeting.attendance_leader_id,
        "attendance_leader_name": _leader_name(db, meeting.attendance_leader_id),
        "host_leader_id": meeting.host_leader_id,
        "host_leader_name": _leader_name(db, meeting.host_leader_id),
    }



@router.delete("/api/class-meetings/{meeting_id}")
def delete_class_meeting(meeting_id: int, db: Session = Depends(get_db, scope="function"),
                         current_user: User = Depends(require_admin)):
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="班会不存在")
    record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == meeting_id).first()
    if record and record.images:
        try:
            images = json.loads(record.images)
            for img in images:
                try:
                    os.remove(os.path.join(UPLOAD_DIR, img))
                except OSError:
                    pass
        except (json.JSONDecodeError, TypeError):
            pass
    db.delete(meeting)
    db.commit()
    return {"message": "删除成功"}



@router.post("/api/class-meetings/batch-delete")
def batch_delete_class_meetings(data: BatchDeleteRequest, db: Session = Depends(get_db, scope="function"),
                                current_user: User = Depends(require_admin)):
    from_dt = datetime.strptime(data.from_date + " 00:00:00", "%Y-%m-%d %H:%M:%S")
    to_dt = datetime.strptime(data.to_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
    meetings = db.query(ClassMeeting).filter(
        ClassMeeting.created_at >= from_dt, ClassMeeting.created_at <= to_dt
    ).all()
    count = 0
    for meeting in meetings:
        record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == meeting.id).first()
        if record and record.images:
            try:
                images = json.loads(record.images)
                for img in images:
                    try:
                        os.remove(os.path.join(UPLOAD_DIR, img))
                    except OSError:
                        pass
            except (json.JSONDecodeError, TypeError):
                pass
        db.delete(meeting)
        count += 1
    db.commit()
    return {"deleted": count}



@router.put("/api/class-meetings/{meeting_id}/record")
def update_meeting_record(meeting_id: int, data: MeetingRecordUpdate, db: Session = Depends(get_db, scope="function"),
                          current_user: User = Depends(require_admin)):
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="班会不存在")
    record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == meeting_id).first()
    if not record:
        record = ClassMeetingRecord(meeting_id=meeting_id)
        db.add(record)
    record.record_text = data.record_text
    record.images = json.dumps(data.images)
    db.commit()
    db.refresh(record)
    return {
        "record_text": record.record_text,
        "images": json.loads(record.images) if record.images else [],
    }



@router.post("/api/class-meetings/{meeting_id}/upload-images")
async def upload_meeting_images(meeting_id: int, files: list[UploadFile] = File(...),
                                 db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="班会不存在")
    uploaded = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        filename = f"meeting_{uuid.uuid4().hex}{ext}"
        file_path = safe_upload_path(filename)
        await save_upload_async(file, file_path)
        uploaded.append(filename)
    return {"images": uploaded}



@router.post("/api/class-meetings/{meeting_id}/upload-file")
async def upload_meeting_file(meeting_id: int, file: UploadFile = File(...),
                              db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """上传班会记录文件（仅支持文档文件）"""
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="班会不存在")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in DOCUMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持上传 pdf 或 word 文件")
    filename = f"meeting_doc_{uuid.uuid4().hex}{ext}"
    file_path = safe_upload_path(filename)
    await save_upload_async(file, file_path)
    record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == meeting_id).first()
    if not record:
        record = ClassMeetingRecord(meeting_id=meeting_id)
        db.add(record)
    if record.record_file:
        try:
            os.remove(os.path.join(UPLOAD_DIR, record.record_file))
        except OSError:
            pass
    record.record_file = filename
    record.record_file_name = file.filename
    db.commit()
    return {"record_file": filename, "record_file_name": file.filename}



@router.post("/api/class-meetings/{meeting_id}/send-email")
def send_meeting_record_email(meeting_id: int, data: dict, db: Session = Depends(get_db, scope="function"),
                              current_user: User = Depends(require_admin)):
    """一键发送班会记录文件到指定邮箱（标题为班会标题，附件为记录文件）"""
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="班会不存在")
    email_addr = (data.get("email") or "").strip()
    if not email_addr or "@" not in email_addr:
        raise HTTPException(status_code=400, detail="请输入有效的邮箱地址")
    record = db.query(ClassMeetingRecord).filter(ClassMeetingRecord.meeting_id == meeting_id).first()
    if not record or not record.record_file:
        raise HTTPException(status_code=400, detail="请先上传班会记录文件")
    file_path = os.path.join(UPLOAD_DIR, record.record_file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="记录文件不存在，请重新上传")
    time_str = meeting.meeting_date.strftime("%Y-%m-%d %H:%M") if meeting.meeting_date else "待定"
    from html import escape
    body = (f"【班会记录】\n班会：{escape(meeting.title)}\n时间：{time_str}\n"
            f"地点：{escape(meeting.location or '待定')}\n\n请查阅班会记录附件；大文件使用限时链接。")
    result = send_emails_batch([email_addr], meeting.title, body, db=db, send_type='meeting_record', related_id=meeting_id,
        attachments=[{'url':'/static/'+record.record_file, 'name':record.record_file_name or record.record_file,
                      'image':False, 'user_id':current_user.id}])
    if not result.get('success'):
        raise HTTPException(502, '班会记录邮件发送失败，请检查邮件设置及发送历史')
    return {'message':'邮件已发送'}

