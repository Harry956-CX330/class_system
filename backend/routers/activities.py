from auth import get_current_user
from auth import require_admin
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from datetime import datetime
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.responses import StreamingResponse
from models import Activity
from models import ActivityParticipant
from models import User
from models import beijing_now
from schemas import ActivityCreate
from schemas import ActivityResponse
from schemas import ActivityUpdate
from schemas import CheckinVerifyRequest
from schemas import ParticipantResponse
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from services.utils import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from urllib.parse import quote
import io
import random

router = APIRouter(tags=["activities"])


def generate_checkin_code() -> str:
    """生成四位数字签到码"""
    return f"{random.randint(0, 9999):04d}"



@router.get("/api/activities", response_model=list[ActivityResponse])
def list_activities(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取活动列表（带参与和签到统计）"""
    acts = db.query(Activity).order_by(Activity.start_time.desc()).all()
    # 当前用户（学生）在各活动中的签到状态
    my_status = {}
    if current_user.role == "student":
        for p in db.query(ActivityParticipant).filter(ActivityParticipant.student_id == current_user.id).all():
            my_status[p.activity_id] = p.sign_status
    counts = dict(db.query(ActivityParticipant.activity_id, func.count(ActivityParticipant.id)).group_by(ActivityParticipant.activity_id).all())
    signed_counts = dict(db.query(ActivityParticipant.activity_id, func.count(ActivityParticipant.id)).filter(
        ActivityParticipant.sign_status.in_(["present", "late"])
    ).group_by(ActivityParticipant.activity_id).all())
    result = []
    for a in acts:
        total = counts.get(a.id, 0)
        signed = signed_counts.get(a.id, 0)
        result.append(ActivityResponse(
            id=a.id, title=a.title, description=a.description, location=a.location,
            start_time=a.start_time, end_time=a.end_time, qr_token=a.qr_token,
            checkin_code=a.checkin_code, checkin_mode=a.checkin_mode, checkin_interval=a.checkin_interval,
            author_id=a.author_id, author_name=a.author.real_name or a.author.username,
            participant_count=total, signed_count=signed,
            my_sign_status=my_status.get(a.id, ""),
            created_at=a.created_at
        ))
    return result



@router.post("/api/activities", response_model=ActivityResponse)
def create_activity(data: ActivityCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    mode = data.checkin_mode if data.checkin_mode in ("auto", "fixed") else "auto"
    interval = max(1, int(data.checkin_interval or 2))
    act = Activity(title=data.title, description=data.description, location=data.location,
                   start_time=datetime.fromisoformat(data.start_time.replace("Z", "+00:00")),
                   end_time=datetime.fromisoformat(data.end_time.replace("Z", "+00:00")),
                   checkin_code=generate_checkin_code(), checkin_mode=mode, checkin_interval=interval,
                   author_id=current_user.id)
    db.add(act)
    db.commit()
    db.refresh(act)
    return ActivityResponse(id=act.id, title=act.title, description=act.description, location=act.location,
                            start_time=act.start_time, end_time=act.end_time, qr_token=act.qr_token,
                            checkin_code=act.checkin_code, checkin_mode=act.checkin_mode, checkin_interval=act.checkin_interval,
                            author_id=act.author_id, author_name=current_user.real_name,
                            participant_count=0, signed_count=0, created_at=act.created_at)



@router.put("/api/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(activity_id: int, data: ActivityUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    if data.title is not None: act.title = data.title
    if data.description is not None: act.description = data.description
    if data.location is not None: act.location = data.location
    if data.start_time is not None: act.start_time = datetime.fromisoformat(data.start_time.replace("Z", "+00:00"))
    if data.end_time is not None: act.end_time = datetime.fromisoformat(data.end_time.replace("Z", "+00:00"))
    if data.checkin_mode is not None:
        act.checkin_mode = data.checkin_mode if data.checkin_mode in ("auto", "fixed") else "auto"
    if data.checkin_interval is not None:
        act.checkin_interval = max(1, int(data.checkin_interval))
    db.commit()
    db.refresh(act)
    total = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == act.id).count()
    signed = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == act.id,
        ActivityParticipant.sign_status.in_(["present", "late"])
    ).count()
    return ActivityResponse(id=act.id, title=act.title, description=act.description, location=act.location,
                            start_time=act.start_time, end_time=act.end_time, qr_token=act.qr_token,
                            checkin_code=act.checkin_code, checkin_mode=act.checkin_mode, checkin_interval=act.checkin_interval,
                            author_id=act.author_id, author_name=act.author.real_name or act.author.username,
                            participant_count=total, signed_count=signed, created_at=act.created_at)



@router.delete("/api/activities/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    db.delete(act)
    db.commit()
    return {"message": "删除成功"}



@router.get("/api/activities/{activity_id}/participants", response_model=list[ParticipantResponse])
def list_participants(activity_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    parts = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == activity_id).all()
    return [ParticipantResponse(
        id=p.id, student_id=p.student_id,
        student_name=p.student.real_name or p.student.username,
        student_student_id=p.student.student_id,
        political_status=p.student.political_status,
        student_qq=p.student.qq_number or "",
        sign_status=p.sign_status, sign_time=p.sign_time
    ) for p in parts]



@router.post("/api/activities/{activity_id}/import-all-students")
def import_all_students(activity_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """将全班学生导入活动参与名单"""
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    students = db.query(User).filter(User.role == "student").all()
    existing_ids = set(
        p[0] for p in db.query(ActivityParticipant.student_id).filter(
            ActivityParticipant.activity_id == activity_id
        ).all()
    )
    count = 0
    for s in students:
        if s.id not in existing_ids:
            db.add(ActivityParticipant(activity_id=activity_id, student_id=s.id, sign_status="absent"))
            count += 1
    db.commit()
    return {"message": f"已导入 {count} 名学生", "count": count}



@router.post("/api/activities/{activity_id}/import-participants")
def import_participants(activity_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """导入指定学生到活动（{ student_ids: [1,2,3] }）"""
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    student_ids = data.get("student_ids", [])
    existing_ids = set(
        p[0] for p in db.query(ActivityParticipant.student_id).filter(
            ActivityParticipant.activity_id == activity_id
        ).all()
    )
    count = 0
    for sid in student_ids:
        if sid not in existing_ids:
            db.add(ActivityParticipant(activity_id=activity_id, student_id=sid, sign_status="absent"))
            count += 1
    db.commit()
    return {"message": f"已导入 {count} 名学生", "count": count}



@router.get("/api/activities/{activity_id}/export")
def export_activity_participants(activity_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """导出活动参与名单为Excel"""
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    parts = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == activity_id).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "活动名单"
    header_font = openpyxl.styles.Font(bold=True, size=11)
    header_fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = openpyxl.styles.Font(bold=True, size=11, color="FFFFFF")
    center_align = openpyxl.styles.Alignment(horizontal="center", vertical="center")
    thin_border = openpyxl.styles.Border(
        left=openpyxl.styles.Side(style="thin"), right=openpyxl.styles.Side(style="thin"),
        top=openpyxl.styles.Side(style="thin"), bottom=openpyxl.styles.Side(style="thin"))
    headers = ["序号", "姓名", "学号", "政治面貌", "签到状态", "签到时间"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font_white; cell.fill = header_fill; cell.alignment = center_align; cell.border = thin_border
    status_map = {"present": "已签到", "late": "迟到", "leave": "请假", "absent": "未签到"}
    for i, p in enumerate(parts, 1):
        row_data = [i, p.student.real_name or p.student.username, p.student.student_id,
                    p.student.political_status, status_map.get(p.sign_status, p.sign_status),
                    p.sign_time.strftime("%Y-%m-%d %H:%M") if p.sign_time else ""]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=i + 1, column=col, value=val)
            cell.alignment = center_align; cell.border = thin_border
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    filename = quote(f"{act.title}_活动名单.xlsx")
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})



@router.put("/api/activities/{activity_id}/sign-in")
def update_sign_status(activity_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """更新签到状态 { student_id: int, sign_status: str }"""
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    student_id = data.get("student_id")
    sign_status = data.get("sign_status", "absent")
    part = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == activity_id,
        ActivityParticipant.student_id == student_id
    ).first()
    if not part:
        part = ActivityParticipant(activity_id=activity_id, student_id=student_id)
        db.add(part)
    part.sign_status = sign_status
    if sign_status in ("present", "late"):
        part.sign_time = beijing_now()
    db.commit()
    return {"message": "签到状态已更新"}



@router.post("/api/activities/{activity_id}/refresh-checkin-code")
def refresh_checkin_code(activity_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """刷新活动四位数字签到码"""
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    act.checkin_code = generate_checkin_code()
    db.commit()
    return {"checkin_code": act.checkin_code, "checkin_mode": act.checkin_mode, "checkin_interval": act.checkin_interval}



@router.put("/api/activities/{activity_id}/checkin-mode")
def set_checkin_mode(activity_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """设置签到模式与刷新间隔 { mode: 'auto' | 'fixed', interval: int }"""
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    mode = data.get("mode", "auto")
    if mode not in ("auto", "fixed"):
        raise HTTPException(status_code=400, detail="无效的签到模式")
    act.checkin_mode = mode
    if data.get("interval") is not None:
        act.checkin_interval = max(1, int(data["interval"]))
    db.commit()
    return {"checkin_code": act.checkin_code, "checkin_mode": act.checkin_mode, "checkin_interval": act.checkin_interval}



@router.post("/api/activities/verify-checkin")
def verify_checkin(data: CheckinVerifyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """学生输入四位数字签到码进行签到"""
    act = db.query(Activity).filter(Activity.id == data.activity_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="活动不存在")
    code = (data.code or "").strip()
    if len(code) != 4 or not code.isdigit() or act.checkin_code != code:
        raise HTTPException(status_code=400, detail="无效的签到码")
    part = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == data.activity_id,
        ActivityParticipant.student_id == current_user.id
    ).first()
    if not part:
        raise HTTPException(status_code=400, detail="你不在本次活动名单中")
    if part.sign_status in ("present", "late"):
        return {"message": "已签到，请勿重复签到", "status": "already"}
    part.sign_status = "present"
    part.sign_time = beijing_now()
    db.commit()
    return {"message": "签到成功", "status": "present"}

