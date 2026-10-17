from services.notifications import build_email
import threading
import ssl

_mail_slot = threading.BoundedSemaphore(1)
from config import SMTP_CONFIG_PATH
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import status
from models import EmailHistory
import json
import os
import smtplib
import time

def load_smtp_config():
    """加载 SMTP 配置，不存在则返回默认配置"""
    if os.path.exists(SMTP_CONFIG_PATH):
        with open(SMTP_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"host": "smtp.qq.com", "port": 587, "username": "", "password": ""}



def save_smtp_config(config: dict):
    with open(SMTP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)



def _send_emails_batch(to_emails: list[str], subject: str, body: str, db=None, send_type: str = "test", related_id: int = None) -> dict:
    """批量发送邮件，分批发送避免触发封禁。每批次 10 人，间隔 3 秒"""
    cfg = load_smtp_config()
    allowed = {h.strip() for h in os.environ.get("SMTP_ALLOWED_HOSTS","smtp.qq.com,smtp.163.com,smtp.126.com,smtp.gmail.com,smtp.office365.com").split(",")}
    if cfg.get("host") not in allowed or cfg.get("port") not in {465,587,25}:
        return {"success":False,"detail":"SMTP 主机或端口未在允许列表中"}
    if not cfg.get("password"):
        return {"success": False, "detail": "SMTP 邮件服务尚未配置"}
    result = {"success": True, "total": len(to_emails), "sent": 0, "failed": 0, "errors": []}
    batch_size = 10
    for i in range(0, len(to_emails), batch_size):
        batch = to_emails[i:i + batch_size]
        # 每批复用一个 SMTP 连接
        try:
            with (smtplib.SMTP_SSL(cfg["host"],cfg["port"],timeout=15,context=ssl.create_default_context()) if cfg["port"] == 465 else smtplib.SMTP(cfg["host"],cfg["port"],timeout=15)) as server:
                if cfg["port"] != 465:
                    server.starttls(context=ssl.create_default_context())
                server.login(cfg["username"], cfg["password"])
                for email_addr in batch:
                    if not email_addr or "@" not in email_addr:
                        result["failed"] += 1
                        result["errors"].append(f"无效邮箱: {email_addr}")
                        _save_email_history(db, email_addr, "", subject, send_type, related_id, "failed", "无效邮箱地址")
                        continue
                    try:
                        msg = build_email(cfg["username"],email_addr,subject,body,len(to_emails))
                        raw = msg.as_bytes()
                        # Reserve at most ~32 KiB/s of the uplink for SMTP.
                        started = time.monotonic()
                        server.sendmail(cfg["username"], email_addr, raw)
                        time.sleep(max(0,len(raw)/(32*1024)-(time.monotonic()-started)))
                        result["sent"] += 1
                        _save_email_history(db, email_addr, "", subject, send_type, related_id, "sent", "")
                    except Exception as e:
                        result["failed"] += 1
                        result["errors"].append(f"{email_addr}: {str(e)}")
                        _save_email_history(db, email_addr, "", subject, send_type, related_id, "failed", str(e))
        except Exception as e:
            result["failed"] += len(batch)
            result["errors"].append(f"连接失败: {str(e)}")
            for email_addr in batch:
                if email_addr and "@" in email_addr:
                    _save_email_history(db, email_addr, "", subject, send_type, related_id, "failed", f"连接失败: {str(e)}")
        # 批次间隔，最后一批不用等
        if i + batch_size < len(to_emails):
            time.sleep(3)
    if result["sent"] == 0:
        result["success"] = False
    return result



def _save_email_history(db, email_addr: str, name: str, subject: str, send_type: str, related_id: int, status: str, error_msg: str):
    """保存邮件发送历史到数据库"""
    if db is None:
        return
    try:
        record = EmailHistory(
            recipient_email=email_addr,
            recipient_name=name,
            subject=subject,
            send_type=send_type,
            related_id=related_id,
            status=status,
            error_message=error_msg or ""
        )
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()  # Do not poison the session for subsequent history writes.



def send_emails_batch(to_emails, subject, body, db=None, send_type="test", related_id=None):
    from fastapi import HTTPException
    if not _mail_slot.acquire(blocking=False):
        raise HTTPException(503,"已有邮件任务正在发送，请稍后重试",headers={"Retry-After":"30"})
    try:
        return _send_emails_batch(list(dict.fromkeys(to_emails)),subject,body,db,send_type,related_id)
    finally:
        _mail_slot.release()
