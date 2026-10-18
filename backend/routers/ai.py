"""Authenticated, bounded AI assistance; settings are system-admin only."""
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user, security
from database import SessionLocal
from models import Notice
from services.ai_settings import AISettingsUpdate, MODEL, load_ai_settings, public_settings, save_ai_settings
from services.ai_provider import limiter, complete
from services.ai_context import AIQuestion, build_messages, notice_detail

router = APIRouter(tags=['ai'])


def ai_user(credentials=Depends(security)):
    # A normal get_current_user dependency would retain a SQLite connection during inference.
    with SessionLocal() as db:
        return get_current_user(credentials, db)


def ai_admin(user=Depends(ai_user)):
    if user.role != 'admin':
        raise HTTPException(403, '仅系统管理员可配置 AI 服务')
    return user


def identity(user):
    return f'{user.id}:{user.username}:{user.created_at}'


@router.get('/api/ai/status')
def ai_status(user=Depends(ai_user)):
    settings = load_ai_settings()
    return {'enabled': settings['enabled'] and bool(settings['api_key']), 'model': MODEL,
            'max_images': 4, 'max_notices': 3, 'user_per_minute': settings['user_per_minute'],
            'user_per_day': settings['user_per_day'], 'min_interval_seconds': settings['min_interval_seconds']}


@router.get('/api/ai/settings')
def get_settings(user=Depends(ai_admin)):
    return public_settings(load_ai_settings())


@router.put('/api/ai/settings')
def update_settings(data: AISettingsUpdate, user=Depends(ai_admin)):
    return save_ai_settings(data)


@router.post('/api/ai/test')
def test_connection(user=Depends(ai_admin)):
    settings = load_ai_settings()
    if not settings['api_key']:
        raise HTTPException(422, '请先保存 API Key')
    with limiter.admit(identity(user), settings):
        result = complete(settings, [{'role': 'user', 'content': '请只回复：连接成功'}], connection_test=True)
    return {'ok': True, 'model': MODEL, 'message': '已成功连接智谱模型'}


@router.get('/api/ai/notices')
def search_notices(q: str = Query(default='', max_length=100), limit: int = Query(default=30, ge=1, le=50), user=Depends(ai_user)):
    with SessionLocal() as db:
        query = db.query(Notice.id, Notice.title, Notice.created_at)
        if q.strip():
            # Escape SQL wildcard characters so search has literal substring semantics.
            term = q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.filter(Notice.title.ilike('%' + term + '%', escape='\\'))
        rows = query.order_by(Notice.created_at.desc(), Notice.id.desc()).limit(limit).all()
        return [{'id': row.id, 'title': row.title, 'created_at': row.created_at} for row in rows]


@router.get('/api/ai/notices/{notice_id}')
def get_notice(notice_id: int, user=Depends(ai_user)):
    with SessionLocal() as db:
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(404, '公告不存在')
        return notice_detail(notice)


@router.post('/api/ai/chat')
def ask(data: AIQuestion, user=Depends(ai_user)):
    settings = load_ai_settings()
    if not settings['enabled'] or not settings['api_key']:
        raise HTTPException(503, 'AI 问答尚未启用，请联系管理员配置')
    # Reject excess work immediately. Do not queue model calls, retry automatically, or hold DB locks.
    with limiter.admit(identity(user), settings):
        messages, sources = build_messages(data)
        result = complete(settings, messages)
    return {**result, 'sources': sources,
            'images_used': len(data.notice_images) + len(data.imported_images)}
