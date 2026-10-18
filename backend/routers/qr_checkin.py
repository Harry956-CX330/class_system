"""限时扫码签到：静态/动态二维码、设备防代签、名单管理与 Excel 导出。"""
import base64
import io
import secrets
from datetime import timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin
from database import get_db
from models import CheckinRecord, CheckinTask, User, beijing_now
from schemas import QrCheckinManualUpdate, QrCheckinTaskCreate, QrCheckinVerifyRequest
from services.utils import openpyxl

router = APIRouter(tags=["qr-checkin"])

QR_TYPE_STATIC = "static"
QR_TYPE_DYNAMIC = "dynamic"
ALLOWED_REFRESH_SECONDS = (3, 5, 10)


def _new_code() -> str:
    return secrets.token_urlsafe(24)


def _qr_data_url(code: str) -> str:
    try:
        import qrcode
    except ImportError as exc:  # pragma: no cover - dependency declared in requirements
        raise HTTPException(500, "服务器未安装 qrcode") from exc
    image = qrcode.make(code)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def _task_dict(task: CheckinTask, with_qr: bool = False) -> dict:
    data = {
        "id": task.id,
        "name": task.name,
        "duration_minutes": task.duration_minutes,
        "qr_type": task.qr_type,
        "refresh_seconds": task.refresh_seconds,
        "status": task.status,
        "started_at": task.started_at,
        "expires_at": task.expires_at,
        "closed_at": task.closed_at,
        "author_id": task.author_id,
        "author_name": task.author.real_name or task.author.username if task.author else "",
        "created_at": task.created_at,
    }
    if with_qr:
        data["current_code"] = task.current_code
        data["qr_data_url"] = _qr_data_url(task.current_code)
    return data


@router.post("/api/qr-checkin/tasks")
def create_task(data: QrCheckinTaskCreate, db: Session = Depends(get_db, scope="function"),
                current_user: User = Depends(require_admin)):
    now = beijing_now()
    task = CheckinTask(
        name=data.name.strip(),
        duration_minutes=data.duration_minutes,
        qr_type=data.qr_type,
        refresh_seconds=data.refresh_seconds,
        current_code=_new_code(),
        code_updated_at=now,
        status="active",
        started_at=now,
        expires_at=now + timedelta(minutes=data.duration_minutes),
        author_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_dict(task, with_qr=True)


@router.get("/api/qr-checkin/tasks")
def list_tasks(db: Session = Depends(get_db, scope="function"),
               current_user: User = Depends(require_admin)):
    tasks = db.query(CheckinTask).order_by(CheckinTask.created_at.desc()).all()
    result = []
    for task in tasks:
        item = _task_dict(task)
        records = task.records
        item["total_students"] = db.query(User).filter(User.role == "student").count()
        item["signed_count"] = sum(1 for r in records if r.status in ("auto", "manual"))
        item["leave_count"] = sum(1 for r in records if r.status == "leave")
        result.append(item)
    return result


@router.get("/api/qr-checkin/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db, scope="function"),
             current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    return _task_dict(task, with_qr=True)


@router.post("/api/qr-checkin/tasks/{task_id}/refresh-code")
def refresh_code(task_id: int, db: Session = Depends(get_db, scope="function"),
                 current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if task.status != "active":
        raise HTTPException(400, "签到已关闭，无法刷新二维码")
    task.current_code = _new_code()
    task.code_updated_at = beijing_now()
    db.commit()
    return _task_dict(task, with_qr=True)


@router.post("/api/qr-checkin/tasks/{task_id}/close")
def close_task(task_id: int, db: Session = Depends(get_db, scope="function"),
               current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if task.status == "active":
        task.status = "closed"
        task.closed_at = beijing_now()
        db.commit()
    return _task_dict(task)


@router.get("/api/qr-checkin/tasks/{task_id}/records")
def list_records(task_id: int, db: Session = Depends(get_db, scope="function"),
                 current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    students = db.query(User).filter(User.role == "student").order_by(User.sort_order, User.student_id).all()
    records = {r.student_id: r for r in task.records}
    result = []
    for student in students:
        record = records.get(student.id)
        result.append({
            "student_id": student.id,
            "name": student.real_name or student.username,
            "student_no": student.student_id,
            "status": record.status if record else "absent",
            "sign_time": record.sign_time if record else None,
            "device_id": record.device_id if record else "",
        })
    return {"task": _task_dict(task), "records": result}


@router.put("/api/qr-checkin/tasks/{task_id}/manual")
def manual_update(task_id: int, data: QrCheckinManualUpdate,
                  db: Session = Depends(get_db, scope="function"),
                  current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if data.status not in ("manual", "leave"):
        raise HTTPException(400, "无效的签到状态")
    record = db.query(CheckinRecord).filter(
        CheckinRecord.task_id == task_id, CheckinRecord.student_id == data.student_id).first()
    if record is None:
        record = CheckinRecord(task_id=task_id, student_id=data.student_id, status=data.status)
        db.add(record)
    record.status = data.status
    if data.status == "manual":
        if record.sign_time is None:
            record.sign_time = beijing_now()
    else:
        record.sign_time = None
        record.device_id = None
    db.commit()
    return {"message": "签到状态已更新"}


@router.post("/api/qr-checkin/verify")
def verify(data: QrCheckinVerifyRequest, db: Session = Depends(get_db, scope="function"),
           current_user: User = Depends(get_current_user)):
    code = data.code.strip()
    task = db.query(CheckinTask).filter(CheckinTask.current_code == code).first()
    if not task:
        raise HTTPException(400, "签到码不存在或已失效")
    if task.status != "active":
        raise HTTPException(400, "该签到已关闭")
    if beijing_now() > task.expires_at:
        raise HTTPException(400, "签到已过期")

    student_record = db.query(CheckinRecord).filter(
        CheckinRecord.task_id == task.id, CheckinRecord.student_id == current_user.id).first()
    if student_record:
        raise HTTPException(400, "该学生已签到，请勿重复签到")

    device_record = db.query(CheckinRecord).filter(
        CheckinRecord.task_id == task.id, CheckinRecord.device_id == data.device_id,
        CheckinRecord.status == "auto").first()
    if device_record:
        raise HTTPException(400, "该设备已完成本次签到")

    record = CheckinRecord(task_id=task.id, student_id=current_user.id,
                           device_id=data.device_id, status="auto", sign_time=beijing_now())
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "该学生或该设备已完成本次签到")
    return {"message": "签到成功", "status": "auto", "task_name": task.name}


@router.get("/api/qr-checkin/tasks/{task_id}/export")
def export_records(task_id: int, db: Session = Depends(get_db, scope="function"),
                   current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if openpyxl is None:
        raise HTTPException(500, "服务器未安装 openpyxl")
    students = db.query(User).filter(User.role == "student").order_by(User.sort_order, User.student_id).all()
    records = {r.student_id: r for r in task.records}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "签到名单"
    header_font = openpyxl.styles.Font(bold=True, size=11, color="FFFFFF")
    header_fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    center = openpyxl.styles.Alignment(horizontal="center", vertical="center")
    thin_border = openpyxl.styles.Border(
        left=openpyxl.styles.Side(style="thin"), right=openpyxl.styles.Side(style="thin"),
        top=openpyxl.styles.Side(style="thin"), bottom=openpyxl.styles.Side(style="thin"))
    red_font = openpyxl.styles.Font(color="FF0000")
    leave_fill = openpyxl.styles.PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    headers = ["序号", "姓名", "学号", "签到状态", "签到方式", "签到时间", "设备标识"]
    for col, value in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=value)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border

    status_map = {"auto": "已签到", "manual": "已签到", "leave": "请假", "absent": "缺勤"}
    method_map = {"auto": "扫码自动签到", "manual": "管理员手动补签", "leave": "请假", "absent": "缺勤（未签到）"}
    for index, student in enumerate(students, 1):
        record = records.get(student.id)
        status = record.status if record else "absent"
        row = [index, student.real_name or student.username, student.student_id,
               status_map.get(status, status), method_map.get(status, status),
               record.sign_time.strftime("%Y-%m-%d %H:%M:%S") if record and record.sign_time else "",
               record.device_id if record and record.device_id else ""]
        for col, value in enumerate(row, 1):
            cell = ws.cell(row=index + 1, column=col, value=value)
            cell.alignment = center
            cell.border = thin_border
        if status == "absent":
            for col in range(1, len(headers) + 1):
                ws.cell(row=index + 1, column=col).font = red_font
        elif status == "leave":
            for col in range(1, len(headers) + 1):
                ws.cell(row=index + 1, column=col).fill = leave_fill

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = quote(f"{task.name}_签到名单.xlsx")
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.delete("/api/qr-checkin/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db, scope="function"),
                current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    db.delete(task)
    db.commit()
    return {"message": "签到记录已删除"}
