from models import GroupAssignment
from models import GroupProject
from sqlalchemy.orm import Session
import json
import os
import uuid

def compute_submit_filename(pattern: str, student, task, group_project_id: int | None, original_filename: str | None, db: Session) -> str:
    """根据命名规则计算文件名（不含扩展名）"""
    safe_name = student.real_name or student.username
    safe_sid = student.student_id or str(student.id)
    safe_task_title = task.title.replace("/", "_").replace("\\", "_")

    base_name = pattern
    base_name = base_name.replace("{sid3}", safe_sid[-3:] if len(safe_sid) >= 3 else safe_sid)
    base_name = base_name.replace("{sid2}", safe_sid[-2:] if len(safe_sid) >= 2 else safe_sid)
    base_name = base_name.replace("{sid}", safe_sid)
    base_name = base_name.replace("{name}", safe_name)
    base_name = base_name.replace("{task}", safe_task_title)

    if original_filename:
        orig_no_ext = os.path.splitext(original_filename)[0]
        base_name = base_name.replace("{orig}", orig_no_ext)

    # 解析 {group} —— 查找学生在该项目中的分组，优先使用自定义组名
    if "{group}" in base_name and group_project_id:
        ga = db.query(GroupAssignment).filter(
            GroupAssignment.project_id == group_project_id,
            GroupAssignment.student_id == student.id
        ).first()
        if ga:
            project = db.query(GroupProject).filter(GroupProject.id == group_project_id).first()
            group_label = f"第{ga.group_number}组"
            if project and project.group_names:
                try:
                    custom = json.loads(project.group_names)
                    if str(ga.group_number) in custom:
                        group_label = custom[str(ga.group_number)]
                except (json.JSONDecodeError, TypeError):
                    pass
            base_name = base_name.replace("{group}", group_label)
        else:
            base_name = base_name.replace("{group}", "未分组")

    # 清理非法字符
    base_name = "".join(c for c in base_name if c not in r'<>:"/\|?*')
    if not base_name.strip():
        base_name = f"task_{uuid.uuid4().hex[:8]}"

    return base_name

