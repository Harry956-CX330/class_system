from auth import require_admin
from config import KDOCS_CONFIG_PATH
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import EmailHistory
from models import Notice
from models import User
from schemas import SmtpConfigCreate
from schemas import SmtpConfigResponse
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.mailer import save_smtp_config
from services.mailer import send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import json
import os

router = APIRouter(tags=["settings"])


@router.get("/api/smtp-config", response_model=SmtpConfigResponse)
def get_smtp_config(current_user: User = Depends(require_admin)):
    """获取 SMTP 配置（密码不返回）"""
    cfg = load_smtp_config()
    return SmtpConfigResponse(
        host=cfg.get("host", ""), port=cfg.get("port", 587),
        username=cfg.get("username", ""), configured=bool(cfg.get("password"))
    )



@router.put("/api/smtp-config")
def update_smtp_config(data: SmtpConfigCreate, current_user: User = Depends(require_admin)):
    """更新 SMTP 配置（管理员自行维护）"""
    cfg = load_smtp_config()
    cfg["host"] = data.host or cfg.get("host", "smtp.qq.com")
    cfg["port"] = data.port or 587
    cfg["username"] = data.username
    if data.password:  # 仅当输入了新密码时才覆盖
        cfg["password"] = data.password
    save_smtp_config(cfg)
    return {"message": "SMTP 配置已更新", "configured": bool(cfg.get("password"))}



@router.post("/api/smtp-config/test-email")
def test_smtp_email(payload: dict, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """测试 SMTP 邮件发送"""
    test_email = payload.get("email", "").strip()
    if not test_email or "@" not in test_email:
        raise HTTPException(status_code=400, detail="请提供有效的测试邮箱地址")
    cfg = load_smtp_config()
    if not cfg.get("password"):
        raise HTTPException(status_code=400, detail="SMTP 邮件服务尚未配置，请先保存配置")
    subject = "[测试邮件] 智能班务系统邮件通知"
    body = "这是一封测试邮件。\n\n如果您收到此邮件，说明 SMTP 邮件服务配置成功！\n\n---\n此邮件由智能班务系统自动发送，请勿回复"
    result = send_emails_batch([test_email], subject, body, db=db, send_type="test")
    if result.get("sent", 0) > 0:
        return {"success": True, "detail": "测试邮件发送成功"}
    else:
        raise HTTPException(status_code=500, detail=result.get("errors", ["发送失败"])[0])



@router.get("/api/email-history", response_model=dict)
def get_email_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query(None, alias="status"),
    send_type: str = Query(None),
    db: Session = Depends(get_db, scope="function"),
    current_user: User = Depends(require_admin)
):
    """查看邮件发送历史"""
    q = db.query(EmailHistory)
    if status_filter:
        q = q.filter(EmailHistory.status == status_filter)
    if send_type:
        q = q.filter(EmailHistory.send_type == send_type)
    total = q.count()
    records = q.order_by(EmailHistory.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "recipient_email": r.recipient_email,
                "recipient_name": r.recipient_name,
                "subject": r.subject,
                "send_type": r.send_type,
                "related_id": r.related_id,
                "status": r.status,
                "error_message": r.error_message,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            }
            for r in records
        ]
    }



@router.post("/api/email-history/resend")
def resend_failed_emails(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """一键重发所有发送失败的邮件"""
    failed_records = db.query(EmailHistory).filter(EmailHistory.status == "failed").all()
    if not failed_records:
        raise HTTPException(status_code=400, detail="没有发送失败的邮件记录")

    # 按 subject 分组，每组取一个邮件地址
    subjects = {}
    for r in failed_records:
        if r.subject not in subjects:
            subjects[r.subject] = []
        if r.recipient_email and "@" in r.recipient_email:
            subjects[r.subject].append(r.recipient_email)

    total_resent = 0
    total_failed = 0
    errors = []

    for subject_text, emails in subjects.items():
        # 构造简化的邮件正文
        body = f"【重发邮件】\n\n{subject_text}\n\n---\n此邮件由智能班务系统自动重发，请勿回复。"
        result = send_emails_batch(emails, subject_text, body, db=db, send_type="test", related_id=None)
        total_resent += result.get("sent", 0)
        total_failed += result.get("failed", 0)
        errors.extend(result.get("errors", []))

    return {"success": True, "total": total_resent + total_failed, "resent": total_resent, "failed": total_failed, "errors": errors}



@router.post("/api/notices/{notice_id}/send-email")
def send_notice_email(notice_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """一键发送邮件通知给全班学生"""
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="通知不存在")
    students = db.query(User).filter(User.role == "student").all()
    to_emails = [s.email for s in students if s.email and "@" in s.email]
    if not to_emails:
        raise HTTPException(status_code=400, detail="没有可用的学生邮箱，请先在用户管理中补充邮箱信息")
    subject = f"[班级通知] {notice.title}"
    body = f"【通知公告】\n\n标题：{notice.title}\n发布人：{notice.author.real_name or notice.author.username}\n联系QQ：{notice.author.qq_number or '未填写'}\n发布时间：{notice.created_at.strftime('%Y-%m-%d %H:%M')}\n\n正文：\n{notice.content}\n\n---\n此邮件由智能班务系统自动发送，请勿回复"
    result = send_emails_batch(to_emails, subject, body, db=db, send_type="notice", related_id=notice_id)
    return {"success": result.get("success", True), "detail": result}



@router.get("/api/config/kdocs-url")
def get_kdocs_url(current_user: User = Depends(require_admin)):
    """获取金山文档在线表格链接（仅管理员）"""
    if os.path.exists(KDOCS_CONFIG_PATH):
        with open(KDOCS_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {"url": ""}
    return {"url": cfg.get("url", "")}



@router.put("/api/config/kdocs-url")
def set_kdocs_url(data: dict, current_user: User = Depends(require_admin)):
    """设置金山文档在线表格链接（仅管理员）"""
    url = data.get("url", "").strip()
    with open(KDOCS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"url": url}, f, ensure_ascii=False, indent=2)
    return {"message": "链接已保存", "url": url}



@router.get("/api/config/kdocs-url-public")
def get_kdocs_url_public():
    """公开获取金山文档在线表格链接（学生可访问）"""
    if os.path.exists(KDOCS_CONFIG_PATH):
        with open(KDOCS_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {"url": ""}
    return {"url": cfg.get("url", "")}

