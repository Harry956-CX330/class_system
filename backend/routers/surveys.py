from services.richtext import clean_html
from services.surveys import options_list, validate_answers, submission_lock
import json
from auth import get_current_user
from auth import require_admin
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from datetime import datetime
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.responses import Response
from models import Survey
from models import SurveyQuestion
from models import SurveyResponse
from models import User
from models import beijing_now
from schemas import SurveyCreate
from schemas import SurveyResponse as SurveyRespSchema
from schemas import SurveyResultListResponse
from schemas import SurveyResultResponse
from schemas import SurveySubmitRequest
from schemas import UserResponse
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.mailer import send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from services.utils import HAS_OPENPYXL
from services.utils import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from urllib.parse import quote
import io

router = APIRouter(tags=["surveys"])


@router.get("/api/surveys", response_model=list[SurveyRespSchema])
def list_surveys(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    surveys = db.query(Survey).order_by(Survey.created_at.desc()).all()
    result = []
    for s in surveys:
        response_count = db.query(SurveyResponse).join(SurveyQuestion).filter(
            SurveyQuestion.survey_id == s.id
        ).with_entities(func.count(func.distinct(SurveyResponse.student_id))).scalar()
        # 当前用户是否已提交
        user_submitted = False
        if True:
            submitted = db.query(SurveyResponse).join(SurveyQuestion).filter(
                SurveyQuestion.survey_id == s.id,
                SurveyResponse.student_id == current_user.id
            ).first()
            user_submitted = submitted is not None
        questions = [{"id": q.id, "survey_id": q.survey_id, "question_text": q.question_text,
                      "description": q.description or "", "question_type": q.question_type,
                      "options": q.options or ""} for q in s.questions]
        result.append({"id": s.id, "title": s.title, "description": s.description or "",
                       "deadline": s.deadline, "is_anonymous": s.is_anonymous,
                       "show_results": s.show_results, "allow_multiple": s.allow_multiple,
                       "created_at": s.created_at, "author_id": s.author_id,
                       "author_name": s.author.real_name if s.author else "",
                       "author_qq": s.author.qq_number if s.author else "",
                       "response_count": response_count, "user_submitted": user_submitted, "has_responses": response_count > 0,
                       "questions": questions})
    return result



@router.post("/api/surveys", response_model=SurveyRespSchema)
def create_survey(data: SurveyCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    deadline = datetime.strptime(data.deadline, "%Y-%m-%d %H:%M:%S") if data.deadline else None
    survey = Survey(title=data.title, description=data.description or "",
                    deadline=deadline, is_anonymous=data.is_anonymous,
                    show_results=data.show_results, allow_multiple=data.allow_multiple,
                    author_id=current_user.id)
    db.add(survey)
    for q in data.questions:
        question = SurveyQuestion(question_text=q.question_text, description=q.description or "",
                                  question_type=q.question_type, options=q.options or "")
        survey.questions.append(question)
    db.commit()
    db.refresh(survey)
    questions = [{"id": q.id, "survey_id": q.survey_id, "question_text": q.question_text,
                  "description": q.description or "", "question_type": q.question_type,
                  "options": q.options or ""} for q in survey.questions]
    return {"id": survey.id, "title": survey.title, "description": survey.description or "",
            "deadline": survey.deadline, "is_anonymous": survey.is_anonymous,
            "show_results": survey.show_results, "allow_multiple": survey.allow_multiple,
            "created_at": survey.created_at, "author_id": survey.author_id,
            "author_name": current_user.real_name, "questions": questions}



@router.get("/api/surveys/{survey_id}", response_model=SurveyRespSchema)
def get_survey(survey_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    questions = [{"id": q.id, "survey_id": q.survey_id, "question_text": q.question_text,
                  "description": q.description or "", "question_type": q.question_type,
                  "options": q.options or ""} for q in survey.questions]
    return {"id": survey.id, "title": survey.title, "description": survey.description or "",
            "deadline": survey.deadline, "is_anonymous": survey.is_anonymous,
            "show_results": survey.show_results, "allow_multiple": survey.allow_multiple,
            "created_at": survey.created_at, "author_id": survey.author_id,
            "author_name": survey.author.real_name if survey.author else "", "questions": questions,
            "has_responses": db.query(SurveyResponse).join(SurveyQuestion).filter(SurveyQuestion.survey_id == survey_id).first() is not None}



@router.put("/api/surveys/{survey_id}", response_model=SurveyRespSchema)
def update_survey(survey_id: int, data: SurveyCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    has_responses = db.query(SurveyResponse).join(SurveyQuestion).filter(SurveyQuestion.survey_id == survey_id).first() is not None
    old = [(q.question_text,clean_html(q.description),q.question_type,options_list(q.options)) for q in survey.questions]
    new = [(q.question_text,clean_html(q.description),q.question_type,options_list(q.options)) for q in data.questions]
    if has_responses and (old != new or survey.is_anonymous != data.is_anonymous):
        raise HTTPException(409, "问卷已有答卷，题目与匿名设置已锁定；请复制问卷后修改")
    if not has_responses:
        survey.questions.clear()
        db.flush()
        for q in data.questions:
            survey.questions.append(SurveyQuestion(question_text=q.question_text,description=q.description,question_type=q.question_type,options=q.options))
    survey.title = data.title
    survey.description = data.description or ""
    survey.deadline = datetime.strptime(data.deadline, "%Y-%m-%d %H:%M:%S") if data.deadline else None
    survey.is_anonymous = data.is_anonymous
    survey.show_results = data.show_results
    survey.allow_multiple = data.allow_multiple
    db.commit()
    db.refresh(survey)
    questions = [{"id": q.id, "survey_id": q.survey_id, "question_text": q.question_text,
                  "description": q.description or "", "question_type": q.question_type,
                  "options": q.options or ""} for q in survey.questions]
    return {"id": survey.id, "title": survey.title, "description": survey.description or "",
            "deadline": survey.deadline, "is_anonymous": survey.is_anonymous,
            "show_results": survey.show_results, "allow_multiple": survey.allow_multiple,
            "created_at": survey.created_at, "author_id": survey.author_id,
            "author_name": current_user.real_name, "questions": questions}



@router.post("/api/surveys/{survey_id}/submit")
def submit_survey(survey_id: int, data: SurveySubmitRequest, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    # One worker: serialize check + replace + commit to avoid double-click races.
    with submission_lock:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise HTTPException(404,"问卷不存在")
        if survey.deadline and beijing_now() > survey.deadline:
            raise HTTPException(400,"已过截止时间，不可再提交问卷")
        validated = validate_answers(survey.questions, data.answers)
        question_ids = [q.id for q in survey.questions]
        existing = db.query(SurveyResponse).filter(SurveyResponse.question_id.in_(question_ids),SurveyResponse.student_id == current_user.id)
        if existing.first() and not survey.allow_multiple:
            raise HTTPException(409,"您已提交过该问卷，不允许重复提交")
        # Repeated submissions replace the previous answer set atomically.
        existing.delete(synchronize_session=False)
        timestamp = beijing_now()
        for question_id,value in validated:
            db.add(SurveyResponse(question_id=question_id,student_id=current_user.id,answer_text=value,created_at=timestamp))
        db.commit()
    return {"message":"提交成功"}



@router.get("/api/surveys/{survey_id}/results")
def survey_results(survey_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey: raise HTTPException(status_code=404, detail="问卷不存在")

    # 收集所有提交的原始数据
    submissions = {}  # student_id -> {student_name, student_id, answers: {question_id: answer}, submitted_at}
    all_responses = db.query(SurveyResponse).join(SurveyQuestion).filter(
        SurveyQuestion.survey_id == survey_id
    ).order_by(SurveyResponse.created_at, SurveyResponse.id).all()
    for r in all_responses:
        if r.student_id not in submissions:
            submissions[r.student_id] = {
                "student_name": r.student.real_name,
                "student_id": r.student.student_id,
                "answers": {},
                "submitted_at": r.created_at,
            }
        submissions[r.student_id]["answers"][r.question_id] = r.answer_text
        if r.created_at > submissions[r.student_id]["submitted_at"]:
            submissions[r.student_id]["submitted_at"] = r.created_at

    questions = []
    for q in survey.questions:
        details = []
        answers = []
        vote_counts = {}
        for sid, sub in submissions.items():
            ans = sub["answers"].get(q.id, "")
            answers.append(ans)
            details.append({
                "student_name": "匿名用户" if survey.is_anonymous else sub["student_name"],
                "student_id": sub["student_id"] if not survey.is_anonymous else "",
                "answer": ans,
                "submitted_at": sub["submitted_at"].isoformat() if sub["submitted_at"] else "",
            })
            # 统计选项票数（单选/多选题）
            if q.question_type in ('single', 'multiple') and ans:
                for opt in ([ans] if q.question_type == "single" else options_list(ans)):
                    opt = opt.strip()
                    if opt:
                        vote_counts[opt] = vote_counts.get(opt, 0) + 1
        questions.append(SurveyResultResponse(
            id=q.id, question_text=q.question_text,
            description=q.description or "",
            question_type=q.question_type, options=q.options or "",
            answers=answers, vote_counts=vote_counts, details=details
        ))

    return SurveyResultListResponse(
        survey_id=survey.id,
        is_anonymous=survey.is_anonymous,
        show_results=survey.show_results,
        allow_multiple=survey.allow_multiple,
        questions=questions
    )



@router.get("/api/surveys/{survey_id}/student-results")
def student_survey_results(survey_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """学生查看投票结果（需show_results=true）"""
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey: raise HTTPException(status_code=404, detail="问卷不存在")
    if not survey.show_results:
        raise HTTPException(status_code=403, detail="管理员未开放结果查看")

    submissions = {}
    all_responses = db.query(SurveyResponse).join(SurveyQuestion).filter(
        SurveyQuestion.survey_id == survey_id
    ).order_by(SurveyResponse.created_at, SurveyResponse.id).all()
    for r in all_responses:
        if r.student_id not in submissions:
            submissions[r.student_id] = {
                "student_name": r.student.real_name,
                "student_id": r.student.student_id,
                "answers": {},
                "submitted_at": r.created_at,
            }
        submissions[r.student_id]["answers"][r.question_id] = r.answer_text
        if r.created_at > submissions[r.student_id]["submitted_at"]:
            submissions[r.student_id]["submitted_at"] = r.created_at

    questions = []
    for q in survey.questions:
        vote_counts = {}
        details = []
        answers = []
        for sid, sub in submissions.items():
            ans = sub["answers"].get(q.id, "")
            answers.append(ans)
            details.append({
                "student_name": "匿名用户" if survey.is_anonymous else sub["student_name"],
                "student_id": sub["student_id"] if not survey.is_anonymous else "",
                "answer": ans,
                "submitted_at": sub["submitted_at"].isoformat() if sub["submitted_at"] else "",
            })
            if q.question_type in ('single', 'multiple') and ans:
                for opt in ([ans] if q.question_type == "single" else options_list(ans)):
                    opt = opt.strip()
                    if opt:
                        vote_counts[opt] = vote_counts.get(opt, 0) + 1
        questions.append(SurveyResultResponse(
            id=q.id, question_text=q.question_text,
            description=q.description or "",
            question_type=q.question_type, options=q.options or "",
            answers=[], vote_counts=vote_counts, details=[]
        ))

    return SurveyResultListResponse(
        survey_id=survey.id,
        is_anonymous=survey.is_anonymous,
        show_results=survey.show_results,
        allow_multiple=survey.allow_multiple,
        questions=questions
    )



@router.delete("/api/surveys/{survey_id}")
def delete_survey(survey_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey: raise HTTPException(status_code=404, detail="问卷不存在")
    db.delete(survey)
    db.commit()
    return {"message": "删除成功"}



@router.get("/api/surveys/{survey_id}/unanswered", response_model=list[UserResponse])
def get_unanswered_students(survey_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """获取尚未填写问卷的学生名单（仅管理员可见）"""
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    answered_ids = set(
        r[0] for r in db.query(SurveyResponse.student_id).filter(
            SurveyResponse.question_id.in_(
                db.query(SurveyQuestion.id).filter(SurveyQuestion.survey_id == survey_id)
            )
        ).distinct().all()
    )
    all_students = db.query(User).filter(User.role == "student").all()
    return [u for u in all_students if u.id not in answered_ids]



@router.get("/api/surveys/{survey_id}/export")
def export_survey_results(survey_id: int, sort_by: str = Query("student_id"),
                          include_all: bool = Query(False), sort_order: str = Query("asc"),
                          db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """导出问卷结果为Excel：固定列 姓名+学号+各题，支持按学号或提交时间排序"""
    if not HAS_OPENPYXL:
        raise HTTPException(status_code=500, detail="服务器未安装openpyxl，无法导出Excel")

    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if survey.is_anonymous and include_all:
        raise HTTPException(400, "匿名问卷不可导出实名未填写名单")
    questions = survey.questions
    question_ids = [q.id for q in questions]

    # 收集已提交学生的答题数据
    submissions = {}  # student_id -> {answers, submitted_at}
    all_responses = db.query(SurveyResponse).filter(
        SurveyResponse.question_id.in_(question_ids)
    ).order_by(SurveyResponse.created_at, SurveyResponse.id).all()
    for r in all_responses:
        if r.student_id not in submissions:
            submissions[r.student_id] = {"answers": {}, "submitted_at": r.created_at}
        submissions[r.student_id]["answers"][r.question_id] = r.answer_text
        if r.created_at > submissions[r.student_id]["submitted_at"]:
            submissions[r.student_id]["submitted_at"] = r.created_at

    # 获取所有学生
    all_students = db.query(User).filter(User.role == "student").order_by(
        User.student_id.asc() if sort_by == "student_id" else User.id
    ).all()

    # 构建导出数据行
    rows_data = []
    for stu in all_students:
        if stu.id in submissions:
            sub = submissions[stu.id]
            row = {
                "student_name": stu.real_name,
                "student_id": stu.student_id,
                "submitted_at": sub["submitted_at"],
                "answers": {qid: sub["answers"].get(qid, "") for qid in question_ids},
                "submitted": True,
            }
            rows_data.append(row)
        elif include_all:
            rows_data.append({
                "student_name": stu.real_name,
                "student_id": stu.student_id,
                "submitted_at": None,
                "answers": {qid: "" for qid in question_ids},
                "submitted": False,
            })

    # 排序
    if sort_by == "student_id":
        reverse = sort_order == "desc"
        rows_data.sort(key=lambda r: r["student_id"] or "", reverse=reverse)
    elif sort_by == "submitted_at":
        # 未提交排到最后
        reverse = sort_order == "desc"
        rows_data.sort(key=lambda r: (
            r["submitted"] if reverse else not r["submitted"],
            r["submitted_at"] or datetime.min
        ), reverse=reverse)

    # 生成Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "问卷结果"

    # 表头
    headers = ["姓名", "学号"]
    for q in questions:
        headers.append(q.question_text)
    if include_all:
        headers.append("提交状态")
    ws.append(headers)

    # 数据行
    for row in rows_data:
        line = ["匿名用户", ""] if survey.is_anonymous else [row["student_name"], row["student_id"]]
        for qid in question_ids:
            line.append(row["answers"].get(qid, ""))
        if include_all:
            line.append("已提交" if row["submitted"] else "未提交")
        ws.append([("\'" + v) if isinstance(v,str) and v.startswith(("=","+","-","@")) else v for v in line])

    # 调整列宽
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 14

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = quote(f"{survey.title}_问卷结果.xlsx")
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )



@router.post("/api/surveys/{survey_id}/send-email")
def send_survey_email_reminder(survey_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """一键发送邮件提醒未填写问卷的学生"""
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    answered_ids = set(
        r[0] for r in db.query(SurveyResponse.student_id).filter(
            SurveyResponse.question_id.in_(
                db.query(SurveyQuestion.id).filter(SurveyQuestion.survey_id == survey_id)
            )
        ).distinct().all()
    )
    all_students = db.query(User).filter(User.role == "student").all()
    unanswered = [u for u in all_students if u.id not in answered_ids]
    to_emails = [s.email for s in unanswered if s.email and "@" in s.email]
    if not to_emails:
        raise HTTPException(status_code=400, detail="没有可用的未填写学生邮箱")
    subject = f"[催交通知] {survey.title}"
    body = f"【调查问卷催交】\n\n问卷：{survey.title}\n描述：{survey.description or '无'}\n发布人：{current_user.real_name}\n联系方式：QQ {current_user.qq_number or '未填写'}\n\n请您尽快登录系统填写问卷。\n\n---\n此邮件由智能班务系统自动发送，请勿回复。"
    result = send_emails_batch(to_emails, subject, body, db=db, send_type="survey", related_id=survey_id)
    return {"success": result.get("success", True), "detail": result}

