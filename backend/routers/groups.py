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
from models import GroupAssignment
from models import GroupProject
from models import User
from models import beijing_now
from schemas import GroupAssignmentResponse
from schemas import GroupJoinRequest
from schemas import GroupProjectCreate
from schemas import GroupProjectDetailResponse
from schemas import GroupProjectResponse
from schemas import GroupProjectUpdate
from schemas import UserResponse
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from services.utils import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from urllib.parse import quote
import io
import json

router = APIRouter(tags=["groups"])


@router.post("/api/group-projects", response_model=GroupProjectResponse)
def create_group_project(req: GroupProjectCreate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    capacities_json = json.dumps(req.group_capacities) if req.group_capacities else None
    names_json = json.dumps(req.group_names, ensure_ascii=False) if req.group_names else None
    deadline = datetime.strptime(req.deadline, "%Y-%m-%d %H:%M:%S") if req.deadline else None
    project = GroupProject(name=req.name, group_count=req.group_count,
                           members_per_group=req.members_per_group, deadline=deadline,
                           group_capacities=capacities_json, group_names=names_json,
                           admin_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    project.total_assigned = 0
    project.group_capacities = req.group_capacities
    project.group_names = req.group_names
    return project



@router.get("/api/group-projects", response_model=list[GroupProjectResponse])
def list_group_projects(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    projects = db.query(GroupProject).order_by(GroupProject.created_at.desc()).all()
    for p in projects:
        p.total_assigned = db.query(GroupAssignment).filter(GroupAssignment.project_id == p.id).count()
        p.group_capacities = json.loads(p.group_capacities) if p.group_capacities else None
        p.group_names = json.loads(p.group_names) if p.group_names else None
    return projects



@router.get("/api/group-projects/{project_id}", response_model=GroupProjectDetailResponse)
def get_group_project(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="分组项目不存在")

    # 截止时间过了自动分配未分组学生
    if project.deadline and beijing_now() > project.deadline:
        assigned_ids = set(
            a[0] for a in db.query(GroupAssignment.student_id).filter(
                GroupAssignment.project_id == project_id
            ).all()
        )
        unassigned = db.query(User).filter(User.role == "student", User.id.notin_(assigned_ids)).all() if assigned_ids \
            else db.query(User).filter(User.role == "student").all()

        if unassigned:
            capacities = json.loads(project.group_capacities) if project.group_capacities else None
            # 计算每组当前人数
            group_counts = {i: db.query(GroupAssignment).filter(
                GroupAssignment.project_id == project_id,
                GroupAssignment.group_number == i
            ).count() for i in range(1, project.group_count + 1)}

            # 轮询分配到未满的小组
            idx = 0
            for student in unassigned:
                # 找一个未满的组
                placed = False
                for _ in range(project.group_count):
                    gn = (idx % project.group_count) + 1
                    max_cap = capacities[gn - 1] if capacities and gn <= len(capacities) else project.members_per_group
                    if group_counts[gn] < max_cap:
                        assignment = GroupAssignment(project_id=project_id, group_number=gn,
                                                     student_id=student.id, role="member")
                        db.add(assignment)
                        group_counts[gn] += 1
                        placed = True
                        idx = (idx + 1) % project.group_count
                        break
                    idx = (idx + 1) % project.group_count
                if not placed:
                    break  # 所有组都满了
            db.commit()

    # 按组号整理
    groups = []
    for i in range(1, project.group_count + 1):
        members = db.query(GroupAssignment).filter(
            GroupAssignment.project_id == project_id,
            GroupAssignment.group_number == i
        ).order_by(GroupAssignment.role.desc(), GroupAssignment.created_at).all()
        group_list = []
        for m in members:
            student = db.query(User).filter(User.id == m.student_id).first()
            group_list.append(GroupAssignmentResponse(
                id=m.id, project_id=m.project_id, group_number=m.group_number,
                student_id=m.student_id,
                student_name=student.real_name if student else "",
                student_student_id=student.student_id if student else "",
                role=m.role
            ))
        groups.append(group_list)
    return GroupProjectDetailResponse(
        id=project.id, name=project.name, group_count=project.group_count,
        members_per_group=project.members_per_group,
        group_capacities=json.loads(project.group_capacities) if project.group_capacities else None,
        group_names=json.loads(project.group_names) if project.group_names else None,
        deadline=project.deadline, created_at=project.created_at, groups=groups
    )



@router.put("/api/group-projects/{project_id}")
def update_group_project(project_id: int, req: GroupProjectUpdate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """更新分组项目（支持修改自定义组名）"""
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="分组项目不存在")
    if req.group_names is not None:
        project.group_names = json.dumps(req.group_names, ensure_ascii=False)
    db.commit()
    return {"message": "更新成功", "group_names": req.group_names}



@router.post("/api/group-projects/{project_id}/join", response_model=GroupAssignmentResponse)
def join_group(project_id: int, req: GroupJoinRequest, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="分组项目不存在")
    # 截止时间检查
    if project.deadline and beijing_now() > project.deadline:
        raise HTTPException(status_code=400, detail="已过截止时间，不可自行加入小组，系统将自动分配")
    if req.group_number < 1 or req.group_number > project.group_count:
        raise HTTPException(status_code=400, detail="无效的小组编号")
    if req.role not in ("leader", "member"):
        raise HTTPException(status_code=400, detail="角色只能是 leader 或 member")

    # 检查该组人数是否已满（支持每组不同容量）
    capacities = json.loads(project.group_capacities) if project.group_capacities else None
    max_members = capacities[req.group_number - 1] if capacities and req.group_number <= len(capacities) else project.members_per_group
    count = db.query(GroupAssignment).filter(
        GroupAssignment.project_id == project_id,
        GroupAssignment.group_number == req.group_number
    ).count()
    if count >= max_members:
        raise HTTPException(status_code=400, detail="该小组已满员")

    # 组长只能有一个
    if req.role == "leader":
        existing_leader = db.query(GroupAssignment).filter(
            GroupAssignment.project_id == project_id,
            GroupAssignment.group_number == req.group_number,
            GroupAssignment.role == "leader"
        ).first()
        if existing_leader:
            raise HTTPException(status_code=400, detail="该组已有组长")

    # 满员前最后一人必须是组长
    if count == max_members - 1 and req.role == "member":
        existing_leader = db.query(GroupAssignment).filter(
            GroupAssignment.project_id == project_id,
            GroupAssignment.group_number == req.group_number,
            GroupAssignment.role == "leader"
        ).first()
        if not existing_leader:
            raise HTTPException(status_code=400, detail="该组仅剩一个名额，必须选择组长")

    # 检查是否已加入其他小组
    existing = db.query(GroupAssignment).filter(
        GroupAssignment.project_id == project_id,
        GroupAssignment.student_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="你已加入其他小组")

    assignment = GroupAssignment(project_id=project_id, group_number=req.group_number,
                                 student_id=current_user.id, role=req.role)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return GroupAssignmentResponse(
        id=assignment.id, project_id=assignment.project_id, group_number=assignment.group_number,
        student_id=assignment.student_id,
        student_name=current_user.real_name,
        student_student_id=current_user.student_id,
        role=assignment.role
    )



@router.delete("/api/group-projects/{project_id}/leave")
def leave_group(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    assignment = db.query(GroupAssignment).filter(
        GroupAssignment.project_id == project_id,
        GroupAssignment.student_id == current_user.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="你未加入任何小组")
    # 如果退出的是组长，把组长传给下一个成员    if assignment.role == "leader":
        next_member = db.query(GroupAssignment).filter(
            GroupAssignment.project_id == project_id,
            GroupAssignment.group_number == assignment.group_number,
            GroupAssignment.id != assignment.id
        ).order_by(GroupAssignment.created_at).first()
        if next_member:
            next_member.role = "leader"
    db.delete(assignment)
    db.commit()
    return {"message": "已退出小组"}



@router.delete("/api/group-projects/{project_id}")
def delete_group_project(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="分组项目不存在")
    db.delete(project)
    db.commit()
    return {"message": "已删除分组项目"}



@router.get("/api/group-projects/{project_id}/export")
def export_group_excel(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="分组项目不存在")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = project.name[:31]

    # 表头样式
    header_font = openpyxl.styles.Font(bold=True, size=12)
    header_fill = openpyxl.styles.PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    center_align = openpyxl.styles.Alignment(horizontal="center", vertical="center")
    thin_border = openpyxl.styles.Border(
        left=openpyxl.styles.Side(style="thin"),
        right=openpyxl.styles.Side(style="thin"),
        top=openpyxl.styles.Side(style="thin"),
        bottom=openpyxl.styles.Side(style="thin"),
    )

    headers = ["小组", "角色", "姓名", "学号"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    row = 2
    for g in range(1, project.group_count + 1):
        members = db.query(GroupAssignment).filter(
            GroupAssignment.project_id == project_id,
            GroupAssignment.group_number == g
        ).order_by(GroupAssignment.role.desc(), GroupAssignment.created_at).all()

        if not members:
            cell = ws.cell(row=row, column=1, value=f"第{g}组")
            cell.border = thin_border
            ws.cell(row=row, column=2, value="暂无成员").border = thin_border
            ws.cell(row=row, column=3).border = thin_border
            ws.cell(row=row, column=4).border = thin_border
            row += 1
            continue

        for i, m in enumerate(members):
            student = db.query(User).filter(User.id == m.student_id).first()
            ws.cell(row=row, column=1, value=f"第{g}组" if i == 0 else "").border = thin_border 
            ws.cell(row=row, column=2, value="组长" if m.role == "leader" else "组员").border = thin_border
            ws.cell(row=row, column=3, value=student.real_name if student else "").border = thin_border
            ws.cell(row=row, column=4, value=student.student_id if student else "").border = thin_border
            row += 1
        # 空行分隔
        row += 1

    # 列宽
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"{project.name}_分组名单.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )



@router.get("/api/group-projects/{project_id}/unassigned", response_model=list[UserResponse])
def get_unassigned_students(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """获取未加入分组的学生名单（仅管理员）"""
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="分组项目不存在")
    assigned_ids = set(
        a[0] for a in db.query(GroupAssignment.student_id).filter(
            GroupAssignment.project_id == project_id
        ).all()
    )
    all_students = db.query(User).filter(User.role == "student").all()
    return [u for u in all_students if u.id not in assigned_ids]

