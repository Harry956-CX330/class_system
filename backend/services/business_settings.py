"""Per-record metadata kept in the existing persistent data directory."""
from fastapi import HTTPException
from config import ALLOWED_DOC_EXTENSIONS
from services.private_settings import read_settings, write_settings, settings_lock

def notice_categories():
    with settings_lock:
        return read_settings('notice-categories.json', {})

def set_notice_category(notice_id, category):
    category = (category or '').strip()
    with settings_lock:
        values = notice_categories()
        if category and category != '未分类':
            values[str(notice_id)] = category
        else:
            values.pop(str(notice_id), None)
        write_settings('notice-categories.json', values)

def task_formats(task_id):
    with settings_lock:
        return read_settings('task-formats.json', {}).get(str(task_id), [])

def validate_formats(formats):
    values = sorted(set(ext.lower().strip() for ext in formats))
    if any(ext not in ALLOWED_DOC_EXTENSIONS for ext in values):
        raise HTTPException(422, '包含不支持的文件格式')
    return values

def set_task_formats(task_id, formats):
    with settings_lock:
        values = read_settings('task-formats.json', {})
        if formats:
            values[str(task_id)] = formats
        else:
            values.pop(str(task_id), None)
        write_settings('task-formats.json', values)
