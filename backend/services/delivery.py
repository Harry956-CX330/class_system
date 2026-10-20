"""Explicit notification targets, stored alongside existing settings without migrations."""
import re
from fastapi import Body, HTTPException
from pydantic import BaseModel, Field, field_validator
from services.private_settings import read_settings, write_settings, settings_lock

class DeliverySelection(BaseModel):
    group_ids: list[str] | None = Field(default=None, max_length=10)
    recipient_ids: list[int] | None = Field(default=None, max_length=200)
    at_all: bool = Field(default=False, strict=True)

    @field_validator('recipient_ids')
    @classmethod
    def valid_users(cls, value):
        if value is not None and (not value or any(uid < 1 for uid in value) or len(set(value)) != len(value)):
            raise ValueError('请选择有效且不重复的收件人')
        return value

    @field_validator('group_ids')
    @classmethod
    def valid_groups(cls, value):
        if value is not None and (not value or any(not re.fullmatch(r'[1-9][0-9]{4,11}', gid) for gid in value) or len(set(value)) != len(value)):
            raise ValueError('请选择有效且不重复的群号')
        return value


def delivery_selection(data: DeliverySelection | None = Body(default=None)):
    return data or DeliverySelection()


def qq_groups(cfg):
    with settings_lock:
        values = read_settings('qq-groups.json', {}).get('groups', [])
    groups = [{'id': str(row['id']), 'name': str(row.get('name') or row['id'])[:50]} for row in values]
    if cfg and cfg.group_id and not any(row['id'] == cfg.group_id for row in groups):
        groups.insert(0, {'id': cfg.group_id, 'name': '默认群'})
    return groups[:10]


def choose_users(users, selection):
    if selection.recipient_ids is None:
        return users
    available = {user.id for user in users}
    if not set(selection.recipient_ids) <= available:
        raise HTTPException(409, '收件人状态已变更或不在本次提醒范围，请重新选择')
    return [user for user in users if user.id in selection.recipient_ids]


def send_groups(cfg, message, selection):
    from services.qq import _send_qq_msg
    groups = qq_groups(cfg)
    requested = selection.group_ids if selection.group_ids is not None else ([cfg.group_id] if cfg.group_id else [])
    if not requested or not set(requested) <= {row['id'] for row in groups}:
        raise HTTPException(422, '请选择已配置的 QQ 群')
    results = []
    for gid in requested:
        try:
            result = _send_qq_msg(cfg.api_url, 'send_group_msg', {'group_id': int(gid), 'message': message, 'at_all': selection.at_all})
            ok = result.get('status') == 'ok' or result.get('retcode') == 0
            results.append({'group_id': gid, 'success': ok, 'partial': bool(result.get('partial')), 'detail': '' if ok else result.get('error', '机器人未确认发送成功')})
        except HTTPException as error:
            results.append({'group_id': gid, 'success': False, 'detail': error.detail})
    sent = sum(row['success'] for row in results)
    failures = [row for row in results if not row['success']]
    detail = '；'.join(f"{row['group_id']}：{str(row.get('detail') or '机器人未确认发送成功')[:120]}" for row in failures[:2])
    return {'message': f'QQ群通知完成：成功 {sent} 个群，失败 {len(results)-sent} 个群' + ('。'+detail if detail else ''), 'sent': sent,
            'failed': len(results)-sent, 'success': sent == len(results), 'targets': results}
