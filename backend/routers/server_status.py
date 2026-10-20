from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import require_admin
from services.server_monitor import monitor, DefenseSettings
from services.server_metrics import metrics
from services.private_settings import settings_lock, write_settings

router=APIRouter(tags=['server-status'])

@router.get('/api/server/status')
def server_status(user=Depends(require_admin)):
    result=monitor.snapshot()
    for alert in result['alerts']:
        # Internal retry bookkeeping never belongs in the status response.
        alert['channels']={name:{key:value for key,value in data.items() if not key.startswith('_') and key!='sent_addresses'} for name,data in alert['channels'].items()}
    from database import SessionLocal
    from models import User, QQConfig
    from sqlalchemy import or_
    from services.mailer import load_smtp_config
    import re
    with SessionLocal() as db:
        leaders=db.query(User).filter(or_(User.role=='admin',User.is_class_leader==True)).all()
        qq=db.query(QQConfig).first()
        readiness={'leaders':len(leaders),'email_contacts':sum(bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',(leader.email or '').strip())) for leader in leaders),
                   'qq_contacts':sum(bool(re.fullmatch(r'[1-9][0-9]{4,11}',(leader.qq_number or '').strip())) for leader in leaders),
                   'qq_enabled':bool(qq and qq.enabled and qq.api_url)}
    try:readiness['smtp_configured']=bool(load_smtp_config().get('password'))
    except (OSError,ValueError):readiness['smtp_configured']=False
    return {**result,'resources':metrics(),'can_configure':user.role=='admin','alert_readiness':readiness}

@router.put('/api/server/defense-settings')
def defense_settings(data:DefenseSettings,user=Depends(require_admin)):
    if user.role!='admin':raise HTTPException(403,'仅系统管理员可以调整防护阈值')
    value=data.model_dump()
    with settings_lock:write_settings('defense-settings.json',value)
    with monitor.lock:
        monitor.settings=value;monitor.settings_at=monitor.clock()
    return value

class Unblock(BaseModel):
    peer:str=Field(min_length=1,max_length=50)

@router.post('/api/server/unblock')
def unblock(data:Unblock,user=Depends(require_admin)):
    import ipaddress
    try:peer=str(ipaddress.ip_address(data.peer))
    except ValueError:raise HTTPException(422,'无效的来源地址')
    with monitor.lock:
        state=monitor.peers.get(peer)
        if state:
            state['until']=0;state['violations'].clear();state['seconds'].clear();state.pop('failures',None)
            monitor.sequence+=1
            from services.server_monitor import timestamp
            monitor.events.append({'id':monitor.sequence,'time':timestamp(),'peer':peer,'reason':'班干人工解除临时封禁',
                'path':'/api/server/unblock','action':f'操作者 ID {user.id}','count':1,'_at':monitor.clock()})
            monitor.dirty=True
    return {'message':'已解除该来源临时封禁；后续异常仍会重新触发防护'}
