"""限时扫码签到：静态/动态二维码、设备防重复、名单管理与 Excel 导出。

签到数据存放在独立的 qr_checkin.db（见 qr_db.py），用户信息仍从主库读取。
"""
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
from models import User
from qr_db import CheckinRecord, CheckinTask, beijing_now, get_qr_db
from schemas import QrCheckinManualUpdate, QrCheckinTaskCreate, QrCheckinVerifyRequest
from services.utils import openpyxl

router = APIRouter(tags=["qr-checkin"])

# 动态二维码在 refresh_seconds 之外再留 1 秒网络延迟余量。
DYNAMIC_GRACE_SECONDS = 1


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


def _task_dict(task: CheckinTask, author_name: str = "", with_qr: bool = False) -> dict:
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
        "author_name": author_name,
        "created_at": task.created_at,
    }
    if with_qr:
        data["current_code"] = task.current_code
        data["qr_data_url"] = _qr_data_url(task.current_code)
    return data


def _author_name(main_db: Session, author_id: int) -> str:
    user = main_db.query(User).filter(User.id == author_id).first()
    if not user:
        return "已删除用户"
    return user.real_name or user.username


def _is_dynamic_code_expired(task: CheckinTask) -> bool:
    if task.qr_type != "dynamic" or not task.refresh_seconds:
        return False
    age = (beijing_now() - task.code_updated_at).total_seconds()
    return age > task.refresh_seconds + DYNAMIC_GRACE_SECONDS


@router.post("/api/qr-checkin/tasks")
def create_task(data: QrCheckinTaskCreate, db: Session = Depends(get_qr_db),
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
    return _task_dict(task, current_user.real_name or current_user.username, with_qr=True)


@router.get("/api/qr-checkin/tasks")
def list_tasks(db: Session = Depends(get_qr_db), main_db: Session = Depends(get_db),
               current_user: User = Depends(require_admin)):
    tasks = db.query(CheckinTask).order_by(CheckinTask.created_at.desc()).all()
    total_students = main_db.query(User).filter(User.role == "student").count()
    authors = main_db.query(User).filter(User.id.in_([t.author_id for t in tasks])).all() if tasks else []
    author_map = {u.id: (u.real_name or u.username) for u in authors}
    result = []
    for task in tasks:
        item = _task_dict(task, author_map.get(task.author_id, "已删除用户"))
        records = db.query(CheckinRecord).filter(CheckinRecord.task_id == task.id).all()
        item["total_students"] = total_students
        item["signed_count"] = sum(1 for r in records if r.status in ("auto", "manual"))
        item["leave_count"] = sum(1 for r in records if r.status == "leave")
        result.append(item)
    return result


@router.get("/api/qr-checkin/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_qr_db),
             main_db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    return _task_dict(task, _author_name(main_db, task.author_id), with_qr=True)


@router.post("/api/qr-checkin/tasks/{task_id}/refresh-code")
def refresh_code(task_id: int, db: Session = Depends(get_qr_db),
                 main_db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if task.status != "active":
        raise HTTPException(400, "签到已关闭，无法刷新二维码")
    task.current_code = _new_code()
    task.code_updated_at = beijing_now()
    db.commit()
    return _task_dict(task, _author_name(main_db, task.author_id), with_qr=True)


@router.post("/api/qr-checkin/tasks/{task_id}/close")
def close_task(task_id: int, db: Session = Depends(get_qr_db),
               main_db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if task.status == "active":
        task.status = "closed"
        task.closed_at = beijing_now()
        db.commit()
    return _task_dict(task, _author_name(main_db, task.author_id))


@router.get("/api/qr-checkin/tasks/{task_id}/records")
def list_records(task_id: int, db: Session = Depends(get_qr_db),
                 main_db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    students = main_db.query(User).filter(User.role == "student").order_by(User.sort_order, User.student_id).all()
    records = {r.student_id: r for r in db.query(CheckinRecord).filter(CheckinRecord.task_id == task_id).all()}
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
    return {"task": _task_dict(task, _author_name(main_db, task.author_id)), "records": result}


@router.put("/api/qr-checkin/tasks/{task_id}/manual")
def manual_update(task_id: int, data: QrCheckinManualUpdate,
                  db: Session = Depends(get_qr_db), main_db: Session = Depends(get_db),
                  current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if task.author_id != current_user.id:
        raise HTTPException(403, "只有发起该任务的管理员本人才能补签")
    if data.status not in ("manual", "leave"):
        raise HTTPException(400, "无效的签到状态")
    target = main_db.query(User).filter(User.id == data.student_id, User.role == "student").first()
    if not target:
        raise HTTPException(404, "学生不存在")
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
def verify(data: QrCheckinVerifyRequest, db: Session = Depends(get_qr_db),
           current_user: User = Depends(get_current_user)):
    code = data.code.strip()
    task = db.query(CheckinTask).filter(CheckinTask.current_code == code).first()
    if not task:
        raise HTTPException(400, "签到码不存在或已失效")
    if task.status != "active":
        raise HTTPException(400, "该签到已关闭")
    if beijing_now() > task.expires_at:
        raise HTTPException(400, "签到已过期")
    if _is_dynamic_code_expired(task):
        raise HTTPException(400, "二维码已过期，请刷新后重试")

    student_record = db.query(CheckinRecord).filter(
        CheckinRecord.task_id == task.id, CheckinRecord.student_id == current_user.id).first()
    if student_record:
        raise HTTPException(400, "该学生已签到，请勿重复签到")

    # Web 环境无法可靠证明物理设备身份，device_id 只能作为“同一浏览器重复提交”的
    # 最佳努力防护，不应作为强安全边界。
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


def _safe_text_cell(ws, row: int, col: int, value):
    cell = ws.cell(row=row, column=col, value=value)
    # 强制按文本写入，避免以 = + - @ 开头的用户输入被当作公式。
    cell.data_type = "s"
    return cell


@router.get("/api/qr-checkin/tasks/{task_id}/export")
def export_records(task_id: int, db: Session = Depends(get_qr_db),
                   main_db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    if openpyxl is None:
        raise HTTPException(500, "服务器未安装 openpyxl")

    records = {r.student_id: r for r in db.query(CheckinRecord).filter(CheckinRecord.task_id == task_id).all()}
    students = main_db.query(User).filter(User.role == "student").order_by(User.sort_order, User.student_id).all()

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

    rows = []
    for student in students:
        record = records.pop(student.id, None)
        rows.append((student.real_name or student.username, student.student_id,
                     record.status if record else "absent", record))
    for student_id, record in records.items():
        rows.append(("已删除用户", str(student_id), record.status, record))
    rows.sort(key=lambda r: (r[2] == "absent", r[1]))

    for index, (name, student_no, status, record) in enumerate(rows, 1):
        values = [index, name, student_no, status_map.get(status, status),
                  method_map.get(status, status),
                  record.sign_time.strftime("%Y-%m-%d %H:%M:%S") if record and record.sign_time else "",
                  record.device_id if record and record.device_id else ""]
        for col, value in enumerate(values, 1):
            cell = _safe_text_cell(ws, index + 1, col, str(value))
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
def delete_task(task_id: int, db: Session = Depends(get_qr_db),
                current_user: User = Depends(require_admin)):
    task = db.query(CheckinTask).filter(CheckinTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "签到任务不存在")
    db.query(CheckinRecord).filter(CheckinRecord.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {"message": "签到记录已删除"}
