"""Predictable portable names for ZIP entries and browser downloads."""
import json
import os
import re
import string
import unicodedata
from datetime import datetime
from fastapi import HTTPException
from models import GroupAssignment, GroupProject, User

VARIABLES = {"name","sid","sid2","sid3","task","orig","group","leader","date","seq"}

def safe_component(value, fallback="附件", max_bytes=160):
    value = unicodedata.normalize("NFKC",str(value))
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", value).strip(" .")
    value = re.sub(r"_+", "_", value) or fallback
    if value.split(".")[0].upper() in {"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}:
        value = "_"+value
    return value.encode("utf-8")[:max_bytes].decode("utf-8",errors="ignore").rstrip(" .") or fallback

def validate_pattern(pattern):
    if not pattern or len(pattern)>160:
        raise HTTPException(422,"命名规则需要 1 至 160 个字符")
    try:
        for _,field,spec,conversion in string.Formatter().parse(pattern):
            if field is not None and (field not in VARIABLES or spec or conversion):
                raise ValueError
    except ValueError:
        raise HTTPException(422,"命名规则包含未知变量或无效括号")
    return pattern

def group_labels(db, project_ids):
    """Resolve groups once per archive, including leaders who have not submitted."""
    if not project_ids:
        return {}
    projects = {p.id: p for p in db.query(GroupProject).filter(GroupProject.id.in_(project_ids)).all()}
    rows = db.query(GroupAssignment).filter(GroupAssignment.project_id.in_(project_ids)).order_by(GroupAssignment.id).all()
    leader_ids = {r.student_id for r in rows if r.role == 'leader'}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(leader_ids)).all()} if leader_ids else {}
    leaders = {(r.project_id, r.group_number): users.get(r.student_id) for r in rows if r.role == 'leader'}
    names = {}
    for project in projects.values():
        try:
            value = json.loads(project.group_names or '{}')
            names[project.id] = value if isinstance(value, dict) else {}
        except (ValueError, TypeError):
            names[project.id] = {}
    labels = {}
    for row in rows:
        group = names.get(row.project_id, {}).get(str(row.group_number), f'第{row.group_number}组')
        user = leaders.get((row.project_id, row.group_number))
        labels[(row.project_id, row.student_id)] = (group, (user.real_name or user.username) if user else '未设置组长')
    return labels


def compute_submit_filename(pattern, student, task, group_project_id, original_filename, db, seq=1, groups=None):
    validate_pattern(pattern)
    sid = student.student_id or str(student.id)
    group, leader = "未分组", "未设置组长"
    project_id = group_project_id or getattr(task,"group_project_id",None)
    if project_id and ("{group}" in pattern or "{leader}" in pattern):
        if groups is None:
            groups = group_labels(db, {project_id})
        group, leader = groups.get((project_id, student.id), (group, leader))
    values = dict(name=student.real_name or student.username,sid=sid,sid2=sid[-2:],sid3=sid[-3:],
        task=task.title,orig=os.path.splitext((original_filename or "附件").replace("\\","/").split("/")[-1])[0],
        group=group,leader=leader,date=task.created_at.strftime("%Y%m%d") if getattr(task,"created_at",None) else "",seq=f"{seq:02d}")
    return safe_component(pattern.format_map(values))
