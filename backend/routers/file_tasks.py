from auth import get_current_user
from auth import require_admin
from config import ALLOWED_DOC_EXTENSIONS
from config import UPLOAD_DIR
from config import ZIP_BATCH_MAX_SIZE
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from datetime import datetime
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Header
from fastapi import UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.responses import Response
from models import FileSubmission
from models import GroupAssignment
from models import GroupProject
import json
from models import FileTask
from models import User
from models import beijing_now
from schemas import FileSubmissionResponse
from schemas import FileTaskCreate
from schemas import FileTaskResponse
from schemas import UserResponse
from services.files import build_zip_response, safe_upload_path, save_upload, save_upload_async, attachment_headers
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.mailer import send_emails_batch
from services.naming import compute_submit_filename
from services.qq import _get_qq_config, _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from urllib.parse import quote
import io
import os
import zipfile

router = APIRouter(tags=["file_tasks"])


@router.get("/api/file-tasks", response_model=list[FileTaskResponse])
def list_file_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tasks = db.query(FileTask).order_by(FileTask.created_at.desc()).all()
    result = []
    for t in tasks:
        submission_count = db.query(FileSubmission).filter(FileSubmission.task_id == t.id).count()
        result.append(FileTaskResponse(id=t.id, title=t.title, description=t.description,
                       created_at=t.created_at, deadline=t.deadline, author_id=t.author_id,
                       author_name=t.author.real_name if t.author else "",
                       author_qq=t.author.qq_number if t.author else "",
                       submission_count=submission_count,
                       naming_pattern=t.naming_pattern or "{name}_{sid}",
                       group_project_id=t.group_project_id,
                       group_project_name=t.group_project.name if t.group_project else None))
    return result



@router.post("/api/file-tasks", response_model=FileTaskResponse)
def create_file_task(data: FileTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = FileTask(title=data.title, description=data.description,
                    deadline=datetime.fromisoformat(data.deadline), author_id=current_user.id,
                    naming_pattern=data.naming_pattern or "{name}_{sid}",
                    group_project_id=data.group_project_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return FileTaskResponse(id=task.id, title=task.title, description=task.description,
                            created_at=task.created_at, deadline=task.deadline,
                            author_id=task.author_id, author_name=current_user.real_name,
                            author_qq=current_user.qq_number,
                            submission_count=0, naming_pattern=task.naming_pattern,
                            group_project_id=task.group_project_id,
                            group_project_name=task.group_project.name if task.group_project else None)



@router.delete("/api/file-tasks/{task_id}")
def delete_file_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    # 删除提交文件
    for sub in task.submissions:
        file_path = safe_upload_path(sub.file_path)
        if os.path.isfile(file_path):
            os.remove(file_path)
    db.delete(task)
    db.commit()
    return {"message": "删除成功"}



@router.put("/api/file-tasks/{task_id}", response_model=FileTaskResponse)
def update_file_task(task_id: int, data: FileTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """编辑文件任务"""
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    task.title = data.title
    task.description = data.description
    task.deadline = datetime.fromisoformat(data.deadline)
    task.naming_pattern = data.naming_pattern or "{name}_{sid}"
    task.group_project_id = data.group_project_id
    db.commit()
    db.refresh(task)
    return FileTaskResponse(id=task.id, title=task.title, description=task.description,
                            created_at=task.created_at, deadline=task.deadline,
                            author_id=task.author_id, author_name=current_user.real_name,
                            author_qq=current_user.qq_number,
                            submission_count=len(task.submissions), naming_pattern=task.naming_pattern,
                            group_project_id=task.group_project_id,
                            group_project_name=task.group_project.name if task.group_project else None)



@router.post("/api/file-tasks/{task_id}/submit")
async def submit_files(task_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """提交文件（支持多文件同时上传，重新提交会覆盖旧文件）"""
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")

    # 截止时间检查
    if task.deadline and beijing_now() > task.deadline:
        raise HTTPException(status_code=400, detail="已过截止时间，不可再提交文件")

    # 删除该学生此任务的旧文件（覆盖模式）
    old_subs = db.query(FileSubmission).filter(
        FileSubmission.task_id == task_id,
        FileSubmission.student_id == current_user.id
    ).all()
    for old in old_subs:
        old_path = safe_upload_path(old.file_path)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
        db.delete(old)

    pattern = task.naming_pattern or "{name}_{sid}"

    submitted = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file.filename}")

        base_name = compute_submit_filename(
            pattern, current_user, task, task.group_project_id, file.filename, db
        )

        # 同名文件加序号避免覆盖
        filename = f"{base_name}{ext}"
        counter = 1
        while os.path.exists(os.path.join(UPLOAD_DIR, filename)):
            filename = f"{base_name}_{counter}{ext}"
            counter += 1

        file_path = safe_upload_path(filename)
        await save_upload_async(file, file_path)

        sub = FileSubmission(task_id=task_id, student_id=current_user.id,
                             file_path=filename, original_name=file.filename)
        db.add(sub)
        submitted.append({"id": None, "filename": filename, "original_name": file.filename})
    db.commit()

    # 回填 id
    for item in submitted:
        s = db.query(FileSubmission).filter(FileSubmission.file_path == item["filename"],
                                             FileSubmission.task_id == task_id,
                                             FileSubmission.student_id == current_user.id).first()
        if s: item["id"] = s.id

    return {"message": f"成功提交 {len(submitted)} 个文件", "files": submitted}



@router.get("/api/file-tasks/{task_id}/submissions", response_model=list[FileSubmissionResponse])
def list_submissions(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                     x_view_mode: str = Header(None)):
    subs = db.query(FileSubmission).filter(FileSubmission.task_id == task_id).order_by(FileSubmission.submitted_at.desc()).all()
    is_admin = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    return [FileSubmissionResponse(
        id=s.id, task_id=s.task_id, student_id=s.student_id,
        student_name=s.student.real_name if s.student else "",
        student_student_id=s.student.student_id if s.student else "",
        file_path=s.file_path if (is_admin or s.student_id == current_user.id) else "",
        original_name=s.original_name if (is_admin or s.student_id == current_user.id) else "",
        submitted_at=s.submitted_at) for s in subs]



@router.get("/api/file-tasks/submissions/{submission_id}/download")
def download_submission(submission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                        x_view_mode: str = Header(None)):
    """下载提交文件（仅管理员和文件提交者本人可下载，使用当前命名规则）"""
    sub = db.query(FileSubmission).filter(FileSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权下载此文件")
    fpath = safe_upload_path(sub.file_path)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="文件不存在")
    # 根据当前命名规则计算下载文件名
    task = db.query(FileTask).filter(FileTask.id == sub.task_id).first()
    student = db.query(User).filter(User.id == sub.student_id).first()
    ext = os.path.splitext(sub.file_path)[1]
    if task and student:
        pattern = task.naming_pattern or "{name}_{sid}"
        new_base = compute_submit_filename(pattern, student, task, task.group_project_id, sub.original_name, db)
        download_name = f"{new_base}{ext}"
    else:
        download_name = sub.original_name or sub.file_path
    filename = quote(download_name)
    return FileResponse(fpath, media_type="application/octet-stream", headers=attachment_headers(download_name))



@router.delete("/api/file-tasks/submissions/{submission_id}")
def delete_submission(submission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
                      x_view_mode: str = Header(None)):
    """删除提交文件（管理员可删除任意，学生仅可删除自己的）"""
    sub = db.query(FileSubmission).filter(FileSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此文件")
    fpath = safe_upload_path(sub.file_path)
    if os.path.isfile(fpath):
        os.remove(fpath)
    db.delete(sub)
    db.commit()
    return {"message": "删除成功"}



@router.get("/api/file-tasks/{task_id}/unsubmitted", response_model=list[UserResponse])
def get_unsubmitted_students(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """获取尚未提交文件任务的学生名单（仅管理员可见）"""
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    submitted_ids = set(
        s[0] for s in db.query(FileSubmission.student_id).filter(
            FileSubmission.task_id == task_id
        ).all()
    )
    all_students = db.query(User).filter(User.role == "student").all()
    return [u for u in all_students if u.id not in submitted_ids]



@router.post("/api/file-tasks/{task_id}/send-email")
def send_task_email_reminder(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """一键发送邮件提醒未提交的学生"""
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    submitted_ids = set(
        s[0] for s in db.query(FileSubmission.student_id).filter(
            FileSubmission.task_id == task_id
        ).all()
    )
    all_students = db.query(User).filter(User.role == "student").all()
    unsubmitted = [u for u in all_students if u.id not in submitted_ids]
    to_emails = [s.email for s in unsubmitted if s.email and "@" in s.email]
    if not to_emails:
        raise HTTPException(status_code=400, detail="没有可用的未提交学生邮箱")
    deadline_str = task.deadline.strftime("%Y-%m-%d %H:%M") if task.deadline else "无"
    subject = f"[催交通知] {task.title}"
    body = f"【文件任务催交】\n\n任务：{task.title}\n截止时间：{deadline_str}\n描述：{task.description or '无'}\n发布人：{current_user.real_name}\n联系方式：QQ {current_user.qq_number or '未填写'}\n\n请您尽快登录系统提交文件。\n\n---\n此邮件由智能班务系统自动发送，请勿回复。"
    result = send_emails_batch(to_emails, subject, body, db=db, send_type="file_task", related_id=task_id)
    return {"success": result.get("success", True), "detail": result}



def _collect_zip_items(db: Session, task=None, structure: str = "flat"):
    """收集需要打包的提交文件，返回 [{path, arcname, size}]（确定性顺序）"""
    items = []
    tasks = [task] if task is not None else db.query(FileTask).order_by(FileTask.id).all()
    task_ids = [t.id for t in tasks]
    submissions = db.query(FileSubmission).filter(FileSubmission.task_id.in_(task_ids)).order_by(FileSubmission.id).all() if task_ids else []
    user_ids = {s.student_id for s in submissions}
    students = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    project_ids = {t.group_project_id for t in tasks if t.group_project_id}
    projects = {p.id: p for p in db.query(GroupProject).filter(GroupProject.id.in_(project_ids)).all()} if project_ids else {}
    group_rows = db.query(GroupAssignment).filter(
        GroupAssignment.project_id.in_(project_ids), GroupAssignment.student_id.in_(user_ids)
    ).all() if project_ids and user_ids else []
    assignments = {(a.project_id, a.student_id): a for a in group_rows}
    by_task = {}
    for submission in submissions:
        by_task.setdefault(submission.task_id, []).append(submission)
    per_student = structure == "per_student"
    for t in tasks:
        pattern = t.naming_pattern or "{name}_{sid}"
        task_folder = t.title.replace("/", "_").replace("\\", "_")
        subs = by_task.get(t.id, [])
        for s in subs:
            fpath = safe_upload_path(s.file_path)
            if not os.path.isfile(fpath):
                continue
            student = students.get(s.student_id)
            ext = os.path.splitext(s.file_path)[1]
            if student:
                effective_pattern = pattern
                if "{group}" in pattern and t.group_project_id:
                    assignment = assignments.get((t.group_project_id, student.id))
                    project = projects.get(t.group_project_id)
                    group_label = f"第{assignment.group_number}组" if assignment else "未分组"
                    if assignment and project and project.group_names:
                        try:
                            group_label = json.loads(project.group_names).get(str(assignment.group_number), group_label)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    effective_pattern = pattern.replace("{group}", group_label)
                new_base = compute_submit_filename(effective_pattern, student, t, None, s.original_name, db)
            else:
                new_base = os.path.splitext(s.file_path)[0].split("/")[-1]
            parts = []
            if task is None:
                parts.append(task_folder)
            if per_student and student:
                safe_name = student.real_name or student.username
                safe_sid = student.student_id or str(student.id)
                student_folder = "".join(c for c in f"{safe_name}_{safe_sid}" if c not in r'<>:"/\|?*')
                parts.append(student_folder)
            parts.append(f"{new_base}{ext}")
            items.append({"path": fpath, "arcname": "/".join(parts), "size": os.path.getsize(fpath)})
    return items



def _split_batches(items: list):
    """按 ZIP_BATCH_MAX_SIZE 将打包项拆分为多批"""
    batches = []
    cur = []
    cur_size = 0
    for it in items:
        if cur and cur_size + it["size"] > ZIP_BATCH_MAX_SIZE:
            batches.append(cur)
            cur = []
            cur_size = 0
        cur.append(it)
        cur_size += it["size"]
    if cur:
        batches.append(cur)
    return batches



def _build_zip_response(items: list, base_filename: str):
    """把一批打包项生成 zip 并返回 Response（同名文件自动加序号避免覆盖）"""
    return build_zip_response(items, base_filename)



@router.get("/api/file-tasks/{task_id}/download-zip-info")
def download_task_zip_info(task_id: int, structure: str = "flat",
                           db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """返回某任务打包下载的分批信息"""
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    items = _collect_zip_items(db, task=task, structure=structure)
    batches = _split_batches(items)
    return {
        "total_batches": len(batches),
        "total_files": len(items),
        "total_size": sum(i["size"] for i in items),
        "batches": [
            {"index": i + 1, "file_count": len(b), "size": sum(x["size"] for x in b)}
            for i, b in enumerate(batches)
        ],
    }



@router.get("/api/file-tasks/{task_id}/download-zip")
def download_task_zip(task_id: int, structure: str = "flat", batch: int | None = None,
                      db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """打包下载某个任务的全部提交文件（支持分批、文件夹结构，使用当前命名规则）"""
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    items = _collect_zip_items(db, task=task, structure=structure)
    if not items:
        raise HTTPException(status_code=404, detail="该任务暂无提交文件")
    batches = _split_batches(items)
    safe_title = task.title.replace("/", "_").replace("\\", "_")
    if batch is not None:
        if batch < 1 or batch > len(batches):
            raise HTTPException(status_code=404, detail="批次不存在")
        selected = batches[batch - 1]
        name = f"{safe_title}_提交文件.zip" if len(batches) == 1 else f"{safe_title}_提交文件_第{batch}批.zip"
    else:
        selected = items
        name = f"{safe_title}_提交文件.zip"
    try:
        return _build_zip_response(selected, name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包下载失败: {str(e)}")



@router.get("/api/file-tasks/{task_id}/students/{student_id}/download-zip")
def download_student_zip(task_id: int, student_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user), x_view_mode: str = Header(None)):
    """打包下载某个学生在该任务下的全部提交文件（使用当前命名规则）"""
    can_manage_all = current_user.role == "admin" or (current_user.is_class_leader and x_view_mode == "admin")
    if not can_manage_all and student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权下载此文件")
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    student = db.query(User).filter(User.id == student_id).first()
    if not student: raise HTTPException(status_code=404, detail="学生不存在")
    subs = db.query(FileSubmission).filter(
        FileSubmission.task_id == task_id,
        FileSubmission.student_id == student_id,
    ).order_by(FileSubmission.id).all()
    if not subs:
        raise HTTPException(status_code=404, detail="该学生暂无提交文件")
    pattern = task.naming_pattern or "{name}_{sid}"
    items = []
    for s in subs:
        fpath = safe_upload_path(s.file_path)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(s.file_path)[1]
        new_base = compute_submit_filename(pattern, student, task, task.group_project_id, s.original_name, db)
        items.append({"path": fpath, "arcname": f"{new_base}{ext}", "size": os.path.getsize(fpath)})
    if not items:
        raise HTTPException(status_code=404, detail="文件不存在")
    safe_name = student.real_name or student.username
    safe_sid = student.student_id or str(student.id)
    safe_student = "".join(c for c in f"{safe_name}_{safe_sid}" if c not in r'<>:"/\|?*')
    try:
        return _build_zip_response(items, f"{safe_student}_提交文件.zip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包下载失败: {str(e)}")



@router.get("/api/file-tasks/download-all-zip-info")
def download_all_tasks_zip_info(structure: str = "flat",
                                db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """返回全部任务打包下载的分批信息"""
    items = _collect_zip_items(db, task=None, structure=structure)
    batches = _split_batches(items)
    return {
        "total_batches": len(batches),
        "total_files": len(items),
        "total_size": sum(i["size"] for i in items),
        "batches": [
            {"index": i + 1, "file_count": len(b), "size": sum(x["size"] for x in b)}
            for i, b in enumerate(batches)
        ],
    }



@router.get("/api/file-tasks/download-all-zip")
def download_all_tasks_zip(structure: str = "flat", batch: int | None = None,
                           db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """打包下载所有任务的提交文件（支持分批、文件夹结构，使用当前命名规则）"""
    items = _collect_zip_items(db, task=None, structure=structure)
    if not items:
        raise HTTPException(status_code=404, detail="暂无可下载的文件")
    batches = _split_batches(items)
    if batch is not None:
        if batch < 1 or batch > len(batches):
            raise HTTPException(status_code=404, detail="批次不存在")
        selected = batches[batch - 1]
        name = "全部任务提交文件.zip" if len(batches) == 1 else f"全部任务提交文件_第{batch}批.zip"
    else:
        selected = items
        name = "全部任务提交文件.zip"
    try:
        return _build_zip_response(selected, name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包下载失败: {str(e)}")

