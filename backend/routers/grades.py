from auth import get_current_user
from auth import require_admin
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Header
from fastapi import Query
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.responses import StreamingResponse
from models import Grade
from models import GradeChangeRequest
from models import User
from schemas import GradeChangeRequestCreate
from schemas import GradeChangeRequestProcess
from schemas import GradeChangeRequestResponse
from schemas import GradeCreate
from schemas import GradeResponse
from schemas import GradeUpdate
from services.files import build_zip_response, safe_upload_path, save_upload, read_small_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from services.utils import HAS_OPENPYXL
from services.utils import decode_csv_content
from services.utils import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import csv
import io

router = APIRouter(tags=["grades"])


@router.get("/api/grades", response_model=list[GradeResponse])
def list_grades(student_id: int = Query(None), semester: str = Query(None), academic_year: str = Query(None),
                db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                x_view_mode: str = Header(None)):
    query = db.query(Grade)
    can_view_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_view_all: query = query.filter(Grade.student_id == current_user.id)
    if student_id and can_view_all: query = query.filter(Grade.student_id == student_id)
    if semester: query = query.filter(Grade.semester == semester)
    if academic_year: query = query.filter(Grade.academic_year == academic_year)
    grades = query.order_by(Grade.created_at.desc()).all()
    return [GradeResponse(id=g.id, student_id=g.student_id,
            student_name=g.student.real_name if g.student else "",
            student_student_id=g.student.student_id if g.student else "",
            score=g.score, gpa=g.gpa,
            semester=g.semester, academic_year=g.academic_year,
            class_rank=g.class_rank, total_students=g.total_students, created_at=g.created_at) for g in grades]



@router.post("/api/grades", response_model=GradeResponse)
def create_grade(data: GradeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    grade = Grade(student_id=data.student_id, score=data.score,
                  gpa=data.gpa, semester=data.semester, academic_year=data.academic_year,
                  class_rank=data.class_rank, total_students=data.total_students)
    db.add(grade)
    db.commit()
    db.refresh(grade)
    student = db.query(User).filter(User.id == grade.student_id).first()
    return GradeResponse(id=grade.id, student_id=grade.student_id,
                         student_name=student.real_name if student else "",
                         student_student_id=student.student_id if student else "",
                         score=grade.score, gpa=grade.gpa,
                         semester=grade.semester, academic_year=grade.academic_year,
                         class_rank=grade.class_rank, total_students=grade.total_students, created_at=grade.created_at)



@router.put("/api/grades/{grade_id}", response_model=GradeResponse)
def update_grade(grade_id: int, data: GradeUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade: raise HTTPException(status_code=404, detail="成绩不存在")
    if data.student_id is not None: grade.student_id = data.student_id
    if data.score is not None: grade.score = data.score
    if data.gpa is not None: grade.gpa = data.gpa
    if data.semester is not None: grade.semester = data.semester
    if data.academic_year is not None: grade.academic_year = data.academic_year
    if data.class_rank is not None: grade.class_rank = data.class_rank
    if data.total_students is not None: grade.total_students = data.total_students
    db.commit()
    db.refresh(grade)
    student = db.query(User).filter(User.id == grade.student_id).first()
    return GradeResponse(id=grade.id, student_id=grade.student_id,
                         student_name=student.real_name if student else "",
                         student_student_id=student.student_id if student else "",
                         score=grade.score, gpa=grade.gpa,
                         semester=grade.semester, academic_year=grade.academic_year,
                         class_rank=grade.class_rank, total_students=grade.total_students, created_at=grade.created_at)



@router.delete("/api/grades/{grade_id}")
def delete_grade(grade_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade: raise HTTPException(status_code=404, detail="成绩不存在")
    db.delete(grade)
    db.commit()
    return {"message": "删除成功"}



@router.post("/api/grades/import-file")
async def import_grades_file(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    created, errors = 0, []
    content = await read_small_upload(file, MAX_IMPORT_BYTES)
    filename = file.filename or ""
    rows = []
    if filename.lower().endswith(".csv"):
        text = decode_csv_content(content)
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    elif filename.lower().endswith((".xlsx", ".xls")):
        if not HAS_OPENPYXL: raise HTTPException(status_code=500, detail="服务器未安装 openpyxl")
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            rows.append(dict(zip(headers, row)))
    else:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls / .csv 格式")

    for row in rows:
        try:
            sid = row.get("student_id") or row.get("学号") or ""
            student = db.query(User).filter(User.student_id == str(sid)).first() if sid else None
            if not student:
                errors.append(f"学号 {sid} 不存在")
                continue
            grade = Grade(student_id=student.id,
                          score=float(row.get("score") or row.get("成绩") or 0),
                          gpa=float(row.get("gpa") or row.get("绩点") or 0),
                          semester=str(row.get("semester") or row.get("学期") or ""),
                          academic_year=str(row.get("academic_year") or row.get("学年") or ""),
                          class_rank=int(row.get("class_rank") or row.get("班级排名") or 0),
                          total_students=int(row.get("total_students") or row.get("班级人数") or 0))
            db.add(grade)
            created += 1
        except Exception as e:
            errors.append(str(e))
    db.commit()
    return {"created": created, "errors": errors}



@router.get("/api/grades/template")
def download_grade_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_id", "score", "gpa", "semester", "academic_year", "class_rank", "total_students"])
    writer.writerow(["2024001", "92", "4.0", "2024-2025-1", "2024-2025", "1", "30"])
    writer.writerow(["2024001", "85", "3.5", "2024-2025-1", "2024-2025", "3", "30"])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=grade_template.csv"})



@router.post("/api/grades/change-request", response_model=GradeChangeRequestResponse)
def create_grade_change_request(data: GradeChangeRequestCreate,
                                 db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    """学生提交成绩修改申请"""
    req = GradeChangeRequest(
        student_id=current_user.id,
        grade_id=data.grade_id,
        proposed_score=data.proposed_score,
        proposed_gpa=data.proposed_gpa,
        proposed_semester=data.proposed_semester,
        proposed_academic_year=data.proposed_academic_year,
        proposed_class_rank=data.proposed_class_rank,
        proposed_total_students=data.proposed_total_students,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _format_change_request(req)



@router.get("/api/grades/change-requests", response_model=list[GradeChangeRequestResponse])
def list_grade_change_requests(status: str = Query(None),
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user),
                                x_view_mode: str = Header(None)):
    """查看成绩修改申请：管理端看全部，学生端看自己的"""
    can_view_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    query = db.query(GradeChangeRequest)
    if not can_view_all:
        query = query.filter(GradeChangeRequest.student_id == current_user.id)
    if status:
        query = query.filter(GradeChangeRequest.status == status)
    query = query.order_by(GradeChangeRequest.created_at.desc())
    return [_format_change_request(r) for r in query.all()]



@router.put("/api/grades/change-requests/{req_id}/approve")
def approve_grade_change_request(req_id: int, data: GradeChangeRequestProcess = None,
                                  db: Session = Depends(get_db),
                                  current_user: User = Depends(require_admin)):
    """管理员审批通过：应用修改到实际成绩"""
    req = db.query(GradeChangeRequest).filter(GradeChangeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")

    if req.grade_id:
        # 修改已有成绩
        grade = db.query(Grade).filter(Grade.id == req.grade_id).first()
        if grade:
            grade.score = req.proposed_score
            grade.gpa = req.proposed_gpa
            grade.semester = req.proposed_semester
            grade.academic_year = req.proposed_academic_year
            grade.class_rank = req.proposed_class_rank
            grade.total_students = req.proposed_total_students
    else:
        # 新增成绩
        grade = Grade(
            student_id=req.student_id,
            score=req.proposed_score,
            gpa=req.proposed_gpa,
            semester=req.proposed_semester,
            academic_year=req.proposed_academic_year,
            class_rank=req.proposed_class_rank,
            total_students=req.proposed_total_students,
        )
        db.add(grade)
    req.status = "approved"
    req.admin_id = current_user.id
    if data and data.comment:
        req.admin_comment = data.comment
    db.commit()
    db.refresh(req)
    return _format_change_request(req)



@router.put("/api/grades/change-requests/{req_id}/reject")
def reject_grade_change_request(req_id: int, data: GradeChangeRequestProcess = None,
                                 db: Session = Depends(get_db),
                                 current_user: User = Depends(require_admin)):
    """管理员驳回申请"""
    req = db.query(GradeChangeRequest).filter(GradeChangeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")
    req.status = "rejected"
    req.admin_id = current_user.id
    if data and data.comment:
        req.admin_comment = data.comment
    db.commit()
    db.refresh(req)
    return _format_change_request(req)



def _format_change_request(r):
    return GradeChangeRequestResponse(
        id=r.id, student_id=r.student_id,
        student_name=r.student.real_name if r.student else "",
        student_student_id=r.student.student_id if r.student else "",
        grade_id=r.grade_id,
        proposed_score=r.proposed_score, proposed_gpa=r.proposed_gpa,
        proposed_semester=r.proposed_semester, proposed_academic_year=r.proposed_academic_year,
        proposed_class_rank=r.proposed_class_rank, proposed_total_students=r.proposed_total_students,
        status=r.status,
        admin_id=r.admin_id,
        admin_name=r.admin.real_name if r.admin else "",
        admin_comment=r.admin_comment or "",
        created_at=r.created_at, updated_at=r.updated_at,
    )

