from auth import get_current_user
from auth import require_admin
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import Notice
from models import User
from schemas import NoticeCreate
from schemas import NoticeResponse
from schemas import NoticeUpdate
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

router = APIRouter(tags=["notices"])


@router.get("/api/notices", response_model=list[NoticeResponse])
def list_notices(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    notices = db.query(Notice).order_by(Notice.created_at.desc()).all()
    return [NoticeResponse(id=n.id, title=n.title, content=n.content,
            is_urgent=n.is_urgent,
            created_at=n.created_at, updated_at=n.updated_at, author_id=n.author_id,
            author_name=n.author.real_name if n.author else "",
            author_qq=n.author.qq_number if n.author else "") for n in notices]



@router.get("/api/notices/urgent", response_model=NoticeResponse)
def get_urgent_notice(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    notice = db.query(Notice).filter(Notice.is_urgent == True).first()
    if not notice:
        raise HTTPException(status_code=404, detail="当前没有紧急通知")
    return NoticeResponse(id=notice.id, title=notice.title, content=notice.content,
                          is_urgent=notice.is_urgent,
                          created_at=notice.created_at, updated_at=notice.updated_at,
                          author_id=notice.author_id, author_name=notice.author.real_name if notice.author else "",
                          author_qq=notice.author.qq_number if notice.author else "")



@router.post("/api/notices", response_model=NoticeResponse)
def create_notice(data: NoticeCreate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    if data.is_urgent:
        for n in db.query(Notice).filter(Notice.is_urgent == True).all():
            n.is_urgent = False
    notice = Notice(title=data.title, content=data.content, is_urgent=data.is_urgent, author_id=current_user.id)
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return NoticeResponse(id=notice.id, title=notice.title, content=notice.content,
                          is_urgent=notice.is_urgent,
                          created_at=notice.created_at, updated_at=notice.updated_at,
                          author_id=notice.author_id, author_name=current_user.real_name,
                          author_qq=current_user.qq_number)



@router.put("/api/notices/{notice_id}", response_model=NoticeResponse)
def update_notice(notice_id: int, data: NoticeUpdate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice: raise HTTPException(status_code=404, detail="通知不存在")
    if data.title is not None: notice.title = data.title
    if data.content is not None: notice.content = data.content
    if data.is_urgent is True:
        for n in db.query(Notice).filter(Notice.is_urgent == True, Notice.id != notice_id).all():
            n.is_urgent = False
    if data.is_urgent is not None: notice.is_urgent = data.is_urgent
    db.commit()
    db.refresh(notice)
    return NoticeResponse(id=notice.id, title=notice.title, content=notice.content,
                          is_urgent=notice.is_urgent,
                          created_at=notice.created_at, updated_at=notice.updated_at,
                          author_id=notice.author_id, author_name=current_user.real_name,
                          author_qq=current_user.qq_number)



@router.delete("/api/notices/{notice_id}")
def delete_notice(notice_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice: raise HTTPException(status_code=404, detail="通知不存在")
    db.delete(notice)
    db.commit()
    return {"message": "删除成功"}

