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

def compute_submit_filename(pattern, student, task, group_project_id, original_filename, db, seq=1):
    validate_pattern(pattern)
    sid = student.student_id or str(student.id)
    group, leader = "未分组", "未设置组长"
    project_id = group_project_id or getattr(task,"group_project_id",None)
    if project_id and ("{group}" in pattern or "{leader}" in pattern):
        assignment = db.query(GroupAssignment).filter_by(project_id=project_id,student_id=student.id).first()
        if assignment:
            group = f"第{assignment.group_number}组"
            project = db.get(GroupProject,project_id)
            try:
                group = json.loads(project.group_names or "{}").get(str(assignment.group_number),group) if project else group
            except (ValueError,TypeError,AttributeError):
                pass
            row = db.query(GroupAssignment).filter_by(project_id=project_id,group_number=assignment.group_number,role="leader").first()
            user = db.get(User,row.student_id) if row else None
            if user:
                leader = user.real_name or user.username
    values = dict(name=student.real_name or student.username,sid=sid,sid2=sid[-2:],sid3=sid[-3:],
        task=task.title,orig=os.path.splitext((original_filename or "附件").replace("\\","/").split("/")[-1])[0],
        group=group,leader=leader,date=task.created_at.strftime("%Y%m%d") if getattr(task,"created_at",None) else "",seq=f"{seq:02d}")
    return safe_component(pattern.format_map(values))
