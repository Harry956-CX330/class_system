"""System-triggered alerts go to every administrator and class leader, never to students."""
from concurrent.futures import ThreadPoolExecutor
from html import escape
from fastapi import HTTPException
from sqlalchemy import or_
from database import SessionLocal
from models import User, QQConfig


def deliver_security_alert(pending):
    from services.mailer import send_emails_batch
    from services.qq import _send_qq_msg
    import re
    with SessionLocal() as db:
        users=db.query(User).filter(or_(User.role=='admin',User.is_class_leader==True)).all()
        emails=list(dict.fromkeys(user.email.strip() for user in users if user.email and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',user.email.strip())))
        qqs=list(dict.fromkeys(user.qq_number.strip() for user in users if user.qq_number and re.fullmatch(r'[1-9][0-9]{4,11}',user.qq_number.strip())))
        cfg=db.query(QQConfig).first()
        api_url=cfg.api_url if cfg and cfg.enabled else ''
        missing_mail=sum(not user.email or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',user.email.strip()) for user in users)
        missing_qq=sum(not user.qq_number or not re.fullmatch(r'[1-9][0-9]{4,11}',user.qq_number.strip()) for user in users)
    event=pending['event']
    body=(f'【服务器安全告警】\n发生时间：{escape(event["time"])}\n异常类型：{escape(event["reason"])}\n'
          f'来源：{escape(event["peer"])}\n接口：{escape(event["path"])}\n已执行：{escape(event["action"])}\n'
          f'合并事件：{pending["incidents"]} 次\n请进入管理端「服务器状态」核查。临时封禁自动到期；共享校园网络可能影响同一出口的同学。')
    previous=pending['channels']
    def email():
        if not emails:return {'sent':0,'failed':0,'missing':missing_mail,'state':'无可用班干邮箱'}
        targets=emails
        try:
            result=send_emails_batch(targets,'服务器安全告警',body,send_type='security_alert')
            # SMTP partial failures are not retried blindly: ambiguous delivery can duplicate mail.
            sent=result.get('sent',0)
            failed=result.get('failed',len(targets) if not result.get('success') else 0)
            return {'sent':sent,'failed':failed,'missing':missing_mail,
                    'state':'部分失败' if sent and failed else '已完成' if sent else '发送失败，请检查邮件配置', 'retry':False}
        except HTTPException as error:return {'sent':0,'failed':len(targets),'missing':missing_mail,'state':'邮件通道繁忙' if error.status_code==503 else '发送失败','retry':error.status_code==503}
        except Exception:return {'sent':0,'failed':len(targets),'missing':missing_mail,'state':'发送失败','retry':False}
    def qq():
        if not api_url:return {'sent':0,'failed':len(qqs),'missing':missing_qq,'state':'QQ 服务未启用'}
        completed=set(previous.get('qq',{}).get('_done',[]))
        attempted=set(previous.get('qq',{}).get('_attempted',[]));retry=False
        for address in qqs:
            if address in attempted:continue
            try:
                result=_send_qq_msg(api_url,'send_private_msg',{'user_id':int(address),'message':body})
                attempted.add(address)
                if result.get('status')=='ok' or result.get('retcode')==0:completed.add(address)
            except HTTPException as error:
                if error.status_code==503:retry=True
                else:attempted.add(address)
            except Exception:attempted.add(address)
        failed=len(qqs)-len(completed)
        return {'sent':len(completed),'failed':failed,'missing':missing_qq,'state':'已完成' if not failed else '部分失败或通道繁忙',
                'retry':retry,'_done':list(completed),'_attempted':list(attempted)}
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='security-alert') as pool:
        futures={}
        for channel,call in [('email',email),('qq',qq)]:
            if previous.get(channel) and not previous[channel].get('retry'):continue
            futures[channel]=pool.submit(call)
        return {channel:future.result() for channel,future in futures.items()}
