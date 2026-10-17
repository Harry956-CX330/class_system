from auth import get_current_user
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import SiteStat
from models import User
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/political-stats")
def political_stats(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    """班级政治面貌统计"""
    students = db.query(User).filter(User.role == "student").all()
    stats = {
        "party_member": 0,       # 中共党员（正式党员）
        "probationary": 0,       # 预备党员
        "league_member": 0,      # 共青团员
        "masses": 0,             # 群众
        "other": 0,              # 其他
        "total": len(students)
    }
    for s in students:
        ps = (s.political_status or "").strip()
        if ps in ("中共党员", "正式党员"):
            stats["party_member"] += 1
        elif ps in ("中共预备党员", "预备党员"):
            stats["probationary"] += 1
        elif ps == "共青团员":
            stats["league_member"] += 1
        elif ps == "群众":
            stats["masses"] += 1
        else:
            stats["other"] += 1
    return stats



@router.get("/api/dashboard/usage-stats")
def usage_stats(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    """系统累计使用量统计"""
    from sqlalchemy import func
    stat = db.query(SiteStat).first()
    if not stat:
        stat = SiteStat(total_visits=0, total_pv=0)
        db.add(stat)
        db.commit()
        db.refresh(stat)
    return {
        "total_visits": stat.total_visits,
        "total_pv": stat.total_pv,
        "total_users": db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0,
    }



@router.post("/api/dashboard/ping")
def ping_dashboard(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    """标记一次页面点击，累加PV"""
    stat = db.query(SiteStat).first()
    if not stat:
        stat = SiteStat(total_visits=0, total_pv=0)
        db.add(stat)
    stat.total_pv += 1
    stat.total_visits = max(stat.total_visits, stat.total_pv)
    db.commit()
    return {"total_visits": stat.total_visits, "total_pv": stat.total_pv}

